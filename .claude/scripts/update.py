#!/usr/bin/env python3
"""
CLEAR Context OS — Update Script

Downloads the latest framework files from upstream and applies them to your
local installation. Your business context (docs/, .private/) is never touched.

Usage:
    python .claude/scripts/update.py              # Interactive update
    python .claude/scripts/update.py --dry-run    # Preview changes only
    python .claude/scripts/update.py --yes        # Apply without confirmation prompt
    python .claude/scripts/update.py --upstream your-org/business-context-os
    python .claude/scripts/update.py --branch main
    python .claude/scripts/update.py --local /path/to/upstream-clone
"""

import os
import sys
import shutil
import hashlib
import tempfile
import zipfile
import difflib
import argparse
import datetime
import ssl
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration — update UPSTREAM_REPO before public launch
# ---------------------------------------------------------------------------

UPSTREAM_REPO   = "walm00/business-context-os"
UPSTREAM_BRANCH = "main"

# Framework directories — synced from upstream on every update.
# Anything NOT listed here is user content and is never touched.
FRAMEWORK_DIRS = [
    ".claude/agents",
    ".claude/hooks",
    ".claude/scripts",
    ".claude/skills",
    "docs/_bcos-framework/architecture",
    "docs/_bcos-framework/guides",
    "docs/_bcos-framework/methodology",
    "docs/_bcos-framework/patterns",
    "docs/_bcos-framework/templates",
    "examples",
]

# Framework files synced from upstream on every update (always overwritten).
# These are NOT user content — they live outside FRAMEWORK_DIRS for structural
# reasons but are owned by the framework.
FRAMEWORK_FILES = [
    ".claude/quality/schedule-config.template.json",
    ".claude/quality/ecosystem/config.json",
    ".claude/quality/ecosystem/lessons-schema.md",
    ".claude/ECOSYSTEM-MAP.md",
]

# .gitignore — merged: new upstream entries are appended, nothing removed
MERGE_FILES = [
    ".gitignore",
]

# CLAUDE.md — user is shown a diff and chooses what to do
REVIEW_FILES = [
    "CLAUDE.md",
]

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def file_hash(path: str) -> str:
    """Hash file contents, normalizing line endings so CRLF == LF."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def posix(path) -> str:
    """Normalize a path to forward-slash form for reliable comparison."""
    return Path(path).as_posix()


def download_upstream(repo: str, branch: str, dest_dir: str) -> str:
    """Download and extract the upstream zip. Returns path to extracted root."""
    url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"
    print(f"  Fetching {url} ...")

    zip_path = os.path.join(dest_dir, "upstream.zip")
    try:
        urllib.request.urlretrieve(url, zip_path)
    except (ssl.SSLError, urllib.error.URLError) as e:
        # macOS python.org installers ship without cert bundle configuration, which
        # surfaces here as an SSL verification failure. Give a targeted hint.
        err = str(e)
        is_ssl = isinstance(e, ssl.SSLError) or "SSL" in err or "certificate" in err.lower()
        print(f"\nERROR: Could not download upstream: {e}")
        if is_ssl and sys.platform == "darwin":
            print("")
            print("SSL certificate verification failed. If you installed Python")
            print("from python.org, run the certificate installer once:")
            print("")
            print("  /Applications/Python\\ 3.*/Install\\ Certificates.command")
            print("")
            print("Or install Python via Homebrew (`brew install python`), which")
            print("ships with certs pre-wired.")
        else:
            print("Check your internet connection and the upstream repo URL.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Could not download upstream: {e}")
        print("Check your internet connection and the upstream repo URL.")
        sys.exit(1)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)

    repo_name = repo.split("/")[-1]
    extracted = os.path.join(dest_dir, f"{repo_name}-{branch}")
    if not os.path.isdir(extracted):
        print(f"\nERROR: Expected extracted directory at {extracted}")
        sys.exit(1)

    return extracted


def collect_framework_files(root: str) -> list[str]:
    """Return all framework file paths relative to root (posix form).
    Skips Python bytecode caches (__pycache__ dirs and *.pyc files) — those are
    machine-local artifacts that should never sync between installs."""
    files = []

    for d in FRAMEWORK_DIRS:
        dir_path = os.path.join(root, d)
        if not os.path.isdir(dir_path):
            continue
        for dirpath, dirnames, filenames in os.walk(dir_path):
            # Prune __pycache__ before descending (modifies dirnames in-place)
            dirnames[:] = [dn for dn in dirnames if dn != "__pycache__"]
            for fname in filenames:
                if fname.endswith(".pyc"):
                    continue
                full = os.path.join(dirpath, fname)
                rel = posix(os.path.relpath(full, root))
                files.append(rel)

    for f in FRAMEWORK_FILES + MERGE_FILES + REVIEW_FILES:
        if os.path.isfile(os.path.join(root, f)):
            files.append(posix(f))

    return files


def classify(upstream_path: str, local_path: str) -> str:
    """Return 'new', 'modified', or 'unchanged'."""
    if not os.path.exists(local_path):
        return "new"
    if file_hash(upstream_path) != file_hash(local_path):
        return "modified"
    return "unchanged"


def print_diff(upstream_path: str, local_path: str, rel: str, max_lines: int = 60):
    with open(local_path,   "r", encoding="utf-8", errors="replace") as f:
        local_lines = f.readlines()
    with open(upstream_path, "r", encoding="utf-8", errors="replace") as f:
        up_lines = f.readlines()

    diff = list(difflib.unified_diff(
        local_lines, up_lines,
        fromfile=f"local/{rel}",
        tofile=f"upstream/{rel}",
        lineterm="",
    ))

    if not diff:
        print("  (files differ by metadata only)")
        return

    for line in diff[:max_lines]:
        print(f"  {line}")
    if len(diff) > max_lines:
        print(f"  ... ({len(diff) - max_lines} more lines — save as .upstream to review in full)")


def merge_gitignore(upstream_path: str, local_path: str) -> int:
    """Append upstream .gitignore entries not already present locally. Returns count added."""
    with open(local_path,   "r", encoding="utf-8") as f:
        local_lines = [l.rstrip("\n") for l in f.readlines()]
    with open(upstream_path, "r", encoding="utf-8") as f:
        up_lines = [l.rstrip("\n") for l in f.readlines()]

    local_entries = {l.strip() for l in local_lines if l.strip() and not l.strip().startswith("#")}
    new_entries = [
        l for l in up_lines
        if l.strip() and not l.strip().startswith("#") and l.strip() not in local_entries
    ]

    if not new_entries:
        return 0

    with open(local_path, "a", encoding="utf-8") as f:
        f.write("\n# Added by CLEAR update script\n")
        for entry in new_entries:
            f.write(entry + "\n")

    return len(new_entries)


def merge_ecosystem_state(upstream_path: str, local_path: str) -> dict:
    """Merge upstream skills/agents inventory into local state.json. Additive only.
    Preserves user-added custom skills/agents and never touches user state
    (`health`, `maintenanceBacklog`, `lastAudit`).

    Returns dict with counts: {"skills_added": N, "agents_added": M}.
    """
    import json as _json

    if not os.path.exists(upstream_path):
        return {"skills_added": 0, "agents_added": 0}

    with open(upstream_path, "r", encoding="utf-8") as f:
        upstream = _json.load(f)

    # Fresh install path — copy upstream wholesale.
    if not os.path.exists(local_path):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(upstream_path, local_path)
        up_skills = upstream.get("inventory", {}).get("skills", {}).get("list", [])
        up_agents = sum(
            len(v) for v in upstream.get("inventory", {}).get("agents", {}).get("byCategory", {}).values()
        )
        return {"skills_added": len(up_skills), "agents_added": up_agents}

    with open(local_path, "r", encoding="utf-8") as f:
        local = _json.load(f)

    skills_added = 0
    agents_added = 0

    up_inv = upstream.get("inventory", {})
    lc_inv = local.setdefault("inventory", {})

    # ---- Skills: list + categorical lists (overlayCapable, discoveryCapable)
    up_skills = up_inv.get("skills", {})
    lc_skills = lc_inv.setdefault("skills", {
        "total": 0, "list": [], "overlayCapable": [], "discoveryCapable": []
    })

    existing = set(lc_skills.get("list", []))
    for s in up_skills.get("list", []):
        if s not in existing:
            lc_skills.setdefault("list", []).append(s)
            existing.add(s)
            skills_added += 1

    for cat in ("overlayCapable", "discoveryCapable"):
        existing_cat = set(lc_skills.get(cat, []))
        for s in up_skills.get(cat, []):
            if s not in existing_cat:
                lc_skills.setdefault(cat, []).append(s)
                existing_cat.add(s)

    # Total is always derived from the list length — keep it accurate
    lc_skills["total"] = len(lc_skills.get("list", []))

    # ---- Agents: byCategory dict
    up_agents = up_inv.get("agents", {})
    lc_agents = lc_inv.setdefault("agents", {"total": 0, "byCategory": {}})

    for cat, agents in up_agents.get("byCategory", {}).items():
        lc_cat_list = lc_agents.setdefault("byCategory", {}).setdefault(cat, [])
        existing_in_cat = set(lc_cat_list)
        for a in agents:
            if a not in existing_in_cat:
                lc_cat_list.append(a)
                existing_in_cat.add(a)
                agents_added += 1

    lc_agents["total"] = sum(len(v) for v in lc_agents.get("byCategory", {}).values())

    if skills_added or agents_added:
        local["lastUpdated"] = datetime.date.today().isoformat()
        with open(local_path, "w", encoding="utf-8") as f:
            _json.dump(local, f, indent=2)
            f.write("\n")

    return {"skills_added": skills_added, "agents_added": agents_added}


def merge_reference_index(upstream_path: str, local_path: str) -> int:
    """Merge upstream reference-index entries into local. Additive only.
    Preserves user-added custom references; never removes any local entries.

    Returns total count of entries added across all categories.
    """
    import json as _json

    if not os.path.exists(upstream_path):
        return 0

    with open(upstream_path, "r", encoding="utf-8") as f:
        upstream = _json.load(f)

    if not os.path.exists(local_path):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(upstream_path, local_path)
        total = 0
        for category in upstream.get("references", {}).values():
            if isinstance(category, dict):
                total += len(category)
        return total

    with open(local_path, "r", encoding="utf-8") as f:
        local = _json.load(f)

    added = 0
    up_refs = upstream.get("references", {})
    lc_refs = local.setdefault("references", {})

    for category, entries in up_refs.items():
        if not isinstance(entries, dict):
            continue
        lc_cat = lc_refs.setdefault(category, {})
        for key, path in entries.items():
            if key not in lc_cat:
                lc_cat[key] = path
                added += 1

    if added > 0:
        local["lastUpdated"] = datetime.date.today().isoformat()
        with open(local_path, "w", encoding="utf-8") as f:
            _json.dump(local, f, indent=2)
            f.write("\n")

    return added


def merge_entities(upstream_path: str, local_path: str) -> int:
    """Merge upstream entities.json categories into local. Additive only.
    Preserves user-added entities; never removes any local entries.

    Dedupes by `canonical` (for objects with that field) or by `term` (for
    glossary entries). Returns total count of entries added across categories.
    """
    import json as _json

    if not os.path.exists(upstream_path):
        return 0

    with open(upstream_path, "r", encoding="utf-8") as f:
        upstream = _json.load(f)

    if not os.path.exists(local_path):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copy2(upstream_path, local_path)
        total = 0
        for category in upstream.get("entities", {}).values():
            if isinstance(category, list):
                total += len(category)
        return total

    with open(local_path, "r", encoding="utf-8") as f:
        local = _json.load(f)

    added = 0
    up_ents = upstream.get("entities", {})
    lc_ents = local.setdefault("entities", {})

    for category, entries in up_ents.items():
        if not isinstance(entries, list):
            continue
        lc_list = lc_ents.setdefault(category, [])
        existing_keys = set()
        for e in lc_list:
            if isinstance(e, dict):
                key = e.get("canonical") or e.get("term")
                if key:
                    existing_keys.add(key)
        for e in entries:
            if not isinstance(e, dict):
                continue
            key = e.get("canonical") or e.get("term")
            if key and key not in existing_keys:
                lc_list.append(e)
                existing_keys.add(key)
                added += 1

    if added > 0:
        local["lastUpdated"] = datetime.date.today().isoformat()
        with open(local_path, "w", encoding="utf-8") as f:
            _json.dump(local, f, indent=2)
            f.write("\n")

    return added


def merge_settings_json(upstream_path: str, local_path: str) -> int:
    """Merge upstream settings.json hooks and permission allowlist into local.
    Additive only — never removes user entries. Returns count of new entries added."""
    import json as _json

    with open(upstream_path, "r", encoding="utf-8") as f:
        upstream = _json.load(f)
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            local = _json.load(f)
    else:
        local = {}

    added = 0

    # --- hooks (additive, keyed by command string) ---
    if "hooks" in upstream:
        if "hooks" not in local:
            local["hooks"] = {}
        for event, matchers in upstream.get("hooks", {}).items():
            if event not in local["hooks"]:
                local["hooks"][event] = matchers
                added += len(matchers)
                continue

            local_commands = set()
            for matcher_group in local["hooks"][event]:
                for hook in matcher_group.get("hooks", []):
                    local_commands.add(hook.get("command", ""))

            for matcher_group in matchers:
                for hook in matcher_group.get("hooks", []):
                    cmd = hook.get("command", "")
                    if cmd and cmd not in local_commands:
                        local["hooks"][event].append(matcher_group)
                        added += 1
                        break  # one add per matcher group

    # --- permissions.allow (additive, deduped by exact rule string) ---
    upstream_allow = upstream.get("permissions", {}).get("allow", [])
    if upstream_allow:
        local.setdefault("permissions", {}).setdefault("allow", [])
        local_allow = local["permissions"]["allow"]
        existing = set(local_allow)
        for rule in upstream_allow:
            if rule not in existing:
                local_allow.append(rule)
                existing.add(rule)
                added += 1

    if added > 0:
        with open(local_path, "w", encoding="utf-8") as f:
            _json.dump(local, f, indent=2)
            f.write("\n")

    return added


def ensure_convention_infrastructure(project_root: str, upstream_root: str) -> list:
    """Create convention directories and files that hooks/scripts depend on.
    Returns list of what was created."""
    created = []

    # Directories that must exist
    convention_dirs = [
        "docs/_inbox/sessions",
        "docs/_collections",
        ".claude/hook_state",
        ".private",
    ]
    for d in convention_dirs:
        full = os.path.join(project_root, d)
        if not os.path.isdir(full):
            os.makedirs(full, exist_ok=True)
            created.append(f"  + {d}/")

    # Private starter templates (copy if missing, never overwrite)
    private_starter_dir = os.path.join(upstream_root, "docs", "_bcos-framework", "templates", "private-starter")
    if os.path.isdir(private_starter_dir):
        for fname in os.listdir(private_starter_dir):
            if not fname.endswith(".md"):
                continue
            src = os.path.join(private_starter_dir, fname)
            dst = os.path.join(project_root, ".private", fname)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                created.append(f"  + .private/{fname}")

    # Gitkeep files
    for d in [".claude/hook_state"]:
        gitkeep = os.path.join(project_root, d, ".gitkeep")
        if not os.path.exists(gitkeep):
            Path(gitkeep).touch()

    return created


# ---------------------------------------------------------------------------
# README check
# ---------------------------------------------------------------------------

def check_readme(project_root: Path, dry_run: bool) -> None:
    """If no README.md exists and BCOS content is present, create a minimal one.

    Three cases:
    - README exists → skip (never touch an existing README, even if empty).
    - README missing + no BCOS content yet → note it for later; too early.
    - README missing + BCOS content present → create a minimal repo README.
    """
    readme_path = project_root / "README.md"
    if readme_path.exists():
        return  # existing repo — never touch it

    # Detect whether meaningful BCOS content has been built up yet.
    # We look for any active context file (not just framework scaffolding).
    has_content = any([
        (project_root / "docs" / "table-of-context.md").is_file(),
        (project_root / "docs" / "current-state.md").is_file(),
        (project_root / "docs" / "document-index.md").is_file(),
    ])

    if not has_content:
        print("  README.md: not found — no content yet, will create once context is established.")
        return

    if dry_run:
        print("  README.md: would create (no README found, BCOS content present)")
        return

    repo_name = project_root.name
    # Produce a human-readable title from the repo/folder name
    title = repo_name.replace("-", " ").replace("_", " ").title()

    readme_content = f"""# {title}

This repository uses [CLEAR Context OS](https://github.com/walm00/business-context-os)
to maintain structured business context for AI-assisted work.

## Navigation

| Location | Contents |
|----------|---------|
| `docs/` | Active context — current business reality |
| `docs/_inbox/` | Raw material waiting to be processed |
| `docs/_planned/` | Ideas and drafts — not yet active |
| `docs/_archive/` | Historical — superseded documents |
| `.private/` | Local-only context — never committed |

## Using with Claude Code

Open Claude Code in this directory and start working. Claude reads the context
automatically and uses it to give you accurate, up-to-date assistance.

To update the framework:
```bash
python .claude/scripts/update.py
```
"""
    readme_path.write_text(readme_content, encoding="utf-8")
    print("  README.md: created (minimal BCOS context README).")



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Update CLEAR Context OS framework files from upstream."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would change; apply nothing")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Apply framework updates without a confirmation prompt")
    parser.add_argument("--upstream", default=None,
                        help=f"Upstream GitHub repo (default: {UPSTREAM_REPO})")
    parser.add_argument("--branch", default=UPSTREAM_BRANCH,
                        help=f"Upstream branch (default: {UPSTREAM_BRANCH})")
    parser.add_argument("--local", default=None, metavar="PATH",
                        help="Use a local directory as upstream instead of downloading from GitHub")
    args = parser.parse_args()

    local_root = Path(__file__).resolve().parent.parent.parent  # repo root

    print()
    print("=" * 62)
    print("  CLEAR Context OS — Update")
    print("=" * 62)
    print(f"  Local:    {local_root}")
    if args.local:
        print(f"  Upstream: {args.local}  (local path)")
    else:
        upstream_repo = args.upstream or UPSTREAM_REPO
        print(f"  Upstream: github.com/{upstream_repo}  (branch: {args.branch})")
    if args.dry_run:
        print("  Mode:     DRY RUN — no changes will be made")
    print()

    # ------------------------------------------------------------------ scan
    def run_scan(upstream_root: str):
        framework_files = collect_framework_files(upstream_root)

        review_set = set(posix(f) for f in REVIEW_FILES)
        merge_set  = set(posix(f) for f in MERGE_FILES)

        new_files      = []   # (rel, upstream_path, local_path)
        modified_files = []
        review_files   = []   # files needing user decision
        merge_files    = []   # files to auto-merge
        unchanged      = 0

        for rel in framework_files:
            upstream_path = os.path.join(upstream_root, rel)
            local_path    = str(local_root / rel)
            status        = classify(upstream_path, local_path)

            if rel in review_set:
                if status != "unchanged":
                    review_files.append((rel, upstream_path, local_path, status))
                else:
                    unchanged += 1
            elif rel in merge_set:
                if status != "unchanged":
                    merge_files.append((rel, upstream_path, local_path, status))
                else:
                    unchanged += 1
            elif status == "new":
                new_files.append((rel, upstream_path, local_path))
            elif status == "modified":
                modified_files.append((rel, upstream_path, local_path))
            else:
                unchanged += 1

        # ------------------------------------------------------------ report
        total = len(new_files) + len(modified_files)
        print(f"  Scan complete:")
        print(f"    {len(new_files):3d}  new framework files")
        print(f"    {len(modified_files):3d}  modified framework files")
        print(f"    {len(review_files):3d}  require your review  (CLAUDE.md)")
        print(f"    {len(merge_files):3d}  auto-merge           (.gitignore)")
        print(f"    {unchanged:3d}  already up to date")
        print()

        if total == 0 and not review_files and not merge_files:
            print("  Already up to date. Nothing to do.")
            print()
            return

        if new_files:
            print("  NEW:")
            for rel, _, _ in new_files:
                print(f"    +  {rel}")
            print()

        if modified_files:
            print("  MODIFIED:")
            for rel, _, _ in modified_files:
                print(f"    ~  {rel}")
            print()

        if args.dry_run:
            print("  Dry run complete. Run without --dry-run to apply.")
            print()
            return

        # ---------------------------------------------------- confirm + apply
        if not args.yes and total > 0:
            resp = input(f"  Apply {total} framework file update(s)? [y/N] ").strip().lower()
            if resp != "y":
                print("  Cancelled.")
                return
            print()

        applied = 0
        for rel, upstream_path, local_path in new_files + modified_files:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            shutil.copy2(upstream_path, local_path)
            applied += 1

        if applied:
            print(f"  Applied {applied} file(s).")

        # --------- self-relaunch if update.py itself was updated
        self_updated = any(
            rel == ".claude/scripts/update.py"
            for rel, _, _ in new_files + modified_files
        )
        if self_updated:
            print()
            print("  Update script itself was updated. Re-launching new version...")
            print()
            import subprocess as _sp
            new_args = [sys.executable, str(local_root / ".claude" / "scripts" / "update.py"), "--yes"]
            if args.local:
                new_args.extend(["--local", args.local])
            result = _sp.run(new_args, cwd=str(local_root))
            sys.exit(result.returncode)
            # subprocess runs the new version — we exit after it finishes

        # ---------------------------------------------------- merge .gitignore
        for rel, upstream_path, local_path, _ in merge_files:
            added = merge_gitignore(upstream_path, local_path)
            if added:
                print(f"  .gitignore: merged {added} new entr{'y' if added == 1 else 'ies'} from upstream.")
            else:
                print(f"  .gitignore: already contains all upstream entries.")

        # ------------------------------------------------ merge settings.json
        upstream_settings = os.path.join(upstream_root, ".claude", "settings.json")
        local_settings = str(local_root / ".claude" / "settings.json")
        if os.path.exists(upstream_settings):
            entries_added = merge_settings_json(upstream_settings, local_settings)
            if entries_added:
                print(f"  settings.json: merged {entries_added} new entries (hooks + permissions) from upstream.")
            else:
                print(f"  settings.json: all upstream entries already registered.")

        # ------------------------------------------------ merge ecosystem state.json
        # Additive merge — preserves user's custom skills/agents and user-state
        # (health, maintenanceBacklog), only adds framework skills/agents not yet
        # registered locally. Without this, framework releases that add new skills
        # would leave existing installs out of sync, failing ecosystem CI checks.
        upstream_state = os.path.join(upstream_root, ".claude", "quality", "ecosystem", "state.json")
        local_state = str(local_root / ".claude" / "quality" / "ecosystem" / "state.json")
        if os.path.exists(upstream_state):
            counts = merge_ecosystem_state(upstream_state, local_state)
            added = counts["skills_added"] + counts["agents_added"]
            if added:
                parts = []
                if counts["skills_added"]:
                    parts.append(f"{counts['skills_added']} skill(s)")
                if counts["agents_added"]:
                    parts.append(f"{counts['agents_added']} agent(s)")
                print(f"  state.json: registered {' + '.join(parts)} from upstream.")
            else:
                print(f"  state.json: all upstream skills/agents already registered.")

        # ------------------------------------------------ merge reference-index.json
        # Same additive pattern. Framework references stay current; user custom
        # references are preserved.
        upstream_ref = os.path.join(upstream_root, ".claude", "registries", "reference-index.json")
        local_ref = str(local_root / ".claude" / "registries" / "reference-index.json")
        if os.path.exists(upstream_ref):
            ref_added = merge_reference_index(upstream_ref, local_ref)
            if ref_added:
                print(f"  reference-index.json: added {ref_added} new entry/entries from upstream.")
            else:
                print(f"  reference-index.json: all upstream entries already present.")

        # ------------------------------------------------ merge entities.json
        # Same additive pattern. Framework-shipped canonical entities stay
        # current; user-added people/projects/terms are preserved.
        upstream_ent = os.path.join(upstream_root, ".claude", "registries", "entities.json")
        local_ent = str(local_root / ".claude" / "registries" / "entities.json")
        if os.path.exists(upstream_ent):
            ent_added = merge_entities(upstream_ent, local_ent)
            if ent_added:
                print(f"  entities.json: added {ent_added} new entry/entries from upstream.")
            else:
                print(f"  entities.json: all upstream entries already present.")

        # ----------------------------------------- convention infrastructure
        infra_created = ensure_convention_infrastructure(str(local_root), upstream_root)
        if infra_created:
            print(f"  Convention infrastructure:")
            for item in infra_created:
                print(item)

        # ------------------------------------------------------ README check
        check_readme(local_root, args.dry_run)

        # ----------------------------------------- regenerate wake-up context
        wakeup_script = str(local_root / ".claude" / "scripts" / "generate_wakeup_context.py")
        toc_exists = (local_root / "docs" / "table-of-context.md").is_file()
        cs_exists = (local_root / "docs" / "current-state.md").is_file()
        if os.path.exists(wakeup_script) and (toc_exists or cs_exists):
            try:
                import subprocess
                subprocess.run([sys.executable, wakeup_script], cwd=str(local_root),
                               capture_output=True, timeout=15)
                print(f"  Wake-up context regenerated.")
            except Exception:
                print(f"  Wake-up context: could not regenerate (non-critical).")

        # ---------------------------------------------------- CLAUDE.md reference
        # CLAUDE.md is NEVER auto-edited. The script saves the upstream version
        # as a reference file. Claude reads both at session start and suggests
        # what critical framework instructions the user's CLAUDE.md is missing.
        for rel, upstream_path, local_path, status in review_files:
            ref_path = str(local_root / ".claude" / "bcos-claude-reference.md")
            os.makedirs(os.path.dirname(ref_path), exist_ok=True)
            shutil.copy2(upstream_path, ref_path)

            print()
            print(f"  CLAUDE.md has upstream changes.")
            print(f"  Your CLAUDE.md was NOT modified (safe).")
            print(f"  Saved latest framework version to: .claude/bcos-claude-reference.md")
            print()
            print(f"  Next session, Claude will compare the two and suggest any")
            print(f"  critical framework instructions your CLAUDE.md may be missing.")

        # -------------------------------------------------------------- done
        print()
        print("  Update complete.")
        print()
        print("  Next: run the document index to refresh metadata:")
        print("    python .claude/scripts/build_document_index.py")
        print()

    # ------------------------------------------------- dispatch: local vs remote
    if args.local:
        upstream_path = os.path.abspath(args.local)
        if not os.path.isdir(upstream_path):
            print(f"  ERROR: --local path does not exist: {upstream_path}")
            sys.exit(1)
        run_scan(upstream_path)
    else:
        upstream_repo = args.upstream or UPSTREAM_REPO
        with tempfile.TemporaryDirectory() as tmp:
            upstream_root = download_upstream(upstream_repo, args.branch, tmp)
            run_scan(upstream_root)


if __name__ == "__main__":
    main()

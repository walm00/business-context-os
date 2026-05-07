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

# Plugin-owned overlay paths — explicitly NOT framework-managed. Listed here
# only as documentation so future maintainers don't accidentally add them to
# FRAMEWORK_DIRS or FRAMEWORK_FILES. update.py does not touch these:
#
#   docs/_wiki/.schema.yml      — per-install live schema, user-owned
#   docs/_wiki/.schema.d/       — plugin schema fragments (one file per plugin)
#                                 written by each plugin's install_here.py
#                                 see docs/_bcos-framework/architecture/
#                                     wiki-zone.md "Schema fragments overlay"
#   docs/_<plugin>/             — plugin-owned data zone (custom-optout)
#
# These survive every BCOS update. The merger that combines base schema +
# fragments lives at .claude/scripts/_wiki_schema_merge.py.

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


def merge_schedule_config(template_path: str, live_path: str, *,
                          interactive: bool = True) -> int:
    """Merge template-only jobs into the live schedule-config.json.

    The framework ships new jobs (lifecycle-sweep, wiki-canonical-drift, etc.)
    in schedule-config.template.json. update.py overwrites the template on
    every sync, but the LIVE config (schedule-config.json) carries user
    customizations and is never touched. Without this helper, new template
    jobs silently never propagate to existing installs.

    Strategy (Option A — manual prompt):
      1. Find jobs in template that don't exist in live config.
      2. List them with their default cadence + _about description.
      3. Prompt user (Y/n) — default Yes.
      4. If yes, copy template entries verbatim into live config. User
         customizations on EXISTING jobs are preserved (we never touch
         shared keys).

    Non-interactive mode (--yes) auto-adds without prompting.

    Returns the number of jobs added.
    """
    import json as _json

    if not (os.path.exists(template_path) and os.path.exists(live_path)):
        return 0

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = _json.load(f)
        with open(live_path, "r", encoding="utf-8") as f:
            live = _json.load(f)
    except (_json.JSONDecodeError, OSError) as exc:
        print(f"  schedule-config.json: skipped (parse error: {exc})")
        return 0

    template_jobs = template.get("jobs") or {}
    live_jobs = live.get("jobs") or {}
    if not isinstance(template_jobs, dict) or not isinstance(live_jobs, dict):
        return 0

    new_job_ids = [jid for jid in template_jobs if jid not in live_jobs]
    if not new_job_ids:
        return 0

    print(f"  schedule-config.json: {len(new_job_ids)} new job(s) available in template:")
    for jid in new_job_ids:
        spec = template_jobs[jid] or {}
        about = (spec.get("_about") or "").strip()
        sched = spec.get("schedule", "?")
        print(f"    + {jid:26}  (default cadence: {sched})")
        if about:
            short = about[:96] + ("…" if len(about) > 96 else "")
            print(f"      {short}")

    if interactive:
        resp = input(f"  Add these {len(new_job_ids)} job(s) to your live schedule? [Y/n] ").strip().lower()
        if resp in ("n", "no"):
            print(f"  schedule-config.json: skipped — run /schedule-tune later to add new jobs.")
            return 0
    else:
        print(f"  schedule-config.json: --yes mode, auto-adding…")

    for jid in new_job_ids:
        live_jobs[jid] = template_jobs[jid]
    live["jobs"] = live_jobs

    # Also merge any new auto_fix.whitelist entries that ship in the template
    # but aren't on the live config — same additive principle.
    template_whitelist = ((template.get("auto_fix") or {}).get("whitelist") or [])
    live_whitelist = ((live.get("auto_fix") or {}).get("whitelist") or [])
    if template_whitelist and live_whitelist is not None:
        new_fixes = [w for w in template_whitelist if w not in live_whitelist]
        if new_fixes:
            print(f"  schedule-config.json: also adding {len(new_fixes)} new auto-fix ID(s) to whitelist: {', '.join(new_fixes)}")
            live.setdefault("auto_fix", {}).setdefault("whitelist", []).extend(new_fixes)

    with open(live_path, "w", encoding="utf-8") as f:
        _json.dump(live, f, indent=2)
        f.write("\n")

    return len(new_job_ids)


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

        # ----------------------------------- merge schedule-config.json
        # The template just got updated above (it's in FRAMEWORK_FILES). Now
        # surface any template-only jobs to the user's live config so the
        # dispatcher actually picks them up. User customizations on existing
        # jobs are preserved — we only append new entries.
        upstream_template = os.path.join(
            upstream_root, ".claude", "quality", "schedule-config.template.json"
        )
        local_schedule = str(local_root / ".claude" / "quality" / "schedule-config.json")
        if os.path.exists(upstream_template) and os.path.exists(local_schedule):
            jobs_added = merge_schedule_config(
                upstream_template, local_schedule, interactive=not args.yes,
            )
            if jobs_added:
                print(f"  schedule-config.json: added {jobs_added} new job(s) from template.")

        # ------------------------------------------------ refresh ecosystem state.json
        # state.json is a derived artifact — regenerated from disk every update.
        # See lesson L-INIT-20260404-009: discovery is the source of truth, state
        # files record what discovery found. The previous additive-merge model was
        # disk-blind and caused systemic drift across deployed repos.
        refresh_script = str(local_root / ".claude" / "scripts" / "refresh_ecosystem_state.py")
        if os.path.exists(refresh_script):
            try:
                import subprocess as _sp
                result = _sp.run(
                    [sys.executable, refresh_script],
                    cwd=str(local_root),
                    capture_output=True, text=True, timeout=30,
                )
                summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
                if result.returncode == 0 and summary:
                    print(f"  {summary}")
                elif result.returncode != 0:
                    print(f"  state.json: refresh exited {result.returncode} (non-fatal)")
            except Exception as e:
                print(f"  state.json: could not refresh ({e}, non-fatal)")

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

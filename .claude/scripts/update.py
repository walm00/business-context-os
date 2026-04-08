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
import urllib.request
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
    "docs/_bcos-framework/templates",
    "examples",
]

# Root-level files that are always overwritten with the upstream version
FRAMEWORK_FILES = [
    "README.md",
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
    """Return all framework file paths relative to root (posix form)."""
    files = []

    for d in FRAMEWORK_DIRS:
        dir_path = os.path.join(root, d)
        if not os.path.isdir(dir_path):
            continue
        for dirpath, _, filenames in os.walk(dir_path):
            for fname in filenames:
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


def merge_settings_json(upstream_path: str, local_path: str) -> int:
    """Merge upstream settings.json hooks into local. Additive only — never removes user hooks.
    Returns count of new hook entries added."""
    import json as _json

    with open(upstream_path, "r", encoding="utf-8") as f:
        upstream = _json.load(f)
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            local = _json.load(f)
    else:
        local = {}

    if "hooks" not in upstream:
        return 0
    if "hooks" not in local:
        local["hooks"] = {}

    added = 0
    for event, matchers in upstream.get("hooks", {}).items():
        if event not in local["hooks"]:
            local["hooks"][event] = matchers
            added += len(matchers)
            continue

        # For each matcher group in upstream, check if local has it
        local_commands = set()
        for matcher_group in local["hooks"][event]:
            for hook in matcher_group.get("hooks", []):
                local_commands.add(hook.get("command", ""))

        for matcher_group in matchers:
            for hook in matcher_group.get("hooks", []):
                cmd = hook.get("command", "")
                if cmd and cmd not in local_commands:
                    # New hook — add the whole matcher group
                    local["hooks"][event].append(matcher_group)
                    added += 1
                    break  # one add per matcher group

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

    # Files that should exist (copy from upstream if missing)
    convention_files = [
        "docs/.session-diary.md",
        "docs/.onboarding-checklist.md",
    ]
    for f in convention_files:
        local_path = os.path.join(project_root, f)
        upstream_path = os.path.join(upstream_root, f)
        if not os.path.exists(local_path) and os.path.exists(upstream_path):
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            shutil.copy2(upstream_path, local_path)
            created.append(f"  + {f}")

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
            hooks_added = merge_settings_json(upstream_settings, local_settings)
            if hooks_added:
                print(f"  settings.json: merged {hooks_added} new hook(s) from upstream.")
            else:
                print(f"  settings.json: all upstream hooks already registered.")

        # ----------------------------------------- convention infrastructure
        infra_created = ensure_convention_infrastructure(str(local_root), upstream_root)
        if infra_created:
            print(f"  Convention infrastructure:")
            for item in infra_created:
                print(item)

        # --------------------------------- migrate old framework doc locations
        # v1.2.0 moved docs/architecture etc. to docs/_bcos-framework/
        OLD_TO_NEW = [
            ("docs/architecture", "docs/_bcos-framework/architecture"),
            ("docs/guides", "docs/_bcos-framework/guides"),
            ("docs/methodology", "docs/_bcos-framework/methodology"),
            ("docs/templates", "docs/_bcos-framework/templates"),
        ]
        migrated = 0
        for old_dir, new_dir in OLD_TO_NEW:
            old_path = os.path.join(str(local_root), old_dir)
            new_path = os.path.join(str(local_root), new_dir)
            if os.path.isdir(old_path) and os.path.isdir(new_path):
                # New location already has files from this update — safe to remove old
                try:
                    shutil.rmtree(old_path)
                    migrated += 1
                except OSError:
                    pass
        if migrated:
            print(f"  Migrated {migrated} old framework folder(s) to docs/_bcos-framework/")

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

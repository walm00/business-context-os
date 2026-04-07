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
    "docs/architecture",
    "docs/guides",
    "docs/methodology",
    "docs/templates",
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
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
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


def merge_claude_md(upstream_path: str, local_path: str) -> dict:
    """Smart-merge CLAUDE.md: keep user's project-specific sections, update framework sections.

    Strategy: The upstream CLAUDE.md ends with a Version/Last Updated footer.
    Everything after that footer in the local file is the user's project-specific content.
    We take the upstream framework content and append the user's custom tail.

    Returns dict with keys: 'action' (merged|saved|kept), 'details' (str).
    """
    with open(local_path, "r", encoding="utf-8", errors="replace") as f:
        local_content = f.read()
    with open(upstream_path, "r", encoding="utf-8", errors="replace") as f:
        upstream_content = f.read()

    # Find the framework footer in both files
    # Pattern: **Version**: X.Y.Z followed by **Last Updated**: YYYY-MM-DD
    import re
    footer_re = re.compile(
        r'(\*\*Version\*\*:\s*\d+\.\d+\.\d+\s*\n\*\*Last Updated\*\*:\s*\d{4}-\d{2}-\d{2})',
        re.MULTILINE
    )

    local_match = footer_re.search(local_content)
    upstream_match = footer_re.search(upstream_content)

    if not upstream_match:
        # Can't find framework footer in upstream — save alongside for manual merge
        aside = local_path + ".upstream"
        with open(aside, "w", encoding="utf-8") as f:
            f.write(upstream_content)
        return {"action": "saved", "details": "Could not identify framework boundary. Saved as CLAUDE.md.upstream for manual merge."}

    # Get the upstream framework content (everything up to and including footer)
    upstream_framework = upstream_content[:upstream_match.end()]

    # Get the user's custom content (everything after the footer in local file)
    user_custom = ""
    if local_match:
        user_custom = local_content[local_match.end():]
    else:
        # No footer found in local — check if there's content after the last ---
        # This handles files that were customized before the footer convention existed
        last_hr = local_content.rfind("\n---\n")
        if last_hr > len(local_content) * 0.7:  # Only if it's near the end
            user_custom = local_content[last_hr:]

    if not user_custom.strip():
        # No user customizations — just use upstream
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(upstream_content)
        return {"action": "merged", "details": "No project-specific sections found. Applied upstream version."}

    # Merge: upstream framework + user custom tail
    merged = upstream_framework + user_custom

    # Ensure it ends with a newline
    if not merged.endswith("\n"):
        merged += "\n"

    with open(local_path, "w", encoding="utf-8") as f:
        f.write(merged)

    return {"action": "merged", "details": "Updated framework sections, preserved your project-specific content."}


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

        # ---------------------------------------------------- merge .gitignore
        for rel, upstream_path, local_path, _ in merge_files:
            added = merge_gitignore(upstream_path, local_path)
            if added:
                print(f"  .gitignore: merged {added} new entr{'y' if added == 1 else 'ies'} from upstream.")
            else:
                print(f"  .gitignore: already contains all upstream entries.")

        # ---------------------------------------------------- review CLAUDE.md
        for rel, upstream_path, local_path, status in review_files:
            print()
            print("  " + "-" * 58)
            print(f"  REVIEW REQUIRED: {rel}")
            print("  " + "-" * 58)

            if args.yes:
                # Non-interactive: auto-merge (keep user sections, update framework)
                result = merge_claude_md(upstream_path, local_path)
                print(f"  CLAUDE.md: {result['details']}")
            else:
                print("  This file may contain your own customizations.")
                print("  Upstream has changes. What would you like to do?")
                print()
                print_diff(upstream_path, local_path, rel)
                print()
                print("  Options:")
                print("    [m]  Smart merge: update framework sections, keep your")
                print("         project-specific content (recommended)")
                print("    [k]  Keep your local version entirely (skip)")
                print("    [u]  Use upstream version (overwrites your local copy)")
                print("    [s]  Save upstream as CLAUDE.md.upstream for manual review")
                print()
                resp = input("  Choice [m/k/u/s] (default: m): ").strip().lower() or "m"

                if resp == "m":
                    result = merge_claude_md(upstream_path, local_path)
                    print(f"  CLAUDE.md: {result['details']}")
                elif resp == "u":
                    shutil.copy2(upstream_path, local_path)
                    print(f"  Applied upstream {rel}.")
                elif resp == "s":
                    aside = local_path + ".upstream"
                    shutil.copy2(upstream_path, aside)
                    print(f"  Saved to {rel}.upstream -- merge manually when ready.")
                else:
                    print(f"  Kept your local {rel}.")

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

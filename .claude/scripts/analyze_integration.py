#!/usr/bin/env python3
"""
analyze_integration.py - Detect ecosystem integration gaps after building new components.

Scans existing skills, agents, hooks, scripts, install.sh, settings.json, and .gitignore
to find references that may need updating when new files are added or existing files change.

This is the mechanical part — it finds what MIGHT need updating. AI does the reasoning
about what ACTUALLY needs changing.

Usage:
    python .claude/scripts/analyze_integration.py --staged          # Check git staged files
    python .claude/scripts/analyze_integration.py --uncommitted     # Check all uncommitted changes
    python .claude/scripts/analyze_integration.py --files f1 f2 f3  # Check specific files
    python .claude/scripts/analyze_integration.py --json            # Output as JSON
"""

import os
import re
import sys
import json
import subprocess
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Files that SHOULD reference new components (ecosystem wiring)
ECOSYSTEM_FILES = [
    "install.sh",
    ".claude/settings.json",
    ".gitignore",
    ".claude/quality/ecosystem/state.json",
    ".claude/ECOSYSTEM-MAP.md",
]

# Directories containing files that reference paths/patterns
REFERENCE_SCAN_DIRS = [
    ".claude/skills",
    ".claude/agents",
    ".claude/hooks",
    ".claude/scripts",
]

# File extensions to scan for references
SCAN_EXTENSIONS = {".md", ".py", ".sh", ".json"}

# Patterns that indicate a file type
FILE_TYPE_PATTERNS = {
    "skill":    re.compile(r"\.claude/skills/.+/SKILL\.md$"),
    "agent":    re.compile(r"\.claude/agents/.+/AGENT\.md$"),
    "hook":     re.compile(r"\.claude/hooks/.+\.(py|sh)$"),
    "script":   re.compile(r"\.claude/scripts/.+\.py$"),
    "registry": re.compile(r"\.claude/registries/.+\.json$"),
    "doc":      re.compile(r"^docs/(?!_inbox|_archive|_planned|methodology|guides|templates|architecture).+\.md$"),
    "config":   re.compile(r"\.claude/settings.*\.json$"),
}


# ---------------------------------------------------------------------------
# Get changed files
# ---------------------------------------------------------------------------

def get_staged_files(project_root: str) -> list[str]:
    """Get git staged files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=10, cwd=project_root
        )
        return [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]
    except Exception:
        return []


def get_uncommitted_files(project_root: str) -> list[str]:
    """Get all uncommitted changes (staged + unstaged + untracked)."""
    files = set()
    try:
        # Staged + unstaged
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=10, cwd=project_root
        )
        files.update(f.strip() for f in result.stdout.strip().splitlines() if f.strip())

        # Untracked
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=10, cwd=project_root
        )
        files.update(f.strip() for f in result.stdout.strip().splitlines() if f.strip())
    except Exception:
        pass
    return sorted(files)


def classify_file(rel_path: str) -> str:
    """Classify a file by type."""
    normalized = rel_path.replace("\\", "/")
    for file_type, pattern in FILE_TYPE_PATTERNS.items():
        if pattern.search(normalized):
            return file_type
    return "other"


# ---------------------------------------------------------------------------
# Scan for references
# ---------------------------------------------------------------------------

def scan_file_for_references(filepath: str, changed_files: list[str]) -> list[dict]:
    """Scan a file for references to changed file paths, directories, or patterns."""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    hits = []
    for changed in changed_files:
        normalized = changed.replace("\\", "/")

        # Check for exact path reference
        if normalized in content:
            hits.append({
                "scanner_file": filepath,
                "references": normalized,
                "match_type": "exact_path",
            })
            continue

        # Check for filename reference
        filename = os.path.basename(normalized)
        if filename in content and filename not in (".gitkeep", ".gitignore"):
            hits.append({
                "scanner_file": filepath,
                "references": normalized,
                "match_type": "filename",
            })
            continue

        # Check for parent directory reference
        parent = os.path.dirname(normalized).replace("\\", "/")
        if parent and parent in content and len(parent) > 5:
            hits.append({
                "scanner_file": filepath,
                "references": normalized,
                "match_type": "directory",
            })

    return hits


def check_install_coverage(project_root: str, changed_files: list[str]) -> list[dict]:
    """Check if install.sh covers new files that need installing."""
    install_path = os.path.join(project_root, "install.sh")
    if not os.path.isfile(install_path):
        return []

    try:
        content = Path(install_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    gaps = []
    for changed in changed_files:
        normalized = changed.replace("\\", "/")
        file_type = classify_file(normalized)

        # Only check framework files that should be installed
        if file_type in ("skill", "agent", "hook", "script", "registry"):
            filename = os.path.basename(normalized)
            parent_dir = os.path.dirname(normalized).replace("\\", "/")

            # Check if install.sh mentions this file or its directory pattern
            if filename not in content and parent_dir not in content:
                # Check if a glob/loop pattern covers it
                covered = False
                if file_type == "skill" and ".claude/skills/" in content:
                    covered = True
                elif file_type == "agent" and ".claude/agents/" in content:
                    covered = True
                elif file_type == "hook" and ".claude/hooks/" in content:
                    covered = True
                elif file_type == "script" and ".claude/scripts/" in content:
                    covered = True

                if not covered:
                    gaps.append({
                        "file": normalized,
                        "type": file_type,
                        "issue": "Not covered by install.sh",
                    })

    return gaps


def check_settings_coverage(project_root: str, changed_files: list[str]) -> list[dict]:
    """Check if new hooks are registered in settings.json."""
    settings_path = os.path.join(project_root, ".claude", "settings.json")
    if not os.path.isfile(settings_path):
        return []

    try:
        content = Path(settings_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    gaps = []
    for changed in changed_files:
        normalized = changed.replace("\\", "/")
        if classify_file(normalized) == "hook":
            filename = os.path.basename(normalized)
            if filename not in content:
                gaps.append({
                    "file": normalized,
                    "issue": f"Hook {filename} not registered in settings.json",
                })

    return gaps


def check_state_coverage(project_root: str, changed_files: list[str]) -> list[dict]:
    """Check if new skills/agents are in state.json."""
    state_path = os.path.join(project_root, ".claude", "quality", "ecosystem", "state.json")
    if not os.path.isfile(state_path):
        return []

    try:
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
        skill_list = state.get("inventory", {}).get("skills", {}).get("list", [])
    except Exception:
        return []

    gaps = []
    for changed in changed_files:
        normalized = changed.replace("\\", "/")
        if classify_file(normalized) == "skill":
            # Extract skill name from path
            parts = normalized.replace("\\", "/").split("/")
            try:
                skills_idx = parts.index("skills")
                skill_name = parts[skills_idx + 1]
                if skill_name not in skill_list:
                    gaps.append({
                        "file": normalized,
                        "issue": f"Skill '{skill_name}' not in state.json inventory",
                    })
            except (ValueError, IndexError):
                pass

    return gaps


def check_gitignore_coverage(project_root: str, changed_files: list[str]) -> list[dict]:
    """Check if new state/generated directories need gitignoring."""
    gitignore_path = os.path.join(project_root, ".gitignore")
    if not os.path.isfile(gitignore_path):
        return []

    try:
        content = Path(gitignore_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    # Directories that typically need gitignoring
    state_patterns = ["hook_state", "sessions/", ".wake-up-context"]

    gaps = []
    for changed in changed_files:
        normalized = changed.replace("\\", "/")
        for pattern in state_patterns:
            if pattern in normalized and pattern not in content:
                gaps.append({
                    "file": normalized,
                    "issue": f"Pattern '{pattern}' may need gitignoring",
                })

    return gaps


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze integration gaps for new/changed files."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--staged", action="store_true",
                       help="Analyze git staged files")
    group.add_argument("--uncommitted", action="store_true",
                       help="Analyze all uncommitted changes")
    group.add_argument("--files", nargs="+", metavar="FILE",
                       help="Analyze specific files")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--ci", action="store_true",
                        help="CI mode: scan all ecosystem files, exit 1 if gaps found")
    args = parser.parse_args()

    project_root = str(Path(__file__).resolve().parent.parent.parent)

    # CI mode: scan all skills, hooks, scripts as "changed" to check full coverage
    if args.ci:
        changed = []
        for scan_dir in [".claude/skills", ".claude/hooks", ".claude/scripts", ".claude/agents"]:
            full_dir = os.path.join(project_root, scan_dir)
            if not os.path.isdir(full_dir):
                continue
            for dirpath, _, filenames in os.walk(full_dir):
                for fname in filenames:
                    full_path = os.path.join(dirpath, fname)
                    rel = os.path.relpath(full_path, project_root).replace("\\", "/")
                    changed.append(rel)
    elif args.staged:
        changed = get_staged_files(project_root)
    elif args.uncommitted:
        changed = get_uncommitted_files(project_root)
    elif args.files:
        changed = [f.replace("\\", "/") for f in args.files]
    else:
        print("No changed files to analyze.")
        sys.exit(0)

    if not changed:
        print("No changed files to analyze.")
        sys.exit(0)

    # Classify changes
    classified = {}
    for f in changed:
        ft = classify_file(f)
        classified.setdefault(ft, []).append(f)

    # Scan ecosystem files for references
    reference_hits = []
    scanned_files = set()

    for scan_dir in REFERENCE_SCAN_DIRS:
        full_dir = os.path.join(project_root, scan_dir)
        if not os.path.isdir(full_dir):
            continue
        for dirpath, _, filenames in os.walk(full_dir):
            for fname in filenames:
                if Path(fname).suffix not in SCAN_EXTENSIONS:
                    continue
                full_path = os.path.join(dirpath, fname)
                rel = os.path.relpath(full_path, project_root).replace("\\", "/")
                # Don't scan changed files against themselves
                if rel in changed:
                    continue
                if rel in scanned_files:
                    continue
                scanned_files.add(rel)
                hits = scan_file_for_references(full_path, changed)
                reference_hits.extend(hits)

    # Also scan ecosystem wiring files
    for eco_file in ECOSYSTEM_FILES:
        full_path = os.path.join(project_root, eco_file)
        if os.path.isfile(full_path) and eco_file not in scanned_files:
            hits = scan_file_for_references(full_path, changed)
            reference_hits.extend(hits)

    # Run specific coverage checks
    install_gaps = check_install_coverage(project_root, changed)
    settings_gaps = check_settings_coverage(project_root, changed)
    state_gaps = check_state_coverage(project_root, changed)
    gitignore_gaps = check_gitignore_coverage(project_root, changed)

    all_gaps = install_gaps + settings_gaps + state_gaps + gitignore_gaps

    # Output
    if args.json:
        print(json.dumps({
            "changed_files": changed,
            "classified": classified,
            "reference_hits": reference_hits,
            "coverage_gaps": all_gaps,
        }, indent=2))
    else:
        print()
        print("=" * 60)
        print("  Integration Analysis")
        print("=" * 60)

        print(f"\n  Changed files: {len(changed)}")
        for ft, files in sorted(classified.items()):
            for f in files:
                print(f"    [{ft}] {f}")

        if reference_hits:
            print(f"\n  Existing files that reference changed paths ({len(reference_hits)}):")
            for hit in reference_hits:
                print(f"    {hit['scanner_file']}")
                print(f"      -> references {hit['references']} ({hit['match_type']})")
            print("\n  >> Review these files for needed updates.")
        else:
            print(f"\n  No existing files reference the changed paths.")

        if all_gaps:
            print(f"\n  Coverage gaps ({len(all_gaps)}):")
            for gap in all_gaps:
                print(f"    {gap['file']}")
                print(f"      -> {gap['issue']}")
            print("\n  >> Fix these before committing.")
        else:
            print(f"\n  No coverage gaps found.")

        print()

    # CI mode: exit 1 if coverage gaps found
    if args.ci and all_gaps:
        sys.exit(1)


if __name__ == "__main__":
    main()

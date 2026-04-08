#!/usr/bin/env python3
"""
post_edit_frontmatter_check.py - Claude Code PostToolUse hook for Edit/Write tools.

Fires after Claude edits or writes a .md file in docs/ (excluding _inbox/, _archive/,
methodology/, guides/, templates/). Validates that YAML frontmatter is present and
contains the required fields. Warns Claude via stderr if compliance issues are found.

Hook event:  PostToolUse
Matcher:     Edit, Write
Exit codes:
  0  = all clear, no issues found
  0  = issues found but reported (non-blocking — warns, doesn't block)

Note: This hook WARNS, it doesn't block. Blocking edits would be too disruptive.
The warning appears in Claude's context so it self-corrects.
"""

from __future__ import annotations

import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ["name", "type", "cluster", "version", "status", "created", "last-updated"]
VALID_STATUSES = {"draft", "active", "under-review", "archived"}
VALID_TYPES = {"context", "process", "policy", "reference", "playbook"}

# Skip these paths — not user content
SKIP_PATHS = [
    "docs/methodology/",
    "docs/guides/",
    "docs/templates/",
    "docs/_inbox/",
    "docs/_archive/",
    "docs/_collections/",
    "docs/document-index.md",
]

# ---------------------------------------------------------------------------
# Read hook input
# ---------------------------------------------------------------------------

def read_input() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}

# ---------------------------------------------------------------------------
# Check if file needs validation
# ---------------------------------------------------------------------------

def should_validate(file_path: str) -> bool:
    """Only validate .md files in docs/ that are user content (not framework, inbox, or archive)."""
    if not file_path:
        return False

    # Normalize path
    path = file_path.replace("\\", "/")

    # Must be in docs/ and be a .md file
    if not path.endswith(".md"):
        return False

    # Must be somewhere under docs/
    if "/docs/" not in path and not path.startswith("docs/"):
        return False

    # Skip framework and special directories
    for skip in SKIP_PATHS:
        if skip in path:
            return False

    return True

# ---------------------------------------------------------------------------
# Extract and validate frontmatter
# ---------------------------------------------------------------------------

YAML_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
YAML_FIELD_RE = re.compile(r'^([a-zA-Z][a-zA-Z0-9_-]*):\s*(.+)$', re.MULTILINE)


def extract_frontmatter(file_path: str) -> dict | None:
    """Read file and extract YAML frontmatter."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return None

    match = YAML_BLOCK_RE.match(content)
    if not match:
        return None

    yaml_block = match.group(1)
    data = {}
    for field_match in YAML_FIELD_RE.finditer(yaml_block):
        key = field_match.group(1).strip()
        value = field_match.group(2).strip().strip('"').strip("'")
        data[key] = value

    return data if data else None


def validate_frontmatter(file_path: str) -> list[str]:
    """Validate frontmatter. Returns list of issues (empty = all good)."""
    issues = []

    meta = extract_frontmatter(file_path)

    if meta is None:
        issues.append(f"MISSING FRONTMATTER: {file_path} has no YAML frontmatter. Active docs require it.")
        return issues

    # Check required fields
    missing = [f for f in REQUIRED_FIELDS if f not in meta]
    if missing:
        issues.append(f"MISSING FIELDS in {file_path}: {', '.join(missing)}")

    # Validate status
    status = meta.get("status", "")
    if status and status not in VALID_STATUSES:
        issues.append(f"INVALID STATUS in {file_path}: '{status}' — must be one of: {', '.join(sorted(VALID_STATUSES))}")

    # Validate type
    doc_type = meta.get("type", "")
    if doc_type and doc_type not in VALID_TYPES:
        issues.append(f"INVALID TYPE in {file_path}: '{doc_type}' — must be one of: {', '.join(sorted(VALID_TYPES))}")

    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    hook_input = read_input()

    # Get the file path from the tool input
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not should_validate(file_path):
        sys.exit(0)  # Not a docs file, nothing to check

    # Validate
    issues = validate_frontmatter(file_path)

    if issues:
        # Write warnings to stderr (Claude sees this)
        warning = "\n".join([
            "⚠️  FRONTMATTER CHECK — issues found after editing:",
            *[f"  • {issue}" for issue in issues],
            "",
            "Fix these before committing. See docs/methodology/document-standards.md for requirements.",
        ])
        print(warning, file=sys.stderr)

    sys.exit(0)  # Always exit 0 — warn, don't block


if __name__ == "__main__":
    main()

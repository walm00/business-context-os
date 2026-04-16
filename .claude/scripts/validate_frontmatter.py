#!/usr/bin/env python3
"""
CI check: validate YAML frontmatter on all managed markdown files.

Checks:
  - docs/*.md (excluding _inbox/, _planned/, _archive/, methodology/, guides/, templates/)
  - .claude/skills/*/SKILL.md
  - .claude/agents/*/AGENT.md

For docs: requires name, type, cluster, version, status, created, last-updated.
For skills/agents: requires name, description (lighter check — different format).

Exit 0 = all pass, Exit 1 = failures found.
"""

import glob
import os
import re
import sys

REQUIRED_DOC_FIELDS = ["name", "type", "cluster", "version", "status", "created", "last-updated"]
VALID_STATUSES = {"draft", "active", "under-review", "archived"}
VALID_TYPES = {"context", "process", "policy", "reference", "playbook"}

SKIP_DIRS = ["docs/_inbox", "docs/_planned", "docs/_archive", "docs/_collections",
             "docs/_bcos-framework", "docs/examples"]

YAML_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
YAML_FIELD_RE = re.compile(r'^([a-zA-Z][a-zA-Z0-9_-]*):\s*(.+)$', re.MULTILINE)


def extract_frontmatter(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return None

    match = YAML_BLOCK_RE.match(content)
    if not match:
        return None

    data = {}
    for m in YAML_FIELD_RE.finditer(match.group(1)):
        data[m.group(1).strip()] = m.group(2).strip().strip('"').strip("'")
    return data if data else None


def should_check_doc(path):
    norm = path.replace("\\", "/")
    for skip in SKIP_DIRS:
        if norm.startswith(skip + "/") or ("/" + skip + "/") in norm:
            return False
    # Skip dot-prefixed convention files
    basename = os.path.basename(norm)
    if basename.startswith("."):
        return False
    # Skip auto-generated files (no frontmatter by design)
    if basename == "document-index.md":
        return False
    return True


def validate_doc(path):
    issues = []
    meta = extract_frontmatter(path)
    if meta is None:
        issues.append("missing YAML frontmatter")
        return issues

    missing = [f for f in REQUIRED_DOC_FIELDS if f not in meta]
    if missing:
        issues.append(f"missing fields: {', '.join(missing)}")

    status = meta.get("status", "")
    if status and status not in VALID_STATUSES:
        issues.append(f"invalid status: '{status}'")

    doc_type = meta.get("type", "")
    if doc_type and doc_type not in VALID_TYPES:
        issues.append(f"invalid type: '{doc_type}'")

    return issues


def validate_skill_agent(path):
    issues = []
    meta = extract_frontmatter(path)
    if meta is None:
        issues.append("missing YAML frontmatter")
        return issues

    if "name" not in meta:
        issues.append("missing field: name")
    if "description" not in meta:
        # description can be multiline, check raw content
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            match = YAML_BLOCK_RE.match(content)
            if match and "description:" not in match.group(1):
                issues.append("missing field: description")
        except (IOError, UnicodeDecodeError):
            pass

    return issues


def main():
    errors = 0
    checked = 0

    # Check docs/*.md
    for path in glob.glob("docs/**/*.md", recursive=True):
        if not should_check_doc(path):
            continue
        issues = validate_doc(path)
        checked += 1
        if issues:
            errors += 1
            print(f"FAIL: {path}")
            for issue in issues:
                print(f"      {issue}")
        else:
            print(f"OK:   {path}")

    # Check skills
    for path in glob.glob(".claude/skills/*/SKILL.md"):
        issues = validate_skill_agent(path)
        checked += 1
        if issues:
            errors += 1
            print(f"FAIL: {path}")
            for issue in issues:
                print(f"      {issue}")
        else:
            print(f"OK:   {path}")

    # Check agents
    for path in glob.glob(".claude/agents/*/AGENT.md"):
        issues = validate_skill_agent(path)
        checked += 1
        if issues:
            errors += 1
            print(f"FAIL: {path}")
            for issue in issues:
                print(f"      {issue}")
        else:
            print(f"OK:   {path}")

    print(f"\n{checked} files checked, {errors} failed")
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()

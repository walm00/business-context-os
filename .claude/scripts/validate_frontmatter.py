#!/usr/bin/env python3
"""
CI check: validate YAML frontmatter on all managed markdown files.

Checks:
  - docs/*.md (excluding _inbox/, _planned/, _archive/, methodology/, guides/, templates/)
  - .claude/skills/*/SKILL.md
  - .claude/agents/*/AGENT.md

For docs: requires name, type, cluster, version, status, created, last-updated.
For skills/agents: requires name, description (lighter check — different format).

Wiki pages (type: wiki) get the full hook-level validation: schema-checked
page-type, page-type-specific required fields, reference-format rule,
forbidden-builds-on-target, source-summary shape discriminators, and
schema-version drift. The single source of truth for these rules is the
PostToolUse hook (`.claude/hooks/post_edit_frontmatter_check.py`); this
script imports the same validator to avoid duplication.

Exit 0 = all pass, Exit 1 = failures found.
"""

import glob
import os
import re
import sys

# Pull wiki rules in from the hook (single source of truth)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOOK_DIR = os.path.join(REPO_ROOT, ".claude", "hooks")
if HOOK_DIR not in sys.path:
    sys.path.insert(0, HOOK_DIR)

try:
    import post_edit_frontmatter_check as hook
    HOOK_AVAILABLE = True
except ImportError:
    HOOK_AVAILABLE = False

REQUIRED_DOC_FIELDS = ["name", "type", "cluster", "version", "status", "created", "last-updated"]
VALID_STATUSES = {"draft", "active", "under-review", "archived"}
# Match the hook's VALID_TYPES so any drift between the two surfaces here
VALID_TYPES = {"context", "process", "policy", "reference", "playbook", "wiki"}

SKIP_DIRS = ["docs/_inbox", "docs/_planned", "docs/_archive", "docs/_collections",
             "docs/_bcos-framework", "docs/examples"]

# Wiki internals that don't carry frontmatter
WIKI_SKIP_PATTERNS = [
    "docs/_wiki/raw/",
    "docs/_wiki/queue.md",
    "docs/_wiki/.archive/",
    "docs/_wiki/.config.yml",
    "docs/_wiki/.schema.yml",
    "docs/_wiki/log.md",
    "docs/_wiki/index.md",      # derived artifact
    "docs/_wiki/overview.md",
    "docs/_wiki/README.md",
]

YAML_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
YAML_FIELD_RE = re.compile(r'^([a-zA-Z][a-zA-Z0-9_-]*):\s*(.+)$', re.MULTILINE)

# stale-claims: block — top-level YAML list of entries. Each entry is a
# mapping introduced by `  - ` and continues with `    <key>: <value>` lines.
# We parse it with a tiny dedicated walker so we can validate per-entry
# shape (section + last-confirmed mandatory, see-evidence must resolve)
# without pulling in a real YAML library.
STALE_CLAIMS_BLOCK_RE = re.compile(
    r"^stale-claims:\s*\n(?P<body>(?:[ \t]+.*\n?)+)",
    re.MULTILINE,
)


def _parse_stale_claims_block(block_text):
    """Parse a `stale-claims:` block into a list of dicts.

    Recognises the shape:
        stale-claims:
          - section: "Cost taxonomy"
            last-confirmed: "2025-10-15"
            see-evidence: docs/_collections/.../foo.meta.md
            note: "..."
          - section: "Another"
            last-confirmed: "2025-11-01"
    Returns [] on no entries.
    """
    entries = []
    current = None
    for raw in block_text.splitlines():
        if not raw.strip():
            continue
        if raw.lstrip().startswith("#"):
            continue
        if re.match(r"^\s*-\s+", raw):
            if current is not None:
                entries.append(current)
            current = {}
            after_dash = re.sub(r"^\s*-\s+", "", raw)
            key, _, val = after_dash.partition(":")
            if key:
                current[key.strip()] = val.strip().strip('"').strip("'")
            continue
        if current is not None and re.match(r"^\s+\S", raw):
            key, _, val = raw.strip().partition(":")
            if key:
                current[key.strip()] = val.strip().strip('"').strip("'")
    if current is not None:
        entries.append(current)
    return entries


def _validate_stale_claims(raw_content, doc_path):
    """Validate the stale-claims: list-of-objects block, if present.

    Returns a list of issue strings (empty when valid or absent).
    """
    fm_match = YAML_BLOCK_RE.match(raw_content)
    if not fm_match:
        return []
    fm_text = fm_match.group(1)
    block_match = STALE_CLAIMS_BLOCK_RE.search(fm_text)
    if not block_match:
        return []
    entries = _parse_stale_claims_block(block_match.group("body"))
    issues = []
    for i, entry in enumerate(entries):
        prefix = f"stale-claims[{i}]"
        if "section" not in entry or not entry["section"]:
            issues.append(f"{prefix}: missing required field 'section'")
        if "last-confirmed" not in entry or not entry["last-confirmed"]:
            issues.append(f"{prefix}: missing required field 'last-confirmed'")
        evidence = entry.get("see-evidence", "").strip()
        if evidence:
            # Repo-relative path must resolve.
            evidence_path = os.path.join(REPO_ROOT, evidence.replace("/", os.sep))
            if not os.path.exists(evidence_path):
                issues.append(
                    f"{prefix}: see-evidence path does not resolve: {evidence}"
                )
    return issues


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
    for skip in WIKI_SKIP_PATTERNS:
        if norm.startswith(skip) or ("/" + skip) in norm:
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

    # Optional stale-claims: block — when present, every entry must have
    # section + last-confirmed; see-evidence (if given) must resolve.
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        issues.extend(_validate_stale_claims(raw, path))
    except (IOError, UnicodeDecodeError):
        pass

    # Wiki-specific deeper validation — delegate to the hook's logic
    if doc_type == "wiki" and HOOK_AVAILABLE:
        try:
            hook_issues = hook.validate_frontmatter(path, REPO_ROOT)
            # Filter out duplicate "missing fields" / "missing frontmatter" reports
            for h_issue in hook_issues:
                lower = h_issue.lower()
                if lower.startswith("warning:"):
                    continue
                if "missing fields" in lower or "missing frontmatter" in lower:
                    continue
                if "invalid status" in lower or "invalid type" in lower:
                    continue
                # Strip the file-path prefix the hook adds for terser CI output
                cleaned = h_issue.split(": ", 1)[-1] if ": " in h_issue else h_issue
                issues.append(cleaned)
        except Exception as e:
            issues.append(f"wiki-validation failed: {e}")

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

    # Allow caller to validate a single file (used by smoke tests)
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        targets = None

    paths = []
    if targets:
        paths = [p for p in targets if os.path.isfile(p)]
    else:
        # Check docs/*.md
        paths.extend(glob.glob("docs/**/*.md", recursive=True))

    for path in paths:
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

    if not targets:
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

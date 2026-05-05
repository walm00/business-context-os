#!/usr/bin/env python3
"""
post_edit_frontmatter_check.py - Claude Code PostToolUse hook for Edit/Write tools.

Fires after Claude edits or writes a .md file in docs/. Validates that YAML
frontmatter is present and contains the required fields. Warns Claude via stderr
if compliance issues are found.

Wiki pages (type: wiki) get extra validation against `_wiki/.schema.yml` —
page-type-specific required fields, reference-format rules, and shape
discriminators. Falls back to the framework template
(docs/_bcos-framework/templates/_wiki.schema.yml.tmpl) when no project-level
schema exists yet.

Hook event:  PostToolUse
Matcher:     Edit, Write
Exit codes:
  0  = all clear, no issues found
  0  = issues found but reported (non-blocking — warns, doesn't block)

Note: This hook WARNS, it doesn't block. Blocking edits would be too disruptive.
The warning appears in Claude's context so it self-corrects.

References:
  - Pre-flight decisions D-02, D-03, D-04, D-05, D-11
  - docs/_bcos-framework/architecture/wiki-zone.md
"""

from __future__ import annotations

import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Standard required fields for ALL active docs
REQUIRED_FIELDS = ["name", "type", "cluster", "version", "status", "created", "last-updated"]

# Default valid statuses; wiki pages may override via _wiki/.schema.yml `statuses:`
VALID_STATUSES = {"draft", "active", "under-review", "archived"}

# Active type enum (wiki added per the wiki-zone integration plan)
VALID_TYPES = {"context", "process", "policy", "reference", "playbook", "wiki"}

# Default valid detail-levels for source-summary pages (overridable via schema)
VALID_DETAIL_LEVELS = {"brief", "standard", "deep"}

# Skip these paths — not user content (or wiki internals that don't carry frontmatter)
SKIP_PATHS = [
    "docs/_bcos-framework/",
    "docs/_inbox/",
    "docs/_archive/",
    "docs/_collections/",
    "docs/_planned/",
    "docs/document-index.md",
    "docs/_wiki/raw/",
    "docs/_wiki/queue.md",
    "docs/_wiki/.archive/",
    "docs/_wiki/.config.yml",
    "docs/_wiki/.schema.yml",
    "docs/_wiki/log.md",        # append-only, format-policed elsewhere
    "docs/_wiki/index.md",      # derived artifact (refresh_wiki_index.py)
]

# Wiki-specific fields validated per page-type
WIKI_BASE_REQUIRED_FIELDS = ["page-type", "last-reviewed", "domain"]

# Fields valid only on source-summary pages (mutual exclusion enforced below)
SHAPE_FIELDS_UMBRELLA = {"subpages"}
SHAPE_FIELDS_SUB = {"parent-slug"}
SHAPE_FIELDS_UNIFIED = {"companion-urls", "raw-files"}

# Schema cache (mtime-keyed) — avoids re-parsing on every hook fire
_SCHEMA_CACHE: dict[str, tuple[float, dict]] = {}

# ---------------------------------------------------------------------------
# Read hook input
# ---------------------------------------------------------------------------

def read_input() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}

# ---------------------------------------------------------------------------
# Path normalization + repo-root resolution
# ---------------------------------------------------------------------------

def normalize(path: str) -> str:
    return path.replace("\\", "/")


def find_repo_root(file_path: str) -> str:
    """Walk up from the edited file to find the BCOS repo root (contains .claude/)."""
    if not file_path:
        return os.getcwd()
    abs_path = os.path.abspath(file_path)
    cur = os.path.dirname(abs_path)
    while cur and cur != os.path.dirname(cur):
        if os.path.isdir(os.path.join(cur, ".claude")) and os.path.isdir(os.path.join(cur, "docs")):
            return cur
        cur = os.path.dirname(cur)
    return os.getcwd()

# ---------------------------------------------------------------------------
# Check if file needs validation
# ---------------------------------------------------------------------------

def should_validate(file_path: str) -> bool:
    """Validate .md files in docs/ that are user content (not framework, inbox, or archive)."""
    if not file_path:
        return False

    path = normalize(file_path)

    if not path.endswith(".md"):
        return False

    if "/docs/" not in path and not path.startswith("docs/"):
        return False

    for skip in SKIP_PATHS:
        if skip in path:
            return False

    return True

# ---------------------------------------------------------------------------
# Frontmatter extraction
# ---------------------------------------------------------------------------

YAML_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
# Allow empty value (e.g. "exclusively-owns:") — value may be "" indicating a multi-line list follows
YAML_SCALAR_RE = re.compile(r'^([a-zA-Z][a-zA-Z0-9_-]*):\s*(.*)$')
YAML_LIST_INLINE_RE = re.compile(r'^\[(.*)\]$')


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def _parse_inline_list(value: str) -> list[str] | None:
    """Parse `[a, b, c]` style inline list. Returns None if not such a list."""
    m = YAML_LIST_INLINE_RE.match(value.strip())
    if not m:
        return None
    inner = m.group(1).strip()
    if not inner:
        return []
    return [_strip_quotes(x.strip()) for x in inner.split(',')]


def extract_frontmatter(file_path: str) -> dict | None:
    """Read file and extract YAML frontmatter. Returns dict with scalar + list values."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return None

    match = YAML_BLOCK_RE.match(content)
    if not match:
        return None

    yaml_block = match.group(1)
    data: dict = {}

    # Track multi-line list state
    pending_key: str | None = None
    pending_list: list[str] = []

    for raw_line in yaml_block.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith('#'):
            continue

        # Multi-line list item: leading "  - value"
        if pending_key is not None and re.match(r'^\s+-\s+', line):
            item = re.sub(r'^\s+-\s+', '', line).strip()
            pending_list.append(_strip_quotes(item))
            continue

        # End of multi-line list — flush
        if pending_key is not None:
            data[pending_key] = pending_list
            pending_key = None
            pending_list = []

        # Top-level scalar/list
        m = YAML_SCALAR_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip()
        value = m.group(2).strip()

        # Inline list?
        inline = _parse_inline_list(value)
        if inline is not None:
            data[key] = inline
            continue

        # Bare key with empty value → start of multi-line list (or nested map; we treat as list-or-empty)
        if value == "" or value == "[]":
            data[key] = []
            pending_key = key
            pending_list = []
            continue

        data[key] = _strip_quotes(value)

    # Flush trailing list
    if pending_key is not None:
        data[pending_key] = pending_list

    return data if data else None

# ---------------------------------------------------------------------------
# Wiki schema parser (minimal, regex-based — no PyYAML dependency)
# ---------------------------------------------------------------------------

def _read_text(path: str) -> str | None:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, UnicodeDecodeError):
        return None


def parse_wiki_schema(text: str) -> dict:
    """
    Minimal parser for _wiki.schema.yml.

    Extracts only the fields the hook actually uses:
      - schema-version: int
      - page-types: {name: {required-fields: [...], folder: str, structural-shapes: [...]}}
      - statuses: [...]
      - detail-levels: [...]
      - clusters.allow-cluster-not-in-source: bool
      - lint-checks.forbidden-builds-on-target.config.forbid-builds-on-paths: [...]
    """
    result: dict = {
        "schema-version": None,
        "page-types": {},
        "statuses": list(VALID_STATUSES),
        "detail-levels": list(VALID_DETAIL_LEVELS),
        "allow-cluster-not-in-source": True,
        "forbid-builds-on-paths": ["_planned/", "_inbox/", "_archive/"],
    }

    lines = text.splitlines()

    def indent_of(s: str) -> int:
        return len(s) - len(s.lstrip(" "))

    def stripped(s: str) -> str:
        return s.strip()

    def is_blank_or_comment(s: str) -> bool:
        t = s.lstrip()
        return not t or t.startswith("#")

    section: str | None = None  # "page-types", "clusters", "lint-checks"
    page_type_name: str | None = None
    in_lint_check: str | None = None
    in_lint_config: bool = False

    for raw in lines:
        if is_blank_or_comment(raw):
            continue
        ind = indent_of(raw)
        body = stripped(raw)

        # Top-level
        if ind == 0:
            section = None
            page_type_name = None
            in_lint_check = None
            in_lint_config = False

            if m := re.match(r'^schema-version:\s*(\d+)', body):
                result["schema-version"] = int(m.group(1))
            elif body.startswith("page-types:"):
                section = "page-types"
            elif body.startswith("clusters:"):
                section = "clusters"
            elif body.startswith("lint-checks:"):
                section = "lint-checks"
            elif m := re.match(r'^statuses:\s*\[(.*)\]', body):
                result["statuses"] = [_strip_quotes(x.strip()) for x in m.group(1).split(",") if x.strip()]
            elif m := re.match(r'^detail-levels:\s*\[(.*)\]', body):
                result["detail-levels"] = [_strip_quotes(x.strip()) for x in m.group(1).split(",") if x.strip()]
            continue

        # Inside page-types
        if section == "page-types":
            if ind == 2:
                m = re.match(r'^([a-z][a-z0-9-]*):\s*$', body)
                if m:
                    page_type_name = m.group(1)
                    result["page-types"][page_type_name] = {
                        "required-fields": [],
                        "folder": "pages",
                        "structural-shapes": [],
                    }
                else:
                    page_type_name = None
            elif ind >= 4 and page_type_name:
                pt = result["page-types"].get(page_type_name)
                if pt is None:
                    continue
                if m := re.match(r'^required-fields:\s*\[(.*)\]', body):
                    pt["required-fields"] = [_strip_quotes(x.strip()) for x in m.group(1).split(",") if x.strip()]
                elif m := re.match(r'^folder:\s*(\S+)', body):
                    pt["folder"] = _strip_quotes(m.group(1))
                elif body.startswith("structural-shapes:"):
                    # Could be inline `[a, b]` or a multi-line list — handle inline here
                    rest = body[len("structural-shapes:"):].strip()
                    if rest.startswith("[") and rest.endswith("]"):
                        pt["structural-shapes"] = [_strip_quotes(x.strip()) for x in rest[1:-1].split(",") if x.strip()]
                    else:
                        pt["structural-shapes"] = []  # multi-line items follow; collected below
                elif body.startswith("- "):
                    # multi-line list item — append to last opened list
                    if pt.get("structural-shapes") is not None:
                        pt["structural-shapes"].append(_strip_quotes(body[2:].strip()))
            continue

        # Inside clusters
        if section == "clusters":
            if m := re.match(r'^allow-cluster-not-in-source:\s*(\S+)', body):
                v = m.group(1).strip().lower()
                result["allow-cluster-not-in-source"] = v in ("true", "yes", "on", "1")
            continue

        # Inside lint-checks (we only care about forbidden-builds-on-target's config.forbid-builds-on-paths)
        if section == "lint-checks":
            if ind == 2:
                m = re.match(r'^([a-z][a-z0-9-]*):\s*$', body)
                if m:
                    in_lint_check = m.group(1)
                    in_lint_config = False
                else:
                    in_lint_check = None
            elif ind == 4 and in_lint_check == "forbidden-builds-on-target":
                if body.startswith("config:"):
                    in_lint_config = True
                else:
                    in_lint_config = False
            elif in_lint_check == "forbidden-builds-on-target" and in_lint_config:
                if body.startswith("forbid-builds-on-paths:"):
                    rest = body[len("forbid-builds-on-paths:"):].strip()
                    if rest.startswith("[") and rest.endswith("]"):
                        result["forbid-builds-on-paths"] = [_strip_quotes(x.strip()) for x in rest[1:-1].split(",") if x.strip()]
                    else:
                        result["forbid-builds-on-paths"] = []
                elif body.startswith("- "):
                    result["forbid-builds-on-paths"].append(_strip_quotes(body[2:].strip()))
            continue

    return result


def load_wiki_schema(repo_root: str) -> tuple[dict, str]:
    """
    Load the wiki schema with project-first / framework-fallback semantics (D-02).

    Returns (schema_dict, source_label) where source_label is 'project' / 'framework' / 'none'.
    Caches by file mtime for sub-millisecond repeat reads (P2_005).
    """
    project_path = os.path.join(repo_root, "docs", "_wiki", ".schema.yml")
    framework_path = os.path.join(repo_root, "docs", "_bcos-framework", "templates", "_wiki.schema.yml.tmpl")

    chosen_path: str | None = None
    source = "none"

    if os.path.isfile(project_path):
        chosen_path = project_path
        source = "project"
    elif os.path.isfile(framework_path):
        chosen_path = framework_path
        source = "framework"

    if chosen_path is None:
        # Schema missing entirely — return permissive defaults so the hook no-ops gracefully
        return parse_wiki_schema(""), "none"

    mtime = os.path.getmtime(chosen_path)
    cached = _SCHEMA_CACHE.get(chosen_path)
    if cached and cached[0] == mtime:
        return cached[1], source

    text = _read_text(chosen_path) or ""
    parsed = parse_wiki_schema(text)
    _SCHEMA_CACHE[chosen_path] = (mtime, parsed)
    return parsed, source


# Framework's expected schema-version (bump in lockstep when the schema breaks).
# The hook compares the project's schema-version against this and warns on drift.
FRAMEWORK_EXPECTED_SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Reference-format rule (D-04)
# ---------------------------------------------------------------------------

# Intra-zone fields: bare slugs, no `.md`
INTRA_ZONE_LIST_FIELDS = {"references", "subpages"}
INTRA_ZONE_SCALAR_FIELDS = {"parent-slug"}

# Cross-zone fields: relative paths, MUST include `.md`
CROSS_ZONE_LIST_FIELDS = {"builds-on", "raw-files", "provides", "companion-urls"}


def check_reference_format(meta: dict) -> list[str]:
    """Return a list of issue strings for reference-format violations."""
    issues = []

    for field in INTRA_ZONE_LIST_FIELDS:
        values = meta.get(field)
        if not isinstance(values, list):
            continue
        for v in values:
            if str(v).endswith(".md"):
                issues.append(
                    f"REFERENCE-FORMAT-MISMATCH: '{field}' is intra-zone — use bare slugs, not '{v}'. "
                    f"Strip the .md extension."
                )

    for field in INTRA_ZONE_SCALAR_FIELDS:
        v = meta.get(field)
        if isinstance(v, str) and v.endswith(".md"):
            issues.append(
                f"REFERENCE-FORMAT-MISMATCH: '{field}' is intra-zone — use bare slug, not '{v}'."
            )

    for field in CROSS_ZONE_LIST_FIELDS:
        values = meta.get(field)
        if not isinstance(values, list):
            continue
        for v in values:
            if not str(v).strip():
                continue
            if field == "companion-urls":
                # URLs not paths; skip
                continue
            if not str(v).endswith(".md"):
                issues.append(
                    f"REFERENCE-FORMAT-MISMATCH: '{field}' is cross-zone — use relative paths "
                    f"with .md extension, not bare slug '{v}'."
                )

    return issues

# ---------------------------------------------------------------------------
# Wiki-specific validation
# ---------------------------------------------------------------------------

def _is_wiki_path(path: str) -> bool:
    p = normalize(path)
    return "/docs/_wiki/pages/" in p or "/docs/_wiki/source-summary/" in p \
        or p.startswith("docs/_wiki/pages/") or p.startswith("docs/_wiki/source-summary/")


def _is_source_summary_path(path: str) -> bool:
    p = normalize(path)
    return "/docs/_wiki/source-summary/" in p or p.startswith("docs/_wiki/source-summary/")


def validate_wiki(file_path: str, meta: dict, schema: dict, schema_source: str) -> list[str]:
    """Wiki-specific frontmatter validation. Runs only when type: wiki."""
    issues: list[str] = []

    # Base wiki fields
    missing_base = [f for f in WIKI_BASE_REQUIRED_FIELDS if f not in meta]
    if missing_base:
        issues.append(f"MISSING WIKI FIELDS in {file_path}: {', '.join(missing_base)}")

    # page-type registered?
    page_type = meta.get("page-type", "")
    page_types_registered = schema.get("page-types") or {}
    if page_type and page_type not in page_types_registered:
        registered = ", ".join(sorted(page_types_registered.keys())) or "(none — schema empty)"
        issues.append(
            f"SCHEMA-VIOLATION in {file_path}: page-type '{page_type}' is not registered in "
            f"_wiki/.schema.yml (schema source: {schema_source}). Registered: {registered}. "
            f"Add it via: /wiki schema add page-type {page_type}"
        )

    # page-type-specific required fields
    if page_type and page_type in page_types_registered:
        pt_def = page_types_registered[page_type] or {}
        for req in pt_def.get("required-fields", []) or []:
            if req not in meta or meta.get(req) in (None, "", [], "null"):
                issues.append(
                    f"SCHEMA-VIOLATION in {file_path}: page-type '{page_type}' requires field "
                    f"'{req}' (per .schema.yml). Add it to frontmatter."
                )
        # Folder placement
        folder = pt_def.get("folder", "pages")
        if folder == "pages" and _is_source_summary_path(file_path):
            issues.append(
                f"FOLDER-MISMATCH in {file_path}: page-type '{page_type}' belongs in _wiki/pages/ "
                f"but file is under _wiki/source-summary/."
            )
        if folder == "source-summary" and not _is_source_summary_path(file_path) and _is_wiki_path(file_path):
            issues.append(
                f"FOLDER-MISMATCH in {file_path}: page-type '{page_type}' belongs in _wiki/source-summary/ "
                f"but file is under _wiki/pages/."
            )

    # Status override per schema (rare; usually wiki-statuses == default)
    statuses_allowed = set(schema.get("statuses") or VALID_STATUSES)
    status = meta.get("status", "")
    if status and status not in statuses_allowed:
        issues.append(
            f"INVALID STATUS in {file_path}: '{status}' — must be one of: {', '.join(sorted(statuses_allowed))}"
        )

    # Source-summary: shape discriminators are mutually exclusive
    if page_type == "source-summary":
        present_shapes = []
        if meta.get("subpages"):
            present_shapes.append("umbrella (subpages)")
        if meta.get("parent-slug"):
            present_shapes.append("sub (parent-slug)")
        if meta.get("companion-urls") or meta.get("raw-files"):
            present_shapes.append("unified (companion-urls/raw-files)")
        if len(present_shapes) > 1:
            issues.append(
                f"SHAPE-CONFLICT in {file_path}: source-summary page declares multiple shapes "
                f"({', '.join(present_shapes)}). Pick exactly one."
            )

        # detail-level enum
        dl_allowed = set(schema.get("detail-levels") or VALID_DETAIL_LEVELS)
        dl = meta.get("detail-level", "")
        if dl and dl not in dl_allowed:
            issues.append(
                f"INVALID DETAIL-LEVEL in {file_path}: '{dl}' — must be one of: {', '.join(sorted(dl_allowed))}"
            )

    # builds-on must not point to forbidden zones (D-03 generalized via schema)
    forbidden_roots = schema.get("forbid-builds-on-paths") or []
    builds_on = meta.get("builds-on") or []
    if isinstance(builds_on, list):
        for path in builds_on:
            for root in forbidden_roots:
                # `../_planned/foo.md` or `../../_planned/foo.md` etc.
                if root in str(path):
                    issues.append(
                        f"FORBIDDEN-BUILDS-ON-TARGET in {file_path}: builds-on contains '{path}' "
                        f"under '{root}' — wiki only builds on canonical reality."
                    )
                    break

    # Reference-format rule (D-04)
    issues.extend(check_reference_format(meta))

    # Schema-version drift (P2_004)
    project_schema_version = schema.get("schema-version")
    if project_schema_version is not None and project_schema_version < FRAMEWORK_EXPECTED_SCHEMA_VERSION:
        issues.append(
            f"SCHEMA-VERSION-DRIFT: project _wiki/.schema.yml is at version "
            f"{project_schema_version} but the framework expects {FRAMEWORK_EXPECTED_SCHEMA_VERSION}. "
            f"Run /wiki schema migrate {project_schema_version} {FRAMEWORK_EXPECTED_SCHEMA_VERSION}."
        )

    return issues

# ---------------------------------------------------------------------------
# Main validation entry point
# ---------------------------------------------------------------------------

def validate_frontmatter(file_path: str, repo_root: str) -> list[str]:
    """Validate frontmatter. Returns list of issues (empty = all good)."""
    issues = []

    meta = extract_frontmatter(file_path)

    if meta is None:
        issues.append(f"MISSING FRONTMATTER: {file_path} has no YAML frontmatter. Active docs require it.")
        return issues

    # Standard required fields
    missing = [f for f in REQUIRED_FIELDS if f not in meta]
    if missing:
        issues.append(f"MISSING FIELDS in {file_path}: {', '.join(missing)}")

    # Validate type
    doc_type = meta.get("type", "")
    if doc_type and doc_type not in VALID_TYPES:
        issues.append(f"INVALID TYPE in {file_path}: '{doc_type}' — must be one of: {', '.join(sorted(VALID_TYPES))}")

    # If this is a wiki page, run wiki-specific validation
    if doc_type == "wiki":
        schema, schema_source = load_wiki_schema(repo_root)
        issues.extend(validate_wiki(file_path, meta, schema, schema_source))
    else:
        # Default status check for non-wiki pages
        status = meta.get("status", "")
        if status and status not in VALID_STATUSES:
            issues.append(
                f"INVALID STATUS in {file_path}: '{status}' — must be one of: {', '.join(sorted(VALID_STATUSES))}"
            )

    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    hook_input = read_input()

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not should_validate(file_path):
        sys.exit(0)

    repo_root = find_repo_root(file_path)
    issues = validate_frontmatter(file_path, repo_root)

    if issues:
        warning = "\n".join([
            "⚠️  FRONTMATTER CHECK — issues found after editing:",
            *[f"  • {issue}" for issue in issues],
            "",
            "Fix these before committing. See docs/_bcos-framework/methodology/document-standards.md for general rules; "
            "docs/_bcos-framework/architecture/wiki-zone.md for wiki-specific rules.",
        ])
        print(warning, file=sys.stderr)

    sys.exit(0)  # Always exit 0 — warn, don't block


if __name__ == "__main__":
    main()

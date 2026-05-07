#!/usr/bin/env python3
"""
Wiki schema fragment merger.

BCOS-enabled plugins (initiatives-os, executions-os, future siblings) extend
the wiki vocabulary by writing **schema fragments** at:

    docs/_wiki/.schema.d/<plugin>.yml

Fragments are owned by plugins, never touched by BCOS update.py, and merged
into the base schema (`docs/_wiki/.schema.yml`) at read time. The base schema
remains plugin-agnostic; per-install `_wiki/.schema.yml` is user-owned.

A fragment may extend two registries:
    - cross-references:   plugin-defined frontmatter ref fields
                          (e.g. initiative-refs, task-refs, stakeholder-refs)
    - raw-source-types:   plugin-defined raw subtypes
                          (e.g. meeting, whatsapp, email)

A fragment must NOT redefine base-owned vocabulary (page-types, statuses,
detail-levels, authority-values, lint-checks, auto-fixes). Identical
declarations across fragments are no-ops; conflicting declarations are a
fragment-level error surfaced to the caller.

Both consumers — the frontmatter pre-edit hook
(.claude/hooks/post_edit_frontmatter_check.py) and the wiki schema CLI
(.claude/scripts/wiki_schema.py) — call into the helpers here so the merge
behaviour stays consistent.

Pure regex / pure stdlib. No PyYAML dependency, matching the rest of the
wiki tooling.

See: docs/_bcos-framework/architecture/wiki-zone.md (Schema fragments overlay)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


SCHEMA_D_DIRNAME = ".schema.d"

# Top-level keys a fragment is allowed to declare. Anything else is reserved
# for the base schema and must not appear in fragments.
ALLOWED_FRAGMENT_KEYS = {
    "plugin",
    "plugin-version",
    "cross-references",
    "raw-source-types",
}

# Base-owned registry keys a fragment must never redefine.
FORBIDDEN_FRAGMENT_KEYS = {
    "schema-version",
    "page-types",
    "statuses",
    "detail-levels",
    "provenance-kinds",
    "authority-values",
    "clusters",
    "lint-checks",
    "auto-fixes",
    "thresholds",
    "migrations",
    "last-updated",
}


@dataclass
class FragmentParseResult:
    """One parsed fragment + any shape errors detected while parsing."""
    plugin: str | None = None
    plugin_version: str | None = None
    cross_references: dict[str, dict] = field(default_factory=dict)
    raw_source_types: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    path: str = ""


@dataclass
class MergeResult:
    """Output of merging base + every fragment."""
    cross_references: dict[str, dict] = field(default_factory=dict)
    raw_source_types: list[str] = field(default_factory=list)
    fragments: list[FragmentParseResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def schema_d_dir(repo_root: str) -> str:
    return os.path.join(repo_root, "docs", "_wiki", SCHEMA_D_DIRNAME)


def list_fragment_paths(repo_root: str) -> list[str]:
    """Return sorted list of fragment file paths under .schema.d/.

    Sorting gives deterministic merge order for diagnostics. The merge logic
    itself is order-independent (conflicting declarations are errors, not
    last-writer-wins) — but stable order keeps error messages reproducible.
    """
    d = schema_d_dir(repo_root)
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        # Plugin convention: <plugin-slug>.yml. Skip dotfiles, READMEs, .tmpl,
        # and anything not ending in .yml so READMEs / examples in the dir
        # don't accidentally parse as fragments.
        if name.startswith("."):
            continue
        if not name.endswith(".yml"):
            continue
        path = os.path.join(d, name)
        if os.path.isfile(path):
            out.append(path)
    return out


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# Minimal regex-based fragment parser. Fragment shape is constrained enough
# that we don't need a full YAML parser — only top-level scalars, one nested
# map (cross-references), and one list (raw-source-types).

_TOP_KEY_RE = re.compile(r"^([a-z][a-z0-9-]*):\s*(.*)$")
_INDENT_KEY_RE = re.compile(r"^(\s+)([a-z][a-z0-9_-]*):\s*(.*)$")
_LIST_ITEM_RE = re.compile(r"^\s*-\s+(.+)$")


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def _strip_inline_comment(s: str) -> str:
    # Stop at first '#' that isn't inside quotes. Fragments don't use quoted
    # values with '#' inside, so plain split is sufficient.
    if "#" in s:
        s = s.split("#", 1)[0]
    return s.rstrip()


def parse_fragment(text: str, path: str = "") -> FragmentParseResult:
    """Parse a fragment file's text into structured form.

    Errors are collected into result.errors rather than raised, so a single
    malformed fragment never breaks the whole merge — the caller decides
    whether to surface them as warnings or hard-fail.
    """
    result = FragmentParseResult(path=path)

    # Guard rails first — disallow obvious base-schema content.
    seen_top_keys: set[str] = set()

    # State for parsing nested cross-references map and raw-source-types list.
    section: str | None = None
    current_ref_name: str | None = None

    lines = text.splitlines()

    for raw in lines:
        line = raw.rstrip()

        # Skip blank + comment-only lines
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))

        # Top-level key (column 0, no leading space)
        if indent == 0:
            m = _TOP_KEY_RE.match(line)
            if not m:
                # Stray non-comment top-level line that isn't `key:` form.
                result.errors.append(
                    f"{path}: malformed top-level line: {line!r}"
                )
                continue

            key = m.group(1)
            value = _strip_inline_comment(m.group(2)).strip()

            if key in FORBIDDEN_FRAGMENT_KEYS:
                result.errors.append(
                    f"{path}: fragment cannot declare '{key}' — that registry "
                    f"is owned by the base schema. Allowed keys: {sorted(ALLOWED_FRAGMENT_KEYS)}."
                )
                section = None
                continue
            if key not in ALLOWED_FRAGMENT_KEYS:
                result.errors.append(
                    f"{path}: unknown top-level key '{key}'. "
                    f"Fragments may only declare: {sorted(ALLOWED_FRAGMENT_KEYS)}."
                )
                section = None
                continue

            seen_top_keys.add(key)

            if key == "plugin":
                result.plugin = _strip_quotes(value) if value else None
                section = None
            elif key == "plugin-version":
                result.plugin_version = _strip_quotes(value) if value else None
                section = None
            elif key == "cross-references":
                if value not in ("", "{}"):
                    result.errors.append(
                        f"{path}: 'cross-references:' must be a multi-line nested map, "
                        f"not an inline value."
                    )
                    section = None
                else:
                    section = "cross-references"
                    current_ref_name = None
            elif key == "raw-source-types":
                # Inline list `[a, b]` allowed; otherwise expect multi-line items.
                if value.startswith("[") and value.endswith("]"):
                    inner = value[1:-1].strip()
                    if inner:
                        result.raw_source_types.extend(
                            _strip_quotes(x.strip()) for x in inner.split(",") if x.strip()
                        )
                    section = None
                else:
                    section = "raw-source-types"
            continue

        # Indented content inside an open section.
        if section == "cross-references":
            # 2-space indent: ref-field name (e.g. `  initiative-refs:`)
            # 4+space indent: nested attributes of that ref field
            mk = _INDENT_KEY_RE.match(line)
            if not mk:
                # Could be a bare value line that doesn't fit — treat as malformed.
                result.errors.append(f"{path}: unexpected line in cross-references: {line!r}")
                continue
            ind_text = mk.group(1)
            child_key = mk.group(2)
            child_val = _strip_inline_comment(mk.group(3)).strip()

            if len(ind_text) == 2:
                # New ref-field entry
                current_ref_name = child_key
                if current_ref_name in result.cross_references:
                    result.errors.append(
                        f"{path}: duplicate cross-reference field '{current_ref_name}' "
                        f"declared twice in the same fragment."
                    )
                else:
                    result.cross_references[current_ref_name] = {}
                # `cross-references:\n  foo:\n` — child_val should be empty;
                # if non-empty, treat as inline shorthand (rare).
                if child_val and child_val not in ("", "{}"):
                    result.errors.append(
                        f"{path}: ref field '{current_ref_name}' must use a nested map; "
                        f"inline value not supported."
                    )
            elif len(ind_text) >= 4 and current_ref_name:
                bucket = result.cross_references.get(current_ref_name)
                if bucket is None:
                    continue
                bucket[child_key] = _strip_quotes(child_val)
            continue

        if section == "raw-source-types":
            mi = _LIST_ITEM_RE.match(line)
            if mi:
                result.raw_source_types.append(_strip_quotes(mi.group(1).strip()))
            else:
                # End of list (would be next top-level key — handled above by
                # indent==0 branch). Anything else is a stray line.
                if indent > 0:
                    result.errors.append(
                        f"{path}: unexpected line in raw-source-types: {line!r}"
                    )
            continue

    # Required fragment metadata
    if "plugin" not in seen_top_keys or not result.plugin:
        result.errors.append(
            f"{path}: fragment must declare a non-empty 'plugin:' field "
            f"(used for diagnostics + conflict reporting)."
        )

    return result


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------

def merge_fragments(
    base_cross_references: dict[str, dict] | None,
    base_raw_source_types: list[str] | None,
    fragments: list[FragmentParseResult],
) -> MergeResult:
    """Merge a list of parsed fragments into base registries.

    - cross-references: keys must be unique across all fragments. If two
      fragments declare the same ref-field name with **identical** value-maps,
      that's a no-op (treated as redundant-but-allowed). Differing value-maps
      are a hard conflict.
    - raw-source-types: deduplicated; identical entries are no-ops; case-
      sensitive equality.

    Errors from individual fragment parsing are propagated into the merged
    result so the caller sees one consolidated error list.
    """
    out = MergeResult()

    # Seed with base values (immutable copies).
    if base_cross_references:
        out.cross_references.update({k: dict(v) for k, v in base_cross_references.items()})
    if base_raw_source_types:
        out.raw_source_types.extend(base_raw_source_types)

    seen_raw_types = set(out.raw_source_types)

    for frag in fragments:
        out.fragments.append(frag)
        # Per-fragment parse errors flow through.
        out.errors.extend(frag.errors)

        for ref_name, ref_attrs in frag.cross_references.items():
            existing = out.cross_references.get(ref_name)
            if existing is None:
                out.cross_references[ref_name] = dict(ref_attrs)
                continue
            # Compare normalized attribute maps.
            if existing == ref_attrs:
                # Identical declaration — no-op, allowed.
                continue
            owner = frag.plugin or os.path.basename(frag.path) or "<unknown>"
            out.errors.append(
                f"cross-reference conflict on '{ref_name}': "
                f"already declared with attributes {existing!r}; "
                f"fragment '{owner}' ({frag.path}) declares {ref_attrs!r}. "
                f"Identical redeclaration is allowed; differing declarations are not."
            )

        for raw_type in frag.raw_source_types:
            if raw_type in seen_raw_types:
                continue
            seen_raw_types.add(raw_type)
            out.raw_source_types.append(raw_type)

    return out


# ---------------------------------------------------------------------------
# Top-level convenience
# ---------------------------------------------------------------------------

def load_and_merge_fragments(
    repo_root: str,
    base_cross_references: dict[str, dict] | None = None,
    base_raw_source_types: list[str] | None = None,
) -> MergeResult:
    """Read all fragments from `<repo>/docs/_wiki/.schema.d/` and merge.

    Caller passes whatever it has parsed from the base schema (typically
    nothing, since the base today doesn't declare cross-references or
    raw-source-types — those registries are introduced by this overlay).

    Missing `.schema.d/` directory returns an empty merge with no errors.
    """
    fragments: list[FragmentParseResult] = []
    for path in list_fragment_paths(repo_root):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except (IOError, OSError, UnicodeDecodeError) as exc:
            frag = FragmentParseResult(path=path)
            frag.errors.append(f"{path}: could not read fragment: {exc}")
            fragments.append(frag)
            continue
        fragments.append(parse_fragment(text, path=path))

    return merge_fragments(base_cross_references, base_raw_source_types, fragments)


def fragments_signature(repo_root: str) -> tuple[float, int]:
    """Cheap (max-mtime, count) signature of the .schema.d/ directory.

    Callers can use this together with the base-schema mtime as a cache key
    so they re-parse only when something actually changed.
    """
    paths = list_fragment_paths(repo_root)
    if not paths:
        return (0.0, 0)
    mtimes = []
    for p in paths:
        try:
            mtimes.append(os.path.getmtime(p))
        except OSError:
            mtimes.append(0.0)
    return (max(mtimes), len(paths))


__all__ = [
    "ALLOWED_FRAGMENT_KEYS",
    "FORBIDDEN_FRAGMENT_KEYS",
    "FragmentParseResult",
    "MergeResult",
    "fragments_signature",
    "list_fragment_paths",
    "load_and_merge_fragments",
    "merge_fragments",
    "parse_fragment",
    "schema_d_dir",
]

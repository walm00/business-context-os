#!/usr/bin/env python3
"""
Consolidated YAML frontmatter parser + emitter for the wiki capability.

Replaces three hand-rolled parsers that drift independently:
- `extract_frontmatter` in `.claude/hooks/post_edit_frontmatter_check.py`
- `parse_frontmatter` in `.claude/scripts/refresh_wiki_index.py`
- the regex parser inside `.claude/scripts/wiki_schema.py`

Stdlib-only (no PyYAML). Supports the narrow YAML subset BCOS frontmatter
actually uses in practice:

- top-level scalars (`key: value`)
- inline lists (`key: [a, b, c]`)
- multi-line block lists with two-space indent and `- ` bullets
- single- and double-quoted scalar values (quotes preserved literally only
  when the value would otherwise be ambiguous; otherwise stripped)
- bare scalars containing `:` and `#` when they appear after the first `:`
- empty values become `""` (scalar context) or `[]` (when the key is in the
  caller-supplied list-field set)

Out of scope (intentional):
- YAML anchors / aliases (`&foo` / `*foo`)
- Block scalars (`|`, `>`)
- Nested mappings beyond the shallow-map shape used by `provenance:` etc.
- Tag handles (`!!str`, `!!int`)

If a richer shape ever becomes necessary, extend this module — never resurrect
a parallel parser.

Public API:
    parse_frontmatter(text_or_path)            -> dict | None
    emit_frontmatter(data, list_fields=None)   -> str
    apply_frontmatter(text, updates, ...)      -> str  # update-in-place helper
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
SCALAR_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_\-.]*)\s*:\s*(.*)$")
BULLET_RE = re.compile(r"^\s*-\s+(.*)$")

# Fields the BCOS frontmatter conventionally treats as lists, used to disambiguate
# "empty value" between scalar `""` and `[]`. Callers can supply more.
DEFAULT_LIST_FIELDS = frozenset(
    {
        "tags",
        "depends-on",
        "consumed-by",
        "builds-on",
        "references",
        "provides",
        "companion-urls",
        "raw-files",
        "subpages",
        "related-clusters",
        "related-data-points",
        "frontmatter-fields-required",
    }
)


def parse_frontmatter(text_or_path: str | Path) -> dict[str, Any] | None:
    """Parse a frontmatter block from text or a Path.

    Returns the populated dict, or None when the input has no frontmatter at all.
    Empty mapping (frontmatter present but no keys) returns None as well — same
    as the legacy parsers.
    """
    text = _coerce_text(text_or_path)
    if text is None:
        return None
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    return _parse_block(match.group(1))


def emit_frontmatter(
    data: dict[str, Any],
    list_fields: Iterable[str] | None = None,
) -> str:
    """Emit a `dict` as a YAML frontmatter body (without the `---` fences).

    Lists render as multi-line block lists when they contain entries with
    structural punctuation (colon, brackets, leading whitespace) and as inline
    `[a, b, c]` otherwise. Strings render unquoted unless they would create
    ambiguity (start with `[`, contain a leading `:`, or are empty).
    """
    out: list[str] = []
    for key, value in data.items():
        out.append(_emit_pair(str(key), value))
    return "\n".join(out)


def apply_frontmatter(
    text: str,
    updates: dict[str, Any],
    *,
    add_only: bool = False,
    list_fields: Iterable[str] | None = None,
) -> str:
    """Return `text` with frontmatter values updated/added per `updates`.

    Untouched keys preserve their original raw lines byte-for-byte — critical
    for migration round-trips where the emitter must not re-quote or re-format
    fields it did not change. Updated keys are re-emitted via `_emit_pair`.
    New keys append at the end of the block.

    Body content after the closing `---` fence is preserved byte-for-byte,
    including any blank lines between the fence and the first heading.

    When `add_only=True`, existing keys are NOT overwritten — useful for
    additive schema migrations.
    """
    body, rest = _split_frontmatter(text)
    if body is None:
        # Synthesize a fresh frontmatter block.
        block = emit_frontmatter(updates, list_fields=list_fields)
        return f"---\n{block}\n---\n{text}"

    parsed = _parse_block(body) or {}
    blocks = _split_into_blocks(body)
    seen_keys = {key for key, _ in blocks if key is not None}

    new_blocks: list[tuple[str | None, str]] = []
    for key, raw in blocks:
        if key is None:
            new_blocks.append((None, raw))
            continue
        if key in updates and not (add_only and key in parsed):
            new_blocks.append((key, _emit_pair(key, updates[key])))
        else:
            new_blocks.append((key, raw))

    for key, value in updates.items():
        if key not in seen_keys:
            if add_only and key in parsed:
                continue
            new_blocks.append((key, _emit_pair(key, value)))

    new_body = "\n".join(raw for _, raw in new_blocks)
    return f"---\n{new_body}\n---\n{rest}"


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    """Split `text` into (frontmatter_body, rest) preserving rest byte-for-byte.

    Returns (None, text) when there is no frontmatter. Otherwise returns the
    body (without the fence lines) and the rest of the document starting with
    whatever character followed the closing `---\\n` — typically a blank line
    before the first heading. Avoids the FRONTMATTER_RE greediness that ate
    body-leading whitespace.
    """
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    body = text[4:end]
    closing_end = end + len("\n---")
    if closing_end < len(text) and text[closing_end] == "\n":
        closing_end += 1
    return body, text[closing_end:]


def _split_into_blocks(body: str) -> list[tuple[str | None, str]]:
    """Split a frontmatter body into per-key blocks while preserving raw text.

    Each entry is `(key | None, raw_text)`. `None` is for blank lines / comments
    that don't bind to any key — they survive verbatim in the original position.
    Multi-line list continuations stay attached to their owning key's block.
    """
    blocks: list[tuple[str | None, str]] = []
    current_key: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_lines
        if current_key is not None:
            blocks.append((current_key, "\n".join(current_lines)))
        elif current_lines:
            blocks.append((None, "\n".join(current_lines)))
        current_key = None
        current_lines = []

    for raw in body.splitlines():
        stripped = raw.lstrip()
        if not raw.strip() or stripped.startswith("#"):
            if current_key is None:
                current_lines.append(raw)
            else:
                flush()
                blocks.append((None, raw))
            continue

        is_continuation = raw.startswith((" ", "\t"))
        if is_continuation and current_key is not None:
            current_lines.append(raw)
            continue

        match = SCALAR_RE.match(raw)
        if match:
            flush()
            current_key = match.group(1).strip()
            current_lines = [raw]
            continue

        # Stray line — keep as orphan
        if current_key is not None:
            flush()
        blocks.append((None, raw))

    flush()
    return blocks


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _coerce_text(text_or_path: str | Path) -> str | None:
    if isinstance(text_or_path, Path):
        try:
            return text_or_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
    return text_or_path


def _parse_block(block: str) -> dict[str, Any] | None:
    data: dict[str, Any] = {}
    pending_key: str | None = None
    pending_list: list[str] = []
    pending_value_was_empty = False

    lines = block.splitlines()
    for raw in lines:
        if pending_key is not None:
            bullet = BULLET_RE.match(raw)
            if bullet:
                pending_list.append(_strip_quotes(bullet.group(1).strip()))
                continue
            if not raw.strip():
                continue
            # End of pending key. Only commit a list when we actually saw
            # bullets — otherwise the empty-scalar placeholder set above
            # ("" or []) must survive. The earlier bug overwrote `etag: ""`
            # with `[]` whenever the next line was another scalar key.
            if pending_list:
                data[pending_key] = pending_list
            pending_key = None
            pending_list = []

        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        match = SCALAR_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()

        inline = _parse_inline_list(value)
        if inline is not None:
            data[key] = inline
            continue

        if value == "" or value == "[]":
            pending_key = key
            pending_list = []
            pending_value_was_empty = True
            data[key] = "" if value == "" else []
            continue

        data[key] = _strip_quotes(value)

    if pending_key is not None:
        if pending_list:
            data[pending_key] = pending_list
        # else: leave whatever placeholder we set above (`""` or `[]`)

    if not data:
        return None
    return data


def _parse_inline_list(value: str) -> list[str] | None:
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_strip_quotes(item.strip()) for item in _split_commas(inner) if item.strip()]


def _split_commas(s: str) -> list[str]:
    """Split on commas that aren't inside quotes."""
    out: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    for ch in s:
        if quote:
            if ch == quote:
                quote = None
            buf.append(ch)
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            continue
        if ch == ",":
            out.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    out.append("".join(buf))
    return out


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _key_order(body: str) -> list[str]:
    keys: list[str] = []
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#") or line.lstrip().startswith("- "):
            continue
        match = SCALAR_RE.match(line)
        if match:
            key = match.group(1).strip()
            if key not in keys:
                keys.append(key)
    return keys


# ---------------------------------------------------------------------------
# Emit helpers
# ---------------------------------------------------------------------------


def _emit_pair(key: str, value: Any) -> str:
    if value is None:
        return f"{key}:"
    if isinstance(value, bool):
        return f"{key}: {'true' if value else 'false'}"
    if isinstance(value, (int, float)):
        return f"{key}: {value}"
    if isinstance(value, list):
        return _emit_list(key, value)
    if isinstance(value, dict):
        # Shallow nested map (provenance:-style).
        rendered = ["{"]
        parts = []
        for k, v in value.items():
            parts.append(f"{k}: {_emit_scalar(v)}")
        rendered.append(", ".join(parts))
        rendered.append("}")
        return f"{key}: {''.join(rendered)}"
    return f"{key}: {_emit_scalar(value)}"


def _emit_list(key: str, items: list[Any]) -> str:
    if not items:
        return f"{key}: []"
    needs_block = any(_needs_block_form(item) for item in items)
    if needs_block:
        lines = [f"{key}:"]
        for item in items:
            lines.append(f"  - {_emit_scalar(item)}")
        return "\n".join(lines)
    rendered = ", ".join(_emit_scalar(item) for item in items)
    return f"{key}: [{rendered}]"


def _needs_block_form(item: Any) -> bool:
    text = _emit_scalar(item)
    return any(ch in text for ch in (":", "[", "]", ",", "#"))


def _emit_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if text.startswith(("[", "{", "&", "*", "!", "?", "-", ">")) or ":" in text or text != text.strip():
        return f'"{text}"'
    return text


__all__ = [
    "parse_frontmatter",
    "emit_frontmatter",
    "apply_frontmatter",
    "DEFAULT_LIST_FIELDS",
]

#!/usr/bin/env python3
"""
Canonical BCOS context index.

Walks docs/ once, parses frontmatter, derives folder/path facets, and emits a
single normalized model for document-index, dashboard Atlas, Galaxy, scheduled
jobs, and future retrieval tooling.

This module deliberately stays stdlib-only. It handles the YAML shapes BCOS
frontmatter uses in practice: scalars, inline lists, block lists, and shallow
nested maps used by provenance/key metadata.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
DEFAULT_OUTPUT = REPO_ROOT / ".claude" / "quality" / "context-index.json"

REQUIRED_FIELDS = ("name", "type", "cluster", "version", "status", "created", "last-updated")
LIST_FIELDS = {
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
}

LIFECYCLE_BUCKETS = ("_inbox", "_planned", "active", "_archive", "_bcos-framework", "_collections")
WIKI_PAGE_PREFIXES = ("docs/_wiki/pages/", "docs/_wiki/source-summary/")
WIKI_INTERNAL_PREFIXES = (
    "docs/_wiki/raw/",
    "docs/_wiki/.archive/",
    "docs/_wiki/queue.md",
    "docs/_wiki/log.md",
    "docs/_wiki/index.md",
    "docs/_wiki/overview.md",
    "docs/_wiki/README.md",
    "docs/_wiki/.config.yml",
    "docs/_wiki/.schema.yml",
)
GENERATED_PATHS = {
    "docs/bcos-control-map.md",
    "docs/document-index.md",
    "docs/_wiki/index.md",
    "docs/.wake-up-context.md",
}
FRAMEWORK_PREFIX = "docs/_bcos-framework/"
KNOWN_UNDERSCORES = {"_inbox", "_planned", "_archive", "_collections", "_wiki", "_bcos-framework"}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
OWNERSHIP_HEADING_RE = re.compile(r"^\s*\*\*([A-Z_ -]+):\*\*\s*(.*)$")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
FIRST_PARAGRAPH_MAX_CHARS = 400


@dataclass
class ContextDoc:
    path: str
    name: str
    filename: str
    zone: str
    bucket: str
    folder: str
    path_tags: list[str]
    trust_level: str
    is_canonical: bool
    size_bytes: int
    modified: str
    has_frontmatter: bool
    missing_required: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    type: str | None = None
    cluster: str | None = None
    status: str | None = None
    version: str | None = None
    created: str | None = None
    last_updated: str | None = None
    last_reviewed: str | None = None
    last_fetched: str | None = None
    review_cycle: str | None = None
    next_review: str | None = None
    age_days: int | None = None
    reviewed_age_days: int | None = None
    tags: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    consumed_by: list[str] = field(default_factory=list)
    page_type: str | None = None
    manifest_schema: str | None = None
    collection: str | None = None
    domain_statement: str | None = None
    exclusively_owns: list[str] = field(default_factory=list)
    strictly_avoids: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    first_paragraph: str | None = None


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Parse BCOS frontmatter into scalars, lists, and shallow maps."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None

    lines = match.group(1).splitlines()
    data: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        if not raw or raw.lstrip().startswith("#") or raw.startswith((" ", "\t")):
            i += 1
            continue
        if ":" not in raw:
            i += 1
            continue

        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()

        inline_list = _parse_inline_list(value)
        if inline_list is not None:
            data[key] = inline_list
            i += 1
            continue

        if value == "":
            nested, next_i = _parse_indented_block(lines, i + 1)
            if nested is None:
                data[key] = [] if key in LIST_FIELDS else ""
                i += 1
            else:
                data[key] = nested
                i = next_i
            continue

        data[key] = _clean_scalar(value)
        i += 1

    return data if data else None


def _parse_indented_block(lines: list[str], start: int) -> tuple[Any, int] | tuple[None, int]:
    items: list[str] = []
    mapping: dict[str, Any] = {}
    saw_item = False
    saw_map = False
    i = start
    while i < len(lines):
        raw = lines[i].rstrip()
        if not raw:
            i += 1
            continue
        if not raw.startswith((" ", "\t")):
            break
        stripped = raw.strip()
        if stripped.startswith("- "):
            saw_item = True
            items.append(_clean_scalar(stripped[2:].strip()))
            i += 1
            continue
        if ":" in stripped:
            saw_map = True
            sub_key, _, sub_val = stripped.partition(":")
            sub_val = sub_val.strip()
            inline = _parse_inline_list(sub_val)
            mapping[sub_key.strip()] = inline if inline is not None else _clean_scalar(sub_val)
            i += 1
            continue
        i += 1
    if saw_item:
        return items, i
    if saw_map:
        return mapping, i
    return None, start


def _parse_inline_list(value: str) -> list[str] | None:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [_clean_scalar(part.strip()) for part in inner.split(",") if part.strip()]


def _clean_scalar(value: Any) -> str:
    s = str(value).strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1]
    return s.strip()


def parse_ownership_spec(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "DOMAIN": None,
        "EXCLUSIVELY_OWNS": [],
        "STRICTLY_AVOIDS": [],
    }
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = OWNERSHIP_HEADING_RE.match(lines[i])
        if not match:
            i += 1
            continue
        key = match.group(1).strip().replace(" ", "_")
        inline = match.group(2).strip()
        if key == "DOMAIN":
            out["DOMAIN"] = _strip_markdown(inline) if inline else None
            i += 1
            continue
        if key in {"EXCLUSIVELY_OWNS", "STRICTLY_AVOIDS"}:
            items: list[str] = []
            if inline:
                items.append(_strip_markdown(inline))
            j = i + 1
            seen_bullet = False
            while j < len(lines):
                line = lines[j]
                stripped = line.strip()
                if OWNERSHIP_HEADING_RE.match(line) or stripped.startswith("#"):
                    break
                if not stripped:
                    if seen_bullet:
                        break
                    j += 1
                    continue
                if stripped.startswith("- "):
                    seen_bullet = True
                    items.append(_strip_markdown(stripped[2:]))
                    j += 1
                    continue
                if seen_bullet:
                    break
                j += 1
            out[key] = [item for item in items if item]
            i = j
            continue
        i += 1
    return out


def _strip_markdown(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value.strip())
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def iter_docs(root: Path | None = None, include_dotfiles: bool = False) -> list[Path]:
    root = (root or REPO_ROOT).resolve()
    docs_root = root / "docs"
    if not docs_root.is_dir():
        return []
    docs: list[Path] = []
    for path in sorted(docs_root.rglob("*.md")):
        if not include_dotfiles and path.name.startswith("."):
            continue
        docs.append(path)
    return docs


def build_context_index(root: Path | None = None, now: _dt.datetime | None = None) -> dict[str, Any]:
    root = (root or REPO_ROOT).resolve()
    now = now or _dt.datetime.now(_dt.timezone.utc)
    docs = [_read_context_doc(path, root, now) for path in iter_docs(root)]
    docs = [doc for doc in docs if doc is not None]
    doc_dicts = [asdict(doc) for doc in docs]
    edges = _build_edges(docs)

    return {
        "schema_version": 1,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "repo_root": str(root),
        "repo_name": root.name,
        "counts": {
            "total": len(docs),
            "with_frontmatter": sum(1 for doc in docs if doc.has_frontmatter),
            "missing_required": sum(1 for doc in docs if doc.missing_required),
            "warnings": sum(len(doc.warnings) for doc in docs),
        },
        "summaries": {
            "zones": _count_by(doc_dicts, "zone"),
            "buckets": _count_by(doc_dicts, "bucket"),
            "clusters": _count_by(doc_dicts, "cluster"),
            "types": _count_by(doc_dicts, "type"),
            "statuses": _count_by(doc_dicts, "status"),
            "page_types": _count_by(doc_dicts, "page_type"),
            "manifest_schemas": _count_by(doc_dicts, "manifest_schema"),
            "tags": _count_many(doc_dicts, "tags"),
            "path_tags": _count_many(doc_dicts, "path_tags"),
            "warnings": _warning_counts(docs),
        },
        "docs": doc_dicts,
        "edges": edges,
        "lifecycle": _lifecycle(doc_dicts),
        "domains": _domains(doc_dicts),
        "orphans": _orphans(doc_dicts, edges),
    }


def _read_context_doc(path: Path, root: Path, now: _dt.datetime) -> ContextDoc | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    rel = path.relative_to(root).as_posix()
    stat = path.stat()
    meta = parse_frontmatter(text) or {}
    has_frontmatter = bool(meta)
    zone = _zone_for(rel)
    bucket = _bucket_for(rel, zone)
    folder = _folder_for(rel)
    path_tags = _path_tags(rel)
    warnings = _metadata_warnings(meta, zone)
    missing_required = [field for field in REQUIRED_FIELDS if not meta.get(field)]
    if not _requires_base_metadata(zone, rel):
        missing_required = []
    ownership = parse_ownership_spec(text)
    body = _strip_frontmatter(text)
    headings = _extract_headings(body)
    first_paragraph = _extract_first_paragraph(body)

    return ContextDoc(
        path=rel,
        name=str(meta.get("name") or path.stem),
        filename=path.name,
        zone=zone,
        bucket=bucket,
        folder=folder,
        path_tags=path_tags,
        trust_level=_trust_level(zone),
        is_canonical=zone == "active",
        size_bytes=len(text.encode("utf-8")),
        modified=_dt.datetime.fromtimestamp(stat.st_mtime).date().isoformat(),
        has_frontmatter=has_frontmatter,
        missing_required=missing_required,
        warnings=warnings,
        meta=meta,
        type=_scalar_or_none(meta.get("type")),
        cluster=_scalar_or_none(meta.get("cluster")),
        status=_scalar_or_none(meta.get("status")),
        version=_scalar_or_none(meta.get("version")),
        created=_scalar_or_none(meta.get("created")),
        last_updated=_scalar_or_none(meta.get("last-updated")),
        last_reviewed=_scalar_or_none(meta.get("last-reviewed")),
        last_fetched=_scalar_or_none(meta.get("last-fetched")),
        review_cycle=_scalar_or_none(meta.get("review-cycle")),
        next_review=_scalar_or_none(meta.get("next-review")),
        age_days=_days_since(meta.get("last-updated"), now),
        reviewed_age_days=_days_since(meta.get("last-reviewed"), now),
        tags=_as_list(meta.get("tags")),
        depends_on=_as_list(meta.get("depends-on")),
        consumed_by=_as_list(meta.get("consumed-by")),
        page_type=_scalar_or_none(meta.get("page-type")),
        manifest_schema=_scalar_or_none(meta.get("manifest-schema")),
        collection=_scalar_or_none(meta.get("collection")),
        domain_statement=ownership.get("DOMAIN"),
        exclusively_owns=ownership.get("EXCLUSIVELY_OWNS", []),
        strictly_avoids=ownership.get("STRICTLY_AVOIDS", []),
        headings=headings,
        first_paragraph=first_paragraph,
    )


def _strip_frontmatter(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    return text[match.end():] if match else text


def _extract_headings(body: str) -> list[str]:
    """Return H1/H2/H3 heading text in document order, deduplicated."""
    seen: set[str] = set()
    headings: list[str] = []
    in_fence = False
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(stripped)
        if not match:
            continue
        text = _strip_markdown(match.group(2))
        if text and text not in seen:
            seen.add(text)
            headings.append(text)
    return headings


def _extract_first_paragraph(body: str) -> str | None:
    """Return the first non-heading, non-fence prose paragraph, capped in length."""
    in_fence = False
    buffer: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        fence = line.lstrip().startswith("```") or line.lstrip().startswith("~~~")
        if fence:
            if buffer:
                break
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            if buffer:
                break
            continue
        if HEADING_RE.match(stripped):
            if buffer:
                break
            continue
        # Skip ownership-spec lines (DOMAIN: / EXCLUSIVELY_OWNS: bullets) so the
        # first prose paragraph is what surfaces, not the spec block.
        if OWNERSHIP_HEADING_RE.match(stripped) or stripped.startswith(("- ", "* ", "> ")):
            if buffer:
                break
            continue
        buffer.append(stripped)
        if sum(len(piece) for piece in buffer) >= FIRST_PARAGRAPH_MAX_CHARS:
            break
    if not buffer:
        return None
    text = " ".join(buffer)
    text = _strip_markdown(text)
    if len(text) > FIRST_PARAGRAPH_MAX_CHARS:
        text = text[:FIRST_PARAGRAPH_MAX_CHARS - 1].rstrip() + "…"
    return text


def _zone_for(rel: str) -> str:
    if rel in GENERATED_PATHS:
        return "generated"
    if rel.startswith(FRAMEWORK_PREFIX):
        return "framework"
    if any(rel.startswith(prefix) or rel == prefix.rstrip("/") for prefix in WIKI_PAGE_PREFIXES):
        return "wiki"
    if any(rel.startswith(prefix) or rel == prefix.rstrip("/") for prefix in WIKI_INTERNAL_PREFIXES):
        return "wiki-internal"
    if rel.startswith("docs/_collections/"):
        if rel.endswith("/_manifest.md"):
            return "collection-manifest"
        if rel.endswith(".meta.md"):
            return "collection-sidecar"
        return "collection-artifact"
    if rel.startswith("docs/_inbox/"):
        return "inbox"
    if rel.startswith("docs/_planned/"):
        return "planned"
    if rel.startswith("docs/_archive/"):
        return "archive"
    parts = rel.split("/")
    if len(parts) > 2 and parts[1].startswith("_") and parts[1] not in KNOWN_UNDERSCORES:
        return "custom-optout"
    return "active"


def _bucket_for(rel: str, zone: str) -> str:
    parts = rel.split("/")
    first = parts[1] if len(parts) > 2 else ""
    if first in {"_inbox", "_planned", "_archive", "_bcos-framework", "_collections"}:
        return first
    return "active"


def _folder_for(rel: str) -> str:
    parent = Path(rel).parent.as_posix()
    return parent if parent != "." else ""


def _path_tags(rel: str) -> list[str]:
    parts = rel.split("/")[1:-1]
    tags = []
    for part in parts:
        if part in {".archive", "raw"}:
            tags.append(part.strip("."))
        else:
            tags.append(part)
    return tags


def _trust_level(zone: str) -> str:
    if zone == "active":
        return "high"
    if zone in {"wiki", "collection-manifest", "collection-sidecar"}:
        return "high-derived"
    if zone == "planned":
        return "future"
    if zone == "archive":
        return "historical"
    if zone == "inbox":
        return "low"
    if zone in {"framework", "generated", "wiki-internal"}:
        return "system"
    if zone == "collection-artifact":
        return "evidence"
    return "opted-out"


def _requires_base_metadata(zone: str, rel: str) -> bool:
    return zone in {"active", "wiki", "collection-sidecar"} or (
        zone == "collection-manifest" and rel.endswith("/_manifest.md")
    )


def _metadata_warnings(meta: dict[str, Any], zone: str) -> list[str]:
    warnings: list[str] = []
    if zone in {"active", "wiki"} and not _as_list(meta.get("tags")):
        warnings.append("missing-tags")
    if zone == "wiki" and not meta.get("last-reviewed"):
        warnings.append("missing-last-reviewed")
    if zone == "active" and meta.get("review-cycle") and not meta.get("last-reviewed"):
        warnings.append("missing-last-reviewed")
    return warnings


def _scalar_or_none(value: Any) -> str | None:
    if value is None or isinstance(value, (list, dict)):
        return None
    s = str(value).strip()
    return s or None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value] if value.strip() else []
    return []


def _days_since(value: Any, now: _dt.datetime) -> int | None:
    raw = _scalar_or_none(value)
    if not raw:
        return None
    try:
        if len(raw) == 10:
            dt = _dt.datetime.fromisoformat(raw + "T00:00:00+00:00")
        else:
            dt = _dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None
    return (now - dt.astimezone(_dt.timezone.utc)).days


def _build_edges(docs: list[ContextDoc]) -> list[dict[str, Any]]:
    name_to_path = {doc.name: doc.path for doc in docs if doc.name}
    stem_to_path = {Path(doc.path).stem: doc.path for doc in docs}
    known_paths = {doc.path for doc in docs}
    edges: list[dict[str, Any]] = []
    for doc in docs:
        for target in doc.depends_on:
            edges.append({"from": doc.path, "to": _resolve_target(target, doc.path, name_to_path, stem_to_path, known_paths), "kind": "depends-on"})
        for target in doc.consumed_by:
            edges.append({"from": doc.path, "to": _resolve_target(target, doc.path, name_to_path, stem_to_path, known_paths), "kind": "consumed-by"})
        for target in _as_list(doc.meta.get("builds-on")):
            edges.append({"from": doc.path, "to": _resolve_target(target, doc.path, name_to_path, stem_to_path, known_paths), "kind": "builds-on"})
        for target in _as_list(doc.meta.get("provides")):
            edges.append({"from": doc.path, "to": _resolve_target(target, doc.path, name_to_path, stem_to_path, known_paths), "kind": "provides"})
        for target in _as_list(doc.meta.get("references")):
            edges.append({"from": doc.path, "to": _resolve_target(target, doc.path, name_to_path, stem_to_path, known_paths), "kind": "references"})
    return edges


def _resolve_target(
    target: str,
    source_path: str,
    name_to_path: dict[str, str],
    stem_to_path: dict[str, str],
    known_paths: set[str],
) -> str:
    """Resolve a frontmatter reference to a repo-relative path when possible.

    Tries in order:
    1. Direct match by `name:` of an existing doc.
    2. Direct match by filename stem (e.g., `pricing` → `docs/pricing.md`).
    3. Relative-path resolution against the source doc's directory, clamped
       to the `docs/` tree (e.g., `../../pricing.md` from
       `docs/_wiki/pages/foo.md` → `docs/pricing.md`).

    A relative target that escapes `docs/` (e.g., `../../../.private/secret.md`)
    is NOT normalized — the literal target string is returned, so we never
    bake an out-of-tree path into `context-index.json` edges. Callers that
    care about edge validity check whether the returned value is in
    `known_paths`.
    """
    if target in name_to_path:
        return name_to_path[target]
    if target in stem_to_path:
        return stem_to_path[target]
    if any(sep in target for sep in ("/", "\\")):
        try:
            source_dir = Path(source_path).parent
            resolved = (source_dir / target).as_posix()
            normalized = _normalize_relpath(resolved)
            if normalized is None:
                # Escapes the repo (or the source root). Refuse to bake it in.
                return target
            if not normalized.startswith("docs/"):
                # Resolved cleanly but landed outside docs/. Refuse the
                # normalization rather than persist a path that points at
                # something the framework doesn't manage.
                return target
            return normalized
        except (ValueError, OSError):
            return target
    return target


def _normalize_relpath(path: str) -> str | None:
    """Collapse `..` / `.` segments without touching the filesystem.

    Returns None if the path escapes its starting tree (i.e., a `..` would
    pop above the implicit root). Previously a leading `..` was silently
    preserved, which let frontmatter references like `../../../.private/foo.md`
    leak out-of-tree paths into the edge list.
    """
    parts = path.replace("\\", "/").split("/")
    out: list[str] = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not out:
                # Trying to escape above the source root.
                return None
            if out[-1] == "..":
                # Already escaped; further `..` is also an escape.
                return None
            out.pop()
            continue
        out.append(part)
    return "/".join(out)


def _count_by(items: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = item.get(field_name) or "unspecified"
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


def _count_many(items: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        values = item.get(field_name) or []
        for value in values:
            counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


def _warning_counts(docs: list[ContextDoc]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for doc in docs:
        for warning in doc.warnings:
            counts[warning] = counts.get(warning, 0) + 1
    return dict(sorted(counts.items()))


def _lifecycle(docs: list[dict[str, Any]]) -> dict[str, list[str]]:
    lifecycle = {bucket: [] for bucket in LIFECYCLE_BUCKETS}
    for doc in docs:
        lifecycle.setdefault(doc["bucket"], []).append(doc["path"])
    return lifecycle


def _domains(docs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    domains: dict[str, dict[str, Any]] = {}
    for doc in docs:
        domain = doc.get("cluster") or (f"({doc['bucket']})" if doc.get("bucket") != "active" else "(unclassified)")
        entry = domains.setdefault(domain, {"doc_count": 0, "total_bytes": 0, "_age_sum": 0, "_age_n": 0, "doc_paths": []})
        entry["doc_count"] += 1
        entry["total_bytes"] += doc.get("size_bytes") or 0
        entry["doc_paths"].append(doc["path"])
        if doc.get("age_days") is not None:
            entry["_age_sum"] += doc["age_days"]
            entry["_age_n"] += 1
    for entry in domains.values():
        entry["avg_age_days"] = (entry["_age_sum"] / entry["_age_n"]) if entry["_age_n"] else None
        del entry["_age_sum"]
        del entry["_age_n"]
    return dict(sorted(domains.items()))


def _orphans(docs: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[str]:
    touched: set[str] = set()
    for edge in edges:
        if isinstance(edge.get("from"), str):
            touched.add(edge["from"])
        target = edge.get("to")
        if isinstance(target, str) and "/" in target:
            touched.add(target)
    return sorted(
        doc["path"]
        for doc in docs
        if doc["bucket"] == "active" and doc["has_frontmatter"] and doc["path"] not in touched
    )


def write_context_index(root: Path | None = None, output: Path | None = None) -> dict[str, Any]:
    root = (root or REPO_ROOT).resolve()
    output = (output or (root / ".claude" / "quality" / "context-index.json")).resolve()
    index = build_context_index(root)
    persisted = _sanitize_for_persist(index)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(persisted, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return index


def _sanitize_for_persist(index: dict[str, Any]) -> dict[str, Any]:
    """Strip absolute paths and the local repo name from the persisted artifact.

    The tracked `.claude/quality/context-index.json` ships in the public template
    repo, so it must not leak the local user's home directory or the dev clone's
    folder name. Runtime callers using `build_context_index()` directly still
    receive the in-memory values unchanged.
    """
    sanitized = dict(index)
    if "repo_root" in sanitized:
        sanitized["repo_root"] = "."
    if "repo_name" in sanitized:
        sanitized["repo_name"] = ""
    return sanitized


def print_summary(index: dict[str, Any]) -> None:
    counts = index.get("counts", {})
    print(f"repo:       {index.get('repo_name')}")
    print(f"docs:       {counts.get('total', 0)}")
    print(f"with FM:    {counts.get('with_frontmatter', 0)}")
    print(f"missing:    {counts.get('missing_required', 0)}")
    print(f"warnings:   {counts.get('warnings', 0)}")
    print("")
    print("zones:")
    for zone, count in (index.get("summaries", {}).get("zones") or {}).items():
        print(f"  {zone:22} {count}")
    tags = index.get("summaries", {}).get("tags") or {}
    if tags:
        print("")
        print("tags:")
        for tag, count in list(tags.items())[:20]:
            print(f"  {tag:22} {count}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build canonical BCOS context index.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repository root")
    parser.add_argument("--output", type=Path, default=None, help="JSON output path")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    parser.add_argument("--write", action="store_true", help="Write .claude/quality/context-index.json")
    parser.add_argument("--summary", action="store_true", help="Print human summary")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.write:
        index = write_context_index(args.root, args.output)
    else:
        index = build_context_index(args.root)

    if args.json:
        print(json.dumps(index, indent=2, ensure_ascii=False))
    elif args.summary or not args.write:
        print_summary(index)
    elif args.write:
        output = args.output or (args.root / ".claude" / "quality" / "context-index.json")
        print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

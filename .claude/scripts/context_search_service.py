#!/usr/bin/env python3
"""
HTTP-facing service wrapper for context_search.py.

Dashboards should call this module instead of duplicating query parsing,
index filtering, and hit enrichment. The scorer still lives in
context_search.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import context_search

_INDEX_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def search_context(
    repo: Path,
    params: Mapping[str, Any],
    *,
    index: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    """Return a dashboard/API context-search response and HTTP status."""
    query = (_param(params, "q") or _param(params, "query") or "").strip()
    if not query:
        return {"error": "missing query"}, 400

    try:
        top_k = max(1, min(25, int(_param(params, "top") or _param(params, "top_k") or "10")))
    except ValueError:
        top_k = 10

    include_raw = (_param(params, "include") or "active").strip() or "active"
    include = None if include_raw == "all" else {x for x in include_raw.split(",") if x}
    zone = (_param(params, "zone") or "").strip() or None
    mode = (_param(params, "mode") or "mechanical").strip().lower() or "mechanical"
    semantic = mode in {"semantic", "llm"} or _truthy(_param(params, "semantic"))
    dry_run = _truthy(_param(params, "dry_run") or _param(params, "dry-run"))
    explain = _truthy(_param(params, "explain"))

    if index is None:
        index = cached_context_index(repo)
    if index is None:
        return {
            "query": query,
            "repo": repo.name,
            "include": include_raw,
            "mode": mode,
            "hits": [],
            "warning": f"index-missing:{repo / '.claude' / 'quality' / 'context-index.json'}",
        }, 200

    search_index = filter_index_by_include(index, include)
    try:
        result = context_search.search(
            query,
            zone=zone,
            top_k=top_k,
            semantic=semantic,
            dry_run=dry_run,
            explain=explain,
            index=search_index,
        )
    except context_search.SemanticNotImplementedError as exc:
        return {
            "ok": False,
            "query": query,
            "repo": repo.name,
            "include": include_raw,
            "mode": mode,
            "error": "semantic-unavailable",
            "message": str(exc),
        }, 501

    docs_by_citation = {
        context_search._citation_id(doc): doc
        for doc in search_index.get("docs") or []
    }
    hits = []
    for hit in result.get("hits") or []:
        doc = docs_by_citation.get(hit.get("citation-id"))
        hits.append(source_from_doc(doc, hit) if doc else hit)

    result["repo"] = repo.name
    result["include"] = include_raw
    result["mode"] = "semantic" if semantic else "mechanical"
    result["hits"] = hits
    return result, 200


def cached_context_index(repo: Path) -> dict[str, Any] | None:
    index_path = repo / ".claude" / "quality" / "context-index.json"
    if not index_path.is_file():
        return None
    stat = index_path.stat()
    key = str(index_path)
    cached = _INDEX_CACHE.get(key)
    if cached and cached[0] == stat.st_mtime:
        return cached[1]
    data = json.loads(index_path.read_text(encoding="utf-8"))
    _INDEX_CACHE[key] = (stat.st_mtime, data)
    return data


def filter_index_by_include(index: dict[str, Any], include: set[str] | None) -> dict[str, Any]:
    if include is None:
        return index
    docs = [d for d in index.get("docs") or [] if d.get("bucket") in include]
    keep = {d.get("path") for d in docs}
    edges = [
        e for e in index.get("edges") or []
        if e.get("from") in keep and (e.get("to") in keep or not isinstance(e.get("to"), str))
    ]
    filtered = dict(index)
    filtered["docs"] = docs
    filtered["edges"] = edges
    return filtered


def source_from_doc(doc: dict[str, Any], hit: dict[str, Any]) -> dict[str, Any]:
    meta = doc.get("meta") or {}
    first_paragraph = (doc.get("first_paragraph") or "").strip()
    if first_paragraph in {"---", "..."}:
        first_paragraph = ""
    if len(first_paragraph) > 420:
        first_paragraph = first_paragraph[:419].rstrip() + "..."
    builds_on = hit.get("builds-on") or meta.get("builds-on") or []
    raw_files = meta.get("raw-files") or meta.get("raw_files") or []
    provenance = meta.get("provenance") or doc.get("provenance") or {}
    source_url = (
        meta.get("source-url")
        or meta.get("source_url")
        or meta.get("url")
        or (provenance.get("url") if isinstance(provenance, dict) else None)
    )
    return {
        **hit,
        "path": doc.get("path"),
        "name": doc.get("name") or doc.get("filename") or hit.get("slug"),
        "filename": doc.get("filename"),
        "type": doc.get("type"),
        "status": doc.get("status"),
        "bucket": doc.get("bucket"),
        "folder": doc.get("folder"),
        "tags": doc.get("tags") or [],
        "path_tags": doc.get("path_tags") or [],
        "trust_level": doc.get("trust_level"),
        "is_canonical": doc.get("is_canonical"),
        "last_updated": doc.get("last_updated"),
        "last_reviewed": doc.get("last_reviewed"),
        "last_fetched": doc.get("last_fetched"),
        "reviewed_age_days": doc.get("reviewed_age_days"),
        "size_bytes": doc.get("size_bytes"),
        "domain_statement": doc.get("domain_statement"),
        "first_paragraph": first_paragraph,
        "source_url": source_url,
        "raw_files": raw_files,
        "builds_on": builds_on,
        "provenance": provenance,
    }


def _param(params: Mapping[str, Any], key: str) -> str:
    value = params.get(key)
    if isinstance(value, list):
        value = value[0] if value else ""
    if value is None:
        return ""
    return str(value)


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

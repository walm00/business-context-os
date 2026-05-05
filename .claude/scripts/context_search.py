#!/usr/bin/env python3
"""
Cross-zone read foundation (P2).

`context_search` ranks documents in `.claude/quality/context-index.json` against
a query using a BM25-style mechanical scorer. Reads the canonical corpus built
by `context_index.py`; never re-walks `docs/` itself.

Mechanical-first (D-10 strict): the default path is pure Python, deterministic,
and fast. The only LLM-touching path is `--semantic`, which the user explicitly
opts into. There is no auto-trigger on 0-hit, no fallback, no hidden LLM cost.

Output schema per hit:
    {
        slug, zone, page-type, cluster, summary, builds-on (top-3),
        freshness-days, last-reviewed, score, citation-id, truncated?
    }

Result envelope:
    {
        query, zones-searched, zones-skipped-not-present,
        hits: [...], escalation: <reason | None>
    }

Usage:
    python .claude/scripts/context_search.py --query "stripe billing"
    python .claude/scripts/context_search.py --query "linkedin tone" --zone wiki
    python .claude/scripts/context_search.py --query "anything" --semantic --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_INDEX = REPO_ROOT / ".claude" / "quality" / "context-index.json"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from load_zone_registry import load_zone_registry  # noqa: E402

DEFAULT_TOP_K = 10
DEFAULT_TOKEN_BUDGET = 8000

ROLE_BOOSTS = {
    "canonical": 1.50,
    "derived": 1.20,
    "evidence": 1.10,
    "system": 1.00,
    "future": 0.90,
    "historical": 0.70,
    "opted-out": 0.50,
}

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "to", "for", "with", "by", "and", "or", "not",
    "this", "that", "these", "those", "it", "its", "as", "at", "from",
    "but", "if", "we", "i", "do", "does", "did",
}

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [tok for tok in TOKEN_RE.findall(text.lower()) if tok not in STOPWORDS and len(tok) >= 2]


def _searchable_text(doc: dict[str, Any]) -> str:
    parts: list[str] = []
    parts.append(str(doc.get("name") or ""))
    parts.append(str(doc.get("filename") or ""))
    parts.append(str(doc.get("cluster") or ""))
    parts.append(str(doc.get("type") or ""))
    parts.append(str(doc.get("page_type") or ""))
    parts.append(str(doc.get("status") or ""))
    parts.append(str(doc.get("domain_statement") or ""))
    parts.append(str(doc.get("first_paragraph") or ""))
    for items_field in ("tags", "exclusively_owns", "strictly_avoids", "path_tags", "headings"):
        for item in doc.get(items_field) or []:
            parts.append(str(item))
    return " ".join(p for p in parts if p)


def _doc_token_counts(docs: list[dict[str, Any]]) -> tuple[list[list[str]], dict[str, int]]:
    """Return per-doc token lists and inverse-document-frequency counts."""
    per_doc_tokens = [_tokenize(_searchable_text(doc)) for doc in docs]
    df: dict[str, int] = {}
    for tokens in per_doc_tokens:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1
    return per_doc_tokens, df


def _zone_role_map() -> dict[str, str]:
    try:
        registry = load_zone_registry()
    except Exception:
        return {}
    return {entry["id"]: entry["source-of-truth-role"] or "system" for entry in registry}


def _zone_optional_map() -> dict[str, bool]:
    try:
        registry = load_zone_registry()
    except Exception:
        return {}
    return {entry["id"]: bool(entry.get("optional")) for entry in registry}


def _recency_boost(age_days: int | None) -> float:
    if age_days is None:
        return 1.0
    # Fresh docs get a small bump; old docs decay gently. Half-life ~365d.
    return 1.0 + 0.5 / (1.0 + max(age_days, 0) / 365.0)


def _citation_id(doc: dict[str, Any]) -> str:
    """Stable, collision-free citation. zone:relative-path shape.

    The relative path is the doc's path under `docs/` with the leading
    underscore-prefixed zone folder stripped (when present) and the `.md`
    extension dropped. This keeps top-level citations short (`active:pricing`)
    while preventing same-stem collisions inside a nested zone
    (`planned:wiki-missing-layers/README` vs
    `planned:collections-schema-governance/README`).

    Stable across whitespace edits because it is derived purely from the path.
    """
    zone = doc.get("zone") or "unknown"
    path = (doc.get("path") or "").replace("\\", "/")
    if not path:
        stem = (doc.get("filename") or "").rsplit(".", 1)[0]
        return f"{zone}:{stem}"
    rel = path[len("docs/"):] if path.startswith("docs/") else path
    if rel.startswith("_") and "/" in rel:
        rel = rel.split("/", 1)[1]
    if rel.endswith(".md"):
        rel = rel[:-3]
    return f"{zone}:{rel}"


def _summary(doc: dict[str, Any], max_chars: int) -> tuple[str, bool]:
    pieces: list[str] = []
    if doc.get("name"):
        pieces.append(str(doc["name"]))
    if doc.get("cluster"):
        pieces.append(f"({doc['cluster']})")
    if doc.get("domain_statement"):
        pieces.append(str(doc["domain_statement"]))
    elif doc.get("exclusively_owns"):
        pieces.append("; ".join(str(x) for x in (doc.get("exclusively_owns") or [])[:2]))
    text = " — ".join(pieces).strip(" —")
    truncated = False
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
        truncated = True
    return text, truncated


def _hit_from_doc(
    doc: dict[str, Any],
    score: float,
    summary_chars: int,
) -> dict[str, Any]:
    summary, truncated = _summary(doc, summary_chars)
    builds_on = list((doc.get("meta") or {}).get("builds-on") or [])[:3]
    return {
        "slug": Path(doc.get("path") or "").stem or (doc.get("name") or ""),
        "zone": doc.get("zone"),
        "page-type": doc.get("page_type"),
        "cluster": doc.get("cluster"),
        "summary": summary,
        "builds-on": builds_on,
        "freshness-days": doc.get("age_days"),
        "last-reviewed": doc.get("last_reviewed"),
        "score": round(score, 4),
        "citation-id": _citation_id(doc),
        "truncated": truncated,
    }


def search(
    query: str,
    *,
    zone: str | None = None,
    top_k: int = DEFAULT_TOP_K,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    semantic: bool = False,
    dry_run: bool = False,
    index: dict[str, Any] | None = None,
    index_path: Path | None = None,
) -> dict[str, Any]:
    """Run a mechanical search and return the structured result envelope."""

    if semantic and not dry_run:
        raise SemanticNotImplementedError(
            "--semantic requires --dry-run for now. The 3-candidate LLM "
            "reformulation path is specified by P2 but the LLM client wiring "
            "is deferred. Use `--semantic --dry-run` to validate the opt-in "
            "envelope without firing the LLM, or run mechanical search by "
            "omitting --semantic. Tracked in plan-manifest follow-ups."
        )

    if index is None:
        target = index_path or DEFAULT_INDEX
        if not target.is_file():
            return _empty_result(query, semantic=semantic, dry_run=dry_run, reason=f"index-missing:{target}")
        index = json.loads(target.read_text(encoding="utf-8"))

    docs = index.get("docs") or []
    role_map = _zone_role_map()
    optional_map = _zone_optional_map()
    declared_zones = set(role_map.keys())

    zones_present = {d.get("zone") for d in docs if d.get("zone")}
    zones_skipped_not_present = sorted(
        zid for zid in declared_zones - zones_present if optional_map.get(zid, False)
    )

    if zone is not None:
        docs = [d for d in docs if d.get("zone") == zone]

    query_tokens = _tokenize(query)

    escalation = _resolve_escalation(semantic=semantic, dry_run=dry_run)

    if not docs or not query_tokens:
        return {
            "query": query,
            "zones-searched": sorted(zones_present),
            "zones-skipped-not-present": zones_skipped_not_present,
            "hits": [],
            "escalation": escalation,
        }

    per_doc_tokens, df = _doc_token_counts(docs)
    n = len(docs)

    scored: list[tuple[float, dict[str, Any]]] = []
    for doc, tokens in zip(docs, per_doc_tokens):
        if not tokens:
            continue
        tf_score = 0.0
        token_set = set(tokens)
        for term in query_tokens:
            if term not in token_set:
                continue
            tf = tokens.count(term)
            idf = math.log(1 + (n / max(df.get(term, 1), 1)))
            tf_score += tf * idf
        if tf_score <= 0:
            continue
        role = role_map.get(doc.get("zone") or "", "system")
        boost = ROLE_BOOSTS.get(role, 1.0)
        recency = _recency_boost(doc.get("age_days"))
        final = tf_score * boost * recency
        scored.append((final, doc))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    scored = scored[:top_k]

    summary_chars_per_hit = max(40, token_budget * 4 // max(len(scored), 1)) if scored else 200
    hits = [_hit_from_doc(doc, score, summary_chars_per_hit) for score, doc in scored]

    return {
        "query": query,
        "zones-searched": sorted(zones_present if zone is None else {zone}),
        "zones-skipped-not-present": zones_skipped_not_present,
        "hits": hits,
        "escalation": escalation,
    }


class SemanticNotImplementedError(NotImplementedError):
    """Raised when --semantic is requested without --dry-run.

    The full reformulation path (LLM produces 3 candidate queries; each runs
    mechanically; results merge) is documented in the P2 spec but the LLM
    client wiring is deferred. Until then, --semantic is honest: it accepts
    --dry-run for opt-in validation, and refuses non-dry-run with a clear
    error rather than silently running mechanical search and pretending it
    reformulated.
    """


def _resolve_escalation(*, semantic: bool, dry_run: bool) -> str | None:
    """D-10 strict: only --semantic triggers any LLM-touching path.

    The mechanical search is always the default. There is no auto-trigger on
    0-hit, no fallback, no hidden cost. If the caller passes --semantic
    --dry-run, we record the opt-in but do not fire the LLM. Non-dry-run
    --semantic is deliberately not silently downgraded to mechanical — see
    SemanticNotImplementedError raised by `search()` itself.
    """
    if not semantic:
        return None
    if dry_run:
        return "semantic-dry-run"
    return "semantic-requested"


def _empty_result(query: str, *, semantic: bool, dry_run: bool, reason: str) -> dict[str, Any]:
    return {
        "query": query,
        "zones-searched": [],
        "zones-skipped-not-present": [],
        "hits": [],
        "escalation": _resolve_escalation(semantic=semantic, dry_run=dry_run),
        "warning": reason,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cross-zone mechanical search over context-index.json.")
    p.add_argument("--query", required=True, help="Search query")
    p.add_argument("--zone", default=None, help="Restrict to a single zone id")
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Maximum hits")
    p.add_argument(
        "--token-budget",
        type=int,
        default=DEFAULT_TOKEN_BUDGET,
        help="Aggregate summary token budget across hits",
    )
    p.add_argument("--index", type=Path, default=None, help="Override path to context-index.json")
    p.add_argument(
        "--semantic",
        action="store_true",
        help="Opt into LLM query reformulation (D-10: explicit only; no auto-trigger).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="With --semantic, record the opt-in without firing the LLM.",
    )
    p.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    return p.parse_args(argv)


def _print_human(result: dict[str, Any]) -> None:
    print(f"query: {result['query']}")
    if result.get("warning"):
        print(f"warning: {result['warning']}")
    print(f"zones-searched: {', '.join(result['zones-searched']) or '(none)'}")
    skipped = result.get("zones-skipped-not-present") or []
    if skipped:
        print(f"zones-skipped-not-present: {', '.join(skipped)}")
    if result.get("escalation"):
        print(f"escalation: {result['escalation']}")
    print(f"hits: {len(result['hits'])}")
    for hit in result["hits"]:
        print(
            f"  [{hit['score']:.2f}] {hit['citation-id']:30}  {hit['summary']}"
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = search(
            args.query,
            zone=args.zone,
            top_k=args.top_k,
            token_budget=args.token_budget,
            semantic=args.semantic,
            dry_run=args.dry_run,
            index_path=args.index,
        )
    except SemanticNotImplementedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

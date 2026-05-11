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
from collections import Counter
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
from cross_repo_fetch import (  # noqa: E402
    fetch_sibling_corpora,
    is_local_insufficient,
    load_umbrella_config,
    peek_envelope,
    peek_sibling_corpora,
    peek_strength,
    status_envelope,
)

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

TOKEN_RE = re.compile(r"[a-z0-9]+")

FIELD_WEIGHTS = {
    "title": 8.0,
    "filename": 6.0,
    "path": 5.0,
    "headings": 4.0,
    "meta": 3.0,
    "ownership": 2.5,
    "body": 1.0,
}

TITLE_FIELDS = {"title"}
TITLE_PATH_ENTITY_FIELDS = {"title", "filename", "path", "meta"}
AUTHORITATIVE_FIELDS = {"title", "filename", "path", "headings", "meta", "ownership"}


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    tokens: list[str] = []
    for raw in TOKEN_RE.findall(text.lower()):
        token = _normalize_token(raw)
        if token and token not in STOPWORDS and len(token) >= 2:
            tokens.append(token)
    return tokens


def _normalize_token(token: str) -> str:
    """Conservative lexical normalization for deterministic keyword search."""
    token = token.strip().lower()
    if not token:
        return ""
    # Treat possessive/entity spellings like Arnold's, Arnolds, and Arnold as
    # one term without introducing a full stemming dependency.
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    return token


def _normalized_sequence(text: str) -> str:
    return " ".join(_tokenize(text))


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


def _field_values(doc: dict[str, Any]) -> dict[str, list[str]]:
    path = str(doc.get("path") or "")
    filename = str(doc.get("filename") or "")
    return {
        "title": [str(doc.get("name") or "")],
        "filename": [filename, Path(filename).stem],
        "path": [path, Path(path).stem, *(str(x) for x in doc.get("path_tags") or [])],
        "headings": [str(x) for x in doc.get("headings") or []],
        "meta": [
            str(doc.get("cluster") or ""),
            str(doc.get("type") or ""),
            str(doc.get("page_type") or ""),
            str(doc.get("status") or ""),
            *(str(x) for x in doc.get("tags") or []),
        ],
        "ownership": [
            str(doc.get("domain_statement") or ""),
            *(str(x) for x in doc.get("exclusively_owns") or []),
            *(str(x) for x in doc.get("strictly_avoids") or []),
        ],
        "body": [str(doc.get("first_paragraph") or "")],
    }


def _field_tokens(doc: dict[str, Any]) -> dict[str, list[str]]:
    return {
        field: _tokenize(" ".join(value for value in values if value))
        for field, values in _field_values(doc).items()
    }


def _doc_token_counts(docs: list[dict[str, Any]]) -> tuple[list[dict[str, list[str]]], dict[str, int]]:
    """Return per-doc token lists and inverse-document-frequency counts."""
    per_doc_tokens = [_field_tokens(doc) for doc in docs]
    df: dict[str, int] = {}
    for fields in per_doc_tokens:
        doc_terms = set()
        for tokens in fields.values():
            doc_terms.update(tokens)
        for term in doc_terms:
            df[term] = df.get(term, 0) + 1
    return per_doc_tokens, df


def _flatten_tokens(fields: dict[str, list[str]]) -> list[str]:
    tokens: list[str] = []
    for value in fields.values():
        tokens.extend(value)
    return tokens


def _field_term_set(fields: dict[str, list[str]], field_names: set[str]) -> set[str]:
    terms: set[str] = set()
    for field in field_names:
        terms.update(fields.get(field) or [])
    return terms


def _phrase_matches(query_terms: list[str], fields: dict[str, list[str]]) -> list[str]:
    if len(query_terms) < 2:
        return []
    phrase = " ".join(query_terms)
    matches: list[str] = []
    for field, tokens in fields.items():
        if phrase and phrase in " ".join(tokens):
            matches.append(field)
    return matches


def _score_fields(
    query_terms: list[str],
    fields: dict[str, list[str]],
    df: dict[str, int],
    n: int,
) -> tuple[float, dict[str, float], set[str]]:
    field_scores = {field: 0.0 for field in FIELD_WEIGHTS}
    matched_terms: set[str] = set()
    for field, tokens in fields.items():
        if not tokens:
            continue
        counts = Counter(tokens)
        weight = FIELD_WEIGHTS.get(field, 1.0)
        for term in query_terms:
            tf = counts.get(term, 0)
            if tf <= 0:
                continue
            idf = math.log(1 + (n / max(df.get(term, 1), 1)))
            field_scores[field] += (1.0 + math.log(tf)) * idf * weight
            matched_terms.add(term)

    phrase_fields = _phrase_matches(query_terms, fields)
    if phrase_fields:
        phrase_idf = sum(math.log(1 + (n / max(df.get(term, 1), 1))) for term in query_terms)
        for field in phrase_fields:
            field_scores[field] += phrase_idf * FIELD_WEIGHTS.get(field, 1.0) * 1.5

    return sum(field_scores.values()), field_scores, matched_terms


def _match_tier(query_terms: list[str], fields: dict[str, list[str]], matched_terms: set[str]) -> int:
    query_set = set(query_terms)
    if not query_set:
        return 0
    title_terms = _field_term_set(fields, TITLE_FIELDS)
    title_path_entity_terms = _field_term_set(fields, TITLE_PATH_ENTITY_FIELDS)
    authoritative_terms = _field_term_set(fields, AUTHORITATIVE_FIELDS)
    all_terms = set(_flatten_tokens(fields))
    phrase_fields = set(_phrase_matches(query_terms, fields))

    if query_set.issubset(title_terms) or phrase_fields.intersection(TITLE_FIELDS):
        return 5
    if query_set.issubset(title_path_entity_terms):
        return 4
    if query_set.issubset(all_terms):
        return 3
    coverage = len(matched_terms) / len(query_set)
    if phrase_fields.intersection(AUTHORITATIVE_FIELDS):
        return 2
    if coverage >= 0.5 and bool(matched_terms.intersection(authoritative_terms)):
        return 2
    return 1 if matched_terms else 0


def _score_breakdown(
    *,
    query_terms: list[str],
    fields: dict[str, list[str]],
    field_scores: dict[str, float],
    matched_terms: set[str],
    tier: int,
    lexical_score: float,
    role_boost: float,
    relation_boost: float,
    freshness_boost: float,
    final: float,
) -> dict[str, Any]:
    query_set = set(query_terms)
    return {
        "match-tier": f"T{tier}",
        "matched-terms": sorted(matched_terms),
        "missing-terms": sorted(query_set - matched_terms),
        "field-scores": {
            field: round(score, 4)
            for field, score in field_scores.items()
        },
        "phrase-matches": _phrase_matches(query_terms, fields),
        "coverage": round(len(matched_terms) / max(len(query_set), 1), 4),
        "lexical-score": round(lexical_score, 4),
        "role-boost": round(role_boost, 4),
        "relation-boost": round(relation_boost, 4),
        "freshness-boost": round(freshness_boost, 4),
        "final": round(final, 4),
    }


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
    explanation: dict[str, Any] | None = None,
    *,
    tier: int | None = None,
    coverage: float | None = None,
) -> dict[str, Any]:
    summary, truncated = _summary(doc, summary_chars)
    builds_on = list((doc.get("meta") or {}).get("builds-on") or [])[:3]
    hit = {
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
        # Always emit tier + coverage so cross-repo gate logic can read them
        # without requiring --explain. These are cheap; full breakdown stays
        # behind --explain to avoid polluting normal output.
        "match-tier": f"T{tier}" if tier is not None else None,
        "coverage": coverage,
    }
    if explanation is not None:
        hit["score-breakdown"] = explanation
    return hit


def search(
    query: str,
    *,
    zone: str | None = None,
    top_k: int = DEFAULT_TOP_K,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    semantic: bool = False,
    dry_run: bool = False,
    explain: bool = False,
    index: dict[str, Any] | None = None,
    index_path: Path | None = None,
    cross_repo: bool | None = None,
    repo_root: Path | None = None,
    _disable_cross_repo_recursion: bool = False,
) -> dict[str, Any]:
    """Run a mechanical search and return the structured result envelope.

    `cross_repo`:
      - None  → use `.bcos-umbrella.json.retrieval.auto_fallthrough` (default: off)
      - True  → force on (`--cross-repo`)
      - False → force off (`--no-cross-repo`)

    See `docs/_bcos-framework/architecture/cross-repo-retrieval.md` for the
    full opt-in / fallthrough contract. D-10 strict: never fires implicitly in
    repos without `.bcos-umbrella.json.retrieval.auto_fallthrough: true`.
    """

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

    query_tokens = list(dict.fromkeys(_tokenize(query)))

    escalation = _resolve_escalation(semantic=semantic, dry_run=dry_run)
    searched_zones = sorted({zone} if zone is not None else zones_present)

    if not docs or not query_tokens:
        return {
            "query": query,
            "zones-searched": searched_zones,
            "zones-skipped-not-present": zones_skipped_not_present,
            "hits": [],
            "escalation": escalation,
        }

    per_doc_tokens, df = _doc_token_counts(docs)
    n = len(docs)

    scored: list[tuple[int, float, str, dict[str, Any], dict[str, Any] | None, float]] = []
    query_set_size = max(len(set(query_tokens)), 1)
    for doc, fields in zip(docs, per_doc_tokens):
        tokens = _flatten_tokens(fields)
        if not tokens:
            continue
        lexical_score, field_scores, matched_terms = _score_fields(query_tokens, fields, df, n)
        if lexical_score <= 0:
            continue
        tier = _match_tier(query_tokens, fields, matched_terms)
        if tier <= 0:
            continue
        coverage = round(len(matched_terms) / query_set_size, 4)
        role = role_map.get(doc.get("zone") or "", "system")
        role_boost = ROLE_BOOSTS.get(role, 1.0)
        relation_boost = 0.0
        recency = _recency_boost(doc.get("age_days"))
        final = lexical_score * role_boost * (1.0 + relation_boost) * recency
        explanation = None
        if explain:
            explanation = _score_breakdown(
                query_terms=query_tokens,
                fields=fields,
                field_scores=field_scores,
                matched_terms=matched_terms,
                tier=tier,
                lexical_score=lexical_score,
                role_boost=role_boost,
                relation_boost=relation_boost,
                freshness_boost=recency,
                final=final,
            )
        scored.append((tier, final, _citation_id(doc), doc, explanation, coverage))

    scored.sort(key=lambda pair: (-pair[0], -pair[1], pair[2]))
    scored = scored[:top_k]

    summary_chars_per_hit = max(40, token_budget * 4 // max(len(scored), 1)) if scored else 200
    hits = [
        _hit_from_doc(doc, score, summary_chars_per_hit, explanation, tier=tier, coverage=coverage)
        for tier, score, _citation, doc, explanation, coverage in scored
    ]

    local_result: dict[str, Any] = {
        "query": query,
        "zones-searched": searched_zones,
        "zones-skipped-not-present": zones_skipped_not_present,
        "hits": hits,
        "escalation": escalation,
    }

    if _disable_cross_repo_recursion:
        return local_result

    return _maybe_extend_with_cross_repo(
        local_result,
        query=query,
        zone=zone,
        top_k=top_k,
        token_budget=token_budget,
        explain=explain,
        cross_repo=cross_repo,
        repo_root=repo_root or REPO_ROOT,
        local_tiers_scores=[(tier, score) for tier, score, *_ in scored],
    )


def _maybe_extend_with_cross_repo(
    local_result: dict[str, Any],
    *,
    query: str,
    zone: str | None,
    top_k: int,
    token_budget: int,
    explain: bool,
    cross_repo: bool | None,
    repo_root: Path,
    local_tiers_scores: list[tuple[int, float]],
) -> dict[str, Any]:
    """Three-stage filter for cross-repo retrieval. D-10 strict (mechanical only).

    Hierarchy: local search across all zones in THIS repo always wins.
    Cross-repo is consulted only as last resort.

    Decision tree:
      1. explicit --no-cross-repo            → skip, emit not-attempted
      2. no .bcos-umbrella.json              → skip, no envelope changes
      3. explicit --cross-repo               → bypass peek gate → deep-fetch
      4. not opted-in (no retrieval block)   → skip, emit not-attempted (if present)
      5. local is sufficient                 → skip peek, emit local-sufficient
      6. local insufficient → run peek:
         - peek strong  → deep-fetch (one sibling clearly owns the topic)
         - peek marginal/none → emit cross-repo-suggestions, NO deep-fetch
                                (calling agent decides whether to surface to user)
    """
    cfg = load_umbrella_config(repo_root)

    # Gate 1: explicit --no-cross-repo
    if cross_repo is False:
        if cfg.present:
            local_result["cross-repo-status"] = status_envelope(
                attempted=False, trigger="explicit-no", fetch_result=None,
            )
        return local_result

    # Gate 2: no umbrella file → behave exactly like single-repo
    if not cfg.present:
        return local_result

    # Gate 3: explicit --cross-repo → bypass peek, deep-fetch directly
    if cross_repo is True:
        return _deep_fetch_and_merge(
            local_result, cfg=cfg, trigger="explicit-flag",
            query=query, zone=zone, top_k=top_k, token_budget=token_budget,
            explain=explain, local_tiers_scores=local_tiers_scores,
        )

    # Gate 4: not opted-in (no retrieval block or auto_fallthrough=false)
    if not cfg.retrieval_block_present or not cfg.auto_fallthrough:
        local_result["cross-repo-status"] = status_envelope(
            attempted=False, trigger="not-opted-in", fetch_result=None,
        )
        return local_result

    # Gate 5: local-sufficient → no peek, no deep-fetch
    insufficient, signal = is_local_insufficient(local_result, cfg.miss_signals)
    if not insufficient:
        local_result["cross-repo-status"] = status_envelope(
            attempted=False, trigger="local-sufficient", fetch_result=None,
        )
        return local_result

    # Gate 6: peek → strong/marginal/none
    query_tokens = list(dict.fromkeys(_tokenize(query)))
    peek_result = peek_sibling_corpora(cfg, query_tokens)
    strength, _winner = peek_strength(peek_result, cfg)

    if strength == "strong":
        return _deep_fetch_and_merge(
            local_result, cfg=cfg, trigger="auto-fallthrough",
            query=query, zone=zone, top_k=top_k, token_budget=token_budget,
            explain=explain, local_tiers_scores=local_tiers_scores,
            insufficient_signal=signal,
        )

    # Marginal or none: surface suggestions (if any) but do NOT deep-fetch.
    trigger = "peek-empty" if strength == "none" else "peek-marginal"
    local_result["cross-repo-status"] = status_envelope(
        attempted=False, trigger=trigger, fetch_result=None,
    )
    local_result["cross-repo-status"]["umbrella-id"] = cfg.umbrella_id
    local_result["cross-repo-status"]["local-insufficient-signal"] = signal
    if strength == "marginal":
        local_result["cross-repo-suggestions"] = peek_envelope(peek_result, strength)
    if peek_result.fatal:
        local_result["cross-repo-status"]["fatal"] = peek_result.fatal
    if peek_result.skipped:
        local_result["cross-repo-status"]["siblings-skipped"] = [
            {"id": s.id, "reason": s.reason, **({"detail": s.detail} if s.detail else {})}
            for s in peek_result.skipped
        ]
    return local_result


def _deep_fetch_and_merge(
    local_result: dict[str, Any],
    *,
    cfg,
    trigger: str,
    query: str,
    zone: str | None,
    top_k: int,
    token_budget: int,
    explain: bool,
    local_tiers_scores: list[tuple[int, float]],
    insufficient_signal: str | None = None,
) -> dict[str, Any]:
    """Run the full BM25 ranker against each sibling, merge with local hits."""
    fetch_result = fetch_sibling_corpora(cfg)

    extra_hits: list[tuple[int, float, str, dict[str, Any]]] = []
    for sibling in fetch_result.siblings:
        sibling_result = search(
            query, zone=zone, top_k=top_k, token_budget=token_budget,
            semantic=False, dry_run=False, explain=explain,
            index={"docs": sibling.docs}, cross_repo=False,
            _disable_cross_repo_recursion=True,
        )
        for hit in sibling_result.get("hits") or []:
            original_citation = hit.get("citation-id") or ""
            hit["citation-id"] = f"{sibling.id}:{original_citation}"
            hit["sibling-id"] = sibling.id
            score = hit.get("score") or 0.0
            tier = _tier_from_breakdown(hit) or 1
            extra_hits.append((tier, float(score), hit["citation-id"], hit))

    if extra_hits:
        local_with_tiers: list[tuple[int, float, str, dict[str, Any]]] = []
        for hit, (tier, score) in zip(local_result["hits"], local_tiers_scores):
            local_with_tiers.append((tier, score, hit.get("citation-id") or "", hit))
        combined = local_with_tiers + extra_hits
        combined.sort(key=lambda t: (-t[0], -t[1], t[2]))
        local_result["hits"] = [hit for _t, _s, _c, hit in combined[:top_k]]

    local_result["cross-repo-status"] = status_envelope(
        attempted=True, trigger=trigger, fetch_result=fetch_result,
    )
    if insufficient_signal:
        local_result["cross-repo-status"]["local-insufficient-signal"] = insufficient_signal
    return local_result


def _tier_from_breakdown(hit: dict[str, Any]) -> int | None:
    """Extract tier number from a hit. Prefers the always-present `match-tier`
    field; falls back to the `score-breakdown.match-tier` (only set under
    `--explain`) for compatibility.
    """
    tier_str = hit.get("match-tier")
    if not tier_str:
        breakdown = hit.get("score-breakdown") or {}
        tier_str = breakdown.get("match-tier")
    if not tier_str:
        return None
    try:
        return int(str(tier_str).lstrip("T"))
    except ValueError:
        return None


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
    p.add_argument("--explain", action="store_true", help="Include score breakdowns per hit")
    p.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    cross = p.add_mutually_exclusive_group()
    cross.add_argument(
        "--cross-repo",
        dest="cross_repo",
        action="store_const",
        const=True,
        default=None,
        help=(
            "Force cross-repo fallthrough on for this call. Reads .bcos-umbrella.json "
            "to find sibling repos. Without this flag, fallthrough fires only when "
            ".bcos-umbrella.json.retrieval.auto_fallthrough is true."
        ),
    )
    cross.add_argument(
        "--no-cross-repo",
        dest="cross_repo",
        action="store_const",
        const=False,
        help="Force cross-repo fallthrough off for this call.",
    )
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
    cross = result.get("cross-repo-status")
    if cross:
        attempted = cross.get("attempted")
        trigger = cross.get("trigger", "?")
        if attempted:
            queried = cross.get("siblings-queried") or []
            skipped_siblings = cross.get("siblings-skipped") or []
            fatal = cross.get("fatal")
            print(
                f"cross-repo: {trigger} — queried {len(queried)}, skipped {len(skipped_siblings)}"
                + (f", fatal: {fatal}" if fatal else "")
            )
        else:
            print(f"cross-repo: not-attempted ({trigger})")
    print(f"hits: {len(result['hits'])}")
    for hit in result["hits"]:
        print(
            f"  [{hit['score']:.2f}] {hit['citation-id']:40}  {hit['summary']}"
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
            explain=args.explain,
            index_path=args.index,
            cross_repo=args.cross_repo,
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

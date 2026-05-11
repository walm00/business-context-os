#!/usr/bin/env python3
"""
Cross-repo retrieval fetch helper.

Resolves the umbrella registration in `.bcos-umbrella.json`, reads the umbrella's
`projects.json`, and loads each sibling repo's `.claude/quality/context-index.json`.
Returns a structured payload for `context_search.py` / `context_bundle.py` to merge.

D-10 strict (framework default unchanged): this helper NEVER fires implicitly.
The calling script decides whether to invoke it based on:
  - explicit `--cross-repo` flag, OR
  - `.bcos-umbrella.json.retrieval.auto_fallthrough: true` (per-portfolio opt-in)

Contract: see `docs/_bcos-framework/architecture/cross-repo-retrieval.md`.

Errors never raise. Every failure becomes a per-sibling skip with a typed reason.
The local search/bundle result is always returned; cross-repo is purely additive.

Usage:
    from cross_repo_fetch import (
        load_umbrella_config, fetch_sibling_corpora, should_fall_through
    )

    cfg = load_umbrella_config(REPO_ROOT)
    if cfg.auto_fallthrough:
        result = fetch_sibling_corpora(cfg, cap=cfg.max_sibling_hops,
                                        per_sibling_timeout_ms=1000)
        for sibling in result.siblings:
            ... # run ranker against sibling.docs, prefix citations with sibling.id
"""

from __future__ import annotations

import fnmatch
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED_PROJECTS_SCHEMA_VERSIONS = {1}
SUPPORTED_UMBRELLA_SCHEMA_VERSIONS = {1}

# Cross-repo peek fires when ANY signal in this list applies to the local result.
# Defaults to ['zero-hit', 'low-coverage']: peek when local has nothing OR when
# local has hits but doesn't cover all query terms. Other valid signals:
# 'low-tier' (top hit T2 or below) and 'unsatisfied-zone-requirements' (bundle).
DEFAULT_MISS_SIGNALS = ["zero-hit", "low-coverage"]

DEFAULT_MAX_SIBLING_HOPS = 5
DEFAULT_PER_SIBLING_TIMEOUT_MS = 1000

# Peek strength thresholds. A peek is "strong" when exactly one sibling has at
# least `min_strong_matches` docs with any authoritative-field match AND at
# most `max_strong_rivals` other siblings have any authoritative match.
#
# Default (min=1, rivals=0): one sibling cleanly owning the topic with no rival
# is a strong signal — auto-fetch. Multiple siblings competing → marginal,
# surface as a suggestion. Tune per portfolio if defaults are too aggressive.
DEFAULT_PEEK_MIN_STRONG_MATCHES = 1
DEFAULT_PEEK_MAX_STRONG_RIVALS = 0

# Fields scanned by the peek. Split into "authoritative" (strongest signals of
# topic ownership) and "supporting" (still informative, but weaker).
PEEK_AUTHORITATIVE_FIELDS = ("name", "filename", "exclusively_owns", "page_type")
PEEK_SUPPORTING_FIELDS = ("tags", "headings", "cluster")


@dataclass
class UmbrellaConfig:
    """Parsed view of the local repo's .bcos-umbrella.json."""

    present: bool
    umbrella_id: str | None = None
    umbrella_path: Path | None = None
    node_id: str | None = None
    node_role: str | None = None
    extra_exposes: list[str] = field(default_factory=list)
    retrieval_block_present: bool = False
    auto_fallthrough: bool = False
    miss_signals: list[str] = field(default_factory=lambda: list(DEFAULT_MISS_SIGNALS))
    max_sibling_hops: int = DEFAULT_MAX_SIBLING_HOPS
    per_sibling_timeout_ms: int = DEFAULT_PER_SIBLING_TIMEOUT_MS
    peek_min_strong_matches: int = DEFAULT_PEEK_MIN_STRONG_MATCHES
    peek_max_strong_rivals: int = DEFAULT_PEEK_MAX_STRONG_RIVALS
    load_error: str | None = None


@dataclass
class SiblingPeek:
    """One sibling's metadata-only peek result for a query.

    Holds enough info for the calling agent to decide whether to deep-fetch
    or surface as a suggestion. NOT a ranked hit list — see SiblingCorpus
    for the deep-fetch payload.
    """

    id: str
    match_count: int                  # total matching docs across all peek fields
    authoritative_match_count: int    # subset: matches in authoritative fields
    top_citations: list[str]          # up to 3 citation-ids, prefixed with sibling-id
    reasons: list[str]                # heuristic labels ("title-match", "tag-match", ...)


@dataclass
class PeekResult:
    """Aggregate peek output across all siblings."""

    umbrella_id: str | None
    siblings: list[SiblingPeek] = field(default_factory=list)
    skipped: list["SiblingSkip"] = field(default_factory=list)
    fatal: str | None = None


@dataclass
class SiblingCorpus:
    """One sibling's filtered context-index corpus, ready for ranking."""

    id: str
    path: Path
    docs: list[dict[str, Any]]
    took_ms: int


@dataclass
class SiblingSkip:
    """One sibling we couldn't query, with a typed reason."""

    id: str | None
    reason: str
    detail: str = ""


@dataclass
class FetchResult:
    """Aggregate result returned to the caller (search/bundle)."""

    umbrella_id: str | None
    siblings: list[SiblingCorpus] = field(default_factory=list)
    skipped: list[SiblingSkip] = field(default_factory=list)
    fatal: str | None = None


def load_umbrella_config(repo_root: Path) -> UmbrellaConfig:
    """Read `.bcos-umbrella.json` from `repo_root`. Never raises.

    Returns UmbrellaConfig with `present=False` if the file is absent or
    cannot be parsed. The caller checks `present` (and optionally `load_error`)
    before any cross-repo work.
    """
    umbrella_file = repo_root / ".bcos-umbrella.json"
    if not umbrella_file.is_file():
        return UmbrellaConfig(present=False)

    try:
        data = json.loads(umbrella_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return UmbrellaConfig(
            present=False,
            load_error=f"{type(exc).__name__}: {exc}",
        )

    schema = data.get("schemaVersion")
    if schema not in SUPPORTED_UMBRELLA_SCHEMA_VERSIONS:
        return UmbrellaConfig(
            present=False,
            load_error=f"unsupported umbrella schemaVersion: {schema!r}",
        )

    umbrella_block = data.get("umbrella") or {}
    node_block = data.get("node") or {}
    shared_block = data.get("shared_context") or {}
    retrieval_block = data.get("retrieval") or {}

    umbrella_path_str = umbrella_block.get("path")
    umbrella_path = (repo_root / umbrella_path_str).resolve() if umbrella_path_str else None

    extra_exposes = [str(x) for x in (shared_block.get("extra_exposes") or [])]

    miss_signals = retrieval_block.get("miss_signals")
    if not isinstance(miss_signals, list) or not miss_signals:
        miss_signals = list(DEFAULT_MISS_SIGNALS)
    else:
        miss_signals = [str(s) for s in miss_signals]

    max_hops = retrieval_block.get("max_sibling_hops", DEFAULT_MAX_SIBLING_HOPS)
    try:
        max_hops = int(max_hops)
    except (TypeError, ValueError):
        max_hops = DEFAULT_MAX_SIBLING_HOPS
    if max_hops < 0:
        max_hops = 0

    timeout = retrieval_block.get("per_sibling_timeout_ms", DEFAULT_PER_SIBLING_TIMEOUT_MS)
    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        timeout = DEFAULT_PER_SIBLING_TIMEOUT_MS
    if timeout < 0:
        timeout = DEFAULT_PER_SIBLING_TIMEOUT_MS

    min_strong = retrieval_block.get("peek_min_strong_matches", DEFAULT_PEEK_MIN_STRONG_MATCHES)
    try:
        min_strong = int(min_strong)
    except (TypeError, ValueError):
        min_strong = DEFAULT_PEEK_MIN_STRONG_MATCHES
    if min_strong < 1:
        min_strong = 1

    max_rivals = retrieval_block.get("peek_max_strong_rivals", DEFAULT_PEEK_MAX_STRONG_RIVALS)
    try:
        max_rivals = int(max_rivals)
    except (TypeError, ValueError):
        max_rivals = DEFAULT_PEEK_MAX_STRONG_RIVALS
    if max_rivals < 0:
        max_rivals = 0

    return UmbrellaConfig(
        present=True,
        umbrella_id=umbrella_block.get("id"),
        umbrella_path=umbrella_path,
        node_id=node_block.get("id"),
        node_role=node_block.get("role"),
        extra_exposes=extra_exposes,
        retrieval_block_present=bool(data.get("retrieval")),
        auto_fallthrough=bool(retrieval_block.get("auto_fallthrough", False)),
        miss_signals=miss_signals,
        max_sibling_hops=max_hops,
        per_sibling_timeout_ms=timeout,
        peek_min_strong_matches=min_strong,
        peek_max_strong_rivals=max_rivals,
    )


def should_fall_through(
    *,
    cfg: UmbrellaConfig,
    local_result: dict[str, Any],
    explicit_flag: bool | None,
) -> tuple[bool, str]:
    """Decide whether to invoke cross-repo fallthrough.

    Returns (should, trigger-label).

    `explicit_flag`:
      - True  → force on (`--cross-repo`)
      - False → force off (`--no-cross-repo`)
      - None  → use config

    Rules (in order):
      1. explicit_flag is False                       → (False, "explicit-no")
      2. .bcos-umbrella.json absent                   → (False, "no-umbrella-file")
      3. explicit_flag is True                        → (True, "explicit-flag")
      4. retrieval block absent / auto_fallthrough False → (False, "not-opted-in")
      5. local result does NOT meet miss signals      → (False, "local-not-miss")
      6. local result meets miss signals              → (True, "auto-fallthrough")
    """
    if explicit_flag is False:
        return False, "explicit-no"
    if not cfg.present:
        return False, "no-umbrella-file"
    if explicit_flag is True:
        return True, "explicit-flag"
    if not cfg.retrieval_block_present or not cfg.auto_fallthrough:
        return False, "not-opted-in"
    if not _meets_miss_signals(local_result, cfg.miss_signals):
        return False, "local-not-miss"
    return True, "auto-fallthrough"


def is_local_insufficient(
    local_result: dict[str, Any],
    signals: list[str],
) -> tuple[bool, str]:
    """Public wrapper around miss-signal evaluation.

    Returns (insufficient, first_signal_that_fired). When no signal fires,
    returns (False, "local-sufficient"). Used by the cross-repo gate to
    decide whether to peek at siblings.

    Signals are OR-ed: if ANY signal in `signals` applies, the local result
    is considered insufficient. Rationale: the user's portfolio intent is
    "this task really needs something thats missing here" — even partial
    local coverage should be augmentable from siblings.
    """
    for signal in signals:
        if _evaluate_signal(signal, local_result):
            return True, signal
    return False, "local-sufficient"


def _meets_miss_signals(local_result: dict[str, Any], signals: list[str]) -> bool:
    """Compatibility wrapper. See `is_local_insufficient` for the canonical API."""
    insufficient, _ = is_local_insufficient(local_result, signals)
    return insufficient


def _evaluate_signal(signal: str, local_result: dict[str, Any]) -> bool:
    """Return True iff `signal` applies to `local_result`.

    Reads from always-present hit fields (`match-tier`, `coverage`) for
    tier/coverage signals. Does not require --explain. Unknown signals
    return False (forward-compatible).
    """
    hits = local_result.get("hits") or []
    if signal == "zero-hit":
        return not hits
    if signal == "unsatisfied-zone-requirements":
        return bool(local_result.get("unsatisfied-zone-requirements") or [])
    if signal == "low-tier":
        if not hits:
            return False  # handled by zero-hit
        top = hits[0]
        tier_str = top.get("match-tier") or (top.get("score-breakdown") or {}).get("match-tier")
        if not tier_str:
            return False
        try:
            return int(str(tier_str).lstrip("T")) <= 2
        except ValueError:
            return False
    if signal == "low-coverage":
        if not hits:
            return False  # handled by zero-hit
        top = hits[0]
        coverage = top.get("coverage")
        if coverage is None:
            coverage = (top.get("score-breakdown") or {}).get("coverage")
        if coverage is None:
            return False
        return coverage < 1.0
    return False


def fetch_sibling_corpora(
    cfg: UmbrellaConfig,
    *,
    cap: int | None = None,
    per_sibling_timeout_ms: int | None = None,
) -> FetchResult:
    """Resolve umbrella, read projects.json, load each sibling's context-index.

    Never raises. Per-sibling failures become entries in `result.skipped`.
    Umbrella-level failures (path missing, projects.json malformed) become
    `result.fatal` and `result.siblings` is empty.

    Args:
      cfg: parsed UmbrellaConfig (from load_umbrella_config).
      cap: max number of siblings to load. Defaults to cfg.max_sibling_hops.
      per_sibling_timeout_ms: per-sibling wall-time budget. Defaults to
        cfg.per_sibling_timeout_ms.
    """
    cap = cap if cap is not None else cfg.max_sibling_hops
    timeout_ms = per_sibling_timeout_ms if per_sibling_timeout_ms is not None else cfg.per_sibling_timeout_ms

    result = FetchResult(umbrella_id=cfg.umbrella_id)

    if not cfg.present:
        result.fatal = "no-umbrella-file"
        return result

    if cfg.umbrella_path is None:
        result.fatal = "no-umbrella-path"
        return result

    umbrella_root = cfg.umbrella_path
    if not umbrella_root.is_dir():
        result.fatal = f"unreachable:{umbrella_root}"
        return result

    projects_file = umbrella_root / "projects.json"
    if not projects_file.is_file():
        result.fatal = f"projects.json-missing:{projects_file}"
        return result

    try:
        projects_data = json.loads(projects_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        result.fatal = f"projects.json-malformed: {type(exc).__name__}: {exc}"
        return result

    schema = projects_data.get("schemaVersion")
    if schema not in SUPPORTED_PROJECTS_SCHEMA_VERSIONS:
        result.fatal = f"unsupported-schema-version:{schema!r}"
        return result

    projects = projects_data.get("projects") or []
    if not isinstance(projects, list):
        result.fatal = "projects.json-malformed:projects-not-list"
        return result

    loaded = 0
    for project in projects:
        if not isinstance(project, dict):
            result.skipped.append(SiblingSkip(id=None, reason="malformed-project-entry"))
            continue

        project_id = project.get("id")
        if not project_id:
            result.skipped.append(SiblingSkip(id=None, reason="missing-id"))
            continue

        if project_id == cfg.node_id:
            # Skip self — never query our own corpus as a sibling.
            continue

        if loaded >= cap:
            result.skipped.append(SiblingSkip(id=project_id, reason="hop-cap-exceeded"))
            continue

        project_path_str = project.get("path")
        if not project_path_str:
            result.skipped.append(SiblingSkip(id=project_id, reason="missing-path"))
            continue

        sibling_root = (umbrella_root / project_path_str).resolve()
        if not sibling_root.is_dir():
            result.skipped.append(SiblingSkip(id=project_id, reason="unreachable", detail=str(sibling_root)))
            continue

        corpus = _load_sibling_corpus(
            sibling_id=project_id,
            sibling_root=sibling_root,
            exposes=list(project.get("exposes") or []),
            extra_exposes_per_sibling=cfg.extra_exposes if project_id == cfg.node_id else [],
            timeout_ms=timeout_ms,
        )

        if isinstance(corpus, SiblingSkip):
            result.skipped.append(corpus)
        else:
            result.siblings.append(corpus)
            loaded += 1

    return result


def _load_sibling_corpus(
    *,
    sibling_id: str,
    sibling_root: Path,
    exposes: list[str],
    extra_exposes_per_sibling: list[str],
    timeout_ms: int,
) -> SiblingCorpus | SiblingSkip:
    """Read one sibling's context-index.json, filter by exposes, time-bounded.

    Returns SiblingCorpus on success, SiblingSkip on any failure.
    """
    started = time.monotonic()
    index_path = sibling_root / ".claude" / "quality" / "context-index.json"
    if not index_path.is_file():
        return SiblingSkip(id=sibling_id, reason="no-index", detail=str(index_path))

    try:
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return SiblingSkip(
            id=sibling_id,
            reason="malformed-index",
            detail=f"{type(exc).__name__}: {exc}",
        )

    docs = index_data.get("docs") or []
    if not isinstance(docs, list):
        return SiblingSkip(id=sibling_id, reason="malformed-index", detail="docs-not-list")

    # Merge per-project exposes with this-sibling-side extra_exposes (rare).
    all_exposes = list(exposes) + list(extra_exposes_per_sibling)

    if all_exposes:
        filtered = _filter_by_exposes(docs, all_exposes)
        if not filtered:
            return SiblingSkip(id=sibling_id, reason="exposes-empty")
    else:
        filtered = docs

    took_ms = int((time.monotonic() - started) * 1000)
    if took_ms > timeout_ms:
        return SiblingSkip(
            id=sibling_id,
            reason="timeout",
            detail=f"took {took_ms}ms > budget {timeout_ms}ms",
        )

    return SiblingCorpus(id=sibling_id, path=sibling_root, docs=filtered, took_ms=took_ms)


def _filter_by_exposes(docs: list[dict[str, Any]], exposes: list[str]) -> list[dict[str, Any]]:
    """Return docs whose `path` matches any glob in `exposes`.

    Globs are matched with fnmatch against the doc's `path` field (the index's
    canonical doc-path under the sibling repo root).
    """
    out: list[dict[str, Any]] = []
    for doc in docs:
        path = doc.get("path") or ""
        if not path:
            continue
        for pattern in exposes:
            if fnmatch.fnmatch(path, pattern):
                out.append(doc)
                break
    return out


# ---------------------------------------------------------------------------
# Peek (cheap metadata-only scan, no BM25)
# ---------------------------------------------------------------------------


def peek_sibling_corpora(
    cfg: UmbrellaConfig,
    query_tokens: list[str],
    *,
    cap: int | None = None,
    per_sibling_timeout_ms: int | None = None,
) -> PeekResult:
    """Cheap metadata-only scan across siblings. No BM25, no body text, no LLM.

    For each sibling, walk their context-index.json docs and count how many
    have ANY query token in any of the configured peek fields. Split counts
    into 'authoritative' (title / filename / exclusively_owns / page_type)
    vs 'supporting' (tags / headings / cluster). Return a SiblingPeek per
    sibling with match counts + top-3 citations + heuristic reasons.

    Never raises. Per-sibling I/O failures become typed SiblingSkip entries.
    The umbrella-level failure modes mirror fetch_sibling_corpora.
    """
    cap = cap if cap is not None else cfg.max_sibling_hops
    timeout_ms = per_sibling_timeout_ms if per_sibling_timeout_ms is not None else cfg.per_sibling_timeout_ms

    result = PeekResult(umbrella_id=cfg.umbrella_id)

    if not cfg.present:
        result.fatal = "no-umbrella-file"
        return result
    if cfg.umbrella_path is None:
        result.fatal = "no-umbrella-path"
        return result

    umbrella_root = cfg.umbrella_path
    if not umbrella_root.is_dir():
        result.fatal = f"unreachable:{umbrella_root}"
        return result

    projects_file = umbrella_root / "projects.json"
    if not projects_file.is_file():
        result.fatal = f"projects.json-missing:{projects_file}"
        return result

    try:
        projects_data = json.loads(projects_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        result.fatal = f"projects.json-malformed: {type(exc).__name__}: {exc}"
        return result

    schema = projects_data.get("schemaVersion")
    if schema not in SUPPORTED_PROJECTS_SCHEMA_VERSIONS:
        result.fatal = f"unsupported-schema-version:{schema!r}"
        return result

    projects = projects_data.get("projects") or []
    if not isinstance(projects, list):
        result.fatal = "projects.json-malformed:projects-not-list"
        return result

    # Normalize query tokens once.
    qset = {t.lower() for t in query_tokens if t}
    if not qset:
        return result  # nothing to peek for

    loaded = 0
    for project in projects:
        if not isinstance(project, dict):
            result.skipped.append(SiblingSkip(id=None, reason="malformed-project-entry"))
            continue
        project_id = project.get("id")
        if not project_id:
            result.skipped.append(SiblingSkip(id=None, reason="missing-id"))
            continue
        if project_id == cfg.node_id:
            continue  # skip self
        if loaded >= cap:
            result.skipped.append(SiblingSkip(id=project_id, reason="hop-cap-exceeded"))
            continue
        project_path_str = project.get("path")
        if not project_path_str:
            result.skipped.append(SiblingSkip(id=project_id, reason="missing-path"))
            continue
        sibling_root = (umbrella_root / project_path_str).resolve()
        if not sibling_root.is_dir():
            result.skipped.append(SiblingSkip(id=project_id, reason="unreachable", detail=str(sibling_root)))
            continue

        peek = _peek_one_sibling(
            sibling_id=project_id,
            sibling_root=sibling_root,
            exposes=list(project.get("exposes") or []),
            qset=qset,
            timeout_ms=timeout_ms,
        )
        if isinstance(peek, SiblingSkip):
            result.skipped.append(peek)
        else:
            result.siblings.append(peek)
            loaded += 1

    return result


def _peek_one_sibling(
    *,
    sibling_id: str,
    sibling_root: Path,
    exposes: list[str],
    qset: set[str],
    timeout_ms: int,
) -> SiblingPeek | SiblingSkip:
    """Read one sibling's context-index.json and tally metadata matches. Never raises."""
    started = time.monotonic()
    index_path = sibling_root / ".claude" / "quality" / "context-index.json"
    if not index_path.is_file():
        return SiblingSkip(id=sibling_id, reason="no-index", detail=str(index_path))

    try:
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return SiblingSkip(
            id=sibling_id, reason="malformed-index",
            detail=f"{type(exc).__name__}: {exc}",
        )

    docs = index_data.get("docs") or []
    if not isinstance(docs, list):
        return SiblingSkip(id=sibling_id, reason="malformed-index", detail="docs-not-list")

    if exposes:
        docs = _filter_by_exposes(docs, exposes)

    # Per-doc: which query tokens hit which fields?
    doc_hits: list[tuple[dict[str, Any], int, set[str]]] = []
    # (doc, authoritative_hit_count, reasons_set)
    for doc in docs:
        auth_hits, supp_hits, reasons = _count_metadata_matches(doc, qset)
        if auth_hits + supp_hits == 0:
            continue
        # Sort key: authoritative matches first, then total matches
        doc_hits.append((doc, auth_hits, reasons))

    if not doc_hits:
        # No matches at all — still return a SiblingPeek with zero counts so
        # peek_strength can distinguish "queried but empty" from "couldn't query".
        took_ms = int((time.monotonic() - started) * 1000)
        if took_ms > timeout_ms:
            return SiblingSkip(id=sibling_id, reason="timeout", detail=f"took {took_ms}ms")
        return SiblingPeek(
            id=sibling_id, match_count=0, authoritative_match_count=0,
            top_citations=[], reasons=[],
        )

    # Rank: authoritative matches first, then total matches, then path stability
    doc_hits.sort(key=lambda t: (-t[1], -(t[1] + len(t[2])), (t[0].get("path") or "")))

    top_citations = [_peek_citation_id(sibling_id, d) for d, _, _ in doc_hits[:3]]
    all_reasons: list[str] = []
    seen_reasons: set[str] = set()
    for _doc, _auth, reasons in doc_hits:
        for r in sorted(reasons):
            if r not in seen_reasons:
                seen_reasons.add(r)
                all_reasons.append(r)

    auth_total = sum(1 for _, a, _ in doc_hits if a > 0)

    took_ms = int((time.monotonic() - started) * 1000)
    if took_ms > timeout_ms:
        return SiblingSkip(id=sibling_id, reason="timeout", detail=f"took {took_ms}ms")

    return SiblingPeek(
        id=sibling_id,
        match_count=len(doc_hits),
        authoritative_match_count=auth_total,
        top_citations=top_citations,
        reasons=all_reasons,
    )


def _count_metadata_matches(
    doc: dict[str, Any],
    qset: set[str],
) -> tuple[int, int, set[str]]:
    """Count how many query tokens hit authoritative vs supporting fields.

    Returns (authoritative_count, supporting_count, reasons_set).
    """
    auth_hits = 0
    supp_hits = 0
    reasons: set[str] = set()

    for field in PEEK_AUTHORITATIVE_FIELDS:
        if _field_contains_any_token(doc, field, qset):
            auth_hits += 1
            reasons.add(f"{field}-match")
    for field in PEEK_SUPPORTING_FIELDS:
        if _field_contains_any_token(doc, field, qset):
            supp_hits += 1
            reasons.add(f"{field}-match")

    return auth_hits, supp_hits, reasons


def _field_contains_any_token(doc: dict[str, Any], field: str, qset: set[str]) -> bool:
    """True iff any token in qset appears (as a substring) in the doc's `field`."""
    value = doc.get(field)
    if value is None:
        return False
    if isinstance(value, str):
        haystack = value.lower()
        return any(t in haystack for t in qset)
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and any(t in item.lower() for t in qset):
                return True
        return False
    return False


def _peek_citation_id(sibling_id: str, doc: dict[str, Any]) -> str:
    """Build `<sibling-id>:<zone>:<slug>` citation for a peek result."""
    zone = doc.get("zone") or "unknown"
    path = (doc.get("path") or "").replace("\\", "/")
    rel = path[len("docs/"):] if path.startswith("docs/") else path
    if rel.startswith("_") and "/" in rel:
        rel = rel.split("/", 1)[1]
    if rel.endswith(".md"):
        rel = rel[:-3]
    if not rel:
        rel = (doc.get("filename") or "").rsplit(".", 1)[0]
    return f"{sibling_id}:{zone}:{rel}"


def peek_strength(
    peek_result: PeekResult,
    cfg: UmbrellaConfig,
) -> tuple[str, str | None]:
    """Classify a peek result as 'strong' / 'marginal' / 'none'.

    Returns (label, winner_sibling_id_or_None). The winner is set only on
    'strong': it's the sibling-id that triggered the deep-fetch decision.

    Strong = exactly one sibling has >= cfg.peek_min_strong_matches in
             authoritative fields AND at most cfg.peek_max_strong_rivals
             OTHER siblings have any authoritative match.
    Marginal = at least one sibling has >=1 match (any field) but doesn't
               meet strong.
    None = no sibling has any match at all.
    """
    siblings = peek_result.siblings
    if not siblings:
        return "none", None

    any_matches = [s for s in siblings if s.match_count > 0]
    if not any_matches:
        return "none", None

    # Strong candidates: enough authoritative matches.
    strong_candidates = [
        s for s in any_matches
        if s.authoritative_match_count >= cfg.peek_min_strong_matches
    ]
    rivals_with_authority = [s for s in any_matches if s.authoritative_match_count > 0]

    if len(strong_candidates) == 1:
        winner = strong_candidates[0]
        other_authority_count = sum(
            1 for s in rivals_with_authority if s.id != winner.id
        )
        if other_authority_count <= cfg.peek_max_strong_rivals:
            return "strong", winner.id

    return "marginal", None


def peek_envelope(peek_result: PeekResult, strength: str) -> dict[str, Any]:
    """Build the `cross-repo-suggestions` envelope block for marginal/ambiguous peeks."""
    return {
        "peek-strength": strength,
        "suggestions": [
            {
                "sibling-id": s.id,
                "match-count": s.match_count,
                "authoritative-match-count": s.authoritative_match_count,
                "top-citations": s.top_citations,
                "reasons": s.reasons,
            }
            for s in peek_result.siblings
            if s.match_count > 0
        ],
        "siblings-skipped": [
            {"id": s.id, "reason": s.reason, **({"detail": s.detail} if s.detail else {})}
            for s in peek_result.skipped
        ],
    }


# ---------------------------------------------------------------------------
# Status envelope (existing)
# ---------------------------------------------------------------------------


def status_envelope(
    *,
    attempted: bool,
    trigger: str,
    fetch_result: FetchResult | None,
) -> dict[str, Any]:
    """Build the `cross-repo-status` block for the search/bundle envelope."""
    envelope: dict[str, Any] = {
        "attempted": attempted,
        "trigger": trigger,
    }
    if fetch_result is None:
        return envelope

    envelope["umbrella-id"] = fetch_result.umbrella_id
    envelope["siblings-queried"] = [
        {"id": s.id, "hits": len(s.docs), "took-ms": s.took_ms}
        for s in fetch_result.siblings
    ]
    envelope["siblings-skipped"] = [
        {"id": s.id, "reason": s.reason, **({"detail": s.detail} if s.detail else {})}
        for s in fetch_result.skipped
    ]
    if fetch_result.fatal:
        envelope["fatal"] = fetch_result.fatal
    return envelope

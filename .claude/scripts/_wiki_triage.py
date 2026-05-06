#!/usr/bin/env python3
"""
Ingest-time 4-class triage detector for wiki pages (schema 1.2).

When a new wiki page is written (or an existing one materially changed) the
ingest pipeline (Step 7.5 in `bcos-wiki/ingest.md`) calls `classify()` to
mechanically detect four kinds of conflict:

  Class A — authority-asymmetry
      The new page contains a fact that contradicts a fact in its
      `builds-on:` canonical doc. The wiki page is `external-reference` (or
      `internal-reference`); the canonical doc owns the truth.
      Action: auto-annotate the wiki page; emit a digest finding for canonical-
      side review. Wiki-side only — never touches `docs/*.md`.

  Class B — temporal-supersession-candidate
      Two pages in the same cluster cite the same `source-url` with different
      `source-published` (or `last-fetched` as proxy when source-published is
      absent). They are the same source captured at different points in time.
      Action: write supersedes/superseded-by links bidirectionally. No callout.

  Class C — true-contradiction
      Two pages with `authority: canonical-process` in the same cluster, both
      within `review-cadence-days`, contain conflicting facts at the same key.
      Action: caller MUST interrupt the user with AskUserQuestion. Highest-
      severity class.

  Class D — canonical-drift-suggestion
      The new external-reference page contains a value that diverges from its
      builds-on canonical target, AND the canonical target's `last-updated` is
      older than `STALE_CANONICAL_DAYS`. Action: emit info finding to morning
      digest suggesting the canonical doc may need review.

Mechanical-first per D-09: no LLM call in the detection path. Pure
frontmatter + token-set comparison + date arithmetic.

Public API
----------
    classify(new_page, root, strict=False)         -> list[TriageFinding]
    write_supersedes_link(successor, predecessor_slug, root)  -> None
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _wiki_yaml import apply_frontmatter, parse_frontmatter  # noqa: E402

# ---------------------------------------------------------------------------
# Tuning constants — see references/triage-confidence.md (P3_004)
# ---------------------------------------------------------------------------

# Class D: canonical doc considered "stale" once its last-updated is older
# than this many days. 180 ≈ 6 months.
STALE_CANONICAL_DAYS = 180

# Class C: only fires if both pages were last reviewed within this window.
# Beyond that, the older page is suspect on its own (separately surfaced by
# `wiki-graveyard` job) and should not block ingest of a fresher page.
DEFAULT_REVIEW_CADENCE_DAYS = 180

# Cross-cluster confidence multiplier when --strict is used.
STRICT_CROSS_CLUSTER_MULTIPLIER = 0.7

# Auto-apply confidence threshold (Class B auto-link) — D-06.
AUTO_APPLY_CONFIDENCE = 0.85

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Numeric-fact tokenization: extract numbers attached to a unit/keyword (rates,
# durations, prices, percentages). Skips bare numbers in numbered lists, dates,
# and section anchors. The capture preserves the unit so "10 minutes" and
# "2 minutes" are distinct tokens (not just "10" / "2").
_NUMERIC_FACT_RE = re.compile(
    r"(?:\$\s*\d+(?:[.,]\d+)*"           # $1234.56 / $1,234
    r"|\d+(?:\.\d+)?\s*%"                # 12% / 12.5%
    r"|\d+(?:\.\d+)?\s*¢"                # 30¢
    r"|\d+(?:\.\d+)?\s*[a-z]+"           # 10 minutes / 30k / 500ms
    r")",
    re.IGNORECASE,
)
# Strip numbered-list bullets so "1. Run make" doesn't contribute "1" as a fact.
_NUMBERED_LIST_RE = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "of", "in", "on", "to",
    "for", "with", "by", "and", "or", "not", "this", "that", "these", "those",
    "it", "its", "as", "at", "from", "but", "if", "we", "i", "do", "does",
    "did", "will", "would", "can", "could", "should", "may", "might", "must",
    "have", "has", "had", "our", "us", "you", "your", "they", "them", "their",
})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TriageFinding:
    """One finding from the triage classifier.

    Attributes
    ----------
    klass : "A" | "B" | "C" | "D"
        Triage class per `wiki-zone.md` "Triage classes" table.
    confidence : float
        0.0–1.0; weighted blend per `references/triage-confidence.md`.
    related_pages : list[Path]
        Other wiki pages or canonical docs referenced by this finding.
    finding_attrs : dict
        Stable shape per `typed-events.md` for the corresponding finding type.
    auto_action : str | None
        Set when the finding is safely auto-appliable (e.g., "supersession-link"
        for Class B with confidence ≥ AUTO_APPLY_CONFIDENCE). The caller decides
        whether to apply.
    """

    klass: str
    confidence: float
    related_pages: list[Path] = field(default_factory=list)
    finding_attrs: dict[str, Any] = field(default_factory=dict)
    auto_action: str | None = None


# ---------------------------------------------------------------------------
# Helpers — frontmatter + path
# ---------------------------------------------------------------------------

def _wiki_pages_under(root: Path) -> list[Path]:
    base = root / "docs" / "_wiki"
    out: list[Path] = []
    for sub in ("pages", "source-summary"):
        d = base / sub
        if d.is_dir():
            out.extend(sorted(d.glob("*.md")))
    return out


def _read_meta(path: Path) -> dict:
    return parse_frontmatter(path) or {}


def _slug(p: Path) -> str:
    return p.stem


# Mechanical default mapping — must stay in lockstep with
# wiki_schema.py::_derive_authority_default and the hook's mirror.
_CANONICAL_PROCESS_TYPES = {"how-to", "runbook", "decision-log", "post-mortem"}
_INTERNAL_REFERENCE_TYPES = {"glossary", "faq"}


def _effective_authority(page_path: Path, meta: dict) -> str:
    """Return declared `authority` or the mechanical default derived from
    path + page-type. Triage uses this so pages predating the 1.1 -> 1.2
    migration still classify correctly."""
    declared = (meta.get("authority") or "").strip()
    if declared:
        return declared
    folder = page_path.parent.name
    page_type = (meta.get("page-type") or "").strip()
    if folder == "source-summary":
        return "external-reference"
    if folder == "pages":
        if page_type in _CANONICAL_PROCESS_TYPES:
            return "canonical-process"
        if page_type in _INTERNAL_REFERENCE_TYPES:
            return "internal-reference"
        return "internal-reference"
    return "external-reference"


def _parse_date(s: str | None) -> date | None:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not _DATE_RE.match(s):
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _temporal_signal(meta: dict) -> date | None:
    """Best-available 'when was this published?' signal.

    Prefers `source-published` (added in 1.2). Falls back to `last-fetched`
    for source-summary pages, then to `created`.
    """
    return (
        _parse_date(meta.get("source-published"))
        or _parse_date(meta.get("last-fetched"))
        or _parse_date(meta.get("created"))
    )


def _resolve_builds_on(new_page_path: Path, builds_on: list, root: Path) -> list[Path]:
    """Resolve relative `builds-on:` paths from the page's frontmatter to absolute paths."""
    out: list[Path] = []
    if not builds_on:
        return out
    parent = new_page_path.parent
    for entry in builds_on:
        s = str(entry).strip()
        if not s:
            continue
        candidate = (parent / s).resolve()
        if candidate.is_file():
            out.append(candidate)
    return out


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    return text[end + len("\n---"):].lstrip("\n")


def _numeric_tokens(text: str) -> set[str]:
    """Pull number-with-unit tokens from a body — these are the most reliable
    contradiction signals (rates, prices, durations, percentages).

    Numbered list bullets (`1. step`, `2. step`) are stripped first so they
    don't pollute the fact set with bare ordinals.
    """
    cleaned = _NUMBERED_LIST_RE.sub("", text)
    # Normalize whitespace inside numeric-fact tokens so "10 minutes" and
    # "10  minutes" produce the same key.
    return {re.sub(r"\s+", " ", m.strip().lower()) for m in _NUMERIC_FACT_RE.findall(cleaned)}


def _content_tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) >= 3}


# ---------------------------------------------------------------------------
# Class A — authority asymmetry
# ---------------------------------------------------------------------------

def _classify_class_a(
    new_page: Path,
    new_meta: dict,
    root: Path,
) -> list[TriageFinding]:
    """Wiki page (external-reference / internal-reference) contains a numeric
    fact diverging from a numeric fact on its builds-on canonical target."""
    if _effective_authority(new_page, new_meta) == "canonical-process":
        return []  # Canonical pages handle their own truth — Class A is for derivative pages

    builds_on_paths = _resolve_builds_on(new_page, new_meta.get("builds-on") or [], root)
    if not builds_on_paths:
        return []

    new_body = _strip_frontmatter(_read_text(new_page))
    new_numbers = _numeric_tokens(new_body)
    if not new_numbers:
        return []

    findings: list[TriageFinding] = []
    for canonical_path in builds_on_paths:
        canonical_text = _read_text(canonical_path)
        canonical_body = _strip_frontmatter(canonical_text)
        canonical_numbers = _numeric_tokens(canonical_body)
        if not canonical_numbers:
            continue

        # Heuristic: if numeric sets are disjoint AND content overlap is high,
        # the pages are about the same thing but reporting different numbers.
        new_content = _content_tokens(new_body)
        canonical_content = _content_tokens(canonical_body)
        if not new_content or not canonical_content:
            continue
        content_overlap = len(new_content & canonical_content) / max(1, len(new_content | canonical_content))
        if content_overlap < 0.10:
            continue  # unrelated pages; numbers diverging is not a conflict

        diverging = new_numbers - canonical_numbers
        if not diverging:
            continue

        # Confidence: weighted blend of content overlap + the size of the
        # divergence. Stronger signal when both pages have a small, overlapping
        # set of numbers but diverge.
        confidence = round(min(1.0, 0.55 + content_overlap), 3)
        findings.append(TriageFinding(
            klass="A",
            confidence=confidence,
            related_pages=[canonical_path],
            finding_attrs={
                "wiki_file": str(new_page.relative_to(root)) if new_page.is_relative_to(root) else str(new_page),
                "canonical_file": str(canonical_path.relative_to(root)) if canonical_path.is_relative_to(root) else str(canonical_path),
                "claim_key": "numeric-divergence",
                "wiki_value": sorted(diverging)[:3],
                "canonical_value": sorted(canonical_numbers - new_numbers)[:3],
                "content_overlap": round(content_overlap, 3),
            },
            auto_action="annotation" if confidence >= AUTO_APPLY_CONFIDENCE else None,
        ))
    return findings


# ---------------------------------------------------------------------------
# Class B — temporal supersession candidate
# ---------------------------------------------------------------------------

def _classify_class_b(
    new_page: Path,
    new_meta: dict,
    root: Path,
    same_cluster_pages: list[tuple[Path, dict]],
) -> list[TriageFinding]:
    """Same source-url + same cluster + different temporal-signal -> supersession candidate."""
    new_url = (new_meta.get("source-url") or "").strip()
    if not new_url:
        return []
    new_when = _temporal_signal(new_meta)
    if new_when is None:
        return []

    findings: list[TriageFinding] = []
    new_slug = _slug(new_page)
    for other_path, other_meta in same_cluster_pages:
        if _slug(other_path) == new_slug:
            continue
        other_url = (other_meta.get("source-url") or "").strip()
        if other_url != new_url:
            continue
        other_when = _temporal_signal(other_meta)
        if other_when is None or other_when == new_when:
            continue

        # Skip if the link already exists in either direction.
        existing_sup = new_meta.get("supersedes") or []
        if not isinstance(existing_sup, list):
            existing_sup = [existing_sup] if existing_sup else []
        if _slug(other_path) in {str(s).strip() for s in existing_sup}:
            continue
        if (new_meta.get("superseded-by") or "").strip() == _slug(other_path):
            continue

        # Decide direction by date.
        if new_when > other_when:
            successor, predecessor = new_page, other_path
            successor_when, predecessor_when = new_when, other_when
        else:
            successor, predecessor = other_path, new_page
            successor_when, predecessor_when = other_when, new_when

        # Confidence: same URL + same cluster + parseable dates → high.
        confidence = 0.92
        findings.append(TriageFinding(
            klass="B",
            confidence=confidence,
            related_pages=[other_path],
            finding_attrs={
                "successor": str(successor.relative_to(root)) if successor.is_relative_to(root) else str(successor),
                "predecessor": str(predecessor.relative_to(root)) if predecessor.is_relative_to(root) else str(predecessor),
                "source_url": new_url,
                "successor_published": successor_when.isoformat(),
                "predecessor_published": predecessor_when.isoformat(),
            },
            auto_action="supersession-link" if confidence >= AUTO_APPLY_CONFIDENCE else None,
        ))
    return findings


# ---------------------------------------------------------------------------
# Class C — true contradiction
# ---------------------------------------------------------------------------

def _within_review_cadence(meta: dict, today: date) -> bool:
    last = _parse_date(meta.get("last-reviewed"))
    if last is None:
        return False
    age = (today - last).days
    return age <= DEFAULT_REVIEW_CADENCE_DAYS


def _classify_class_c(
    new_page: Path,
    new_meta: dict,
    root: Path,
    same_cluster_pages: list[tuple[Path, dict]],
) -> list[TriageFinding]:
    """Two canonical-process pages, same cluster, both current, conflicting numeric facts."""
    if _effective_authority(new_page, new_meta) != "canonical-process":
        return []
    today = date.today()
    if not _within_review_cadence(new_meta, today):
        return []

    new_body = _strip_frontmatter(_read_text(new_page))
    new_numbers = _numeric_tokens(new_body)
    new_content = _content_tokens(new_body)
    if not new_numbers or not new_content:
        return []

    findings: list[TriageFinding] = []
    new_slug = _slug(new_page)
    for other_path, other_meta in same_cluster_pages:
        if _slug(other_path) == new_slug:
            continue
        if _effective_authority(other_path, other_meta) != "canonical-process":
            continue
        if not _within_review_cadence(other_meta, today):
            continue

        other_body = _strip_frontmatter(_read_text(other_path))
        other_numbers = _numeric_tokens(other_body)
        other_content = _content_tokens(other_body)
        if not other_numbers or not other_content:
            continue

        content_overlap = len(new_content & other_content) / max(1, len(new_content | other_content))
        if content_overlap < 0.20:
            continue  # different topics, even within same cluster

        diverging_new = new_numbers - other_numbers
        diverging_other = other_numbers - new_numbers
        if not diverging_new or not diverging_other:
            continue  # both must have unique numbers — otherwise one is just more detailed

        confidence = round(min(1.0, 0.60 + content_overlap * 0.40), 3)
        findings.append(TriageFinding(
            klass="C",
            confidence=confidence,
            related_pages=[other_path],
            finding_attrs={
                "wiki_file_a": str(new_page.relative_to(root)) if new_page.is_relative_to(root) else str(new_page),
                "wiki_file_b": str(other_path.relative_to(root)) if other_path.is_relative_to(root) else str(other_path),
                "cluster": new_meta.get("cluster"),
                "claim_key": "numeric-divergence",
                "value_a": sorted(diverging_new)[:3],
                "value_b": sorted(diverging_other)[:3],
                "content_overlap": round(content_overlap, 3),
            },
            auto_action=None,  # Class C never auto-applies — always interrupt
        ))
    return findings


# ---------------------------------------------------------------------------
# Class D — stale-canonical drift
# ---------------------------------------------------------------------------

def _classify_class_d(
    new_page: Path,
    new_meta: dict,
    root: Path,
) -> list[TriageFinding]:
    """New external-reference fact diverges from a canonical doc whose
    last-updated is older than STALE_CANONICAL_DAYS."""
    if _effective_authority(new_page, new_meta) != "external-reference":
        return []
    builds_on_paths = _resolve_builds_on(new_page, new_meta.get("builds-on") or [], root)
    if not builds_on_paths:
        return []

    new_body = _strip_frontmatter(_read_text(new_page))
    new_numbers = _numeric_tokens(new_body)
    if not new_numbers:
        return []

    today = date.today()
    findings: list[TriageFinding] = []
    for canonical_path in builds_on_paths:
        canonical_text = _read_text(canonical_path)
        canonical_body = _strip_frontmatter(canonical_text)
        canonical_meta = parse_frontmatter(canonical_text) or {}
        canonical_numbers = _numeric_tokens(canonical_body)
        if not canonical_numbers:
            continue

        canonical_last_updated = _parse_date(canonical_meta.get("last-updated"))
        if canonical_last_updated is None:
            continue
        age_days = (today - canonical_last_updated).days
        if age_days < STALE_CANONICAL_DAYS:
            continue  # canonical is fresh; not Class D

        diverging = new_numbers - canonical_numbers
        if not diverging:
            continue

        new_content = _content_tokens(new_body)
        canonical_content = _content_tokens(canonical_body)
        if not new_content or not canonical_content:
            continue
        content_overlap = len(new_content & canonical_content) / max(1, len(new_content | canonical_content))
        if content_overlap < 0.10:
            continue

        confidence = round(min(1.0, 0.50 + content_overlap + min(0.2, age_days / 1825)), 3)
        findings.append(TriageFinding(
            klass="D",
            confidence=confidence,
            related_pages=[canonical_path],
            finding_attrs={
                "canonical_file": str(canonical_path.relative_to(root)) if canonical_path.is_relative_to(root) else str(canonical_path),
                "supporting_wiki_files": [str(new_page.relative_to(root)) if new_page.is_relative_to(root) else str(new_page)],
                "canonical_last_updated": canonical_last_updated.isoformat(),
                "age_days": age_days,
                "claim_keys": ["numeric-divergence"],
                "wiki_values": sorted(diverging)[:3],
                "canonical_values": sorted(canonical_numbers - new_numbers)[:3],
                "content_overlap": round(content_overlap, 3),
            },
            auto_action=None,  # Class D suggests review; never auto-edits canonical
        ))
    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def classify(
    new_page: Path | str,
    root: Path | str,
    strict: bool = False,
) -> list[TriageFinding]:
    """Mechanically classify a newly-written wiki page into 0+ findings.

    Parameters
    ----------
    new_page : Path
        Path to the wiki page just written by ingest.
    root : Path
        Repository root (the directory whose `docs/_wiki/` is the wiki zone).
    strict : bool
        When True, allow cross-cluster comparison (with confidence × 0.7).
        Default False — same-cluster only (D-04).
    """
    new_page = Path(new_page)
    root = Path(root)
    new_meta = _read_meta(new_page)
    if not new_meta:
        return []

    new_cluster = (new_meta.get("cluster") or "").strip()
    all_pages = [(p, _read_meta(p)) for p in _wiki_pages_under(root)]
    if strict:
        peer_pages = [(p, m) for (p, m) in all_pages if p != new_page]
    else:
        peer_pages = [
            (p, m) for (p, m) in all_pages
            if p != new_page and (m.get("cluster") or "").strip() == new_cluster
        ]

    findings: list[TriageFinding] = []
    findings.extend(_classify_class_a(new_page, new_meta, root))
    findings.extend(_classify_class_b(new_page, new_meta, root, peer_pages))
    findings.extend(_classify_class_c(new_page, new_meta, root, peer_pages))
    findings.extend(_classify_class_d(new_page, new_meta, root))

    if strict and new_cluster:
        # Apply cross-cluster confidence multiplier per D-04.
        for f in findings:
            for related in f.related_pages:
                related_meta = _read_meta(related) if related.is_file() else {}
                related_cluster = (related_meta.get("cluster") or "").strip()
                if related_cluster and related_cluster != new_cluster:
                    f.confidence = round(f.confidence * STRICT_CROSS_CLUSTER_MULTIPLIER, 3)

    return findings


# ---------------------------------------------------------------------------
# Bidirectional supersedes write (called by Class B auto-apply)
# ---------------------------------------------------------------------------

def write_supersedes_link(
    successor: Path | str,
    predecessor_slug: str,
    root: Path | str,
) -> None:
    """Atomically write `supersedes:[predecessor]` on the successor and
    `superseded-by: <successor-slug>` on the predecessor.

    Aborts with `ValueError` if the operation would create a cycle.
    """
    successor = Path(successor)
    root = Path(root)

    # Locate the predecessor file from the slug across pages/ and source-summary/.
    pred_path: Path | None = None
    for candidate in _wiki_pages_under(root):
        if _slug(candidate) == predecessor_slug:
            pred_path = candidate
            break
    if pred_path is None:
        raise ValueError(f"predecessor slug '{predecessor_slug}' not found in wiki")

    succ_slug = _slug(successor)

    # Cycle guard: would adding successor -> predecessor create a path back?
    # Build the supersedes graph and DFS from `predecessor_slug`.
    graph: dict[str, list[str]] = {}
    for path in _wiki_pages_under(root):
        meta = _read_meta(path)
        sup = meta.get("supersedes") or []
        if not isinstance(sup, list):
            sup = [sup] if sup else []
        graph[_slug(path)] = [str(s).strip() for s in sup if str(s).strip()]

    # Add the candidate edge: successor -> predecessor_slug
    graph.setdefault(succ_slug, []).append(predecessor_slug)

    # Detect cycle reachable from successor.
    stack = [succ_slug]
    seen = {succ_slug}
    while stack:
        node = stack.pop()
        for nbr in graph.get(node, []):
            if nbr == succ_slug:
                raise ValueError(
                    f"supersession-cycle: writing '{succ_slug}' -> supersedes -> '{predecessor_slug}' "
                    f"would create a cycle (path returns to '{succ_slug}')"
                )
            if nbr not in seen:
                seen.add(nbr)
                stack.append(nbr)

    # Apply the writes — successor adds slug to its supersedes list,
    # predecessor sets superseded-by to successor slug.
    succ_text = _read_text(successor)
    succ_meta = parse_frontmatter(succ_text) or {}
    existing = succ_meta.get("supersedes") or []
    if not isinstance(existing, list):
        existing = [existing] if existing else []
    if predecessor_slug not in {str(s).strip() for s in existing}:
        existing = list(existing) + [predecessor_slug]
        successor.write_text(
            apply_frontmatter(succ_text, {"supersedes": existing}),
            encoding="utf-8",
        )

    pred_text = _read_text(pred_path)
    pred_meta = parse_frontmatter(pred_text) or {}
    if (pred_meta.get("superseded-by") or "").strip() != succ_slug:
        pred_path.write_text(
            apply_frontmatter(pred_text, {"superseded-by": succ_slug}),
            encoding="utf-8",
        )


__all__ = [
    "TriageFinding",
    "classify",
    "write_supersedes_link",
    "STALE_CANONICAL_DAYS",
    "AUTO_APPLY_CONFIDENCE",
    "STRICT_CROSS_CLUSTER_MULTIPLIER",
]

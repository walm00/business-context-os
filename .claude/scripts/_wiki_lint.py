#!/usr/bin/env python3
"""
Wiki lint: `duplication-vs-data-point` Jaccard check (P4_007).

A wiki page that `builds-on:` a canonical data point should LINK to that data
point, not RESTATE its content. This check flags cases where the wiki page
body contains paragraphs whose token sets overlap heavily with paragraphs in
the data point — a heuristic for "you copy-pasted instead of citing."

Mechanical (D-10): pure token-set similarity. No LLM. Deterministic. False
positives are accepted at WARN severity; the rule is "if it looks like a
restatement, ask the human." If the heuristic over-fires, raise the threshold
in `_wiki/.config.yml` `thresholds.duplication-jaccard` (default 0.5).

Public API:
    jaccard(set_a, set_b)                                  -> float
    paragraph_tokens(paragraph)                            -> set[str]
    split_paragraphs(text)                                 -> list[str]
    detect_duplication(wiki_text, target_text, threshold)  -> list[Finding]
    lint_page(wiki_path, builds_on_paths, threshold)       -> list[Finding]

A `Finding` is a dataclass with the wiki paragraph that triggered, the matched
target paragraph, and the Jaccard score, suitable for inclusion in the
`/wiki lint` report under id `duplication-vs-data-point` (severity WARN).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_THRESHOLD = 0.5
MIN_TOKENS_PER_PARAGRAPH = 8     # paragraphs shorter than this are skipped
MIN_CONSECUTIVE_MATCHES = 1      # ≥1 paragraph match → flag (per spec)

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
_HEADING_RE = re.compile(r"^#{1,6}\s")
_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n?", re.DOTALL)
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "of", "in", "on", "to", "for", "with", "by", "and", "or", "not",
        "this", "that", "these", "those", "it", "its", "as", "at", "from",
        "but", "if", "we", "i", "do", "does", "did", "will", "would", "can",
        "could", "should", "may", "might", "must", "have", "has", "had",
        "our", "we", "us", "you", "your", "they", "them", "their",
    }
)


@dataclass(frozen=True)
class Finding:
    wiki_path: Path
    target_path: Path
    wiki_paragraph: str
    target_paragraph: str
    score: float


def jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Standard Jaccard similarity over two token sets."""
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def paragraph_tokens(paragraph: str) -> set[str]:
    """Lower-cased, stopword-filtered token set."""
    tokens = {tok for tok in _TOKEN_RE.findall(paragraph.lower()) if tok not in _STOPWORDS and len(tok) >= 3}
    return tokens


def split_paragraphs(text: str) -> list[str]:
    """Split markdown into prose paragraphs.

    Strips frontmatter, skips heading lines, joins consecutive non-blank
    non-heading lines into paragraphs. Code fences are skipped entirely.
    """
    body = _FRONTMATTER_RE.sub("", text, count=1)
    paragraphs: list[str] = []
    buffer: list[str] = []
    in_fence = False

    def flush() -> None:
        if buffer:
            paragraphs.append(" ".join(buffer).strip())
            buffer.clear()

    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            flush()
            continue
        if _HEADING_RE.match(stripped):
            flush()
            continue
        if stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("> "):
            flush()
            continue
        buffer.append(stripped)
    flush()
    return [p for p in paragraphs if p]


def detect_duplication(
    wiki_text: str,
    target_text: str,
    *,
    wiki_path: Path | None = None,
    target_path: Path | None = None,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[Finding]:
    """Find wiki paragraphs that overlap with target paragraphs above threshold.

    Returns one Finding per (wiki paragraph, target paragraph) match. Paragraphs
    shorter than MIN_TOKENS_PER_PARAGRAPH are skipped to avoid noisy hits on
    one-line glossary entries.
    """
    wiki_paragraphs = split_paragraphs(wiki_text)
    target_paragraphs = split_paragraphs(target_text)
    target_token_sets = [
        (para, paragraph_tokens(para)) for para in target_paragraphs
    ]
    target_token_sets = [
        (para, toks) for para, toks in target_token_sets if len(toks) >= MIN_TOKENS_PER_PARAGRAPH
    ]

    findings: list[Finding] = []
    wiki_path = wiki_path or Path("<wiki>")
    target_path = target_path or Path("<target>")

    for w_para in wiki_paragraphs:
        w_tokens = paragraph_tokens(w_para)
        if len(w_tokens) < MIN_TOKENS_PER_PARAGRAPH:
            continue
        for t_para, t_tokens in target_token_sets:
            score = jaccard(w_tokens, t_tokens)
            if score >= threshold:
                findings.append(
                    Finding(
                        wiki_path=wiki_path,
                        target_path=target_path,
                        wiki_paragraph=w_para,
                        target_paragraph=t_para,
                        score=round(score, 3),
                    )
                )
    return findings


def lint_page(
    wiki_path: Path,
    builds_on_paths: Iterable[Path],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[Finding]:
    """Run the duplication-vs-data-point check for a wiki page.

    `builds_on_paths` are the canonical data points the wiki page builds on
    (resolved by the caller from the page's `builds-on:` frontmatter). Each is
    compared against the wiki body; findings aggregate across all targets.
    """
    try:
        wiki_text = wiki_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    findings: list[Finding] = []
    for target in builds_on_paths:
        try:
            target_text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        findings.extend(
            detect_duplication(
                wiki_text,
                target_text,
                wiki_path=wiki_path,
                target_path=target,
                threshold=threshold,
            )
        )
    return findings


__all__ = [
    "Finding",
    "jaccard",
    "paragraph_tokens",
    "split_paragraphs",
    "detect_duplication",
    "lint_page",
    "DEFAULT_THRESHOLD",
    "scan_supersession",
    "scan_authority",
    "main",
]


# ---------------------------------------------------------------------------
# Schema 1.2 lint checks
# ---------------------------------------------------------------------------

import sys as _sys
from pathlib import Path as _Path

_AUTHORITY_CANONICAL_PROCESS_TYPES = {"how-to", "runbook", "decision-log", "post-mortem"}
_AUTHORITY_INTERNAL_REFERENCE_TYPES = {"glossary", "faq"}


def _wiki_pages_under(root: _Path) -> list[_Path]:
    base = root / "docs" / "_wiki"
    out: list[_Path] = []
    for sub in ("pages", "source-summary"):
        d = base / sub
        if d.is_dir():
            out.extend(sorted(d.glob("*.md")))
    return out


def _slug(p: _Path) -> str:
    return p.stem


def _derive_authority(p: _Path, meta: dict) -> str | None:
    folder = p.parent.name
    page_type = (meta.get("page-type") or "").strip()
    if folder == "source-summary":
        return "external-reference"
    if folder == "pages":
        if page_type in _AUTHORITY_CANONICAL_PROCESS_TYPES:
            return "canonical-process"
        if page_type in _AUTHORITY_INTERNAL_REFERENCE_TYPES:
            return "internal-reference"
        return "internal-reference"
    return None


def scan_supersession(root: _Path) -> list[str]:
    """Emit findings for orphan-supersession, supersession-cycle, and
    both-supersedes-and-superseded-by across the entire wiki zone."""
    _sys.path.insert(0, str(_Path(__file__).resolve().parent))
    from _wiki_yaml import parse_frontmatter  # type: ignore[import-not-found]

    pages = _wiki_pages_under(root)
    slugs = {_slug(p) for p in pages}
    metas: dict[str, tuple[_Path, dict]] = {_slug(p): (p, parse_frontmatter(p) or {}) for p in pages}

    findings: list[str] = []

    for slug, (path, meta) in metas.items():
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        sup = meta.get("supersedes") or []
        if not isinstance(sup, list):
            sup = [sup] if sup else []
        sup_by = (meta.get("superseded-by") or "").strip() if isinstance(meta.get("superseded-by"), str) else (meta.get("superseded-by") or "")

        if sup and sup_by:
            findings.append(
                f"ERROR: both-supersedes-and-superseded-by: {rel}: page declares both "
                f"supersedes and superseded-by — must be chain head or chain tail, not both"
            )

        for target in sup:
            t = str(target).strip()
            if not t:
                continue
            if t.endswith(".md"):
                t = t[:-3]
            if t not in slugs:
                findings.append(
                    f"WARN: orphan-supersession: {rel}: supersedes target '{t}' does not exist in wiki"
                )

        if isinstance(sup_by, str) and sup_by:
            t = sup_by[:-3] if sup_by.endswith(".md") else sup_by
            if t not in slugs:
                findings.append(
                    f"WARN: orphan-supersession: {rel}: superseded-by target '{t}' does not exist in wiki"
                )

    graph: dict[str, list[str]] = {}
    for slug, (_p, meta) in metas.items():
        sup = meta.get("supersedes") or []
        if not isinstance(sup, list):
            sup = [sup] if sup else []
        graph[slug] = [str(s).strip()[:-3] if str(s).strip().endswith(".md") else str(s).strip() for s in sup if str(s).strip()]

    def _has_cycle(start: str) -> list[str] | None:
        stack = [(start, [start])]
        seen_paths: set[tuple[str, ...]] = set()
        while stack:
            node, path = stack.pop()
            for neighbor in graph.get(node, []):
                if neighbor == start:
                    return path + [neighbor]
                if neighbor not in path:
                    new_path = path + [neighbor]
                    if tuple(new_path) not in seen_paths:
                        seen_paths.add(tuple(new_path))
                        stack.append((neighbor, new_path))
        return None

    cycles_seen: set[frozenset[str]] = set()
    for slug in graph:
        cycle = _has_cycle(slug)
        if cycle:
            sig = frozenset(cycle)
            if sig in cycles_seen:
                continue
            cycles_seen.add(sig)
            chain = " -> ".join(cycle)
            findings.append(f"ERROR: supersession-cycle: cycle detected: {chain}")

    return findings


def scan_authority(root: _Path) -> list[str]:
    """Emit authority-default-questionable INFO findings when declared
    `authority` disagrees with the mechanical default derived from path + page-type."""
    _sys.path.insert(0, str(_Path(__file__).resolve().parent))
    from _wiki_yaml import parse_frontmatter  # type: ignore[import-not-found]

    findings: list[str] = []
    for path in _wiki_pages_under(root):
        meta = parse_frontmatter(path) or {}
        declared = (meta.get("authority") or "").strip() or None
        if declared is None:
            continue
        expected = _derive_authority(path, meta)
        if expected and declared != expected and declared != "external-evidence":
            rel = path.relative_to(root) if path.is_relative_to(root) else path
            findings.append(
                f"INFO: authority-default-questionable: {rel}: declared 'authority: {declared}' "
                f"disagrees with mechanical default '{expected}'"
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    """Run all wiki lint checks under --root and print findings, one per line.

    Findings already carry their severity prefix (ERROR/WARN/INFO). Exit code:
      0 — no findings or only INFO
      1 — one or more WARN/ERROR
    """
    import argparse
    parser = argparse.ArgumentParser(description="Run wiki lint checks (schema 1.2)")
    parser.add_argument("--root", type=_Path, required=True)
    args = parser.parse_args(argv)

    findings: list[str] = []
    findings.extend(scan_supersession(args.root))
    findings.extend(scan_authority(args.root))

    for line in findings:
        print(line)

    if any(f.startswith("ERROR:") or f.startswith("WARN:") for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

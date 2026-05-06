#!/usr/bin/env python3
"""
run_wiki_coverage_audit.py — quarterly coverage scan, runnable headless.

Three checks:

  coverage-gap-data-point   Active docs/*.md data points with no wiki page
                            listing them in builds-on.
  coverage-gap-inbox-term   Inbox filenames / first-headings repeated across
                            captures but not covered by any wiki page title
                            or builds-on path fragment.
  cluster-mismatch          Wiki pages whose `cluster:` value is not present
                            in document-index.md.

Reference: .claude/skills/schedule-dispatcher/references/job-wiki-coverage-audit.md

CLI:
    python .claude/scripts/run_wiki_coverage_audit.py
    python .claude/scripts/run_wiki_coverage_audit.py --dry-run
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _wiki_job_runner import (  # noqa: E402
    iter_wiki_pages,
    no_wiki_zone,
    repo_root,
    run_wiki_job,
)
from _wiki_yaml import parse_frontmatter  # noqa: E402


JOB_ID = "wiki-coverage-audit"


# ---------------------------------------------------------------------------
# Wiki knowledge: covered sources + page titles + clusters
# ---------------------------------------------------------------------------

def _load_wiki_knowledge(root: Path) -> dict:
    covered: set[str] = set()
    titles_lower: set[str] = set()
    clusters: dict[str, str] = {}

    for page in iter_wiki_pages(root, subdir="pages"):
        fm = parse_frontmatter(page) or {}
        name = fm.get("name") or ""
        if name:
            titles_lower.add(str(name).lower())
        titles_lower.add(page.stem.lower())

        builds_on = fm.get("builds-on") or fm.get("builds_on") or []
        if isinstance(builds_on, list):
            for ref in builds_on:
                covered.add(str(ref).strip())

        cluster = fm.get("cluster")
        if cluster:
            rel = str(page.relative_to(root)).replace("\\", "/")
            clusters[rel] = str(cluster)

    return {"covered": covered, "titles_lower": titles_lower, "clusters": clusters}


# ---------------------------------------------------------------------------
# document-index.md cluster harvest
# ---------------------------------------------------------------------------

_CLUSTER_HEADING_RE = re.compile(r"^#+\s+Cluster[s]?\s*:\s*(.+)$", re.IGNORECASE)
_CLUSTER_ROW_RE = re.compile(r"^\|[^|]*\|\s*`?([A-Za-z][^|`]*?)`?\s*\|")


def _load_index_clusters(root: Path) -> set[str]:
    idx = root / "docs" / "document-index.md"
    if not idx.is_file():
        return set()
    text = idx.read_text(encoding="utf-8")
    out: set[str] = set()
    for line in text.splitlines():
        m = _CLUSTER_HEADING_RE.match(line)
        if m:
            out.add(m.group(1).strip())
            continue
        m2 = _CLUSTER_ROW_RE.match(line)
        if m2:
            val = m2.group(1).strip()
            if val and val.lower() not in ("cluster", "—", "-"):
                out.add(val)
    return out


# ---------------------------------------------------------------------------
# Inbox term mining (cheap)
# ---------------------------------------------------------------------------

_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _inbox_terms(root: Path) -> list[str]:
    inbox = root / "docs" / "_inbox"
    if not inbox.is_dir():
        return []
    terms: list[str] = []
    for md in inbox.glob("*.md"):
        terms.append(md.stem.lower().replace("-", " ").replace("_", " "))
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
            m = _H1_RE.search(text)
            if m:
                terms.append(m.group(1).strip().lower())
        except OSError:
            pass
    return terms


def _is_covered_by_wiki(term: str, titles_lower: set[str], covered: set[str]) -> bool:
    if term in titles_lower:
        return True
    return any(term in ref.lower() for ref in covered)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

_SKIP_TOP_DIRS = {"_planned", "_archive", "_inbox", "_collections", "_bcos-framework", "_wiki"}


def _is_skipped(path: Path, docs_root: Path) -> bool:
    try:
        rel = path.relative_to(docs_root)
    except ValueError:
        return True
    parts = rel.parts
    if not parts:
        return True
    return parts[0].startswith("_")


def detect_findings(root: Path | None = None) -> list[dict]:
    r = root or repo_root()
    if no_wiki_zone(r):
        return []

    docs_root = r / "docs"
    wiki = _load_wiki_knowledge(r)
    covered = wiki["covered"]
    titles_lower = wiki["titles_lower"]
    page_clusters = wiki["clusters"]
    index_clusters = _load_index_clusters(r)

    findings: list[dict] = []

    # coverage-gap-data-point
    for doc_path in sorted(docs_root.rglob("*.md")):
        if _is_skipped(doc_path, docs_root):
            continue
        fm = parse_frontmatter(doc_path) or {}
        # Only flag actual data points; framework / index files have a different type.
        doc_type = fm.get("type") or ""
        if doc_type in ("_bcos-framework", "framework"):
            continue
        rel = str(doc_path.relative_to(r)).replace("\\", "/")
        if rel not in covered:
            name = fm.get("name") or doc_path.stem
            findings.append({
                "finding_type": "coverage-gap-data-point",
                "verdict": "amber",
                "emitted_by": JOB_ID,
                "finding_attrs": {
                    "data_point_file": rel,
                    "data_point": name,
                },
                "suggested_actions": ["coverage-gap-stub"],
            })

    # coverage-gap-inbox-term
    seen_terms: set[str] = set()
    for term in _inbox_terms(r):
        t = term.strip()
        if not t or len(t) < 4 or t in seen_terms:
            continue
        seen_terms.add(t)
        if not _is_covered_by_wiki(t, titles_lower, covered):
            findings.append({
                "finding_type": "coverage-gap-inbox-term",
                "verdict": "amber",
                "emitted_by": JOB_ID,
                "finding_attrs": {"term": t},
                "suggested_actions": ["coverage-gap-stub"],
            })

    # cluster-mismatch
    if index_clusters:
        for rel_page, cluster in sorted(page_clusters.items()):
            if cluster not in index_clusters:
                findings.append({
                    "finding_type": "cluster-mismatch",
                    "verdict": "amber",
                    "emitted_by": JOB_ID,
                    "finding_attrs": {
                        "wiki_file": rel_page,
                        "cluster": cluster,
                    },
                    "suggested_actions": [],
                })

    return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    dry_run = "--dry-run" in argv
    r = repo_root()

    if no_wiki_zone(r):
        result = {
            "verdict": "green",
            "findings_count": 0,
            "auto_fixed": [],
            "actions_needed": [],
            "notes": "No docs/_wiki/ zone in this repo — wiki-coverage-audit skipped cleanly.",
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0

    findings = detect_findings(r)

    if dry_run:
        result = {
            "verdict": "green" if not findings else "amber",
            "findings_count": len(findings),
            "auto_fixed": [],
            "actions_needed": [
                f"{f['finding_type']}: {f['finding_attrs'].get('data_point_file') or f['finding_attrs'].get('wiki_file') or f['finding_attrs'].get('term', '?')}"
                for f in findings
            ],
            "notes": f"Dry-run — would write {len(findings)} finding(s) to digest.",
            "dry_run": True,
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0

    notes = (
        f"Coverage audit found {len(findings)} wiki expansion candidate(s)."
        if findings
        else "Coverage clean — every active data point has wiki coverage."
    )
    result = run_wiki_job(
        job_id=JOB_ID,
        findings=findings,
        notes=notes,
        trigger="scheduled-headless",
        root=r,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["verdict"] != "error" else 1


if __name__ == "__main__":
    sys.exit(main())

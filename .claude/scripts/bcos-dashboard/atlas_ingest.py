"""
atlas_ingest.py - Dashboard compatibility layer over the canonical context index.

The canonical parser and docs walk now live in `.claude/scripts/context_index.py`.
This module keeps the old Atlas/file_health API stable:

  - parse_frontmatter(text)
  - parse_ownership_spec(text)
  - iter_docs(skip_dirs=..., include_dotfiles=...)
  - build_atlas()

Dashboard collectors and Galaxy can keep consuming the same payload shape while
gaining wiki, collection, tags, review metadata, and path-derived facets.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
for p in (_HERE, _SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from single_repo import REPO_ROOT  # noqa: E402
from context_index import (  # noqa: E402
    build_context_index,
    parse_frontmatter,
    parse_ownership_spec,
)

DOCS_ROOT = REPO_ROOT / "docs"
LIFECYCLE_BUCKETS = ("_inbox", "_planned", "active", "_archive", "_bcos-framework", "_collections")


def iter_docs(skip_dirs: set[str] | None = None, include_dotfiles: bool = False) -> list[Path]:
    """List markdown files under docs/, preserving the historical dashboard API."""
    if not DOCS_ROOT.is_dir():
        return []
    skip = skip_dirs or set()
    docs: list[Path] = []
    for path in sorted(DOCS_ROOT.rglob("*.md")):
        parts = set(path.relative_to(DOCS_ROOT).parts)
        if parts & skip:
            continue
        if not include_dotfiles and path.name.startswith("."):
            continue
        docs.append(path)
    return docs


def build_atlas(now=None) -> dict:
    """Return the Atlas payload shape expected by dashboard and Galaxy callers."""
    index = build_context_index(REPO_ROOT, now=now)
    docs = list(index.get("docs") or [])
    lifecycle = {bucket: [] for bucket in LIFECYCLE_BUCKETS}
    for doc in docs:
        lifecycle.setdefault(doc.get("bucket") or "active", []).append(doc.get("path"))

    # Keep the old `counts` keys stable while preserving richer index data.
    counts = {
        "total": len(docs),
        "with_frontmatter": sum(1 for d in docs if d.get("has_frontmatter")),
        "missing_required": sum(1 for d in docs if d.get("missing_required")),
    }
    return {
        "generated_at": index.get("generated_at"),
        "repo_root": index.get("repo_root"),
        "repo_name": index.get("repo_name"),
        "counts": counts,
        "docs": docs,
        "domains": index.get("domains") or {},
        "lifecycle": lifecycle,
        "edges": index.get("edges") or [],
        "orphans": index.get("orphans") or [],
        "summaries": index.get("summaries") or {},
        "schema_version": index.get("schema_version"),
    }


def _iter_docs_fh_compat() -> list[Path]:
    skip = {"_inbox", "_planned", "_archive", "_collections", "_bcos-framework"}
    return iter_docs(skip_dirs=skip, include_dotfiles=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Dump dashboard Atlas data as JSON.")
    ap.add_argument("--out", help="Write JSON here instead of stdout")
    ap.add_argument("--summary", action="store_true", help="Print only counts + domain list")
    args = ap.parse_args()
    atlas = build_atlas()
    if args.summary:
        print(f"docs:       {atlas['counts']['total']}")
        print(f"with FM:    {atlas['counts']['with_frontmatter']}")
        print(f"missing:    {atlas['counts']['missing_required']}")
        print(f"domains:    {len(atlas['domains'])}")
        print(f"edges:      {len(atlas['edges'])}")
        print(f"orphans:    {len(atlas['orphans'])}")
        print()
        for dom, info in sorted(atlas["domains"].items(), key=lambda kv: -kv[1]["doc_count"]):
            avg = info["avg_age_days"]
            avg_s = f"{avg:.0f}d" if avg is not None else "-"
            print(f"  {dom:40} {info['doc_count']:>3} docs  avg-age {avg_s}")
    else:
        text = json.dumps(atlas, indent=2, ensure_ascii=False)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"Wrote {args.out}")
        else:
            print(text)

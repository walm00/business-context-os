#!/usr/bin/env python3
"""
cmd_wiki_search.py — search wiki pages through the shared context backend.

User-triggered command (mirrors `/wiki search <query>` chat path). This is
zone-scoped sugar over context_search.py with `zone=wiki`.

CLI:
    python .claude/scripts/cmd_wiki_search.py --query "pricing"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import context_search_service  # noqa: E402


def repo_root() -> Path:
    import os
    override = os.environ.get("BCOS_REPO_ROOT", "").strip()
    if override:
        p = Path(override).expanduser().resolve()
        if p.is_dir():
            return p
    return _HERE.parents[1]


def search(query: str, *, root: Path | None = None, limit: int = 25) -> dict:
    r = root or repo_root()
    q = query.strip().lower()
    if not q:
        return {
            "ok": False, "status": "red", "query": query,
            "notes": "Query cannot be empty.",
        }

    result, status = context_search_service.search_context(
        r,
        {"q": query, "zone": "wiki", "top": str(limit)},
    )
    if status >= 400:
        return {
            "ok": False, "status": "red", "query": query,
            "notes": result.get("message") or result.get("error") or f"HTTP {status}",
            "result": result,
        }
    hits = result.get("hits") or []
    results = [
        {
            "slug": hit.get("slug"),
            "name": hit.get("name") or hit.get("summary") or hit.get("slug"),
            "page_type": hit.get("page-type") or "",
            "path": hit.get("path") or (hit.get("citation-id") or "").split(":", 1)[-1],
            "score": hit.get("score"),
            "citation_id": hit.get("citation-id"),
        }
        for hit in hits
    ]

    return {
        "ok": True, "status": "green", "query": query,
        "notes": f"{len(results)} match(es).",
        "hits": hits,
        "warning": result.get("warning"),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args(argv)
    result = search(args.query, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

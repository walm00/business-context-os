#!/usr/bin/env python3
"""
cmd_wiki_search.py — search wiki pages by query (filename + frontmatter name).

User-triggered command (mirrors `/wiki search <query>` chat path). Mechanical
substring + token match against page slugs and `name` frontmatter fields.

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

from _wiki_yaml import parse_frontmatter  # noqa: E402


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
    wiki_dir = r / "docs" / "_wiki"
    if not wiki_dir.is_dir():
        return {
            "ok": True, "status": "green", "query": query,
            "notes": "No wiki zone present.",
            "results": [],
        }

    q = query.strip().lower()
    if not q:
        return {
            "ok": False, "status": "red", "query": query,
            "notes": "Query cannot be empty.",
        }

    results: list[dict] = []
    for sub in ("pages", "source-summary"):
        base = wiki_dir / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            slug = path.stem
            fm = parse_frontmatter(path) or {}
            name = (fm.get("name") or "").strip()
            page_type = (fm.get("page-type") or fm.get("type") or "").strip()
            haystack = f"{slug} {name}".lower()
            if q in haystack:
                rel = path.relative_to(r).as_posix()
                results.append({
                    "slug": slug,
                    "name": name or slug,
                    "page_type": page_type,
                    "path": rel,
                    "subdir": sub,
                })
                if len(results) >= limit:
                    break

    return {
        "ok": True, "status": "green", "query": query,
        "notes": f"{len(results)} match(es).",
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

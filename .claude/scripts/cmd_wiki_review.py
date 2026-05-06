#!/usr/bin/env python3
"""
cmd_wiki_review.py — bump `last-reviewed: <today>` on a wiki page.

User-triggered command (mirrors `/wiki review <slug>` chat path). Mechanical:
no LLM, no fetching, just a frontmatter date bump. Idempotent — re-running
on the same day is a no-op.

CLI:
    python .claude/scripts/cmd_wiki_review.py --slug pricing-strategy
    python .claude/scripts/cmd_wiki_review.py --slug pricing-strategy --dry-run

JSON line on stdout (dispatcher contract): {ok, slug, status, before, after, notes}.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _wiki_yaml import apply_frontmatter, parse_frontmatter  # noqa: E402


def repo_root() -> Path:
    import os
    override = os.environ.get("BCOS_REPO_ROOT", "").strip()
    if override:
        p = Path(override).expanduser().resolve()
        if p.is_dir():
            return p
    return _HERE.parents[1]


def _resolve_page(slug: str, root: Path) -> Path | None:
    pages = root / "docs" / "_wiki" / "pages"
    candidate = pages / f"{slug}.md"
    if candidate.is_file():
        return candidate
    # Try source-summary too
    src = root / "docs" / "_wiki" / "source-summary" / f"{slug}.md"
    if src.is_file():
        return src
    return None


def review_page(slug: str, *, root: Path | None = None, dry_run: bool = False) -> dict:
    r = root or repo_root()
    path = _resolve_page(slug, r)
    if path is None:
        return {
            "ok": False,
            "slug": slug,
            "status": "red",
            "notes": f"No wiki page found for slug {slug!r} under docs/_wiki/pages/ or docs/_wiki/source-summary/.",
        }

    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text) or {}
    before = fm.get("last-reviewed") or fm.get("last_reviewed") or "(unset)"
    today = datetime.now(timezone.utc).date().isoformat()

    if before == today:
        return {
            "ok": True,
            "slug": slug,
            "status": "green",
            "before": before,
            "after": today,
            "notes": f"Already reviewed today ({today}); no change.",
            "no_op": True,
        }

    if dry_run:
        return {
            "ok": True,
            "slug": slug,
            "status": "green",
            "before": before,
            "after": today,
            "notes": f"Dry-run: would bump last-reviewed {before} → {today}.",
            "dry_run": True,
        }

    new_text = apply_frontmatter(text, {"last-reviewed": today})
    path.write_text(new_text, encoding="utf-8")
    return {
        "ok": True,
        "slug": slug,
        "status": "green",
        "before": before,
        "after": today,
        "notes": f"Marked reviewed: {path.relative_to(r).as_posix()} (last-reviewed: {today}).",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = review_page(args.slug, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

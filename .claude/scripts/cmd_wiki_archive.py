#!/usr/bin/env python3
"""
cmd_wiki_archive.py — set `status: archived` + `last-archived: <today>` on a wiki page.

User-triggered command (mirrors `/wiki archive <slug>` chat path). Mechanical
soft-delete — frontmatter only, file stays in place. Reversible: `git revert`
the single-file commit, or run cmd_wiki_archive.py --slug <slug> --restore.

CLI:
    python .claude/scripts/cmd_wiki_archive.py --slug pricing-strategy
    python .claude/scripts/cmd_wiki_archive.py --slug pricing-strategy --dry-run
    python .claude/scripts/cmd_wiki_archive.py --slug pricing-strategy --restore
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
    for sub in ("pages", "source-summary"):
        candidate = root / "docs" / "_wiki" / sub / f"{slug}.md"
        if candidate.is_file():
            return candidate
    return None


def archive_page(slug: str, *, root: Path | None = None, dry_run: bool = False,
                 restore: bool = False) -> dict:
    r = root or repo_root()
    path = _resolve_page(slug, r)
    if path is None:
        return {
            "ok": False, "slug": slug, "status": "red",
            "notes": f"No wiki page found for slug {slug!r}.",
        }

    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text) or {}
    current_status = fm.get("status") or "active"
    today = datetime.now(timezone.utc).date().isoformat()

    if restore:
        if current_status != "archived":
            return {
                "ok": True, "slug": slug, "status": "green",
                "notes": f"Page is not archived (status={current_status}); nothing to restore.",
                "no_op": True,
            }
        if dry_run:
            return {
                "ok": True, "slug": slug, "status": "green",
                "notes": f"Dry-run: would restore status archived → active on {path.relative_to(r).as_posix()}.",
                "dry_run": True,
            }
        new_text = apply_frontmatter(text, {"status": "active"})
        path.write_text(new_text, encoding="utf-8")
        return {
            "ok": True, "slug": slug, "status": "green",
            "notes": f"Restored {path.relative_to(r).as_posix()} (status: active).",
        }

    if current_status == "archived":
        return {
            "ok": True, "slug": slug, "status": "green",
            "notes": f"Already archived; no change.",
            "no_op": True,
        }

    if dry_run:
        return {
            "ok": True, "slug": slug, "status": "green",
            "notes": f"Dry-run: would set status: archived + last-archived: {today} on {path.relative_to(r).as_posix()}.",
            "dry_run": True,
        }

    new_text = apply_frontmatter(text, {"status": "archived", "last-archived": today})
    path.write_text(new_text, encoding="utf-8")
    return {
        "ok": True, "slug": slug, "status": "green",
        "notes": f"Archived {path.relative_to(r).as_posix()} (status: archived, last-archived: {today}).",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--restore", action="store_true",
                        help="Reverse: set status: active on a previously-archived page.")
    args = parser.parse_args(argv)
    result = archive_page(args.slug, dry_run=args.dry_run, restore=args.restore)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

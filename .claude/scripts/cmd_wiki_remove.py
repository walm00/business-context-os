#!/usr/bin/env python3
"""
cmd_wiki_remove.py — hard-delete a wiki page (and optionally its raw files).

DESTRUCTIVE. Mirrors `/wiki remove <slug>` chat path. The dashboard MUST
require explicit confirmation before invoking this — the script itself
refuses to run without --confirm to avoid accidental loss.

CLI:
    python .claude/scripts/cmd_wiki_remove.py --slug pricing-strategy --confirm
    python .claude/scripts/cmd_wiki_remove.py --slug pricing-strategy --confirm --dry-run
    python .claude/scripts/cmd_wiki_remove.py --slug pricing-strategy --confirm --keep-raw
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


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


def remove_page(slug: str, *, root: Path | None = None, dry_run: bool = False,
                keep_raw: bool = False) -> dict:
    r = root or repo_root()
    page = _resolve_page(slug, r)
    if page is None:
        return {
            "ok": False, "slug": slug, "status": "red",
            "notes": f"No wiki page found for slug {slug!r}.",
        }

    raw_dir = r / "docs" / "_wiki" / "raw"
    raw_candidates = list(raw_dir.rglob(f"{slug}*")) if raw_dir.is_dir() else []
    will_remove: list[str] = [page.relative_to(r).as_posix()]
    if not keep_raw:
        will_remove.extend(p.relative_to(r).as_posix() for p in raw_candidates)

    if dry_run:
        return {
            "ok": True, "slug": slug, "status": "amber",
            "notes": f"Dry-run: would delete {len(will_remove)} path(s).",
            "would_remove": will_remove,
            "dry_run": True,
        }

    # Use git rm where possible so deletions land in the index
    removed: list[str] = []
    for rel in will_remove:
        target = r / rel
        if not target.exists():
            continue
        try:
            subprocess.run(
                ["git", "-C", str(r), "rm", "-rf", "--quiet", rel],
                check=False, capture_output=True, text=True, timeout=10,
            )
            if target.exists():
                # Fallback for non-tracked files
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            removed.append(rel)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False, "slug": slug, "status": "red",
                "notes": f"Failed to remove {rel}: {type(exc).__name__}: {exc}",
                "removed": removed,
            }

    return {
        "ok": True, "slug": slug, "status": "green",
        "notes": f"Removed {len(removed)} path(s) for slug {slug}.",
        "removed": removed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--confirm", action="store_true",
                        help="Required — refuses to run without it.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-raw", action="store_true",
                        help="Leave docs/_wiki/raw/<slug>* files in place.")
    args = parser.parse_args(argv)
    if not args.confirm and not args.dry_run:
        print(json.dumps({
            "ok": False, "slug": args.slug, "status": "red",
            "notes": "Refusing to run without --confirm. Add --confirm to acknowledge destructive operation.",
        }, ensure_ascii=False))
        return 2
    result = remove_page(args.slug, dry_run=args.dry_run, keep_raw=args.keep_raw)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

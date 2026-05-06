#!/usr/bin/env python3
"""
cmd_wiki_queue_add.py — append a URL to docs/_wiki/queue.md without fetching.

User-triggered command (mirrors `/wiki queue <url>` chat path). Mechanical:
just appends a line to the queue file. The actual fetch happens later via
`/wiki run` (chat-driven, LLM-required).

Idempotent — if the URL already appears in queue.md (Pending or Completed),
the script is a no-op and reports the existing line.

CLI:
    python .claude/scripts/cmd_wiki_queue_add.py --url https://example.com
    python .claude/scripts/cmd_wiki_queue_add.py --url https://example.com --dry-run
"""

from __future__ import annotations

import argparse
import json
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


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def queue_add(url: str, *, root: Path | None = None, dry_run: bool = False) -> dict:
    r = root or repo_root()
    queue_path = r / "docs" / "_wiki" / "queue.md"
    if not (r / "docs" / "_wiki").is_dir():
        return {
            "ok": False, "url": url, "status": "red",
            "notes": "No docs/_wiki/ zone. Run /wiki init first.",
        }

    normalized = _normalize_url(url)
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        return {
            "ok": False, "url": url, "status": "red",
            "notes": f"URL must start with http:// or https:// — got {normalized!r}.",
        }

    existing = queue_path.read_text(encoding="utf-8") if queue_path.is_file() else ""
    if normalized in existing:
        return {
            "ok": True, "url": normalized, "status": "green",
            "notes": "URL already present in queue.md; no change.",
            "no_op": True,
        }

    if dry_run:
        return {
            "ok": True, "url": normalized, "status": "green",
            "notes": f"Dry-run: would append {normalized} under ## Pending in queue.md.",
            "dry_run": True,
        }

    if not queue_path.is_file():
        queue_path.write_text(
            "# Wiki Queue\n\n## Pending\n\n## Completed\n", encoding="utf-8"
        )
        existing = queue_path.read_text(encoding="utf-8")

    # Insert under ## Pending
    if "## Pending" in existing:
        marker = "## Pending\n"
        idx = existing.index(marker) + len(marker)
        new = existing[:idx] + f"- {normalized}\n" + existing[idx:]
    else:
        new = existing.rstrip() + f"\n\n## Pending\n- {normalized}\n"
    queue_path.write_text(new, encoding="utf-8")

    return {
        "ok": True, "url": normalized, "status": "green",
        "notes": f"Queued {normalized} under ## Pending in docs/_wiki/queue.md. Run /wiki run via chat to fetch.",
        "follow_up_chat_command": f"wiki run {normalized}",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = queue_add(args.url, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

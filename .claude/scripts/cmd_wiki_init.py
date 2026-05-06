#!/usr/bin/env python3
"""
cmd_wiki_init.py — scaffold the wiki zone (mirrors `/wiki init` chat path).

Creates docs/_wiki/{pages,source-summary,raw}/ + queue.md + .schema.yml +
.config.yml from framework templates. Idempotent — running on an existing
wiki zone is a no-op.

CLI:
    python .claude/scripts/cmd_wiki_init.py
    python .claude/scripts/cmd_wiki_init.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
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


_QUEUE_TEMPLATE = """# Wiki Queue

URLs to ingest into the wiki zone. The `bcos-wiki` skill drains this queue
via `/wiki run`. Each URL appears under one of the two sections below.

## Pending

(Add URLs here with `/wiki queue <url>` or via the dashboard.)

## Completed

(Processed URLs move here automatically once `/wiki run` succeeds.)
"""


def init(*, root: Path | None = None, dry_run: bool = False) -> dict:
    r = root or repo_root()
    wiki = r / "docs" / "_wiki"
    pages_dir = wiki / "pages"
    summary_dir = wiki / "source-summary"
    raw_dir = wiki / "raw"
    queue = wiki / "queue.md"
    schema = wiki / ".schema.yml"
    config = wiki / ".config.yml"

    schema_tmpl = r / "docs" / "_bcos-framework" / "templates" / "_wiki.schema.yml.tmpl"
    config_tmpl = r / "docs" / "_bcos-framework" / "templates" / "_wiki.config.yml.tmpl"

    will_create: list[str] = []
    if not pages_dir.is_dir():
        will_create.append("docs/_wiki/pages/")
    if not summary_dir.is_dir():
        will_create.append("docs/_wiki/source-summary/")
    if not raw_dir.is_dir():
        will_create.append("docs/_wiki/raw/")
    if not queue.is_file():
        will_create.append("docs/_wiki/queue.md")
    if not schema.is_file() and schema_tmpl.is_file():
        will_create.append("docs/_wiki/.schema.yml")
    if not config.is_file() and config_tmpl.is_file():
        will_create.append("docs/_wiki/.config.yml")

    if not will_create:
        return {
            "ok": True, "status": "green",
            "notes": "Wiki zone already initialized; nothing to do.",
            "created": [],
            "no_op": True,
        }

    if dry_run:
        return {
            "ok": True, "status": "green",
            "notes": f"Dry-run: would create {len(will_create)} item(s).",
            "would_create": will_create,
            "dry_run": True,
        }

    today = datetime.now(timezone.utc).date().isoformat()
    pages_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    if not queue.is_file():
        queue.write_text(_QUEUE_TEMPLATE, encoding="utf-8")

    if not schema.is_file() and schema_tmpl.is_file():
        text = schema_tmpl.read_text(encoding="utf-8").replace("TODAY", today)
        schema.write_text(text, encoding="utf-8")

    if not config.is_file() and config_tmpl.is_file():
        text = config_tmpl.read_text(encoding="utf-8").replace("TODAY", today)
        config.write_text(text, encoding="utf-8")

    return {
        "ok": True, "status": "green",
        "notes": f"Initialized wiki zone — created {len(will_create)} item(s).",
        "created": will_create,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = init(dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

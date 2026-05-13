#!/usr/bin/env python3
"""
cmd_wiki_init.py — scaffold the wiki zone (mirrors `/wiki init --defaults`).

Creates the complete wiki zone:
  docs/_wiki/
    .config.yml       (display_name = git repo basename; defaults: standard, all source-types, batch, true, true)
    .schema.yml       (from framework template)
    queue.md          (Path A URL queue)
    overview.md       (cross-source synthesis stub)
    log.md            (append-only ingest history stub)
    README.md         (one-paragraph zone overview)
    index.md          (derived; refreshed via refresh_wiki_index.py)
    pages/            (Path B internal pages — runbooks, SOPs, decisions, etc.)
    source-summary/   (Path A external captures)
    raw/{web,github,youtube,local}/  (immutable raw captures)
    .archive/         (soft-deleted pages)

Idempotent — running on an existing wiki zone is a no-op (returns "already initialized").

This script is the headless backend for:
  * /wiki init --defaults  (the chat command's defaults mode)
  * ensure_wiki_zone.py    (plugin install_here.py callers needing substrate readiness)
  * The interactive /wiki init flow (which calls this and then offers schema customization)

CLI:
    python .claude/scripts/cmd_wiki_init.py
    python .claude/scripts/cmd_wiki_init.py --dry-run
    python .claude/scripts/cmd_wiki_init.py --display-name "Custom Name"
"""

from __future__ import annotations

import argparse
import json
import subprocess
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


def resolve_display_name(root: Path, override: str | None = None) -> str:
    """Display name = override > git repo basename > 'wiki' fallback.

    The wiki is multi-purpose by design (plugin-storage-contract Rule 2);
    display_name is just a label, not a single-domain narrowing.
    """
    if override and override.strip():
        return override.strip()
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).name
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return root.name or "wiki"


# Sensible defaults for --defaults / ensure_wiki_zone mode.
# Match init.md's interactive defaults exactly.
DEFAULTS = {
    "detail_level": "standard",
    "source_types": "[web, github, youtube]",  # YAML inline list
    "auto_lint": "batch",
    "auto_mark_complete": "true",
    "enable_path_b": "true",
}


_QUEUE_TEMPLATE = """# Wiki Queue

URLs to ingest into the wiki zone. The `bcos-wiki` skill drains this queue
via `/wiki run`. Each URL appears under one of the two sections below.

## Pending

(Add URLs here with `/wiki queue <url>` or via the dashboard.)

## Completed

(Processed URLs move here automatically once `/wiki run` succeeds.)
"""


def _render_template(template_path: Path, substitutions: dict[str, str]) -> str:
    """Read template, apply {{KEY}} → value substitutions, return text."""
    text = template_path.read_text(encoding="utf-8")
    for key, value in substitutions.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    # TODAY-only legacy substitution (some templates use bare TODAY, not {{TODAY}})
    text = text.replace("TODAY", substitutions.get("TODAY", ""))
    return text


def _readme_body(display_name: str) -> str:
    return f"""# {display_name} Wiki

This zone is managed by the `bcos-wiki` skill — invoke with `/wiki`.

The wiki is BCOS's universal long-form / cross-cutting content destination per
[plugin-storage-contract.md](../../docs/_bcos-framework/architecture/plugin-storage-contract.md)
Rule 2. It holds:

- **Operational truth** (`authority: canonical-process`) — runbooks, SOPs,
  how-tos, decision logs, post-mortems, playbooks, scripts-with-context
- **Internal reference** (`authority: internal-reference`) — glossaries, FAQs,
  derivative explainers
- **Plugin cross-cutting + external sources** — meeting transcripts,
  WhatsApp/Slack exports, research clippings, captured URLs / GitHub /
  YouTube (banner-cited to verbatim raw captures)

Page-type is in the frontmatter — folder structure is flat. See
[wiki-zone.md](../_bcos-framework/architecture/wiki-zone.md) for full rules.

## Layout

| Path | What's there |
|---|---|
| `pages/` | Internal authored pages (Path B). Page-type in frontmatter. |
| `source-summary/` | External URL captures (Path A). Three structural shapes. |
| `raw/<type>/` | Immutable raw captures by source type. |
| `queue.md` | Pending URLs awaiting Path A ingest. |
| `overview.md` | Authored cross-source synthesis. |
| `log.md` | Append-only ingest/refresh history. |
| `index.md` | **Derived** — regenerated by `refresh_wiki_index.py`. Do not hand-edit. |
| `.archive/` | Soft-deleted pages. |
| `.schema.yml` | Vocabulary registry (page-types, statuses, etc.). |
| `.schema.d/` | Plugin schema fragments (one file per plugin). |
| `.config.yml` | Runtime config (display name, defaults, paths). |

## Adding content

| Action | Command |
|---|---|
| Drop a local runbook / SOP / script-with-context | `/wiki create from <path>` |
| Promote an `_inbox/` capture | `/wiki promote docs/_inbox/<file>` |
| Queue a URL for later | `/wiki queue <url>` |
| Ingest queued URLs | `/wiki run` |
| Single-shot URL ingest | `/wiki run <url>` |

## Authority

`docs/*.md` canonical wins over `_wiki/pages/` operational truth wins over
`_wiki/source-summary/` external reference. See
[wiki-zone.md "Authority Semantics"](../_bcos-framework/architecture/wiki-zone.md#authority-semantics-schema-12)
for the full hierarchy and lint rules.
"""


def _overview_body(display_name: str, today: str) -> str:
    return f"""---
name: "{display_name} wiki overview"
type: wiki
cluster: "Framework Evolution"
version: 1.0.0
status: active
created: {today}
last-updated: {today}
domain: "Cross-source synthesis for {display_name}"
exclusively-owns:
  - wiki overview synthesis
strictly-avoids: []
page-type: glossary
last-reviewed: {today}
sources: []
---

# {display_name} overview

No sources ingested yet.
"""


def _log_body(display_name: str, today: str) -> str:
    return f"""---
name: "{display_name} wiki log"
type: reference
cluster: "Framework Evolution"
version: 1.0.0
status: active
created: {today}
last-updated: {today}
---

# {display_name} wiki log

Newest entries first. This file is append-only.

- {today} — Wiki zone initialized (cmd_wiki_init.py / `/wiki init --defaults`). Display name: "{display_name}".
"""


def init(*, root: Path | None = None, dry_run: bool = False, display_name: str | None = None) -> dict:
    """Idempotent scaffold of docs/_wiki/. Returns a JSON-serializable result.

    Args:
        root: repo root (defaults to BCOS_REPO_ROOT env or script parents[1])
        dry_run: report what would be created, do not write
        display_name: override for {{DOMAIN}} substitution (default: git repo basename)

    Returns:
        {"ok": bool, "status": "green"|"red", "notes": str, "created": [paths], "no_op": bool?}
    """
    r = root or repo_root()
    wiki = r / "docs" / "_wiki"
    pages_dir = wiki / "pages"
    summary_dir = wiki / "source-summary"
    raw_dir = wiki / "raw"
    archive_dir = wiki / ".archive"
    queue = wiki / "queue.md"
    schema = wiki / ".schema.yml"
    config = wiki / ".config.yml"
    overview = wiki / "overview.md"
    log = wiki / "log.md"
    readme = wiki / "README.md"

    schema_tmpl = r / "docs" / "_bcos-framework" / "templates" / "_wiki.schema.yml.tmpl"
    config_tmpl = r / "docs" / "_bcos-framework" / "templates" / "_wiki.config.yml.tmpl"

    # Resolve display_name early so dry-run can echo it.
    resolved_display_name = resolve_display_name(r, display_name)

    will_create: list[str] = []
    if not pages_dir.is_dir():
        will_create.append("docs/_wiki/pages/")
    if not summary_dir.is_dir():
        will_create.append("docs/_wiki/source-summary/")
    if not raw_dir.is_dir():
        will_create.append("docs/_wiki/raw/")
    if not archive_dir.is_dir():
        will_create.append("docs/_wiki/.archive/")
    if not queue.is_file():
        will_create.append("docs/_wiki/queue.md")
    if not schema.is_file() and schema_tmpl.is_file():
        will_create.append("docs/_wiki/.schema.yml")
    if not config.is_file() and config_tmpl.is_file():
        will_create.append("docs/_wiki/.config.yml")
    if not overview.is_file():
        will_create.append("docs/_wiki/overview.md")
    if not log.is_file():
        will_create.append("docs/_wiki/log.md")
    if not readme.is_file():
        will_create.append("docs/_wiki/README.md")

    if not will_create:
        return {
            "ok": True, "status": "green",
            "notes": "Wiki zone already initialized; nothing to do.",
            "created": [],
            "no_op": True,
            "display_name": resolved_display_name,
        }

    if dry_run:
        return {
            "ok": True, "status": "green",
            "notes": f"Dry-run: would create {len(will_create)} item(s).",
            "would_create": will_create,
            "dry_run": True,
            "display_name": resolved_display_name,
        }

    today = datetime.now(timezone.utc).date().isoformat()

    substitutions = {
        "DOMAIN": resolved_display_name,
        "TODAY": today,
        "DETAIL_LEVEL": DEFAULTS["detail_level"],
        "SOURCE_TYPES_LIST": DEFAULTS["source_types"],
        "AUTO_LINT": DEFAULTS["auto_lint"],
        "AUTO_MARK_COMPLETE": DEFAULTS["auto_mark_complete"],
        "ENABLE_PATH_B": DEFAULTS["enable_path_b"],
    }

    pages_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    # Create raw subdirectories matching default source-types + local
    for sub in ("web", "github", "youtube", "local"):
        (raw_dir / sub).mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    if not queue.is_file():
        queue.write_text(_QUEUE_TEMPLATE, encoding="utf-8")

    if not schema.is_file() and schema_tmpl.is_file():
        schema.write_text(_render_template(schema_tmpl, substitutions), encoding="utf-8")

    if not config.is_file() and config_tmpl.is_file():
        config.write_text(_render_template(config_tmpl, substitutions), encoding="utf-8")

    if not overview.is_file():
        overview.write_text(_overview_body(resolved_display_name, today), encoding="utf-8")

    if not log.is_file():
        log.write_text(_log_body(resolved_display_name, today), encoding="utf-8")

    if not readme.is_file():
        readme.write_text(_readme_body(resolved_display_name), encoding="utf-8")

    return {
        "ok": True, "status": "green",
        "notes": f"Initialized wiki zone — created {len(will_create)} item(s).",
        "created": will_create,
        "display_name": resolved_display_name,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be created; do not write")
    parser.add_argument("--display-name", default=None,
                        help="override display name (default: git repo basename, fallback 'wiki')")
    args = parser.parse_args(argv)
    result = init(dry_run=args.dry_run, display_name=args.display_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

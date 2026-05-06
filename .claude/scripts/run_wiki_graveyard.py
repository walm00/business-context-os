#!/usr/bin/env python3
"""
run_wiki_graveyard.py — monthly archive-candidate scan, runnable headless.

Walks every wiki page and emits up to three classes of finding per page:

  graveyard-stale     last-reviewed older than thresholds.graveyard-days
                      (default 365)
  orphan-pages        no other wiki page lists this page in builds-on AND
                      file mtime > thresholds.orphan-grace-days (default 365)
  retired-page-type   page-type value not in the active page-types list
                      from docs/_wiki/.schema.yml (or the framework template)

Reference: .claude/skills/schedule-dispatcher/references/job-wiki-graveyard.md

CLI:
    python .claude/scripts/run_wiki_graveyard.py
    python .claude/scripts/run_wiki_graveyard.py --dry-run
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _wiki_job_runner import (  # noqa: E402
    iter_wiki_pages,
    no_wiki_zone,
    parse_iso_date,
    repo_root,
    run_wiki_job,
)
from _wiki_yaml import parse_frontmatter  # noqa: E402


JOB_ID = "wiki-graveyard"
DEFAULT_GRAVEYARD_DAYS = 365
DEFAULT_ORPHAN_GRACE_DAYS = 365


# ---------------------------------------------------------------------------
# Schema discovery: thresholds + active page-types
# ---------------------------------------------------------------------------

_PAGE_TYPE_BLOCK_RE = re.compile(
    r"^page-types:\s*\n(.*?)(?=^\S|\Z)", re.MULTILINE | re.DOTALL
)
_PAGE_TYPE_KEY_RE = re.compile(r"^\s{2}([a-z][a-z0-9-]*):", re.MULTILINE)
_THRESHOLDS_BLOCK_RE = re.compile(
    r"^thresholds:\s*\n(.*?)(?=^\S|\Z)", re.MULTILINE | re.DOTALL
)
_THRESHOLD_RE = re.compile(r"^\s+([a-z-]+):\s*(\d+)", re.MULTILINE)


def _load_schema(root: Path) -> dict:
    """Return active page-types + threshold values, falling back to template."""
    candidates = (
        root / "docs" / "_wiki" / ".schema.yml",
        root / "docs" / "_bcos-framework" / "templates" / "_wiki.schema.yml.tmpl",
    )
    text = ""
    for c in candidates:
        if c.is_file():
            try:
                text = c.read_text(encoding="utf-8")
                break
            except OSError:
                continue

    active_types: set[str] = set()
    graveyard_days = DEFAULT_GRAVEYARD_DAYS
    orphan_grace_days = DEFAULT_ORPHAN_GRACE_DAYS

    if text:
        m = _PAGE_TYPE_BLOCK_RE.search(text)
        if m:
            for k in _PAGE_TYPE_KEY_RE.finditer(m.group(1)):
                active_types.add(k.group(1))

        m2 = _THRESHOLDS_BLOCK_RE.search(text)
        if m2:
            for t in _THRESHOLD_RE.finditer(m2.group(1)):
                key, val = t.group(1), int(t.group(2))
                if key == "graveyard-days":
                    graveyard_days = val
                elif key == "orphan-grace-days":
                    orphan_grace_days = val

    return {
        "active_types": active_types,
        "graveyard_days": graveyard_days,
        "orphan_grace_days": orphan_grace_days,
    }


def _file_mtime_date(path: Path) -> date | None:
    try:
        return date.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def detect_findings(root: Path | None = None) -> list[dict]:
    r = root or repo_root()
    if no_wiki_zone(r):
        return []

    schema = _load_schema(r)
    active_types = schema["active_types"]
    graveyard_days = schema["graveyard_days"]
    orphan_grace_days = schema["orphan_grace_days"]
    today = date.today()

    pages = list(iter_wiki_pages(r, subdir="pages"))

    # Build inbound-link map: page filename → set of pages that builds-on it.
    inbound: dict[str, set[str]] = {}
    pages_dir = r / "docs" / "_wiki" / "pages"
    for page in pages:
        fm = parse_frontmatter(page) or {}
        builds_on = fm.get("builds-on") or fm.get("builds_on") or []
        if not isinstance(builds_on, list):
            continue
        for ref in builds_on:
            ref_path = r / str(ref).strip()
            if ref_path.parent == pages_dir:
                inbound.setdefault(ref_path.name, set()).add(page.name)

    findings: list[dict] = []

    for page in pages:
        fm = parse_frontmatter(page) or {}
        page_rel = str(page.relative_to(r)).replace("\\", "/")

        # graveyard-stale
        last_reviewed = parse_iso_date(fm.get("last-reviewed") or fm.get("last_reviewed"))
        if last_reviewed is not None:
            age_days = (today - last_reviewed.date()).days
            if age_days > graveyard_days:
                findings.append({
                    "finding_type": "graveyard-stale",
                    "verdict": "amber",
                    "emitted_by": JOB_ID,
                    "finding_attrs": {
                        "file": page_rel,
                        "last_reviewed_date": last_reviewed.date().isoformat(),
                        "age_days": age_days,
                        "threshold_days": graveyard_days,
                    },
                    "suggested_actions": ["graveyard-stale-archive"],
                })

        # orphan-pages
        if page.name not in inbound:
            mtime = _file_mtime_date(page)
            last_edit_days = (today - mtime).days if mtime else orphan_grace_days + 1
            if last_edit_days > orphan_grace_days:
                findings.append({
                    "finding_type": "orphan-pages",
                    "verdict": "amber",
                    "emitted_by": JOB_ID,
                    "finding_attrs": {
                        "wiki_file": page_rel,
                        "last_edit_days": last_edit_days,
                        "grace_days": orphan_grace_days,
                    },
                    "suggested_actions": ["orphan-page-archive"],
                })

        # retired-page-type
        page_type = fm.get("page-type") or fm.get("type")
        if page_type and active_types and page_type not in active_types:
            findings.append({
                "finding_type": "retired-page-type",
                "verdict": "amber",
                "emitted_by": JOB_ID,
                "finding_attrs": {
                    "wiki_file": page_rel,
                    "retired_type": page_type,
                },
                "suggested_actions": ["retired-page-type-migrate"],
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
            "notes": "No docs/_wiki/ zone in this repo — wiki-graveyard skipped cleanly.",
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
                f"{f['finding_type']}: {f['finding_attrs'].get('file') or f['finding_attrs'].get('wiki_file', '?')}"
                for f in findings
            ],
            "notes": f"Dry-run — would write {len(findings)} finding(s) to digest.",
            "dry_run": True,
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if findings:
        notes = f"{len(findings)} archive candidate(s) flagged across the wiki."
    else:
        notes = "No archive candidates — wiki is clean."

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

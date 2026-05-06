#!/usr/bin/env python3
"""
run_wiki_source_refresh.py — weekly source-summary freshness check.

Two-tier check for `docs/_wiki/source-summary/*.md` pages whose
`page-type: source-summary`:

  quick tier   last-fetched ≥ stale_threshold/4 days ago → conditional GET
               (If-None-Match / If-Modified-Since); changed upstream emits
               source-summary-upstream-changed.

  full tier    last-fetched ≥ stale_threshold days ago → emits refresh-due;
               no auto-rewrite (user runs /wiki refresh <slug>).

Network calls are skipped when BCOS_OFFLINE=1; all network errors are
caught and logged so the job never raises.

Reference: .claude/skills/schedule-dispatcher/references/job-wiki-source-refresh.md

CLI:
    python .claude/scripts/run_wiki_source_refresh.py
    python .claude/scripts/run_wiki_source_refresh.py --dry-run
    BCOS_OFFLINE=1 python .claude/scripts/run_wiki_source_refresh.py
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


JOB_ID = "wiki-source-refresh"
DEFAULT_STALE_DAYS = 30
MAX_QUICK_CHECKS_PER_RUN = 20

_THRESHOLDS_BLOCK_RE = re.compile(
    r"^thresholds:\s*\n(.*?)(?=^\S|\Z)", re.MULTILINE | re.DOTALL
)
_THRESHOLD_RE = re.compile(r"^\s+([a-z-]+):\s*(\d+)", re.MULTILINE)


def _load_stale_threshold(root: Path) -> int:
    candidates = (
        root / "docs" / "_wiki" / ".schema.yml",
        root / "docs" / "_bcos-framework" / "templates" / "_wiki.schema.yml.tmpl",
    )
    for c in candidates:
        if not c.is_file():
            continue
        try:
            text = c.read_text(encoding="utf-8")
        except OSError:
            continue
        m = _THRESHOLDS_BLOCK_RE.search(text)
        if m:
            for t in _THRESHOLD_RE.finditer(m.group(1)):
                if t.group(1) == "stale-threshold-days":
                    return int(t.group(2))
    return DEFAULT_STALE_DAYS


def _head_check(url: str, etag: str | None, last_modified: str | None) -> str:
    """Return 'changed', 'unchanged', or 'error'."""
    if os.environ.get("BCOS_OFFLINE"):
        return "unchanged"
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        if etag:
            req.add_header("If-None-Match", etag)
        elif last_modified:
            req.add_header("If-Modified-Since", last_modified)
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = resp.getcode()
            if code == 304:
                return "unchanged"
            if 200 <= code < 300:
                return "changed"
            return "error"
    except Exception:  # noqa: BLE001 — network is inherently flaky
        return "error"


def detect_findings(root: Path | None = None) -> list[dict]:
    r = root or repo_root()
    source_dir = r / "docs" / "_wiki" / "source-summary"
    if not source_dir.is_dir():
        return []

    stale_days = _load_stale_threshold(r)
    quick_days = max(1, stale_days // 4)
    today = date.today()

    findings: list[dict] = []
    quick_done = 0

    for page in iter_wiki_pages(r, subdir="source-summary"):
        fm = parse_frontmatter(page) or {}
        if fm.get("page-type") != "source-summary":
            continue
        last_fetched = parse_iso_date(fm.get("last-fetched") or fm.get("last_fetched"))
        if last_fetched is None:
            continue

        age_days = (today - last_fetched.date()).days
        rel = str(page.relative_to(r)).replace("\\", "/")

        if age_days >= stale_days:
            findings.append({
                "finding_type": "refresh-due",
                "verdict": "amber",
                "emitted_by": JOB_ID,
                "finding_attrs": {
                    "file": rel,
                    "last_fetched": last_fetched.date().isoformat(),
                    "age_days": age_days,
                    "days_overdue": age_days - stale_days,
                },
                "suggested_actions": ["source-summary-refresh"],
            })
            continue

        if age_days >= quick_days and quick_done < MAX_QUICK_CHECKS_PER_RUN:
            url = fm.get("source-url") or fm.get("url")
            if not url:
                continue
            quick_done += 1
            etag = fm.get("etag")
            last_mod = fm.get("last-modified")
            status = _head_check(str(url), etag, last_mod)
            if status == "changed":
                findings.append({
                    "finding_type": "source-summary-upstream-changed",
                    "verdict": "amber",
                    "emitted_by": JOB_ID,
                    "finding_attrs": {
                        "wiki_file": rel,
                        "source_url": str(url),
                        "last_fetched": last_fetched.date().isoformat(),
                        "age_days": age_days,
                    },
                    "suggested_actions": ["source-summary-refresh"],
                })

    return findings


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
            "notes": "No docs/_wiki/ zone in this repo — wiki-source-refresh skipped cleanly.",
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

    notes = (
        f"Source freshness check: {len(findings)} candidate(s) need refresh."
        if findings
        else "All source summaries within freshness threshold."
    )
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

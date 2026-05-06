#!/usr/bin/env python3
"""
run_wiki_stale_propagation.py — wiki staleness scan, runnable headless.

For every wiki page under `docs/_wiki/pages/` that declares `builds-on:`,
compare each source's last-updated timestamp against the wiki page's
own `last-reviewed`. Sources updated AFTER the page was last reviewed
trigger a `stale-propagation` finding.

Reference: .claude/skills/schedule-dispatcher/references/job-wiki-stale-propagation.md

Output: per-job JSON line on stdout (consumed by _post_run_job_now in
the dashboard) + diary entry + sidecar merge via _wiki_job_runner.

CLI:
    python .claude/scripts/run_wiki_stale_propagation.py
    python .claude/scripts/run_wiki_stale_propagation.py --dry-run
"""

from __future__ import annotations

import json
import sys
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


JOB_ID = "wiki-stale-propagation"
RED_THRESHOLD = 3  # ≥3 stale sources on a single page → cluster-drift signal


def _resolve_source_path(source: str, root: Path) -> Path | None:
    """Resolve a builds-on entry to a file path. Accepts:
    - Full repo-relative path: "docs/strategy/icp.md"
    - Bare slug: "icp" → resolves to "docs/icp.md" (best-effort)
    - Wiki-link form: "[wiki:foo]" → "docs/_wiki/pages/foo.md"
    Returns None when the target can't be resolved.
    """
    s = (source or "").strip()
    if not s:
        return None
    if s.startswith("[wiki:") and s.endswith("]"):
        slug = s[len("[wiki:"):-1].strip()
        candidate = root / "docs" / "_wiki" / "pages" / f"{slug}.md"
        return candidate if candidate.is_file() else None
    if s.endswith(".md"):
        candidate = root / s
        return candidate if candidate.is_file() else None
    # Bare slug — best-effort search under docs/.
    for base in (root / "docs",):
        candidate = base / f"{s}.md"
        if candidate.is_file():
            return candidate
    return None


def _last_updated(path: Path) -> "datetime | None":
    """Read frontmatter `last-updated` (or `last_updated`) → datetime."""
    fm = parse_frontmatter(path) or {}
    raw = fm.get("last-updated") or fm.get("last_updated")
    return parse_iso_date(raw) if raw else None


def detect_findings(root: Path | None = None) -> list[dict]:
    """Walk every wiki page, compare builds-on freshness vs last-reviewed.

    Returns a list of typed-event findings ready for sidecar merge.
    """
    r = root or repo_root()
    findings: list[dict] = []
    if no_wiki_zone(r):
        return findings

    for page in iter_wiki_pages(r, subdir="pages"):
        fm = parse_frontmatter(page) or {}
        builds_on = fm.get("builds-on") or fm.get("builds_on") or []
        if not isinstance(builds_on, list) or not builds_on:
            continue

        last_reviewed = parse_iso_date(fm.get("last-reviewed") or fm.get("last_reviewed"))
        if last_reviewed is None:
            # No last-reviewed means we can't compute drift — skip silently.
            # The wiki-graveyard job catches "missing review date" via a
            # different finding type.
            continue

        page_rel = str(page.relative_to(r)).replace("\\", "/")
        stale_sources: list[tuple[str, str]] = []  # (source_rel, source_updated_iso)
        max_lag_days = 0

        for src in builds_on:
            src_path = _resolve_source_path(str(src), r)
            if src_path is None:
                continue
            src_updated = _last_updated(src_path)
            if src_updated is None:
                continue
            if src_updated > last_reviewed:
                src_rel = str(src_path.relative_to(r)).replace("\\", "/")
                stale_sources.append((src_rel, src_updated.date().isoformat()))
                lag = (src_updated.date() - last_reviewed.date()).days
                if lag > max_lag_days:
                    max_lag_days = lag

        if not stale_sources:
            continue

        # Emit one finding per (page, source) pair so the cockpit can
        # surface targeted "mark-reviewed" or "open-for-edit" cards
        # rather than one umbrella card per page.
        for src_rel, src_updated in stale_sources:
            verdict = "red" if len(stale_sources) >= RED_THRESHOLD else "amber"
            findings.append({
                "finding_type": "stale-propagation",
                "verdict": verdict,
                "emitted_by": JOB_ID,
                "finding_attrs": {
                    "wiki_file": page_rel,
                    "source_file": src_rel,
                    "source_updated_date": src_updated,
                    "last_reviewed_date": last_reviewed.date().isoformat(),
                    "stale_builds_on_count": len(stale_sources),
                    "max_lag_days": max_lag_days,
                },
                "suggested_actions": ["mark-reviewed", "open-for-edit"],
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
            "notes": "No docs/_wiki/ zone in this repo — wiki-stale-propagation skipped cleanly.",
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0

    findings = detect_findings(r)

    if dry_run:
        result = {
            "verdict": "green" if not findings else ("red" if any(f["verdict"] == "red" for f in findings) else "amber"),
            "findings_count": len(findings),
            "auto_fixed": [],
            "actions_needed": [f"stale-propagation: {f['finding_attrs']['wiki_file']}" for f in findings],
            "notes": f"Dry-run — would write {len(findings)} finding(s) to digest.",
            "dry_run": True,
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0

    notes = ""
    if findings:
        affected = len({f["finding_attrs"]["wiki_file"] for f in findings})
        notes = f"{len(findings)} stale source link(s) across {affected} wiki page(s)."
    else:
        notes = "All wiki pages are up to date with their builds-on sources."

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

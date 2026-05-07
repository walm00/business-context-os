#!/usr/bin/env python3
"""wiki_failed_ingest.py — surface wiki ingest failure modes as findings.

The wiki pipeline has three failure shapes that historically lived only in
lint output and never reached the dispatcher's amber-stream digest:

  1. **Stuck queue items** — URLs in `docs/_wiki/queue.md ## Pending` whose
     line hasn't moved in N days. Either the user hasn't run `/wiki run`,
     or fetch keeps failing silently.
  2. **Provenance-missing source summaries** — files in
     `docs/_wiki/source-summary/` whose frontmatter `provenance.source` is
     absent or empty. These violate Path A's contract (every external
     summary must cite its source) but the wiki schema linter only flags
     them on validate, not in the daily digest.
  3. **Schema-violation drafts** — files in `docs/_wiki/raw/local/` or
     `docs/_wiki/pages/` whose YAML frontmatter fails to parse. These get
     dropped from the wiki index silently.

This job is mechanical-only and emits per-issue findings; humans decide what
to do (re-fetch, edit frontmatter, archive, etc.). Auto-fix is intentionally
not whitelisted — these failure modes carry editorial judgement.

CLI:
    python .claude/scripts/wiki_failed_ingest.py
        [--root <repo_root>] [--stale-days <N>] [--json]

Default --stale-days = 14.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _scan_stuck_queue(wiki_dir: Path, stale_days: int) -> list[dict]:
    queue = wiki_dir / "queue.md"
    if not queue.is_file():
        return []
    text = queue.read_text(encoding="utf-8", errors="replace")
    # Capture the "## Pending" section only.
    m = re.search(r"##\s+Pending\s*\n(.*?)(?:\n##\s+|\Z)", text, re.DOTALL)
    if not m:
        return []
    pending = m.group(1)
    # Lines that look like list items with URLs
    urls = re.findall(r"^\s*[-*]\s+(https?://\S+)", pending, re.MULTILINE)
    if not urls:
        return []
    age_days = (datetime.now(timezone.utc).timestamp() - queue.stat().st_mtime) / 86400
    if age_days < stale_days:
        return []
    return [{
        "type": "wiki-failed-ingest:stuck-queue",
        "verdict": "amber",
        "path": "docs/_wiki/queue.md",
        "pending_count": len(urls),
        "queue_age_days": round(age_days, 1),
        "note": (
            f"{len(urls)} URL(s) have been in queue.md ## Pending for "
            f"{round(age_days, 0)} days. Run /wiki run to drain, or move them "
            "to ## Completed if they're no longer relevant."
        ),
        "sample_urls": urls[:3],
    }]


def _scan_missing_provenance(wiki_dir: Path) -> list[dict]:
    summary_dir = wiki_dir / "source-summary"
    if not summary_dir.is_dir():
        return []
    findings = []
    for path in sorted(summary_dir.rglob("*.md")):
        if path.name.startswith("."):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end < 0:
            continue
        frontmatter = text[3:end]
        # Cheap detection: provenance.source missing/empty
        prov_match = re.search(r"^\s*provenance\s*:\s*\n((?:\s+[^\n]*\n)+)", frontmatter, re.MULTILINE)
        source_present = False
        if prov_match:
            block = prov_match.group(1)
            src = re.search(r"^\s+source\s*:\s*(\S.*)$", block, re.MULTILINE)
            source_present = bool(src and src.group(1).strip() not in {"''", '""', "null", "~"})
        if not source_present:
            findings.append({
                "type": "wiki-failed-ingest:provenance-missing",
                "verdict": "amber",
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "note": (
                    "source-summary file is missing provenance.source — "
                    "every external summary must cite the URL/document it "
                    "summarises. Edit the file or move it to _archive/."
                ),
            })
    return findings


def _scan_schema_violations(wiki_dir: Path) -> list[dict]:
    """Detect files whose frontmatter doesn't parse as YAML at all."""
    findings = []
    for sub in ("raw/local", "pages"):
        d = wiki_dir / sub
        if not d.is_dir():
            continue
        for path in sorted(d.rglob("*.md")):
            if path.name.startswith(".") or path.name == "index.md":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if not text.startswith("---"):
                findings.append({
                    "type": "wiki-failed-ingest:schema-violation",
                    "verdict": "amber",
                    "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "note": "Wiki file is missing the YAML frontmatter delimiter (---). It will be invisible to the wiki index and search.",
                })
                continue
            end = text.find("\n---", 3)
            if end < 0:
                findings.append({
                    "type": "wiki-failed-ingest:schema-violation",
                    "verdict": "amber",
                    "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "note": "Wiki file's YAML frontmatter is unterminated (no closing ---).",
                })
    return findings


def run(root: Path, stale_days: int) -> dict:
    wiki = root / "docs" / "_wiki"
    if not wiki.is_dir():
        return {
            "verdict": "green",
            "findings_count": 0,
            "auto_fixed": [],
            "actions_needed": [],
            "notes": "Wiki zone not enabled; failed-ingest scan skipped.",
        }
    findings: list[dict] = []
    findings.extend(_scan_stuck_queue(wiki, stale_days))
    findings.extend(_scan_missing_provenance(wiki))
    findings.extend(_scan_schema_violations(wiki))
    verdict = "amber" if findings else "green"
    return {
        "verdict": verdict,
        "findings_count": len(findings),
        "auto_fixed": [],
        "actions_needed": [
            f"{f['type'].split(':', 1)[1]}: {f['path']} — {f['note']}"
            for f in findings
        ],
        "findings": findings,
        "notes": (
            f"{len(findings)} wiki ingest issue(s) found"
            if findings else "All wiki ingest paths clean."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan wiki for failed-ingest dead-letter conditions.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--stale-days", type=int, default=14)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    result = run(args.root.resolve(), args.stale_days)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"verdict: {result['verdict']}")
        print(f"findings: {result['findings_count']}")
        for line in result["actions_needed"]:
            print(f"  - {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

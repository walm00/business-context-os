#!/usr/bin/env python3
"""
run_wiki_canonical_drift.py — daily mechanical scan for canonical-drift suggestions.

For every wiki page with `authority: external-reference` (or its mechanical
default) that declares `builds-on:` canonical docs, emit a
`wiki-canonical-drift-suggestion` finding when:
  * The wiki page has a numeric fact diverging from the canonical doc, AND
  * The canonical doc's `last-updated` is older than `STALE_CANONICAL_DAYS`
    (default 180 days, ≈ 6 months).

Reference: .claude/skills/schedule-dispatcher/references/job-wiki-canonical-drift.md

The job NEVER edits canonical docs. It only emits findings into the digest
sidecar. Schema 1.2 Class D from `_wiki_triage`.

CLI:
    python .claude/scripts/run_wiki_canonical_drift.py
        # default: writes via run_wiki_job() into the dispatcher sidecar

    python .claude/scripts/run_wiki_canonical_drift.py --root <repo-root> \\
        --sidecar-dir <dir>
        # test/dispatcher mode: writes a self-contained JSON to <dir>
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

from _wiki_triage import classify  # noqa: E402

JOB_ID = "wiki-canonical-drift"


def _wiki_pages(root: Path) -> list[Path]:
    base = root / "docs" / "_wiki"
    out: list[Path] = []
    for sub in ("pages", "source-summary"):
        d = base / sub
        if d.is_dir():
            out.extend(sorted(d.glob("*.md")))
    return out


def detect_findings(root: Path) -> list[dict]:
    """Walk every wiki page; collect Class D findings only.

    Class D is cross-cluster by definition (canonical doc may be in any cluster).
    We pass strict=False — same cluster — but Class D's check is keyed on
    `builds-on:` resolution, not cluster membership, so cluster scoping does not
    suppress legitimate canonical-drift findings.
    """
    pages = _wiki_pages(root)
    out: list[dict] = []
    for page in pages:
        try:
            findings = classify(new_page=page, root=root, strict=False)
        except Exception:
            continue  # Per-page errors must not crash the daily job
        for f in findings:
            if f.klass != "D":
                continue
            attrs = dict(f.finding_attrs)
            attrs["confidence"] = round(f.confidence, 3)
            out.append({
                "finding_type": "wiki-canonical-drift-suggestion",
                "verdict": "amber",
                "severity": "INFO",
                "finding_attrs": attrs,
                "suggested_actions": ["review-canonical", "snooze-30d"],
            })
    return out


def _verdict(findings: list[dict]) -> str:
    if not findings:
        return "green"
    return "amber"  # Class D never escalates to red — INFO only.


def _write_self_contained_sidecar(sidecar_dir: Path, findings: list[dict]) -> Path:
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = sidecar_dir / f"{JOB_ID}-{ts}.json"
    payload = {
        "job_id": JOB_ID,
        "generated_at": ts,
        "verdict": _verdict(findings),
        "findings_count": len(findings),
        "findings": findings,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--root", type=Path, default=None,
                        help="Repository root. Defaults to dispatcher-discovered root.")
    parser.add_argument("--sidecar-dir", type=Path, default=None,
                        help="Write a self-contained JSON to this directory (test / dashboard mode). "
                             "Without this flag, the script uses run_wiki_job() for dispatcher integration.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    # Resolve root: --root, then env, then dispatcher utility
    if args.root is not None:
        root = args.root
    else:
        from _wiki_job_runner import repo_root  # local import — only needed in default mode
        root = repo_root()

    wiki_zone = root / "docs" / "_wiki"
    if not wiki_zone.is_dir():
        result = {
            "verdict": "green",
            "findings_count": 0,
            "auto_fixed": [],
            "actions_needed": [],
            "notes": "No docs/_wiki/ zone in this repo — wiki-canonical-drift skipped cleanly.",
        }
        if args.sidecar_dir:
            _write_self_contained_sidecar(args.sidecar_dir, [])
        print(json.dumps(result, ensure_ascii=False))
        return 0

    findings = detect_findings(root)

    if args.sidecar_dir:
        _write_self_contained_sidecar(args.sidecar_dir, findings)
        result = {
            "verdict": _verdict(findings),
            "findings_count": len(findings),
            "auto_fixed": [],
            "actions_needed": [
                f"wiki-canonical-drift-suggestion: {f['finding_attrs']['canonical_file']}"
                for f in findings
            ],
            "notes": f"Wrote {len(findings)} finding(s) to {args.sidecar_dir}.",
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.dry_run:
        result = {
            "verdict": _verdict(findings),
            "findings_count": len(findings),
            "auto_fixed": [],
            "actions_needed": [
                f"wiki-canonical-drift-suggestion: {f['finding_attrs']['canonical_file']}"
                for f in findings
            ],
            "notes": f"Dry-run — would write {len(findings)} finding(s) to digest.",
            "dry_run": True,
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0

    # Default mode — dispatcher integration
    from _wiki_job_runner import run_wiki_job  # noqa: E402
    notes = (
        f"{len(findings)} canonical-drift suggestion(s) across "
        f"{len({f['finding_attrs']['canonical_file'] for f in findings})} canonical doc(s)."
        if findings
        else "No canonical-drift suggestions — every external-reference wiki page agrees with its builds-on canonical, or canonical docs are fresh."
    )
    result = run_wiki_job(
        job_id=JOB_ID,
        findings=findings,
        notes=notes,
        trigger="scheduled-headless",
        root=root,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["verdict"] != "error" else 1


if __name__ == "__main__":
    sys.exit(main())

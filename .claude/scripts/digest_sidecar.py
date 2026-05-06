"""
digest_sidecar.py — Read and write the typed-event sidecar that lives next
to `docs/_inbox/daily-digest.md`.

The contract is defined in `docs/_bcos-framework/architecture/typed-events.md`.
The dispatcher (Step 7 of `.claude/skills/schedule-dispatcher/SKILL.md`) writes
both `daily-digest.md` (prose) and `daily-digest.json` (this sidecar). The
dashboard cockpit prefers the sidecar because typed events let it render
one-click cards without re-parsing strings; prose is the human view.

Public surface:

    parse_sidecar(path: Path) -> ParsedSidecar | None
    write_sidecar(path: Path, sidecar: ParsedSidecar) -> None
    SCHEMA_VERSION = "1.0.0"

`ParsedSidecar` mirrors the JSON shape but is import-friendly. Schema-version
mismatch is tolerated for `0.1.0-provisional` (the P0 fixture corpus); any
other unknown major bump raises.

The reader is forgiving on missing optional keys (best-effort) but strict on
the load-bearing ones (`overall_verdict`, `findings[].finding_type`,
`findings[].finding_attrs`). Bad data fails loudly so the dashboard does not
silently render half a card.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
_TOLERATED_VERSIONS = {SCHEMA_VERSION, "0.1.0-provisional"}


@dataclass
class Finding:
    number: int
    finding_type: str
    verdict: str  # green | amber | red
    emitted_by: str
    finding_attrs: dict[str, Any]
    suggested_actions: list[str] = field(default_factory=list)


@dataclass
class AutoFix:
    fix_id: str
    target: str
    detail: str = ""


@dataclass
class JobSummary:
    job: str
    verdict: str
    finding_count: int


@dataclass
class ParsedSidecar:
    schema_version: str
    date: str | None
    overall_verdict: str  # green | amber | red
    run_at: str | None
    findings: list[Finding] = field(default_factory=list)
    auto_fixed: list[AutoFix] = field(default_factory=list)
    jobs: list[JobSummary] = field(default_factory=list)


def _require(obj: dict, key: str, ctx: str) -> Any:
    if key not in obj:
        raise ValueError(f"sidecar {ctx}: missing required key {key!r}")
    return obj[key]


def parse_sidecar(path: Path) -> ParsedSidecar | None:
    """Parse a sidecar JSON file. Return None if the file is absent.

    Raises ValueError if the file exists but is malformed (we'd rather fail
    a build than silently render a half-card cockpit).
    """
    p = Path(path)
    if not p.is_file():
        return None
    raw = p.read_text(encoding="utf-8")
    data = json.loads(raw)

    schema_version = data.get("schema_version", SCHEMA_VERSION)
    if schema_version not in _TOLERATED_VERSIONS:
        raise ValueError(
            f"sidecar {path}: schema_version {schema_version!r} not in "
            f"{sorted(_TOLERATED_VERSIONS)}"
        )

    overall_verdict = _require(data, "overall_verdict", str(path))
    if overall_verdict not in ("green", "amber", "red"):
        raise ValueError(
            f"sidecar {path}: overall_verdict {overall_verdict!r} not green/amber/red"
        )

    findings: list[Finding] = []
    for i, f in enumerate(data.get("findings", [])):
        ctx = f"{path} findings[{i}]"
        findings.append(
            Finding(
                number=int(_require(f, "number", ctx)),
                finding_type=str(_require(f, "finding_type", ctx)),
                verdict=str(f.get("verdict", overall_verdict)),
                emitted_by=str(_require(f, "emitted_by", ctx)),
                finding_attrs=dict(_require(f, "finding_attrs", ctx)),
                suggested_actions=list(f.get("suggested_actions", [])),
            )
        )

    auto_fixed: list[AutoFix] = []
    for i, fix in enumerate(data.get("auto_fixed", [])):
        ctx = f"{path} auto_fixed[{i}]"
        auto_fixed.append(
            AutoFix(
                fix_id=str(_require(fix, "fix_id", ctx)),
                target=str(_require(fix, "target", ctx)),
                detail=str(fix.get("detail", "")),
            )
        )

    jobs: list[JobSummary] = []
    for i, j in enumerate(data.get("jobs", [])):
        ctx = f"{path} jobs[{i}]"
        jobs.append(
            JobSummary(
                job=str(_require(j, "job", ctx)),
                verdict=str(_require(j, "verdict", ctx)),
                finding_count=int(j.get("finding_count", 0)),
            )
        )

    return ParsedSidecar(
        schema_version=schema_version,
        date=data.get("date"),
        overall_verdict=overall_verdict,
        run_at=data.get("run_at"),
        findings=findings,
        auto_fixed=auto_fixed,
        jobs=jobs,
    )


def write_sidecar(path: Path, sidecar: ParsedSidecar) -> None:
    """Write a sidecar to disk in the canonical shape, deterministically.

    Field ordering matches typed-events.md so byte-stable regeneration is
    possible (per L-ECOSYSTEM-20260501-013 — derived files must be
    regeneratable byte-stable from source).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "schema_version": sidecar.schema_version or SCHEMA_VERSION,
        "date": sidecar.date,
        "overall_verdict": sidecar.overall_verdict,
        "run_at": sidecar.run_at,
        "findings": [
            {
                "number": f.number,
                "finding_type": f.finding_type,
                "verdict": f.verdict,
                "emitted_by": f.emitted_by,
                "finding_attrs": f.finding_attrs,
                "suggested_actions": f.suggested_actions,
            }
            for f in sidecar.findings
        ],
        "auto_fixed": [
            {"fix_id": x.fix_id, "target": x.target, "detail": x.detail}
            for x in sidecar.auto_fixed
        ],
        "jobs": [
            {"job": j.job, "verdict": j.verdict, "finding_count": j.finding_count}
            for j in sidecar.jobs
        ],
    }

    p.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/_inbox/daily-digest.json")
    s = parse_sidecar(target)
    if s is None:
        print(f"no sidecar at {target}", file=sys.stderr)
        sys.exit(2)
    print(
        json.dumps(
            {
                "schema_version": s.schema_version,
                "date": s.date,
                "overall_verdict": s.overall_verdict,
                "findings_count": len(s.findings),
                "auto_fixed_count": len(s.auto_fixed),
                "jobs_count": len(s.jobs),
            },
            indent=2,
        )
    )

"""
_wiki_job_runner.py — shared boilerplate for the four wiki maintenance scripts.

Per the plan in `docs/_planned/wiki-headless-scripts/`, every wiki job
ends with the same three steps: derive a verdict from findings, append
a diary entry, and merge findings into the typed-event sidecar so the
cockpit can render new cards within seconds. Factor that out so the
four scripts only contain the detection logic that's unique to them.

Public surface:
    run_wiki_job(*, job_id, findings, notes="", auto_fixed=(), trigger="scheduled") -> dict
    repo_root() -> Path
    no_wiki_zone(repo_root) -> bool
    iter_wiki_pages(repo_root, subdir="pages") -> Iterator[Path]
    parse_iso_date(s) -> datetime | None
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def repo_root() -> Path:
    """Resolve repo root the same way the dispatcher / dashboard do."""
    override = os.environ.get("BCOS_REPO_ROOT", "").strip()
    if override:
        p = Path(override).expanduser().resolve()
        if p.is_dir():
            return p
    # _wiki_job_runner.py lives at .claude/scripts/, so two parents up
    # is the repo root.
    return _HERE.parents[1]


def no_wiki_zone(root: Path | None = None) -> bool:
    """True when this repo has no `docs/_wiki/` zone — the four scripts
    should no-op cleanly with verdict=green and a "no wiki zone" note,
    not error out."""
    r = root or repo_root()
    return not (r / "docs" / "_wiki").is_dir()


def iter_wiki_pages(root: Path | None = None, *, subdir: str = "pages") -> Iterator[Path]:
    """Yield every `.md` file under `docs/_wiki/<subdir>/`.

    Common subdirs: "pages" (explainers), "source-summary" (URL captures),
    or "" (the whole wiki zone). Skips hidden files and `index.md`.
    """
    r = root or repo_root()
    base = r / "docs" / "_wiki" / subdir if subdir else r / "docs" / "_wiki"
    if not base.is_dir():
        return
    for p in sorted(base.rglob("*.md")):
        if p.name.startswith("."):
            continue
        if p.name == "index.md":
            continue
        yield p


def parse_iso_date(s: str | None) -> datetime | None:
    """Parse YYYY-MM-DD or full ISO-8601. UTC-naive results lifted to UTC."""
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    # Date-only fast path
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _verdict_from_findings(findings: list[dict[str, Any]]) -> str:
    """Roll up the worst-finding verdict into the job's overall verdict."""
    if not findings:
        return "green"
    rank = {"green": 0, "amber": 1, "red": 2, "error": 3}
    worst = "green"
    for f in findings:
        v = f.get("verdict", "amber")
        if rank.get(v, 1) > rank.get(worst, 0):
            worst = v
    return worst


def _append_diary(entry: dict[str, Any], root: Path) -> None:
    """Atomic-append one JSON line to schedule-diary.jsonl.

    Uses the existing append_diary.py helper if available; otherwise
    falls back to a direct write. Both paths create the parent dir.
    """
    diary_path = root / ".claude" / "hook_state" / "schedule-diary.jsonl"
    diary_path.parent.mkdir(parents=True, exist_ok=True)
    with diary_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _merge_into_sidecar(findings: list[dict[str, Any]], job_id: str, root: Path) -> bool:
    """Merge findings into `docs/_inbox/daily-digest.json`.

    The cockpit reads this sidecar to render cards. We append rather
    than replace so multiple jobs can run independently in the same
    day without clobbering each other's findings. Returns True when
    the file was updated.
    """
    sidecar = root / "docs" / "_inbox" / "daily-digest.json"
    if not sidecar.parent.is_dir():
        return False

    # Load existing or seed empty.
    if sidecar.is_file():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}

    today = datetime.now(timezone.utc).date().isoformat()
    data.setdefault("schema_version", "1.0.0")
    data.setdefault("date", today)
    data.setdefault("run_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    # auto_fixed is part of the typed-events sidecar contract (see fixtures);
    # seed an empty list so headless runs match chat-dispatcher shape.
    data.setdefault("auto_fixed", [])
    existing_findings = list(data.get("findings") or [])
    existing_jobs = list(data.get("jobs") or [])

    # Drop any prior findings emitted by THIS job (idempotent re-run).
    existing_findings = [f for f in existing_findings if f.get("emitted_by") != job_id]

    # Number new findings continuing the existing sequence.
    next_n = max((int(f.get("number", 0)) for f in existing_findings), default=0) + 1
    for i, f in enumerate(findings):
        f.setdefault("number", next_n + i)
        f.setdefault("emitted_by", job_id)

    existing_findings.extend(findings)
    data["findings"] = existing_findings

    # Roll up overall verdict from ALL findings (across all jobs).
    data["overall_verdict"] = _verdict_from_findings(existing_findings)

    # Per-job summary entry — replace any existing entry for this job.
    existing_jobs = [j for j in existing_jobs if j.get("job") != job_id]
    job_findings = [f for f in existing_findings if f.get("emitted_by") == job_id]
    existing_jobs.append({
        "job": job_id,
        "verdict": _verdict_from_findings(job_findings),
        "finding_count": len(job_findings),
    })
    data["jobs"] = existing_jobs

    # Atomic write
    tmp = sidecar.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(sidecar)
    return True


def run_wiki_job(
    *,
    job_id: str,
    findings: list[dict[str, Any]],
    notes: str = "",
    auto_fixed: list[str] = (),
    trigger: str = "scheduled",
    root: Path | None = None,
) -> dict[str, Any]:
    """Append diary + merge sidecar + return the per-job result dict.

    The result mirrors the dispatcher's per-job contract:
        {verdict, findings_count, auto_fixed, actions_needed, notes}
    Scripts call this once at the end of their detection pass and print
    the JSON return so the dashboard's _post_run_job_now sees the same
    summary line the dispatcher would.
    """
    r = root or repo_root()
    verdict = _verdict_from_findings(findings)

    # Compact action-item strings for the diary's `actions_needed` list.
    # The sidecar has the rich finding payload; the diary just keeps a
    # one-liner per finding for grep-friendly history.
    actions_needed = []
    for f in findings:
        ft = f.get("finding_type", "?")
        attrs = f.get("finding_attrs") or {}
        target = (
            attrs.get("file") or attrs.get("wiki_file")
            or attrs.get("data_point_file") or attrs.get("term") or "?"
        )
        actions_needed.append(f"{ft}: {target}")

    diary_entry = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "job": job_id,
        "verdict": verdict,
        "findings_count": len(findings),
        "auto_fixed": list(auto_fixed),
        "actions_needed": actions_needed,
        "notes": notes,
        "trigger": trigger,
    }
    try:
        _append_diary(diary_entry, r)
    except Exception:  # noqa: BLE001
        pass  # diary append must never block sidecar update

    sidecar_updated = _merge_into_sidecar(findings, job_id, r)

    return {
        "verdict": verdict,
        "findings_count": len(findings),
        "auto_fixed": list(auto_fixed),
        "actions_needed": actions_needed,
        "notes": notes,
        "sidecar_updated": sidecar_updated,
    }

"""
diary_grouper.py — Group .claude/hook_state/schedule-diary.jsonl by job.

The diary is append-only. Two historical shapes coexist:

  v1 (pre-v1.2):  {"ts": ..., "job": ..., "status": "ok|warn|error", "summary": "..."}
  v1.2+        :  {"ts": ..., "job": ..., "verdict": "green|amber|red|error",
                   "findings_count": N, "auto_fixed": [...], "actions_needed": [...],
                   "duration_s": N, "trigger": "scheduled|on-demand", "notes": "..."}

`normalize_entry` maps both to a single dict the dashboard can render
directly. `group_by_job(n=5)` returns the last N runs per job, newest
first, across the whole file.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

_STATUS_TO_VERDICT = {
    "ok": "green",
    "green": "green",
    "warn": "amber",
    "amber": "amber",
    "yellow": "amber",
    "fail": "red",
    "red": "red",
    "critical": "red",
    "error": "error",
}


@dataclass
class DiaryEntry:
    ts: str
    ts_dt: datetime
    job: str
    verdict: str  # green|amber|red|error
    findings_count: int
    auto_fixed: list[str]
    actions_needed: list[str]
    duration_s: float | None
    trigger: str | None
    notes: str

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "job": self.job,
            "verdict": self.verdict,
            "findings_count": self.findings_count,
            "auto_fixed": self.auto_fixed,
            "actions_needed": self.actions_needed,
            "duration_s": self.duration_s,
            "trigger": self.trigger,
            "notes": self.notes,
        }


def _parse_ts(raw: str | None) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        iso = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_entry(raw: dict) -> DiaryEntry | None:
    """Translate either shape into the v1.2+ contract. Returns None if
    the line is unparseable (skip silently)."""
    ts = raw.get("ts")
    dt = _parse_ts(ts)
    job = raw.get("job")
    if not isinstance(job, str) or not job or dt is None:
        return None

    verdict_raw = raw.get("verdict") or raw.get("status") or "ok"
    verdict = _STATUS_TO_VERDICT.get(str(verdict_raw).lower(), "green")

    findings = raw.get("findings_count")
    if not isinstance(findings, int):
        findings = 0

    auto_fixed = raw.get("auto_fixed") or []
    if not isinstance(auto_fixed, list):
        auto_fixed = []

    actions_needed = raw.get("actions_needed") or []
    if not isinstance(actions_needed, list):
        actions_needed = []

    dur = raw.get("duration_s")
    if not isinstance(dur, (int, float)):
        dur = None

    trigger = raw.get("trigger") if isinstance(raw.get("trigger"), str) else None

    notes = raw.get("notes") or raw.get("summary") or ""
    if not isinstance(notes, str):
        notes = str(notes)

    return DiaryEntry(
        ts=ts or dt.isoformat(),
        ts_dt=dt,
        job=job,
        verdict=verdict,
        findings_count=findings,
        auto_fixed=auto_fixed,
        actions_needed=actions_needed,
        duration_s=dur,
        trigger=trigger,
        notes=notes,
    )


def iter_entries(path: Path) -> Iterable[DiaryEntry]:
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            entry = normalize_entry(obj)
            if entry is not None:
                yield entry


def group_by_job(path: Path, n: int = 5) -> dict[str, list[DiaryEntry]]:
    """Return {job: [last n entries, newest first]}.

    Entries are sorted by ts ascending while reading, then trimmed+reversed
    per group.
    """
    by_job: dict[str, list[DiaryEntry]] = defaultdict(list)
    for e in iter_entries(path):
        by_job[e.job].append(e)

    out: dict[str, list[DiaryEntry]] = {}
    for job, entries in by_job.items():
        entries.sort(key=lambda e: e.ts_dt)
        out[job] = list(reversed(entries[-n:]))
    return out


def recent_unified(path: Path, n: int = 20) -> list[DiaryEntry]:
    """Return the last N entries across all jobs, newest first."""
    all_entries = list(iter_entries(path))
    all_entries.sort(key=lambda e: e.ts_dt)
    return list(reversed(all_entries[-n:]))


if __name__ == "__main__":
    import sys

    diary = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        ".claude/hook_state/schedule-diary.jsonl"
    )
    grouped = group_by_job(diary, n=5)
    for job in sorted(grouped):
        print(f"== {job} ==")
        for e in grouped[job]:
            print(f"  {e.ts}  {e.verdict:<6}  findings={e.findings_count}  trigger={e.trigger or '—'}")

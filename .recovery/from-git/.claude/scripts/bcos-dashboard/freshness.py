"""
freshness.py — Snapshot-freshness canary.

~/.local-dashboard/schedules.json is the source of nextRunAt / lastRunAt
for every scheduled BCOS job. It's populated by a Claude-executed
dispatcher step (MCP call to list_scheduled_tasks → write JSON). Because
it's Claude-executed, it can silently skip a run.

This panel is the canary: when the file goes stale, downstream panels
start lying about "next run / last run". The banner escalates severity
so a skipped refresh becomes visible instead of invisible.

Thresholds:
  - fresh      (< 26h)        -> ok    (green, quiet confirmation)
  - stale warn (26h - 48h)    -> warn  (amber)
  - stale crit (>= 48h)       -> critical (red)
  - missing    (no file)      -> critical (red)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SCHEDULES_PATH = Path.home() / ".local-dashboard" / "schedules.json"

_STALE_WARN_HOURS = 26
_STALE_CRITICAL_HOURS = 48


def _parse_generated_at(path: Path) -> datetime | None:
    """Best-effort parse of the 'generated_at' field; fall back to file mtime."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data.get("generated_at")
        if isinstance(raw, str):
            iso = raw.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(iso)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                pass
    except Exception:
        pass
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except Exception:
        return None


def _humanize_age(hours: float) -> str:
    if hours < 1:
        return f"{int(hours * 60)} min"
    if hours < 24:
        return f"{hours:.1f} h"
    return f"{hours / 24:.1f} d"


def collect_snapshot_freshness() -> dict:
    gen = _parse_generated_at(SCHEDULES_PATH)
    now = datetime.now(timezone.utc)

    if gen is None:
        return {
            "stats": [{
                "value": "Missing",
                "label": "~/.local-dashboard/schedules.json not found",
                "hint": (
                    "Paste into any Claude session: "
                    "call mcp__scheduled-tasks__list_scheduled_tasks and write "
                    "the result to ~/.local-dashboard/schedules.json. "
                    "The BCOS dispatcher can run this as a daily snapshot job."
                ),
            }],
            "_severity": "critical",
        }

    age_h = (now - gen).total_seconds() / 3600.0
    age_label = _humanize_age(age_h)

    if age_h >= _STALE_CRITICAL_HOURS:
        sev = "critical"
        value = f"Stale {age_label}"
        hint = (
            "Snapshot is over 48h old — downstream Next/Last-run columns are "
            "unreliable. Refresh by invoking mcp__scheduled-tasks__list_scheduled_tasks "
            "in any Claude session, or investigate why the dispatcher skipped "
            "the snapshot job."
        )
    elif age_h >= _STALE_WARN_HOURS:
        sev = "warn"
        value = f"Stale {age_label}"
        hint = (
            "Snapshot is over a day old. Today's dispatcher may have skipped "
            "the snapshot job. Refresh on-demand from any Claude session."
        )
    else:
        sev = "ok"
        value = f"Fresh {age_label}"
        hint = (
            f"Snapshot generated_at: {gen.isoformat().replace('+00:00', 'Z')}. "
            "Refreshed daily by the BCOS dispatcher."
        )

    return {
        "stats": [{
            "value": value,
            "label": "Schedules snapshot freshness",
            "hint": hint,
        }],
        "_severity": sev,
    }

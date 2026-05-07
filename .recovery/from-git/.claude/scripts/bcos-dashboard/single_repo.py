"""
single_repo.py — Collectors for the BCOS single-repo control panel.

Feeds three panels:
  - Jobs panel        — per-job cards with verdict, schedule, next/last run,
                        actions_needed, auto_fixed, notes, 5-run history
  - Actions inbox     — deduped user-facing decisions from today's digest
                        + the latest diary entries
  - Run history       — unified timeline of the last N diary entries

Data sources (all standard BCOS locations — resolved relative to REPO_ROOT):
  - .claude/quality/schedule-config.json   → enabled jobs + their schedule
  - docs/_inbox/daily-digest.md            → today's per-job verdict + actions
  - .claude/hook_state/schedule-diary.jsonl → immutable run history
  - ~/.local-dashboard/schedules.json      → nextRunAt / lastRunAt snapshot

REPO_ROOT detection:
  1. BCOS_REPO_ROOT env var (explicit override), or
  2. _HERE.parents[2] (default: dashboard lives at .claude/scripts/bcos-dashboard/,
     so three parents up is the repo root)

A shared _snapshot() caches the heavy reads per refresh so the three
collectors read each file once per TTL.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from diary_grouper import DiaryEntry, group_by_job, recent_unified  # noqa: E402
from digest_parser import ParsedDigest, parse_digest  # noqa: E402
from labels import (  # noqa: E402
    JOB_LABELS,
    decorate_action,
    decorate_diary_entry,
    decorate_file_finding,
    decorate_job,
    humanize_time,
    job_display,
    schedule_display,
    verdict_display,
    verdict_dot,
)


def _repo_root() -> Path:
    override = os.environ.get("BCOS_REPO_ROOT", "").strip()
    if override:
        p = Path(override).expanduser().resolve()
        if p.is_dir():
            return p
    return _HERE.parents[2]


REPO_ROOT = _repo_root()

SCHEDULE_CONFIG_PATH = REPO_ROOT / ".claude" / "quality" / "schedule-config.json"
DIGEST_PATH = REPO_ROOT / "docs" / "_inbox" / "daily-digest.md"
DIARY_PATH = REPO_ROOT / ".claude" / "hook_state" / "schedule-diary.jsonl"
SCHEDULES_PATH = Path.home() / ".local-dashboard" / "schedules.json"

_VERDICT_SEV = {"green": "ok", "amber": "warn", "red": "critical", "error": "critical"}
_VERDICT_EMOJI = {"green": "🟢", "amber": "🟡", "red": "🔴", "error": "⚠️"}

# The canonical BCOS job roster. Consumer configs may enable a subset.
# Unknown jobs are still surfaced with placeholder status so the dashboard
# shows what's POSSIBLE, not just what's configured.
#
# Two groups: core maintenance (5 jobs) + wiki zone maintenance (4 jobs).
# Consumers without a `_wiki/` zone simply leave the wiki jobs disabled in
# `schedule-config.json`; they surface as "not configured" without errors.
_KNOWN_JOBS = [
    # Core BCOS maintenance
    "index-health",
    "audit-inbox",
    "daydream-lessons",
    "daydream-deep",
    "architecture-review",
    # Self-learning safety brake (Friday)
    "auto-fix-audit",
    # Lifecycle classifier (Friday)
    "lifecycle-sweep",
    # Wiki zone maintenance
    "wiki-stale-propagation",
    "wiki-source-refresh",
    "wiki-graveyard",
    "wiki-coverage-audit",
    "wiki-canonical-drift",
]


# ---------------------------------------------------------------------------
# Cockpit (hero)
#
# The cockpit is the "one glance" surface. It wraps a plain-English
# summary sentence + a per-job maintenance strip. All the data is
# already computed by the other collectors — this is pure composition
# with a headline-picking helper.
# ---------------------------------------------------------------------------


def _headline_for_state(action_count: int, overall_sev: str, freshness_sev: str,
                       freshness_value: str | None, first_run: bool = False,
                       any_enabled: bool = False,
                       display_next_run: str | None = None) -> tuple[str, str]:
    """Return (sentence, tone) for the hero block.

    tone is one of ok / warn / critical / info / first_run — drives the
    accent colour and lets the client pick the empty/first-run skin.

    First-run wording branches on whether ANY scheduled job is enabled.
    Claiming "your first check runs tomorrow at 9 AM" when nothing is
    actually scheduled is a lie that erodes trust on day one.
    """
    if first_run:
        if not any_enabled:
            return (
                "Welcome to BCOS. No maintenance jobs are scheduled yet — "
                "open Settings to enable the routine you want.",
                "first_run",
            )
        if display_next_run and display_next_run != "—":
            return (
                f"Welcome to BCOS. Your first maintenance check runs "
                f"{display_next_run}. Come back to see what it finds.",
                "first_run",
            )
        return (
            "Welcome to BCOS. Your maintenance routine is configured and "
            "will run on its next scheduled trigger.",
            "first_run",
        )

    # Freshness critical beats everything — if the snapshot is broken we say so.
    if freshness_sev == "critical":
        return ("Heads up — background data is missing or outdated. "
                "Refresh when you can.", "warn")

    if action_count > 0 and overall_sev == "critical":
        word = "thing needs" if action_count == 1 else "things need"
        return (f"Your attention is needed on {action_count} {word} review.", "critical")

    if action_count > 0:
        word = "thing is" if action_count == 1 else "things are"
        return (f"Your system is healthy. {action_count} {word} waiting on "
                "a decision from you.", "warn")

    if overall_sev == "warn":
        return ("Most things are fine. A few findings worth a look "
                "when you have time.", "warn")

    if freshness_sev == "warn":
        return (f"Everything is in order. Note: background data is "
                f"{freshness_value or 'a bit old'}.", "info")

    return ("Everything is in order. Nothing needs your attention "
            "right now.", "ok")


def collect_cockpit() -> dict:
    # Reuse the other collectors — they're cached by the outer TTL
    # machinery so this isn't a re-read storm.
    from freshness import collect_snapshot_freshness

    fresh = collect_snapshot_freshness()
    jobs = collect_jobs_panel()
    actions = collect_actions_inbox()

    # First-run detector — diary file has zero entries (or is missing).
    # A fresh BCOS install ships with schedule-config.json so we cannot
    # use that as the signal — only the diary tells us whether the
    # dispatcher has actually run yet. See plan open question #3.
    first_run = False
    try:
        if not DIARY_PATH.is_file() or DIARY_PATH.stat().st_size == 0:
            first_run = True
    except Exception:
        first_run = False

    # Pull per-job data for the maintenance strip (human label + verdict glyph + severity).
    # Track:
    #   - any_enabled: at least one scheduled job is on (drives first-run copy)
    #   - earliest_next_run: the soonest configured next-run timestamp across
    #     enabled jobs (used in the first-run welcome line when applicable)
    dots = []
    worst_sev = "ok"
    any_enabled = False
    earliest_next_run_iso: str | None = None
    earliest_next_run_display: str | None = None
    # Jobs that ACTUALLY run end-to-end from the dashboard via a standalone
    # Python script (subprocess). All others — judgement jobs (audit-inbox,
    # daydream-*, architecture-review) and wiki jobs without scripts yet —
    # fall through to a "Run via chat" hint. Honest UX: only call something
    # Run-now if the click really does the thing.
    #
    # Headless wiki jobs ship per docs/_planned/wiki-headless-scripts/:
    #   - wiki-stale-propagation: run_wiki_stale_propagation.py (shipped)
    #   - wiki-graveyard, wiki-coverage-audit, wiki-source-refresh: TODO
    _HEADLESS_RUNNABLE = {
        "index-health",
        "auto-fix-audit",
        "wiki-stale-propagation",
    }

    for j in jobs.get("jobs") or []:
        sev = _VERDICT_SEV.get(j.get("verdict") or "", "muted")
        is_enabled = bool(j.get("enabled"))
        if is_enabled:
            any_enabled = True
            nri = j.get("next_run_iso")
            if nri and (earliest_next_run_iso is None or nri < earliest_next_run_iso):
                earliest_next_run_iso = nri
                earliest_next_run_display = j.get("display_next_run")

        # Last 5 verdicts as compact dots (most-recent first → reverse for
        # left-to-right reading). Diary entries are already newest-first.
        history = (j.get("history") or [])[:5]
        recent_verdicts = [
            {"ts": h.get("ts"), "verdict": h.get("verdict"),
             "findings_count": h.get("findings_count", 0)}
            for h in reversed(history)
        ]

        # Last-run findings count (for the card status line).
        last_findings = None
        if history:
            last_findings = (history[0] or {}).get("findings_count")

        job_id = j.get("job") or ""
        dots.append({
            "job": job_id,
            "label": j.get("display_name") or job_id,
            "dot": j.get("display_dot") or ("○" if not j.get("verdict") else "●"),
            "severity": sev,
            "verdict": j.get("verdict"),
            "display_verdict": j.get("display_verdict"),
            "schedule": j.get("display_schedule_short"),
            "last_run": j.get("display_last_run"),
            "next_run": j.get("display_next_run"),
            "enabled": is_enabled,
            # placeholder copy the client can show next to a dim dot:
            #   - "Not configured" when enabled=false
            #   - "Scheduled — not run yet" when enabled=true but no verdict
            #   - "" when there's a real verdict
            "placeholder": (
                "Not configured" if not is_enabled
                else ("Scheduled — not run yet" if not j.get("verdict") else "")
            ),
            # New fields for the per-job card layout (replaces dot strip):
            "recent_verdicts": recent_verdicts,           # last 5, oldest→newest
            "last_findings_count": last_findings,         # int or None
            "headless_runnable": job_id in _HEADLESS_RUNNABLE,
            "hint": j.get("display_hint") or "",
            "actions_needed_count": len(j.get("actions_needed") or []),
        })
        if _rank(sev) > _rank(worst_sev):
            worst_sev = sev

    freshness_sev = fresh.get("_severity", "ok")
    freshness_value = None
    stats = fresh.get("stats") or []
    if stats:
        freshness_value = stats[0].get("value")

    action_count = int(actions.get("count") or 0)
    headline, tone = _headline_for_state(
        action_count=action_count,
        overall_sev=worst_sev,
        freshness_sev=freshness_sev,
        freshness_value=freshness_value,
        first_run=first_run,
        any_enabled=any_enabled,
        display_next_run=earliest_next_run_display,
    )

    # Empty-state detection — everything healthy, nothing waiting. The
    # client uses this to collapse the cockpit to a one-line "all clear".
    is_empty = (
        not first_run
        and action_count == 0
        and worst_sev == "ok"
        and freshness_sev == "ok"
    )

    # Panel severity tracks the tone so the aggregate health badge stays honest.
    _TONE_TO_SEV = {"ok": "ok", "warn": "warn", "critical": "critical",
                    "info": "info", "first_run": "info"}

    return {
        "kind": "cockpit",
        "title": "Your knowledge system",
        "headline": headline,
        "tone": tone,
        "first_run": first_run,
        "is_empty": is_empty,
        "action_count": action_count,
        "actions": {
            "items": actions.get("items") or [],
            "hidden_resolved": actions.get("hidden_resolved") or 0,
        },
        "dots": dots,
        "freshness": {
            "value": freshness_value,
            "severity": freshness_sev,
            "show_line": freshness_sev in {"warn", "critical"},
        },
        "bcos_framework": _collect_bcos_framework_block(),
        "atlas": _collect_atlas_teaser(),
        "_severity": _TONE_TO_SEV.get(tone, "ok"),
    }


def _collect_bcos_framework_block() -> dict:
    """Cockpit block for the §0 BCOS framework strip (status + 3 buttons).

    Resolves to a small dict the JS cockpit renderer consumes. Errors are
    swallowed so a transient GitHub-API hiccup never breaks the cockpit.
    """
    try:
        from bcos_sync import collect_freshness
        return collect_freshness()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def _collect_atlas_teaser() -> dict:
    """Small cockpit block linking to the Context Atlas view."""
    try:
        from atlas_collectors import collect_atlas_teaser
        return collect_atlas_teaser()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "href": "/atlas"}


# ---------------------------------------------------------------------------
# §04 File health (v1: frontmatter + stale + textual)
# ---------------------------------------------------------------------------

def collect_file_health() -> dict:
    # Lazy import — file_health imports REPO_ROOT back from this module.
    from file_health import collect as _collect

    report = _collect()
    total = report.get("total", 0)
    fixable = report.get("fixable", 0)

    # Severity escalates with unfixable finding count
    cats = report.get("categories", {}) or {}
    # Attach display_* fields to every finding.
    for items in cats.values():
        for f in items:
            decorate_file_finding(f)
    unfixable = sum(1 for lst in cats.values() for f in lst if not f.get("fix_id"))
    if total == 0:
        sev = "ok"
    elif unfixable == 0:
        sev = "info"   # all findings are auto-fixable, not really bad
    elif unfixable <= 3:
        sev = "warn"
    else:
        sev = "critical"

    return {
        "kind": "file_health",
        "categories": cats,
        "total": total,
        "fixable": fixable,
        "stale_threshold_days": report.get("stale_threshold_days", 30),
        "_severity": sev,
    }

_SEV_ORDER = {"muted": 0, "info": 1, "ok": 2, "warn": 3, "critical": 4}


def _rank(sev: str) -> int:
    return _SEV_ORDER.get(sev, 0)


def _load_schedule_config() -> dict:
    if not SCHEDULE_CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(SCHEDULE_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_schedules_map() -> dict[str, dict]:
    """Return { taskId: task } from ~/.local-dashboard/schedules.json."""
    if not SCHEDULES_PATH.is_file():
        return {}
    try:
        data = json.loads(SCHEDULES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    tasks = data.get("tasks") or []
    return {t.get("taskId"): t for t in tasks if isinstance(t, dict) and t.get("taskId")}


def _humanize_relative(iso: str | None, now: datetime | None = None) -> str:
    if not iso:
        return "—"
    now = now or datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = (now - dt.astimezone(timezone.utc)).total_seconds()
    future = delta < 0
    mag = abs(delta)
    if mag < 60:
        s = f"{int(mag)}s"
    elif mag < 3600:
        s = f"{int(mag // 60)}m"
    elif mag < 86400:
        s = f"{mag / 3600:.1f}h"
    elif mag < 86400 * 14:
        s = f"{mag / 86400:.1f}d"
    else:
        return dt.date().isoformat()
    return f"in {s}" if future else f"{s} ago"


def _node_task_id() -> str | None:
    """Infer the scheduled-task id for this node.

    BCOS convention: the dispatcher scheduled task is `bcos-<slug>` where
    slug matches the repo directory name (lowercased). If BCOS_TASK_ID is
    set, that takes precedence for non-standard installs.
    """
    override = os.environ.get("BCOS_TASK_ID", "").strip()
    if override:
        return override
    return f"bcos-{REPO_ROOT.name.lower()}"


@dataclass
class _Snapshot:
    cfg: dict
    digest: ParsedDigest | None
    diary_by_job: dict[str, list[DiaryEntry]]
    schedules: dict[str, dict]


def _snapshot() -> _Snapshot:
    return _Snapshot(
        cfg=_load_schedule_config(),
        digest=parse_digest(DIGEST_PATH),
        diary_by_job=group_by_job(DIARY_PATH, n=5),
        schedules=_load_schedules_map(),
    )


# ---------------------------------------------------------------------------
# §B Jobs panel
# ---------------------------------------------------------------------------

def collect_jobs_panel() -> dict:
    """One card's worth of data per job.

    Returns union of (configured jobs ∪ known BCOS jobs) so missing config
    surfaces as "not configured" instead of being invisible.
    """
    snap = _snapshot()
    cfg_jobs: dict[str, dict] = (snap.cfg.get("jobs") or {}) if isinstance(snap.cfg, dict) else {}

    job_ids: list[str] = []
    seen: set[str] = set()
    for jid in cfg_jobs:
        if jid not in seen:
            job_ids.append(jid); seen.add(jid)
    for jid in _KNOWN_JOBS:
        if jid not in seen:
            job_ids.append(jid); seen.add(jid)

    task_id = _node_task_id()
    sched_task = snap.schedules.get(task_id) if task_id else None
    next_run_iso = sched_task.get("nextRunAt") if sched_task else None
    last_run_iso = sched_task.get("lastRunAt") if sched_task else None

    worst_sev = "ok"
    cards = []
    for jid in job_ids:
      try:
        cfg_entry = cfg_jobs.get(jid) or {}
        enabled = bool(cfg_entry.get("enabled")) if cfg_entry else False
        schedule = cfg_entry.get("schedule") if cfg_entry else None

        history = snap.diary_by_job.get(jid) or []
        last = history[0] if history else None

        dg_job = snap.digest.jobs.get(jid) if snap.digest else None
        verdict = None
        actions_needed: list[str] = []
        notes = ""
        if last is not None:
            verdict = last.verdict
            actions_needed = list(last.actions_needed)
            notes = last.notes
        if dg_job is not None:
            verdict = dg_job.verdict
            notes = dg_job.body or notes

        if cfg_entry:
            status = "configured" if enabled else "disabled"
        else:
            status = "unknown"
        status_detail = "never run" if not history else None

        sev = _VERDICT_SEV.get(verdict or "", "muted") if history else "muted"
        if _rank(sev) > _rank(worst_sev):
            worst_sev = sev

        card = {
            "job": jid,
            "status": status,
            "status_detail": status_detail,
            "enabled": enabled,
            "schedule": schedule or ("off" if cfg_entry and not enabled else "—"),
            "verdict": verdict,
            "verdict_emoji": _VERDICT_EMOJI.get(verdict or "", "·"),
            "next_run_iso": next_run_iso if enabled else None,
            "last_run_iso": last.ts if last else None,
            "next_run_rel": _humanize_relative(next_run_iso) if enabled else "—",
            # Only show last-run when THIS job has a diary entry. The
            # scheduled-task-level lastRunAt refers to the whole dispatcher
            # run, not this specific job — using it as a fallback would
            # falsely show "N hours ago" for jobs that never actually ran.
            "last_run_rel": _humanize_relative(last.ts) if last else "—",
            "actions_needed": actions_needed,
            "auto_fixed": list(last.auto_fixed) if last else [],
            "notes": notes,
            "history": [
                {"ts": e.ts, "verdict": e.verdict, "findings_count": e.findings_count}
                for e in history
            ],
        }
        decorate_job(card)
        cards.append(card)
      except Exception as exc:  # noqa: BLE001 — per-job isolation
        # Plan P3_006: one job's collect failure must not blank the whole
        # cockpit. Emit a stub card carrying the error so the dot renders
        # as a warning glyph with hover context.
        cards.append({
            "job": jid,
            "status": "unknown",
            "status_detail": "collect failed",
            "enabled": False,
            "schedule": None,
            "verdict": "error",
            "verdict_emoji": "⚠️",
            "next_run_iso": None,
            "last_run_iso": None,
            "next_run_rel": "—",
            "last_run_rel": "—",
            "actions_needed": [],
            "auto_fixed": [],
            "notes": f"collect failed: {type(exc).__name__}: {exc}",
            "history": [],
            "display_name": jid,
            "display_hint": f"collect failed: {type(exc).__name__}",
            "display_dot": "⚠",
            "display_verdict": "Failed to collect",
            "display_status": "Collect error",
            "display_schedule_short": "—",
            "display_schedule_long": "—",
            "display_next_run": "—",
            "display_last_run": "—",
            "_error": True,
        })

    return {
        "kind": "jobs_panel",
        "jobs": cards,
        "task_id": task_id,
        "repo_root": str(REPO_ROOT),
        "_severity": worst_sev,
    }


# ---------------------------------------------------------------------------
# §C Per-job detail (drawer)
#
# Rich payload for a single job — everything the side drawer needs to
# render without a second round-trip. Composes off the same _snapshot()
# the other collectors use, so it costs nothing extra during a refresh
# tick.
# ---------------------------------------------------------------------------


def collect_job_detail(job_id: str) -> dict:
    """Per-job payload for the drawer.

    Returns a dict with:
      - identity: job, display_name, description (JOB_LABELS hint)
      - schedule: raw + display_short + display_long + enabled flag
      - timing: next_run_iso/rel + last_run_iso/rel
      - verdict: raw + display + dot
      - today: digest body for this job (markdown), if present
      - actions_needed / auto_fixed (from latest diary entry)
      - runs: last 5 history entries with display_when + display_verdict
      - technical: schedule_config_path, task_id, repo_root, fingerprint inputs
    """
    jid = (job_id or "").strip()
    if not jid:
        return {"error": "job_id required", "_severity": "warn"}

    snap = _snapshot()
    cfg_jobs: dict[str, dict] = (snap.cfg.get("jobs") or {}) if isinstance(snap.cfg, dict) else {}
    cfg_entry = cfg_jobs.get(jid) or {}

    if not cfg_entry and jid not in JOB_LABELS and jid not in _KNOWN_JOBS:
        return {"error": f"unknown job: {jid}", "_severity": "warn"}

    enabled = bool(cfg_entry.get("enabled")) if cfg_entry else False
    schedule = cfg_entry.get("schedule")
    if cfg_entry:
        status = "configured" if enabled else "disabled"
    else:
        status = "unknown"

    label, hint = job_display(jid)

    task_id = _node_task_id()
    sched_task = snap.schedules.get(task_id) if task_id else None
    next_run_iso = sched_task.get("nextRunAt") if (sched_task and enabled) else None
    last_task_run_iso = sched_task.get("lastRunAt") if sched_task else None

    history = snap.diary_by_job.get(jid) or []
    last = history[0] if history else None

    dg_job = snap.digest.jobs.get(jid) if snap.digest else None
    verdict = None
    actions_needed: list[str] = []
    auto_fixed: list[str] = []
    notes = ""
    if last is not None:
        verdict = last.verdict
        actions_needed = list(last.actions_needed)
        auto_fixed = list(last.auto_fixed)
        notes = last.notes
    if dg_job is not None:
        verdict = dg_job.verdict

    today_body = (dg_job.body or "").strip() if dg_job else ""

    runs = []
    for e in history[:5]:
        sev = _VERDICT_SEV.get(e.verdict, "muted")
        runs.append({
            "ts": e.ts,
            "verdict": e.verdict,
            "display_verdict": verdict_display(e.verdict),
            "display_dot": verdict_dot(e.verdict),
            "display_when": humanize_time(e.ts),
            "severity": sev,
            "findings_count": e.findings_count,
            "trigger": e.trigger or "—",
            "notes_preview": (e.notes[:180] + "…") if len(e.notes) > 180 else e.notes,
        })

    sev = _VERDICT_SEV.get(verdict or "", "muted") if history else "muted"

    # Frequency hint: when the last 5 runs are all green AND the current
    # schedule is denser than the next preset down, suggest slowing it down.
    # The dispatcher hint is mechanical-first — the user makes the final call
    # via the in-drawer one-click button.
    frequency_hint: dict | None = None
    if (
        enabled
        and len(runs) >= 5
        and all((r.get("verdict") == "green") for r in runs[:5])
    ):
        # Map current schedule -> next-slower preset id (used by /api/schedule/preset).
        # Skip when already at "weekly_mon" or below; further slowing is the human's call.
        sched_norm = (schedule or "").strip().lower()
        slower = None
        if sched_norm in ("daily", "everyday", "every day", "mon-fri", "mon-fri,daily"):
            slower = ("mon_wed_fri", "Mon / Wed / Fri")
        elif sched_norm in ("mon,wed,fri", "mon, wed, fri", "mon_wed_fri"):
            slower = ("weekly_mon", "weekly (Monday)")
        if slower:
            preset_id, preset_label = slower
            frequency_hint = {
                "reason": "5_green",
                "current_schedule": schedule,
                "suggested_preset": preset_id,
                "suggested_label": preset_label,
                "message": (
                    f"Last 5 runs were all green. Want to slow this to {preset_label}?"
                ),
            }

    return {
        "kind": "job_detail",
        "job": jid,
        "display_name": label,
        "description": hint,
        "status": status,
        "enabled": enabled,
        "schedule": schedule or ("off" if cfg_entry and not enabled else None),
        "display_schedule_short": schedule_display(schedule, short=True),
        "display_schedule_long": schedule_display(schedule, short=False),
        "frequency_hint": frequency_hint,
        "verdict": verdict,
        "display_verdict": verdict_display(verdict),
        "display_dot": verdict_dot(verdict),
        "next_run_iso": next_run_iso,
        "last_run_iso": last.ts if last else None,
        "display_next_run": humanize_time(next_run_iso) if next_run_iso else "—",
        "display_last_run": humanize_time(last.ts) if last else "—",
        "today_body": today_body,
        "actions_needed": actions_needed,
        "auto_fixed": auto_fixed,
        "notes": notes,
        "runs": runs,
        "technical": {
            "task_id": task_id,
            "repo_root": str(REPO_ROOT),
            "schedule_config_path": str(SCHEDULE_CONFIG_PATH),
            "diary_path": str(DIARY_PATH),
            "digest_path": str(DIGEST_PATH),
            "schedules_snapshot_path": str(SCHEDULES_PATH),
            "task_last_run_iso": last_task_run_iso,
        },
        "_severity": sev,
    }


# ---------------------------------------------------------------------------
# §D Run history
# ---------------------------------------------------------------------------

def collect_run_history(n: int = 20) -> dict:
    entries = recent_unified(DIARY_PATH, n=n)
    worst_sev = "ok"
    items = []
    for e in entries:
        sev = _VERDICT_SEV.get(e.verdict, "muted")
        if _rank(sev) > _rank(worst_sev):
            worst_sev = sev
        row = {
            "timestamp": e.ts,
            "job": e.job,
            "verdict": e.verdict,
            "verdict_emoji": _VERDICT_EMOJI.get(e.verdict, "·"),
            "findings_count": e.findings_count,
            "trigger": e.trigger or "—",
            "notes_preview": (e.notes[:180] + "…") if len(e.notes) > 180 else e.notes,
            "actions_preview": e.actions_needed[:3],
            "severity": sev,
        }
        decorate_diary_entry(row)
        items.append(row)
    return {
        "kind": "run_history",
        "items": items,
        "_severity": worst_sev if items else "info",
    }


# ---------------------------------------------------------------------------
# §E Actions inbox
# ---------------------------------------------------------------------------

def collect_actions_inbox() -> dict:
    # Lazy import to avoid a module-level cycle (actions_resolved imports
    # REPO_ROOT from this module).
    from actions_resolved import fingerprint, load_resolved_set

    snap = _snapshot()
    resolved = load_resolved_set()

    items: list[dict] = []
    hidden = 0
    seen_titles: set[str] = set()

    import re as _re
    _PATH_RE = _re.compile(r"(docs/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)")

    def _emit(title: str, source: str, source_job: str | None, number: int | None, body: str) -> None:
        nonlocal hidden
        fp = fingerprint(title)
        if fp in resolved:
            hidden += 1
            return
        # Detect referenced repo-relative file path and flag whether it
        # actually exists. The seed/fixture digest references demo paths
        # (Q1-notes.md, competitor-x.md, …) that won't resolve on a fresh
        # repo — surfacing the "example" tag prevents users from clicking
        # Open file and getting a silent "path not found" error.
        ref_path: str | None = None
        path_exists = True
        m = _PATH_RE.search(title)
        if m:
            ref_path = m.group(1)
            try:
                path_exists = (REPO_ROOT / ref_path).exists()
            except Exception:  # noqa: BLE001
                path_exists = False
        item = {
            "source": source,
            "source_job": source_job,
            "number": number,
            "title": title,
            "body": body,
            "fingerprint": fp,
            "ref_path": ref_path,
            "path_exists": path_exists,
        }
        decorate_action(item)
        items.append(item)

    if snap.digest is not None:
        for act in snap.digest.actions:
            key = act.title.strip().lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            _emit(
                title=act.title.strip(),
                source="digest",
                source_job=_infer_source_job(act.title, act.body, snap.digest),
                number=act.number,
                body=act.body,
            )

    for job, entries in snap.diary_by_job.items():
        if not entries:
            continue
        latest = entries[0]
        for raw in latest.actions_needed:
            key = raw.strip().lower()
            if key in seen_titles:
                continue
            if any(key.split(":")[0].strip() in t for t in seen_titles):
                continue
            seen_titles.add(key)
            _emit(
                title=raw.strip(),
                source="diary",
                source_job=job,
                number=None,
                body="",
            )

    sev = "ok" if not items else ("warn" if len(items) <= 2 else "critical")
    return {
        "kind": "actions_inbox",
        "items": items,
        "count": len(items),
        "hidden_resolved": hidden,
        "_severity": sev,
    }


def _infer_source_job(title: str, body: str, pd: ParsedDigest) -> str | None:
    if not pd.jobs:
        return None
    probe = (title.split("—")[0] + " " + body).lower()
    tokens = {w for w in probe.replace("`", " ").split() if len(w) > 3}
    best = None
    best_score = 0
    for job_id, section in pd.jobs.items():
        body_l = section.body.lower()
        score = sum(1 for t in tokens if t in body_l)
        if score > best_score:
            best = job_id
            best_score = score
    return best if best_score >= 2 else None

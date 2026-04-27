"""
run.py — Launch the BCOS Context Dashboard.

A single-mode local dashboard for one BCOS-enabled repo. Shows dispatcher
job status, today's action items, and recent run history — with one
snapshot-freshness canary so silently-skipped maintenance runs surface
visibly.

Quick start (from the root of a BCOS-enabled repo):

    python .claude/scripts/bcos-dashboard/run.py

Then open http://127.0.0.1:8091 in a browser.

Environment overrides:
  - BCOS_DASHBOARD_PORT=<int>    override default port (8091)
  - BCOS_REPO_ROOT=<path>        pin data sources to a specific repo
                                 (default: three folders up from this file)
  - BCOS_TASK_ID=<str>           pin the scheduled-task ID used for
                                 next/last run (default: bcos-<repo-name>)

Data sources (read-only, all relative to BCOS_REPO_ROOT unless noted):
  - .claude/quality/schedule-config.json    — enabled jobs + cadence
  - docs/_inbox/daily-digest.md             — today's verdicts + actions
  - .claude/hook_state/schedule-diary.jsonl — immutable run history
  - ~/.local-dashboard/schedules.json       — nextRunAt / lastRunAt (user home)

Panels:
  §00 Snapshot freshness    — canary on schedules.json staleness
  §01 Jobs                  — per-job status cards (verdict, schedule, history)
  §02 Actions inbox         — deduped user-facing decisions
  §03 Run history           — last 20 entries across all jobs
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from server import Panel, serve  # noqa: E402
from freshness import collect_snapshot_freshness  # noqa: E402
from single_repo import (  # noqa: E402
    REPO_ROOT,
    collect_actions_inbox,
    collect_cockpit,
    collect_file_health,
    collect_job_detail,
    collect_jobs_panel,
    collect_run_history,
)
from actions_resolved import mark_resolved, unmark_resolved  # noqa: E402
from schedule_editor import (  # noqa: E402
    KNOWN_AUTO_FIX_IDS,
    PRESETS as SCHEDULE_PRESETS,
    apply_preset,
    read_config as read_schedule_config,
    set_auto_fix_whitelist,
)
from file_health import apply_fix as apply_file_fix  # noqa: E402


DEFAULT_PORT = int(os.environ.get("BCOS_DASHBOARD_PORT", "8091"))


def panels() -> list[Panel]:
    return [
        # Hero: one-glance cockpit. No section number — it's the frame,
        # not a section.
        Panel(
            id="cockpit",
            title="Your knowledge system",
            kind="cockpit",
            span=12,
            ttl=30,
            collector=collect_cockpit,
        ),
        # actions_inbox used to be its own panel here; Step 3 folded it
        # into the cockpit so the user's attention goes to one place.
        # The mark-done endpoints at /api/actions/* still work unchanged
        # — the cockpit renderer uses them directly.
        # jobs_panel was removed from the main page in Step 4. Its data
        # still feeds the cockpit's 5-dot maintenance strip via
        # collect_jobs_panel() (called inside collect_cockpit()), and the
        # per-job drawer fetches /api/job/<id> directly. No standalone
        # panel — clicking a dot opens the drawer.
        # snapshot_freshness, run_history, file_health used to render here
        # as standalone panels (Steps 1-3). Step 5 moved them behind
        # /settings/{technical,runs,files}; their collectors still feed
        # /api/panel/<id> for those sub-pages, and snapshot_freshness still
        # surfaces in the cockpit headline when stale.
    ]


def _settings_panels() -> list[Panel]:
    """Panels exposed only via /api/panel/<id> for /settings sub-pages.

    Not part of the main panels() list (so they don't render in the
    cockpit grid), but still need to live in the panel_map so the
    settings client can fetch them via /api/panel/<id>.
    """
    return [
        Panel(
            id="jobs_panel",
            title="Maintenance checks",
            kind="jobs_panel",
            span=12,
            ttl=30,
            collector=collect_jobs_panel,
        ),
        Panel(
            id="snapshot_freshness",
            title="Schedules snapshot",
            kind="metric",
            span=12,
            ttl=30,
            collector=collect_snapshot_freshness,
            tag="canary",
        ),
        Panel(
            id="run_history",
            title="Recent activity",
            kind="run_history",
            span=12,
            ttl=15,
            collector=collect_run_history,
        ),
        Panel(
            id="file_health",
            title="Document health",
            kind="file_health",
            span=12,
            ttl=60,
            collector=collect_file_health,
        ),
    ]


def _post_mark_resolved(body: dict, ctx: dict) -> dict:
    title = body.get("title")
    source_job = body.get("source_job")
    if not isinstance(title, str) or not title.strip():
        return {"ok": False, "error": "title required"}
    result = mark_resolved(title, source_job if isinstance(source_job, str) else None)
    if result.get("ok"):
        # Cockpit composes actions inbox, so both caches must be invalidated
        # — otherwise the periodic /api/data refresh re-renders the cockpit
        # with the stale pre-resolve list and overwrites the optimistic UI.
        ctx["invalidate_panel"]("actions_inbox")
        ctx["invalidate_panel"]("cockpit")
    return result


def _post_unmark_resolved(body: dict, ctx: dict) -> dict:
    fp = body.get("fingerprint") or body.get("title")
    if not isinstance(fp, str) or not fp.strip():
        return {"ok": False, "error": "fingerprint or title required"}
    result = unmark_resolved(fp)
    if result.get("ok"):
        ctx["invalidate_panel"]("actions_inbox")
        ctx["invalidate_panel"]("cockpit")
    return result


def _post_schedule_preset(body: dict, ctx: dict) -> dict:
    job = body.get("job")
    preset = body.get("preset")
    if not isinstance(job, str) or not job.strip():
        return {"ok": False, "error": "job required"}
    if not isinstance(preset, str) or not preset.strip():
        return {"ok": False, "error": "preset required"}
    result = apply_preset(job.strip(), preset.strip())
    if result.get("ok"):
        ctx["invalidate_panel"]("jobs_panel")
        ctx["invalidate_panel"]("cockpit")  # maintenance strip mirrors the jobs
    return result


def _post_schedule_whitelist(body: dict, ctx: dict) -> dict:
    """POST /api/schedule/whitelist — toggle auto-fix IDs on/off in bulk."""
    additions = body.get("add") or []
    removals = body.get("remove") or []
    if not isinstance(additions, list) or not isinstance(removals, list):
        return {"ok": False, "error": "add and remove must be arrays"}
    additions = [str(a) for a in additions if isinstance(a, str)]
    removals = [str(r) for r in removals if isinstance(r, str)]
    result = set_auto_fix_whitelist(additions=additions, removals=removals)
    if result.get("ok"):
        # Schedules page reads /api/schedule/config; no panel cache to bust.
        pass
    return result


def _post_file_fix(body: dict, ctx: dict) -> dict:
    fix_id = body.get("fix_id")
    rel_path = body.get("path")
    if not isinstance(fix_id, str) or not fix_id.strip():
        return {"ok": False, "error": "fix_id required"}
    if not isinstance(rel_path, str) or not rel_path.strip():
        return {"ok": False, "error": "path required"}
    result = apply_file_fix(fix_id.strip(), rel_path.strip())
    if result.get("ok"):
        ctx["invalidate_panel"]("file_health")
    return result


def _get_job_detail(suffix: str, params: dict) -> dict:
    """GET /api/job/<id> — drawer payload for one job."""
    job_id = (suffix or "").strip("/").strip()
    return collect_job_detail(job_id)


def _get_schedule_config(suffix: str, params: dict) -> dict:
    """GET /api/schedule/config — full schedule-config + known auto-fix IDs.

    Used by /settings/schedules (whitelist toggles) and /settings/technical
    (raw config viewer). Suffix is ignored; we always serve the whole config.
    """
    cfg = read_schedule_config() or {}
    af = cfg.get("auto_fix") or {}
    whitelist = af.get("whitelist") or []
    from single_repo import SCHEDULE_CONFIG_PATH
    return {
        "ok": True,
        "config": cfg,
        "config_path": str(SCHEDULE_CONFIG_PATH),
        "auto_fix_whitelist": whitelist,
        "known_auto_fix_ids": sorted(KNOWN_AUTO_FIX_IDS),
        "presets": sorted(SCHEDULE_PRESETS.keys()),
    }


GET_ROUTES = {
    "/api/job/": _get_job_detail,
    "/api/schedule/config": _get_schedule_config,
}


POST_ROUTES = {
    "/api/actions/resolve":   _post_mark_resolved,
    "/api/actions/unresolve": _post_unmark_resolved,
    "/api/schedule/preset":    _post_schedule_preset,
    "/api/schedule/whitelist": _post_schedule_whitelist,
    "/api/file-health/fix":    _post_file_fix,
}


def main() -> None:
    print(f"[bcos-dashboard] repo root: {REPO_ROOT}")
    serve(
        panels(),
        title="BCOS Dashboard",
        subtitle=f"Context maintenance — {REPO_ROOT.name}",
        port=DEFAULT_PORT,
        host="127.0.0.1",
        refresh_ms=30000,
        auto_port=True,
        open_browser=False,
        post_routes=POST_ROUTES,
        get_routes=GET_ROUTES,
        hidden_panels=_settings_panels(),
    )


if __name__ == "__main__":
    main()

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
    get_auto_commit,
    read_config as read_schedule_config,
    set_auto_commit,
    set_auto_fix_whitelist,
)
from file_health import apply_fix as apply_file_fix  # noqa: E402
from atlas_collectors import (  # noqa: E402
    collect_atlas_ecosystem,
    collect_atlas_lifecycle,
    collect_atlas_ownership,
    collect_atlas_relationships,
)


# Port resolution: per-repo stable assignment via port_assign.py, with the
# BCOS_DASHBOARD_PORT env var winning if explicitly set.
#
# This means: in a multi-repo setup where every repo ships its own
# bcos-dashboard, each gets its own stable port — no fights, no surprise
# bookmark breakage. The registry lives at ~/.local-dashboard/bcos-dashboard-ports.json
# and is human-editable.
from port_assign import assign_port  # noqa: E402

# REPO_ROOT is imported below in single_repo; we need it earlier here.
def _repo_root_eager() -> Path:
    override = os.environ.get("BCOS_REPO_ROOT", "").strip()
    if override:
        return Path(override).resolve()
    # bcos-dashboard/ -> scripts/ -> .claude/ -> repo root
    return Path(__file__).resolve().parents[3]

_DASH_PORT, _PORT_SOURCE = assign_port(
    repo_id=_repo_root_eager().name,
    repo_path=str(_repo_root_eager()),
)
DEFAULT_PORT = _DASH_PORT


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
        # still feeds the cockpit's per-job maintenance strip via
        # collect_jobs_panel() (called inside collect_cockpit()), and the
        # per-job drawer fetches /api/job/<id> directly. No standalone
        # panel — clicking a dot opens the drawer.
        # snapshot_freshness, run_history, file_health used to render here
        # as standalone panels (Steps 1-3). Step 5 moved them behind
        # /settings/{technical,runs,files}; their collectors still feed
        # /api/panel/<id> for those sub-pages, and snapshot_freshness still
        # surfaces in the cockpit headline when stale.
    ]


def _hidden_panels() -> list[Panel]:
    """Panels exposed only via /api/panel/<id> for routed sub-pages.

    Not part of the main panels() list (so they don't render in the
    cockpit grid), but still need to live in the panel_map so /settings
    and /atlas clients can fetch them via /api/panel/<id>.
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
        Panel(
            id="atlas_ownership",
            title="Context Atlas",
            kind="atlas_ownership",
            span=12,
            ttl=120,
            collector=collect_atlas_ownership,
            collector_args=lambda params: (params.get("scope") or "context",),
        ),
        Panel(
            id="atlas_lifecycle",
            title="Context lifecycle",
            kind="atlas_lifecycle",
            span=12,
            ttl=120,
            collector=collect_atlas_lifecycle,
            collector_args=lambda params: (params.get("scope") or "context",),
        ),
        Panel(
            id="atlas_relationships",
            title="Context relationships",
            kind="atlas_relationships",
            span=12,
            ttl=120,
            collector=collect_atlas_relationships,
            collector_args=lambda params: (params.get("scope") or "context",),
        ),
        Panel(
            id="atlas_ecosystem",
            title="Context ecosystem",
            kind="atlas_ecosystem",
            span=12,
            ttl=120,
            collector=collect_atlas_ecosystem,
            collector_args=lambda params: (params.get("scope") or "context",),
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


def _post_auto_commit(body: dict, ctx: dict) -> dict:
    """POST /api/schedule/auto-commit — flip the global auto-commit toggle.

    Body: {"enabled": true|false}. Writes to `jobs.digest.auto_commit` in
    `schedule-config.json`. The dispatcher reads this on its next run.
    """
    if "enabled" not in body:
        return {"ok": False, "error": "enabled (bool) required"}
    enabled = body.get("enabled")
    if not isinstance(enabled, bool):
        return {"ok": False, "error": "enabled must be true or false"}
    return set_auto_commit(enabled)


def _get_auto_commit(suffix: str, params: dict) -> dict:
    """GET /api/schedule/auto-commit — current value of the toggle."""
    return {"enabled": get_auto_commit()}


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


def _post_atlas_move(body: dict, ctx: dict) -> dict:
    """Move a docs markdown file between BCOS lifecycle buckets."""
    rel_path = body.get("path")
    action = body.get("action")
    if not isinstance(rel_path, str) or not rel_path.strip():
        return {"ok": False, "error": "path required"}
    if not isinstance(action, str) or not action.strip():
        return {"ok": False, "error": "action required"}

    import shutil
    src = (REPO_ROOT / rel_path).resolve()
    docs_root = (REPO_ROOT / "docs").resolve()
    try:
        src.relative_to(docs_root)
    except ValueError:
        return {"ok": False, "error": "path must be inside docs/"}
    if not src.is_file() or src.suffix.lower() != ".md":
        return {"ok": False, "error": "markdown file not found"}

    action = action.strip().lower()
    if action in {"promote", "activate", "restore"}:
        dest_dir = docs_root
    elif action == "archive":
        dest_dir = docs_root / "_archive"
    else:
        return {"ok": False, "error": f"unsupported action: {action}"}

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.resolve() == src:
        return {"ok": True, "status": "already_there", "path": rel_path}
    if dest.exists():
        return {"ok": False, "error": f"destination exists: {dest.relative_to(REPO_ROOT).as_posix()}"}

    shutil.move(str(src), str(dest))
    for pid in ("atlas_ownership", "atlas_lifecycle", "atlas_relationships", "atlas_ecosystem", "cockpit"):
        ctx["invalidate_panel"](pid)
    return {
        "ok": True,
        "status": "moved",
        "from": rel_path,
        "to": dest.relative_to(REPO_ROOT).as_posix(),
    }


def _post_atlas_open(body: dict, ctx: dict) -> dict:
    """Open a repo-local file or its folder from the local dashboard."""
    rel_path = body.get("path")
    target = str(body.get("target") or "file").strip().lower()
    if not isinstance(rel_path, str) or not rel_path.strip():
        return {"ok": False, "error": "path required"}
    if target not in {"file", "folder"}:
        return {"ok": False, "error": "target must be file or folder"}

    path = (REPO_ROOT / rel_path).resolve()
    repo_root = REPO_ROOT.resolve()
    try:
        path.relative_to(repo_root)
    except ValueError:
        return {"ok": False, "error": "path must be inside repo"}
    if not path.exists():
        return {"ok": False, "error": "path not found"}

    open_path = path.parent if target == "folder" and path.is_file() else path
    if target == "folder" and not open_path.is_dir():
        return {"ok": False, "error": "folder not found"}

    import os
    import subprocess
    import sys
    if sys.platform.startswith("win"):
        os.startfile(str(open_path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(open_path)])
    else:
        subprocess.Popen(["xdg-open", str(open_path)])
    return {
        "ok": True,
        "target": target,
        "path": open_path.relative_to(repo_root).as_posix(),
    }


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


# --- BCOS framework sync wiring -------------------------------------------
# Three POST actions (start_sync / refresh / view-last) + one GET drawer feed.
# All delegate to bcos_sync.py; this run.py file just forwards the JSON body.

def _post_bcos_sync(body: dict, ctx: dict) -> dict:
    from bcos_sync import start_sync
    flags = {
        "review":     bool(body.get("review", True)),
        "autocommit": bool(body.get("autocommit", True)),
        "push":       bool(body.get("push", True)),
    }
    result = start_sync(flags)
    if result.get("ok"):
        ctx["invalidate_panel"]("cockpit")
    return result


def _post_bcos_refresh(body: dict, ctx: dict) -> dict:
    from bcos_sync import refresh_freshness
    result = refresh_freshness()
    ctx["invalidate_panel"]("cockpit")
    return result


def _get_bcos_run(suffix: str, params: dict) -> dict:
    """GET /api/bcos/run/<run_id> — drawer payload for one sync run.

    If suffix is empty or "last", returns the most recent run.
    """
    from bcos_sync import get_run, last_run_id
    rid = (suffix or "").strip("/").strip()
    if rid in ("", "last"):
        rid = last_run_id() or ""
    if not rid:
        return {"ok": False, "error": "no runs yet"}
    return get_run(rid)


# --- Context Atlas ---------------------------------------------------------
# Phase 1 surface: a single debug endpoint that returns the full atlas dict.
# The Atlas lens collectors / page shell land in Phases 2-6.

def _get_atlas(suffix: str, params: dict) -> dict:
    """GET /api/atlas — full atlas dict for inspection.

    `?summary=1` returns counts + domain list only (cheap; safe to poll).
    """
    from atlas_ingest import build_atlas
    atlas = build_atlas()
    if params.get("summary") in ("1", "true", "yes"):
        return {
            "ok": True,
            "generated_at": atlas["generated_at"],
            "counts": atlas["counts"],
            "domains": {
                k: {"doc_count": v["doc_count"],
                    "total_bytes": v["total_bytes"],
                    "avg_age_days": v["avg_age_days"]}
                for k, v in atlas["domains"].items()
            },
            "lifecycle_counts": {k: len(v) for k, v in atlas["lifecycle"].items()},
            "edge_count": len(atlas["edges"]),
            "orphan_count": len(atlas["orphans"]),
        }
    return {"ok": True, "atlas": atlas}


def _get_profile(suffix: str, params: dict) -> dict:
    """GET /api/profile — current repo profile + available options."""
    from bcos_profile import collect_profile
    return collect_profile()


def _post_profile(body: dict, ctx: dict) -> dict:
    """POST /api/profile — switch shared ↔ personal.

    Body: {"profile": "shared" | "personal", "dry_run"?: bool}
    Returns the structured result from bcos_profile.set_profile().
    """
    from bcos_profile import set_profile
    target = (body or {}).get("profile")
    if not isinstance(target, str):
        return {"ok": False, "error": "profile required (shared|personal)"}
    dry = bool((body or {}).get("dry_run", False))
    result = set_profile(target, dry_run=dry)
    if result.get("ok") and not dry:
        # Profile change can affect what shows up in jobs/files panels
        # (different files now tracked or ignored). Force a refresh.
        ctx["invalidate_panel"]("cockpit")
        ctx["invalidate_panel"]("jobs_panel")
        ctx["invalidate_panel"]("file_health")
    return result


def _get_commands(suffix: str, params: dict) -> dict:
    """GET /api/commands — list user-triggered commands the dashboard can fire."""
    commands = []
    for cmd_id, spec in COMMAND_REGISTRY.items():
        commands.append({
            "id": cmd_id,
            "label": spec.get("label", cmd_id),
            "args": [
                {"flag": flag, "key": key, "required": required}
                for flag, key, required in spec.get("args", [])
            ],
            "destructive": bool(spec.get("destructive")),
            "script": spec["script"],
        })
    return {"ok": True, "commands": commands}


def _get_wiki_pages(suffix: str, params: dict) -> dict:
    """GET /api/wiki/pages — list wiki page slugs for slug pickers in command cards."""
    pages = []
    for sub in ("pages", "source-summary"):
        base = REPO_ROOT / "docs" / "_wiki" / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            slug = path.stem
            try:
                _scripts = REPO_ROOT / ".claude" / "scripts"
                if str(_scripts) not in sys.path:
                    sys.path.insert(0, str(_scripts))
                from _wiki_yaml import parse_frontmatter  # type: ignore[import-not-found]
                fm = parse_frontmatter(path) or {}
            except Exception:  # noqa: BLE001
                fm = {}
            pages.append({
                "slug": slug,
                "name": (fm.get("name") or slug),
                "subdir": sub,
                "page_type": (fm.get("page-type") or fm.get("type") or ""),
                "status": (fm.get("status") or "active"),
            })
    return {"ok": True, "pages": pages, "count": len(pages)}


GET_ROUTES = {
    "/api/job/": _get_job_detail,
    "/api/schedule/config": _get_schedule_config,
    "/api/schedule/auto-commit": _get_auto_commit,
    "/api/profile": _get_profile,
    "/api/bcos/run/": _get_bcos_run,
    "/api/atlas": _get_atlas,
    "/api/commands": _get_commands,
    "/api/wiki/pages": _get_wiki_pages,
}


def _post_onboard_schedule(body: dict, ctx: dict) -> dict:
    """POST /api/onboard/schedule — one-click 'enable maintenance routine'.

    Creates `schedule-config.json` from the framework template if it
    doesn't already exist. After this, the dispatcher reads it daily
    and the cockpit cards switch from "Schedule" → "Run now".

    Two prerequisites can fail:
    - The template doesn't exist (broken install — show copy-pasteable
      `python .claude/scripts/update.py` remediation)
    - schedule-config.json already exists (idempotent — return ok with
      a "already scheduled" status)

    Both failure modes return structured remediation the client can
    render as guidance, not a generic error.
    """
    config_path = REPO_ROOT / ".claude" / "quality" / "schedule-config.json"
    template_path = REPO_ROOT / ".claude" / "quality" / "schedule-config.template.json"

    if config_path.is_file():
        ctx["invalidate_panel"]("cockpit")
        ctx["invalidate_panel"]("jobs_panel")
        return {
            "ok": True,
            "status": "already_scheduled",
            "message": "Maintenance routine is already scheduled.",
            "config_path": str(config_path),
        }

    if not template_path.is_file():
        return {
            "ok": False,
            "status": "missing_template",
            "error": "schedule-config.template.json is missing — your BCOS install may be incomplete.",
            "remediation": {
                "summary": "Run the framework install/update to fetch the template:",
                "command": "python .claude/scripts/update.py",
                "then": "Reload this page and click Schedule again.",
            },
        }

    try:
        import shutil
        config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template_path, config_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": "write_failed",
            "error": f"Could not write {config_path.name}: {type(exc).__name__}: {exc}",
            "remediation": {
                "summary": "The dashboard couldn't write the config file. Copy it manually:",
                "command": f"cp {template_path} {config_path}",
                "then": "Reload this page.",
            },
        }

    ctx["invalidate_panel"]("cockpit")
    ctx["invalidate_panel"]("jobs_panel")
    return {
        "ok": True,
        "status": "scheduled",
        "message": "Maintenance routine scheduled. The dispatcher will run on its next daily trigger.",
        "config_path": str(config_path),
    }


def _post_run_job_now(body: dict, ctx: dict) -> dict:
    """POST /api/jobs/run-now — trigger a job from the dashboard.

    Two paths:
    - Scriptable jobs (index-health, auto-fix-audit) run their primary
      mechanical entry-point via subprocess. Returns the script's last
      output line so the user gets immediate feedback.
    - Judgement jobs and not-yet-scriptable wiki jobs return a `chat_hint`
      the client surfaces as a copyable command. The dashboard is honest
      about what it can and cannot run without Claude.

    The full dispatcher logic lives in Claude (per the SKILL.md references)
    so this endpoint only kicks the mechanical sub-pieces. For a real
    end-to-end run, the user types 'run the X job' in chat.
    """
    job_id = (body or {}).get("job")
    if not isinstance(job_id, str) or not job_id.strip():
        return {"ok": False, "error": "job required"}
    job_id = job_id.strip()

    # Map of scriptable jobs to their primary mechanical entry-points.
    # None means "no standalone script yet — punts to chat".
    SCRIPTABLE = {
        "index-health":           ["python", ".claude/scripts/build_document_index.py"],
        "auto-fix-audit":         ["python", ".claude/scripts/auto_fix_audit.py"],
        "lifecycle-sweep":        ["python", ".claude/scripts/lifecycle_sweep.py"],
        "wiki-stale-propagation": ["python", ".claude/scripts/run_wiki_stale_propagation.py"],
        "wiki-source-refresh":    ["python", ".claude/scripts/run_wiki_source_refresh.py"],
        "wiki-graveyard":         ["python", ".claude/scripts/run_wiki_graveyard.py"],
        "wiki-coverage-audit":    ["python", ".claude/scripts/run_wiki_coverage_audit.py"],
        "wiki-canonical-drift":   ["python", ".claude/scripts/run_wiki_canonical_drift.py"],
    }

    cmd = SCRIPTABLE.get(job_id)
    if cmd is not None:
        import subprocess
        try:
            proc = subprocess.run(
                cmd, cwd=str(REPO_ROOT),
                capture_output=True, text=True, timeout=60, check=False,
            )
            stdout = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            tail = (stdout or stderr).splitlines()[-1] if (stdout or stderr) else ""
            ctx["invalidate_panel"]("cockpit")
            ctx["invalidate_panel"]("jobs_panel")
            return {
                "ok": proc.returncode == 0,
                "job": job_id,
                "exit_code": proc.returncode,
                "summary": tail or "(no output)",
                "ran": "script",
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "job": job_id, "error": "script timed out (60s)"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "job": job_id, "error": f"{type(exc).__name__}: {exc}"}

    # Falls through for judgement jobs + scriptable-but-no-script-yet jobs.
    return {
        "ok": True,
        "job": job_id,
        "ran": "chat-hint",
        "chat_hint": f"run the {job_id} job",
        "message": (
            f"This check needs Claude in the loop. Tell Claude: "
            f"“run the {job_id} job”"
        ),
    }


def _post_run_command(body: dict, ctx: dict) -> dict:
    """POST /api/commands/run — execute a user-action command from the dashboard.

    Body: {"id": "<command-id>", "args": {...}}

    Mirrors _post_run_job_now but for user-triggered commands (mechanical
    equivalents of slash subcommands like /wiki review, /wiki archive). Each
    entry in COMMAND_REGISTRY declares:
      - script: path to a cmd_*.py
      - args: ordered list of (flag, value) pairs to pass; flags map to body.args keys
      - confirm_flag: optional flag (e.g. "--confirm") added when body.args.confirmed=True
      - destructive: bool — UI must show a confirmation modal before posting

    The script's stdout JSON is returned verbatim under `result`; non-zero exit
    sets ok=False. Cockpit + jobs_panel caches are invalidated so any sidecar
    findings the script wrote land immediately.
    """
    import subprocess

    command_id = (body or {}).get("id")
    args = (body or {}).get("args") or {}
    if not isinstance(command_id, str) or not command_id.strip():
        return {"ok": False, "error": "id required", "status": 400}
    command_id = command_id.strip()

    spec = COMMAND_REGISTRY.get(command_id)
    if spec is None:
        return {"ok": False, "error": f"unknown command: {command_id}", "status": 404}

    if spec.get("destructive") and not args.get("confirmed"):
        return {
            "ok": False, "command": command_id, "status": "needs_confirm",
            "error": "Destructive command — set args.confirmed=true after user approval.",
            "destructive": True,
        }

    cmd: list[str] = ["python", spec["script"]]
    missing: list[str] = []
    for flag, key, required in spec.get("args", []):
        val = args.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            if required:
                missing.append(key)
            continue
        cmd.extend([flag, str(val)])
    if spec.get("destructive") and args.get("confirmed"):
        cmd.append("--confirm")

    if missing:
        return {
            "ok": False, "command": command_id, "status": "missing_args",
            "error": f"missing required args: {missing}",
        }

    try:
        proc = subprocess.run(
            cmd, cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=60, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "command": command_id, "error": "script timed out (60s)"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "command": command_id, "error": f"{type(exc).__name__}: {exc}"}

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    parsed: dict | None = None
    if stdout:
        try:
            import json as _json
            parsed = _json.loads(stdout.splitlines()[-1])
        except Exception:  # noqa: BLE001
            parsed = None

    ctx["invalidate_panel"]("cockpit")
    ctx["invalidate_panel"]("jobs_panel")
    return {
        "ok": proc.returncode == 0,
        "command": command_id,
        "exit_code": proc.returncode,
        "result": parsed,
        "raw_stdout": stdout if not parsed else None,
        "raw_stderr": stderr if proc.returncode != 0 else None,
    }


# Registry of mechanical user-triggered commands. Each entry maps to a
# cmd_*.py script. The args list is (cli-flag, body-arg-key, required) tuples
# applied in order. Adding a new command = adding a script + one entry here.
COMMAND_REGISTRY: dict[str, dict] = {
    "wiki-init": {
        "script": ".claude/scripts/cmd_wiki_init.py",
        "args": [],
        "label": "Initialize wiki zone",
    },
    "wiki-review": {
        "script": ".claude/scripts/cmd_wiki_review.py",
        "args": [("--slug", "slug", True)],
        "label": "Mark page reviewed",
    },
    "wiki-archive": {
        "script": ".claude/scripts/cmd_wiki_archive.py",
        "args": [("--slug", "slug", True)],
        "label": "Archive page",
    },
    "wiki-queue-add": {
        "script": ".claude/scripts/cmd_wiki_queue_add.py",
        "args": [("--url", "url", True)],
        "label": "Queue URL for fetch",
    },
    "wiki-lint": {
        "script": ".claude/scripts/cmd_wiki_lint.py",
        "args": [],
        "label": "Lint wiki schema",
    },
    "wiki-search": {
        "script": ".claude/scripts/cmd_wiki_search.py",
        "args": [("--query", "query", True)],
        "label": "Search wiki pages",
    },
    "wiki-remove": {
        "script": ".claude/scripts/cmd_wiki_remove.py",
        "args": [("--slug", "slug", True)],
        "label": "Remove page (destructive)",
        "destructive": True,
    },
}


POST_ROUTES = {
    "/api/actions/resolve":   _post_mark_resolved,
    "/api/actions/unresolve": _post_unmark_resolved,
    "/api/commands/run":      _post_run_command,
    "/api/jobs/run-now":      _post_run_job_now,
    "/api/onboard/schedule":  _post_onboard_schedule,
    "/api/profile":           _post_profile,
    "/api/schedule/preset":    _post_schedule_preset,
    "/api/schedule/whitelist": _post_schedule_whitelist,
    "/api/schedule/auto-commit": _post_auto_commit,
    "/api/file-health/fix":    _post_file_fix,
    "/api/atlas/move":         _post_atlas_move,
    "/api/atlas/open":         _post_atlas_open,
    "/api/bcos/sync":          _post_bcos_sync,
    "/api/bcos/refresh":       _post_bcos_refresh,
}


def main() -> None:
    print(f"[bcos-dashboard] repo root: {REPO_ROOT}")
    print(f"[bcos-dashboard] port: {DEFAULT_PORT} (source: {_PORT_SOURCE})")
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
        hidden_panels=_hidden_panels(),
    )


if __name__ == "__main__":
    main()

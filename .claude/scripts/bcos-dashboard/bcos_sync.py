"""
bcos_sync.py — Single-repo BCOS framework sync + freshness.

This module is what the cockpit's "BCOS framework" block plugs into. It mirrors
the umbrella-level §0 BCOS Framework pane that ships in the theo-portfolio
Command Center, simplified for the single-repo case (each end-user has one
BCOS install).

Public API used by the dashboard:

  collect_freshness()                -> dict  (cockpit data block)
  start_sync(flags)                  -> dict  ({"run_id": "..."}) — non-blocking
  get_run(run_id)                    -> dict  (status + stdout snippet)
  read_log(run_id)                   -> str   (full log for the drawer)
  last_run_id()                      -> str | None
  refresh_freshness()                -> dict  (force-refetch upstream tip)

State & files:

  ~/.local-dashboard/bcos-sync-stamps/<repo-id>.json  — last successful sync
  ~/.local-dashboard/bcos-upstream.json               — cached upstream tip
  ~/.local-dashboard/bcos-runs/<run-id>.log           — drawer log per run
  ~/.local-dashboard/bcos-runs/last.txt               — pointer to most recent

Design notes:

  * No AI-judged CLAUDE.md review step. Removed 2026-05-12 — see the long
    comment block before _run_sync. CLAUDE.md is handled by the marker-fence
    contract in _claude_md.py: framework owns inside CORE markers (verbatim
    replace), user owns outside (untouched).
  * One thread per run. A module-level lock prevents concurrent syncs in the
    same dashboard process.
  * No SQLite. Logs are plain files. Run state is in-memory + the log file
    on disk; "last run" survives a dashboard restart via last.txt.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# REPO_ROOT comes from single_repo.py — same detection logic the rest of the
# framework dashboard already uses, so we share its env-var override.
from single_repo import REPO_ROOT  # noqa: E402

# ---------------------------------------------------------------------------
# Constants & paths
# ---------------------------------------------------------------------------

UPSTREAM_REPO = "walm00/business-context-os"
UPSTREAM_BRANCH = "main"
UPSTREAM_TTL_SECONDS = 3600  # "Refresh status" button bypasses cache.

LOCAL_STATE = Path.home() / ".local-dashboard"
SYNC_STAMPS_DIR = LOCAL_STATE / "bcos-sync-stamps"
UPSTREAM_CACHE = LOCAL_STATE / "bcos-upstream.json"
RUNS_DIR = LOCAL_STATE / "bcos-runs"
LAST_RUN_PTR = RUNS_DIR / "last.txt"

REPO_ID = REPO_ROOT.name  # used as the sync-stamp filename


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

_LOCK = threading.Lock()
_active: dict = {"run_id": None, "started_at": None, "status": None}
# In-memory snapshot of finished runs for the GET endpoint. The log file is
# the durable record; this map just avoids re-reading status from disk.
_runs: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _format_relative(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        return iso_str
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"


def _log_path(run_id: str) -> Path:
    return RUNS_DIR / f"{run_id}.log"


def _append_log(run_id: str, line: str) -> None:
    try:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        with _log_path(run_id).open("a", encoding="utf-8") as fh:
            fh.write(line.rstrip("\n") + "\n")
    except OSError:
        pass


def _set_last_run(run_id: str) -> None:
    try:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        LAST_RUN_PTR.write_text(run_id, encoding="utf-8")
    except OSError:
        pass


def last_run_id() -> str | None:
    try:
        return LAST_RUN_PTR.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def read_log(run_id: str) -> str:
    if not run_id:
        return ""
    try:
        return _log_path(run_id).read_text(encoding="utf-8")
    except OSError:
        return ""


def _write_sync_stamp() -> None:
    try:
        SYNC_STAMPS_DIR.mkdir(parents=True, exist_ok=True)
        (SYNC_STAMPS_DIR / f"{REPO_ID}.json").write_text(
            json.dumps({"synced_at": _iso_now(), "repo_id": REPO_ID}),
            encoding="utf-8",
        )
    except OSError:
        pass


def _read_sync_stamp() -> str | None:
    """Return ISO timestamp of last successful sync, or None."""
    stamp_file = SYNC_STAMPS_DIR / f"{REPO_ID}.json"
    if stamp_file.is_file():
        try:
            return json.loads(stamp_file.read_text(encoding="utf-8")).get("synced_at")
        except (OSError, ValueError):
            return None
    # Legacy fallback: bcos-claude-reference.md mtime, in case the user synced
    # via update.py before this dashboard module existed.
    ref = REPO_ROOT / ".claude" / "bcos-claude-reference.md"
    if ref.is_file():
        try:
            mt = datetime.fromtimestamp(ref.stat().st_mtime, tz=timezone.utc)
            return mt.isoformat(timespec="seconds").replace("+00:00", "Z")
        except OSError:
            return None
    return None


# ---------------------------------------------------------------------------
# Upstream tip — GitHub API
# ---------------------------------------------------------------------------

def _fetch_upstream(force: bool = False) -> dict:
    """Return {sha, date, message, fetched_at} or {error}."""
    now = datetime.now(timezone.utc)
    if not force:
        try:
            cached = json.loads(UPSTREAM_CACHE.read_text(encoding="utf-8"))
            fetched = datetime.fromisoformat(cached["fetched_at"].replace("Z", "+00:00"))
            if (now - fetched).total_seconds() < UPSTREAM_TTL_SECONDS:
                return cached
        except (OSError, ValueError, KeyError):
            pass

    url = f"https://api.github.com/repos/{UPSTREAM_REPO}/commits/{UPSTREAM_BRANCH}"
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"bcos-dashboard/{REPO_ID}",
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        return {"error": f"{type(e).__name__}: {e}"}

    result = {
        "sha": data.get("sha", "")[:7],
        "date": data.get("commit", {}).get("committer", {}).get("date", ""),
        "message": (data.get("commit", {}).get("message", "").splitlines() or [""])[0][:80],
        "fetched_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    try:
        UPSTREAM_CACHE.parent.mkdir(parents=True, exist_ok=True)
        UPSTREAM_CACHE.write_text(json.dumps(result), encoding="utf-8")
    except OSError:
        pass
    return result


# ---------------------------------------------------------------------------
# Freshness — what the cockpit renders
# ---------------------------------------------------------------------------

def collect_freshness() -> dict:
    """Cockpit data block. Cheap; safe to call on every render."""
    upstream = _fetch_upstream(force=False)
    local_iso = _read_sync_stamp()

    # Status logic mirrors the Command Center.
    if "error" in upstream:
        status, severity = "upstream check failed", "warn"
    elif local_iso is None:
        status, severity = "never synced", "warn"
    else:
        try:
            up_dt = datetime.fromisoformat(upstream["date"].replace("Z", "+00:00"))
            loc_dt = datetime.fromisoformat(local_iso.replace("Z", "+00:00"))
            if (up_dt - loc_dt).total_seconds() <= 60:
                status, severity = "up to date", "ok"
            else:
                status, severity = "behind upstream", "warn"
        except (ValueError, KeyError):
            status, severity = "unknown", "warn"

    return {
        "repo_id": REPO_ID,
        "status": status,
        "severity": severity,
        "last_synced": _format_relative(local_iso) if local_iso else "never",
        "last_synced_iso": local_iso,
        "upstream": {
            "sha": upstream.get("sha", ""),
            "date": upstream.get("date", ""),
            "message": upstream.get("message", ""),
            "fetched_at": upstream.get("fetched_at", ""),
            "error": upstream.get("error"),
        },
        "active_run_id": _active.get("run_id"),
        "last_run_id": last_run_id(),
    }


def refresh_freshness() -> dict:
    """Force-refetch the upstream tip (ignores TTL)."""
    upstream = _fetch_upstream(force=True)
    return {"ok": "error" not in upstream, "upstream": upstream}


# ---------------------------------------------------------------------------
# CLAUDE.md review — REMOVED 2026-05-12.
#
# Previously this module ran an AI-judged merge of local CLAUDE.md against
# upstream after every sync. That mechanism had additive-merge semantics:
# anything "missing from local but present in the reference" got re-added,
# even when local had intentionally trimmed it. Result: every framework-side
# trim of CLAUDE.md got silently resurrected on the next sync of every
# installed repo (discovered against execution-os during the v1.9.0 → v1.10.0
# trim).
#
# The correct contract is much simpler:
#   - Inside <!-- BCOS:CORE:START --> / <!-- BCOS:CORE:END -->: framework owns
#     it; _claude_md.py replaces it verbatim on every update. Always wins.
#   - Outside those markers: user owns it; update.py never touches it.
#
# Both sides of the fence are unambiguous, so the AI-judged review had
# nothing to actually decide — it could only introduce bugs. The previous
# CORE block is still saved to .claude/bcos-claude-reference.md by
# _claude_md.py:103-108 as a pure recovery artifact (diff-against-on-demand;
# nothing reads it back into CLAUDE.md programmatically).
#
# Symmetric fix applied in bcos-umbrella's command_center_dashboard 2026-05-12.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Sync orchestration
# ---------------------------------------------------------------------------

def _git_is_clean() -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return False, f"git status failed: {type(e).__name__}"
    if proc.returncode != 0:
        return False, f"git status exit {proc.returncode}"
    return (proc.stdout.strip() == ""), ("dirty working tree" if proc.stdout.strip() else "")


def _do_commit_push(run_id: str, push: bool) -> str:
    """Stage all changes, commit with a fixed message, optionally push."""
    msg = "chore(bcos): sync framework to upstream"
    try:
        subprocess.run(["git", "-C", str(REPO_ROOT), "add", "-A"], check=False, timeout=30)
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "commit", "-m", msg],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            if "nothing to commit" in (proc.stdout + proc.stderr).lower():
                _append_log(run_id, "[commit] nothing to commit")
                return "no changes"
            _append_log(run_id, f"[commit] failed exit {proc.returncode}: {proc.stderr[:300]}")
            return f"FAILED: commit exit {proc.returncode}"
        _append_log(run_id, "[commit] committed")
        if push:
            pproc = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "push"],
                capture_output=True, text=True, timeout=120,
                encoding="utf-8", errors="replace",
            )
            if pproc.returncode == 0:
                _append_log(run_id, "[push] pushed")
                return "committed + pushed"
            _append_log(run_id, f"[push] failed: {pproc.stderr[:300]}")
            return "committed (push failed)"
        return "committed"
    except (subprocess.TimeoutExpired, OSError) as e:
        _append_log(run_id, f"[commit] {type(e).__name__}: {e}")
        return f"FAILED: {type(e).__name__}"


def _run_sync(run_id: str, flags: dict) -> None:
    """Worker thread: update.py → commit/push.

    The AI-judged CLAUDE.md review step was removed 2026-05-12 — see the
    long comment block above for the rationale. Sync is now strictly
    update.py + (optional) commit + (optional) push.
    """
    started = _iso_now()
    _append_log(run_id, f"=== bcos sync — {REPO_ID} ===")
    _append_log(run_id, f"started_at: {started}")
    _append_log(run_id, f"flags: autocommit={flags.get('autocommit')} push={flags.get('push')}")

    state = {"update_exit": -1, "commit": None}

    update_script = REPO_ROOT / ".claude" / "scripts" / "update.py"
    if not update_script.is_file():
        _append_log(run_id, f"[update] ERROR — {update_script} not found")
        _finalize(run_id, state, exit_code=1)
        return

    pre_clean, dirty_reason = (True, "")
    if flags.get("autocommit"):
        pre_clean, dirty_reason = _git_is_clean()
        if not pre_clean:
            _append_log(run_id, f"[pre-check] {dirty_reason} — autocommit will be skipped")

    # Phase A — update.py
    _append_log(run_id, "[update] running update.py --yes ...")
    try:
        proc = subprocess.run(
            [sys.executable, str(update_script), "--yes"],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=600,
        )
        state["update_exit"] = proc.returncode
        if proc.stdout:
            _append_log(run_id, "[update] stdout:")
            for ln in proc.stdout.splitlines():
                _append_log(run_id, f"  {ln}")
        if proc.stderr:
            _append_log(run_id, f"[update] stderr: {proc.stderr.strip()[:500]}")
        _append_log(run_id, f"[update] exit {proc.returncode}")
    except subprocess.TimeoutExpired:
        _append_log(run_id, "[update] TIMEOUT after 10min")
        state["update_exit"] = 124
    except OSError as e:
        _append_log(run_id, f"[update] {type(e).__name__}: {e}")
        state["update_exit"] = 1

    if state["update_exit"] != 0:
        _finalize(run_id, state, exit_code=state["update_exit"])
        return

    _write_sync_stamp()
    _append_log(run_id, "[stamp] wrote sync stamp")

    # Phase B — commit + push. The previous Phase B (AI-judged CLAUDE.md
    # review) was removed; see module-top comment.
    if flags.get("autocommit"):
        if not pre_clean:
            state["commit"] = f"skipped ({dirty_reason})"
            _append_log(run_id, f"[commit] {state['commit']}")
        else:
            state["commit"] = _do_commit_push(run_id, push=bool(flags.get("push")))
    else:
        _append_log(run_id, "[commit] skipped (autocommit off)")

    _finalize(run_id, state, exit_code=0)


def _finalize(run_id: str, state: dict, exit_code: int) -> None:
    ended = _iso_now()
    _append_log(run_id, f"=== done — exit {exit_code} — {ended} ===")
    with _LOCK:
        _runs[run_id] = {
            "run_id": run_id,
            "status": "done",
            "exit_code": exit_code,
            "ended_at": ended,
            "state": state,
        }
        if _active.get("run_id") == run_id:
            _active["run_id"] = None
            _active["started_at"] = None
            _active["status"] = None


# ---------------------------------------------------------------------------
# Public action API
# ---------------------------------------------------------------------------

def start_sync(flags: dict | None = None) -> dict:
    """Spawn a worker thread to run the sync. Returns immediately with run_id.

    Flags: {autocommit: bool, push: bool}. The legacy `review` flag is accepted
    silently for backward compatibility with older callers but is now a no-op
    (see module-top comment for why the review phase was removed).
    """
    flags = flags or {"autocommit": True, "push": True}
    # Strip legacy review flag if a caller still passes it.
    flags.pop("review", None)
    with _LOCK:
        if _active.get("run_id"):
            return {"ok": False, "error": "another sync is already running",
                    "run_id": _active["run_id"]}
        run_id = secrets.token_hex(6)
        _active["run_id"] = run_id
        _active["started_at"] = _iso_now()
        _active["status"] = "running"
        _runs[run_id] = {"run_id": run_id, "status": "running",
                         "started_at": _active["started_at"]}
        _set_last_run(run_id)

    t = threading.Thread(target=_run_sync, args=(run_id, flags), daemon=True)
    t.start()
    return {"ok": True, "run_id": run_id}


def get_run(run_id: str) -> dict:
    """Return current status + log path for a run."""
    if not run_id:
        return {"ok": False, "error": "run_id required"}
    with _LOCK:
        rec = dict(_runs.get(run_id) or {})
    if not rec:
        # Run may have finished before this dashboard process started — read
        # its log from disk if present.
        if _log_path(run_id).is_file():
            return {"ok": True, "run_id": run_id, "status": "done",
                    "log": read_log(run_id)}
        return {"ok": False, "error": "unknown run_id"}
    rec["log"] = read_log(run_id)
    rec["ok"] = True
    return rec

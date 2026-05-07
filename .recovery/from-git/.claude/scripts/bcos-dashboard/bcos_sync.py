"""
bcos_sync.py — Single-repo BCOS framework sync, review, and freshness.

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

  * CLAUDE.md review uses schema-in-prompt + --output-format json. NO reliance
    on --json-schema (which is only available in newer Claude CLI versions).
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
# CLAUDE.md review — schema-in-prompt (no --json-schema)
# ---------------------------------------------------------------------------

_REVIEW_PROMPT = (
    "You are reviewing a CLAUDE.md drift between this repo and its upstream BCOS framework.\n"
    "Compare the local CLAUDE.md against `.claude/bcos-claude-reference.md` (the upstream copy).\n"
    "Do NOT delete any files — the caller handles cleanup.\n"
    "\n"
    "Three possible verdicts:\n"
    "  NOOP         — local CLAUDE.md is already functionally identical to upstream.\n"
    "  MERGED       — upstream has additive, non-conflicting changes; merge them in via Edit\n"
    "                 preserving ALL local overrides.\n"
    "  REVIEW_NEEDED — upstream changes conflict or are substantive; do NOT edit anything.\n"
    "\n"
    "Return ONLY a JSON object on the LAST LINE of your response, with NO surrounding prose:\n"
    '  {"verdict": "NOOP|MERGED|REVIEW_NEEDED", "summary": "<one sentence>"}\n'
    "No markdown fences. No other output after the JSON."
)


def _parse_review_output(raw: str) -> dict | None:
    """Extract {verdict, summary} from claude CLI stdout.

    The CLI returns a JSON wrapper containing the model's text under `result`.
    We then locate the last JSON object in that text — robust to small
    formatting variations.
    """
    if not raw:
        return None
    # Step 1: unwrap CLI envelope.
    inner = raw
    try:
        wrapper = json.loads(raw)
        if isinstance(wrapper, dict):
            inner = wrapper.get("result") or wrapper.get("structured_output") or raw
            if isinstance(inner, dict):
                return inner if "verdict" in inner else None
            if not isinstance(inner, str):
                inner = raw
    except ValueError:
        pass

    # Step 2: scan for the last `{...}` block in `inner`.
    text = inner.strip()
    last_open = text.rfind("{")
    while last_open != -1:
        try:
            obj = json.loads(text[last_open:])
            if isinstance(obj, dict) and "verdict" in obj:
                return obj
        except ValueError:
            pass
        last_open = text.rfind("{", 0, last_open)
    return None


def _run_review(run_id: str) -> str:
    """Execute the CLAUDE.md review. Returns a status string for the log."""
    ref_file = REPO_ROOT / ".claude" / "bcos-claude-reference.md"
    claude_md = REPO_ROOT / "CLAUDE.md"
    if not (ref_file.is_file() and claude_md.is_file()):
        _append_log(run_id, "[review] skipped — reference or CLAUDE.md missing")
        return "SKIPPED (no ref file)"

    claude_exe = shutil.which("claude")
    if not claude_exe:
        _append_log(run_id, "[review] ERROR: claude CLI not on PATH")
        return "ERROR: claude not on PATH"

    base = [
        "-p",
        "--permission-mode", "acceptEdits",
        "--output-format", "json",
        _REVIEW_PROMPT,
    ]
    if sys.platform.startswith("win") and claude_exe.lower().endswith((".cmd", ".bat", ".ps1")):
        argv = ["cmd", "/c", "claude", *base]
    else:
        argv = [claude_exe, *base]

    _append_log(run_id, "[review] launching claude CLI...")
    try:
        proc = subprocess.run(
            argv, cwd=str(REPO_ROOT),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        _append_log(run_id, "[review] TIMEOUT after 5min")
        return "TIMEOUT"
    except OSError as e:
        _append_log(run_id, f"[review] ERROR: {type(e).__name__}: {e}")
        return f"ERROR: {type(e).__name__}"

    if proc.stderr:
        _append_log(run_id, f"[review] stderr: {proc.stderr.strip()[:500]}")
    if proc.returncode != 0:
        _append_log(run_id, f"[review] exit {proc.returncode}")
        _append_log(run_id, (proc.stdout or "").strip()[:1500] or "(no output)")
        return f"ERROR: exit {proc.returncode}"

    verdict_obj = _parse_review_output(proc.stdout or "")
    if not verdict_obj:
        snippet = (proc.stdout or "").strip()[:200]
        _append_log(run_id, f"[review] unparseable result: {snippet}")
        return "ERROR: unparseable result"

    v = verdict_obj["verdict"]
    summary = (verdict_obj.get("summary") or "").strip()[:200]
    label_map = {"NOOP": "NOOP", "MERGED": "MERGED", "REVIEW_NEEDED": "REVIEW NEEDED"}
    status = f"{label_map.get(v, v)}: {summary}" if summary else label_map.get(v, v)
    _append_log(run_id, f"[review] verdict — {status}")

    # On NOOP/MERGED, delete the reference file (Claude has either reconciled
    # the differences or there were none). REVIEW_NEEDED leaves it in place
    # for the human to handle.
    if v in ("MERGED", "NOOP"):
        try:
            ref_file.unlink(missing_ok=True)
            _append_log(run_id, "[review] deleted bcos-claude-reference.md")
        except OSError as e:
            _append_log(run_id, f"[review] could not delete ref file: {e}")
    return status


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
    msg = "chore(bcos): sync framework to upstream + CLAUDE.md review"
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
    """Worker thread: update.py → review → commit/push."""
    started = _iso_now()
    _append_log(run_id, f"=== bcos sync — {REPO_ID} ===")
    _append_log(run_id, f"started_at: {started}")
    _append_log(run_id, f"flags: review={flags.get('review')} autocommit={flags.get('autocommit')} push={flags.get('push')}")

    state = {"update_exit": -1, "review": None, "commit": None}

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

    # Phase B — CLAUDE.md review
    if flags.get("review"):
        state["review"] = _run_review(run_id)
    else:
        _append_log(run_id, "[review] skipped (flag off)")

    # Phase C — commit + push
    review_failed = isinstance(state["review"], str) and state["review"].startswith(("ERROR", "TIMEOUT"))
    if flags.get("autocommit"):
        if not pre_clean:
            state["commit"] = f"skipped ({dirty_reason})"
            _append_log(run_id, f"[commit] {state['commit']}")
        elif review_failed:
            state["commit"] = "skipped (review failed)"
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
    """Spawn a worker thread to run the sync. Returns immediately with run_id."""
    flags = flags or {"review": True, "autocommit": True, "push": True}
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

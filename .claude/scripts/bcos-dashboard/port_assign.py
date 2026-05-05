"""
port_assign.py — Stable per-repo port assignment for the BCOS dashboard.

Why this exists
---------------
End-user machines often have several BCOS-enabled repos, each shipping its
own bcos-dashboard. They all default to port 8091, so the first one wins
and the rest fail to bind. We need:

  1. Each repo to get its OWN port — different from siblings.
  2. The SAME port across launches — bookmarks shouldn't break.
  3. No manual config — picks happen on first launch.
  4. A discoverable record — so Command Center / `lsof` users can see what's
     where without inspecting processes.

How it works
------------
A single user-level JSON file at ~/.local-dashboard/bcos-dashboard-ports.json
maps `repo_id -> {port, path, registered_at, last_launch_at}`.

On launch, `assign_port(repo_id, repo_path)` returns the port to use:

  * Honor an explicit BCOS_DASHBOARD_PORT env override (above all).
  * If repo_id is already registered AND the path matches AND the port is
    still in the allowed range, reuse it (even if currently bound — the
    server's auto_port=True takes care of bumping if it's a different
    PID; we just refuse to grant the same port to two DIFFERENT repos).
  * Else find the lowest free port in [8091, 8190] that isn't registered
    to any other repo, register it, and return it.

On every launch the registry's `last_launch_at` is bumped so a future
"clean stale entries" command can prune repos that haven't launched in N
days. Not implemented yet — the registry is small enough to ignore.

The registry is the source of truth users can edit by hand to force a
repo onto a specific port. We never overwrite an existing entry's port
unless the path itself has changed (repo moved on disk).
"""
from __future__ import annotations

import json
import os
import socket
import threading
from datetime import datetime, timezone
from pathlib import Path

LOCAL_STATE = Path.home() / ".local-dashboard"
PORTS_FILE = LOCAL_STATE / "bcos-dashboard-ports.json"

# Port range. 8091 is the historical default — keep it as the first slot
# so single-repo users with no neighbors get the familiar number.
PORT_RANGE_START = 8091
PORT_RANGE_END = 8190  # inclusive

_LOCK = threading.Lock()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_registry() -> dict:
    try:
        return json.loads(PORTS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_registry(reg: dict) -> None:
    LOCAL_STATE.mkdir(parents=True, exist_ok=True)
    PORTS_FILE.write_text(
        json.dumps(reg, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _is_port_free(port: int) -> bool:
    """True if no listener is currently bound to (127.0.0.1, port).

    Note: a `False` here doesn't mean unusable — auto_port=True in serve()
    will skip bound ports. We use this only when picking a NEW assignment
    so the freshly-registered port has the best chance of working today.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.2)
        s.bind(("127.0.0.1", port))
        s.close()
        return True
    except OSError:
        return False


def assign_port(repo_id: str, repo_path: str | None = None) -> tuple[int, str]:
    """Return (port, source) for the given repo.

    `source` is one of:
      "env"        — BCOS_DASHBOARD_PORT env var was set, registry untouched.
      "registered" — repo was already in the registry; reusing.
      "fresh"      — first time we've seen this repo; picked + registered.

    repo_path is stored alongside the port so a hand-edit of the registry
    (or detection of a moved repo) is straightforward.
    """
    env = os.environ.get("BCOS_DASHBOARD_PORT", "").strip()
    if env.isdigit():
        return int(env), "env"

    with _LOCK:
        reg = _read_registry()
        existing = reg.get(repo_id)
        if (
            isinstance(existing, dict)
            and isinstance(existing.get("port"), int)
            and PORT_RANGE_START <= existing["port"] <= PORT_RANGE_END
            # If a path is recorded and we know the current path, a mismatch
            # means the repo was probably moved — recycle the port to avoid
            # a stale-entry orphan.
            and (not repo_path or not existing.get("path")
                 or existing["path"] == repo_path)
        ):
            existing["last_launch_at"] = _iso_now()
            reg[repo_id] = existing
            _write_registry(reg)
            return existing["port"], "registered"

        # Pick a fresh port. Skip those already claimed by another repo,
        # and prefer ports that aren't bound right now so first-launch is
        # the friendliest possible experience.
        claimed = {
            entry["port"] for entry in reg.values()
            if isinstance(entry, dict) and isinstance(entry.get("port"), int)
        }
        chosen: int | None = None
        for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
            if port in claimed:
                continue
            if _is_port_free(port):
                chosen = port
                break
        if chosen is None:
            # Every port in the friendly range is either claimed or bound.
            # Fall back to the first unclaimed slot — server's auto_port
            # will deal with bound-but-unclaimed conflicts at startup.
            for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
                if port not in claimed:
                    chosen = port
                    break
        if chosen is None:
            raise RuntimeError(
                f"No free port available in [{PORT_RANGE_START},{PORT_RANGE_END}]; "
                f"manually edit {PORTS_FILE} to clear stale entries."
            )

        reg[repo_id] = {
            "port": chosen,
            "path": repo_path or "",
            "registered_at": _iso_now(),
            "last_launch_at": _iso_now(),
        }
        _write_registry(reg)
        return chosen, "fresh"


def list_assignments() -> dict:
    """Return the current registry as a plain dict — used by CLI inspectors."""
    return _read_registry()


def release(repo_id: str) -> bool:
    """Remove a repo's port reservation. Returns True if something was removed."""
    with _LOCK:
        reg = _read_registry()
        if repo_id in reg:
            del reg[repo_id]
            _write_registry(reg)
            return True
        return False


if __name__ == "__main__":
    # `python port_assign.py` — print the registry, useful for debugging.
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "release":
        if len(sys.argv) < 3:
            print("usage: python port_assign.py release <repo-id>")
            sys.exit(2)
        ok = release(sys.argv[2])
        print("released" if ok else "no such repo_id")
        sys.exit(0 if ok else 1)
    reg = list_assignments()
    if not reg:
        print(f"(no assignments in {PORTS_FILE})")
    else:
        print(f"# {PORTS_FILE}")
        for repo_id, entry in sorted(reg.items()):
            print(f"  {repo_id:40s}  port={entry.get('port')}  path={entry.get('path')}")

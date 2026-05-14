#!/usr/bin/env python3
"""
_settings_merge.py — `merge_settings_json` entry point used by `update.py`.

Lives in its own module so tests + tooling can import the merge logic
without triggering `update.py`'s pause-sentinel guard (which runs at
import time in framework-source repos). `update.py` re-exports
`merge_settings_json` for backwards compatibility.
"""

from __future__ import annotations

import json as _json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from _settings_reconciler import SettingsReconciler  # noqa: E402


def merge_settings_json(upstream_path: str, local_path: str,
                        *, dry_run: bool = False) -> int:
    """Merge upstream settings.json hooks and permission allowlist into local.

    Permission allow rules are reconciled through the marker-aware
    `SettingsReconciler` (`_settings_reconciler.py`) — see its docstring
    for the 5-state contract. Hooks remain additive (matched by command
    string) — they don't need marker semantics because BCOS is the only
    writer.

    Returns count of mutations (hooks added + allow rules ADD/ADOPT/REVOKE).
    When `dry_run=True`, no disk write occurs but the return count is the
    same as a real run.
    """
    with open(upstream_path, "r", encoding="utf-8") as f:
        upstream = _json.load(f)
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            local = _json.load(f)
    else:
        local = {}

    mutations = 0

    # --- hooks (additive, keyed by command string — no marker needed) ---
    if "hooks" in upstream:
        if "hooks" not in local:
            local["hooks"] = {}
        for event, matchers in upstream.get("hooks", {}).items():
            if event not in local["hooks"]:
                local["hooks"][event] = matchers
                mutations += len(matchers)
                continue

            local_commands = set()
            for matcher_group in local["hooks"][event]:
                for hook in matcher_group.get("hooks", []):
                    local_commands.add(hook.get("command", ""))

            for matcher_group in matchers:
                for hook in matcher_group.get("hooks", []):
                    cmd = hook.get("command", "")
                    if cmd and cmd not in local_commands:
                        local["hooks"][event].append(matcher_group)
                        mutations += 1
                        break  # one add per matcher group

    # --- permissions.allow (marker-aware 5-state reconciler) ---
    upstream_allow = upstream.get("permissions", {}).get("allow", [])
    plan = None
    if upstream_allow:
        reconciler = SettingsReconciler(upstream_allow)
        local, plan = reconciler.apply(local)
        mutations += plan.total_changes()

    # --- atomic write (only if there's anything to write) ---
    if mutations > 0 and not dry_run:
        SettingsReconciler.write_atomic(local_path, local)

    # Surface the plan in human terms when there's anything noteworthy.
    if plan is not None and (plan.total_changes() > 0 or plan.adopt):
        action = "would" if dry_run else "did"
        if plan.adopt and plan.total_changes() == len(plan.adopt):
            # Pure first-run-after-v2.0 ADOPT migration — no ADDs, no REVOKEs.
            print(f"  settings.json: {action} ADOPT {len(plan.adopt)} rule(s) into "
                  f"`_bcosManagedPermissions` (first run after v2.0 upgrade).")
        else:
            print(f"  settings.json: {action} apply 5-state plan — "
                  f"{len(plan.add)} ADD, {len(plan.adopt)} ADOPT, "
                  f"{len(plan.revoke)} REVOKE, "
                  f"{len(plan.respect_user_removal)} tombstone(s), "
                  f"{len(plan.user_added_preserved)} user-added preserved.")

    return mutations

#!/usr/bin/env python3
"""
_settings_reconciler.py — marker-aware writer for `.claude/settings.json`.

BCOS tracks its own shipped allow rules in the top-level
`_bcosManagedPermissions` key. The reconciler distinguishes BCOS-shipped
rules from user-added rules and respects user removals (tombstones).

Consumed by `update.py:merge_settings_json` (Surface 1, project-level
writer). For the user-facing rescue command (drop the marker so the next
update re-ADOPTs from current allow), see `reset_permissions_marker.py`.

5-state reconciler:

  ┌──────────────────────────┬──────────────┬────────────┬─────────────────────────┐
  │ Rule in OLD marker?      │ Rule in allow│ State      │ Action                  │
  ├──────────────────────────┼──────────────┼────────────┼─────────────────────────┤
  │ No                       │ No           │ ADD        │ Append to allow + mark  │
  │ No                       │ Yes          │ ADOPT      │ Add to marker only      │
  │ Yes                      │ Yes          │ NOOP       │ Skip                    │
  │ Yes                      │ No           │ TOMBSTONE  │ Skip (RESPECT_USER_REM) │
  │ Was in old marker, not   │ (any)        │ REVOKE     │ Drop from allow + marker│
  │ in new shipped list      │              │            │                         │
  └──────────────────────────┴──────────────┴────────────┴─────────────────────────┘

User-added rules (in `allow`, not in old marker, not in shipped) are
invisible to the reconciler. Touched by no codepath.

Atomic write contract: changes are written to `<file>.tmp` in the same
directory, fsync'd, then atomically renamed over the target. On any
exception the tempfile is cleaned up and the original file is unchanged.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

MARKER_KEY = "_bcosManagedPermissions"


@dataclass
class ReconcilePlan:
    """The 5-state diff produced by SettingsReconciler.plan().

    Lists are stable-ordered: rules appear in the order they were
    encountered in `shipped_allow` (forward pass) or `existing_marker`
    (reverse pass). This makes `--dry-run` output deterministic.
    """
    add: list = field(default_factory=list)
    adopt: list = field(default_factory=list)
    noop: list = field(default_factory=list)
    respect_user_removal: list = field(default_factory=list)
    revoke: list = field(default_factory=list)
    # Informational — rules the reconciler will NOT touch
    user_added_preserved: list = field(default_factory=list)

    def total_changes(self) -> int:
        """Count of state transitions that mutate `allow` or the marker.

        NOOP and TOMBSTONE (RESPECT_USER_REMOVAL) are not counted —
        they're stable states. user_added_preserved is informational.
        """
        return len(self.add) + len(self.adopt) + len(self.revoke)

    def to_dict(self) -> dict:
        return {
            "add": list(self.add),
            "adopt": list(self.adopt),
            "noop": list(self.noop),
            "respect_user_removal": list(self.respect_user_removal),
            "revoke": list(self.revoke),
            "user_added_preserved": list(self.user_added_preserved),
            "total_changes": self.total_changes(),
        }

    def format_human(self, *, verbose: bool = False) -> str:
        """Human-readable summary. Set verbose=True to list every rule."""
        lines = [
            f"  ADD:                    {len(self.add)} rule(s)",
            f"  ADOPT:                  {len(self.adopt)} rule(s)",
            f"  NOOP:                   {len(self.noop)} rule(s)",
            f"  RESPECT_USER_REMOVAL:   {len(self.respect_user_removal)} rule(s)",
            f"  REVOKE:                 {len(self.revoke)} rule(s)",
            f"  user-added (untouched): {len(self.user_added_preserved)} rule(s)",
        ]
        if verbose:
            def render_section(label: str, prefix: str, items: list) -> None:
                if not items:
                    return
                lines.append("")
                lines.append(f"  {label}:")
                for r in items:
                    lines.append(f"    {prefix} {r}")
            render_section("ADD", "+", self.add)
            render_section("ADOPT", "~", self.adopt)
            render_section("REVOKE", "-", self.revoke)
            render_section("RESPECT_USER_REMOVAL (tombstoned)", ".", self.respect_user_removal)
            render_section("user-added (preserved)", " ", self.user_added_preserved)
        return "\n".join(lines)


class SettingsReconciler:
    """Marker-aware writer for `.claude/settings.json > permissions.allow`.

    Construct with `shipped_allow` (the current canonical allow list) and
    optionally `marker_key` (defaults to BCOS's `_bcosManagedPermissions`).
    Use `.plan(existing)` for a non-mutating diff, or `.apply(existing)` to
    produce both the new settings dict and the plan in one pass.

    The `marker_key` parameter exists so other tooling that writes to the
    same `.claude/settings.json` from outside BCOS can use the same class
    with its own marker (avoiding clobbers across writers). BCOS itself
    always uses the default.

    The class guarantees it touches only the rows in `shipped_allow` and
    its own marker slice — every other top-level key and every user-added
    rule (in `allow` but not in the marker) is left alone.
    """

    # Default marker — preserved as a class attribute for callers that
    # introspect (e.g. reset_permissions_marker.py). Per-instance value
    # is on self.marker_key.
    MARKER_KEY = MARKER_KEY

    def __init__(self, shipped_allow, marker_key: "str | None" = None):
        self.shipped_allow = list(shipped_allow)
        self.marker_key = marker_key or self.MARKER_KEY

    # ----- planning (pure, no mutation) -----

    def plan(self, existing: dict) -> ReconcilePlan:
        """Compute the 5-state diff without mutating `existing`."""
        shipped_set = set(self.shipped_allow)
        existing_allow = list(existing.get("permissions", {}).get("allow", []))
        existing_marker_list = list(existing.get(self.marker_key, []))
        existing_marker = set(existing_marker_list)
        allow_set = set(existing_allow)

        plan = ReconcilePlan()

        # Forward pass — classify every shipped rule
        for rule in self.shipped_allow:
            in_marker = rule in existing_marker
            in_allow = rule in allow_set
            if not in_marker and not in_allow:
                plan.add.append(rule)
            elif not in_marker and in_allow:
                plan.adopt.append(rule)
            elif in_marker and in_allow:
                plan.noop.append(rule)
            else:
                # in_marker and not in_allow → user removed; tombstone
                plan.respect_user_removal.append(rule)

        # Reverse pass — old marker entries no longer shipped → REVOKE
        for rule in existing_marker_list:
            if rule not in shipped_set:
                plan.revoke.append(rule)

        # Informational — rules in allow that BCOS doesn't track at all
        # (user-added or another plugin's slice if they don't use a marker)
        for rule in existing_allow:
            if rule not in shipped_set and rule not in existing_marker:
                plan.user_added_preserved.append(rule)

        return plan

    # ----- applying (produces a new settings dict; never mutates the input) -----

    def apply(self, existing: dict) -> "tuple[dict, ReconcilePlan]":
        """Compute the plan and produce a new settings dict that reflects it.

        Returns (new_settings, plan). The input `existing` is not mutated.

        New marker = every rule in `shipped_allow` (whether currently
        adopted, freshly added, or tombstoned). Revoked rules drop from
        both `allow` and the marker. User-added rules stay in `allow`
        and never enter the marker.
        """
        plan = self.plan(existing)
        new_settings = copy.deepcopy(existing)
        new_settings.setdefault("permissions", {}).setdefault("allow", [])
        allow = new_settings["permissions"]["allow"]

        # ADD: append to allow (marker rebuild below covers the marker side)
        for rule in plan.add:
            if rule not in allow:
                allow.append(rule)

        # REVOKE: drop from allow
        revoke_set = set(plan.revoke)
        if revoke_set:
            new_settings["permissions"]["allow"] = [
                r for r in allow if r not in revoke_set
            ]

        # Marker = every shipped rule. This is the elegant invariant:
        # the marker IS the current shipped contract. ADOPT, ADD, NOOP,
        # and RESPECT_USER_REMOVAL all end up represented exactly once.
        # REVOKE entries are absent (good — they're no longer ours).
        new_settings[self.marker_key] = list(self.shipped_allow)

        return new_settings, plan

    # ----- atomic disk write -----

    @staticmethod
    def write_atomic(path, settings: dict) -> None:
        """Write `settings` to `path` atomically.

        Strategy: write to a tempfile in the same directory, fsync if
        supported, then `os.replace` (atomic rename on POSIX; near-atomic
        on Windows). On any exception, tempfile is cleaned up; `path` is
        left unchanged.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
                f.write("\n")
                try:
                    f.flush()
                    os.fsync(f.fileno())
                except OSError:
                    pass  # some Windows filesystems reject fsync; acceptable
            os.replace(tmp_path, str(path))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

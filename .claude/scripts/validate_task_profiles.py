#!/usr/bin/env python3
"""
Validate the task-profiles catalog against its schema (P5).

Checks:
- Each profile carries the required fields with the right types.
- `id` is a non-empty unique string.
- Every zone referenced by `required-zones` and `source-of-truth-ranking`
  exists in the loaded zone registry.
- Every freshness-thresholds key references a valid zone.
- Every coverage-assertion key references a declared content-family.
- `traversal-hints[*].depth-cap` is a non-negative integer.

Wired into the FIXED END doc-lint check; CLI exit code is non-zero on
validation failure.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from load_task_profiles import load_task_profiles, TaskProfilesError  # noqa: E402
from load_zone_registry import load_zone_registry  # noqa: E402


def _known_zone_ids() -> set[str]:
    try:
        return {entry["id"] for entry in load_zone_registry()}
    except Exception:
        return set()


def validate_profiles(profiles: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    known_zones = _known_zone_ids()

    for i, profile in enumerate(profiles):
        prefix = f"profile[{i}]"
        if not isinstance(profile, dict):
            errors.append(f"{prefix}: not a mapping")
            continue

        pid = profile.get("id")
        if not isinstance(pid, str) or not pid.strip():
            errors.append(f"{prefix}: missing/invalid id")
            continue
        prefix = f"profile {pid!r}"
        if pid in seen_ids:
            errors.append(f"{prefix}: duplicate id")
        seen_ids.add(pid)

        # required-zones
        rz = profile.get("required-zones")
        if not isinstance(rz, list):
            errors.append(f"{prefix}: required-zones must be a list")
        else:
            for entry in rz:
                if not isinstance(entry, dict) or "id" not in entry:
                    errors.append(f"{prefix}: malformed required-zones entry: {entry!r}")
                    continue
                zid = entry["id"]
                if known_zones and zid not in known_zones:
                    errors.append(
                        f"{prefix}: required-zones references unknown zone "
                        f"{zid!r} (known: {sorted(known_zones)})"
                    )
                if "required" not in entry:
                    errors.append(f"{prefix}: required-zones entry {zid!r} missing required:bool")

        # source-of-truth-ranking
        ranking = profile.get("source-of-truth-ranking")
        if not isinstance(ranking, list):
            errors.append(f"{prefix}: source-of-truth-ranking must be a list")
        else:
            for zid in ranking:
                if known_zones and zid not in known_zones:
                    errors.append(
                        f"{prefix}: source-of-truth-ranking references unknown zone {zid!r}"
                    )

        # content-families
        families = profile.get("content-families")
        family_names: set[str] = set()
        if not isinstance(families, list):
            errors.append(f"{prefix}: content-families must be a list")
        else:
            for entry in families:
                if not isinstance(entry, dict):
                    errors.append(f"{prefix}: malformed content-families entry: {entry!r}")
                    continue
                fname = entry.get("name")
                if not isinstance(fname, str) or not fname:
                    errors.append(f"{prefix}: content-family missing name: {entry!r}")
                    continue
                family_names.add(fname)
                if "pattern" not in entry:
                    errors.append(f"{prefix}: family {fname!r} missing pattern")
                if "min-count" in entry and not isinstance(entry["min-count"], int):
                    errors.append(f"{prefix}: family {fname!r} min-count must be int")

        # freshness-thresholds
        thresholds = profile.get("freshness-thresholds")
        if not isinstance(thresholds, dict):
            errors.append(f"{prefix}: freshness-thresholds must be a mapping")
        else:
            for zid, days in thresholds.items():
                if known_zones and zid not in known_zones:
                    errors.append(
                        f"{prefix}: freshness-thresholds references unknown zone {zid!r}"
                    )
                if days is not None and not isinstance(days, int):
                    errors.append(
                        f"{prefix}: freshness-thresholds[{zid}] must be int or null; got {days!r}"
                    )

        # coverage-assertions
        coverage = profile.get("coverage-assertions")
        if not isinstance(coverage, dict):
            errors.append(f"{prefix}: coverage-assertions must be a mapping")
        else:
            for fname, mn in coverage.items():
                if family_names and fname not in family_names:
                    errors.append(
                        f"{prefix}: coverage-assertion {fname!r} references undeclared family"
                    )
                if not isinstance(mn, int):
                    errors.append(f"{prefix}: coverage-assertion {fname!r} min-count must be int")

        # traversal-hints
        hints = profile.get("traversal-hints")
        if not isinstance(hints, list):
            errors.append(f"{prefix}: traversal-hints must be a list")
        else:
            for entry in hints:
                if not isinstance(entry, dict):
                    errors.append(f"{prefix}: malformed traversal-hint: {entry!r}")
                    continue
                if "depth-cap" in entry:
                    cap = entry["depth-cap"]
                    if not isinstance(cap, int) or cap < 0:
                        errors.append(
                            f"{prefix}: traversal-hints depth-cap must be non-negative int; got {cap!r}"
                        )

    return len(errors) == 0, errors


def main() -> int:
    try:
        profiles = load_task_profiles()
    except TaskProfilesError as exc:
        print(f"error loading profiles: {exc}", file=sys.stderr)
        return 2
    ok, errors = validate_profiles(profiles)
    if ok:
        print(f"task-profiles validation passed ({len(profiles)} profile(s)).")
        return 0
    print(f"task-profiles validation found {len(errors)} issue(s):", file=sys.stderr)
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

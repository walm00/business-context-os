"""
schedule_editor.py — Validated writes to `.claude/quality/schedule-config.json`.

The schedule-tune skill (a BCOS skill) edits the same file via natural
language. This module is its deterministic twin: preset-button clicks
in the dashboard write structured changes directly. Both paths respect
the same schema, so a click is equivalent to "run {job} on {cadence}".

Public API:
    apply_preset(job_id: str, preset: str) -> dict
        Known presets: "daily", "mon_wed_fri", "weekly_mon", "off".
    set_auto_fix_whitelist(additions: list, removals: list) -> dict
        Idempotent — returns the resulting whitelist.
    read_config() -> dict
        Parses the config with safe defaults on missing / unreadable.

All writes go through `_write_config_atomic` which:
  1. Parses the existing file (fail if invalid JSON).
  2. Applies the mutation in-memory.
  3. Writes to a .tmp file then atomically renames — no partial state.
  4. Preserves unknown keys and field order where possible.

Why not extend the schedule-tune skill? schedule-tune is NL-first and
routes through Claude. That's the right tool for free-form edits like
"run audit twice a week". One-button presets are deterministic; running
them through an LLM adds latency, variance, and no value.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from threading import Lock

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from single_repo import REPO_ROOT, SCHEDULE_CONFIG_PATH  # noqa: E402

_WRITE_LOCK = Lock()

# Preset → {enabled, schedule}. `schedule` follows the schedule-tune
# shorthand: "daily" = every weekday; comma-separated three-letter
# weekdays; "off" is handled via enabled:false (schedule preserved).
PRESETS = {
    "daily":        {"enabled": True,  "schedule": "daily"},
    "mon_wed_fri":  {"enabled": True,  "schedule": "mon,wed,fri"},
    "weekly_mon":   {"enabled": True,  "schedule": "mon"},
    "weekly_fri":   {"enabled": True,  "schedule": "fri"},
    "off":          {"enabled": False, "schedule": None},  # preserve existing
}

# Auto-fix IDs accepted by the schedule-tune whitelist. Match
# docs/_bcos-framework references/auto-fix-whitelist.md. Any ID outside
# this set is rejected by the API.
KNOWN_AUTO_FIX_IDS = {
    "missing-last-updated",
    "frontmatter-field-order",
    "trailing-whitespace",
    "eof-newline",
    "broken-xref-single-candidate",
}


def read_config() -> dict:
    if not SCHEDULE_CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(SCHEDULE_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_config_atomic(cfg: dict) -> None:
    SCHEDULE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SCHEDULE_CONFIG_PATH.with_suffix(".json.tmp")
    data = json.dumps(cfg, indent=2, ensure_ascii=False)
    with _WRITE_LOCK:
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(data)
            fh.write("\n")
        os.replace(tmp, SCHEDULE_CONFIG_PATH)


def apply_preset(job_id: str, preset: str) -> dict:
    if not job_id or not isinstance(job_id, str):
        return {"ok": False, "error": "job required"}
    if preset not in PRESETS:
        return {
            "ok": False,
            "error": f"unknown preset {preset!r}",
            "known": sorted(PRESETS.keys()),
        }
    cfg = read_config()
    if not cfg:
        return {"ok": False, "error": "schedule-config.json not found or unreadable"}
    jobs = cfg.setdefault("jobs", {})
    if not isinstance(jobs, dict):
        return {"ok": False, "error": "config.jobs is not an object"}

    entry = jobs.setdefault(job_id, {})
    if not isinstance(entry, dict):
        return {"ok": False, "error": f"config.jobs.{job_id} is not an object"}

    before = {"enabled": entry.get("enabled"), "schedule": entry.get("schedule")}
    spec = PRESETS[preset]
    entry["enabled"] = bool(spec["enabled"])
    if spec["schedule"] is not None:
        entry["schedule"] = spec["schedule"]
    # "off" preserves the existing schedule so re-enabling restores it.

    after = {"enabled": entry.get("enabled"), "schedule": entry.get("schedule")}
    _write_config_atomic(cfg)

    return {
        "ok": True,
        "job": job_id,
        "preset": preset,
        "before": before,
        "after": after,
    }


def set_auto_commit(enabled: bool) -> dict:
    """Toggle auto-commit globally for scheduled-job artifacts.

    When `auto_commit` is true, the dispatcher commits its generated
    artifacts (digest, index, diary, wake-up context) at the end of each run
    — but ONLY if the working tree has no other changes. Never pushes,
    never branches. Default is false.

    The flag lives at `jobs.digest.auto_commit` in `schedule-config.json`
    and is treated as the global toggle: if any job-level override is added
    later, this function still flips the canonical digest entry that the
    dispatcher reads.
    """
    cfg = read_config()
    if not cfg:
        return {"ok": False, "error": "schedule-config.json not found or unreadable"}
    jobs = cfg.setdefault("jobs", {})
    if not isinstance(jobs, dict):
        return {"ok": False, "error": "config.jobs is not an object"}
    digest = jobs.setdefault("digest", {})
    if not isinstance(digest, dict):
        return {"ok": False, "error": "config.jobs.digest is not an object"}

    before = bool(digest.get("auto_commit", False))
    digest["auto_commit"] = bool(enabled)
    after = bool(digest["auto_commit"])
    _write_config_atomic(cfg)

    return {"ok": True, "before": before, "after": after}


def get_auto_commit() -> bool:
    """Read the current auto-commit flag from `jobs.digest.auto_commit`."""
    cfg = read_config()
    digest = ((cfg or {}).get("jobs") or {}).get("digest") or {}
    return bool(digest.get("auto_commit", False))


def set_auto_fix_whitelist(additions: list | None = None, removals: list | None = None) -> dict:
    additions = additions or []
    removals = removals or []
    bad_add = [a for a in additions if a not in KNOWN_AUTO_FIX_IDS]
    if bad_add:
        return {
            "ok": False,
            "error": "unknown auto-fix ids",
            "unknown": bad_add,
            "known": sorted(KNOWN_AUTO_FIX_IDS),
        }
    cfg = read_config()
    if not cfg:
        return {"ok": False, "error": "schedule-config.json not found or unreadable"}
    af = cfg.setdefault("auto_fix", {})
    if not isinstance(af, dict):
        return {"ok": False, "error": "config.auto_fix is not an object"}
    current = af.get("whitelist") or []
    if not isinstance(current, list):
        current = []
    new_set = set(current)
    new_set.update(additions)
    new_set.difference_update(removals)
    ordered = [fid for fid in sorted(KNOWN_AUTO_FIX_IDS) if fid in new_set]
    # Append any unknown-but-kept IDs (shouldn't happen given the validation
    # above, but we're tolerant of existing config that predates this module).
    extras = [f for f in current if f in new_set and f not in ordered]
    result = ordered + extras
    af["whitelist"] = result
    _write_config_atomic(cfg)
    return {"ok": True, "whitelist": result, "added": additions, "removed": removals}

"""
auto_fix_audit.py — Friday weekly audit on the self-learning ladder's safety brake.

The auditor reads `.claude/quality/ecosystem/resolutions.jsonl` and looks for
signals that a learned rule (or a silently-applied auto-fix) is producing
trouble. v0.1 ships ONE check; P7_005 + P7_007 + P8_004 add four more on
top of the same pipeline.

Checks (per implementation-plan.md §D-04):

| # | Check                          | Phase    | Auto-action authority |
|---|--------------------------------|----------|------------------------|
| 1 | Reversal rate > 5% in 7 days   | P6 ✓    | recommend-only         |
| 2 | Validation failures (≥5 / ≥3 files / 24h) | P7_005 | AUTO-DISABLE (only check with this authority) |
| 3 | Downstream-error correlation   | P7_007   | recommend-only         |
| 4 | Semantic drift (LLM, opt-in)   | P8_005   | recommend-only         |
| 5 | Cross-rule flap (A→B→A)         | P8_004   | recommend-only         |

The audit() function returns a dict shape compatible with the typed-event
sidecar (`{findings: [...], auto_disabled: [...]}`) so the dispatcher can
fold its output into the daily digest just like any other job's emission.

Per D-04: only Check 2 has auto-action authority. Every other check
including Check 1 (reversal rate) is recommend-only — it surfaces an amber
card with [Demote] [Show evidence] [Keep silent] buttons. The user picks.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
_DASH = _HERE / "bcos-dashboard"
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))
from single_repo import REPO_ROOT  # noqa: E402

DEFAULT_RESOLUTIONS = REPO_ROOT / ".claude" / "quality" / "ecosystem" / "resolutions.jsonl"

# Reversal-rate threshold: strictly greater than 5%. A rule with exactly
# 5% reversal rate is borderline-OK; we want clear signal to surface a
# card. Move to a config knob in P7 if user feedback wants it tuneable.
REVERSAL_THRESHOLD = 0.05
REVERSAL_WINDOW_DAYS = 7

# Don't run reversal math against a rule with fewer than this many applied
# events — small samples produce 50%/100% reversal rates that are statistical
# noise. v0.1 uses a low bar so the auditor surfaces signal even early in
# adoption; P7 will revisit.
REVERSAL_MIN_N = 3

# Check 2 — validation-failure auto-disable (P7_005). The ONLY check with
# auto-action authority per D-04. Triggers a write to learning-blocklist.json
# when N≥5 events have subsequent_validation_status="failed" AND those events
# touch ≥3 distinct files within a 24-hour window. The min_distinct_targets
# gate (R-03) prevents schema-version drift on a single migration file from
# mass-disabling a rule that's actually correct.
VALIDATION_FAILURE_MIN_N = 5
VALIDATION_FAILURE_MIN_DISTINCT_TARGETS = 3
VALIDATION_FAILURE_WINDOW_HOURS = 24

# Check 3 — downstream-error correlation (P7_007). Recommend-only.
# Surfaces an amber card when a fix batch (≥3 applied events on the same
# rule) is followed by an `index-health` verdict flip from green→amber
# within 24h. The user judges whether the batch caused the flip.
DOWNSTREAM_BATCH_MIN_SIZE = 3
DOWNSTREAM_WINDOW_HOURS = 24
DOWNSTREAM_TRACKED_JOB = "index-health"


def _parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_rows(path: Path | None) -> list[dict[str, Any]]:
    p = path or DEFAULT_RESOLUTIONS
    if not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def _load_diary(path: Path | None) -> list[dict[str, Any]]:
    """Read schedule-diary.jsonl. Tolerates absent file (returns empty)."""
    if path is None:
        return []
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def _load_blocked_set(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return set(data.get("blocked") or [])


def _rule_id(finding_type: str, action_taken: str) -> str:
    return f"{finding_type}::{action_taken}"


# ---------------------------------------------------------------------------
# Check 1 — reversal rate (P6_003)
# ---------------------------------------------------------------------------


def check_reversal_rate(
    rows: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    window_days: int = REVERSAL_WINDOW_DAYS,
    threshold: float = REVERSAL_THRESHOLD,
) -> list[dict[str, Any]]:
    """Find rules where reversal_rate > threshold inside the rolling window.

    A rule's reversal rate inside the window =
        (count of `outcome=reverted` events) / (count of `outcome=applied` events)

    Both counts are scoped to `(rule_id, ts ≥ now - window_days)`. We do
    not pair specific applied/reverted events; a count ratio is enough
    signal at v0.1. P7+ may upgrade to per-target pairing for stronger
    correlation.

    Returns a list of typed-event findings (one per rule that crosses
    the threshold) in the standard sidecar shape. Findings are sorted
    by reversal_rate descending so the worst offender is `findings[0]`.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)

    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"applied": 0, "reverted": 0})

    for row in rows:
        ts = _parse_ts(row.get("ts"))
        if ts is None or ts < cutoff:
            continue  # outside window
        ft = row.get("finding_type")
        at = row.get("action_taken")
        if not ft or not at:
            continue
        outcome = row.get("outcome")
        if outcome not in ("applied", "reverted"):
            continue  # skipped/errored don't move the rate
        counts[_rule_id(ft, at)][outcome] += 1

    findings: list[dict[str, Any]] = []
    for rid, c in counts.items():
        n_applied = c["applied"]
        n_reverted = c["reverted"]
        if n_applied < REVERSAL_MIN_N:
            continue
        rate = n_reverted / n_applied
        if rate <= threshold:
            continue

        ft, _, at = rid.partition("::")
        findings.append({
            "finding_type": "rule-reversal-spike",
            "verdict": "amber",
            "emitted_by": "auto-fix-audit",
            "finding_attrs": {
                "rule_id": rid,
                "underlying_finding_type": ft,
                "underlying_action_taken": at,
                "n_applied": n_applied,
                "n_reverted": n_reverted,
                "reversal_rate": round(rate, 4),
                "window_days": window_days,
                "threshold_percent": int(threshold * 100),
            },
            "suggested_actions": ["demote-rule", "show-evidence", "keep-silent"],
        })

    findings.sort(key=lambda f: f["finding_attrs"]["reversal_rate"], reverse=True)
    return findings


# ---------------------------------------------------------------------------
# Check 2 — validation-failure auto-disable (P7_005)
# ---------------------------------------------------------------------------


def check_validation_failures(
    rows: list[dict[str, Any]],
    *,
    blocklist_path: Path | None,
    dry_run: bool,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Find rules whose subsequent_validation_status="failed" rate trips the
    auto-disable threshold. Per D-04 this is the only check with auto-action.

    Threshold: N≥5 failures across ≥3 distinct files in the last 24 hours.
    The distinct-targets gate (R-03 mitigation) blocks mass-disable when
    a single in-flight migration file produces 5 false-positives in a row.

    When `dry_run=False` and a rule trips, the rule_id is written to
    learning-blocklist.json (atomic temp-file rewrite via promote_resolutions
    helpers, sorted for byte-stability). When `dry_run=True` the would-be
    disable is reported in the result without touching disk.

    Returns a list of disable records (one per rule that tripped). The
    audit() entry-point folds these into `result["auto_disabled"]`.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=VALIDATION_FAILURE_WINDOW_HOURS)
    blocked_already = _load_blocked_set(blocklist_path)

    # Group failures by rule, tracking distinct targets.
    failures_per_rule: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"n_failed": 0, "targets": set(), "first_seen": None, "last_seen": None}
    )

    for row in rows:
        if row.get("subsequent_validation_status") != "failed":
            continue
        ts = _parse_ts(row.get("ts"))
        if ts is None or ts < cutoff:
            continue
        ft = row.get("finding_type")
        at = row.get("action_taken")
        if not ft or not at:
            continue
        rid = _rule_id(ft, at)
        bucket = failures_per_rule[rid]
        bucket["n_failed"] += 1
        target = row.get("action_target") or (row.get("finding_attrs") or {}).get("file")
        if target:
            bucket["targets"].add(target)
        if bucket["first_seen"] is None or ts < bucket["first_seen"]:
            bucket["first_seen"] = ts
        if bucket["last_seen"] is None or ts > bucket["last_seen"]:
            bucket["last_seen"] = ts

    disabled: list[dict[str, Any]] = []
    new_to_block: list[str] = []
    for rid, bucket in failures_per_rule.items():
        if bucket["n_failed"] < VALIDATION_FAILURE_MIN_N:
            continue
        if len(bucket["targets"]) < VALIDATION_FAILURE_MIN_DISTINCT_TARGETS:
            continue
        if rid in blocked_already:
            continue  # already disabled — idempotent

        ft, _, at = rid.partition("::")
        record = {
            "rule_id": rid,
            "finding_type": ft,
            "action_taken": at,
            "n_failed": bucket["n_failed"],
            "distinct_targets": len(bucket["targets"]),
            "window_hours": VALIDATION_FAILURE_WINDOW_HOURS,
            "first_failure_at": bucket["first_seen"].isoformat().replace("+00:00", "Z") if bucket["first_seen"] else None,
            "last_failure_at": bucket["last_seen"].isoformat().replace("+00:00", "Z") if bucket["last_seen"] else None,
            "dry_run": bool(dry_run),
        }
        disabled.append(record)
        if not dry_run:
            new_to_block.append(rid)

    # Wet path: persist the disables. We import promote_resolutions lazily
    # to avoid a hard dependency cycle (promote_resolutions doesn't depend
    # on this module, but might in future).
    if new_to_block and not dry_run:
        try:
            from promote_resolutions import add_to_blocklist  # type: ignore[import-not-found]
            for rid in new_to_block:
                add_to_blocklist(rid, blocklist_path=blocklist_path)
        except Exception as exc:  # noqa: BLE001
            # If we can't write the blocklist, downgrade the records to
            # dry_run=True so callers don't believe the rule was disabled.
            for d in disabled:
                d["dry_run"] = True
                d["error"] = f"blocklist write failed: {type(exc).__name__}: {exc}"

    return disabled


# ---------------------------------------------------------------------------
# Check 3 — downstream-error correlation (P7_007)
# ---------------------------------------------------------------------------


def check_downstream_errors(
    rows: list[dict[str, Any]],
    diary: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Surface rules whose fix batches preceded an index-health verdict flip.

    Recommend-only — never auto-disables. Algorithm:

    1. Group recent applied events into per-rule batches (events on the
       same rule_id, within DOWNSTREAM_WINDOW_HOURS of each other).
    2. For each batch with size ≥ DOWNSTREAM_BATCH_MIN_SIZE, look at the
       index-health diary entries before and after the batch's last event.
    3. If the most-recent BEFORE entry was green AND any AFTER entry within
       the window is amber/red, emit a typed-event finding.

    The user reads the card and decides if causation is real.
    """
    now = now or datetime.now(timezone.utc)
    window = timedelta(hours=DOWNSTREAM_WINDOW_HOURS)

    # Bucket events by rule_id and ts.
    by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("outcome") != "applied":
            continue
        ts = _parse_ts(row.get("ts"))
        if ts is None:
            continue
        ft = row.get("finding_type")
        at = row.get("action_taken")
        if not ft or not at:
            continue
        by_rule[_rule_id(ft, at)].append({**row, "_ts": ts})

    # Diary entries for the tracked job, sorted by ts ascending.
    diary_entries = []
    for d in diary:
        if d.get("job") != DOWNSTREAM_TRACKED_JOB:
            continue
        ts = _parse_ts(d.get("ts"))
        if ts is None:
            continue
        diary_entries.append({"ts": ts, "verdict": d.get("verdict")})
    diary_entries.sort(key=lambda e: e["ts"])

    findings: list[dict[str, Any]] = []
    seen_rule_ids: set[str] = set()  # one finding per rule per audit run

    for rid, events in by_rule.items():
        if rid in seen_rule_ids:
            continue
        events.sort(key=lambda r: r["_ts"])
        # Look for a recent batch (last entry within last 24h)
        last_event_ts = events[-1]["_ts"]
        if last_event_ts < now - window:
            continue
        batch = [e for e in events if last_event_ts - e["_ts"] <= window]
        if len(batch) < DOWNSTREAM_BATCH_MIN_SIZE:
            continue

        batch_end = max(e["_ts"] for e in batch)
        # Most recent BEFORE entry
        before = [d for d in diary_entries if d["ts"] < batch[0]["_ts"]]
        after = [d for d in diary_entries if batch_end <= d["ts"] <= batch_end + window]
        if not before or not after:
            continue
        verdict_before = before[-1]["verdict"]
        # Pick the most concerning AFTER verdict
        after_verdicts = {d["verdict"] for d in after}
        verdict_after = "red" if "red" in after_verdicts else ("amber" if "amber" in after_verdicts else "green")

        if verdict_before == "green" and verdict_after in ("amber", "red"):
            ft, _, at = rid.partition("::")
            findings.append({
                "finding_type": "rule-downstream-error",
                "verdict": "amber",
                "emitted_by": "auto-fix-audit",
                "finding_attrs": {
                    "rule_id": rid,
                    "underlying_finding_type": ft,
                    "underlying_action_taken": at,
                    "downstream_job": DOWNSTREAM_TRACKED_JOB,
                    "verdict_before": verdict_before,
                    "verdict_after": verdict_after,
                    "batch_size": len(batch),
                    "window_hours": DOWNSTREAM_WINDOW_HOURS,
                },
                "suggested_actions": ["show-evidence", "investigate", "dismiss"],
            })
            seen_rule_ids.add(rid)

    return findings


# ---------------------------------------------------------------------------
# Public audit() entry point
# ---------------------------------------------------------------------------


def audit(
    *,
    resolutions_path: Path | None = None,
    diary_path: Path | None = None,
    blocklist_path: Path | None = None,
    dry_run: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run all enabled checks and return the typed-event payload.

    Shape:
        {
          "findings":      [...],   # typed events for the digest sidecar
          "auto_disabled": [...],   # records of rules disabled this run (Check 2 only)
          "checks_run":    ["reversal-rate", "validation-failure", "downstream-error"],
          "events_inspected": int,
        }

    `dry_run=True` (the default) means the auditor reports what WOULD be
    auto-disabled but does not write to learning-blocklist.json. The
    Friday scheduled job invokes with `dry_run=False` once the user has
    confirmed the auditor is producing acceptable signal — for v0.2
    rollout the dispatcher invokes dry-run first and surfaces a card
    asking the user to enable wet-run autonomy.

    Per D-04, only Check 2 ever auto-disables. Checks 1 + 3 are
    recommend-only — they emit findings into the digest as amber cards.
    """
    rows = _load_rows(resolutions_path)
    diary = _load_diary(diary_path)

    findings: list[dict[str, Any]] = []
    findings.extend(check_reversal_rate(rows, now=now))
    findings.extend(check_downstream_errors(rows, diary, now=now))

    auto_disabled = check_validation_failures(
        rows, blocklist_path=blocklist_path, dry_run=dry_run, now=now,
    )

    return {
        "findings": findings,
        "auto_disabled": auto_disabled,
        "checks_run": ["reversal-rate", "validation-failure", "downstream-error"],
        "events_inspected": len(rows),
    }


if __name__ == "__main__":
    out = audit()
    print(json.dumps(out, indent=2, ensure_ascii=False))

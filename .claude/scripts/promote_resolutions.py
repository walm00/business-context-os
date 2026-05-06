"""
promote_resolutions.py — Compute the self-learning ladder from resolutions.jsonl.

Given the append-only event log written by record_resolution.py, derive
.claude/quality/ecosystem/learned-rules.json — the canonical list of
(finding_type, action_taken) pairs the user has implicitly endorsed often
enough that the cockpit can pre-select / auto-apply / fire silently.

Tier ladder (per implementation-plan.md):

    preselect  (P5)  N≥3  AND consistency=1.0
    auto-apply (P7)  N≥5  AND consistency≥0.9 AND calendar_span_days≥14
    silent     (P8)  N≥10 AND consistency≥0.95 AND auditor-clean 6+ weeks
                     AND explicit user opt-in per rule

This file ships only the preselect tier (P5_002). Auto-apply + silent
extend the same `compute_rules()` function in P7_002 / P8_002.

DERIVED-ARTIFACT INVARIANT (per L-ECOSYSTEM-20260501-013): learned-rules.json
must be **byte-stable regeneratable** from resolutions.jsonl + blocklist.
That means deterministic ordering, no timestamps that aren't present in the
source, no hash of "now". The wiring test in P5_007 calls regenerate twice
and asserts byte-equality.

Public API:

    compute_rules(*, resolutions_path=None, blocklist_path=None) -> list[dict]
    write_learned_rules(rules, path=None) -> None
    regenerate(*, resolutions_path=None, blocklist_path=None, output_path=None)

Used by:
- the architecture-review job (reads learned-rules.json to surface "rules
  learned this month" in monthly reports)
- the cockpit card renderer (reads learned-rules.json to add a "✨ suggested"
  badge on cards where the learned default applies)
- /learning forget (writes to learning-blocklist.json, then regenerates)
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
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
DEFAULT_BLOCKLIST = REPO_ROOT / ".claude" / "quality" / "ecosystem" / "learning-blocklist.json"
DEFAULT_LEARNED = REPO_ROOT / ".claude" / "quality" / "ecosystem" / "learned-rules.json"

SCHEMA_VERSION = "1.0.0"

# Tier thresholds.
PRESELECT_MIN_N = 3
PRESELECT_MIN_CONSISTENCY = 1.0

# Auto-apply tier (P7_002): higher bar, plus a calendar-span gate per
# R-04 (R-04 mitigation: 5 same-day clicks in a panic-cleanup session
# must not graduate to auto-apply).
AUTO_APPLY_MIN_N = 5
AUTO_APPLY_MIN_CONSISTENCY = 0.9
AUTO_APPLY_MIN_SPAN_DAYS = 14


def _rule_id(finding_type: str, action_taken: str) -> str:
    """Stable kebab-case rule ID. Used everywhere a rule is referenced —
    blocklist entries, /learning forget, audit-log lines, etc."""
    return f"{finding_type}::{action_taken}"


def _load_blocklist(path: Path | None) -> set[str]:
    p = path or DEFAULT_BLOCKLIST
    if not p.is_file():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return set(data.get("blocked") or [])


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


def _calendar_span_days(timestamps: list[str]) -> int:
    """Inclusive span between earliest and latest ts, in whole days."""
    if not timestamps:
        return 0
    parsed: list[datetime] = []
    for t in timestamps:
        try:
            parsed.append(datetime.fromisoformat(t.replace("Z", "+00:00")))
        except Exception:
            continue
    if not parsed:
        return 0
    return (max(parsed).date() - min(parsed).date()).days


def compute_rules(
    *,
    resolutions_path: Path | None = None,
    blocklist_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Derive learned rules from the event log.

    Excludes rows with `outcome == "reverted"` (explicit anti-signal).
    Groups by `finding_type` first to compute consistency, then by
    (finding_type, action_taken) for the per-rule N count.

    Returns rules sorted by rule_id for byte-stable output.
    """
    rows = _load_rows(resolutions_path)
    blocked = _load_blocklist(blocklist_path)

    # Filter signals: drop reverted events; keep applied/skipped/errored.
    # `errored` is rare but legitimate signal that the user TRIED the action.
    signal_rows = [r for r in rows if r.get("outcome") != "reverted"]

    # First pass: count actions per finding_type, to compute consistency.
    actions_per_finding: dict[str, Counter] = defaultdict(Counter)
    for r in signal_rows:
        ft = r.get("finding_type")
        at = r.get("action_taken")
        if not ft or not at:
            continue
        actions_per_finding[ft][at] += 1

    # Second pass: collect per-rule supporting evidence (timestamps, triggers).
    evidence: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in signal_rows:
        ft = r.get("finding_type")
        at = r.get("action_taken")
        if not ft or not at:
            continue
        evidence[(ft, at)].append(r)

    rules: list[dict[str, Any]] = []
    for (ft, at), rows_for_rule in evidence.items():
        rid = _rule_id(ft, at)
        if rid in blocked:
            continue

        n = len(rows_for_rule)
        ft_total = sum(actions_per_finding[ft].values())
        consistency = n / ft_total if ft_total else 0.0

        ts_list = sorted(r.get("ts", "") for r in rows_for_rule if r.get("ts"))
        span_days = _calendar_span_days(ts_list)
        triggers = Counter(r.get("trigger") for r in rows_for_rule if r.get("trigger"))

        # Pick the highest tier this rule qualifies for. A rule is in
        # exactly one tier — auto-apply outranks preselect when both
        # thresholds are met. Silent (P8) stacks on top of auto-apply.
        tier: str | None = None
        if (
            n >= AUTO_APPLY_MIN_N
            and consistency >= AUTO_APPLY_MIN_CONSISTENCY
            and span_days >= AUTO_APPLY_MIN_SPAN_DAYS
        ):
            tier = "auto-apply"
        elif n >= PRESELECT_MIN_N and consistency >= PRESELECT_MIN_CONSISTENCY:
            tier = "preselect"

        if tier is None:
            continue  # not eligible for any tier

        rules.append({
            "rule_id": rid,
            "finding_type": ft,
            "action_taken": at,
            "tier": tier,
            "n": n,
            "consistency": round(consistency, 4),
            "first_observed": ts_list[0] if ts_list else None,
            "last_observed": ts_list[-1] if ts_list else None,
            "calendar_span_days": span_days,
            "trigger_breakdown": dict(sorted(triggers.items())),
        })

    rules.sort(key=lambda r: r["rule_id"])
    return rules


def _derive_generated_at(rules: list[dict[str, Any]]) -> str:
    """Deterministic 'generated_at': latest last_observed across all rules,
    or the unix-epoch sentinel when there are no rules. This keeps the
    derived artifact byte-stable per L-ECOSYSTEM-20260501-013 — running
    the regen twice with no new events produces identical bytes."""
    if not rules:
        return "1970-01-01T00:00:00Z"
    return max((r.get("last_observed") or "") for r in rules) or "1970-01-01T00:00:00Z"


def write_learned_rules(rules: list[dict[str, Any]], path: Path | None = None) -> Path:
    """Write the derived artifact deterministically. Atomic via temp-file."""
    p = path or DEFAULT_LEARNED
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "generated_at": _derive_generated_at(rules),
        "rule_count": len(rules),
        "rules": rules,
    }
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    import os
    os.replace(tmp, p)
    return p


def regenerate(
    *,
    resolutions_path: Path | None = None,
    blocklist_path: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """End-to-end: read events + blocklist → compute rules → write artifact.

    The byte-stability invariant: calling regenerate() twice in a row with
    no new events produces a file whose bytes are identical between calls.
    Test coverage in P5_007.
    """
    rules = compute_rules(
        resolutions_path=resolutions_path,
        blocklist_path=blocklist_path,
    )
    return write_learned_rules(rules, output_path)


# ---------------------------------------------------------------------------
# /learning forget — adds a rule to the blocklist
# ---------------------------------------------------------------------------


def add_to_blocklist(rule_id: str, *, blocklist_path: Path | None = None) -> dict[str, Any]:
    """Append rule_id to learning-blocklist.json. Idempotent.

    Used by the `/learning forget <rule-id>` slash command (P5_006). Once a
    rule is blocked, subsequent regen calls drop it from learned-rules.json
    even if the supporting evidence is overwhelming.
    """
    p = blocklist_path or DEFAULT_BLOCKLIST
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {"blocked": []}
    else:
        data = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                "schema_version": SCHEMA_VERSION,
                "blocked": []}

    blocked = list(data.get("blocked") or [])
    if rule_id in blocked:
        return {"ok": True, "status": "already_blocked", "rule_id": rule_id, "count": len(blocked)}
    blocked.append(rule_id)
    blocked.sort()  # deterministic
    data["blocked"] = blocked
    data["schema_version"] = SCHEMA_VERSION

    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    import os
    os.replace(tmp, p)
    return {"ok": True, "status": "blocked", "rule_id": rule_id, "count": len(blocked)}


def remove_from_blocklist(rule_id: str, *, blocklist_path: Path | None = None) -> dict[str, Any]:
    """Reverse of add_to_blocklist. Used by /learning unblock."""
    p = blocklist_path or DEFAULT_BLOCKLIST
    if not p.is_file():
        return {"ok": True, "status": "not_blocked", "rule_id": rule_id}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"ok": False, "error": "blocklist unreadable"}
    blocked = [b for b in (data.get("blocked") or []) if b != rule_id]
    if len(blocked) == len(data.get("blocked") or []):
        return {"ok": True, "status": "not_blocked", "rule_id": rule_id}
    data["blocked"] = blocked
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    import os
    os.replace(tmp, p)
    return {"ok": True, "status": "removed", "rule_id": rule_id, "count": len(blocked)}


def is_blocked(rule_id: str, *, blocklist_path: Path | None = None) -> bool:
    return rule_id in _load_blocklist(blocklist_path)


def is_suggested(finding_type: str, action_taken: str, *, learned_path: Path | None = None) -> bool:
    """Quick lookup: does this (finding_type, action_taken) carry a learned default?

    The cockpit calls this per-card to decide whether to render the
    "✨ suggested" badge (P5_005). Reads learned-rules.json once and
    caches per-process — the file is small.
    """
    p = learned_path or DEFAULT_LEARNED
    if not p.is_file():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return False
    rid = _rule_id(finding_type, action_taken)
    return any(r.get("rule_id") == rid for r in (data.get("rules") or []))


if __name__ == "__main__":
    out = regenerate()
    print(f"wrote {out}")

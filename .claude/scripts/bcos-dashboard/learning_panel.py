"""
learning_panel.py — Cockpit + /settings/learning data source.

Reads `.claude/quality/ecosystem/learned-rules.json`,
`.claude/quality/ecosystem/learning-blocklist.json`, and a sliced view of
`resolutions.jsonl` (last 30 days, last 10 events per rule for the
evidence drill-down) and shapes them for the dashboard.

Five tier views (per implementation-plan.md P7_008):
- pending          — rules with N>=1 but below preselect threshold (≥3 + 1.0)
- preselect        — promoted to "✨ suggested" on cards
- auto-apply       — promoted to 10s-undo countdown
- silent           — P8 only; empty in v0.2
- auto-disabled    — entries in learning-blocklist.json

Used by:
- collect_learning_panel() — full payload for /settings/learning
- collect_learning_summary() — summary counts for the cockpit teaser
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from single_repo import REPO_ROOT  # noqa: E402

LEARNED_PATH = REPO_ROOT / ".claude" / "quality" / "ecosystem" / "learned-rules.json"
BLOCKLIST_PATH = REPO_ROOT / ".claude" / "quality" / "ecosystem" / "learning-blocklist.json"
RESOLUTIONS_PATH = REPO_ROOT / ".claude" / "quality" / "ecosystem" / "resolutions.jsonl"

# Cap evidence rows shown per rule on the panel — full log lives in
# resolutions.jsonl, the panel only surfaces recent context.
EVIDENCE_PER_RULE = 10


def _load_json(p: Path, default: Any) -> Any:
    if not p.is_file():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _load_resolutions() -> list[dict[str, Any]]:
    if not RESOLUTIONS_PATH.is_file():
        return []
    out: list[dict[str, Any]] = []
    with RESOLUTIONS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def _evidence_for_rule(rows: list[dict[str, Any]], finding_type: str, action_taken: str) -> list[dict[str, Any]]:
    """Most-recent EVIDENCE_PER_RULE events backing a rule."""
    matches = [
        r for r in rows
        if r.get("finding_type") == finding_type and r.get("action_taken") == action_taken
    ]
    matches.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return [
        {
            "ts": r.get("ts"),
            "outcome": r.get("outcome"),
            "trigger": r.get("trigger"),
            "action_target": r.get("action_target"),
            "user_specificity": r.get("user_specificity"),
            "validation": r.get("subsequent_validation_status"),
        }
        for r in matches[:EVIDENCE_PER_RULE]
    ]


def _pending_rules(rows: list[dict[str, Any]], promoted_ids: set[str], blocked_ids: set[str]) -> list[dict[str, Any]]:
    """Rules with N≥1 but below the preselect threshold — i.e., the user
    has clicked but the rule isn't yet promoted. Useful for transparency:
    "the system is watching this; one more click and it'll suggest it"."""
    counts: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"n": 0, "first": None, "last": None}
    )
    for r in rows:
        if r.get("outcome") == "reverted":
            continue
        ft = r.get("finding_type")
        at = r.get("action_taken")
        if not ft or not at:
            continue
        key = (ft, at)
        counts[key]["n"] += 1
        ts = r.get("ts") or ""
        if counts[key]["first"] is None or ts < counts[key]["first"]:
            counts[key]["first"] = ts
        if counts[key]["last"] is None or ts > counts[key]["last"]:
            counts[key]["last"] = ts

    pending = []
    for (ft, at), c in counts.items():
        rid = f"{ft}::{at}"
        if rid in promoted_ids or rid in blocked_ids:
            continue
        if c["n"] >= 3:
            # 3+ clicks but not promoted means consistency<1.0 (mixed actions
            # for the same finding_type); still surface it as "watching".
            pass
        pending.append({
            "rule_id": rid,
            "finding_type": ft,
            "action_taken": at,
            "n": c["n"],
            "first_observed": c["first"],
            "last_observed": c["last"],
            "tier": "pending",
        })
    pending.sort(key=lambda r: (-r["n"], r["rule_id"]))
    return pending[:25]  # cap


def collect_learning_panel() -> dict[str, Any]:
    """Full payload for the /settings/learning route."""
    learned = _load_json(LEARNED_PATH, {"rules": [], "rule_count": 0})
    blocklist = _load_json(BLOCKLIST_PATH, {"blocked": []})
    rows = _load_resolutions()

    rules = list(learned.get("rules") or [])
    promoted_ids = {r["rule_id"] for r in rules if "rule_id" in r}
    blocked_ids = set(blocklist.get("blocked") or [])

    # Decorate each promoted rule with its recent evidence.
    for r in rules:
        ft = r.get("finding_type")
        at = r.get("action_taken")
        if ft and at:
            r["evidence"] = _evidence_for_rule(rows, ft, at)

    by_tier: dict[str, list[dict[str, Any]]] = {
        "preselect": [r for r in rules if r.get("tier") == "preselect"],
        "auto-apply": [r for r in rules if r.get("tier") == "auto-apply"],
        "silent": [r for r in rules if r.get("tier") == "silent"],
    }

    pending = _pending_rules(rows, promoted_ids, blocked_ids)
    auto_disabled = [{"rule_id": rid} for rid in sorted(blocked_ids)]

    counts = {
        "events_total": len(rows),
        "rules_promoted": len(rules),
        "rules_pending": len(pending),
        "rules_blocked": len(blocked_ids),
        "by_trigger": dict(Counter(
            r.get("trigger") for r in rows if r.get("trigger")
        )),
    }

    return {
        "kind": "learning_panel",
        "title": "Self-learning",
        "schema_version": learned.get("schema_version"),
        "generated_at": learned.get("generated_at"),
        "counts": counts,
        "tiers": {
            "pending": pending,
            "preselect": by_tier["preselect"],
            "auto-apply": by_tier["auto-apply"],
            "silent": by_tier["silent"],
            "auto-disabled": auto_disabled,
        },
        "_severity": "ok",
    }


def collect_learning_summary() -> dict[str, Any]:
    """Compact summary for the cockpit (count badges only)."""
    full = collect_learning_panel()
    return {
        "kind": "learning_summary",
        "events_total": full["counts"]["events_total"],
        "rules_promoted": full["counts"]["rules_promoted"],
        "rules_pending": full["counts"]["rules_pending"],
        "rules_blocked": full["counts"]["rules_blocked"],
        "_severity": "ok",
    }

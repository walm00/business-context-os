"""
cockpit.py — Convert a ParsedSidecar into a CockpitView the dashboard renders.

The contract this module satisfies is pinned by `.claude/scripts/test_card_shape.py`
(P2_001-3). The dashboard front-end (dashboard.js / dashboard.html) consumes
the shapes defined here verbatim; the test guarantees that:

- green view: single-line headline, no per-job notes echoed, no cards
- amber view: cards with title ≤6 words, body ≤2 lines ≤80 chars/line, full
  action-slot set (primary required; secondary/tertiary/dismiss present)
- red view: takeover flag set; auto-commit blocked when block_on_red is true

A per-finding-type renderer registry keeps card prose short and
typed-event-aware. Adding a new finding_type to typed-events.md without
a renderer here drops to a generic fallback (still shape-compliant). The
P2_010 wiring test asserts that every finding_type in any fixture renders
into a card.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
for p in (str(_HERE), str(_SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

from labels import finding_type_display, job_display  # noqa: E402

# Promotion ladder lookup (P5_005). Lazy-imported so cockpit stays usable
# in environments where promote_resolutions.py hasn't shipped yet (early
# rollout, fixture-only test runs). Lookup is cheap; we read the file
# fresh per call and let the OS page-cache it. If the file is missing,
# is_suggested() returns False and no badge renders.
try:
    from promote_resolutions import is_suggested as _is_suggested  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    def _is_suggested(finding_type: str, action_taken: str) -> bool:  # type: ignore[misc]
        return False


@dataclass
class Card:
    finding_type: str
    title: str  # ≤6 words
    body: str   # ≤2 lines, ≤80 chars/line
    verdict: str
    emitted_by: str
    actions: dict[str, Any] = field(default_factory=dict)  # primary/secondary/tertiary/dismiss
    finding_attrs: dict[str, Any] = field(default_factory=dict)
    suggested_action: str | None = None  # P5_005: action_id with "✨ suggested" badge


@dataclass
class CockpitView:
    verdict: str
    headline: str
    takeover: bool = False  # red view full-screen blocker
    cards: list[Card] = field(default_factory=list)
    auto_commit_blocked: bool = False
    auto_commit_reason: str | None = None
    per_job_notes_echoed: bool = False  # always False — we hide them


# ---------------------------------------------------------------------------
# Per-finding-type renderers
# ---------------------------------------------------------------------------
#
# Each renderer is `(finding_attrs) -> (title, body, suggested_actions)`. Actions
# are action-id strings from headless-actions.md (P3); the cockpit lifts them
# into the action slots downstream. Title and body must respect the shape
# budget (≤6-word title, ≤2 lines ≤80 chars body).

_Renderer = Callable[[dict[str, Any]], tuple[str, str, list[str]]]


def _truncate(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _path_only(p: str | None) -> str:
    """Show last 2 path segments at most (avoids over-long card bodies)."""
    if not p:
        return ""
    parts = p.replace("\\", "/").rstrip("/").split("/")
    return "/".join(parts[-2:]) if len(parts) > 2 else p


def _r_inbox_aged(a):
    title = "Inbox item past triage"
    body = f"{_path_only(a.get('file'))} — {a.get('age_days', '?')} days old"
    return title, _truncate(body, 80), ["triage", "archive", "snooze-7d"]


def _r_refresh_due(a):
    title = "Source summary refresh due"
    body = f"{_path_only(a.get('wiki_file') or a.get('file'))} — {a.get('age_days') or a.get('days_overdue', '?')} days overdue"
    return title, _truncate(body, 80), ["refresh-now", "snooze-7d"]


def _r_stale_propagation(a):
    title = "Wiki out of sync"
    body = f"{_path_only(a.get('wiki_file') or a.get('file'))} — {a.get('stale_builds_on_count', '?')} stale links"
    return title, _truncate(body, 80), ["mark-reviewed", "open-for-edit"]


def _r_broken_xref(a):
    title = "Broken cross-reference"
    body = f"{_path_only(a.get('file'))} → {_path_only(a.get('target') or a.get('broken_link'))}"
    return title, _truncate(body, 80), ["relink", "remove-reference"]


def _r_orphan_pages(a):
    title = "Orphan wiki page"
    body = f"{_path_only(a.get('wiki_file') or a.get('file'))} — no inbound links"
    return title, _truncate(body, 80), ["archive", "attach-anchor"]


def _r_graveyard_stale(a):
    title = "Archived item past graveyard"
    body = f"{_path_only(a.get('file'))} — {a.get('age_days', '?')}d > {a.get('threshold_days', 365)}d"
    return title, _truncate(body, 80), ["move-to-private", "delete"]


def _r_coverage_gap(a):
    title = "Data point lacks explainer"
    dp = a.get("data_point") or _path_only(a.get("data_point_file") or a.get("owner_doc"))
    body = f"{dp} — no wiki page"
    return title, _truncate(body, 80), ["stub-wiki-page", "mark-non-explainable"]


def _r_frequency_suggestion(a):
    title = "Job cadence suggestion"
    body = f"{a.get('job', '?')}: {a.get('current_schedule', '—')} → {a.get('suggested_schedule', '—')}"
    return title, _truncate(body, 80), ["apply-suggestion", "dismiss"]


def _r_rule_reversal_spike(a):
    rid = a.get("rule_id", "?")
    n_rev = a.get("n_reverted", "?")
    n_app = a.get("n_applied", "?")
    rate_pct = int(round(float(a.get("reversal_rate", 0)) * 100))
    title = "Rule reversal rate high"  # 4 words
    body = f"{rid} — {n_rev}/{n_app} reverted ({rate_pct}%)"
    return title, _truncate(body, 80), ["demote-rule", "show-evidence", "keep-silent"]


def _r_rule_downstream_error(a):
    rid = a.get("rule_id", "?")
    job = a.get("downstream_job", "?")
    before = a.get("verdict_before", "?")
    after = a.get("verdict_after", "?")
    title = "Fix may have caused error"  # 5 words
    body = f"{rid} → {job} flipped {before} → {after}"
    return title, _truncate(body, 80), ["show-evidence", "investigate", "dismiss"]


def _r_generic(a):
    """Fallback for any finding_type without a dedicated renderer."""
    file_hint = _path_only(a.get("file") or a.get("wiki_file") or a.get("data_point_file") or "")
    title = "Action needed"  # 2 words, deliberately generic
    body = file_hint or "See digest for details"
    return title, _truncate(body, 80), ["open-for-edit", "dismiss"]


_RENDERERS: dict[str, _Renderer] = {
    "inbox-aged": _r_inbox_aged,
    "refresh-due": _r_refresh_due,
    "source-summary-upstream-changed": _r_refresh_due,
    "stale-propagation": _r_stale_propagation,
    "broken-xref": _r_broken_xref,
    "broken-xref-single-candidate": _r_broken_xref,
    "xref-broken-ecosystem": _r_broken_xref,
    "orphan-pages": _r_orphan_pages,
    "graveyard-stale": _r_graveyard_stale,
    "coverage-gap-data-point": _r_coverage_gap,
    "coverage-gap-inbox-term": _r_coverage_gap,
    "frequency-suggestion": _r_frequency_suggestion,
    "rule-reversal-spike": _r_rule_reversal_spike,
    "rule-downstream-error": _r_rule_downstream_error,
}


def _render_finding_to_card(finding) -> Card:
    """Convert a typed-event Finding into a Card."""
    attrs = dict(finding.finding_attrs or {})
    renderer = _RENDERERS.get(finding.finding_type, _r_generic)
    title, body, suggested = renderer(attrs)

    primary = suggested[0] if suggested else None
    secondary = suggested[1] if len(suggested) > 1 else None
    tertiary = suggested[2] if len(suggested) > 2 else None

    # P5_005: stamp the "✨ suggested" badge when the user has consistently
    # picked an action for this finding_type (preselect tier, learned-rules.json).
    # We probe each suggested action in priority order; the first one that
    # carries a learned default wins. Renders as a small badge in the UI but
    # also pre-fills which action is the cockpit's default keystroke target.
    suggested_action = None
    for candidate in suggested:
        try:
            if _is_suggested(finding.finding_type, candidate):
                suggested_action = candidate
                break
        except Exception:  # noqa: BLE001
            break  # treat lookup failure as "no learned default"

    return Card(
        finding_type=finding.finding_type,
        title=title,
        body=body,
        verdict=finding.verdict,
        emitted_by=finding.emitted_by,
        finding_attrs=attrs,
        actions={
            "primary": primary,
            "secondary": secondary,
            "tertiary": tertiary,
            "dismiss": "dismiss",  # always available
        },
        suggested_action=suggested_action,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def should_block_auto_commit(verdict: str, block_on_red: bool) -> bool:
    """Encode the Step 7b gate: skip auto-commit on red when flag is true."""
    return bool(verdict == "red" and block_on_red)


def render_cockpit(sidecar, *, block_on_red: bool = True) -> CockpitView:
    """Render a ParsedSidecar into the cockpit-shape the dashboard consumes.

    `sidecar` is a `digest_sidecar.ParsedSidecar`. `block_on_red` mirrors
    the schedule-config flag; defaults to true to match the template
    default (see schedule-config.template.json).
    """
    if sidecar is None:
        return CockpitView(verdict="green", headline="No digest available.")

    verdict = sidecar.overall_verdict
    findings_count = len(sidecar.findings)
    auto_fixed_count = len(sidecar.auto_fixed)
    jobs_count = len(sidecar.jobs)

    if verdict == "green":
        headline = f"All clear — {jobs_count} jobs ran, {auto_fixed_count} auto-fixes."
        return CockpitView(
            verdict="green",
            headline=headline,
            cards=[],
            per_job_notes_echoed=False,
        )

    cards = [_render_finding_to_card(f) for f in sidecar.findings]
    blocked = should_block_auto_commit(verdict, block_on_red)
    reason = (
        f"Auto-commit paused — {findings_count} critical finding"
        f"{'s' if findings_count != 1 else ''} need attention"
        if blocked
        else None
    )

    if verdict == "red":
        headline = f"{findings_count} critical findings need attention"
        return CockpitView(
            verdict="red",
            headline=headline,
            takeover=True,
            cards=cards,
            auto_commit_blocked=blocked,
            auto_commit_reason=reason,
        )

    # amber
    headline = f"{findings_count} item{'s' if findings_count != 1 else ''} need attention"
    return CockpitView(
        verdict="amber",
        headline=headline,
        takeover=False,
        cards=cards,
        auto_commit_blocked=blocked,
        auto_commit_reason=reason,
    )


def supported_finding_types() -> set[str]:
    """Set of finding_type IDs with a dedicated renderer (excludes fallback)."""
    return set(_RENDERERS.keys())

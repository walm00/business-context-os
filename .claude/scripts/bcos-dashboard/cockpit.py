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
    # Added in 1.1.0 — drives category-aware rendering + stuck-badge UX.
    category: str = "repo-context"           # repo-context | bcos-framework
    consecutive_runs: int = 1                # for stuck-badge display
    stuck: bool = False                      # True when consecutive_runs >= 3 OR severity_override == "stuck"
    first_seen: str | None = None            # ISO YYYY-MM-DD; shown on stuck cards
    footer_note: str | None = None           # acknowledge-only banner text for framework cards


@dataclass
class CockpitView:
    verdict: str
    headline: str
    takeover: bool = False  # red view full-screen blocker
    cards: list[Card] = field(default_factory=list)
    auto_commit_blocked: bool = False
    auto_commit_reason: str | None = None
    per_job_notes_echoed: bool = False  # always False — we hide them
    # Added in 1.1.0 — split counts for verdict-bar rendering.
    repo_findings_count: int = 0
    framework_findings_count: int = 0
    stuck_findings_count: int = 0


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


# ---------------------------------------------------------------------------
# Framework renderers (1.1.0 — category=bcos-framework, acknowledge-only)
# ---------------------------------------------------------------------------
#
# These render the 7 bcos-framework finding_types. They MUST return
# ["acknowledge"] as the only suggested action — the dashboard never gives
# the user a Fix button for framework findings (patching them in a client
# repo would be overwritten by the next `update.py` run). Body prose names
# the offending artifact so the framework owner has enough context to fix
# upstream without opening the sidecar.

def _r_dispatcher_silent_skip(a):
    title = "Job silent-skip detected"
    body = f"{a.get('job', '?')} — no diary entry since {a.get('last_diary_ts') or 'never'}"
    return title, _truncate(body, 80), ["acknowledge"]


def _r_job_reference_missing(a):
    title = "Job reference file missing"
    body = f"{a.get('job', '?')} → {_path_only(a.get('expected_path', '?'))}"
    return title, _truncate(body, 80), ["acknowledge"]


def _r_schema_validation_failed(a):
    title = "Typed-event contract violated"
    body = f"{a.get('offending_finding_type', '?')} — {a.get('validation_error', 'shape mismatch')}"
    return title, _truncate(body, 80), ["acknowledge"]


def _r_auto_fix_handler_threw(a):
    title = "Auto-fix handler crashed"
    body = f"{a.get('fix_id', '?')} on {_path_only(a.get('target'))} — {a.get('exception_class', 'Exception')}"
    return title, _truncate(body, 80), ["acknowledge"]


def _r_installer_seed_missing(a):
    title = "Framework file not installed"
    body = f"{_path_only(a.get('expected_path', '?'))} — run update.py to re-seed"
    return title, _truncate(body, 80), ["acknowledge"]


def _r_data_corruption_detected(a):
    title = "JSONL silent data drop"
    body = f"{_path_only(a.get('file'))} — {a.get('dropped_line_count', '?')}/{a.get('total_lines', '?')} lines unreadable"
    return title, _truncate(body, 80), ["acknowledge"]


def _r_framework_config_malformed(a):
    title = "Framework config malformed"
    err = a.get("parse_error") or (
        "missing: " + ", ".join(a.get("missing_fields") or []) if a.get("missing_fields") else "shape error"
    )
    body = f"{_path_only(a.get('file', '?'))} — {err}"
    return title, _truncate(body, 80), ["acknowledge"]


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
    # 1.1.0 — framework category (acknowledge-only)
    "dispatcher-silent-skip": _r_dispatcher_silent_skip,
    "job-reference-missing": _r_job_reference_missing,
    "schema-validation-failed": _r_schema_validation_failed,
    "auto-fix-handler-threw": _r_auto_fix_handler_threw,
    "installer-seed-missing": _r_installer_seed_missing,
    "data-corruption-detected": _r_data_corruption_detected,
    "framework-config-malformed": _r_framework_config_malformed,
}


# Standard footer note shown on every framework card. Inline here so the
# wording is consistent across all 7 finding_types — the L-DASHBOARD-
# 20260425-010 single-translation-map principle applied to card footers.
_FRAMEWORK_FOOTER = "Reported to BCOS — will be fixed in next release."


def _render_finding_to_card(finding) -> Card:
    """Convert a typed-event Finding into a Card.

    1.1.0 — branches on `finding.category`:
    - `repo-context` (default): existing Fix/Snooze/Dismiss action slots
    - `bcos-framework`: acknowledge-only card with the standard framework
      footer; Fix slot is forcibly absent. Patching framework state in a
      client repo would be overwritten by the next `update.py`.
    """
    attrs = dict(finding.finding_attrs or {})
    # Category may be absent on a 1.0.0 sidecar — Finding's dataclass
    # default ("repo-context") covers that path.
    category = getattr(finding, "category", "repo-context")
    renderer = _RENDERERS.get(finding.finding_type, _r_generic)
    title, body, suggested = renderer(attrs)

    if category == "bcos-framework":
        # Force the action set to acknowledge-only regardless of what the
        # renderer proposed. _h_acknowledge is the only handler permitted.
        actions = {
            "primary": "acknowledge",
            "secondary": None,
            "tertiary": None,
            "dismiss": "dismiss",
        }
        suggested_action = None  # no learned-default for framework cards
        footer_note: str | None = _FRAMEWORK_FOOTER
    else:
        primary = suggested[0] if suggested else None
        secondary = suggested[1] if len(suggested) > 1 else None
        tertiary = suggested[2] if len(suggested) > 2 else None

        # P5_005: stamp the "✨ suggested" badge when the user has consistently
        # picked an action for this finding_type (preselect tier, learned-rules.json).
        suggested_action = None
        for candidate in suggested:
            try:
                if _is_suggested(finding.finding_type, candidate):
                    suggested_action = candidate
                    break
            except Exception:  # noqa: BLE001
                break  # treat lookup failure as "no learned default"

        actions = {
            "primary": primary,
            "secondary": secondary,
            "tertiary": tertiary,
            "dismiss": "dismiss",
        }
        footer_note = None

    consecutive_runs = int(getattr(finding, "consecutive_runs", 1) or 1)
    severity_override = getattr(finding, "severity_override", None)
    stuck = severity_override == "stuck" or consecutive_runs >= 3

    return Card(
        finding_type=finding.finding_type,
        title=title,
        body=body,
        verdict=finding.verdict,
        emitted_by=finding.emitted_by,
        finding_attrs=attrs,
        actions=actions,
        suggested_action=suggested_action,
        category=category,
        consecutive_runs=consecutive_runs,
        stuck=stuck,
        first_seen=getattr(finding, "first_seen", None),
        footer_note=footer_note,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def should_block_auto_commit(verdict: str, block_on_red: bool) -> bool:
    """Encode the Step 7b gate: skip auto-commit on red when flag is true."""
    return bool(verdict == "red" and block_on_red)


def _card_sort_key(card: Card) -> tuple[int, int, int]:
    """Pinning order for the cockpit card list:
    1) framework category first (acknowledge-only, but high-trust signal — Guntis owns these)
    2) stuck cards above non-stuck within the same category
    3) red > amber > green within each (stuck, category) bucket
    """
    cat_rank = 0 if card.category == "bcos-framework" else 1
    stuck_rank = 0 if card.stuck else 1
    verdict_rank = {"red": 0, "amber": 1, "green": 2}.get(card.verdict, 3)
    return (cat_rank, stuck_rank, verdict_rank)


def render_cockpit(sidecar, *, block_on_red: bool = True) -> CockpitView:
    """Render a ParsedSidecar into the cockpit-shape the dashboard consumes.

    `sidecar` is a `digest_sidecar.ParsedSidecar`. `block_on_red` mirrors
    the schedule-config flag; defaults to true to match the template
    default (see schedule-config.template.json).

    1.1.0 — split count fields (`repo_findings_count`, `framework_findings_count`,
    `stuck_findings_count`) drive the verdict-bar's "N repo · M framework"
    split rendering in the front-end. Sidecar's pre-computed `headline` is
    preferred over the cockpit's fallback synthesis when present.
    """
    if sidecar is None:
        return CockpitView(verdict="green", headline="No digest available.")

    verdict = sidecar.overall_verdict
    auto_fixed_count = len(sidecar.auto_fixed)
    jobs_count = len(sidecar.jobs)

    repo_count = sum(
        1 for f in sidecar.findings
        if getattr(f, "category", "repo-context") == "repo-context"
    )
    framework_count = sum(
        1 for f in sidecar.findings
        if getattr(f, "category", "repo-context") == "bcos-framework"
    )
    stuck_count = sum(
        1 for f in sidecar.findings
        if getattr(f, "severity_override", None) == "stuck"
        or int(getattr(f, "consecutive_runs", 1) or 1) >= 3
    )
    findings_count = repo_count + framework_count

    # Sidecar-supplied headline always wins. Fallback synthesis only when
    # absent (older 1.0.0 sidecar — pre-Step-4c dispatcher).
    sidecar_headline = getattr(sidecar, "headline", None)

    if verdict == "green" and findings_count == 0:
        headline = sidecar_headline or (
            f"All clear — {jobs_count} jobs ran, {auto_fixed_count} auto-fixes."
        )
        return CockpitView(
            verdict="green",
            headline=headline,
            cards=[],
            per_job_notes_echoed=False,
            repo_findings_count=0,
            framework_findings_count=0,
            stuck_findings_count=0,
        )

    cards = sorted(
        (_render_finding_to_card(f) for f in sidecar.findings),
        key=_card_sort_key,
    )
    blocked = should_block_auto_commit(verdict, block_on_red)
    reason = (
        f"Auto-commit paused — {findings_count} critical finding"
        f"{'s' if findings_count != 1 else ''} need attention"
        if blocked
        else None
    )

    if verdict == "red":
        fallback = f"{findings_count} critical findings need attention"
        return CockpitView(
            verdict="red",
            headline=sidecar_headline or fallback,
            takeover=True,
            cards=cards,
            auto_commit_blocked=blocked,
            auto_commit_reason=reason,
            repo_findings_count=repo_count,
            framework_findings_count=framework_count,
            stuck_findings_count=stuck_count,
        )

    # amber. Headline preference: sidecar > stuck-aware > generic.
    if sidecar_headline:
        headline = sidecar_headline
    elif stuck_count > 0:
        headline = (
            f"{stuck_count} stuck — won't resolve on its own."
        )
    else:
        headline = f"{findings_count} item{'s' if findings_count != 1 else ''} need attention"

    return CockpitView(
        verdict="amber",
        headline=headline,
        takeover=False,
        cards=cards,
        auto_commit_blocked=blocked,
        auto_commit_reason=reason,
        repo_findings_count=repo_count,
        framework_findings_count=framework_count,
        stuck_findings_count=stuck_count,
    )


def supported_finding_types() -> set[str]:
    """Set of finding_type IDs with a dedicated renderer (excludes fallback)."""
    return set(_RENDERERS.keys())

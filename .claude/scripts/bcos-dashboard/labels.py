"""
labels.py — Canonical technical-to-human translation map.

Single source of truth for every user-facing string derived from an
internal identifier, verdict enum, schedule shorthand, issue code, or
timestamp. The rest of the dashboard should never render a raw field
name or enum — it goes through one of the helpers here first.

Why this file exists: internal identifiers (`index-health`,
`daydream-lessons`, `mon,wed,fri`, `green`, `amber`, `missing_frontmatter`)
are stable, kebab-case, and appropriate for config files, diary entries,
and cross-tool contracts. They are *not* appropriate in a UI for a
knowledge-worker audience. Collectors attach a `display_*` counterpart
to every such value, and the client renders the human label.

The raw value is always kept alongside the human one so Tier-3
(settings / advanced) views can surface the technical ID on demand.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


# ---------------------------------------------------------------------------
# Job identity
# ---------------------------------------------------------------------------

# (label, short explanation shown in drawer / tooltip)
JOB_LABELS: dict[str, tuple[str, str]] = {
    # Core BCOS maintenance jobs
    "index-health":        ("Documentation check",  "Daily scan of your docs structure, metadata, and references."),
    "audit-inbox":         ("Weekly review",        "Looks at what's piled up in your inbox and what's gone stale."),
    "daydream-lessons":    ("Weekly reflection",    "Surfaces patterns and lessons emerging in your context."),
    "daydream-deep":       ("Deep reflection",      "One architectural recommendation when something feels off."),
    "architecture-review": ("Monthly review",       "Full health score and top priorities across your context."),
    # Wiki zone maintenance jobs
    "wiki-stale-propagation": (
        "Wiki staleness",
        "Flags wiki pages whose source data points have moved on since last review.",
    ),
    "wiki-source-refresh": (
        "Wiki source refresh",
        "Two-tier upstream check: HEAD/ETag quick-check + full re-fetch when sources drift.",
    ),
    "wiki-graveyard": (
        "Wiki graveyard",
        "Surfaces wiki pages that no other content references — candidates for archive.",
    ),
    "wiki-coverage-audit": (
        "Wiki coverage audit",
        "Quarterly scan for gaps where active data points lack a wiki explainer.",
    ),
    "auto-fix-audit": (
        "Self-learning audit",
        "Friday safety brake: surfaces learned rules whose reversal rate has spiked.",
    ),
    "lifecycle-sweep": (
        "Lifecycle sweep",
        "Classifies active-zone docs against lifecycle-routing rules; surfaces archive / wiki / fold-into candidates.",
    ),
    # Umbrella / portfolio jobs — in case they surface via diary:
    "portfolio-index-health":     ("Portfolio index",    "Rebuilds the cross-repo index for a multi-project setup."),
    "portfolio-brief":            ("Portfolio brief",    "Synthesizes a CEO-level summary across all projects."),
    "portfolio-wakeup-refresh":   ("Wake-up snapshot",   "Refreshes the session-start context snapshot."),
    "command-center-schedules-snapshot": (
        "Schedule sync",
        "Caches scheduled-task state so the dashboard can show next / last run.",
    ),
    "usage-telemetry-digest":     ("Usage summary",       "Weekly Claude token and cost summary."),
    "repo-clear-audit":           ("Cross-repo audit",    "Surfaces ownership violations across a portfolio."),
}


def job_display(job_id: str) -> tuple[str, str]:
    """Return (label, hint) for a job id. Falls back to title-casing the id."""
    if job_id in JOB_LABELS:
        return JOB_LABELS[job_id]
    fallback = job_id.replace("-", " ").replace("_", " ").strip().capitalize()
    return fallback, ""


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

VERDICT_LABELS: dict[str, str] = {
    "green":  "Healthy",
    "amber":  "Needs attention",
    "red":    "Action required",
    "error":  "Failed to run",
}
# Single-char glyphs for space-constrained contexts (sparklines, dots).
VERDICT_DOT: dict[str, str] = {
    "green":  "●",
    "amber":  "◐",
    "red":    "✕",
    "error":  "⚠",
}


def verdict_display(verdict: str | None) -> str:
    return VERDICT_LABELS.get(verdict or "", "Not yet run")


def verdict_dot(verdict: str | None) -> str:
    return VERDICT_DOT.get(verdict or "", "○")


# ---------------------------------------------------------------------------
# Schedule shorthand  → sentence-case phrase
# ---------------------------------------------------------------------------

_WEEKDAY_FULL = {
    "mon": "Mondays",  "tue": "Tuesdays",  "wed": "Wednesdays",
    "thu": "Thursdays","fri": "Fridays",   "sat": "Saturdays", "sun": "Sundays",
}
_WEEKDAY_SHORT = {
    "mon": "Mon", "tue": "Tue", "wed": "Wed",
    "thu": "Thu", "fri": "Fri", "sat": "Sat", "sun": "Sun",
}


def schedule_display(raw: str | None, *, short: bool = False) -> str:
    """Convert a raw schedule string into a sentence-case phrase.

    Short form ("Mon · Wed · Fri") for chip-constrained spaces; long
    form ("Every Monday, Wednesday, and Friday") for drawer / tooltip.
    """
    s = (raw or "").strip().lower()
    if not s or s == "—":
        return "—"
    if s == "daily":
        return "Every weekday"
    if s == "1st":
        return "Monthly"
    if s == "off":
        return "Paused"
    if "," in s:
        days = [d.strip() for d in s.split(",") if d.strip()]
        if short:
            return " · ".join(_WEEKDAY_SHORT.get(d, d.title()) for d in days)
        pretty = [_WEEKDAY_FULL.get(d, d.title()) for d in days]
        if len(pretty) == 2:
            return f"{pretty[0]} and {pretty[1]}"
        return ", ".join(pretty[:-1]) + f", and {pretty[-1]}"
    if s in _WEEKDAY_FULL:
        return _WEEKDAY_FULL[s] if not short else _WEEKDAY_SHORT[s]
    return s.replace("-", " ").title()


# ---------------------------------------------------------------------------
# Status (of a job in config)
# ---------------------------------------------------------------------------

STATUS_LABELS: dict[str, str] = {
    "configured": "Active",
    "disabled":   "Paused",
    "unknown":    "Not enabled",
}
STATUS_DETAIL_LABELS: dict[str, str] = {
    "never run": "Not yet run",
}


def status_display(status: str | None, detail: str | None = None) -> str:
    if detail and detail in STATUS_DETAIL_LABELS:
        return STATUS_DETAIL_LABELS[detail]
    if detail:
        return detail.capitalize()
    return STATUS_LABELS.get(status or "", status or "—")


# ---------------------------------------------------------------------------
# File-health issue codes
# ---------------------------------------------------------------------------

ISSUE_LABELS: dict[str, str] = {
    "missing_frontmatter":  "Missing metadata",
    "missing_field":        "Incomplete metadata",
    "invalid_type":         "Unrecognized document type",
    "missing_last_updated": "Missing last-updated date",
    "stale":                "Hasn't been updated recently",
    "eof_newline":          "Formatting nit (missing newline)",
    "trailing_ws":          "Formatting nit (extra spaces)",
}


def issue_display(code: str | None) -> str:
    return ISSUE_LABELS.get(code or "", (code or "").replace("_", " ").capitalize())


# ---------------------------------------------------------------------------
# Fix buttons
# ---------------------------------------------------------------------------

FIX_LABELS: dict[str, str] = {
    "eof-newline":           "Auto-fix",
    "trailing-whitespace":   "Auto-fix",
    "missing-last-updated":  "Set today's date",
    "frontmatter-field-order": "Tidy metadata",
    "broken-xref-single-candidate": "Apply suggested link",
}


def fix_display(fix_id: str | None) -> str:
    return FIX_LABELS.get(fix_id or "", "Apply fix")


# ---------------------------------------------------------------------------
# Finding types (typed-event sidecar IDs from typed-events.md)
# ---------------------------------------------------------------------------
#
# Single translation map per L-DASHBOARD-20260425-010: collectors emit raw
# kebab-case IDs (the same strings recorded in resolutions.jsonl), renderers
# prefer the human-friendly display form, and Tier-3 settings views can
# surface the technical ID on demand.
#
# Coverage is enforced by .claude/scripts/test_finding_type_coverage.py:
# every finding_type declared in any job-*.md `emits-finding-types` block
# must have an entry here. Adding a new finding_type without a label
# fails the wiring test.

FINDING_TYPE_LABELS: dict[str, str] = {
    # audit-inbox (8)
    "missing-frontmatter":       "Missing metadata",
    "boundary-violation":        "Boundary crossed",
    "broken-xref":               "Broken cross-reference",
    "stale-marker":              "Stale TODO/FIXME marker",
    "duplication-obvious":       "Duplicate heading across docs",
    "inbox-aged":                "Inbox item past triage threshold",
    "lesson-overlap-proposal":   "Overlapping lessons",
    "lesson-orphaned":           "Lesson references missing concept",
    # index-health (8 — 2 shared with audit-inbox)
    "missing-required-field":      "Frontmatter missing required field",
    "missing-last-updated":        "Missing last-updated date",
    "frontmatter-field-order":     "Frontmatter field order off",
    "broken-xref-single-candidate":"Broken xref with single candidate",
    "trailing-whitespace":         "Trailing whitespace",
    "eof-newline":                 "Missing end-of-file newline",
    # architecture-review (6)
    "integration-coverage-gap":    "Skill/agent/hook not wired in",
    "xref-broken-ecosystem":       "Ecosystem cross-reference broken",
    "lesson-retirement-candidate": "Lesson candidate for retirement",
    "lesson-sharp-still":          "Lesson still actively violated",
    "lesson-merge-candidate":      "Lessons candidate for merge",
    "lessons-count-high":          "lessons.json over consolidation threshold",
    # daydream-deep (6)
    "architecture-misalignment":   "Two docs claim same topic",
    "datapoint-should-split":      "Data point grew beyond single ownership",
    "datapoint-should-merge":      "Data points heavily overlap",
    "datapoint-should-retire":     "Data point no longer reflects reality",
    "datapoint-missing":           "Knowledge missing from structured docs",
    "cluster-needs-restructuring": "Cluster shape no longer fits",
    # daydream-lessons (3)
    "daydream-observation":        "Reflection-surfaced drift",
    "lesson-duplicate-candidate":  "New lesson overlaps existing",
    "lesson-new-capture":          "New lesson surfaced",
    # wiki-coverage-audit (3)
    "coverage-gap-data-point":     "Data point lacks wiki explainer",
    "coverage-gap-inbox-term":     "Inbox term lacks wiki page",
    "cluster-mismatch":            "Wiki cluster value not in index",
    # wiki-graveyard (3)
    "graveyard-stale":             "Wiki page past graveyard threshold",
    "orphan-pages":                "Wiki page with no inbound links",
    "retired-page-type":           "Wiki page-type retired in schema",
    # wiki-source-refresh (2)
    "source-summary-upstream-changed": "Source summary upstream changed",
    "refresh-due":                     "Source summary refresh due",
    # wiki-stale-propagation (1)
    "stale-propagation":          "Wiki page out of sync with source",
    # dispatcher meta (1)
    "frequency-suggestion":       "Job cadence suggestion",
    # auto-fix-audit (2)
    "rule-reversal-spike":        "Rule reversal rate spike",
    "rule-downstream-error":      "Fix batch preceded downstream error",
    # lifecycle-sweep (4)
    "lifecycle-trigger-fired":           "Lifecycle trigger ready to route",
    "lifecycle-body-marker-confirmed":   "Body marker confirms lifecycle route",
    "lifecycle-route-ambiguous":         "Lifecycle routing needs your call",
    "lifecycle-orphan-active":           "Active doc with no lifecycle field",
    # wiki-canonical-drift (4 — schema 1.2 Class D)
    "wiki-canonical-drift-suggestion":         "Wiki diverges from canonical source",
    "wiki-true-contradiction":                 "Wiki contradicts canonical source",
    "wiki-authority-asymmetry":                "Wiki claims authority over canonical",
    "wiki-temporal-supersession-candidate":    "Wiki page supersedes canonical version",
}


def finding_type_display(finding_type: str | None) -> str:
    """Return the human-friendly label for a typed-event finding_type ID.

    Falls back to a title-cased rendering of the ID so an unmapped emitter
    still produces something sensible while the wiring test flags it.
    """
    if not finding_type:
        return "—"
    if finding_type in FINDING_TYPE_LABELS:
        return FINDING_TYPE_LABELS[finding_type]
    return finding_type.replace("-", " ").replace("_", " ").capitalize()


def decorate_finding(finding: dict) -> dict:
    """Add display_* fields to a typed-event Finding dict."""
    ft = finding.get("finding_type")
    finding["display_finding_type"] = finding_type_display(ft)
    finding["display_verdict"] = verdict_display(finding.get("verdict"))
    finding["display_dot"] = verdict_dot(finding.get("verdict"))
    if "emitted_by" in finding:
        finding["display_emitted_by"] = job_display(finding["emitted_by"])[0]
    return finding


# ---------------------------------------------------------------------------
# Trigger (scheduled vs manual)
# ---------------------------------------------------------------------------

TRIGGER_LABELS: dict[str, str] = {
    "scheduled": "Automatic",
    "on-demand": "Manual",
}


def trigger_display(trigger: str | None) -> str:
    return TRIGGER_LABELS.get(trigger or "", "—")


# ---------------------------------------------------------------------------
# Source (where an action item came from)
# ---------------------------------------------------------------------------

SOURCE_LABELS: dict[str, str] = {
    "digest": "Today's report",
    "diary":  "Recent run log",
}


def source_display(source: str | None) -> str:
    return SOURCE_LABELS.get(source or "", source or "")


# ---------------------------------------------------------------------------
# Timestamps — relative human phrasing
# ---------------------------------------------------------------------------

def humanize_time(iso: str | None, now: datetime | None = None) -> str:
    """Relative phrase for past or future timestamps, knowledge-worker friendly.

    Past:
      < 1 min       -> "just now"
      < 1 hour      -> "N minutes ago"
      < 6 hours     -> "about N hours ago"
      same day      -> "earlier today" / "this morning" / "this afternoon"
      yesterday     -> "yesterday"
      < 7 days      -> "last {weekday}"
      < 30 days     -> "N weeks ago"
      else          -> ISO date

    Future:
      < 1 hour      -> "in N minutes"
      same day      -> "later today at HH:MM"
      tomorrow      -> "tomorrow at HH:MM"
      < 7 days      -> "next {weekday} at HH:MM"
      else          -> ISO date
    """
    if not iso:
        return "—"
    now = now or datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    delta = (dt - now).total_seconds()
    abs_d = abs(delta)

    # Past
    if delta <= 0:
        if abs_d < 60:
            return "just now"
        if abs_d < 3600:
            m = int(abs_d // 60)
            return f"{m} minute{'s' if m != 1 else ''} ago"
        if abs_d < 6 * 3600:
            h = int(abs_d // 3600)
            return f"about {h} hour{'s' if h != 1 else ''} ago"
        if dt.date() == now.date():
            hour = dt.hour
            if hour < 12:
                return "earlier this morning"
            if hour < 17:
                return "earlier this afternoon"
            return "earlier this evening"
        if (now.date() - dt.date()).days == 1:
            return "yesterday"
        if abs_d < 7 * 86400:
            return f"last {dt.strftime('%A')}"
        weeks = int(abs_d // (7 * 86400))
        if weeks <= 4:
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        return dt.date().isoformat()

    # Future
    if abs_d < 3600:
        m = max(1, int(abs_d // 60))
        return f"in {m} minute{'s' if m != 1 else ''}"
    hhmm = dt.strftime("%H:%M")
    if dt.date() == now.date():
        return f"later today at {hhmm}"
    if (dt.date() - now.date()).days == 1:
        return f"tomorrow at {hhmm}"
    if abs_d < 7 * 86400:
        return f"next {dt.strftime('%A')} at {hhmm}"
    return dt.date().isoformat()


# ---------------------------------------------------------------------------
# Convenience for collectors
# ---------------------------------------------------------------------------

def decorate_job(job: dict) -> dict:
    """Mutate a job dict in-place to add display_* fields.

    The collector creates the raw fields; this function adds their human
    twins so the client can pick whichever tier it's rendering for.
    """
    label, hint = job_display(job.get("job", ""))
    job["display_name"] = label
    job["display_hint"] = hint
    job["display_schedule_short"] = schedule_display(job.get("schedule"), short=True)
    job["display_schedule_long"] = schedule_display(job.get("schedule"), short=False)
    job["display_verdict"] = verdict_display(job.get("verdict"))
    job["display_status"] = status_display(job.get("status"), job.get("status_detail"))
    job["display_dot"] = verdict_dot(job.get("verdict"))
    # Relative-time versions of next/last run. The existing _humanize_relative
    # stays for the chip, but the drawer uses these richer forms.
    job["display_next_run"] = humanize_time(job.get("next_run_iso"))
    job["display_last_run"] = humanize_time(job.get("last_run_iso"))
    return job


def decorate_diary_entry(entry: dict) -> dict:
    """Add display_* fields for a unified run-history row."""
    label, _ = job_display(entry.get("job", ""))
    entry["display_name"] = label
    entry["display_verdict"] = verdict_display(entry.get("verdict"))
    entry["display_dot"] = verdict_dot(entry.get("verdict"))
    entry["display_trigger"] = trigger_display(entry.get("trigger"))
    entry["display_when"] = humanize_time(entry.get("timestamp"))
    return entry


def decorate_action(item: dict) -> dict:
    """Add display_* fields for an actions-inbox item."""
    sj = item.get("source_job")
    if sj:
        item["display_source_job"] = job_display(sj)[0]
    item["display_source"] = source_display(item.get("source"))
    return item


def decorate_file_finding(f: dict) -> dict:
    f["display_issue"] = issue_display(f.get("issue"))
    f["display_fix"] = fix_display(f.get("fix_id")) if f.get("fix_id") else None
    return f


def decorate_each(items: Iterable[dict], fn) -> list[dict]:
    return [fn(x) for x in items]

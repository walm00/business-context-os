"""
headless_actions.py — Handler dispatch for one-click cards.

Each entry in `HANDLERS` corresponds to an action ID defined in
`.claude/skills/schedule-dispatcher/references/headless-actions.md`. The
schema/wiring tests in `.claude/scripts/test_headless_actions.py` enforce
that every action defined there has a handler here, and that every
handler is reachable.

Handlers receive `(body, ctx)` from the dashboard server and return a
result dict consumed by /api/actions/headless. The body shape is fixed:

    {
      "id": "<action-id>",
      "finding": { ... full Finding from sidecar ... },
      "natural_language_command": "..." | None,
      "bulk_id": "<uuid>" | None,
      "dry_run": bool   # default true until P4 wires record_resolution
    }

DRY-RUN POLICY (v0.1)
---------------------
The dispatcher endpoint defaults to `dry_run: true`. Handlers compute
`applied_diff_summary` (what the change WOULD do) without touching the
filesystem. The wet path turns on once `record_resolution.py` (P4_002)
is in place — at that point the body's `dry_run` flag is plumbed through
and only callers explicitly opting out of dry-run cause writes.

This staged approach lets us land the contract + endpoint registration
+ wiring tests now, without the risk of a misfired headless click moving
or deleting a real file before the resolutions log can record it. Per
CLAUDE.md: hard-to-reverse operations stay gated.

If a handler cannot describe its proposed change without inspecting
state (e.g. the move target depends on cluster mapping) it returns
`needs-followup` with a question payload that the cockpit surfaces as a
follow-up card.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from single_repo import REPO_ROOT  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_finding(body: dict) -> dict:
    f = body.get("finding") or {}
    if not isinstance(f, dict):
        return {}
    return f


def _attrs(body: dict) -> dict:
    return _coerce_finding(body).get("finding_attrs") or {}


def _envelope(action_id: str, body: dict, *, summary: str, telemetry: str, **extra) -> dict:
    """Standard handler return shape."""
    return {
        "ok": True,
        "action_id": action_id,
        "applied": False,            # flips True once P4 wet path lands
        "dry_run": bool(body.get("dry_run", True)),
        "applied_diff_summary": summary,
        "telemetry_event": telemetry,
        "ts": _now_iso(),
        "bulk_id": body.get("bulk_id") or str(uuid.uuid4()),
        "natural_language_command": body.get("natural_language_command"),
        **extra,
    }


def _need_field(attrs: dict, key: str) -> str | None:
    """Return the value or None; lets handlers fail-soft with a clear error."""
    val = attrs.get(key)
    if val is None or val == "":
        return None
    return str(val)


# ---------------------------------------------------------------------------
# Per-action handlers
# ---------------------------------------------------------------------------


def _h_inbox_aged_triage(body: dict, ctx: dict | None = None) -> dict:
    file_ = _need_field(_attrs(body), "file")
    if not file_:
        return {"ok": False, "error": "finding_attrs.file required for inbox-aged-triage"}
    return _envelope(
        "inbox-aged-triage",
        body,
        summary=f"Open {file_} and prompt for triage destination (cluster).",
        telemetry="inbox-triaged",
        followup={"kind": "ask-cluster", "file": file_},
    )


def _h_inbox_aged_archive(body: dict, ctx: dict | None = None) -> dict:
    file_ = _need_field(_attrs(body), "file")
    if not file_:
        return {"ok": False, "error": "finding_attrs.file required for inbox-aged-archive"}
    year = datetime.now(timezone.utc).strftime("%Y")
    target = f"docs/_archive/{year}/{Path(file_).name}"
    return _envelope(
        "inbox-aged-archive",
        body,
        summary=f"Move {file_} → {target}; add last-archived: {datetime.now(timezone.utc).date().isoformat()}.",
        telemetry="inbox-archived",
        proposed_target=target,
    )


def _h_stale_propagation_mark_reviewed(body: dict, ctx: dict | None = None) -> dict:
    wiki_file = _need_field(_attrs(body), "wiki_file") or _need_field(_attrs(body), "file")
    if not wiki_file:
        return {"ok": False, "error": "finding_attrs.wiki_file required for stale-propagation-mark-reviewed"}
    today = datetime.now(timezone.utc).date().isoformat()
    return _envelope(
        "stale-propagation-mark-reviewed",
        body,
        summary=f"Set last-reviewed: {today} on {wiki_file} (frontmatter only, body untouched).",
        telemetry="wiki-marked-reviewed",
    )


def _h_source_summary_refresh(body: dict, ctx: dict | None = None) -> dict:
    wiki_file = _need_field(_attrs(body), "wiki_file") or _need_field(_attrs(body), "file")
    if not wiki_file:
        return {"ok": False, "error": "finding_attrs.wiki_file required for source-summary-refresh"}
    slug = Path(wiki_file).stem
    return _envelope(
        "source-summary-refresh",
        body,
        summary=f"Invoke bcos-wiki refresh --slug {slug} (delegated to skill).",
        telemetry="source-summary-refreshed",
        delegate={"skill": "bcos-wiki", "subcommand": "refresh", "slug": slug},
    )


def _h_graveyard_stale_archive(body: dict, ctx: dict | None = None) -> dict:
    file_ = _need_field(_attrs(body), "file")
    if not file_:
        return {"ok": False, "error": "finding_attrs.file required for graveyard-stale-archive"}
    target = f".private/_planned-archive/{Path(file_).name}"
    return _envelope(
        "graveyard-stale-archive",
        body,
        summary=f"Move {file_} → {target} (.private/ is gitignored).",
        telemetry="graveyard-archived",
        proposed_target=target,
    )


def _h_orphan_page_archive(body: dict, ctx: dict | None = None) -> dict:
    wiki_file = _need_field(_attrs(body), "wiki_file") or _need_field(_attrs(body), "file")
    if not wiki_file:
        return {"ok": False, "error": "finding_attrs.wiki_file required for orphan-page-archive"}
    year = datetime.now(timezone.utc).strftime("%Y")
    target = f"docs/_archive/wiki-pages/{year}/{Path(wiki_file).name}"
    return _envelope(
        "orphan-page-archive",
        body,
        summary=f"Move {wiki_file} → {target}.",
        telemetry="orphan-archived",
        proposed_target=target,
    )


def _h_retired_page_type_migrate(body: dict, ctx: dict | None = None) -> dict:
    attrs = _attrs(body)
    wiki_file = _need_field(attrs, "wiki_file")
    retired = _need_field(attrs, "retired_type")
    if not wiki_file or not retired:
        return {"ok": False, "error": "wiki_file + retired_type required"}
    return _envelope(
        "retired-page-type-migrate",
        body,
        summary=f"Update page-type on {wiki_file} from {retired} → canonical replacement (per wiki-zone.md).",
        telemetry="page-type-migrated",
    )


def _h_coverage_gap_stub(body: dict, ctx: dict | None = None) -> dict:
    attrs = _attrs(body)
    anchor = (
        _need_field(attrs, "data_point")
        or _need_field(attrs, "data_point_file")
        or _need_field(attrs, "owner_doc")
        or _need_field(attrs, "term")
    )
    if not anchor:
        return {"ok": False, "error": "no anchor field (data_point / data_point_file / owner_doc / term) on finding_attrs"}
    slug = Path(str(anchor)).stem.lower().replace(" ", "-").replace("_", "-")
    target = f"docs/_wiki/pages/{slug}.md"
    return _envelope(
        "coverage-gap-stub",
        body,
        summary=f"Create stub at {target} with builds-on: [{anchor}], status: stub.",
        telemetry="coverage-stub-created",
        proposed_target=target,
    )


def _h_demote_rule(body: dict, ctx: dict | None = None) -> dict:
    """P7_010 — /settings/learning [Demote] button.

    Adds the rule_id to learning-blocklist.json and triggers regen so the
    cockpit's "✨ suggested" badge clears immediately. Reversible via
    /learning unblock.
    """
    rid = (_attrs(body) or {}).get("rule_id") or body.get("rule_id")
    if not rid:
        return {"ok": False, "error": "finding_attrs.rule_id required"}
    try:
        from promote_resolutions import add_to_blocklist, regenerate
        add_to_blocklist(rid)
        regenerate()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"blocklist write failed: {type(exc).__name__}: {exc}"}
    return _envelope(
        "demote-rule",
        body,
        summary=f"Demoted rule {rid} (added to learning-blocklist.json).",
        telemetry="rule-demoted",
    )


def _h_unblock_rule(body: dict, ctx: dict | None = None) -> dict:
    """Reverse of demote-rule. Removes rule_id from learning-blocklist.json."""
    rid = (_attrs(body) or {}).get("rule_id") or body.get("rule_id")
    if not rid:
        return {"ok": False, "error": "finding_attrs.rule_id required"}
    try:
        from promote_resolutions import remove_from_blocklist, regenerate
        remove_from_blocklist(rid)
        regenerate()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"blocklist remove failed: {type(exc).__name__}: {exc}"}
    return _envelope(
        "unblock-rule",
        body,
        summary=f"Unblocked rule {rid} (removed from learning-blocklist.json).",
        telemetry="rule-unblocked",
    )


def _h_apply_suggestion(body: dict, ctx: dict | None = None) -> dict:
    """P2_008 — frequency-suggestion Apply card.

    Forwards to /api/schedule/preset with the suggested cadence. The
    cockpit's frequency-suggestion finding carries the job + suggested
    schedule in finding_attrs; we just rewrap and dispatch.

    Wet-path-friendly: the underlying preset endpoint is non-destructive
    (writes to schedule-config.json with atomic-rename). No dry-run gate
    needed — the user clicked a card with the proposed schedule visible.
    """
    attrs = _attrs(body)
    job = _need_field(attrs, "job")
    new_schedule = _need_field(attrs, "suggested_schedule")
    if not job or not new_schedule:
        return {"ok": False, "error": "finding_attrs.job + suggested_schedule required"}

    # Delegate by importing run.py's preset writer. Lazy import keeps the
    # module-level dependency graph clean.
    try:
        from run import _post_schedule_preset  # type: ignore[import-not-found]
        # _post_schedule_preset expects (body, ctx); body is {job, preset}.
        result = _post_schedule_preset(
            {"job": job, "preset": new_schedule},
            ctx or {"invalidate_panel": lambda _: None},
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"preset write failed: {type(exc).__name__}: {exc}"}

    if not result.get("ok"):
        return result

    return _envelope(
        "apply-suggestion",
        body,
        summary=f"Applied schedule {new_schedule!r} to job {job!r}.",
        telemetry="frequency-suggestion-applied",
        delegated_to="schedule-preset",
    )


def _h_lesson_candidate_add(body: dict, ctx: dict | None = None) -> dict:
    attrs = _attrs(body)
    text = _need_field(attrs, "lesson_text")
    if not text:
        return {"ok": False, "error": "finding_attrs.lesson_text required"}
    existing = _need_field(attrs, "existing_lesson_id")
    if existing:
        summary = f"Bump last-violation-date on existing lesson {existing} (no duplicate created)."
    else:
        summary = "Append new entry to .claude/quality/ecosystem/lessons.json with current timestamp."
    return _envelope(
        "lesson-candidate-add",
        body,
        summary=summary,
        telemetry="lesson-captured",
    )


def _h_lifecycle_route_archive(body: dict, ctx: dict | None = None) -> dict:
    attrs = _attrs(body)
    file_ = _need_field(attrs, "file")
    if not file_:
        return {"ok": False, "error": "finding_attrs.file required for lifecycle-route-archive"}
    bucket = attrs.get("destination_bucket") or "lifecycle"
    target = f"docs/_archive/{bucket}/{Path(file_).name}"
    return _envelope(
        "lifecycle-route-archive",
        body,
        summary=f"git mv {file_} → {target}.",
        telemetry="lifecycle-archived",
        proposed_target=target,
    )


def _h_lifecycle_route_wiki(body: dict, ctx: dict | None = None) -> dict:
    attrs = _attrs(body)
    file_ = _need_field(attrs, "file")
    if not file_:
        return {"ok": False, "error": "finding_attrs.file required for lifecycle-route-wiki"}
    slug = Path(file_).stem
    return _envelope(
        "lifecycle-route-wiki",
        body,
        summary=f"Delegate to bcos-wiki: /wiki promote {slug}.",
        telemetry="lifecycle-promoted-to-wiki",
        delegate={"skill": "bcos-wiki", "subcommand": "promote", "slug": slug},
    )


def _h_lifecycle_route_collection(body: dict, ctx: dict | None = None) -> dict:
    attrs = _attrs(body)
    file_ = _need_field(attrs, "file")
    if not file_:
        return {"ok": False, "error": "finding_attrs.file required for lifecycle-route-collection"}
    bucket = attrs.get("destination_bucket") or "uncategorized"
    target = f"docs/_collections/{bucket}/{Path(file_).name}"
    return _envelope(
        "lifecycle-route-collection",
        body,
        summary=f"Delegate to context-ingest Path 5: route {file_} → {target}.",
        telemetry="lifecycle-routed-to-collection",
        proposed_target=target,
        delegate={"skill": "context-ingest", "subcommand": "path-5", "destination": target},
    )


def _h_lifecycle_fold_into(body: dict, ctx: dict | None = None) -> dict:
    attrs = _attrs(body)
    file_ = _need_field(attrs, "file")
    if not file_:
        return {"ok": False, "error": "finding_attrs.file required for lifecycle-fold-into"}
    return _envelope(
        "lifecycle-fold-into",
        body,
        summary=f"Surface fold target for {file_}; user confirms before edit.",
        telemetry="lifecycle-folded",
        followup={"kind": "ask-fold-target", "file": file_},
    )


def _h_acknowledge(body: dict, ctx: dict | None = None) -> dict:
    """The only action permitted on `category: "bcos-framework"` findings.

    The user is saying "I've seen this; mark read in the cockpit, route to
    portfolio aggregation as already-seen." No files mutated in client repo
    — patching framework state locally would be overwritten by the next
    `update.py`. The framework owner sees the issue via the umbrella's
    cross-sibling aggregation of `bcos-framework-issues.jsonl`.

    Added in 1.1.0. Applies to any of the 7 framework finding_types listed
    in `finding-categories.md`. Safe to call on a repo-context finding too
    (degenerate case: equivalent to dismissing), but the cockpit only
    surfaces this action for framework cards.
    """
    finding = _coerce_finding(body)
    finding_type = finding.get("finding_type", "?")
    return _envelope(
        "acknowledge",
        body,
        summary=f"Acknowledged framework finding: {finding_type}. No files mutated.",
        telemetry="framework-issue-acknowledged",
    )


HANDLERS: dict[str, Callable[..., dict]] = {
    "inbox-aged-triage":              _h_inbox_aged_triage,
    "inbox-aged-archive":             _h_inbox_aged_archive,
    "stale-propagation-mark-reviewed": _h_stale_propagation_mark_reviewed,
    "source-summary-refresh":         _h_source_summary_refresh,
    "graveyard-stale-archive":        _h_graveyard_stale_archive,
    "orphan-page-archive":            _h_orphan_page_archive,
    "retired-page-type-migrate":      _h_retired_page_type_migrate,
    "coverage-gap-stub":              _h_coverage_gap_stub,
    "lesson-candidate-add":           _h_lesson_candidate_add,
    "apply-suggestion":               _h_apply_suggestion,
    "demote-rule":                    _h_demote_rule,
    "unblock-rule":                   _h_unblock_rule,
    "lifecycle-route-archive":        _h_lifecycle_route_archive,
    "lifecycle-route-wiki":           _h_lifecycle_route_wiki,
    "lifecycle-route-collection":     _h_lifecycle_route_collection,
    "lifecycle-fold-into":            _h_lifecycle_fold_into,
    # 1.1.0 — acknowledge-only handler for bcos-framework category findings.
    "acknowledge":                    _h_acknowledge,
}


def _is_action_enabled(action_id: str) -> bool:
    """Read schedule-config.json > headless_actions.enabled[].

    Defaults to false-on-missing; the action is opt-in until the user
    explicitly enables it. Reads on every call (configs are small;
    saves us a cache-invalidation seam).
    """
    cfg_path = REPO_ROOT / ".claude" / "quality" / "schedule-config.json"
    if not cfg_path.is_file():
        # Fall back to the template default — the config may not exist yet
        # in fresh installs.
        cfg_path = REPO_ROOT / ".claude" / "quality" / "schedule-config.template.json"
    try:
        import json

        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    enabled = (cfg.get("headless_actions") or {}).get("enabled") or []
    return action_id in enabled


def _infer_trigger(body: dict) -> str:
    """Pick the right `trigger` enum for resolutions.jsonl.

    The endpoint serves three callers:
    - browser click → "dashboard-click"
    - assistant invokes for many findings under one phrase → "chat-bulk-fix"
    - assistant invokes for one specific finding → "chat-targeted-fix"

    Heuristic: an assistant supplies natural_language_command (the chat
    intercept payload from option-a in headless-actions.md). A bulk_id
    supplied externally implies a multi-call grouping → bulk-fix; absent
    implies targeted. Browser clicks send neither.
    """
    if body.get("natural_language_command"):
        if body.get("bulk_id"):
            return "chat-bulk-fix"
        return "chat-targeted-fix"
    return "dashboard-click"


def dispatch(body: dict, ctx: dict | None = None) -> dict:
    """Public entry point for /api/actions/headless POST.

    Body required: {id, finding}. Optional: natural_language_command,
    bulk_id, dry_run.

    P4_004: every successful dispatch writes a row to resolutions.jsonl
    with all 14 fields populated. Recording failures are logged but
    don't block the response — the user always sees the action result.
    """
    action_id = (body or {}).get("id")
    if not action_id:
        return {"ok": False, "error": "id required"}
    if action_id not in HANDLERS:
        return {"ok": False, "error": f"unknown action: {action_id}"}
    if not _is_action_enabled(action_id):
        return {"ok": False, "error": f"action {action_id!r} not enabled in schedule-config.json", "status": 403}

    result = HANDLERS[action_id](body, ctx)

    if result.get("ok"):
        try:
            # record_resolution lives one dir up.
            _scripts = _HERE.parent
            if str(_scripts) not in sys.path:
                sys.path.insert(0, str(_scripts))
            from record_resolution import ResolutionEvent, record  # type: ignore[import-not-found]

            finding = body.get("finding") or {}
            attrs = finding.get("finding_attrs") or {}
            outcome = "skipped" if result.get("dry_run", True) else "applied"

            record(ResolutionEvent(
                finding_type=finding.get("finding_type") or action_id,
                finding_attrs=attrs,
                action_taken=action_id,
                action_target=(
                    attrs.get("file")
                    or attrs.get("wiki_file")
                    or attrs.get("data_point_file")
                    or result.get("proposed_target")
                ),
                outcome=outcome,
                trigger=_infer_trigger(body),
                bulk_id=result.get("bulk_id"),
                natural_language_command=body.get("natural_language_command"),
                applied_diff_summary=result.get("applied_diff_summary", ""),
            ))
        except Exception:
            import traceback
            traceback.print_exc(file=sys.stderr)

    return result

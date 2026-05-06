"""
record_resolution.py — Append-only event log for every resolution decision.

The contract is pinned in `docs/_planned/autonomy-ux-self-learning/implementation-plan.md`
§D-02. Every fix path that BCOS triggers (auto-fix-whitelist silent runs, headless
card clicks, chat-bulk-fix invocations, dashboard mark-done) writes one line to
`.claude/quality/ecosystem/resolutions.jsonl` with all 14 fields populated from
day 1 — no migration debt for downstream consumers (P5 promotion ladder, P6
auditor, P7 evidence views).

Schema fields (the canonical 14):

    ts                           ISO-8601 UTC timestamp
    finding_type                 enum value from typed-events.md
    finding_attrs                flat dict from the typed event
    action_taken                 ID from headless-actions.md / auto-fix-whitelist.md
    action_target                primary target path (usually finding_attrs.file)
    outcome                      "applied" | "reverted" | "skipped" | "errored"
    time_to_resolution_s         seconds from finding emit to action click
    trigger                      "dashboard-click" | "chat-bulk-fix" |
                                 "chat-targeted-fix" | "scheduled-headless" |
                                 "auto-fix-whitelist"
    bulk_id                      UUID; one per chat phrase, fresh per dashboard click
    natural_language_command     verbatim user phrase (assistant-supplied) or null
    user_specificity             "global" | "category" | "targeted" | null
    applied_diff_summary         one-line description of the change
    applied_diff_hash            sha256 of the proposed-or-applied diff
    subsequent_validation_status "pending" | "passed" | "failed" | null

Rule of thumb: emit "pending" for `subsequent_validation_status` and let the
post-edit hook stamp it later (P4_008 lazy writeback). Never silently drop a
field — emit `null` instead so downstream consumers can rely on the shape.

Used by:
- bcos-dashboard/actions_resolved.py (mark-done clicks)
- bcos-dashboard/headless_actions.py (one-click cards)
- the dispatcher's auto-fix path (when whitelist fixes apply)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Resolve repo root via the dashboard's helper to keep one source of truth.
_DASH = _HERE / "bcos-dashboard"
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))
from single_repo import REPO_ROOT  # noqa: E402

STORE_PATH = REPO_ROOT / ".claude" / "quality" / "ecosystem" / "resolutions.jsonl"
_WRITE_LOCK = Lock()

ALLOWED_TRIGGERS = {
    "dashboard-click",
    "chat-bulk-fix",
    "chat-targeted-fix",
    "scheduled-headless",
    "auto-fix-whitelist",
}
ALLOWED_OUTCOMES = {"applied", "reverted", "skipped", "errored"}
ALLOWED_VALIDATION = {"pending", "passed", "failed", None}
ALLOWED_USER_SPECIFICITY = {"global", "category", "targeted", None}


REQUIRED_FIELDS = (
    "ts",
    "finding_type",
    "finding_attrs",
    "action_taken",
    "action_target",
    "outcome",
    "time_to_resolution_s",
    "trigger",
    "bulk_id",
    "natural_language_command",
    "user_specificity",
    "applied_diff_summary",
    "applied_diff_hash",
    "subsequent_validation_status",
)


# ---------------------------------------------------------------------------
# user_specificity classifier (P4_006)
# ---------------------------------------------------------------------------
#
# Mechanical heuristic per D-01. Returns "global" / "category" / "targeted" /
# None depending on the natural-language phrase the assistant supplied.
# Order of checks matters — "fix all the inbox stuff" should classify as
# `category` (the inbox one), not `global` ("all").

_GLOBAL_PATTERNS = (
    r"\b(fix|clean|address|do)\s+(all|everything|the lot)\b",
    r"\bfix\s+them\s+all\b",
    r"\b(everything|all of (them|it))\b",
    r"\bclean\s+it\s+up\b",
)
_TARGETED_PATTERNS = (
    r"\b(fix|address)\s+(this|that)\b",
    r"\b(this|that)\s+(one|file|page|item)\b",
    r"\bjust\s+this\b",
    r"\bthe\s+\w+\s+(file|page|doc)\b",
)
_CATEGORY_KEYWORDS = (
    "wiki",
    "inbox",
    "lessons",
    "lesson",
    "frontmatter",
    "xref",
    "stale",
    "archive",
    "graveyard",
    "coverage",
    "source",
)


def classify_user_specificity(phrase: str | None) -> str | None:
    """Classify a natural-language command into global/category/targeted.

    Returns None when phrase is None/empty, signalling "no chat intercept
    happened" rather than a low-confidence classification. The downstream
    consumer treats None as different from a positive classification.
    """
    if not phrase:
        return None
    p = phrase.lower().strip()
    if not p:
        return None

    # Targeted check first: an explicit "this one" beats a category keyword.
    for pat in _TARGETED_PATTERNS:
        if re.search(pat, p):
            return "targeted"

    # Category check: a domain keyword present without an "all" qualifier
    # is category-scoped ("fix the wiki ones").
    if any(kw in p for kw in _CATEGORY_KEYWORDS):
        # If "all" qualifies the keyword, it's still category — the user
        # named a slice. "Fix all the wiki ones" = category, not global.
        return "category"

    # Global check: "all" / "everything" with no domain keyword.
    for pat in _GLOBAL_PATTERNS:
        if re.search(pat, p):
            return "global"

    # Phrase exists but matched nothing recognizable.
    return None


# ---------------------------------------------------------------------------
# bulk_id grouping (P4_005)
# ---------------------------------------------------------------------------


def new_bulk_id() -> str:
    """Generate a fresh UUID4 for a new bulk grouping.

    The assistant supplies one bulk_id per natural-language phrase. The
    recorder accepts whatever the assistant provides; if absent, it
    generates a fresh ID per call (no grouping). Callers wanting to
    group N events under one ID should call this once and pass it to
    each `record()` call.
    """
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# applied_diff_hash + summary (P4_007)
# ---------------------------------------------------------------------------


def diff_hash(diff_text: str | bytes) -> str:
    """Stable sha256 of a `git diff -p` output (or summary string in dry-run).

    Returns the hex digest. The auditor (P6) keys reversal detection on
    exact-inverse pairs of this hash within a 7-day window, so stability
    matters: same diff twice → same hash twice. Trailing whitespace is
    stripped before hashing to reduce trivial drift.
    """
    if isinstance(diff_text, str):
        data = diff_text.strip().encode("utf-8")
    else:
        data = diff_text.strip()
    return hashlib.sha256(data).hexdigest()


def capture_git_diff(target_path: str | None) -> tuple[str, str]:
    """Run `git diff -p <path>` and return (summary, hash).

    Used by the wet path. The summary is one line: "M docs/foo.md (+2/-1)".
    For dry-run callers (handlers in headless_actions.py v0.1), use
    `_envelope`'s pre-computed `applied_diff_summary` and pass it to
    `diff_hash()` directly.
    """
    if not target_path:
        return ("(no target)", diff_hash("(no target)"))
    try:
        import subprocess

        result = subprocess.run(
            ["git", "diff", "-p", "--", target_path],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        diff_text = result.stdout or ""
    except Exception:
        return (f"(diff capture failed for {target_path})", diff_hash(target_path))

    if not diff_text.strip():
        return (f"(no changes on {target_path})", diff_hash(f"noop:{target_path}"))

    plus = sum(1 for ln in diff_text.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    minus = sum(1 for ln in diff_text.splitlines() if ln.startswith("-") and not ln.startswith("---"))
    summary = f"M {target_path} (+{plus}/-{minus})"
    return (summary, diff_hash(diff_text))


# ---------------------------------------------------------------------------
# Public record() entry point
# ---------------------------------------------------------------------------


@dataclass
class ResolutionEvent:
    finding_type: str
    finding_attrs: dict[str, Any]
    action_taken: str
    action_target: str | None
    outcome: str  # "applied" | "reverted" | "skipped" | "errored"
    trigger: str
    time_to_resolution_s: float = 0.0
    bulk_id: str | None = None
    natural_language_command: str | None = None
    user_specificity: str | None = None
    applied_diff_summary: str = ""
    applied_diff_hash: str = ""
    subsequent_validation_status: str | None = "pending"
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    def to_row(self) -> dict[str, Any]:
        # Auto-classify if caller passed a phrase but no specificity.
        if self.natural_language_command and self.user_specificity is None:
            self.user_specificity = classify_user_specificity(self.natural_language_command)
        # Auto-fill bulk_id if missing.
        if not self.bulk_id:
            self.bulk_id = new_bulk_id()
        # Auto-fill diff hash from summary if caller passed a summary but no hash.
        if self.applied_diff_summary and not self.applied_diff_hash:
            self.applied_diff_hash = diff_hash(self.applied_diff_summary)

        row: dict[str, Any] = {
            "ts": self.ts,
            "finding_type": self.finding_type,
            "finding_attrs": dict(self.finding_attrs or {}),
            "action_taken": self.action_taken,
            "action_target": self.action_target,
            "outcome": self.outcome,
            "time_to_resolution_s": float(self.time_to_resolution_s),
            "trigger": self.trigger,
            "bulk_id": self.bulk_id,
            "natural_language_command": self.natural_language_command,
            "user_specificity": self.user_specificity,
            "applied_diff_summary": self.applied_diff_summary or "",
            "applied_diff_hash": self.applied_diff_hash or "",
            "subsequent_validation_status": self.subsequent_validation_status,
        }
        _validate(row)
        return row


def _validate(row: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_FIELDS if k not in row]
    if missing:
        raise ValueError(f"resolution row missing fields: {missing}")
    if row["trigger"] not in ALLOWED_TRIGGERS:
        raise ValueError(f"invalid trigger: {row['trigger']!r}")
    if row["outcome"] not in ALLOWED_OUTCOMES:
        raise ValueError(f"invalid outcome: {row['outcome']!r}")
    if row["user_specificity"] not in ALLOWED_USER_SPECIFICITY:
        raise ValueError(f"invalid user_specificity: {row['user_specificity']!r}")
    if row["subsequent_validation_status"] not in ALLOWED_VALIDATION:
        raise ValueError(f"invalid subsequent_validation_status: {row['subsequent_validation_status']!r}")
    if not isinstance(row["finding_attrs"], dict):
        raise ValueError("finding_attrs must be a dict")
    if not isinstance(row["time_to_resolution_s"], (int, float)):
        raise ValueError("time_to_resolution_s must be numeric")


def record(event: ResolutionEvent) -> dict[str, Any]:
    """Append a resolution event. Returns the written row.

    Atomic against parallel callers via _WRITE_LOCK. Creates the parent
    directory on first write. Append-only — never edits prior rows.
    """
    row = event.to_row()
    with _WRITE_LOCK:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with STORE_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def stamp_validation_status(applied_diff_hash: str, status: str) -> int:
    """Lazy writeback for subsequent_validation_status (P4_008).

    The post-edit frontmatter hook drains a queue of (hash → status) tuples
    and updates rows whose `applied_diff_hash` matches. Atomic via temp-file
    rewrite. Returns the number of rows updated.
    """
    if status not in ("passed", "failed"):
        raise ValueError(f"status must be passed/failed: {status!r}")
    if not STORE_PATH.is_file():
        return 0

    updated = 0
    rows: list[str] = []
    with STORE_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            raw = line.rstrip("\n")
            if not raw.strip():
                rows.append(raw)
                continue
            try:
                obj = json.loads(raw)
            except Exception:
                rows.append(raw)
                continue
            if (
                obj.get("applied_diff_hash") == applied_diff_hash
                and obj.get("subsequent_validation_status") == "pending"
            ):
                obj["subsequent_validation_status"] = status
                updated += 1
                rows.append(json.dumps(obj, ensure_ascii=False))
            else:
                rows.append(raw)

    if updated == 0:
        return 0

    tmp = STORE_PATH.with_suffix(".jsonl.tmp")
    with _WRITE_LOCK:
        with tmp.open("w", encoding="utf-8") as fh:
            for ln in rows:
                fh.write(ln + "\n")
        os.replace(tmp, STORE_PATH)
    return updated


def load_all_rows() -> list[dict[str, Any]]:
    """Read the full event log. Used by P5 promotion + P6 auditor."""
    if not STORE_PATH.is_file():
        return []
    out: list[dict[str, Any]] = []
    with STORE_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out

"""
digest_parser.py — Parse docs/_inbox/daily-digest.md into per-job sections.

The dispatcher emits a digest with this fixed shape (see
schedule-dispatcher/SKILL.md Step 7):

    # Daily Maintenance Digest — YYYY-MM-DD

    **Overall:** {emoji} {verdict} — N jobs ran, M auto-fixes, K action items.

    ## ⚠️ Action needed (K)
    ### 1. ...
    ### 2. ...

    ## 🔧 Auto-fixed (M)
    None. OR list

    ## Per-job summary
    ### {job} — {emoji} {verdict}
    {body}

    ### {next-job} — ...

    ---
    _Run at {iso}. Full history: ..._

We parse it back into structured data so the dashboard can render each
section in its own UI surface (jobs panel, actions inbox). Heuristic /
regex — the digest is authored by Claude from a fixed template, so shape
is stable. Unknown sections are preserved as `extra_sections`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_VERDICT_EMOJI = {
    "🟢": "green",
    "🟡": "amber",
    "🔴": "red",
    "⚠️": "error",
    "⚠": "error",
}

_JOB_HEADING = re.compile(
    r"^###\s+(?P<job>[A-Za-z0-9_\-]+)\s+—\s+(?P<emoji>🟢|🟡|🔴|⚠️|⚠)\s+(?P<verdict>green|amber|red|error)\s*$"
)
_ACTION_HEADING = re.compile(r"^###\s+(?P<num>\d+)\.\s+(?P<title>.+)$")
_OVERALL = re.compile(
    r"^\*\*Overall:\*\*\s+(?P<emoji>🟢|🟡|🔴|⚠️|⚠)\s+(?P<verdict>green|amber|red|error)\s*(?:—\s*(?P<tail>.+))?$"
)
_RUN_AT = re.compile(r"_Run at (?P<ts>[0-9T:\-.Z+]+)\.")


@dataclass
class JobSection:
    job: str
    verdict: str  # green|amber|red|error
    body: str = ""  # trimmed markdown body of this job's subsection


@dataclass
class ActionItem:
    number: int
    title: str
    body: str = ""


@dataclass
class ParsedDigest:
    date: str | None = None
    overall_verdict: str | None = None
    overall_summary: str | None = None
    run_at: str | None = None
    actions: list[ActionItem] = field(default_factory=list)
    auto_fixed: list[str] = field(default_factory=list)
    jobs: dict[str, JobSection] = field(default_factory=dict)


def parse_digest(path: Path) -> ParsedDigest | None:
    """Parse a daily-digest.md file; return None if absent or unreadable."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    return _parse_text(text)


def _parse_text(text: str) -> ParsedDigest:
    pd = ParsedDigest()
    lines = text.splitlines()

    # Title line: "# Daily Maintenance Digest — YYYY-MM-DD"
    for ln in lines[:3]:
        m = re.match(r"^#\s+Daily Maintenance Digest\s+—\s+(\d{4}-\d{2}-\d{2})", ln)
        if m:
            pd.date = m.group(1)
            break

    # Overall line
    for ln in lines[:10]:
        m = _OVERALL.match(ln.strip())
        if m:
            pd.overall_verdict = m.group("verdict")
            pd.overall_summary = (m.group("tail") or "").strip()
            break

    # run_at trailer
    for ln in reversed(lines[-10:]):
        m = _RUN_AT.search(ln)
        if m:
            pd.run_at = m.group("ts")
            break

    # Section walker — track current H2 and within that, H3 items.
    section = None        # "actions" | "auto_fixed" | "per_job" | None
    cur_action: ActionItem | None = None
    cur_job: JobSection | None = None
    cur_job_buf: list[str] = []
    cur_action_buf: list[str] = []

    def _flush_action() -> None:
        nonlocal cur_action, cur_action_buf
        if cur_action is not None:
            cur_action.body = "\n".join(cur_action_buf).strip()
            pd.actions.append(cur_action)
        cur_action = None
        cur_action_buf = []

    def _flush_job() -> None:
        nonlocal cur_job, cur_job_buf
        if cur_job is not None:
            cur_job.body = "\n".join(cur_job_buf).strip()
            pd.jobs[cur_job.job] = cur_job
        cur_job = None
        cur_job_buf = []

    for raw in lines:
        ln = raw.rstrip()
        stripped = ln.strip()

        # H2 section boundaries
        if stripped.startswith("## "):
            _flush_action()
            _flush_job()
            h = stripped[3:].strip().lower()
            if h.startswith("⚠") or "action needed" in h:
                section = "actions"
            elif "auto-fixed" in h or "auto fixed" in h or "🔧" in h:
                section = "auto_fixed"
            elif "per-job" in h or "per job summary" in h:
                section = "per_job"
            else:
                section = None
            continue

        # Horizontal rule = end of body
        if stripped == "---":
            _flush_action()
            _flush_job()
            section = None
            continue

        if section == "actions":
            m = _ACTION_HEADING.match(stripped)
            if m:
                _flush_action()
                cur_action = ActionItem(number=int(m.group("num")), title=m.group("title").strip())
                continue
            if cur_action is not None:
                cur_action_buf.append(ln)
            continue

        if section == "auto_fixed":
            if not stripped or stripped.lower() == "none." or stripped.lower() == "none":
                continue
            # "- foo" bullet or plain line
            item = stripped.lstrip("-*• ").strip()
            if item:
                pd.auto_fixed.append(item)
            continue

        if section == "per_job":
            m = _JOB_HEADING.match(stripped)
            if m:
                _flush_job()
                cur_job = JobSection(job=m.group("job"), verdict=m.group("verdict"))
                continue
            if cur_job is not None:
                cur_job_buf.append(ln)
            continue

    # EOF flush
    _flush_action()
    _flush_job()
    return pd


if __name__ == "__main__":
    import json
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/_inbox/daily-digest.md")
    pd = parse_digest(target)
    if pd is None:
        print(f"no digest at {target}", file=sys.stderr)
        sys.exit(2)
    out = {
        "date": pd.date,
        "overall_verdict": pd.overall_verdict,
        "overall_summary": pd.overall_summary,
        "run_at": pd.run_at,
        "action_count": len(pd.actions),
        "auto_fixed_count": len(pd.auto_fixed),
        "jobs": {k: {"verdict": v.verdict, "body_chars": len(v.body)} for k, v in pd.jobs.items()},
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))

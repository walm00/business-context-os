#!/usr/bin/env python3
"""audit_node_configs — portfolio-level drift spotter for the BCOS
node-job cross-repo boundary.

Walks every BCOS-installed sibling under `--root` (or the parent
directory of `$CLAUDE_PROJECT_DIR` if `--root` is omitted), reads each
sibling's `.claude/quality/schedule-config.json`, and scans every
referenced `job-{name}.md` spec for cross-repo references — the same
scan the runtime dispatcher applies in Step 4a preflight.

Diagnostic only. Exit code is **always 0**; the verdict lives in the
JSON output. Wire as an advisory CI step, a one-shot before
onboarding a sibling into a portfolio, or run ad-hoc when investigating
a `node-job-cross-repo-reference` finding from the portfolio
framework-issues feed.

Usage:
    python .claude/scripts/audit_node_configs.py
    python .claude/scripts/audit_node_configs.py --root /path/to/portfolio
    python .claude/scripts/audit_node_configs.py --json
    python .claude/scripts/audit_node_configs.py --root /path --json

Output (JSON shape):
    {
      "scanned": <int>,            # BCOS-installed siblings inspected
      "clean": <int>,              # siblings with zero violations
      "violations": [
        {
          "sibling_id": "<dir-name>",
          "job": "<job_id>",
          "location": "_run" | "_claude_step" | "spec_prose",
          "offending_path": "<first matched substring>"
        },
        ...
      ]
    }

Conceptual pairing: the runtime check is in
`schedule-dispatcher/SKILL.md` Step 4a (emits typed finding
`node-job-cross-repo-reference`). This is the off-line/cold-scan
equivalent — same predicate, different surface.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Patterns flagged as cross-repo references in a job spec. Mirrors the
# documented Step 4a preflight in schedule-dispatcher/SKILL.md.
_PARENT_PATH = re.compile(r"\.\.(?:/|\\)")
_ABSOLUTE_OUTSIDE = re.compile(
    r"(?:^|[^\w])(/(?:home|Users|var|opt|srv)/[^\s`'\"]+|"
    r"[A-Z]:[\\/][^\s`'\"]+)"
)

# Strip markdown-link URLs `[text](path)` before scanning. Internal repo
# navigation via relative paths is common in `## See also` sections; it's
# documentation, not runtime content.
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
# Strip inline `\`backtick\`` code (single-line) so the rule documentation
# (e.g. `\`../\``, `\`$CLAUDE_PROJECT_DIR\``) doesn't false-positive.
_INLINE_CODE = re.compile(r"`[^`]*`")

# Location classifier: where in the spec the offending substring appeared.
_RUN_PREFIX = re.compile(r"_run\s*:", re.IGNORECASE)
_CLAUDE_STEP_PREFIX = re.compile(r"_claude_step\s*:", re.IGNORECASE)


def _classify_location(line: str) -> str:
    if _RUN_PREFIX.search(line):
        return "_run"
    if _CLAUDE_STEP_PREFIX.search(line):
        return "_claude_step"
    return "spec_prose"


def _strip_docs(line: str) -> str:
    """Remove markdown link URLs + inline backtick code from a line before
    scanning. Both are documentation surfaces, not runtime content."""
    return _INLINE_CODE.sub("", _MD_LINK.sub(r"\1", line))


def scan_spec(spec_text: str) -> tuple[str, str] | None:
    """Return (offending_path, location) for the first cross-repo match, or
    None if the spec is clean. Same predicate as the runtime Step 4a
    preflight.

    Two classes of line content are exempt:
    - The `**Boundary:**` stamp line, which by design quotes `../` as a
      forbidden token in its own explanation.
    - Markdown link URLs `[text](path)` and inline backtick code, which
      are documentation surfaces (Phase 3 stamps + See-also sections use
      these heavily for internal navigation within the same repo).
    """
    for raw in spec_text.splitlines():
        if "**Boundary:**" in raw:
            continue
        line = _strip_docs(raw)
        m = _PARENT_PATH.search(line)
        if m:
            start = max(0, m.start() - 0)
            tail = line[start:].split()[0] if line[start:].split() else "../"
            return (tail, _classify_location(line))
        m = _ABSOLUTE_OUTSIDE.search(line)
        if m:
            return (m.group(1), _classify_location(line))
    return None


def _load_jobs(node: Path) -> dict[str, dict]:
    cfg = node / ".claude" / "quality" / "schedule-config.json"
    if not cfg.is_file():
        return {}
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    jobs = data.get("jobs")
    return jobs if isinstance(jobs, dict) else {}


def _spec_path(node: Path, job_name: str) -> Path:
    return (
        node / ".claude" / "skills" / "schedule-dispatcher" / "references"
        / f"job-{job_name}.md"
    )


def audit_node(node: Path) -> list[dict]:
    """Return one violation dict per offending (job, spec) pair for this
    sibling. Empty list = clean."""
    violations: list[dict] = []
    for job_name, job_cfg in _load_jobs(node).items():
        if not isinstance(job_cfg, dict):
            continue
        if not job_cfg.get("enabled", True):
            continue
        spec = _spec_path(node, job_name)
        if not spec.is_file():
            # Out of scope here — the runtime dispatcher emits
            # `job-reference-missing` for these.
            continue
        match = scan_spec(spec.read_text(encoding="utf-8"))
        if match is None:
            continue
        offending_path, location = match
        violations.append({
            "sibling_id": node.name,
            "job": job_name,
            "location": location,
            "offending_path": offending_path,
        })
    return violations


def _is_bcos_node(p: Path) -> bool:
    return p.is_dir() and (p / ".claude" / "quality" / "schedule-config.json").is_file()


def audit_root(root: Path) -> dict:
    """Walk every direct subdirectory of `root`, audit each BCOS node,
    return the summary dict."""
    scanned = 0
    clean = 0
    violations: list[dict] = []
    for child in sorted(root.iterdir()):
        if child.name.startswith("."):
            continue
        if not _is_bcos_node(child):
            continue
        scanned += 1
        node_violations = audit_node(child)
        if not node_violations:
            clean += 1
        else:
            violations.extend(node_violations)
    return {"scanned": scanned, "clean": clean, "violations": violations}


def _resolve_root(arg_root: Path | None) -> Path:
    if arg_root is not None:
        return arg_root.expanduser().resolve()
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve().parent
    return Path.cwd().resolve()


def _render_human(summary: dict, root: Path) -> str:
    lines = [
        f"audit_node_configs scanned {summary['scanned']} BCOS node(s) under {root}",
        f"  clean: {summary['clean']}",
        f"  violations: {len(summary['violations'])}",
    ]
    for v in summary["violations"]:
        lines.append(
            f"    - {v['sibling_id']} :: {v['job']} :: {v['location']} :: {v['offending_path']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", type=Path, default=None,
                   help="Directory containing the BCOS nodes to audit "
                        "(default: parent of $CLAUDE_PROJECT_DIR, or cwd).")
    p.add_argument("--json", action="store_true",
                   help="Emit machine-readable JSON to stdout (verdict-in-payload).")
    p.add_argument("--dry-run", action="store_true",
                   help="(Reserved; this auditor is already read-only.)")
    args = p.parse_args(argv)

    root = _resolve_root(args.root)
    summary = audit_root(root)

    if args.json:
        sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    else:
        sys.stdout.write(_render_human(summary, root) + "\n")
    # Always 0 — verdict lives in the payload.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
post_commit_context_check.py - Claude Code PostToolUse hook for Bash (git commit).

Fires after Claude runs a Bash command containing "git commit". Inspects what
was committed and surfaces targeted suggestions via stderr:
  - New/changed skill or agent → suggest ecosystem-manager
  - Active context docs changed → suggest lessons capture
  - Any commit → lightweight reminder

Hook event:  PostToolUse
Matcher:     Bash
Exit codes:
  0  always — warns, never blocks

Note: This hook SUGGESTS, it doesn't block. Claude sees the warnings and
can choose to act. The user is always in control.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Patterns — what file paths signal what kind of work
# ---------------------------------------------------------------------------

SKILL_PATTERN   = re.compile(r"\.claude/skills/.+/SKILL\.md")
AGENT_PATTERN   = re.compile(r"\.claude/agents/.+/AGENT\.md")
ACTIVE_DOC_PAT  = re.compile(r"^docs/(?!_inbox/|_archive/|_planned/|methodology/|guides/|templates/|architecture/).+\.md$")
HOOK_PATTERN    = re.compile(r"\.claude/hooks/.+\.py")
SCRIPT_PATTERN  = re.compile(r"\.claude/scripts/.+\.py")

# ---------------------------------------------------------------------------
# Read hook input
# ---------------------------------------------------------------------------

def read_input() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}


def is_git_commit(command: str) -> bool:
    """Return True if the bash command is a git commit (not just contains 'commit' in a string)."""
    return bool(re.search(r'\bgit\s+commit\b', command))


# ---------------------------------------------------------------------------
# Get committed files
# ---------------------------------------------------------------------------

def get_committed_files(cwd: str) -> list[str]:
    """Return list of files changed in the most recent commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "--name-only"],
            capture_output=True, text=True, timeout=10, cwd=cwd
        )
        if result.returncode != 0:
            # First commit — try listing all files in HEAD instead
            result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", "HEAD"],
                capture_output=True, text=True, timeout=10, cwd=cwd
            )
        files = [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]
        # Normalize to forward slashes
        return [f.replace("\\", "/") for f in files]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(files: list[str]) -> dict:
    """Categorize changed files and return signals."""
    skills   = [f for f in files if SKILL_PATTERN.search(f)]
    agents   = [f for f in files if AGENT_PATTERN.search(f)]
    docs     = [f for f in files if ACTIVE_DOC_PAT.match(f)]
    hooks    = [f for f in files if HOOK_PATTERN.search(f)]
    scripts  = [f for f in files if SCRIPT_PATTERN.search(f)]

    return {
        "skills":  skills,
        "agents":  agents,
        "docs":    docs,
        "hooks":   hooks,
        "scripts": scripts,
        "total":   len(files),
    }


def build_message(signals: dict, files: list[str]) -> str | None:
    """Build the warning message. Returns None if nothing significant to flag."""
    lines = ["💡 POST-COMMIT CONTEXT CHECK"]

    has_ecosystem_signal = signals["skills"] or signals["agents"]
    has_context_signal   = signals["docs"]
    has_infra_signal     = signals["hooks"] or signals["scripts"]
    significant          = signals["total"] >= 3 or (has_ecosystem_signal and has_context_signal)

    # List what changed
    for f in signals["skills"]:
        lines.append(f"  ~ Skill:  {f}")
    for f in signals["agents"]:
        lines.append(f"  ~ Agent:  {f}")
    for f in signals["docs"]:
        lines.append(f"  ~ Doc:    {f}")
    for f in signals["hooks"] + signals["scripts"]:
        lines.append(f"  ~ Infra:  {f}")

    lines.append("")

    # Targeted suggestions
    suggestions = []

    if has_ecosystem_signal:
        suggestions.append(
            "→ Skill/agent changed — run ecosystem-manager to check for overlap or drift."
        )

    if has_context_signal:
        suggestions.append(
            "→ Active context updated — consider: does lessons.json need a new entry?"
        )

    if significant:
        suggestions.append(
            "→ Significant session — consider running ecosystem-manager > 'capture learnings'."
        )

    if has_infra_signal and not has_ecosystem_signal:
        suggestions.append(
            "→ Infrastructure changed — verify hook/script still aligns with CLAUDE.md rules."
        )

    if not suggestions:
        # Lightweight catch-all for any commit
        suggestions.append(
            "→ Was anything learned this session worth capturing in lessons.json?"
        )

    lines.extend(suggestions)
    lines.append("")
    lines.append("  (These are suggestions — act on what's relevant, skip what isn't.)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    hook_input = read_input()

    # Only act on git commit commands
    tool_input = hook_input.get("tool_input", {})
    command    = tool_input.get("command", "")

    if not is_git_commit(command):
        sys.exit(0)

    # Get the working directory from hook context, fall back to cwd
    cwd = hook_input.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    files = get_committed_files(cwd)
    if not files:
        sys.exit(0)  # Can't determine what changed — stay silent

    signals = analyze(files)
    message = build_message(signals, files)

    if message:
        print(message, file=sys.stderr)

    sys.exit(0)  # Always non-blocking


if __name__ == "__main__":
    main()

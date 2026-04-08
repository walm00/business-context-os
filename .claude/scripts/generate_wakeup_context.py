#!/usr/bin/env python3
"""
generate_wakeup_context.py - Generate compressed wake-up context (~200 tokens).

Reads table-of-context.md, current-state.md, and .session-diary.md to produce
a concise docs/.wake-up-context.md for instant session orientation.

Usage:
    python .claude/scripts/generate_wakeup_context.py
    python .claude/scripts/generate_wakeup_context.py --dry-run
"""

import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

YAML_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
YAML_FIELD_RE = re.compile(r'^([a-zA-Z][a-zA-Z0-9_-]*):\s*(.+)$', re.MULTILINE)
BULLET_RE = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)
SECTION_DATE_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})")


def extract_frontmatter_field(content: str, field: str) -> str:
    """Extract a single field value from YAML frontmatter."""
    match = YAML_BLOCK_RE.match(content)
    if not match:
        return ""
    yaml = match.group(1)
    for m in YAML_FIELD_RE.finditer(yaml):
        if m.group(1) == field:
            return m.group(2).strip().strip('"').strip("'")
    return ""


def extract_section_content(content: str, heading: str, max_lines: int = 3) -> list[str]:
    """Extract first N non-empty, non-comment content lines under a ## heading.
    Uses flexible matching: 'This Week' matches 'This Week's Focus'."""
    pattern = re.compile(
        r"^##\s+" + re.escape(heading) + r"[^\n]*\n(.*?)(?=\n##\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(content)
    if not match:
        return []
    section = match.group(1)
    lines = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<!--") or stripped.startswith(">"):
            continue
        lines.append(stripped)
        if len(lines) >= max_lines:
            break
    return lines


def extract_section_bullets(content: str, heading: str, max_items: int = 3) -> list[str]:
    """Extract bullet points under a ## heading. Flexible: 'This Week' matches 'This Week's Focus'."""
    pattern = re.compile(
        r"^##\s+" + re.escape(heading) + r"[^\n]*\n(.*?)(?=\n##\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(content)
    if not match:
        return []
    section = match.group(1)
    bullets = BULLET_RE.findall(section)
    return bullets[:max_items]


def extract_diary_recent(content: str, max_entries: int = 3) -> list[str]:
    """Extract last N diary entries as 'date: focus' lines."""
    entries = []
    current_date = None
    current_focus = None

    for line in content.splitlines():
        date_match = SECTION_DATE_RE.match(line)
        if date_match:
            if current_date and current_focus:
                entries.append(f"{current_date}: {current_focus}")
            current_date = date_match.group(1)
            current_focus = None
        elif current_date and not current_focus:
            # Look for **Focus:** line
            focus_match = re.match(r"\*\*Focus:\*\*\s*(.+)", line)
            if focus_match:
                current_focus = focus_match.group(1).strip()

    if current_date and current_focus:
        entries.append(f"{current_date}: {current_focus}")

    return entries[-max_entries:]


def main():
    parser = argparse.ArgumentParser(description="Generate compressed wake-up context.")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing file")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    docs = project_root / "docs"
    output_path = docs / ".wake-up-context.md"

    # --- Read sources ---
    toc_path = docs / "table-of-context.md"
    cs_path = docs / "current-state.md"
    diary_path = docs / ".session-diary.md"

    business_name = ""
    business_desc = ""
    current_phase = ""
    priorities = []
    decisions = []
    diary_entries = []

    if toc_path.is_file():
        toc = toc_path.read_text(encoding="utf-8", errors="replace")
        # Business name: try "Who We Are" section first line, then frontmatter "project" or "business" field
        who_lines = extract_section_content(toc, "Who We Are", 1)
        if who_lines:
            business_name = who_lines[0][:150]
        if not business_name:
            business_name = extract_frontmatter_field(toc, "project") or extract_frontmatter_field(toc, "business")
        # Business description: "What We Do" section first line
        what_lines = extract_section_content(toc, "What We Do", 1)
        if what_lines:
            business_desc = what_lines[0][:200]
        # Look for phase/stage
        phase_bullets = extract_section_bullets(toc, "Current Phase", 1)
        if not phase_bullets:
            phase_bullets = extract_section_bullets(toc, "Phase", 1)
        if phase_bullets:
            current_phase = phase_bullets[0]

    if cs_path.is_file():
        cs = cs_path.read_text(encoding="utf-8", errors="replace")
        priorities = extract_section_bullets(cs, "Priorities", 3)
        if not priorities:
            priorities = extract_section_bullets(cs, "This Week", 3)
        decisions = extract_section_bullets(cs, "Active Decisions", 3)
        if not decisions:
            decisions = extract_section_bullets(cs, "Decisions", 3)

    if diary_path.is_file():
        diary = diary_path.read_text(encoding="utf-8", errors="replace")
        diary_entries = extract_diary_recent(diary, 3)

    # --- Build output ---
    lines = [
        "# Wake-Up Context",
        "",
        "*Auto-generated by `python .claude/scripts/generate_wakeup_context.py` — do not edit manually.*",
        "",
    ]

    if business_name:
        line = f"**Business:** {business_name}"
        if business_desc:
            line += f" — {business_desc}"
        if current_phase:
            line += f" Phase: {current_phase}"
        lines.append(line)
        lines.append("")

    if priorities:
        lines.append("**This week:**")
        for p in priorities:
            lines.append(f"- {p}")
        lines.append("")

    if decisions:
        lines.append("**Active decisions:**")
        for d in decisions:
            lines.append(f"- {d}")
        lines.append("")

    if diary_entries:
        lines.append("**Recent sessions:**")
        for e in diary_entries:
            lines.append(f"- {e}")
        lines.append("")

    if not (business_name or priorities or decisions or diary_entries):
        lines.append("*No context sources found yet. Create table-of-context.md and current-state.md to populate this file.*")
        lines.append("")

    output = "\n".join(lines)

    if args.dry_run:
        print(output)
        print(f"\n--- {len(output)} chars, ~{len(output.split())  } words ---")
    else:
        output_path.write_text(output, encoding="utf-8")
        print(f"Generated {output_path} ({len(output)} chars, ~{len(output.split())} words)")


if __name__ == "__main__":
    main()

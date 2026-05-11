#!/usr/bin/env python3
"""
generate_wakeup_context.py - Generate compressed wake-up context (~200 tokens).

Reads table-of-context.md, current-state.md, and .session-diary.md to produce
a concise docs/.wake-up-context.md for instant session orientation.

Also surfaces a 1-line inventory from .claude/quality/context-index.json and
emits *task-driven drill-down pointers* — short hints that tell the LLM
WHEN to read the heavier orientation docs (document-index.md,
current-state.md, table-of-context.md) instead of relying on grep.

Usage:
    python .claude/scripts/generate_wakeup_context.py
    python .claude/scripts/generate_wakeup_context.py --dry-run
"""

import json
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


def wiki_summary(docs: Path) -> str:
    """Return a compact wiki-zone summary for wake-up context, or empty string."""
    wiki = docs / "_wiki"
    if not wiki.is_dir():
        return ""

    page_count = len(list((wiki / "pages").glob("*.md"))) if (wiki / "pages").is_dir() else 0
    source_count = len(list((wiki / "source-summary").glob("*.md"))) if (wiki / "source-summary").is_dir() else 0
    pending = 0
    queue = wiki / "queue.md"
    if queue.is_file():
        text = queue.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^## Pending\s*\n(.*?)(?=\n##\s|\Z)", text, re.MULTILINE | re.DOTALL)
        if match:
            pending = len([line for line in match.group(1).splitlines() if line.strip().startswith("-")])

    return f"enabled; {page_count} page(s), {source_count} source summary page(s), {pending} pending queue item(s)"


def wiki_top_clusters(docs: Path, top_n: int = 5) -> list[str]:
    """Return the top N clusters by page count in the wiki, or empty list."""
    wiki = docs / "_wiki"
    if not wiki.is_dir():
        return []
    counts: dict[str, int] = {}
    for sub in ("pages", "source-summary"):
        d = wiki / sub
        if not d.is_dir():
            continue
        for page in d.glob("*.md"):
            try:
                text = page.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            m = YAML_BLOCK_RE.match(text)
            if not m:
                continue
            for fm in YAML_FIELD_RE.finditer(m.group(1)):
                if fm.group(1) == "cluster":
                    cluster = fm.group(2).strip().strip('"').strip("'")
                    if cluster:
                        counts[cluster] = counts.get(cluster, 0) + 1
                    break
    if not counts:
        return []
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [name for name, _count in ranked[:top_n]]


def context_inventory(project_root: Path) -> str:
    """Return a 1-line inventory from context-index.json, or empty string."""
    idx_path = project_root / ".claude" / "quality" / "context-index.json"
    if not idx_path.is_file():
        return ""
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    zones = (idx.get("summaries") or {}).get("zones") or {}
    active = zones.get("active", 0)
    inbox = zones.get("inbox", 0)
    planned = zones.get("planned", 0)
    archive = zones.get("archive", 0)
    wiki_pages = zones.get("wiki-pages", 0)
    wiki_src = zones.get("wiki-source-summary", 0)
    parts = [f"{active} active"]
    if inbox:
        parts.append(f"{inbox} inbox")
    if planned:
        parts.append(f"{planned} planned")
    if archive:
        parts.append(f"{archive} archive")
    wiki_total = wiki_pages + wiki_src
    if wiki_total:
        parts.append(f"{wiki_total} wiki")
    counts = idx.get("counts") or {}
    issues = []
    if counts.get("missing_required"):
        issues.append(f"{counts['missing_required']} missing required fields")
    if counts.get("warnings"):
        issues.append(f"{counts['warnings']} warnings")
    line = "**Inventory:** " + ", ".join(parts)
    if issues:
        line += " · " + ", ".join(issues)
    return line


def drill_down_pointers(docs: Path) -> list[str]:
    """Task-driven hints: when to drill into the heavier orientation docs.

    Each pointer appears only if its target file exists, so a fresh repo
    (no document-index.md yet) doesn't get nagged with broken pointers.
    """
    pointers: list[str] = []
    if (docs / "document-index.md").is_file():
        pointers.append(
            "- **Answering a business question, or adding / editing a data "
            "point?** Read `docs/document-index.md` first — it owns the "
            "topic-to-file map. Identify the topic → find the owning data "
            "point → read it → THEN answer or edit. Don't answer business "
            "questions cold."
        )
    if (docs / "current-state.md").is_file():
        pointers.append(
            "- **Strategy / \"what's true right now\"?** Read "
            "`docs/current-state.md` — that's the canonical source for "
            "active priorities, decisions, and recent changes."
        )
    if (docs / "table-of-context.md").is_file():
        pointers.append(
            "- **Architecture-level navigation / where does X live?** Read "
            "`docs/table-of-context.md` — domain map of the whole context."
        )
    return pointers


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
    wiki_status = ""

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

    wiki_status = wiki_summary(docs)

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

    if wiki_status:
        lines.append(f"**Wiki:** {wiki_status}")
        # Schema 1.2 — authority hierarchy framing.
        # Explicit anti-pattern: do NOT add "always check the wiki first".
        lines.append(
            "**Wiki authority:** `docs/*.md` is canonical. `_wiki/pages/` "
            "(authority: canonical-process) is operational truth. "
            "`_wiki/source-summary/` is reference-only — if it conflicts "
            "with active context, active wins."
        )
        clusters = wiki_top_clusters(docs, top_n=5)
        if clusters:
            lines.append(f"**Wiki topics:** {', '.join(clusters)}")
        lines.append("")

    inventory_line = context_inventory(project_root)
    if inventory_line:
        lines.append(inventory_line)
        lines.append("")

    pointers = drill_down_pointers(docs)
    if pointers:
        lines.append("**Drill into when relevant:**")
        lines.extend(pointers)
        lines.append(
            "- **Searching across zones?** Use `/context search <query>` — "
            "BM25 over the canonical index, no grep."
        )
        lines.append(
            "- **Full task→retrieval map:** see `CLAUDE.md` → "
            "**Retrieval Playbook** (the structured way to find context "
            "for any task — leverages frontmatter, authority tiers, "
            "`builds-on:`, and the wiki / collections structure)."
        )
        lines.append("")

    if not (business_name or priorities or decisions or diary_entries or wiki_status or inventory_line):
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

#!/usr/bin/env python3
"""
prune_diary.py - Remove session diary entries older than 30 days.

Reads docs/.session-diary.md, parses ## YYYY-MM-DD section headers,
drops sections older than the retention period, rewrites the file.

Usage:
    python .claude/scripts/prune_diary.py              # Prune (default 30 days)
    python .claude/scripts/prune_diary.py --days 14    # Custom retention
    python .claude/scripts/prune_diary.py --dry-run    # Preview only
"""

import re
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_RETENTION_DAYS = 30
SECTION_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})")

# Everything before the first ## entry is the header (preserved always)
ENTRIES_MARKER = "<!-- ENTRIES BELOW"


def main():
    parser = argparse.ArgumentParser(description="Prune old session diary entries.")
    parser.add_argument("--days", type=int, default=DEFAULT_RETENTION_DAYS,
                        help=f"Retention period in days (default: {DEFAULT_RETENTION_DAYS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be pruned")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    diary_path = project_root / "docs" / ".session-diary.md"

    if not diary_path.is_file():
        print("Session diary not found. Nothing to prune.")
        sys.exit(0)

    content = diary_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    cutoff = datetime.now() - timedelta(days=args.days)

    # Split into header and entries
    header_lines = []
    entry_sections = []  # list of (date_str, lines)
    current_section = None

    for line in lines:
        match = SECTION_RE.match(line)
        if match:
            if current_section:
                entry_sections.append(current_section)
            current_section = (match.group(1), [line])
        elif current_section:
            current_section[1].append(line)
        else:
            header_lines.append(line)

    if current_section:
        entry_sections.append(current_section)

    # Filter entries
    kept = []
    pruned = 0
    for date_str, section_lines in entry_sections:
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            kept.append((date_str, section_lines))
            continue

        if entry_date < cutoff:
            if args.dry_run:
                print(f"  Would prune: {date_str}")
            pruned += 1
        else:
            kept.append((date_str, section_lines))

    if pruned == 0:
        print("Nothing to prune. All entries within retention period.")
        sys.exit(0)

    if args.dry_run:
        print(f"\nWould prune {pruned} entries. {len(kept)} kept.")
        sys.exit(0)

    # Rewrite file
    with open(diary_path, "w", encoding="utf-8") as f:
        f.writelines(header_lines)
        for _, section_lines in kept:
            f.writelines(section_lines)

    print(f"Pruned {pruned} entries older than {args.days} days. {len(kept)} kept.")


if __name__ == "__main__":
    main()

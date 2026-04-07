#!/usr/bin/env python3
"""
prune_sessions.py - Delete session capture files older than 30 days.

Scans docs/_inbox/sessions/ for .md files, parses the date from the filename
(YYYY-MM-DD prefix), and deletes any older than the retention period.

Usage:
    python .claude/scripts/prune_sessions.py              # Prune (default 30 days)
    python .claude/scripts/prune_sessions.py --days 14    # Custom retention
    python .claude/scripts/prune_sessions.py --dry-run    # Preview only
"""

import os
import re
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_RETENTION_DAYS = 30
DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def main():
    parser = argparse.ArgumentParser(description="Prune old session capture files.")
    parser.add_argument("--days", type=int, default=DEFAULT_RETENTION_DAYS,
                        help=f"Retention period in days (default: {DEFAULT_RETENTION_DAYS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be deleted")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    sessions_dir = project_root / "docs" / "_inbox" / "sessions"

    if not sessions_dir.is_dir():
        print(f"Sessions directory not found: {sessions_dir}")
        sys.exit(0)

    cutoff = datetime.now() - timedelta(days=args.days)
    pruned = 0
    kept = 0

    for filepath in sorted(sessions_dir.glob("*.md")):
        match = DATE_PREFIX_RE.match(filepath.name)
        if not match:
            kept += 1
            continue

        try:
            file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            kept += 1
            continue

        if file_date < cutoff:
            if args.dry_run:
                print(f"  Would delete: {filepath.name}")
            else:
                filepath.unlink()
                print(f"  Deleted: {filepath.name}")
            pruned += 1
        else:
            kept += 1

    action = "Would prune" if args.dry_run else "Pruned"
    print(f"\n{action} {pruned} file(s) older than {args.days} days. {kept} kept.")


if __name__ == "__main__":
    main()

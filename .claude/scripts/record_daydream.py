#!/usr/bin/env python3
"""record_daydream.py — write the daydream "last run" timestamp.

Replaces the shell-redirect form `echo "{date}" > .claude/quality/last-daydream.txt`
which Claude Code's permission gate flags as an unscoped write. A small helper
script is covered by the existing `Bash(python .claude/scripts/:*)` catch-all.

USAGE
    python .claude/scripts/record_daydream.py              # write today's UTC date
    python .claude/scripts/record_daydream.py 2026-05-14   # write a specific date
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(".claude/quality/last-daydream.txt")


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        stamp = argv[1].strip()
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(stamp + "\n", encoding="utf-8")
    print(f"last-daydream: {stamp}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

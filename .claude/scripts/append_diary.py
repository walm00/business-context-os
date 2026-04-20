#!/usr/bin/env python3
"""Append one JSON line to .claude/hook_state/schedule-diary.jsonl.

Hard-coded target path — the script refuses to write anywhere else, so the
permission allowlist entry `Bash(python .claude/scripts/append_diary.py:*)`
stays narrow. Creates the hook_state directory on first run.

Usage: python .claude/scripts/append_diary.py '<json-object>'
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DIARY_REL = Path(".claude/hook_state/schedule-diary.jsonl")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: append_diary.py '<json-object>'", file=sys.stderr)
        return 2

    try:
        entry = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"invalid JSON: {e}", file=sys.stderr)
        return 2

    if not isinstance(entry, dict):
        print("entry must be a JSON object", file=sys.stderr)
        return 2

    target = Path.cwd() / DIARY_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

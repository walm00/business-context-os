"""Boundary-aware CLAUDE.md management for BCOS.

The shipped CLAUDE.md template wraps the framework-managed portion in
`<!-- BCOS:CORE:START vX.Y.Z -->` ... `<!-- BCOS:CORE:END -->` markers.

`ensure_bcos_core_block` is the single entry point shared by:
  - install.sh           (fresh install or re-run on existing repo)
  - update.py            (framework refresh)
  - context-onboarding   (self-heal at session start; handles the git-clone case
                          where install.sh was never run)

Behavior:
  * Target file missing      -> write the shipped template as-is.
  * Target has CORE markers  -> replace the block between markers with the
                                shipped CORE. If the previous CORE differed,
                                save it to `recovery_path` first so the user
                                can recover any unintended hand-edits.
  * Target lacks CORE markers -> append the CORE block to the END of the file,
                                preserving everything above.

Idempotent. Safe to re-run.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CORE_START_RE = re.compile(r"<!--\s*BCOS:CORE:START(?:\s+v\S+)?\s*-->")
CORE_END_RE = re.compile(r"<!--\s*BCOS:CORE:END\s*-->")


def extract_core_block(text: str) -> str | None:
    """Return the CORE block (markers included) from text, or None if absent.

    Uses the LAST `BCOS:CORE:END` marker after the start marker. The CORE
    block itself contains a self-referential instruction that mentions the
    marker text in backticks (the "integrity check" line), and a naive
    first-match approach truncates the block there — silently dropping
    everything below it on update.
    """
    m_start = CORE_START_RE.search(text)
    if not m_start:
        return None
    end_matches = list(CORE_END_RE.finditer(text, m_start.end()))
    if not end_matches:
        return None
    m_end = end_matches[-1]
    return text[m_start.start():m_end.end()]


def _splice_at_end(target_text: str, core_block: str) -> str:
    if not target_text:
        return core_block + "\n"
    if target_text.endswith("\n\n"):
        sep = ""
    elif target_text.endswith("\n"):
        sep = "\n"
    else:
        sep = "\n\n"
    return target_text + sep + core_block + "\n"


def ensure_bcos_core_block(
    target_claude_md: Path | str,
    source_claude_md: Path | str,
    recovery_path: Path | str | None = None,
) -> dict:
    """Ensure target CLAUDE.md contains the current CORE block from source.

    Returns:
        {"action": "created" | "replaced" | "spliced" | "unchanged",
         "recovered_to": <str path> | None}
    """
    target = Path(target_claude_md)
    source = Path(source_claude_md)

    source_text = source.read_text(encoding="utf-8")
    new_core = extract_core_block(source_text)
    if new_core is None:
        raise ValueError(
            f"Source CLAUDE.md at {source} has no BCOS:CORE markers"
        )

    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source_text, encoding="utf-8")
        return {"action": "created", "recovered_to": None}

    target_text = target.read_text(encoding="utf-8")
    existing_core = extract_core_block(target_text)

    if existing_core is None:
        new_text = _splice_at_end(target_text, new_core)
        target.write_text(new_text, encoding="utf-8")
        return {"action": "spliced", "recovered_to": None}

    if existing_core == new_core:
        return {"action": "unchanged", "recovered_to": None}

    recovered_to = None
    if recovery_path is not None:
        rp = Path(recovery_path)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(existing_core + "\n", encoding="utf-8")
        recovered_to = str(rp)

    new_text = target_text.replace(existing_core, new_core, 1)
    target.write_text(new_text, encoding="utf-8")
    return {"action": "replaced", "recovered_to": recovered_to}


def _main() -> int:
    ap = argparse.ArgumentParser(
        description="Ensure BCOS:CORE block in target CLAUDE.md"
    )
    ap.add_argument("--target", required=True, help="Path to user's CLAUDE.md")
    ap.add_argument("--source", required=True, help="Path to shipped CLAUDE.md template")
    ap.add_argument("--recovery", default=None,
                    help="Optional path to write previous CORE block on replacement")
    args = ap.parse_args()

    try:
        result = ensure_bcos_core_block(args.target, args.source, args.recovery)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"action={result['action']}")
    if result["recovered_to"]:
        print(f"recovered_to={result['recovered_to']}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())

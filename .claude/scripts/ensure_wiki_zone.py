#!/usr/bin/env python3
"""
ensure_wiki_zone.py — idempotent helper for substrate-readiness guarantees.

The wiki is BCOS's universal long-form / cross-cutting content destination per
plugin-storage-contract.md Rule 2. Plugin install scripts (`install_here.py`)
need a ready `docs/_wiki/.schema.d/` directory to drop their schema fragments
into; without an initialized wiki zone, the fragment lands orphaned and breaks
the wiki tooling's fragment-merge contract.

This helper is the plugin-install hook: idempotent, headless, no-op on existing
zones. Internally it wraps `cmd_wiki_init.py` with defaults.

CONTRACT:
  * Exit 0 if zone exists OR was successfully scaffolded.
  * Exit non-zero only if scaffolding failed (write-protected fs, missing
    framework templates, etc.).
  * Stdout: structured JSON ({"ok": bool, "status": str, "notes": str, ...})
    suitable for plugin install scripts to parse.

USAGE FROM PLUGIN install_here.py:

    import subprocess
    import json
    from pathlib import Path

    bcos_py = Path(".claude/bin/python3")  # or resolved via BCOS_PY
    result = subprocess.run(
        [str(bcos_py), ".claude/scripts/ensure_wiki_zone.py"],
        capture_output=True, text=True, check=False,
    )
    payload = json.loads(result.stdout)
    if not payload["ok"]:
        raise RuntimeError(f"Cannot initialize wiki zone: {payload['notes']}")

    # Safe to write _wiki/.schema.d/<plugin>.yml now.

USAGE FROM SHELL:

    .claude/bin/python3 .claude/scripts/ensure_wiki_zone.py
    .claude/bin/python3 .claude/scripts/ensure_wiki_zone.py --display-name "My Plugin"
    .claude/bin/python3 .claude/scripts/ensure_wiki_zone.py --dry-run

NON-INTERACTIVE BY DESIGN:
This script never prompts. It assumes the caller is automation (plugin install,
CI, dispatcher). For the interactive scaffold path, use `/wiki init` in chat.
For the user-prompted auto-init path, the bcos-wiki SKILL.md Guard handles
that via AskUserQuestion.

See:
  * docs/_bcos-framework/architecture/plugin-storage-contract.md (Rule 2)
  * .claude/scripts/cmd_wiki_init.py (the underlying scaffold backend)
  * .claude/skills/bcos-wiki/init.md (interactive flow + --defaults docs)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# Import cmd_wiki_init from the sibling script.
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "cmd_wiki_init",
    _HERE / "cmd_wiki_init.py",
)
_cmd_wiki_init = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cmd_wiki_init)


def ensure(*, root: Path | None = None, dry_run: bool = False,
           display_name: str | None = None) -> dict:
    """Idempotent substrate-readiness check + scaffold.

    Returns the same shape as cmd_wiki_init.init():
        {"ok": bool, "status": "green"|"red", "notes": str,
         "created": [paths], "no_op": bool?, "display_name": str}
    """
    result = _cmd_wiki_init.init(
        root=root,
        dry_run=dry_run,
        display_name=display_name,
    )
    # Tag the response so plugin callers can confirm they hit ensure_wiki_zone,
    # not a different scaffold path (defensive — survives future refactors).
    result["entry_point"] = "ensure_wiki_zone.py"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ensure docs/_wiki/ is initialized (idempotent).")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be created; do not write")
    parser.add_argument("--display-name", default=None,
                        help="override display name (default: git repo basename)")
    args = parser.parse_args(argv)
    result = ensure(dry_run=args.dry_run, display_name=args.display_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

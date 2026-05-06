#!/usr/bin/env python3
"""
cmd_wiki_lint.py — wiki-zone health check (wraps wiki_schema.py validate).

User-triggered command (mirrors `/wiki lint` chat path). Pure wrapper —
no LLM, no fetching. Returns a JSON line with status + raw findings.

CLI:
    python .claude/scripts/cmd_wiki_lint.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def repo_root() -> Path:
    import os
    override = os.environ.get("BCOS_REPO_ROOT", "").strip()
    if override:
        p = Path(override).expanduser().resolve()
        if p.is_dir():
            return p
    return _HERE.parents[1]


def lint(root: Path | None = None) -> dict:
    r = root or repo_root()
    if not (r / "docs" / "_wiki").is_dir():
        return {
            "ok": True, "status": "green",
            "notes": "No wiki zone — nothing to lint.",
            "findings": [],
        }

    schema_script = r / ".claude" / "scripts" / "wiki_schema.py"
    if not schema_script.is_file():
        return {
            "ok": False, "status": "red",
            "notes": f"wiki_schema.py not found at {schema_script}.",
        }

    proc = subprocess.run(
        [sys.executable, str(schema_script), "validate"],
        cwd=str(r), capture_output=True, text=True, timeout=30, check=False,
    )
    output = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    findings = [ln for ln in output.splitlines() if ln.strip() and not ln.startswith(("OK", "."))]

    if proc.returncode == 0:
        status = "green"
        notes = output.splitlines()[-1] if output else "Wiki schema validates cleanly."
    else:
        status = "amber" if findings else "red"
        notes = f"Schema validation reported {len(findings)} issue(s)."

    return {
        "ok": proc.returncode == 0,
        "status": status,
        "notes": notes,
        "findings": findings,
        "raw_stdout": output,
        "raw_stderr": err if err else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    args = parser.parse_args(argv)
    result = lint()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

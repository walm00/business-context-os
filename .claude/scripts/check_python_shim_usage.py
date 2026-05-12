#!/usr/bin/env python3
"""check_python_shim_usage.py — enforce the BCOS shim convention.

Scans BCOS-controlled files for bare `python3 <script>` invocations that
should be using the .claude/bin/python3 shim instead. Exits non-zero with a
list of offenders so pre-commit and CI can block.

Why this exists: on Windows, bare `python3` resolves to the Microsoft Store
stub and exits 49 silently. The shim at .claude/bin/python3 bypasses that via
`py -3`. Every BCOS-controlled hook/script/settings.json command MUST use the
shim path so the framework works on every supported platform.

Scope (intentionally narrow to avoid false positives):
  - Scans only files we know should obey the convention:
    .claude/hooks/*.sh, .claude/hooks/*.py with shell invocations,
    .claude/settings.json (hook command strings),
    .codex/hooks.json, .codex/hooks/*.sh
  - Skips comments (# / // / /*).
  - Skips lines that already contain ".claude/bin/python3".
  - Skips fallback lines that explicitly check for the shim's absence
    (lines containing both 'BCOS_PY=' and '"python3"').
  - Skips shebangs (#!/usr/bin/env python3 is fine — never invoked as
    `python3 file.py`).

Exit codes:
  0 — clean, no violations
  1 — at least one violation; details printed to stdout
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]


def _scoped_files() -> Iterable[Path]:
    """Yield files whose `python3` invocations are subject to the convention."""
    scopes = [
        REPO_ROOT / ".claude" / "hooks",
        REPO_ROOT / ".claude" / "settings.json",
        REPO_ROOT / ".codex" / "hooks",
        REPO_ROOT / ".codex" / "hooks.json",
    ]
    for s in scopes:
        if s.is_file():
            yield s
        elif s.is_dir():
            for p in s.rglob("*"):
                if p.is_file() and p.suffix in {".sh", ".json"}:
                    yield p


# Match a bare `python3` followed by a path-like argument referencing a
# BCOS-controlled location. This is intentionally narrow — we only want to
# catch invocations that should be using the shim. `python3 -c "..."` (a
# detection probe), `python3 --version`, and string-literal references in
# error messages won't match.
_INVOCATION_RE = re.compile(
    r'(?<![A-Za-z0-9._/\\-])python3\s+'
    r'(?:'
    r'[\'"]?\$CLAUDE_PROJECT_DIR'    # "$CLAUDE_PROJECT_DIR/.claude/..."
    r'|[\'"]?\.\.?/'                  # ./path or ../path
    r'|[\'"]?\.claude/'               # .claude/scripts/...
    r'|[\'"]?\.codex/'                # .codex/hooks/...
    r')'
)


def _is_comment_line(line: str, ext: str) -> bool:
    s = line.lstrip()
    if ext == ".json":
        # JSON has no comments; values are strings — never treat as comment.
        return False
    return s.startswith("#") or s.startswith("//") or s.startswith("/*")


def _is_shebang(line: str) -> bool:
    return line.startswith("#!")


def _is_shim_fallback(line: str) -> bool:
    """Allow the transition-fallback pattern:
       [ -x "$BCOS_PY" ] || BCOS_PY="python3"
       command -v python3 && python3 -c ...
    These lines define the fallback path itself; the rest of the file uses
    "$BCOS_PY". The fallback is sanctioned, not a violation.
    """
    # Lines that ARE the resolution logic (set BCOS_PY) or the fallback test.
    if 'BCOS_PY=' in line:
        return True
    # The detection command `command -v python3` is fine.
    if 'command -v python3' in line:
        return True
    # The exec line inside the POSIX shim itself.
    if 'exec /usr/bin/env python3' in line:
        return True
    return False


def _is_settings_allowlist_pattern(path: Path, line: str) -> bool:
    """`.claude/settings.json` allowlist patterns (`"Bash(python3 ...)"`)
    intentionally allow the bare form for backward compatibility during the
    transition. They're configuration, not invocations. Skip them.
    """
    if path.name != "settings.json":
        return False
    s = line.strip()
    # Allowlist entries are strings like:  "Bash(python3 .claude/scripts/...)"
    return s.startswith('"Bash(python3 ') or s.startswith('"Bash(python ')


def scan() -> list[tuple[Path, int, str]]:
    violations: list[tuple[Path, int, str]] = []
    for path in _scoped_files():
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        ext = path.suffix
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _is_shebang(line):
                continue
            if _is_comment_line(line, ext):
                continue
            if ".claude/bin/python3" in line:
                continue
            if _is_shim_fallback(line):
                continue
            if _is_settings_allowlist_pattern(path, line):
                continue
            if _INVOCATION_RE.search(line):
                violations.append((path, lineno, line.rstrip()))
    return violations


def main() -> int:
    violations = scan()
    if not violations:
        print("OK: no bare python3 invocations in BCOS-controlled files.")
        return 0

    print("FAIL: bare `python3` invocations found in BCOS-controlled files.")
    print("Every hook/script/settings.json command must use the shim:")
    print('  "$CLAUDE_PROJECT_DIR/.claude/bin/python3"   (Claude Code hook context)')
    print('  "$BCOS_PY"                                  (shell hooks with resolution block)')
    print("")
    for path, lineno, line in violations:
        try:
            rel = path.relative_to(REPO_ROOT)
        except ValueError:
            rel = path
        print(f"  {rel}:{lineno}: {line}")
    print("")
    print("If this is intentional (e.g. resolution fallback), make sure")
    print("the line contains 'BCOS_PY=' or 'command -v python3' so the")
    print("scanner recognizes it as the sanctioned transition pattern.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

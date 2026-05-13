#!/usr/bin/env python3
"""Helpers for BCOS scheduled-task working-directory verification.

Used by `context-onboarding` Step 6e (registration-time cwd check)
to extract the `Working directory:` directive from a stored task
prompt body and compare it against the expected repo path.

Mirrors the same predicate used by `bcos-umbrella`'s
`audit_scheduled_task_cwd.py` (portfolio-level audit). Kept here in
the BCOS repo so context-onboarding has no runtime dependency on
the umbrella plugin — works the same whether the host is umbrella-aware
or standalone.

Both functions are pure (no I/O) so they unit-test cleanly without
fixtures.
"""

from __future__ import annotations

import os
import re

# `Working directory:` directive, case-insensitive key, value runs to EOL.
_WD_LINE = re.compile(r"^working directory:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def parse_working_directory(prompt_body: str) -> str | None:
    """Extract the value of the first `Working directory:` directive in
    a stored scheduled-task prompt body, or None if absent.

    Whitespace around the value is stripped. Subsequent directives (e.g.
    in 'IMPORTANT: Working directory:' restatement clauses) are ignored
    — the first match is canonical."""
    m = _WD_LINE.search(prompt_body)
    if not m:
        return None
    return m.group(1).strip()


def paths_equivalent(a: str, b: str) -> bool:
    """Compare two filesystem paths for equivalence, ignoring separator
    style (forward vs backslash). Does NOT resolve symlinks or
    canonicalize — that's the caller's job if they care."""
    return os.path.normcase(a.replace("\\", "/")) == os.path.normcase(b.replace("\\", "/"))

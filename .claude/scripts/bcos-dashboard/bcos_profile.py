"""
profile.py — Dashboard helpers for the BCOS repo profile (`shared` | `personal`).

Mirrors `.claude/scripts/set_profile.sh` so the dashboard can read and
toggle the profile without shelling out to bash. Both surfaces write to
the same files (`.claude/bcos-profile` + `.gitignore`) and use the same
template (`.claude/templates/gitignore.template`), so swapping between
the bash CLI and the dashboard toggle is fully interchangeable.

Profiles:
- `shared`   — BCOS dropped into a multi-tenant/team repo. Runtime
               artifacts (sessions, lessons, diary, digest, wake-up,
               doc-index) are gitignored. (Default.)
- `personal` — BCOS as a personal knowledge repo. Knowledge artifacts
               ARE tracked so they sync across machines. Only secrets
               and machine-local files stay ignored.

Public surface:
    read_profile() -> str
    set_profile(profile, *, dry_run=False) -> dict
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from single_repo import REPO_ROOT  # noqa: E402

PROFILE_FILE = REPO_ROOT / ".claude" / "bcos-profile"
GITIGNORE = REPO_ROOT / ".gitignore"
TEMPLATE = REPO_ROOT / ".claude" / "templates" / "gitignore.template"

VALID_PROFILES = ("shared", "personal")
DEFAULT_PROFILE = "shared"

DESCRIPTIONS = {
    "shared": (
        "Drop-in for a team repo. Runtime artifacts (session diary, "
        "lessons, daily digest, wake-up context, document index) are "
        "gitignored to keep the host codebase clean."
    ),
    "personal": (
        "Personal knowledge repo. Knowledge artifacts ARE tracked so "
        "they sync across machines. Only secrets and machine-local "
        "files stay ignored."
    ),
}


def read_profile() -> str:
    """Current profile (defaults to 'shared' when the marker file is missing)."""
    if not PROFILE_FILE.is_file():
        return DEFAULT_PROFILE
    try:
        text = PROFILE_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return DEFAULT_PROFILE
    if text not in VALID_PROFILES:
        return DEFAULT_PROFILE
    return text


def _render_gitignore(profile: str) -> str:
    """Strip the inactive profile block from the template.

    Section headers in the template:
      # === ALWAYS ===            (always included)
      # === SHARED ONLY ===       (only when profile == 'shared')
      # === PERSONAL ONLY ===     (only when profile == 'personal')

    Mirrors the awk script in set_profile.sh exactly.
    """
    if not TEMPLATE.is_file():
        raise FileNotFoundError(f"Template not found at {TEMPLATE}")

    out_lines: list[str] = []
    skipping = False
    for raw in TEMPLATE.read_text(encoding="utf-8").splitlines():
        if raw.startswith("# === ALWAYS ==="):
            skipping = False
            out_lines.append(raw)
            continue
        if raw.startswith("# === SHARED ONLY ==="):
            skipping = profile != "shared"
            out_lines.append(raw)
            continue
        if raw.startswith("# === PERSONAL ONLY ==="):
            skipping = profile != "personal"
            out_lines.append(raw)
            continue
        if not skipping:
            out_lines.append(raw)

    rendered = "\n".join(out_lines)

    header = (
        "# Generated from .claude/templates/gitignore.template\n"
        f"# Profile: {profile}\n"
        "# Re-generate with: bash .claude/scripts/set_profile.sh <shared|personal>\n"
        "# DO NOT edit by hand — edit the template instead.\n"
    )
    return header + "\n" + rendered + "\n"


def set_profile(profile: str, *, dry_run: bool = False) -> dict:
    """Switch the repo profile. Idempotent.

    On success returns:
        {
          ok: True,
          before: "shared",                  # previous profile
          after:  "personal",                # new profile (== arg)
          gitignore_changed: bool,           # whether .gitignore content moved
          dry_run: bool,
        }

    On failure returns `{ok: False, error: str, remediation: {...}?}` with a
    structured remediation hint when the cause is a missing template — same
    shape the dashboard's _remediationToast() helper renders.
    """
    if profile not in VALID_PROFILES:
        return {
            "ok": False,
            "error": f"Invalid profile {profile!r}. Must be one of {VALID_PROFILES}.",
        }

    before = read_profile()

    if not TEMPLATE.is_file():
        return {
            "ok": False,
            "status": "missing_template",
            "error": f"Template not found at {TEMPLATE.relative_to(REPO_ROOT)}.",
            "remediation": {
                "summary": "Re-fetch the framework templates:",
                "command": "python .claude/scripts/update.py",
                "then": "Reload this page and try again.",
            },
        }

    try:
        new_content = _render_gitignore(profile)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Couldn't render template: {type(exc).__name__}: {exc}"}

    existing = GITIGNORE.read_text(encoding="utf-8") if GITIGNORE.is_file() else ""
    gitignore_changed = existing != new_content

    if dry_run:
        return {
            "ok": True,
            "before": before,
            "after": profile,
            "gitignore_changed": gitignore_changed,
            "dry_run": True,
        }

    try:
        # Write atomically — temp-file + rename so a crash doesn't leave
        # a half-written .gitignore.
        if gitignore_changed:
            tmp = GITIGNORE.with_suffix(".tmp")
            tmp.write_text(new_content, encoding="utf-8")
            tmp.replace(GITIGNORE)
        PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_FILE.write_text(profile + "\n", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Write failed: {type(exc).__name__}: {exc}"}

    return {
        "ok": True,
        "before": before,
        "after": profile,
        "gitignore_changed": gitignore_changed,
        "dry_run": False,
    }


def collect_profile() -> dict:
    """Cockpit/settings panel data for the profile section."""
    current = read_profile()
    return {
        "current": current,
        "available": list(VALID_PROFILES),
        "descriptions": DESCRIPTIONS,
        "template_exists": TEMPLATE.is_file(),
        "_severity": "ok",
    }

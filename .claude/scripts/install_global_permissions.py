#!/usr/bin/env python3
"""Mirror this project's BCOS permission allowlist into ~/.claude/settings.json.

When BCOS schedules and workflows span multiple repos (umbrella + sub-repos,
portfolio mode, sibling-repo writes), the project-local `.claude/settings.json`
isn't enough — it only applies in this one project. The cron task fires fine,
but the moment a job tries to read or write a sibling repo, Claude Code asks
for approval and the unattended session stalls.

This script copies the BCOS allowlist into the user-global
`~/.claude/settings.json` so the same rules apply across every project on the
machine. The merge is **additive**: existing user-level entries are never
removed, replaced, or reordered. Re-running the script is idempotent.

USAGE
    python .claude/scripts/install_global_permissions.py            # apply
    python .claude/scripts/install_global_permissions.py --dry-run  # preview

WHAT GETS COPIED
    Every entry under .claude/settings.json -> permissions.allow.

WHAT DOES NOT GET COPIED
    Hooks (project-specific by design), denies, and any other key.

SAFETY NOTES
    User-level rules apply globally. A rule like
        Bash(python .claude/scripts/refresh_ecosystem_state.py:*)
    will allow that command in ANY repo on this machine that has a script of
    that name. If you only trust BCOS-installed repos, this is what you want
    (the script names are unambiguous and BCOS-owned). If you ever check out
    an untrusted repo with the same script names, revoke that rule from
    `~/.claude/settings.json`.

    The script never adds blanket Bash/Edit/Write or destructive git rules
    because the project-level settings.json never had them in the first place.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _project_settings_path() -> Path:
    """Resolve .claude/settings.json relative to this script."""
    return Path(__file__).resolve().parent.parent / "settings.json"


def _user_settings_path() -> Path:
    """Resolve ~/.claude/settings.json regardless of platform."""
    return Path.home() / ".claude" / "settings.json"


def _additive_merge_allow(project_allow: list[str], user_settings: dict) -> tuple[int, list[str]]:
    """Append project_allow rules to user_settings.permissions.allow if missing.

    Returns (count_added, rules_added).
    """
    perms = user_settings.setdefault("permissions", {})
    user_allow = perms.setdefault("allow", [])
    existing = set(user_allow)
    added = []
    for rule in project_allow:
        if rule not in existing:
            user_allow.append(rule)
            existing.add(rule)
            added.append(rule)
    return len(added), added


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Mirror the BCOS project allowlist into ~/.claude/settings.json so "
            "scheduled jobs that span multiple repos run without permission prompts."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be added without writing.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the summary line.",
    )
    args = parser.parse_args(argv)

    project_path = _project_settings_path()
    user_path = _user_settings_path()

    if not project_path.exists():
        print(f"Error: project settings not found at {project_path}", file=sys.stderr)
        return 1

    try:
        project_settings = json.loads(project_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: project settings.json is malformed: {exc}", file=sys.stderr)
        return 1

    project_allow = project_settings.get("permissions", {}).get("allow", [])
    if not project_allow:
        print("Project settings.json has no permissions.allow block — nothing to mirror.")
        return 0

    if user_path.exists():
        try:
            user_settings = json.loads(user_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(
                f"Error: ~/.claude/settings.json is malformed: {exc}\n"
                f"Fix it (or delete it to let Claude Code recreate it) and re-run.",
                file=sys.stderr,
            )
            return 1
    else:
        user_settings = {}

    count, added = _additive_merge_allow(project_allow, user_settings)

    if not args.quiet and count > 0:
        print(f"Would add {count} entr{'y' if count == 1 else 'ies'} to {user_path}:")
        for rule in added:
            print(f"  + {rule}")
    elif not args.quiet:
        print(f"All {len(project_allow)} project allow rules are already present in {user_path}.")

    if args.dry_run:
        print()
        print("(--dry-run: no changes written.)")
        return 0

    if count == 0:
        return 0

    user_path.parent.mkdir(parents=True, exist_ok=True)
    user_path.write_text(
        json.dumps(user_settings, indent=2) + "\n",
        encoding="utf-8",
    )
    print()
    print(f"Done. {count} entr{'y' if count == 1 else 'ies'} merged into {user_path}.")
    print("Cross-repo BCOS workflows will now run without per-repo permission prompts.")
    print()
    print("To revoke later: open ~/.claude/settings.json and remove the rules you no longer want.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

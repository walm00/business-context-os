#!/usr/bin/env python3
"""
reset_permissions_marker.py — drop the `_bcosManagedPermissions` key from
`.claude/settings.json`. Use this if a tombstone has trapped a rule you
want to re-enable.

CONTEXT

The marker-aware writer (`merge_settings_json` v2+) tracks every BCOS-shipped
rule in `_bcosManagedPermissions`. If you remove a rule from `permissions.allow`,
the reconciler interprets this as "user explicitly removed; never re-add"
(state RESPECT_USER_REMOVAL — a tombstone). That's usually what you want.

But if you change your mind — you want the rule back — the writer won't
re-add it on the next `update.py` because the tombstone is sticky. This
script is the escape hatch: drop the marker entirely, and the next
`update.py` re-ADOPTs every currently-shipped rule that's in `allow`.

USAGE

    python .claude/scripts/reset_permissions_marker.py            # apply
    python .claude/scripts/reset_permissions_marker.py --dry-run  # preview

CONTRACT

  - Only removes `_bcosManagedPermissions`. Other marker keys
    (`_bcosManagedUmbrellaPermissions`, etc.) are untouched.
  - `permissions.allow` is NOT modified — your current set of active
    rules stays exactly as it is.
  - Idempotent: if the key is already absent, the script reports "no
    marker present" and exits 0.

See also:
  - docs/_bcos-framework/architecture/permissions-catalog.md
  - .claude/scripts/_settings_reconciler.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _settings_reconciler import MARKER_KEY, SettingsReconciler  # noqa: E402


def _resolve_settings_path() -> Path:
    """Resolve .claude/settings.json relative to the project root."""
    # Script lives at .claude/scripts/. Project root is two parents up.
    return _HERE.parent.parent / ".claude" / "settings.json"


def main(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Drop the `_bcosManagedPermissions` marker key from "
            ".claude/settings.json so the next update.py re-ADOPTs all "
            "currently-shipped rules."
        ),
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would change without writing.")
    args = ap.parse_args(argv)

    settings_path = _resolve_settings_path()
    if not settings_path.is_file():
        print(f"settings.json not found at {settings_path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"settings.json is malformed: {exc}", file=sys.stderr)
        return 1

    if MARKER_KEY not in data:
        print(f"No `{MARKER_KEY}` key present in {settings_path} — nothing to reset.")
        return 0

    marker_size = len(data.get(MARKER_KEY) or [])
    if args.dry_run:
        print(f"Would drop `{MARKER_KEY}` ({marker_size} entry(ies)) from {settings_path}.")
        print(f"`permissions.allow` would be untouched.")
        print()
        print("(--dry-run: no changes written.)")
        return 0

    del data[MARKER_KEY]
    SettingsReconciler.write_atomic(settings_path, data)
    print(f"Dropped `{MARKER_KEY}` ({marker_size} entry(ies)) from {settings_path}.")
    print(f"Next `python .claude/scripts/update.py` will re-ADOPT all currently-shipped")
    print(f"rules already present in permissions.allow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
validate_permissions_catalog.py — drift guard between
`docs/_bcos-framework/architecture/permissions-catalog.md` (the SoT) and
`.claude/settings.json > permissions.allow` (the live shipped allowlist).

Bidirectional check:

  Forward (catalog -> settings.json)
    Every permission string quoted with backticks in the catalog tables
    must be present in settings.json as either:
      - a verbatim match, OR
      - a more-specific entry covered by a catalog catch-all glob, OR
      - a glob/prefix in the catalog that itself covers ≥1 settings entry.

  Reverse (settings.json -> catalog)
    Every entry in `permissions.allow` must be either:
      - a verbatim match in the catalog, OR
      - covered by a catalog glob/prefix (e.g. `Bash(python .claude/scripts/:*)`
        covers any `Bash(python .claude/scripts/foo.py:*)`), OR
      - on the small explicit STRUCTURAL_INFRA exemption list — basic
        capabilities (Read, Glob, Grep) that don't warrant per-row
        rationale.

Exit codes:
  0 — clean
  1 — drift found (forward or reverse mismatch)
  2 — hard error (catalog or settings.json missing / malformed)

CLI:
  python .claude/scripts/validate_permissions_catalog.py            # advisory
  python .claude/scripts/validate_permissions_catalog.py --json     # machine-readable
  python .claude/scripts/validate_permissions_catalog.py --strict   # exit 1 also if structural-allowlist is empty
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Where things live.
CATALOG_REL = Path("docs/_bcos-framework/architecture/permissions-catalog.md")
SETTINGS_REL = Path(".claude/settings.json")

# Basic capabilities that don't warrant a catalog rationale row.
# Keep this list TIGHT — the whole point of the catalog is to document
# every shipped rule. Only structural primitives go here.
STRUCTURAL_INFRA: set[str] = {
    "Read(**)",
    "Glob",
    "Grep",
}

# Regex matching permission tokens inside backticks.
# Examples of what we match:
#   `Bash(python .claude/scripts/:*)`
#   `Edit(.claude/hook_state/**)`
#   `Skill(context-mine)`
#   `Read(**)`
#   `Glob`
#   `Grep`
#   `mcp__scheduled-tasks__list_scheduled_tasks`
# We do NOT match bare filenames or prose words.
_TOKEN_RE = re.compile(
    r"`([A-Za-z][A-Za-z0-9_]*(?:\([^`]+\))?)`"
)


def _resolve_root(arg_root: Path | None) -> Path:
    if arg_root:
        return arg_root.expanduser().resolve()
    return Path.cwd().resolve()


def _load_catalog_tokens(catalog_path: Path) -> tuple[set[str], list[str]]:
    """Extract every backtick-quoted permission token from the catalog.

    Only extracts from markdown TABLE rows (lines starting with `|`).
    Tokens in prose paragraphs are intentionally ignored — the catalog
    uses backticks in rationale sections to discuss permissions that
    are explicitly NOT shipped (e.g. `Bash(git push:*)` is mentioned to
    explain why it's omitted). Treating table rows as the contract
    surface and prose as commentary keeps the signal clean.

    Returns (tokens, errors). Filters out non-permission backticked
    content (bare prose words like `dispatcher`).
    """
    errors: list[str] = []
    if not catalog_path.is_file():
        return (set(), [f"catalog not found: {catalog_path}"])
    try:
        text = catalog_path.read_text(encoding="utf-8")
    except OSError as e:
        return (set(), [f"catalog unreadable: {e}"])

    tokens: set[str] = set()
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("|"):
            continue  # only consider markdown table rows
        # Skip table separator rows (|---|---|)
        if set(stripped.replace("|", "").replace("-", "").strip()) == set():
            continue
        for tok in _TOKEN_RE.findall(line):
            # Heuristic filter: a real permission token either has `(...)`
            # in it OR is a known structural primitive OR starts with `mcp__`.
            if "(" in tok:
                tokens.add(tok)
            elif tok in STRUCTURAL_INFRA:
                tokens.add(tok)
            elif tok.startswith("mcp__"):
                tokens.add(tok)
            # otherwise it's prose like `dispatcher` or `BCOS` — skip silently.
    return (tokens, errors)


def _load_settings_allow(settings_path: Path) -> tuple[list[str], list[str]]:
    """Load permissions.allow from settings.json. Returns (entries, errors)."""
    if not settings_path.is_file():
        return ([], [f"settings.json not found: {settings_path}"])
    try:
        raw = settings_path.read_text(encoding="utf-8")
    except OSError as e:
        return ([], [f"settings.json unreadable: {e}"])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return ([], [f"settings.json invalid JSON: {e}"])
    allow = data.get("permissions", {}).get("allow", [])
    if not isinstance(allow, list):
        return ([], ["settings.json permissions.allow is not a list"])
    return ([str(x) for x in allow], [])


def _glob_covers(catch_all: str, specific: str) -> bool:
    """Does `catch_all` (a glob/prefix rule) cover `specific`?

    Rules ending in `:*)` or `:*` cover anything starting with their
    prefix (the part before the trailing `:*`/`:*)`). Exact-match
    catch-alls don't cover anything narrower than themselves.
    """
    if catch_all == specific:
        return True
    if catch_all.endswith(":*)"):
        prefix = catch_all[:-3]  # strip `:*)` → `Bash(python ...`
        # specific must start with prefix and have something after it.
        return specific.startswith(prefix) and specific != prefix + ")"
    if catch_all.endswith(":*"):
        prefix = catch_all[:-2]
        return specific.startswith(prefix) and specific != prefix
    if catch_all.endswith("**)"):
        # `Edit(.claude/hook_state/**)` covers `Edit(.claude/hook_state/foo)`.
        prefix = catch_all[:-3]  # `Edit(.claude/hook_state/`
        return specific.startswith(prefix) and specific != catch_all
    return False


def _covered_by_any(specific: str, pool: list[str] | set[str]) -> bool:
    """True iff some entry in `pool` covers `specific` (including
    verbatim match)."""
    for entry in pool:
        if _glob_covers(entry, specific):
            return True
    return False


def _check_forward(
    catalog_tokens: set[str], settings_allow: list[str],
) -> list[str]:
    """Forward check: every catalog token must be present in settings
    (verbatim or as a glob-coverer of ≥1 settings entry)."""
    settings_set = set(settings_allow)
    missing: list[str] = []
    for tok in sorted(catalog_tokens):
        if tok in settings_set:
            continue
        # Maybe the token is a glob that catches ≥1 settings entry?
        if any(_glob_covers(tok, s) for s in settings_allow):
            continue
        # Maybe a settings glob covers it? (e.g. catalog has
        # `Bash(python .claude/scripts/foo.py:*)` but settings only has
        # the catch-all `Bash(python .claude/scripts/:*)`.)
        if _covered_by_any(tok, settings_allow):
            continue
        missing.append(tok)
    return missing


def _check_reverse(
    settings_allow: list[str], catalog_tokens: set[str],
) -> list[str]:
    """Reverse check: every settings entry must be findable in catalog
    (verbatim, covered by catalog glob) or be on STRUCTURAL_INFRA."""
    catalog_list = sorted(catalog_tokens)
    unrationalized: list[str] = []
    for entry in settings_allow:
        if entry in STRUCTURAL_INFRA:
            continue
        if entry in catalog_tokens:
            continue
        if _covered_by_any(entry, catalog_list):
            continue
        unrationalized.append(entry)
    return unrationalized


def validate(root: Path) -> tuple[dict, int]:
    """Run the bidirectional check. Returns (summary, exit_code)."""
    catalog_tokens, cat_errs = _load_catalog_tokens(root / CATALOG_REL)
    settings_allow, set_errs = _load_settings_allow(root / SETTINGS_REL)

    if cat_errs or set_errs:
        return ({"ok": False, "errors": cat_errs + set_errs}, 2)

    forward_missing = _check_forward(catalog_tokens, settings_allow)
    reverse_unrationalized = _check_reverse(settings_allow, catalog_tokens)

    summary = {
        "ok": not (forward_missing or reverse_unrationalized),
        "catalog_tokens": len(catalog_tokens),
        "settings_entries": len(settings_allow),
        "structural_exemptions": sorted(
            e for e in settings_allow if e in STRUCTURAL_INFRA
        ),
        "forward_missing": forward_missing,
        "reverse_unrationalized": reverse_unrationalized,
        "errors": [],
    }
    return (summary, 0 if summary["ok"] else 1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Validate that .claude/settings.json permissions.allow and "
            "docs/_bcos-framework/architecture/permissions-catalog.md agree."
        ),
    )
    ap.add_argument("--root", type=Path, default=None,
                    help="Repo root (default: CWD)")
    ap.add_argument("--json", action="store_true",
                    help="Emit a JSON summary on stdout")
    ap.add_argument("--strict", action="store_true",
                    help="Reserved for future use (currently a no-op)")
    args = ap.parse_args(argv)

    root = _resolve_root(args.root)
    summary, rc = validate(root)

    if args.json:
        print(json.dumps(summary, indent=2))
        return rc

    print("=" * 62)
    print("  Permissions catalog drift check")
    print(f"  Root: {root}")
    print("=" * 62)
    print(f"  Catalog tokens:    {summary.get('catalog_tokens', '-')}")
    print(f"  Settings entries:  {summary.get('settings_entries', '-')}")
    print(f"  Structural exempt: {len(summary.get('structural_exemptions', []))}")
    print()

    if rc == 2:
        print("  HARD ERROR:")
        for e in summary.get("errors", []):
            print(f"    {e}")
        return rc

    forward_missing = summary.get("forward_missing", [])
    reverse_unrat = summary.get("reverse_unrationalized", [])

    if not forward_missing and not reverse_unrat:
        print("  All catalog entries map to settings.json and vice versa.")
        print()
        return 0

    if forward_missing:
        print(f"  FORWARD DRIFT — {len(forward_missing)} catalog token(s) "
              f"not in settings.json (catalog says shipped, settings says no):")
        for tok in forward_missing:
            print(f"    catalog says:  {tok}")
        print()

    if reverse_unrat:
        print(f"  REVERSE DRIFT — {len(reverse_unrat)} settings entry(ies) "
              f"with no catalog row (settings ships them, catalog doesn't "
              f"document them):")
        for entry in reverse_unrat:
            print(f"    settings has:  {entry}")
        print()

    print("  To resolve:")
    print("    - Add missing rows to docs/_bcos-framework/architecture/permissions-catalog.md")
    print("    - OR remove unused entries from .claude/settings.json")
    print("    - OR add to STRUCTURAL_INFRA in validate_permissions_catalog.py if a")
    print("      true structural primitive (rare — keep that list tight)")
    print()
    return rc


if __name__ == "__main__":
    sys.exit(main())

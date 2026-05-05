#!/usr/bin/env python3
"""
Load the BCOS task-profile catalog (P5).

Resolution order:
  1. docs/.context.task-profiles.yml          (per-repo override; optional)
  2. docs/_bcos-framework/templates/_context.task-profiles.yml.tmpl
                                              (framework default)

Returns a list of normalized profile dicts. Each profile:
  {
    "id": "<profile-id>",
    "description": "<text>",
    "required-zones":      [{"id": ..., "required": bool}, ...],
    "content-families":    [{"name": ..., "pattern": ..., "required": bool, "min-count": int}, ...],
    "source-of-truth-ranking": [<zone-id>, ...],
    "freshness-thresholds":    {<zone-id>: <int days> | None (never)},
    "traversal-hints":         [{"from-edge": ..., "depth-cap": int}, ...],
    "coverage-assertions":     {<family-name>: <min-count>},
  }

Stdlib-only — re-uses the inline-list parsing pattern from
`load_zone_registry.py`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
OVERRIDE_PATH = REPO_ROOT / "docs" / ".context.task-profiles.yml"
TEMPLATE_PATH = REPO_ROOT / "docs" / "_bcos-framework" / "templates" / "_context.task-profiles.yml.tmpl"

PROFILE_REQUIRED_FIELDS = (
    "id",
    "description",
    "required-zones",
    "content-families",
    "source-of-truth-ranking",
    "freshness-thresholds",
    "traversal-hints",
    "coverage-assertions",
)


class TaskProfilesError(Exception):
    """Raised when the catalog file is missing or malformed."""


def resolve_profiles_path() -> Path:
    if OVERRIDE_PATH.is_file():
        return OVERRIDE_PATH
    if TEMPLATE_PATH.is_file():
        return TEMPLATE_PATH
    raise TaskProfilesError(
        f"No task-profile catalog found. Looked at: {OVERRIDE_PATH}, then {TEMPLATE_PATH}"
    )


def load_task_profiles(path: Path | None = None) -> list[dict[str, Any]]:
    """Parse the catalog and return the list of normalized profile entries."""
    target = path or resolve_profiles_path()
    text = target.read_text(encoding="utf-8")
    raw_profiles = _parse_catalog(text)
    return [_normalize_profile(p) for p in raw_profiles]


# ---------------------------------------------------------------------------
# Parser (narrow YAML subset matching load_zone_registry.py's shape)
# ---------------------------------------------------------------------------


def _parse_catalog(text: str) -> list[dict[str, Any]]:
    """Parse the profiles catalog into a list of raw-string dicts.

    Profile-level bullets start with `  - ` (2-space indent + dash). Field
    values may either be inline on the same line as the key, or be a block
    list of bullets indented at 6 spaces (`      - …`) — those bullets
    accumulate into a single comma-joined string under the field key, so
    downstream normalisers can consume them with the same parser as the
    inline form.
    """
    lines = text.splitlines()
    in_profiles = False
    profiles: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    pending_block_key: str | None = None
    pending_block_items: list[str] = []

    def _flush_block_to_current() -> None:
        nonlocal pending_block_key, pending_block_items
        if pending_block_key is not None and current is not None:
            current[pending_block_key] = "[" + ", ".join(pending_block_items) + "]"
        pending_block_key = None
        pending_block_items = []

    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not in_profiles:
            if stripped == "profiles:":
                in_profiles = True
            continue

        # Indented block-list continuation (6+ space indent + bullet)
        if raw.startswith("      - ") and pending_block_key is not None:
            pending_block_items.append(raw[8:].strip())
            continue

        # Profile-level bullet `  - id: ...`
        if raw.startswith("  - "):
            _flush_block_to_current()
            if current is not None:
                profiles.append(current)
            current = {}
            after_dash = raw[4:]
            key, _, value = after_dash.partition(":")
            current[key.strip()] = value.strip()
            continue

        # Field at 4-space indent
        if raw.startswith("    ") and current is not None:
            _flush_block_to_current()
            content = raw.strip()
            if not content or content.startswith("#"):
                continue
            key, _, value = content.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                # Block-list follows; collect indented bullets into this key.
                pending_block_key = key
                pending_block_items = []
            else:
                current[key] = value
            continue

        # Non-indented line ends the profiles block
        if raw and not raw.startswith(" "):
            _flush_block_to_current()
            if current is not None:
                profiles.append(current)
                current = None
            in_profiles = False

    _flush_block_to_current()
    if current is not None:
        profiles.append(current)
    return profiles


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_profile(raw: dict[str, Any]) -> dict[str, Any]:
    pid = _strip_quotes(str(raw.get("id") or "<unknown>"))
    out: dict[str, Any] = {}
    out["id"] = pid
    out["description"] = _strip_quotes(str(raw.get("description") or ""))
    out["required-zones"] = _parse_required_zones(
        raw.get("required-zones") or "[]", profile_id=pid
    )
    out["content-families"] = _parse_content_families(raw.get("content-families") or "[]")
    out["source-of-truth-ranking"] = _parse_inline_list(raw.get("source-of-truth-ranking") or "[]")
    out["freshness-thresholds"] = _parse_freshness_thresholds(
        raw.get("freshness-thresholds") or "[]", profile_id=pid
    )
    out["traversal-hints"] = _parse_traversal_hints(
        raw.get("traversal-hints") or "[]", profile_id=pid
    )
    out["coverage-assertions"] = _parse_coverage_assertions(
        raw.get("coverage-assertions") or "[]", profile_id=pid
    )
    return out


def _parse_inline_list(value: str) -> list[str]:
    s = value.strip()
    if not (s.startswith("[") and s.endswith("]")):
        return []
    inner = s[1:-1].strip()
    if not inner:
        return []
    return [_strip_quotes(item.strip()) for item in inner.split(",") if item.strip()]


def _parse_required_zones(value: str, *, profile_id: str) -> list[dict[str, Any]]:
    """Parse `[active=true, wiki=false]` into [{id, required}, ...].

    Strict: any flag that is not exactly `true` or `false` (case-insensitive)
    raises `TaskProfilesError`. The default-to-False behaviour silently
    disabled required zones on typos like `active=treu`.
    """
    out: list[dict[str, Any]] = []
    for entry in _parse_inline_list(value):
        if "=" not in entry:
            raise TaskProfilesError(
                f"profile {profile_id!r}: required-zones entry {entry!r} missing `=`"
            )
        zone_id, _, flag = entry.partition("=")
        flag_lower = flag.strip().lower()
        if flag_lower not in ("true", "false"):
            raise TaskProfilesError(
                f"profile {profile_id!r}: required-zones[{zone_id.strip()}] "
                f"must be 'true' or 'false'; got {flag.strip()!r}"
            )
        out.append({
            "id": zone_id.strip(),
            "required": flag_lower == "true",
        })
    return out


def _parse_freshness_thresholds(value: str, *, profile_id: str) -> dict[str, int | None]:
    """Parse `[active=30, wiki=never]` into {zone: days or None}.

    Strict: anything other than a non-negative integer or the literal `never`
    raises. Previously silent fallback-to-`never` masked typos like
    `active=thirty` as if the zone had no freshness check.
    """
    out: dict[str, int | None] = {}
    for entry in _parse_inline_list(value):
        if "=" not in entry:
            raise TaskProfilesError(
                f"profile {profile_id!r}: freshness-thresholds entry {entry!r} missing `=`"
            )
        zone_id, _, days = entry.partition("=")
        zone_id = zone_id.strip()
        days_clean = days.strip().lower()
        if days_clean == "never":
            out[zone_id] = None
            continue
        try:
            parsed = int(days_clean)
        except ValueError:
            raise TaskProfilesError(
                f"profile {profile_id!r}: freshness-thresholds[{zone_id}] "
                f"must be a non-negative integer or 'never'; got {days.strip()!r}"
            )
        if parsed < 0:
            raise TaskProfilesError(
                f"profile {profile_id!r}: freshness-thresholds[{zone_id}] "
                f"must be non-negative; got {parsed}"
            )
        out[zone_id] = parsed
    return out


def _parse_coverage_assertions(value: str, *, profile_id: str) -> dict[str, int]:
    """Parse `[competitor-data=1, market-data=1]` into {family: min}.

    Strict: invalid integers raise. Previously silent fallback-to-0 disabled
    coverage checks on typos like `competitor-data=one`.
    """
    out: dict[str, int] = {}
    for entry in _parse_inline_list(value):
        if "=" not in entry:
            raise TaskProfilesError(
                f"profile {profile_id!r}: coverage-assertions entry {entry!r} missing `=`"
            )
        family, _, mn = entry.partition("=")
        family = family.strip()
        try:
            parsed = int(mn.strip())
        except ValueError:
            raise TaskProfilesError(
                f"profile {profile_id!r}: coverage-assertions[{family}] "
                f"must be an integer; got {mn.strip()!r}"
            )
        if parsed < 0:
            raise TaskProfilesError(
                f"profile {profile_id!r}: coverage-assertions[{family}] "
                f"must be non-negative; got {parsed}"
            )
        out[family] = parsed
    return out


def _parse_traversal_hints(value: str, *, profile_id: str) -> list[dict[str, Any]]:
    """Parse one inline mapping like `[from-edge=builds-on, depth-cap=2]`.

    Strict: invalid `depth-cap` integers raise. Previously silent
    fallback-to-0 disabled traversal entirely on typos.
    """
    out: dict[str, Any] = {}
    for entry in _parse_inline_list(value):
        if "=" not in entry:
            raise TaskProfilesError(
                f"profile {profile_id!r}: traversal-hints entry {entry!r} missing `=`"
            )
        key, _, val = entry.partition("=")
        key = key.strip()
        val = val.strip()
        if key == "depth-cap":
            try:
                parsed = int(val)
            except ValueError:
                raise TaskProfilesError(
                    f"profile {profile_id!r}: traversal-hints depth-cap "
                    f"must be a non-negative integer; got {val!r}"
                )
            if parsed < 0:
                raise TaskProfilesError(
                    f"profile {profile_id!r}: traversal-hints depth-cap "
                    f"must be non-negative; got {parsed}"
                )
            out[key] = parsed
        else:
            out[key] = val
    return [out] if out else []


_FAMILY_RE = re.compile(
    r"name=(?P<name>[a-zA-Z0-9_-]+)"
    r"\s*,\s*pattern=(?P<pattern>[^,]+?)"
    r"\s*,\s*required=(?P<required>true|false)"
    r"\s*,\s*min-count=(?P<min>\d+)"
)


def _parse_content_families(value: Any) -> list[dict[str, Any]]:
    """Each entry: `name=X, pattern=Y, required=Z, min-count=N`.

    Accepts either the full bracketed string or a single-line value where the
    parser already stripped brackets. Family entries themselves contain
    commas (between key=value pairs), so we split on `name=` boundaries
    rather than on naive commas.
    """
    families: list[dict[str, Any]] = []
    s = (value if isinstance(value, str) else "").strip()
    if not s:
        return families
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
    else:
        inner = s
    if not inner:
        return families
    for raw in _split_family_entries(inner):
        m = _FAMILY_RE.search(raw)
        if not m:
            continue
        families.append({
            "name": m.group("name").strip(),
            "pattern": m.group("pattern").strip(),
            "required": m.group("required").strip().lower() == "true",
            "min-count": int(m.group("min")),
        })
    return families


def _split_family_entries(inner: str) -> list[str]:
    """Split family entries by detecting `name=` boundaries.

    The catalog convention is one entry per family, joined by `, ` between
    `min-count=N` and the next `name=...`.
    """
    parts: list[str] = []
    pieces = re.split(r",\s*(?=name=)", inner)
    for piece in pieces:
        if piece.strip():
            parts.append(piece.strip())
    return parts


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def main() -> int:
    try:
        profiles = load_task_profiles()
    except TaskProfilesError as exc:
        print(f"error: {exc}")
        return 1
    print(f"loaded {len(profiles)} profile(s) from {resolve_profiles_path()}")
    for p in profiles:
        zones = ", ".join(z["id"] for z in p["required-zones"])
        families = ", ".join(f["name"] for f in p["content-families"])
        print(f"  {p['id']:30} zones=[{zones}] families=[{families}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

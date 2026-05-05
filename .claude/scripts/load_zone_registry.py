#!/usr/bin/env python3
"""
Load the BCOS context-zones registry.

Resolution order:
  1. docs/.context-zones.yml          (per-repo override; optional)
  2. docs/_bcos-framework/templates/_context-zones.yml.tmpl  (framework default)

Returns a list of mappings, one per zone, with the eight required fields
populated. The caller (context_search.py, context_bundle.py, validators) does
not need to know which file was loaded.

Stdlib-only. The registry YAML shape is intentionally narrow:
  - top-level scalars (schema-version, last-updated)
  - one list-of-mappings under `zones:` with two-space indented entries
  - inline-list values inside the mappings ([a, b, c])
  - scalar values (string / boolean / null)

If the project ever needs richer YAML, swap this parser for the consolidated
_wiki_yaml.py shipped in P4. The function signature stays the same.

Usage:
    from load_zone_registry import load_zone_registry
    zones = load_zone_registry()
    for zone in zones:
        print(zone["id"], zone["source-of-truth-role"])
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
OVERRIDE_PATH = REPO_ROOT / "docs" / ".context-zones.yml"
TEMPLATE_PATH = REPO_ROOT / "docs" / "_bcos-framework" / "templates" / "_context-zones.yml.tmpl"

REQUIRED_ZONE_FIELDS = (
    "id",
    "path-glob",
    "frontmatter-fields-required",
    "freshness-field",
    "freshness-model",
    "source-of-truth-role",
    "addressing",
    "optional",
)

LIST_FIELDS = {"frontmatter-fields-required", "freshness-by-page-type"}


class ZoneRegistryError(Exception):
    """Raised when the registry file is missing or malformed."""


def resolve_registry_path() -> Path:
    """Return the path the loader will read from. Override wins if present."""
    if OVERRIDE_PATH.is_file():
        return OVERRIDE_PATH
    if TEMPLATE_PATH.is_file():
        return TEMPLATE_PATH
    raise ZoneRegistryError(
        f"No zone registry found. Looked at: {OVERRIDE_PATH}, then {TEMPLATE_PATH}"
    )


def load_zone_registry(path: Path | None = None) -> list[dict[str, Any]]:
    """Parse the zone registry and return the list of zone entries.

    Each entry is a dict with the eight required fields (see REQUIRED_ZONE_FIELDS).
    Missing fields are populated with safe defaults so the caller can rely on
    `entry["freshness-field"]` etc. always being present.
    """
    target = path or resolve_registry_path()
    text = target.read_text(encoding="utf-8")
    zones = _parse_registry(text)
    return [_normalize_entry(entry) for entry in zones]


def _parse_registry(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    i = 0
    in_zones = False
    zones: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    while i < len(lines):
        raw = lines[i].rstrip("\r")
        stripped = raw.strip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        if not in_zones:
            if stripped == "zones:":
                in_zones = True
            i += 1
            continue

        # Inside the `zones:` block. Entries are 2-space indented; new entry
        # starts with `- key: value`. Continuation lines are 4-space indented
        # `  key: value`.
        if raw.startswith("  - "):
            if current is not None:
                zones.append(current)
            current = {}
            after_dash = raw[4:]
            key, _, value = after_dash.partition(":")
            current[key.strip()] = _parse_scalar(value.strip(), key.strip())
            i += 1
            continue

        if raw.startswith("    ") and current is not None:
            content = raw.strip()
            if not content or content.startswith("#"):
                i += 1
                continue
            key, _, value = content.partition(":")
            current[key.strip()] = _parse_scalar(value.strip(), key.strip())
            i += 1
            continue

        # A non-indented line ends the zones block.
        if raw and not raw.startswith(" "):
            if current is not None:
                zones.append(current)
                current = None
            in_zones = False
            i += 1
            continue

        i += 1

    if current is not None:
        zones.append(current)

    return zones


def _parse_scalar(value: str, key: str) -> Any:
    value = value.strip()
    if value == "":
        return [] if key in LIST_FIELDS else None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_strip_quotes(part.strip()) for part in inner.split(",") if part.strip()]
    if value.lower() in {"null", "~"}:
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return _strip_quotes(value)


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field in REQUIRED_ZONE_FIELDS:
        if field in entry:
            out[field] = entry[field]
        elif field in LIST_FIELDS:
            out[field] = []
        elif field == "optional":
            out[field] = False
        else:
            out[field] = None
    # Preserve any extra fields the registry adds without breaking the contract.
    for k, v in entry.items():
        if k not in out:
            out[k] = v
    # Expose `freshness-by-page-type` both as the raw list (preserved above) and
    # as a normalized dict for direct lookup by consumers (P5 bundle resolver).
    overrides = entry.get("freshness-by-page-type")
    if isinstance(overrides, list):
        out["freshness-by-page-type-map"] = _parse_kv_list(overrides)
    else:
        out["freshness-by-page-type-map"] = {}
    return out


def _parse_kv_list(items: list[str]) -> dict[str, str]:
    """Parse a list of `key=value` strings into a dict. Skips malformed entries."""
    out: dict[str, str] = {}
    for item in items:
        if not isinstance(item, str) or "=" not in item:
            continue
        key, _, value = item.partition("=")
        key = key.strip()
        value = value.strip()
        if key and value:
            out[key] = value
    return out


def freshness_field_for(entry: dict[str, Any], page_type: str | None) -> str | None:
    """Resolve the freshness field for a doc, given its zone entry and page-type.

    Falls back to `freshness-field` when the page-type isn't in the override map.
    Returns None for zones with no freshness signal at all.
    """
    if page_type:
        override = (entry.get("freshness-by-page-type-map") or {}).get(page_type)
        if override:
            return override
    return entry.get("freshness-field")


def main() -> int:
    try:
        zones = load_zone_registry()
    except ZoneRegistryError as exc:
        print(f"error: {exc}")
        return 1
    print(f"loaded {len(zones)} zones from {resolve_registry_path()}")
    for zone in zones:
        print(
            f"  {zone['id']:22} role={zone['source-of-truth-role']:11} "
            f"freshness={zone['freshness-field'] or '-':14} optional={zone['optional']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

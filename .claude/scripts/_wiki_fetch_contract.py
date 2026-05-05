#!/usr/bin/env python3
"""
Contract validator for the `wiki-fetch` sub-agent's return value (P3).

Sub-agents are LLM calls. Their outputs drift if not constrained — fields
appear, disappear, get renamed, or balloon past the documented token cap.
This validator is the mechanical guard: every result that comes back from a
`wiki-fetch` Task dispatch passes through `validate_result()` before the
calling skill writes a wiki page from it.

Public API:
    validate_result(result, max_tokens=4000) -> (ok: bool, errors: list[str])

The check is conservative: anything that violates the documented contract
returns `ok=False` with a list of human-readable issue strings. The caller
decides whether to surface to the user, retry, or skip.
"""

from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = (
    "title",
    "h2-outline",
    "key-sentences",
    "suggested-page-type",
    "suggested-cluster",
    "raw-file-pointer",
    "citation-banner-fields",
)

DEFAULT_MAX_TOKENS = 4000

# Approximate "tokens" via char/4 — close enough for the cap check, and avoids
# pulling in a tokenizer dependency. The cap is conservative on purpose.
CHARS_PER_TOKEN_APPROX = 4


REQUIRED_CITATION_BANNER_FIELDS = ("source-url", "last-fetched", "detail-level", "provenance")
REQUIRED_PROVENANCE_FIELDS = ("kind", "fetched-at")
ALLOWED_DETAIL_LEVELS = frozenset({"shallow", "standard", "deep"})


def validate_result(
    result: Any,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> tuple[bool, list[str]]:
    """Return `(ok, errors)` for one wiki-fetch return value.

    Strict validation: every field's type is checked, list item types are
    checked, and the citation banner's required subfields are checked. The
    only relaxation is the error variant, where most fields may be empty
    because the sub-agent failed to produce real content.
    """
    errors: list[str] = []

    if not isinstance(result, dict):
        return False, ["result is not a JSON object"]

    is_error_variant = bool(result.get("error"))

    for field in REQUIRED_FIELDS:
        if field not in result:
            errors.append(f"missing required field: {field!r}")

    if not is_error_variant:
        # Scalar fields
        _expect_str(result, "title", errors)
        _expect_str_or_null(result, "suggested-page-type", errors)
        _expect_str_or_null(result, "suggested-cluster", errors)
        _expect_str_or_null(result, "raw-file-pointer", errors)

        # List fields with item-type checks
        _expect_list_of_strs(result, "h2-outline", errors)
        _expect_list_of_strs(result, "key-sentences", errors)

        # Citation banner — must be a dict with the documented subfields
        if "citation-banner-fields" in result:
            _validate_citation_banner(result["citation-banner-fields"], errors)

    # Token cap
    payload = _payload_for_size(result)
    estimated_tokens = max(1, len(payload) // CHARS_PER_TOKEN_APPROX)
    if estimated_tokens > max_tokens:
        errors.append(
            f"result exceeds token cap: ~{estimated_tokens} tokens > {max_tokens}"
        )

    if "error" in result and result["error"] is not None:
        if not isinstance(result["error"], dict):
            errors.append("error must be an object when present")
        else:
            for ekey in ("kind", "message"):
                if ekey not in result["error"]:
                    errors.append(f"error object missing required field: {ekey!r}")
                elif not isinstance(result["error"][ekey], str):
                    errors.append(f"error.{ekey} must be a string")

    return len(errors) == 0, errors


def _expect_str(obj: dict, key: str, errors: list[str]) -> None:
    if key not in obj:
        return
    if not isinstance(obj[key], str):
        errors.append(f"{key} must be a string; got {type(obj[key]).__name__}")


def _expect_str_or_null(obj: dict, key: str, errors: list[str]) -> None:
    if key not in obj:
        return
    value = obj[key]
    if value is not None and not isinstance(value, str):
        errors.append(f"{key} must be a string or null; got {type(value).__name__}")


def _expect_list_of_strs(obj: dict, key: str, errors: list[str]) -> None:
    if key not in obj:
        return
    value = obj[key]
    if not isinstance(value, list):
        errors.append(f"{key} must be a list; got {type(value).__name__}")
        return
    for i, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(
                f"{key}[{i}] must be a string; got {type(item).__name__}"
            )


def _validate_citation_banner(banner: Any, errors: list[str]) -> None:
    if not isinstance(banner, dict):
        errors.append(
            f"citation-banner-fields must be an object; got {type(banner).__name__}"
        )
        return
    for field in REQUIRED_CITATION_BANNER_FIELDS:
        if field not in banner:
            errors.append(f"citation-banner-fields missing required field: {field!r}")
            continue
        if field == "provenance":
            _validate_provenance(banner["provenance"], errors)
        elif field == "detail-level":
            value = banner["detail-level"]
            if not isinstance(value, str):
                errors.append(
                    f"citation-banner-fields.detail-level must be a string; "
                    f"got {type(value).__name__}"
                )
            elif value not in ALLOWED_DETAIL_LEVELS:
                errors.append(
                    f"citation-banner-fields.detail-level must be one of "
                    f"{sorted(ALLOWED_DETAIL_LEVELS)}; got {value!r}"
                )
        else:
            value = banner[field]
            if not isinstance(value, str):
                errors.append(
                    f"citation-banner-fields.{field} must be a string; "
                    f"got {type(value).__name__}"
                )


def _validate_provenance(provenance: Any, errors: list[str]) -> None:
    if not isinstance(provenance, dict):
        errors.append(
            f"citation-banner-fields.provenance must be an object; "
            f"got {type(provenance).__name__}"
        )
        return
    for field in REQUIRED_PROVENANCE_FIELDS:
        if field not in provenance:
            errors.append(
                f"citation-banner-fields.provenance missing required field: {field!r}"
            )
            continue
        if not isinstance(provenance[field], str):
            errors.append(
                f"citation-banner-fields.provenance.{field} must be a string"
            )


def _payload_for_size(result: dict) -> str:
    """Concat the heavy fields for the size estimate."""
    parts: list[str] = []
    parts.append(str(result.get("title") or ""))
    for item in result.get("h2-outline") or []:
        parts.append(str(item))
    for item in result.get("key-sentences") or []:
        parts.append(str(item))
    return " ".join(parts)


__all__ = ["validate_result", "REQUIRED_FIELDS", "DEFAULT_MAX_TOKENS"]

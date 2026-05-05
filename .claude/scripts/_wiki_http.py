#!/usr/bin/env python3
"""
HEAD/ETag/Last-Modified helper for the wiki-source-refresh quick-check tier.

Replaces a documentation-only claim in `wiki-zone.md` ("HEAD-only or
equivalent") with a real, mechanical check. The quick-check tier compares
stored `etag` / `last-modified` / `content-hash` from a source-summary page's
frontmatter against fresh HEAD response headers; when nothing changed, the
tier bumps `last-fetched` and skips the full refresh-must-rediscover work.

Stdlib-only — `urllib.request.Request` with `method="HEAD"`. No `requests`
dependency. No third-party HTTP client. Works offline against the dict shape
in `extract_head_signals()` so tests don't need network access.

Public API:
    extract_head_signals(headers)              -> dict[str, Any]
    head_signals_unchanged(stored, fresh)      -> bool
    head_check(url, timeout=10)                -> dict[str, Any] | None

The first two are pure functions over header dicts; `head_check` is the
HTTP-touching wrapper. Tests use the pure helpers exclusively.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any, Mapping

# RFC 7232 §2.3: ETags can be "weak" (W/-prefixed) or "strong". For the wiki
# quick-check tier we treat them as semantically equivalent — a server may
# downgrade strong→weak across revalidations without changing content.
_WEAK_PREFIX = "W/"


def extract_head_signals(headers: Mapping[str, Any]) -> dict[str, Any]:
    """Pull the freshness-relevant signals from a HEAD response's headers.

    Header lookup is case-insensitive (HTTP headers are by spec). Missing
    fields become None. `Content-Length` is parsed to int when numeric.
    """
    norm = _case_insensitive(headers)
    return {
        "etag": _clean(norm.get("etag")),
        "last-modified": _clean(norm.get("last-modified")),
        "content-length": _parse_int(norm.get("content-length")),
        "content-type": _clean(norm.get("content-type")),
    }


def head_signals_unchanged(
    *, stored: Mapping[str, Any], fresh: Mapping[str, Any]
) -> bool:
    """Return True when the HEAD signals indicate the resource has not changed.

    HEAD-tier comparison uses ONLY validators a server returns in a HEAD
    response — `ETag` and `Last-Modified`. **The wiki's stored `content-hash`
    is NOT consulted here:** a body content hash is a full-tier validator
    (computed after a body fetch), not a quick-check signal. See
    `body_content_unchanged()` for the full-tier comparison.

    Comparison rules (in order of precedence):
    1. ETag: if both sides have one and they match (after stripping the
       weak `W/` prefix), the resource is unchanged.
    2. Last-Modified: if both sides have one and they match, unchanged.
    3. Otherwise (one side missing both validators), the result is `False` —
       the quick-check tier defers to the full refresh.

    The function never auto-decides "unchanged" when validators are absent;
    a missing validator is a "don't know" signal that escalates to refresh.
    """
    s_etag = _strip_weak(stored.get("etag"))
    f_etag = _strip_weak(fresh.get("etag"))
    if s_etag and f_etag:
        return s_etag == f_etag

    s_lm = stored.get("last-modified")
    f_lm = fresh.get("last-modified")
    if s_lm and f_lm:
        return s_lm == f_lm

    return False


def body_content_unchanged(
    *, stored_hash: str | None, fresh_body: bytes | str | None
) -> bool:
    """Full-tier validator: did the fetched body hash match what the page stored?

    Used after `wiki-fetch` returns a body, by the full refresh path. A
    matching hash means "the body bytes are the same as last time" even when
    HEAD validators were absent or unreliable. Returns False when either side
    is missing — same "don't auto-decide unchanged" rule as the quick-check.
    """
    if not stored_hash or fresh_body is None:
        return False
    fresh_hash = compute_body_hash(fresh_body)
    return stored_hash.strip() == fresh_hash


def compute_body_hash(body: bytes | str) -> str:
    """Stable SHA-256 hex digest of a body, truncated to 16 chars.

    Matches the format used elsewhere in the wiki capability for
    `provenance.notes` so `_wiki_yaml`-driven migrations can populate
    `content-hash` from existing provenance entries when available.
    """
    import hashlib

    if isinstance(body, str):
        body = body.encode("utf-8")
    return hashlib.sha256(body).hexdigest()[:16]


def head_check(url: str, *, timeout: float = 10.0) -> dict[str, Any] | None:
    """Issue an HTTP HEAD request and return the extracted signals.

    Returns None on network/HTTP error so callers can fall back to a full
    refresh. The wiki quick-check tier treats None as "don't know — escalate".
    """
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            headers = {key: response.headers.get(key) for key in response.headers.keys()}
            signals = extract_head_signals(headers)
            signals["status"] = response.status
            return signals
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _case_insensitive(headers: Mapping[str, Any]) -> dict[str, Any]:
    """Map of lower-cased keys → original values."""
    return {str(k).lower(): v for k, v in headers.items()}


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _strip_weak(etag: Any) -> str | None:
    if etag is None:
        return None
    text = str(etag).strip()
    if not text:
        return None
    if text.startswith(_WEAK_PREFIX):
        text = text[len(_WEAK_PREFIX):]
    return text


__all__ = [
    "extract_head_signals",
    "head_signals_unchanged",
    "head_check",
    "body_content_unchanged",
    "compute_body_hash",
]

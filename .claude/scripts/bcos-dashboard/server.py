#!/usr/bin/env python3
"""
server.py — Zero-dependency dashboard server.

Python stdlib only. Serves:
  GET /                  -> HTML shell (dashboard.html)
  GET /static/<file>     -> dashboard.css, dashboard.js
  GET /api/data          -> { meta, panels: [...] }   (all panels, each cached)
  GET /api/panel/<id>    -> single panel (debugging / selective refresh)
  GET /api/cache         -> cache introspection
  GET /api/health        -> liveness

Usage:
    from server import Panel, serve

    def collect_sales():
        return {"stats": [{"value": 12400, "label": "Revenue this week"}]}

    PANELS = [
        Panel(id="sales", title="Sales", kind="metric", span=4, ttl=30,
              collector=collect_sales),
    ]

    if __name__ == "__main__":
        serve(PANELS, title="My Dashboard", port=8765)

Design decisions:
  * Each panel has its own TTL cache. One slow collector doesn't slow the others.
  * Each collector is wrapped in _safe() — exceptions become {"error": ...} on the
    panel rather than a 500 on the whole endpoint.
  * HTML/CSS/JS are loaded from disk next to this file (or a user-supplied
    template_dir). Users edit them with normal syntax highlighting.
  * Title/subtitle are substituted into the HTML at request time. Everything
    else is driven by /api/data so HTML stays static.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import threading
import time
import traceback
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Iterable

# ---------------------------------------------------------------------------
# Panel definition
# ---------------------------------------------------------------------------

VALID_KINDS = {
    "metric", "table", "list", "feed", "grid", "progress", "chart",
    # BCOS dashboard extensions (vendored — diverges from upstream LDB):
    "jobs_panel", "actions_inbox", "run_history", "file_health", "cockpit",
    "atlas_ownership", "atlas_lifecycle", "atlas_relationships", "atlas_ecosystem",
}
VALID_SPANS = {3, 4, 6, 8, 12}


@dataclass
class Panel:
    """Declarative panel spec.

    Attributes
    ----------
    id              : stable identifier used in the URL fragment / DOM id /
                      cache-key base.
    title           : rendered in the panel header.
    kind            : renderer picked on the client; one of VALID_KINDS.
    span            : grid span out of 12 (3/4/6/8/12).
    collector       : callable returning a dict matching the kind's contract.
                      Default: zero-arg. If `collector_args` is set, the
                      collector is called with `*args` (for a tuple) or with
                      `**args` (for a dict).
                      See references/data-contract.md.
    collector_args  : optional positional/keyword arguments for the collector.
                      - tuple | list  -> hashable; collector called as
                        `collector(*args)` and cache keyed as
                        `f"{id}:{args!r}"`.
                      - callable(params: dict) -> tuple — resolved at request
                        time against URL query params. Enables URL-driven
                        filters (see references/data-contract.md,
                        "Parameterized collectors"). Default `()` preserves
                        zero-arg behaviour (cache keyed by id alone).
    ttl             : seconds to cache the collector's output. Tune per cost +
                      cadence.
    tag             : optional small badge shown next to the title
                      (e.g. "git", "db").
    severity        : optional base severity; overridden per-refresh if
                      collector returns "_severity" in its output.
    number          : optional section-number prefix rendered above the title
                      (e.g. "§01"). Additive — ignored when absent. See the
                      "warm newsprint" notes in references/design-principles.md.
    """

    id: str
    title: str
    kind: str
    span: int = 4
    ttl: float = 30.0
    collector: Callable[..., dict] | None = None
    collector_args: tuple | list | Callable[[dict], tuple] = ()
    tag: str | None = None
    severity: str | None = None
    number: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(
                f"Panel(id={self.id!r}): kind {self.kind!r} not in {sorted(VALID_KINDS)}"
            )
        if self.span not in VALID_SPANS:
            raise ValueError(
                f"Panel(id={self.id!r}): span {self.span} not in {sorted(VALID_SPANS)}"
            )
        if self.collector is None:
            raise ValueError(f"Panel(id={self.id!r}): collector is required")
        # Coerce list -> tuple for cache-key hashability. Callables pass through.
        if isinstance(self.collector_args, list):
            self.collector_args = tuple(self.collector_args)


# ---------------------------------------------------------------------------
# Empty-envelope helpers
#
# Every self-scanning dashboard starts life with a freshly-created-but-empty
# data source. "No data yet — run `python scanner.py`" is the correct first-
# boot UX, not an error. These helpers return envelopes that the client
# renders as a muted info card with the given hint. They coexist with a
# severity badge (see the `_severity` handling in _resolve_panel, which now
# runs before the missing short-circuit).
# ---------------------------------------------------------------------------

def _empty_list_envelope(scan_hint: str = "run `python scanner.py`") -> dict:
    """Envelope for an empty list/table/feed/grid panel on first boot.

    Renders as a muted *info* card with the hint text. The `hint` field is
    first-class so the client can style it distinctly from missing_message —
    see references/data-contract.md §"Empty vs error states".
    """
    return {
        "missing": True,
        "missing_message": "No data yet",
        "hint": scan_hint,
        "_severity": "info",
    }


def _empty_chart_envelope(scan_hint: str = "run `python scanner.py`") -> dict:
    """Envelope for an empty chart panel on first boot."""
    return {
        "missing": True,
        "missing_message": "No data yet",
        "hint": scan_hint,
        "_severity": "info",
    }


def _empty_metric_envelope(scan_hint: str = "run `python scanner.py`") -> dict:
    """Envelope for an empty metric/progress panel on first boot."""
    return {
        "missing": True,
        "missing_message": "No data yet",
        "hint": scan_hint,
        "_severity": "info",
    }


def _error_envelope(message: str, hint: str | None = None,
                    severity: str = "warn") -> dict:
    """Envelope for a panel whose data source is *broken* (not merely empty).

    Distinct from the `_empty_*_envelope()` helpers above: those signal
    "correctly configured, no data yet" (severity=info). This one signals
    "something is wrong, the user probably needs to act" — severity defaults
    to `warn`, and `hint` holds a copy-pasteable recovery instruction such
    as `"Check SCAN_ROOT env var"` or `"Re-run the migration: python -m migrate"`.

    Prefer raising a real exception inside a collector when the failure is
    unexpected — `_safe()` catches it and the client shows an error card.
    Reach for `_error_envelope` when the collector itself can detect a
    recoverable misconfiguration (missing path, wrong permissions, stale
    schema) and wants to surface a helpful message.
    """
    return {
        "error": str(message),
        "hint": hint,
        "_severity": severity,
    }


# ---------------------------------------------------------------------------
# _safe + TTL cache
# ---------------------------------------------------------------------------

def _safe(fn: Callable[[], dict]) -> dict:
    """Run a collector, converting any exception to a structured error dict.

    Panels should never crash the whole endpoint; one broken source is isolated.
    """
    try:
        out = fn()
        if out is None:
            return {"error": "collector returned None", "partial": True}
        if not isinstance(out, dict):
            return {"error": f"collector returned {type(out).__name__}, expected dict",
                    "partial": True}
        return out
    except Exception as exc:  # noqa: BLE001 - we deliberately swallow everything
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "partial": True,
            "trace": traceback.format_exc(limit=3),
        }


class _Cache:
    """Per-panel TTL cache, thread-safe (GIL is enough for dict set/get)."""

    def __init__(self) -> None:
        # id -> (expires_at_epoch, ttl_used, value)
        self._entries: dict[str, tuple[float, float, dict]] = {}
        self._lock = threading.Lock()

    def get_or_compute(self, key: str, ttl: float, compute: Callable[[], dict]) -> dict:
        now = time.time()
        with self._lock:
            entry = self._entries.get(key)
            if entry and entry[0] > now:
                return entry[2]
        # Compute outside the lock so slow collectors don't block others.
        value = compute()
        with self._lock:
            self._entries[key] = (now + ttl, ttl, value)
        return value

    def invalidate(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._entries.clear()
            else:
                self._entries.pop(key, None)

    def info(self) -> dict[str, dict[str, float]]:
        now = time.time()
        with self._lock:
            return {
                key: {
                    "age_seconds": round(ttl - (expires - now), 1),
                    "expires_in": round(expires - now, 1),
                    "ttl": ttl,
                }
                for key, (expires, ttl, _value) in self._entries.items()
            }


# ---------------------------------------------------------------------------
# Panel resolution (collector -> panel payload the client renders)
# ---------------------------------------------------------------------------

def _resolve_panel(panel: Panel, cache: _Cache, params: dict | None = None) -> dict:
    """Pull cached collector output and merge with panel metadata.

    If `panel.collector_args` is callable, resolve it against `params` (URL
    query dict) to materialize the tuple. The resolved tuple becomes part of
    the cache key so each distinct argument set is cached independently.
    """
    # Resolve collector_args for this request
    args = panel.collector_args
    if callable(args):
        try:
            args = args(params or {}) or ()
        except Exception as exc:  # noqa: BLE001
            return _panel_payload_error(panel, f"collector_args raised: {type(exc).__name__}: {exc}")
        if isinstance(args, list):
            args = tuple(args)

    # Cache key: plain id for zero-arg (backward compat); id:args for parameterized.
    cache_key = panel.id if not args else f"{panel.id}:{args!r}"
    raw = cache.get_or_compute(
        cache_key,
        panel.ttl,
        lambda: _safe(lambda: panel.collector(*args) if args else panel.collector()),  # type: ignore[misc]
    )

    payload: dict[str, Any] = {
        "id": panel.id,
        "title": panel.title,
        "kind": panel.kind,
        "span": panel.span,
    }
    if panel.tag:
        payload["tag"] = panel.tag
    if panel.severity:
        payload["severity"] = panel.severity
    if panel.number:
        payload["number"] = panel.number

    # The collector's output is either an error dict or the actual data.
    if "error" in raw:
        payload["error"] = raw["error"]
        if "trace" in raw:
            payload["trace"] = raw["trace"]
        # `hint` lets a collector attach actionable recovery text
        # alongside the error message — see `_error_envelope()` helper
        # and references/data-contract.md §"Empty vs error states".
        if raw.get("hint"):
            payload["hint"] = raw["hint"]
        # `_severity` override applies to error envelopes too (e.g. a
        # collector can classify a broken source as critical vs warn).
        sev = raw.get("_severity")
        if sev:
            payload["severity"] = sev
        return payload

    # Severity and tag overrides apply whether or not data is missing — a
    # correctly-configured-but-no-data-yet panel legitimately wants to render
    # as "info" while still carrying the missing flag. Read them BEFORE the
    # missing short-circuit so the envelope can be both at once (data-contract
    # pattern #5, "Empty-state envelopes").
    # NOTE: use .get (not .pop) so we don't mutate the cached dict — pop would
    # only work on the first resolve per TTL window, then silently lose state
    # on every subsequent cache hit.
    sev = raw.get("_severity")
    if sev:
        payload["severity"] = sev
    tag_override = raw.get("_tag")
    if tag_override:
        payload["tag"] = tag_override

    if raw.get("missing"):
        payload["missing"] = True
        if "missing_message" in raw:
            payload["missing_message"] = raw["missing_message"]
        # Missing panels can carry an actionable `hint` alongside the
        # missing_message (e.g. "run `python scanner.py`"). The client
        # styles this as a secondary line under the message.
        if raw.get("hint"):
            payload["hint"] = raw["hint"]
        return payload

    # Strip underscore-prefixed magic keys (_severity, _tag, and any future
    # internal markers) from the data envelope the client receives. The server
    # has already elevated the meaningful ones to payload.severity / payload.tag.
    payload["data"] = {k: v for k, v in raw.items() if not k.startswith("_")}
    return payload


def _panel_payload_error(panel: Panel, message: str) -> dict:
    """Build a minimal payload envelope for a resolve-time error (before the
    collector even runs). Keeps the rest of the dashboard rendering."""
    payload: dict[str, Any] = {
        "id": panel.id,
        "title": panel.title,
        "kind": panel.kind,
        "span": panel.span,
        "error": message,
    }
    if panel.tag:
        payload["tag"] = panel.tag
    if panel.number:
        payload["number"] = panel.number
    return payload


def _compute_health(panels_payload: list[dict]) -> dict:
    """Aggregate panel severities into a one-glance health summary."""
    counts = {"ok": 0, "warn": 0, "critical": 0, "info": 0, "muted": 0}
    errors = 0
    for p in panels_payload:
        if p.get("error"):
            errors += 1
            counts["warn"] += 1
            continue
        sev = p.get("severity")
        if sev in counts:
            counts[sev] += 1
        else:
            counts["muted"] += 1

    status = "ok"
    if counts["critical"] > 0:
        status = "critical"
    elif counts["warn"] > 0 or errors > 0:
        status = "warn"
    return {
        "ok": counts["ok"],
        "warn": counts["warn"],
        "critical": counts["critical"],
        "info": counts["info"],
        "errors": errors,
        "status": status,
    }


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

def _make_handler(
    panels: list[Panel],
    cache: _Cache,
    template_dir: Path,
    title: str,
    subtitle: str,
    refresh_ms: int,
    headline: Any = None,
    controls: Any = None,
    post_routes: dict[str, Callable[[dict], dict]] | None = None,
    get_routes: dict[str, Callable[[str, dict], dict]] | None = None,
    hidden_panels: list | None = None,
) -> type[BaseHTTPRequestHandler]:
    post_routes = post_routes or {}
    # BCOS extension: prefix-keyed GET routes for parametric paths like
    # `/api/job/<id>`. Handler receives `(suffix, params)` where suffix is
    # everything after the prefix and params is the parsed query dict.
    # Returns a dict; non-`ok=False` results are 200, otherwise 400.
    get_routes = get_routes or {}
    # BCOS extension: hidden_panels are reachable via /api/panel/<id> but
    # NOT included in /api/data — used by /settings sub-pages whose
    # collectors should not render in the cockpit grid.
    hidden_panels = hidden_panels or []
    panel_map = {p.id: p for p in panels}
    for hp in hidden_panels:
        panel_map[hp.id] = hp

    # Pre-load + pre-compute static files at handler-definition time; the server
    # gets restarted whenever the template changes, so a cache bust is cheap.
    def _load(path: Path) -> bytes:
        return path.read_bytes()

    html_raw = _load(template_dir / "dashboard.html")
    css_bytes = _load(template_dir / "dashboard.css")
    js_bytes = _load(template_dir / "dashboard.js")
    # Substitute title/subtitle into the HTML shell.
    html_rendered = (
        html_raw.decode("utf-8")
        .replace("{{TITLE}}", title)
        .replace("{{SUBTITLE}}", subtitle)
    ).encode("utf-8")

    static_files = {
        "dashboard.css": (css_bytes, "text/css; charset=utf-8"),
        "dashboard.js":  (js_bytes, "application/javascript; charset=utf-8"),
    }

    # Vendored assets (e.g. echarts.min.js). Served under /static/vendor/<file>
    # only when the dashboard directory contains a vendor/ folder. Absent when
    # the dashboard was scaffolded with the default --chart-library none.
    vendor_dir = template_dir / "vendor"
    if vendor_dir.is_dir():
        for p in vendor_dir.iterdir():
            if not p.is_file():
                continue
            suffix = p.suffix.lower()
            ctype = {
                ".js":  "application/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".map": "application/json; charset=utf-8",
            }.get(suffix, "application/octet-stream")
            static_files[f"vendor/{p.name}"] = (_load(p), ctype)

    # Favicons — optional. Served at /favicon.svg and /favicon.ico if present
    # in the dashboard directory. Drop in your own brand marks; nothing else
    # needs changing. Missing files resolve to 204 No Content (silent — avoids
    # noisy 404s in the browser console when a dashboard pre-dates this
    # feature or deliberately doesn't ship a favicon).
    favicon_files: dict[str, tuple[bytes, str]] = {}
    for name, ctype in (
        ("favicon.svg", "image/svg+xml"),
        ("favicon.ico", "image/x-icon"),
    ):
        p = template_dir / name
        if p.is_file():
            favicon_files[name] = (_load(p), ctype)

    class DashboardHandler(BaseHTTPRequestHandler):
        # Quiet default access log; keep errors visible.
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            if args and isinstance(args[0], str) and args[0].startswith(("4", "5")):
                sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

        # -- routing --
        def do_GET(self) -> None:  # noqa: N802 (http.server convention)
            path = self.path.split("?", 1)[0]

            if path in ("/", "/index.html"):
                return self._send_bytes(html_rendered, "text/html; charset=utf-8")

            if path.startswith("/static/"):
                name = path[len("/static/"):]
                if name not in static_files:
                    return self._send_json({"error": f"unknown asset {name}"}, status=404)
                body, ctype = static_files[name]
                return self._send_bytes(body, ctype)

            if path in ("/favicon.svg", "/favicon.ico"):
                fname = path[1:]  # strip leading slash
                if fname in favicon_files:
                    body, ctype = favicon_files[fname]
                    return self._send_bytes(body, ctype)
                # Graceful — dashboards that pre-date favicons return 204.
                self.send_response(204)
                self.end_headers()
                return

            if path == "/api/data":
                return self._send_json(self._collect_all(self._query_params()))

            if path.startswith("/api/panel/"):
                pid = path[len("/api/panel/"):].strip("/")
                panel = panel_map.get(pid)
                if panel is None:
                    return self._send_json({"error": f"unknown panel {pid}"}, status=404)
                return self._send_json(_resolve_panel(panel, cache, self._query_params()))

            if path == "/api/cache":
                return self._send_json({"cache": cache.info()})

            for prefix, handler in get_routes.items():
                if path.startswith(prefix):
                    suffix = path[len(prefix):]
                    try:
                        result = handler(suffix, self._query_params())
                    except Exception as exc:  # noqa: BLE001
                        return self._send_json(
                            {"error": f"{type(exc).__name__}: {exc}"}, status=500,
                        )
                    if not isinstance(result, dict):
                        result = {"result": result}
                    status = 200 if result.get("ok", True) and "error" not in result else 404
                    return self._send_json(result, status=status)

            if path == "/api/health":
                return self._send_json({
                    "ok": True,
                    "ts": datetime.now(timezone.utc)
                        .replace(microsecond=0)
                        .isoformat()
                        .replace("+00:00", "Z"),
                })

            # SPA fallback: any path that isn't /api/*, /static/*, or a
            # favicon serves the dashboard shell. Client-side router
            # decides whether to render the cockpit (/) or settings
            # layout (/settings/*). Reload-on-/settings/foo works because
            # the server hands back the same HTML and the client routes.
            if not path.startswith("/api/"):
                return self._send_bytes(html_rendered, "text/html; charset=utf-8")

            self._send_json({"error": "not found", "path": path}, status=404)

        # BCOS dashboard extension — POST support for mutating endpoints
        # (mark-done, schedule tuning). Upstream local-dashboard-builder
        # is read-only; we add a tiny JSON-body dispatcher here.
        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path not in post_routes:
                return self._send_json({"error": "not found", "path": path}, status=404)
            body = {}
            try:
                length = int(self.headers.get("Content-Length") or "0")
                if length > 0:
                    raw = self.rfile.read(length)
                    if raw:
                        body = json.loads(raw.decode("utf-8"))
                        if not isinstance(body, dict):
                            body = {}
            except Exception as exc:  # noqa: BLE001
                return self._send_json(
                    {"error": f"bad body: {type(exc).__name__}: {exc}"}, status=400,
                )
            try:
                handler = post_routes[path]
                # Backwards-compat: handler may accept (body) OR (body, ctx).
                # ctx exposes invalidate_panel() so the handler can force
                # the dashboard to re-compute a panel on the next fetch.
                import inspect
                sig = inspect.signature(handler)
                if len(sig.parameters) >= 2:
                    ctx = {"invalidate_panel": lambda pid: cache.invalidate(pid)}
                    result = handler(body, ctx)
                else:
                    result = handler(body)
            except Exception as exc:  # noqa: BLE001
                return self._send_json(
                    {"error": f"{type(exc).__name__}: {exc}"}, status=500,
                )
            status = 200 if (isinstance(result, dict) and result.get("ok", True)) else 400
            return self._send_json(result if isinstance(result, dict) else {"result": result}, status=status)

        # -- request params --
        def _query_params(self) -> dict:
            """Parse URL query string into a flat dict (last wins on duplicates)."""
            _, _, qs = self.path.partition("?")
            if not qs:
                return {}
            from urllib.parse import parse_qs
            parsed = parse_qs(qs, keep_blank_values=True)
            return {k: v[-1] for k, v in parsed.items()}

        # -- builders --
        def _collect_all(self, params: dict | None = None) -> dict:
            panels_payload = [_resolve_panel(p, cache, params) for p in panels]
            meta: dict[str, Any] = {
                "title": title,
                "subtitle": subtitle,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "refresh_ms": refresh_ms,
                "health": _compute_health(panels_payload),
            }
            # Optional headline banner — "most important today".
            # Pass a dict {text, meta?} or a callable returning such a dict.
            if headline is not None:
                try:
                    value = headline() if callable(headline) else headline
                    if isinstance(value, str):
                        meta["headline"] = {"text": value}
                    elif isinstance(value, dict) and value.get("text"):
                        meta["headline"] = value
                except Exception:
                    pass  # a broken headline must never 500 the dashboard

            # Optional controls bar — HTML fragment rendered above the panel
            # grid (typical use: filter buttons with data-filter-key/value).
            # Pass a string, a callable returning a string, or a callable
            # accepting (params: dict) -> string (useful for reflecting URL
            # state into the buttons at request time). See
            # references/design-principles.md → "URL-driven filters".
            if controls is not None:
                try:
                    if callable(controls):
                        # Try with params arg first, fall back to zero-arg
                        try:
                            value = controls(params or {})
                        except TypeError:
                            value = controls()
                    else:
                        value = controls
                    if isinstance(value, str) and value.strip():
                        meta["controls"] = value
                except Exception:
                    pass  # broken controls must never 500 the dashboard

            return {"meta": meta, "panels": panels_payload}

        # -- low level --
        def _send_bytes(self, body: bytes, ctype: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _send_json(self, obj: Any, status: int = 200) -> None:
            data = json.dumps(obj, default=str).encode("utf-8")
            self._send_bytes(data, "application/json; charset=utf-8", status=status)

    return DashboardHandler


# ---------------------------------------------------------------------------
# Port handling
# ---------------------------------------------------------------------------

def _find_free_port(preferred: int, host: str = "127.0.0.1") -> int:
    """Return `preferred` if it's bindable, else the next free port (≤+20).

    Raises OSError if nothing in the range works. The idea is to spare the user
    from cryptic "address already in use" errors when another dashboard is up.
    """
    # reconstructed from pyc reference (source was truncated on disk)
    import socket
    for candidate in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            try:
                s.bind((host, candidate))
                return candidate
            except OSError:
                pass
    raise OSError(f"no free port in [{preferred}, {preferred + 20})")


# ---------------------------------------------------------------------------
# serve()
# ---------------------------------------------------------------------------

def serve(
    panels: Iterable[Panel],
    *,
    title: str = "Local Dashboard",
    subtitle: str = "",
    host: str = "127.0.0.1",
    port: int = 8765,
    refresh_ms: int = 30000,
    open_browser: bool = False,
    template_dir: "Path | str | None" = None,
    auto_port: bool = True,
    headline: Any = None,
    controls: Any = None,
    post_routes: dict[str, Callable[[dict], dict]] | None = None,
    get_routes: dict[str, Callable[[str, dict], dict]] | None = None,
    hidden_panels: list | None = None,
) -> None:
    """Start the HTTP server and serve forever (Ctrl+C to stop).

    Parameters
    ----------
    panels       : iterable of `Panel` instances.
    title        : H1 in the header, browser tab title.
    subtitle     : subdued tagline next to the title.
    host / port  : bind address. Port defaults to 8765.
    refresh_ms   : client poll interval. Override the default 30s if needed.
    open_browser : open the default browser on startup. Defaults to False so
                   headless sandboxes (CI, /tmp sanity scripts) don't hang on
                   ``webbrowser.open()``. Set True for interactive local use.
    template_dir : directory containing dashboard.html/.css/.js. Defaults to
                   the directory of this server.py file.
    auto_port    : if the preferred port is bound, quietly pick the next free one.
    headline     : optional "most important today" banner. Pass either a
                   string, a dict ``{"text": str, "meta": str?}``, or a
                   zero-arg callable returning one of those. Hidden when unset.
                   If the callable raises, the banner is quietly skipped on
                   that refresh.
    controls     : optional HTML fragment rendered above the panel grid
                   (typical use: filter buttons). Accepts a string, a
                   zero-arg callable returning a string, or a callable
                   ``(params: dict) -> str`` for URL-state-aware rendering.
                   Hidden when unset. Exceptions are swallowed.
    """
    # reconstructed from pyc reference (source was truncated on disk).
    # Deltas from the pyc: open_browser default flipped to False (feedback #6),
    # webbrowser.open() guarded in try/except, controls kwarg plumbed through
    # to _make_handler (the param already existed on the handler factory).
    panels = list(panels)
    if not panels:
        raise ValueError("serve() called with no panels")

    template_dir = Path(template_dir) if template_dir else Path(__file__).parent
    for asset in ("dashboard.html", "dashboard.css", "dashboard.js"):
        if not (template_dir / asset).exists():
            raise FileNotFoundError(f"missing template asset: {template_dir / asset}")

    cache = _Cache()
    if auto_port:
        actual_port = _find_free_port(port, host=host)
        if actual_port != port:
            print(f"[local-dashboard-builder] port {port} busy; using {actual_port}")
        port = actual_port

    handler_cls = _make_handler(
        panels, cache, template_dir, title, subtitle, refresh_ms,
        headline=headline, controls=controls, post_routes=post_routes,
        get_routes=get_routes,
        hidden_panels=hidden_panels,
    )
    server = ThreadingHTTPServer((host, port), handler_cls)
    url = f"http://{host}:{port}"
    print(f"[local-dashboard-builder] serving {url}")
    print(f"  panels: {', '.join(p.id for p in panels)}")
    print("  endpoints: /, /api/data, /api/panel/<id>, /api/cache, /api/health")
    print("  keys in the browser: R=refresh, Esc=pause auto-refresh")
    print("  Ctrl+C to stop")

    if open_browser:
        def _try_open() -> None:
            # Guarded because headless environments have no registered browser
            # and webbrowser.open() can raise or hang.
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Timer(0.6, _try_open).start()

    try:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[local-dashboard-builder] shutting down")
    finally:
        server.server_close()


def _demo() -> None:
    """Minimal working example so `python server.py` does something."""
    # reconstructed from pyc reference (source was truncated on disk)
    def hello() -> dict:
        return {"stats": [{"value": 42, "label": "The Answer", "hint": "demo panel"}]}
    serve(
        [Panel(id="hello", title="Hello", kind="metric", span=12, ttl=60, collector=hello)],
        title="local-dashboard-builder demo",
        subtitle="replace this with your own panels",
    )


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    _demo()

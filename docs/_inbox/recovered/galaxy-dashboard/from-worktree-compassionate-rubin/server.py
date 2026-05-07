"""
server.py — Static + JSON server for the Context Galaxy.

Serves:
  GET /                  → index.html
  GET /galaxy.js         → main scene
  GET /galaxy.css        → styles
  GET /api/atlas         → fresh atlas.json (TTL-cached, ?include=... + ?repo=...)
  GET /api/repos         → list of available BCOS-mature repos to swap between
  GET /api/doc           → raw markdown for one docs/ file (?repo=...&path=docs/...)

Stdlib http.server. Zero deps. Same pattern as bcos-dashboard/server.py.
"""

from __future__ import annotations

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from generate import DEFAULT_REPO, GITHUB_ROOT, build_galaxy_atlas, resolve_repo  # noqa: E402

PORT = int(os.environ.get("BCOS_GALAXY_PORT", "8094"))
TTL_SECONDS = 30

_STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/galaxy.js": ("galaxy.js", "application/javascript; charset=utf-8"),
    "/galaxy.css": ("galaxy.css", "text/css; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    "/diag": ("diag.html", "text/html; charset=utf-8"),
    "/diag.html": ("diag.html", "text/html; charset=utf-8"),
    "/diag2": ("diag2.html", "text/html; charset=utf-8"),
    "/diag2.html": ("diag2.html", "text/html; charset=utf-8"),
}

_REPO_CANDIDATES = [
    "theo-delivery-os",
    "theo-portfolio",
    "the-leverage-ai",
    "tystiq",
    "project-nurture-trunk",
    "theo-gtm",
    "business-context-os-dev",
]
_cache: dict[str, tuple[float, dict]] = {}


def _cached_atlas(repo: Path, include_key: str, include: set[str] | None) -> dict:
    key = f"{repo}|{include_key}"
    now = time.time()
    if key in _cache:
        ts, data = _cache[key]
        if now - ts < TTL_SECONDS:
            return data
    data = build_galaxy_atlas(repo_root=repo, include=include)
    _cache[key] = (now, data)
    return data


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[galaxy] {fmt % args}\n")

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, rel: str, ctype: str) -> None:
        p = _HERE / rel
        if not p.is_file():
            self.send_error(404, f"missing: {rel}")
            return
        body = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _repo_from_query(self, qs: dict) -> Path | None:
        repo_name = (qs.get("repo") or [DEFAULT_REPO.name])[0]
        repo = resolve_repo(repo_name)
        if not repo.is_dir() or not (repo / "docs").is_dir():
            self._send_json({"error": f"repo not found: {repo_name}"}, 404)
            return None
        return repo

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path in _STATIC:
            rel, ctype = _STATIC[path]
            self._send_static(rel, ctype)
            return

        if path == "/api/atlas":
            qs = parse_qs(parsed.query)
            inc_raw = (qs.get("include") or ["active"])[0]
            if inc_raw == "all":
                include: set[str] | None = None
                include_key = "all"
            else:
                include = {x for x in inc_raw.split(",") if x}
                include_key = ",".join(sorted(include))
            repo = self._repo_from_query(qs)
            if repo is None:
                return
            try:
                atlas = _cached_atlas(repo, include_key, include)
            except Exception as exc:  # noqa: BLE001
                self._send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)
                return
            self._send_json(atlas)
            return

        if path == "/api/doc":
            qs = parse_qs(parsed.query)
            repo = self._repo_from_query(qs)
            if repo is None:
                return
            rel_path = (qs.get("path") or [""])[0]
            if not rel_path:
                self._send_json({"error": "missing path"}, 400)
                return
            target = (repo / rel_path).resolve()
            docs_root = (repo / "docs").resolve()
            try:
                inside_docs = target.is_relative_to(docs_root)
            except AttributeError:
                inside_docs = str(target).startswith(str(docs_root))
            if not inside_docs or target.suffix.lower() != ".md":
                self._send_json({"error": "path must point to a docs/*.md file"}, 400)
                return
            if not target.is_file():
                self._send_json({"error": f"doc not found: {rel_path}"}, 404)
                return
            try:
                text = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = target.read_text(encoding="utf-8-sig")
            self._send_json({
                "repo": repo.name,
                "path": target.relative_to(repo).as_posix(),
                "name": target.name,
                "content": text,
                "size_bytes": target.stat().st_size,
            })
            return

        if path == "/api/repos":
            repos = []
            for name in _REPO_CANDIDATES:
                p = GITHUB_ROOT / name
                if p.is_dir() and (p / "docs").is_dir():
                    repos.append({
                        "id": name,
                        "label": name,
                        "is_default": name == DEFAULT_REPO.name,
                    })
            self._send_json({"repos": repos, "default": DEFAULT_REPO.name})
            return

        self.send_error(404, f"not found: {path}")


def serve(port: int = PORT) -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    sys.stderr.write(
        f"[galaxy] serving on http://127.0.0.1:{port}/ "
        f"(default repo: {DEFAULT_REPO.name})\n"
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("[galaxy] shutting down\n")
        httpd.server_close()


if __name__ == "__main__":
    serve()

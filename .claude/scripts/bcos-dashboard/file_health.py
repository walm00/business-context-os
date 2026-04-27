"""
file_health.py — Aggregated file-health checks across the BCOS docs tree.

Scans `docs/` for common issues the dispatcher would also catch on its
next run. Surface-and-fix loop is deliberately narrow in v1:

Detected:
  - Frontmatter issues (missing required fields, invalid type)
  - Stale docs (last-updated > `STALE_DAYS` ago, from the frontmatter
    field — we deliberately don't consult git log so the dashboard
    stays stdlib-only; the dispatcher's own index-health does the
    git-aware version)

Fixable from the UI (whitelisted):
  - eof-newline           — ensure file ends with exactly one \\n
  - trailing-whitespace   — strip trailing spaces on every line
  - missing-last-updated  — inject today's UTC date into frontmatter

Not in v1 (out of scope for a light standalone reader):
  - orphaned files (requires parsing every link in the repo)
  - broken cross-references (same)
  - frontmatter-field-order (edge cases in multi-line values)

We intentionally mirror a SUBSET of validate_frontmatter.py's schema.
BCOS consumers may override REQUIRED_FIELDS / VALID_TYPES via the
BCOS_DOC_REQUIRED and BCOS_DOC_TYPES env vars (comma-separated).
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from single_repo import REPO_ROOT  # noqa: E402

DOCS_ROOT = REPO_ROOT / "docs"
STALE_DAYS = 30                 # last-updated older than this → stale
SKIP_DIRS = {"_inbox", "_planned", "_archive", "_collections", "_bcos-framework"}

_DEFAULT_REQUIRED = ("name", "type", "cluster", "version", "status", "created", "last-updated")
_DEFAULT_TYPES = ("context", "process", "policy", "reference", "playbook")


def _env_tuple(name: str, default: tuple) -> tuple:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    parts = tuple(p.strip() for p in raw.split(",") if p.strip())
    return parts or default


REQUIRED_FIELDS = _env_tuple("BCOS_DOC_REQUIRED", _DEFAULT_REQUIRED)
VALID_TYPES = _env_tuple("BCOS_DOC_TYPES", _DEFAULT_TYPES)

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_WRITE_LOCK = Lock()


@dataclass
class Finding:
    path: str          # relative to REPO_ROOT, forward-slash
    issue: str         # short category key
    detail: str        # human-readable specifics
    fix_id: str | None # whitelist fix id if auto-fixable, else None


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------

def _iter_docs() -> list[Path]:
    if not DOCS_ROOT.is_dir():
        return []
    out: list[Path] = []
    for p in DOCS_ROOT.rglob("*.md"):
        parts = set(p.relative_to(DOCS_ROOT).parts)
        if parts & SKIP_DIRS:
            continue
        # Dot-files are system-generated artifacts (.wake-up-context.md,
        # .session-diary.md, .onboarding-checklist.md, .portfolio-aggregate.md).
        # They legitimately don't have frontmatter — skip entirely.
        if p.name.startswith("."):
            continue
        out.append(p)
    return out


def _parse_frontmatter(text: str) -> dict | None:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    block = m.group(1)
    out: dict = {}
    # Minimal YAML — key: value per line, ignore nested blocks
    # (enough to validate required scalar fields).
    for line in block.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith(" ") or line.startswith("\t"):
            continue  # nested — skip for required-field purposes
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def _days_since(iso_date: str, now: datetime | None = None) -> int | None:
    now = now or datetime.now(timezone.utc)
    if not iso_date:
        return None
    iso_date = iso_date.strip('"').strip("'").strip()
    try:
        # Accept YYYY-MM-DD and full ISO.
        if len(iso_date) == 10:
            dt = datetime.fromisoformat(iso_date + "T00:00:00+00:00")
        else:
            dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (now - dt.astimezone(timezone.utc)).days


def scan_frontmatter() -> list[Finding]:
    out: list[Finding] = []
    for p in _iter_docs():
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        # Auto-generated files (document-index.md is the canonical exception)
        # legitimately lack frontmatter. Skip any file explicitly marked as such.
        if rel.endswith("/document-index.md") or rel == "docs/document-index.md":
            continue
        meta = _parse_frontmatter(text)
        if meta is None:
            out.append(Finding(rel, "missing_frontmatter", "no YAML frontmatter block", None))
            continue
        missing = [f for f in REQUIRED_FIELDS if f not in meta or not meta[f]]
        if "last-updated" in missing and "created" in meta:
            # The dispatcher's 'missing-last-updated' fix can populate this
            # from today's date. Surface it with the fix-id.
            out.append(Finding(rel, "missing_last_updated",
                               "frontmatter has no 'last-updated' field", "missing-last-updated"))
            missing = [m for m in missing if m != "last-updated"]
        if missing:
            out.append(Finding(
                rel, "missing_field",
                "missing required: " + ", ".join(missing),
                None,
            ))
        doc_type = meta.get("type", "").strip("\"'")
        if doc_type and VALID_TYPES and doc_type not in VALID_TYPES:
            out.append(Finding(
                rel, "invalid_type",
                f"type '{doc_type}' not in {list(VALID_TYPES)}",
                None,
            ))
    return out


def scan_stale(days: int = STALE_DAYS) -> list[Finding]:
    out: list[Finding] = []
    for p in _iter_docs():
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        meta = _parse_frontmatter(text)
        if not meta:
            continue
        age = _days_since(meta.get("last-updated", ""))
        if age is not None and age >= days:
            out.append(Finding(
                rel, "stale",
                f"last-updated {age} days ago",
                None,
            ))
    return out


def _scan_textual_issues() -> list[Finding]:
    """Cheap byte-level checks for the two safest auto-fixes."""
    out: list[Finding] = []
    for p in _iter_docs():
        try:
            raw = p.read_bytes()
        except Exception:
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        # eof-newline
        if not raw.endswith(b"\n"):
            out.append(Finding(rel, "eof_newline", "file does not end with newline", "eof-newline"))
        # trailing whitespace
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        lines = text.splitlines()
        bad = sum(1 for ln in lines if ln != ln.rstrip(" \t"))
        if bad > 0:
            out.append(Finding(rel, "trailing_ws",
                               f"{bad} line(s) with trailing whitespace",
                               "trailing-whitespace"))
    return out


def collect() -> dict:
    fm = scan_frontmatter()
    stale = scan_stale()
    text = _scan_textual_issues()
    categories = {
        "frontmatter": [f.__dict__ for f in fm],
        "stale":       [f.__dict__ for f in stale],
        "textual":     [f.__dict__ for f in text],
    }
    total = sum(len(v) for v in categories.values())
    fixable = sum(1 for lst in categories.values() for f in lst if f.get("fix_id"))
    return {
        "categories": categories,
        "total": total,
        "fixable": fixable,
        "stale_threshold_days": STALE_DAYS,
    }


# ---------------------------------------------------------------------------
# Fixers (whitelisted IDs only)
# ---------------------------------------------------------------------------

def _safe_doc_path(rel: str) -> Path | None:
    """Guardrail: only operate on files inside REPO_ROOT/docs."""
    if not rel or ".." in Path(rel).parts:
        return None
    p = (REPO_ROOT / rel).resolve()
    try:
        p.relative_to(DOCS_ROOT.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None


def fix_eof_newline(rel_path: str) -> dict:
    p = _safe_doc_path(rel_path)
    if p is None:
        return {"ok": False, "error": "file not found or outside docs/"}
    with _WRITE_LOCK:
        raw = p.read_bytes()
        if raw.endswith(b"\n"):
            return {"ok": True, "status": "already_clean"}
        p.write_bytes(raw + b"\n")
    return {"ok": True, "status": "fixed", "fix_id": "eof-newline"}


def fix_trailing_whitespace(rel_path: str) -> dict:
    p = _safe_doc_path(rel_path)
    if p is None:
        return {"ok": False, "error": "file not found or outside docs/"}
    with _WRITE_LOCK:
        text = p.read_text(encoding="utf-8")
        # Preserve line endings pattern of the original file.
        nl = "\r\n" if "\r\n" in text else "\n"
        lines = text.split(nl)
        cleaned = [ln.rstrip(" \t") for ln in lines]
        if cleaned == lines:
            return {"ok": True, "status": "already_clean"}
        p.write_text(nl.join(cleaned), encoding="utf-8")
    return {"ok": True, "status": "fixed", "fix_id": "trailing-whitespace"}


def fix_missing_last_updated(rel_path: str) -> dict:
    p = _safe_doc_path(rel_path)
    if p is None:
        return {"ok": False, "error": "file not found or outside docs/"}
    with _WRITE_LOCK:
        text = p.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(text)
        if not m:
            return {"ok": False, "error": "no frontmatter to edit"}
        block = m.group(1)
        if re.search(r"(?m)^last-updated\s*:", block):
            return {"ok": True, "status": "already_present"}
        today = datetime.now(timezone.utc).date().isoformat()
        new_block = block.rstrip() + f"\nlast-updated: \"{today}\""
        new_text = text.replace(m.group(0), f"---\n{new_block}\n---\n", 1)
        p.write_text(new_text, encoding="utf-8")
    return {"ok": True, "status": "fixed", "fix_id": "missing-last-updated"}


FIXERS = {
    "eof-newline":           fix_eof_newline,
    "trailing-whitespace":   fix_trailing_whitespace,
    "missing-last-updated":  fix_missing_last_updated,
}


def apply_fix(fix_id: str, rel_path: str) -> dict:
    fn = FIXERS.get(fix_id)
    if not fn:
        return {"ok": False, "error": f"unknown fix id: {fix_id}", "known": sorted(FIXERS.keys())}
    return fn(rel_path)

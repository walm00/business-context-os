"""
actions_resolved.py — Persist "mark done" clicks on actions inbox items.

When the user marks an action done in the dashboard, we append one line
to `.claude/hook_state/actions-resolved.jsonl` with a stable fingerprint
of the item title. The actions collector then filters those fingerprints
out of the next render, so a resolved item doesn't keep reappearing.

Resolution is by fingerprint (sha1 of normalized title), NOT by full
text — digests and diaries can phrase the same finding slightly
differently between runs, and we want "mark done" to stick when that
happens.

File shape (append-only, one JSON per line):
    {"ts":"<ISO-utc>","fingerprint":"<sha1>","title":"<original>","source_job":"<job-id or null>"}

Retention: 90 days — beyond that, fingerprints are dropped on read.
The file itself is not pruned automatically (keeps a long audit trail);
prune by rotation if it grows.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Resolve repo root the same way single_repo.py does — keep one source of truth.
from single_repo import REPO_ROOT  # noqa: E402

STORE_PATH = REPO_ROOT / ".claude" / "hook_state" / "actions-resolved.jsonl"
RETENTION_DAYS = 90

_WRITE_LOCK = Lock()


def _normalize(title: str) -> str:
    """Collapse whitespace + lowercase to make fingerprint robust against
    tiny whitespace / casing differences across digest regenerations."""
    t = (title or "").strip().lower()
    # Strip trailing ellipses and excess punctuation
    t = re.sub(r"[\.…]+$", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def fingerprint(title: str) -> str:
    return hashlib.sha1(_normalize(title).encode("utf-8")).hexdigest()[:16]


def _parse_ts(raw: str | None) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        iso = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_resolved_set() -> set[str]:
    """Return fingerprints resolved within the retention window.

    Entries older than RETENTION_DAYS are skipped silently — the raw
    file still contains them for audit, but the dashboard treats them
    as expired (item may reappear if the finding is still present).
    """
    if not STORE_PATH.is_file():
        return set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    out: set[str] = set()
    try:
        with STORE_PATH.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                dt = _parse_ts(obj.get("ts"))
                if dt is None or dt < cutoff:
                    continue
                fp = obj.get("fingerprint")
                if isinstance(fp, str) and fp:
                    out.add(fp)
    except Exception:
        return out
    return out


def is_resolved(title: str) -> bool:
    return fingerprint(title) in load_resolved_set()


def mark_resolved(title: str, source_job: str | None = None) -> dict:
    """Append a resolution line. Returns the written entry (for the API
    response). Creates the parent directory if needed, silently ignores
    duplicates."""
    if not title or not isinstance(title, str):
        return {"ok": False, "error": "title required"}
    fp = fingerprint(title)
    if fp in load_resolved_set():
        return {"ok": True, "fingerprint": fp, "status": "already_resolved"}
    entry = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "fingerprint": fp,
        "title": title.strip(),
        "source_job": source_job or None,
    }
    with _WRITE_LOCK:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with STORE_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"ok": True, "fingerprint": fp, "status": "resolved", "entry": entry}


def unmark_resolved(fp_or_title: str) -> dict:
    """Rewrite the store without the given fingerprint (undo).

    Accepts either a fingerprint directly or a title (which we hash).
    Writes to a temp file then atomically renames.
    """
    if not fp_or_title:
        return {"ok": False, "error": "fingerprint or title required"}
    target_fp = fp_or_title if re.fullmatch(r"[0-9a-f]{16}", fp_or_title) else fingerprint(fp_or_title)
    if not STORE_PATH.is_file():
        return {"ok": True, "status": "nothing_to_remove"}

    kept: list[str] = []
    removed = 0
    with STORE_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            raw = line.rstrip("\n")
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except Exception:
                kept.append(raw)
                continue
            if obj.get("fingerprint") == target_fp:
                removed += 1
                continue
            kept.append(raw)

    if removed == 0:
        return {"ok": True, "fingerprint": target_fp, "status": "not_found"}

    tmp = STORE_PATH.with_suffix(".jsonl.tmp")
    with _WRITE_LOCK:
        with tmp.open("w", encoding="utf-8") as fh:
            for ln in kept:
                fh.write(ln + "\n")
        os.replace(tmp, STORE_PATH)
    return {"ok": True, "fingerprint": target_fp, "status": "removed", "count": removed}

"""Safe JSONL loader with corruption tracking.

Most BCOS loaders read JSONL with `try: json.loads(line) except: continue`,
which silently drops malformed lines. On Windows, concurrent appends to a
JSONL file are NOT atomic — a race can produce one mangled line, which then
silently disappears from the auditor's denominator and skews the
self-learning ladder's reversal-rate computation.

This module replaces the pattern with one that counts drops, so the
dispatcher can surface a `data-corruption-detected` finding when a loader
quietly threw away rows. No behaviour change on clean data.

Migration: replace

    out = []
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out

with

    rows, report = safe_load_jsonl(p)
    if report.dropped:
        log_corruption(report)   # or: include in dispatcher findings
    return rows
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CorruptionReport:
    path: str
    dropped: int
    sample_offsets: list[int]  # byte offsets of the first few bad lines

    def as_finding(self) -> dict:
        """Shape compatible with the dispatcher's `actions_needed` finding format."""
        return {
            "type": "data-corruption-detected",
            "severity": "amber" if self.dropped < 5 else "red",
            "path": self.path,
            "dropped_lines": self.dropped,
            "sample_offsets": self.sample_offsets[:3],
            "note": (
                f"{self.dropped} malformed JSONL line(s) dropped from {self.path}. "
                "Likely cause: concurrent append on Windows (no atomic O_APPEND) "
                "or an interrupted write. Inspect the file at the listed byte offsets."
            ),
        }


def safe_load_jsonl(path: Path) -> tuple[list[dict], CorruptionReport]:
    """Load a JSONL file, returning rows and a corruption report.

    Empty/missing files return empty results with `dropped=0` (not an error).
    """
    rows: list[dict] = []
    bad_offsets: list[int] = []
    if not path.is_file():
        return rows, CorruptionReport(str(path), 0, [])
    offset = 0
    with path.open("rb") as fh:
        for raw in fh:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                offset += len(raw)
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                bad_offsets.append(offset)
            offset += len(raw)
    return rows, CorruptionReport(str(path), len(bad_offsets), bad_offsets)


def safe_load_jsonl_rows(path: Path) -> list[dict]:
    """Backwards-compatible drop-in: same signature as the old `_load_rows`.

    Drops the corruption report; loaders that don't yet surface findings can
    use this and migrate later.
    """
    rows, _ = safe_load_jsonl(path)
    return rows

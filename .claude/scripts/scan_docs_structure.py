#!/usr/bin/env python3
"""
scan_docs_structure.py — structural scan for `index-health` step 5/6.

Walks docs/ (active zone only), checks every doc against the 8 issue types
defined in .claude/skills/schedule-dispatcher/references/job-index-health.md,
optionally applies whitelisted auto-fixes inline, and emits a JSON result
the dispatcher can fold straight into its digest.

This script exists so the index-health job has a backing _run command for
step 5 instead of a prose _claude_step. That stops Claude from improvising
scratch helpers like `_xref_check.py` inside `.claude/` (which trip the
sensitive-file UI even when the path is allow-listed).

Detects:
  - missing-frontmatter
  - missing-required-field
  - missing-last-updated
  - frontmatter-field-order
  - broken-xref
  - broken-xref-single-candidate
  - trailing-whitespace
  - eof-newline

Auto-fix IDs honoured via --apply-whitelist (comma-separated):
  missing-last-updated, frontmatter-field-order, trailing-whitespace,
  eof-newline, broken-xref-single-candidate

Usage:
  python .claude/scripts/scan_docs_structure.py --json
  python .claude/scripts/scan_docs_structure.py --json \\
      --apply-whitelist trailing-whitespace,eof-newline,missing-last-updated

Exit code: 0 always (diagnostic, not CI). Errors surface via verdict=error.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from context_index import (  # noqa: E402
    FRONTMATTER_RE,
    REQUIRED_FIELDS,
    _zone_for,
    iter_docs,
    parse_frontmatter,
)

CANONICAL_FIELD_ORDER = list(REQUIRED_FIELDS)

# URI schemes that are external by design — never flag as broken-xref.
URI_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*:", re.IGNORECASE)

# Markdown inline link: [text](href) — no images, no reference-style.
MD_LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+?)(?:\s+\"[^\"]*\")?\)")


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


def _iter_active(root: Path) -> list[Path]:
    """Return docs/**/*.md whose zone is 'active' (skip framework/wiki/inbox/_*-custom/dotfiles/generated)."""
    out: list[Path] = []
    for path in iter_docs(root):
        rel = path.relative_to(root).as_posix()
        if _zone_for(rel) == "active":
            out.append(path)
    return out


def _build_basename_index(root: Path) -> dict[str, list[str]]:
    """Map basename → list of rel-paths for ALL docs/**/*.md (incl. wiki/inbox), used by broken-xref-single-candidate."""
    docs_root = root / "docs"
    index: dict[str, list[str]] = defaultdict(list)
    if not docs_root.is_dir():
        return index
    for path in docs_root.rglob("*.md"):
        rel = path.relative_to(root).as_posix()
        index[path.name].append(rel)
    return index


def _check_frontmatter_field_order(text: str) -> bool:
    """Return True iff frontmatter has all required fields AND they appear in canonical order.

    Optional fields may interleave; only the relative order of required fields is checked.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return True  # caller handles missing-frontmatter
    field_order: list[str] = []
    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")):
            continue
        key, sep, _ = raw.partition(":")
        if not sep:
            continue
        field_order.append(key.strip())
    present_required = [f for f in field_order if f in REQUIRED_FIELDS]
    if set(present_required) != set(REQUIRED_FIELDS):
        return True  # missing fields → not a field-order issue
    return present_required == CANONICAL_FIELD_ORDER


def _check_trailing_whitespace(text: str) -> bool:
    return any(line != line.rstrip(" \t") for line in text.splitlines())


def _check_eof_newline(text: str) -> bool:
    """Return True iff file ends with exactly one trailing newline."""
    if not text:
        return False
    return text.endswith("\n") and not text.endswith("\n\n")


def _extract_links(text: str) -> list[tuple[str, str]]:
    """Return list of (href, fragment) — fragment is the part after '#' if present."""
    out: list[tuple[str, str]] = []
    # Strip frontmatter so YAML colons don't trip the regex
    body = FRONTMATTER_RE.sub("", text, count=1) if FRONTMATTER_RE.match(text) else text
    for m in MD_LINK_RE.finditer(body):
        href = m.group(1).strip()
        if not href:
            continue
        if href.startswith("#"):  # pure fragment
            continue
        if URI_SCHEME_RE.match(href):  # http:, mailto:, computer:, etc.
            continue
        target, _, _frag = href.partition("#")
        if target:
            out.append((target, href))
    return out


def _resolve_link(href: str, source_rel: str, root: Path) -> Path | None:
    """Resolve a relative or repo-absolute markdown link to an on-disk path. Returns None if escapes repo."""
    target = href.split("#", 1)[0]
    if not target:
        return None
    if target.startswith("/"):
        candidate = (root / target.lstrip("/")).resolve()
    else:
        source_dir = (root / source_rel).resolve().parent
        candidate = (source_dir / target).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


# ---------------------------------------------------------------------------
# Fixers (in-memory transforms; caller writes back if changed)
# ---------------------------------------------------------------------------


def _fix_trailing_whitespace(text: str) -> str:
    # Preserve original line-ending style by stripping per-line and re-joining
    lines = text.splitlines(keepends=True)
    fixed = []
    for line in lines:
        if line.endswith("\r\n"):
            fixed.append(line[:-2].rstrip(" \t") + "\r\n")
        elif line.endswith("\n"):
            fixed.append(line[:-1].rstrip(" \t") + "\n")
        else:
            fixed.append(line.rstrip(" \t"))
    return "".join(fixed)


def _fix_eof_newline(text: str) -> str:
    return text.rstrip("\n") + "\n" if text else "\n"


def _fix_missing_last_updated(text: str, today: str) -> str:
    """Insert `last-updated: <today>` into frontmatter (after `created:` if present, else at end of block)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text
    block = m.group(1)
    new_field = f"last-updated: \"{today}\""
    lines = block.splitlines()
    insert_at = len(lines)
    for i, raw in enumerate(lines):
        if raw.strip().startswith("created:"):
            insert_at = i + 1
            break
    lines.insert(insert_at, new_field)
    new_block = "\n".join(lines)
    return text[: m.start(1)] + new_block + text[m.end(1) :]


def _fix_frontmatter_field_order(text: str) -> str:
    """Reorder required fields into canonical order; leave everything else where it is."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text
    block = m.group(1)
    lines = block.splitlines()

    # Capture each required field's full line (including any continuation indented lines)
    captured: dict[str, list[str]] = {}
    keep: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        stripped = raw.lstrip()
        key, sep, _rest = raw.partition(":")
        bare_key = key.strip()
        if sep and not raw.startswith((" ", "\t")) and bare_key in REQUIRED_FIELDS:
            chunk = [raw]
            j = i + 1
            while j < n and lines[j].startswith((" ", "\t")):
                chunk.append(lines[j])
                j += 1
            captured[bare_key] = chunk
            i = j
            continue
        keep.append(raw)
        i += 1

    if set(captured.keys()) != set(REQUIRED_FIELDS):
        return text  # safety: don't reorder if any required field is missing

    canonical_chunk: list[str] = []
    for f in CANONICAL_FIELD_ORDER:
        canonical_chunk.extend(captured[f])

    new_block = "\n".join(canonical_chunk + keep)
    return text[: m.start(1)] + new_block + text[m.end(1) :]


def _fix_broken_xref_single_candidate(text: str, source_rel: str, broken: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Rewrite each broken link in `broken` (list of (old_href, new_rel_path)) inside `text`."""
    rewrites: list[str] = []
    new_text = text
    for old_href, new_rel in broken:
        # Compute new href relative to source
        src_dir = Path(source_rel).parent
        try:
            new_href = Path(new_rel).resolve().relative_to((REPO_ROOT / src_dir).resolve()).as_posix() if False else _relpath(new_rel, source_rel)
        except Exception:
            continue
        # Preserve fragment if present
        frag = ""
        if "#" in old_href:
            frag = "#" + old_href.split("#", 1)[1]
        # Replace only inside markdown link parens to avoid clobbering code samples
        pattern = re.compile(
            r"(\]\()" + re.escape(old_href) + r"(\s+\"[^\"]*\")?(\))"
        )
        replacement = r"\g<1>" + new_href + frag + r"\g<2>\g<3>"
        new_text2, n = pattern.subn(replacement, new_text)
        if n:
            new_text = new_text2
            rewrites.append(f"{old_href} → {new_href}")
    return new_text, rewrites


def _relpath(target_rel: str, source_rel: str) -> str:
    """POSIX relpath from source's directory to target."""
    from os.path import relpath as _rp
    src_dir = Path(source_rel).parent.as_posix() or "."
    return _rp(target_rel, start=src_dir).replace("\\", "/")


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------


def scan(root: Path, apply_whitelist: set[str], today: str) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    auto_fixed: list[str] = []
    actions_needed: list[str] = []
    fixed_counts: dict[str, int] = defaultdict(int)

    basename_index = _build_basename_index(root)
    active_docs = _iter_active(root)

    for path in active_docs:
        rel = path.relative_to(root).as_posix()
        try:
            original = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append({"id": "read-error", "path": rel, "detail": str(exc)})
            actions_needed.append(f"read-error: {rel} — {exc}")
            continue

        text = original

        meta = parse_frontmatter(text)
        if meta is None:
            findings.append({"id": "missing-frontmatter", "path": rel})
            actions_needed.append(f"missing-frontmatter: {rel} — no YAML block")
            # Without frontmatter the other field-level checks don't apply
        else:
            missing = [f for f in REQUIRED_FIELDS if not meta.get(f)]
            if missing:
                if missing == ["last-updated"]:
                    if "missing-last-updated" in apply_whitelist:
                        text = _fix_missing_last_updated(text, today)
                        auto_fixed.append(f"missing-last-updated in {rel}")
                        fixed_counts["missing-last-updated"] += 1
                    else:
                        findings.append({"id": "missing-last-updated", "path": rel})
                        actions_needed.append(f"missing-last-updated: {rel}")
                else:
                    findings.append({"id": "missing-required-field", "path": rel, "fields": missing})
                    actions_needed.append(f"missing-required-field: {rel} — {', '.join(missing)}")
            elif not _check_frontmatter_field_order(text):
                if "frontmatter-field-order" in apply_whitelist:
                    text = _fix_frontmatter_field_order(text)
                    auto_fixed.append(f"frontmatter-field-order in {rel}")
                    fixed_counts["frontmatter-field-order"] += 1
                else:
                    findings.append({"id": "frontmatter-field-order", "path": rel})
                    actions_needed.append(f"frontmatter-field-order: {rel}")

        # Broken-xref scan
        broken_single: list[tuple[str, str]] = []
        for target, href in _extract_links(text):
            resolved = _resolve_link(href, rel, root)
            if resolved is None:
                continue
            if resolved.exists():
                continue
            # Broken — try single-candidate resolution
            basename = Path(target).name
            candidates = basename_index.get(basename, [])
            if len(candidates) == 1 and candidates[0] != rel:
                if "broken-xref-single-candidate" in apply_whitelist:
                    broken_single.append((href, candidates[0]))
                else:
                    findings.append({"id": "broken-xref-single-candidate", "path": rel, "link": href, "candidate": candidates[0]})
                    actions_needed.append(f"broken-xref-single-candidate: {rel} — {href} → {candidates[0]} (auto-fixable)")
            else:
                findings.append({"id": "broken-xref", "path": rel, "link": href, "candidates": candidates})
                if candidates:
                    actions_needed.append(f"broken-xref: {rel} — {href} (ambiguous: {len(candidates)} candidates)")
                else:
                    actions_needed.append(f"broken-xref: {rel} — {href} (no candidate)")

        if broken_single:
            text, rewrites = _fix_broken_xref_single_candidate(text, rel, broken_single)
            for r in rewrites:
                auto_fixed.append(f"broken-xref-single-candidate in {rel}: {r}")
                fixed_counts["broken-xref-single-candidate"] += 1

        # Whitespace / EOF (do these last so they normalise any insertions above)
        if _check_trailing_whitespace(text):
            if "trailing-whitespace" in apply_whitelist:
                text = _fix_trailing_whitespace(text)
                auto_fixed.append(f"trailing-whitespace in {rel}")
                fixed_counts["trailing-whitespace"] += 1
            else:
                findings.append({"id": "trailing-whitespace", "path": rel})
                actions_needed.append(f"trailing-whitespace: {rel}")

        if not _check_eof_newline(text):
            if "eof-newline" in apply_whitelist:
                text = _fix_eof_newline(text)
                auto_fixed.append(f"eof-newline in {rel}")
                fixed_counts["eof-newline"] += 1
            else:
                findings.append({"id": "eof-newline", "path": rel})
                actions_needed.append(f"eof-newline: {rel}")

        if text != original:
            path.write_text(text, encoding="utf-8")

    # Verdict
    has_critical = any(f["id"] in {"missing-frontmatter"} for f in findings)
    if not findings and not actions_needed:
        verdict = "green"
    elif has_critical:
        verdict = "red"
    else:
        verdict = "amber" if actions_needed else "green"

    summary_bits = []
    if active_docs:
        summary_bits.append(f"{len(active_docs)} active doc(s) scanned")
    if fixed_counts:
        summary_bits.append("auto-fixed: " + ", ".join(f"{k}×{v}" for k, v in sorted(fixed_counts.items())))
    if not findings and not auto_fixed:
        summary_bits.append("no findings")

    return {
        "verdict": verdict,
        "findings_count": len(findings) + len(auto_fixed),
        "auto_fixed": auto_fixed,
        "actions_needed": actions_needed,
        "findings": findings,
        "notes": " · ".join(summary_bits),
        "scanned": len(active_docs),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true", help="Emit JSON (default)")
    p.add_argument("--apply-whitelist", default="", help="Comma-separated fix IDs to apply silently")
    p.add_argument("--root", default=None, help="Repo root (defaults to script's parent of parent)")
    args = p.parse_args()

    root = Path(args.root).resolve() if args.root else REPO_ROOT
    whitelist = {x.strip() for x in args.apply_whitelist.split(",") if x.strip()}
    today = _dt.date.today().isoformat()

    try:
        result = scan(root, whitelist, today)
    except Exception as exc:  # noqa: BLE001
        result = {
            "verdict": "error",
            "findings_count": 0,
            "auto_fixed": [],
            "actions_needed": [],
            "findings": [],
            "notes": f"scan_docs_structure error: {exc}",
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

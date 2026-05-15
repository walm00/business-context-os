#!/usr/bin/env python3
"""
promote_outputs.py — Phase 5 writer for the `promote-outputs` headless action.

Triggered from the dispatcher's `job-missing-outputs-declaration` chip
("Yes, always"). Idempotently declares paths a job actually wrote into:

  1. .claude/quality/schedule-config.json   -> jobs.<name>.outputs
  2. .claude/skills/schedule-dispatcher/references/job-<name>.md  -> ## Outputs

The same validation rules the dispatcher's Step 7b applies are enforced here
so a path that's not auto-commit-eligible can't slip in via the chip.

CLI:
    python promote_outputs.py --job <name> --paths <p1,p2,...>

Exit codes:
    0  success (updated or no-op)
    2  validation failure (one or more paths rejected)
    3  unknown job name
    4  spec file missing the `## Outputs` section
    5  (umbrella mirror only) path resolves outside umbrella host
    1  unexpected / I-O error

stderr on validation failure is a SINGLE JSON line matching the
`job-outputs-validation-error` typed-event finding_attrs shape:
    {"finding_type":"job-outputs-validation-error",
     "job":"<name>","invalid_entries":[...],"reason":"<one-line>"}

stdout on success is a single JSON line:
    {"status":"updated"|"noop","job":"<name>","added":[...],"total":N}

DERIVED-ARTIFACT INVARIANT: this script is deterministic — same args + same
prior state yield identical bytes. Atomic JSON write via os.replace. Spec
section rewrite preserves frontmatter and surrounding sections verbatim.

stdlib only. No external deps.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

ALLOWED_ROOTS = ("docs/", ".claude/")
MAX_LITERALS = 20
MAX_GLOBS = 5
GLOB_CHARS = re.compile(r"[*?\[]")


def find_repo_root(start: Path | None = None) -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        p = Path(env).resolve()
        if (p / ".claude").is_dir():
            return p
    cur = (start or Path.cwd()).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / ".claude" / "quality").is_dir():
            return candidate
    raise SystemExit(_err_io(f"could not locate .claude/quality from {cur}"))


def _err_io(msg: str) -> str:
    sys.stderr.write(json.dumps({"reason": msg}) + "\n")
    return msg


def _emit_validation_error(job: str, invalid: list[str], reason: str) -> int:
    payload = {
        "finding_type": "job-outputs-validation-error",
        "job": job,
        "invalid_entries": invalid,
        "reason": reason,
    }
    sys.stderr.write(json.dumps(payload, sort_keys=True) + "\n")
    return 2


def is_glob(p: str) -> bool:
    return bool(GLOB_CHARS.search(p))


def validate_path(p: str) -> str | None:
    """Return None if valid; else a one-line reason string."""
    if not p:
        return "empty path"
    if "\\" in p:
        return f"backslash not allowed (POSIX-relative paths only): {p!r}"
    if p.startswith("/"):
        return f"absolute path not allowed: {p!r}"
    # Windows drive letter
    if len(p) >= 2 and p[1] == ":":
        return f"drive-letter path not allowed: {p!r}"
    parts = p.split("/")
    if any(seg == ".." for seg in parts):
        return f"parent-traversal segment not allowed: {p!r}"
    if not any(p.startswith(root) for root in ALLOWED_ROOTS):
        return f"must lie inside {ALLOWED_ROOTS}: {p!r}"
    return None


def extra_path_validators(repo_root: Path) -> list:
    """Hook for the umbrella mirror to install its asymmetric host-root check.
    BCOS-side returns an empty list. The umbrella script imports validate_path
    and adds its own pass before calling promote().
    """
    return []


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _load_config(config_path: Path) -> dict:
    if not config_path.is_file():
        raise SystemExit(_err_io(f"schedule-config not found at {config_path}"))
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(_err_io(f"schedule-config malformed: {e}"))


def _dump_config(cfg: dict, config_path: Path) -> None:
    # Pretty-print to match typical hand-edited schedule-config style.
    text = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_text(config_path, text)


def _unique_preserve(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _rewrite_outputs_section(spec_text: str, outputs: list[str]) -> tuple[str, bool]:
    """Return (new_text, found). If `## Outputs` section is missing, found=False
    and new_text == spec_text."""
    pattern = re.compile(r"(^## Outputs[ \t]*\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    m = pattern.search(spec_text)
    if not m:
        return spec_text, False
    body_lines = [f"- `{p}`" for p in outputs] if outputs else ["(none)"]
    new_body = "\n".join(body_lines) + "\n\n"
    new_text = spec_text[: m.start(2)] + new_body + spec_text[m.end(2):]
    return new_text, True


def promote(
    job: str,
    paths: list[str],
    *,
    repo_root: Path | None = None,
    config_path: Path | None = None,
    spec_dir: Path | None = None,
    extra_validators=None,
) -> int:
    repo_root = repo_root or find_repo_root()
    config_path = config_path or (repo_root / ".claude" / "quality" / "schedule-config.json")
    spec_dir = spec_dir or (
        repo_root / ".claude" / "skills" / "schedule-dispatcher" / "references"
    )

    invalid: list[tuple[str, str]] = []
    for p in paths:
        reason = validate_path(p)
        if reason is not None:
            invalid.append((p, reason))
    for fn in extra_validators or extra_path_validators(repo_root):
        for p in paths:
            r = fn(p, repo_root=repo_root)
            if r is not None:
                invalid.append((p, r))
    if invalid:
        bad = _unique_preserve([p for p, _ in invalid])
        first_reason = invalid[0][1]
        return _emit_validation_error(job, bad, first_reason)

    cfg = _load_config(config_path)
    jobs = cfg.get("jobs", {})
    if job not in jobs:
        sys.stderr.write(json.dumps({"reason": f"unknown job: {job}"}) + "\n")
        return 3
    existing = list(jobs[job].get("outputs", []) or [])
    merged = _unique_preserve(existing + list(paths))

    # Cap check after merge
    literal_n = sum(1 for p in merged if not is_glob(p))
    glob_n = sum(1 for p in merged if is_glob(p))
    if literal_n > MAX_LITERALS or glob_n > MAX_GLOBS:
        return _emit_validation_error(
            job,
            list(paths),
            f"outputs cap exceeded after merge: {literal_n} literals (max {MAX_LITERALS}), "
            f"{glob_n} globs (max {MAX_GLOBS})",
        )

    spec_path = spec_dir / f"job-{job}.md"
    if not spec_path.is_file():
        sys.stderr.write(
            json.dumps({"reason": f"spec missing: {spec_path}"}) + "\n"
        )
        return 4
    spec_text = spec_path.read_text(encoding="utf-8")
    new_spec_text, found = _rewrite_outputs_section(spec_text, merged)
    if not found:
        sys.stderr.write(
            json.dumps(
                {"reason": f"spec {spec_path.name} missing ## Outputs section"}
            )
            + "\n"
        )
        return 4

    added = [p for p in paths if p not in existing]
    if not added and new_spec_text == spec_text:
        sys.stdout.write(json.dumps({"status": "noop", "job": job}) + "\n")
        return 0

    jobs[job]["outputs"] = merged
    _dump_config(cfg, config_path)
    if new_spec_text != spec_text:
        _atomic_write_text(spec_path, new_spec_text)

    sys.stdout.write(
        json.dumps(
            {"status": "updated", "job": job, "added": added, "total": len(merged)},
            sort_keys=True,
        )
        + "\n"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Promote paths into a job's outputs declaration.")
    ap.add_argument("--job", required=True, help="Job name (must exist in schedule-config.json).")
    ap.add_argument(
        "--paths",
        required=True,
        help="Comma-separated list of paths to declare. Whitespace tolerated.",
    )
    args = ap.parse_args(argv)
    paths = [p.strip() for p in args.paths.split(",") if p.strip()]
    if not paths:
        sys.stderr.write(json.dumps({"reason": "--paths produced empty list"}) + "\n")
        return 2
    return promote(args.job, paths)


if __name__ == "__main__":
    sys.exit(main())

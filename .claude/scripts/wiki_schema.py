#!/usr/bin/env python3
"""
Wiki schema governance helper for the bcos-wiki skill.

This script backs `/wiki schema ...` with executable behavior while keeping the
agent-facing skill in charge of AskUserQuestion confirmation. Mutating commands
dry-run by default and only write when called with `--apply`.
"""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = ROOT / ".claude" / "hooks" / "post_edit_frontmatter_check.py"
SCHEMA_TEMPLATE = ROOT / "docs" / "_bcos-framework" / "templates" / "_wiki.schema.yml.tmpl"
REFRESH_SCRIPT = ROOT / ".claude" / "scripts" / "refresh_wiki_index.py"

PAGE_TYPE_RE = re.compile(r"^  ([a-z][a-z0-9-]*):\s*$", re.MULTILINE)
YAML_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass(frozen=True)
class PageMigration:
    path: Path
    old_type: str
    new_type: str
    old_version: str
    new_version: str


def load_hook():
    spec = importlib.util.spec_from_file_location("post_edit_frontmatter_check", HOOK_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import hook: {HOOK_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def schema_path(root: Path) -> Path:
    return root / "docs" / "_wiki" / ".schema.yml"


def wiki_dir(root: Path) -> Path:
    return root / "docs" / "_wiki"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def ensure_schema(root: Path, today: str) -> Path:
    path = schema_path(root)
    if path.is_file():
        return path
    if not SCHEMA_TEMPLATE.is_file():
        raise FileNotFoundError(f"Missing schema template: {SCHEMA_TEMPLATE}")
    if not wiki_dir(root).is_dir():
        raise FileNotFoundError(f"Missing wiki zone: {wiki_dir(root)}")
    text = read_text(SCHEMA_TEMPLATE).replace("TODAY", today)
    write_text(path, text)
    return path


def load_schema_text(root: Path, today: str, create_for_mutation: bool = False) -> tuple[Path, str]:
    path = schema_path(root)
    if path.is_file():
        return path, read_text(path)
    if create_for_mutation:
        if not wiki_dir(root).is_dir():
            raise FileNotFoundError(f"Missing wiki zone: {wiki_dir(root)}")
        return path, read_text(SCHEMA_TEMPLATE).replace("TODAY", today)
    return SCHEMA_TEMPLATE, read_text(SCHEMA_TEMPLATE)


def unified_diff(path: Path, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


def print_diff(path: Path, before: str, after: str) -> None:
    diff = unified_diff(path, before, after)
    print(diff if diff else f"No changes for {path}")


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def list_block_items(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    items: list[str] = []
    in_section = False
    for line in lines:
        if re.match(rf"^{re.escape(heading)}:\s*$", line):
            in_section = True
            continue
        if in_section and line and not line.startswith(" ") and not line.startswith("#"):
            break
        if in_section:
            match = re.match(r"^\s+-\s+([a-zA-Z0-9_-]+)", line)
            if match:
                items.append(match.group(1))
    return items


def map_keys_in_section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    keys: list[str] = []
    in_section = False
    for line in lines:
        if re.match(rf"^{re.escape(heading)}:\s*$", line):
            in_section = True
            continue
        if in_section and line and not line.startswith(" ") and not line.startswith("#"):
            break
        if in_section:
            match = re.match(r"^  ([a-z][a-z0-9-]*):\s*$", line)
            if match:
                keys.append(match.group(1))
    return keys


def schema_version(text: str) -> str:
    match = re.search(r"^schema-version:\s*(\d+)", text, re.MULTILINE)
    return match.group(1) if match else "unknown"


def page_type_names(text: str) -> list[str]:
    return [match.group(1) for match in PAGE_TYPE_RE.finditer(text)]


def command_list(args: argparse.Namespace) -> int:
    path, text = load_schema_text(args.root, args.today)
    hook = load_hook()
    parsed = hook.parse_wiki_schema(text)
    print(f"schema: {path}")
    print(f"schema-version: {parsed.get('schema-version') or 'unknown'}")
    print("")
    print("page-types:")
    for name in sorted(parsed.get("page-types", {}).keys()):
        definition = parsed["page-types"][name]
        retired = " retired" if re.search(rf"^  {re.escape(name)}:\n(?:    .*\n)*?    retired:\s*true", text, re.MULTILINE) else ""
        fields = ", ".join(definition.get("required-fields") or [])
        folder = definition.get("folder", "pages")
        print(f"  - {name}{retired} (folder: {folder}; required: {fields or 'none'})")
    for heading in ["statuses", "detail-levels", "provenance-kinds"]:
        print("")
        print(f"{heading}:")
        for item in list_block_items(text, heading):
            print(f"  - {item}")
    print("")
    print("lint-checks:")
    for item in sorted(map_keys_in_section(text, "lint-checks")):
        print(f"  - {item}")
    print("")
    print("auto-fixes:")
    for item in sorted(map_keys_in_section(text, "auto-fixes")):
        print(f"  - {item}")
    return 0


def append_schema_migration(text: str, lines: list[str]) -> str:
    block = "".join(f"  {line}\n" for line in lines)
    if re.search(r"^migrations:\s*\[\]\s*$", text, re.MULTILINE):
        return re.sub(r"^migrations:\s*\[\]\s*$", "migrations:\n" + block.rstrip(), text, count=1, flags=re.MULTILINE)
    if re.search(r"^migrations:\s*$", text, re.MULTILINE):
        return re.sub(r"^migrations:\s*$", "migrations:\n" + block.rstrip(), text, count=1, flags=re.MULTILINE)
    return text.rstrip() + "\n\nmigrations:\n" + block


def append_log(root: Path, today: str, operation: str, lines: list[str], apply: bool) -> None:
    log_path = wiki_dir(root) / "log.md"
    entry = "\n".join([f"\n## {today} - schema {operation}", *[f"- {line}" for line in lines], ""])
    if apply:
        current = read_text(log_path) if log_path.is_file() else "# Wiki Log\n"
        write_text(log_path, current.rstrip() + "\n" + entry)
    else:
        print("")
        print(f"Log entry that would be appended to {log_path}:")
        print(entry)


def find_page_type_block(text: str, name: str) -> tuple[int, int] | None:
    pattern = re.compile(rf"^  {re.escape(name)}:\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    next_match = pattern_next_page_type(text, match.end())
    end = next_match.start() if next_match else page_types_section_end(text, match.end())
    return match.start(), end


def pattern_next_page_type(text: str, start: int):
    return PAGE_TYPE_RE.search(text, start)


def page_types_section_end(text: str, start: int) -> int:
    match = re.search(r"^\S.*$", text[start:], re.MULTILINE)
    if not match:
        return len(text)
    return start + match.start()


def add_page_type_block(
    text: str,
    name: str,
    description: str,
    folder: str,
    required_fields: list[str],
    review_cadence_days: str,
    auto_archive_after_days: str,
) -> str:
    if name in page_type_names(text):
        raise ValueError(f"page-type already exists: {name}")
    fields = ", ".join(required_fields)
    block = (
        f"\n  {name}:\n"
        f"    description: {yaml_quote(description)}\n"
        f"    required-fields: [{fields}]\n"
        f"    folder: {folder}\n"
        f"    review-cadence-days: {review_cadence_days}\n"
        f"    auto-archive-after-days: {auto_archive_after_days}\n"
    )
    insert_at = page_types_section_end(text, text.index("page-types:") + len("page-types:"))
    return text[:insert_at].rstrip() + block + "\n" + text[insert_at:].lstrip("\n")


def command_add(args: argparse.Namespace) -> int:
    if args.kind != "page-type":
        raise ValueError("Only `add page-type <name>` is implemented for P4")
    path, before = load_schema_text(args.root, args.today, create_for_mutation=True)
    required_fields = split_csv(args.required_fields)
    description = args.description or args.name.replace("-", " ").capitalize()
    after = add_page_type_block(
        before,
        args.name,
        description,
        args.folder,
        required_fields,
        str(args.review_cadence_days),
        "null" if args.auto_archive_after_days is None else str(args.auto_archive_after_days),
    )
    after = append_schema_migration(
        after,
        [
            "- schema-version: " + schema_version(after),
            f"  applied: {args.today}",
            "  operation: add-page-type",
            f"  page-type: {args.name}",
        ],
    )
    print_diff(path, before, after)
    append_log(args.root, args.today, "add-page-type", [f"page-type: {args.name}"], args.apply)
    if args.apply:
        write_text(path, after)
        ensure_skill_template(args.root, args.name)
        print(f"Applied add-page-type {args.name}")
    else:
        print("Dry-run only. Re-run with --apply after AskUserQuestion confirmation.")
    return 0


def ensure_skill_template(root: Path, name: str) -> None:
    if root != ROOT:
        return
    template_dir = ROOT / ".claude" / "skills" / "bcos-wiki" / "templates" / "page-types"
    if not template_dir.is_dir():
        return
    path = template_dir / f"{name}.md"
    if path.exists():
        return
    write_text(path, f"# {name.replace('-', ' ').title()} Template\n\nUse this starter only after registering `{name}` in `_wiki/.schema.yml`.\n")


def split_csv(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def bump_patch(version: str) -> str:
    parts = version.strip().split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return version
    parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts)


def rewrite_frontmatter_type(content: str, old: str, new: str, today: str) -> tuple[str, str, str] | None:
    match = YAML_FRONTMATTER_RE.match(content)
    if not match:
        return None
    frontmatter = match.group(1)
    if not re.search(rf"^page-type:\s*{re.escape(old)}\s*$", frontmatter, re.MULTILINE):
        return None
    version_match = re.search(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", frontmatter, re.MULTILINE)
    old_version = version_match.group(1) if version_match else "unknown"
    new_version = bump_patch(old_version)
    updated = re.sub(rf"^page-type:\s*{re.escape(old)}\s*$", f"page-type: {new}", frontmatter, count=1, flags=re.MULTILINE)
    if version_match:
        updated = re.sub(r"^version:\s*[0-9]+\.[0-9]+\.[0-9]+\s*$", f"version: {new_version}", updated, count=1, flags=re.MULTILINE)
    if re.search(r"^last-updated:\s*.*$", updated, re.MULTILINE):
        updated = re.sub(r"^last-updated:\s*.*$", f"last-updated: {today}", updated, count=1, flags=re.MULTILINE)
    body_start = match.end()
    return "---\n" + updated + "\n---\n\n" + content[body_start:].lstrip("\n"), old_version, new_version


def wiki_pages(root: Path) -> list[Path]:
    base = wiki_dir(root)
    paths = []
    for rel in ["pages", "source-summary"]:
        folder = base / rel
        if folder.is_dir():
            paths.extend(sorted(folder.glob("*.md")))
    return paths


def collect_page_renames(root: Path, old: str, new: str, today: str) -> tuple[list[PageMigration], dict[Path, str]]:
    migrations: list[PageMigration] = []
    rewritten: dict[Path, str] = {}
    for path in wiki_pages(root):
        content = read_text(path)
        result = rewrite_frontmatter_type(content, old, new, today)
        if result is None:
            continue
        new_content, old_version, new_version = result
        migrations.append(PageMigration(path, old, new, old_version, new_version))
        rewritten[path] = new_content
    return migrations, rewritten


def command_rename(args: argparse.Namespace) -> int:
    if args.kind != "page-type":
        raise ValueError("Only `rename page-type <old> <new>` is implemented for P4")
    path, before = load_schema_text(args.root, args.today, create_for_mutation=True)
    if args.old not in page_type_names(before):
        raise ValueError(f"unknown page-type: {args.old}")
    if args.new in page_type_names(before):
        raise ValueError(f"page-type already exists: {args.new}")
    block = find_page_type_block(before, args.old)
    if block is None:
        raise ValueError(f"cannot find page-type block: {args.old}")
    start, end = block
    renamed_block = re.sub(rf"^  {re.escape(args.old)}:\s*$", f"  {args.new}:", before[start:end], count=1, flags=re.MULTILINE)
    after = before[:start] + renamed_block + before[end:]
    page_migrations, rewritten_pages = collect_page_renames(args.root, args.old, args.new, args.today)
    after = append_schema_migration(
        after,
        [
            "- schema-version: " + schema_version(after),
            f"  applied: {args.today}",
            "  operation: rename-page-type",
            f"  from: {args.old}",
            f"  to: {args.new}",
            f"  pages-migrated: {len(page_migrations)}",
            f"  reversible-via: rename-page-type {args.new} {args.old}",
        ],
    )
    print_diff(path, before, after)
    for migration in page_migrations:
        print("")
        print(f"Page migration: {migration.path}")
        print(f"  page-type: {migration.old_type} -> {migration.new_type}")
        print(f"  version: {migration.old_version} -> {migration.new_version}")
    append_log(
        args.root,
        args.today,
        "rename-page-type",
        [f"from: {args.old}", f"to: {args.new}", f"pages-migrated: {len(page_migrations)}"],
        args.apply,
    )
    if args.apply:
        write_text(path, after)
        for page_path, page_text in rewritten_pages.items():
            write_text(page_path, page_text)
        refresh_index(args.root)
        print(f"Applied rename-page-type {args.old} -> {args.new}")
    else:
        print("Dry-run only. Re-run with --apply after AskUserQuestion confirmation.")
    return 0


def command_retire(args: argparse.Namespace) -> int:
    if args.kind != "page-type":
        raise ValueError("Only `retire page-type <name>` is implemented for P4")
    path, before = load_schema_text(args.root, args.today, create_for_mutation=True)
    block = find_page_type_block(before, args.name)
    if block is None:
        raise ValueError(f"unknown page-type: {args.name}")
    start, end = block
    old_block = before[start:end]
    if re.search(r"^    retired:\s*true\s*$", old_block, re.MULTILINE):
        raise ValueError(f"page-type already retired: {args.name}")
    new_block = old_block.rstrip() + f"\n    retired: true\n    retired-at: {args.today}\n"
    after = before[:start] + new_block + before[end:]
    after = append_schema_migration(
        after,
        [
            "- schema-version: " + schema_version(after),
            f"  applied: {args.today}",
            "  operation: retire-page-type",
            f"  page-type: {args.name}",
        ],
    )
    print_diff(path, before, after)
    append_log(args.root, args.today, "retire-page-type", [f"page-type: {args.name}"], args.apply)
    if args.apply:
        write_text(path, after)
        print(f"Applied retire-page-type {args.name}")
    else:
        print("Dry-run only. Re-run with --apply after AskUserQuestion confirmation.")
    return 0


def refresh_index(root: Path) -> None:
    if not REFRESH_SCRIPT.is_file():
        return
    subprocess.run(
        [sys.executable, str(REFRESH_SCRIPT), "--root", str(root), "--quiet"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def command_validate(args: argparse.Namespace) -> int:
    hook = load_hook()
    pages = wiki_pages(args.root)
    issues: list[tuple[Path, str]] = []
    for path in pages:
        for issue in hook.validate_frontmatter(str(path), str(args.root)):
            if issue.lower().startswith("warning:"):
                continue
            issues.append((path, issue))
    if not pages:
        print("No wiki pages found.")
        return 0
    if issues:
        print(f"Wiki schema validation found {len(issues)} issue(s):")
        for path, issue in issues:
            check_id = issue.split(":", 1)[0].lower()
            print(f"- {check_id}: {path}: {issue}")
        return 1
    print(f"Wiki schema validation passed ({len(pages)} page(s)).")
    return 0


def command_migrate(args: argparse.Namespace) -> int:
    if args.from_version == args.to_version:
        print(f"No migration needed: schema-version {args.from_version}.")
        return 0
    recipe = _MIGRATION_RECIPES.get((args.from_version, args.to_version))
    if recipe is None:
        print(
            "No executable migration recipe is registered for "
            f"schema-version {args.from_version} -> {args.to_version}. "
            "See .claude/skills/bcos-wiki/references/migration-helpers.md."
        )
        return 2
    return _run_migration_recipe(args, recipe)


# ---------------------------------------------------------------------------
# Migration recipes (P4)
# ---------------------------------------------------------------------------
#
# Each recipe is a callable `recipe(page_path, page_text) -> str | None`:
#   - Returns the new file text on a successful transform.
#   - Returns None to indicate "no change for this page" (e.g., the page is not
#     a candidate for this migration).
#
# Recipes must be byte-deterministic and reversible whenever practical. The
# inverse recipe is registered separately under the reversed `(from, to)` key.


def _migrate_source_summary_add_http_signals(page_path: Path, page_text: str) -> str | None:
    """1.0 -> 1.1: add `etag`, `last-modified`, `content-hash` to source-summary pages.

    Idempotent and additive — existing fields are preserved. Pages that are not
    `page-type: source-summary` are returned unchanged (recipe returns None).
    """
    from _wiki_yaml import apply_frontmatter, parse_frontmatter  # local import; sys.path setup below

    meta = parse_frontmatter(page_text) or {}
    if meta.get("page-type") != "source-summary":
        return None

    additions = {
        "schema-version": "1.1",
        "etag": meta.get("etag", ""),
        "last-modified": meta.get("last-modified", ""),
        "content-hash": meta.get("content-hash", ""),
    }
    return apply_frontmatter(page_text, additions)


def _migrate_source_summary_strip_http_signals(page_path: Path, page_text: str) -> str | None:
    """1.1 -> 1.0: remove `etag`, `last-modified`, `content-hash` from source-summary.

    Inverse of _migrate_source_summary_add_http_signals. Routes through
    `_wiki_yaml._split_frontmatter` so body content (including blank lines
    between the closing fence and the first heading) is preserved byte-for-byte.
    """
    from _wiki_yaml import parse_frontmatter, _split_frontmatter, _split_into_blocks  # local import

    meta = parse_frontmatter(page_text) or {}
    if meta.get("page-type") != "source-summary":
        return None

    body, rest = _split_frontmatter(page_text)
    if body is None:
        return None

    new_blocks: list[str] = []
    for key, raw in _split_into_blocks(body):
        if key in {"etag", "last-modified", "content-hash"}:
            continue
        if key == "schema-version":
            new_blocks.append("schema-version: 1.0")
            continue
        new_blocks.append(raw)

    new_body = "\n".join(new_blocks)
    return f"---\n{new_body}\n---\n{rest}"


def _derive_authority_default(page_path: Path, meta: dict) -> str:
    """Mechanical default for `authority:` per schema 1.2 mapping table.

    Inputs are the page's path (folder = `pages` or `source-summary`) and its
    parsed frontmatter. Never returns `external-evidence` — that value is
    explicit-only.

    See docs/_bcos-framework/architecture/wiki-zone.md "Authority semantics".
    """
    folder = page_path.parent.name
    page_type = (meta.get("page-type") or "").strip()
    provenance = meta.get("provenance") or {}
    kind = provenance.get("kind") if isinstance(provenance, dict) else None  # noqa: F841 — reserved for future signals

    if folder == "source-summary":
        return "external-reference"
    if folder == "pages":
        if page_type in {"how-to", "runbook", "decision-log", "post-mortem"}:
            return "canonical-process"
        if page_type in {"glossary", "faq"}:
            return "internal-reference"
    return "internal-reference" if folder == "pages" else "external-reference"


def _append_migration_log(root: Path, entries: list[dict]) -> None:
    """Append-only audit trail of derivation decisions for the 1.1 -> 1.2 migration."""
    if not entries:
        return
    log_path = root / ".claude" / "quality" / "migration-log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    with log_path.open("a", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")


def _migrate_add_authority_default(page_path: Path, page_text: str) -> str | None:
    """1.1 -> 1.2: add `authority:` to every wiki page (mechanical default).

    Non-clobbering: if the page already declares `authority:` (any value), the
    page is returned unchanged. Idempotent — second pass adds nothing.
    """
    sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    from _wiki_yaml import apply_frontmatter, parse_frontmatter

    meta = parse_frontmatter(page_text) or {}
    if "authority" in meta and (meta.get("authority") or "").strip():
        return None
    derived = _derive_authority_default(page_path, meta)
    return apply_frontmatter(page_text, {"authority": derived}, add_only=True)


def _migrate_strip_authority(page_path: Path, page_text: str) -> str | None:
    """1.2 -> 1.1: remove `authority:` from every wiki page.

    Reversal is data-preserving for users who relied on mechanical defaults;
    explicit overrides are lost (logged in migration-log.jsonl).
    """
    sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    from _wiki_yaml import _split_frontmatter, _split_into_blocks  # type: ignore[attr-defined]

    body, rest = _split_frontmatter(page_text)
    if body is None:
        return None
    new_blocks = []
    changed = False
    for key, raw in _split_into_blocks(body):
        if key == "authority":
            changed = True
            continue
        new_blocks.append(raw)
    if not changed:
        return None
    new_body = "\n".join(new_blocks)
    return f"---\n{new_body}\n---\n{rest}"


_MIGRATION_RECIPES: dict[tuple[str, str], list[callable]] = {
    ("1.0", "1.1"): [_migrate_source_summary_add_http_signals],
    ("1.1", "1.0"): [_migrate_source_summary_strip_http_signals],
    ("1.1", "1.2"): [_migrate_add_authority_default],
    ("1.2", "1.1"): [_migrate_strip_authority],
}


def _run_migration_recipe(args: argparse.Namespace, recipes: list) -> int:
    """Apply each registered recipe to every wiki page under args.root."""
    sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    pages = wiki_pages(args.root)
    if not pages:
        print(f"No wiki pages found under {wiki_dir(args.root)}.")
        return 0

    changes: list[tuple[Path, str, str]] = []
    for path in pages:
        text = read_text(path)
        new_text = text
        for recipe in recipes:
            candidate = recipe(path, new_text)
            if candidate is not None:
                new_text = candidate
        if new_text != text:
            changes.append((path, text, new_text))

    if not changes:
        print(
            f"Schema {args.from_version} -> {args.to_version}: no pages need migration."
        )
        return 0

    if not args.apply:
        print(
            f"Schema {args.from_version} -> {args.to_version}: would migrate "
            f"{len(changes)} page(s) (dry-run; pass --apply to write):"
        )
        for path, _, _ in changes:
            print(f"  - {path.relative_to(args.root)}")
        return 0

    sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
    from _wiki_yaml import parse_frontmatter

    # Bump the schema file's `schema-version:` line so `validate` reports the new state.
    sch = schema_path(args.root)
    if sch.is_file():
        sch_text = read_text(sch)
        bumped = re.sub(
            r"^schema-version:\s*\S+",
            f"schema-version: {args.to_version}",
            sch_text,
            count=1,
            flags=re.MULTILINE,
        )
        if bumped != sch_text:
            write_text(sch, bumped)

    log_entries: list[dict] = []
    for path, old_text, new_text in changes:
        path.write_text(new_text, encoding="utf-8")
        old_meta = parse_frontmatter(old_text) or {}
        new_meta = parse_frontmatter(new_text) or {}
        for key in ("authority", "etag", "last-modified", "content-hash"):
            if old_meta.get(key) != new_meta.get(key):
                log_entries.append({
                    "timestamp": args.today,
                    "page": str(path.relative_to(args.root)),
                    "from_version": args.from_version,
                    "to_version": args.to_version,
                    "field": key,
                    "old_value": old_meta.get(key),
                    "new_value": new_meta.get(key),
                })
    _append_migration_log(args.root, log_entries)
    print(
        f"Schema {args.from_version} -> {args.to_version}: migrated "
        f"{len(changes)} page(s)."
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Govern docs/_wiki/.schema.yml")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root")
    parser.add_argument("--today", default=date.today().isoformat(), help="Date to stamp into migrations")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list")
    sub.add_parser("validate")

    add = sub.add_parser("add")
    add.add_argument("kind", choices=["page-type"])
    add.add_argument("name")
    add.add_argument("--description", default="")
    add.add_argument("--folder", default="pages", choices=["pages", "source-summary"])
    add.add_argument("--required-fields", default="")
    add.add_argument("--review-cadence-days", default=180)
    add.add_argument("--auto-archive-after-days", default=None)
    add.add_argument("--apply", action="store_true")

    rename = sub.add_parser("rename")
    rename.add_argument("kind", choices=["page-type"])
    rename.add_argument("old")
    rename.add_argument("new")
    rename.add_argument("--apply", action="store_true")

    retire = sub.add_parser("retire")
    retire.add_argument("kind", choices=["page-type"])
    retire.add_argument("name")
    retire.add_argument("--apply", action="store_true")

    migrate = sub.add_parser("migrate")
    migrate.add_argument("from_version")
    migrate.add_argument("to_version")
    migrate.add_argument("--apply", action="store_true", help="Reserved for future non-noop migrations")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    args.root = args.root.resolve()
    try:
        if args.command == "list":
            return command_list(args)
        if args.command == "add":
            return command_add(args)
        if args.command == "rename":
            return command_rename(args)
        if args.command == "retire":
            return command_retire(args)
        if args.command == "validate":
            return command_validate(args)
        if args.command == "migrate":
            return command_migrate(args)
    except (FileNotFoundError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

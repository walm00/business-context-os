#!/usr/bin/env python3
"""
Build Document Index from the canonical BCOS context index.

`docs/document-index.md` stays the human-readable inventory with a preserved
user-notes section. The scanning/parsing source of truth is
`.claude/scripts/context_index.py`.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from context_index import build_context_index, write_context_index  # noqa: E402


OUTPUT_FILE = "docs/document-index.md"

AUTO_START = "<!-- AUTO-GENERATED SECTION -- DO NOT EDIT BELOW THIS LINE -->"
AUTO_END = "<!-- END AUTO-GENERATED SECTION -->"
USER_START = "<!-- USER NOTES -- EDIT FREELY BELOW THIS LINE. This section is preserved across runs. -->"
USER_END = "<!-- END USER NOTES -->"


def extract_user_notes(filepath: str) -> str | None:
    path = Path(filepath)
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    start_idx = content.find(USER_START)
    end_idx = content.find(USER_END)
    if start_idx == -1 or end_idx == -1:
        return None
    notes = content[start_idx + len(USER_START):end_idx].strip()
    return notes if notes else None


def _docs(index: dict[str, Any], *zones: str) -> list[dict[str, Any]]:
    wanted = set(zones)
    return [doc for doc in index.get("docs", []) if doc.get("zone") in wanted]


def _fmt(value: Any, fallback: str = "-") -> str:
    if value is None or value == "" or value == []:
        return fallback
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else fallback
    return str(value)


def _link(doc: dict[str, Any]) -> str:
    path = doc.get("path") or ""
    label = doc.get("name") or doc.get("filename") or path
    href = path[len("docs/"):] if path.startswith("docs/") else path
    return f"[{label}]({href})"


def _size(doc: dict[str, Any]) -> str:
    size = int(doc.get("size_bytes") or 0)
    return f"{size} B" if size < 1024 else f"{size / 1024:.1f} KB"


def generate_report(index: dict[str, Any], existing_user_notes: str | None) -> str:
    today = datetime.date.today().isoformat()
    lines: list[str] = []

    active = _docs(index, "active")
    managed = [doc for doc in active if doc.get("has_frontmatter")]
    unmanaged = [doc for doc in active if not doc.get("has_frontmatter")]
    incomplete = [doc for doc in managed if doc.get("missing_required")]
    warning_docs = [doc for doc in index.get("docs", []) if doc.get("warnings")]
    inbox = _docs(index, "inbox")
    planned = _docs(index, "planned")
    archive = _docs(index, "archive")
    wiki_pages = _docs(index, "wiki")
    collection_manifests = _docs(index, "collection-manifest")
    sidecars = _docs(index, "collection-sidecar")
    custom_optout = _docs(index, "custom-optout")

    lines.extend([
        "# Document Index",
        "",
        f"> **Generated:** {today} by `build_document_index.py`",
        "",
        "This file has two sections:",
        "- **Auto-generated** -- rebuilt every time the script runs. DO NOT edit.",
        "- **Your Notes** -- your annotations, priorities, decisions. Preserved across runs.",
        "",
        "---",
        "",
        AUTO_START,
        "",
        "## DO NOT EDIT THIS SECTION",
        "",
        "Everything between here and the end marker is regenerated automatically.",
        "Your edits WILL be overwritten. Use the **Your Notes** section below for custom content.",
        "",
        "## Summary",
        "",
    ])

    clusters: dict[str, list[dict[str, Any]]] = {}
    for doc in managed:
        clusters.setdefault(doc.get("cluster") or "_Unassigned_", []).append(doc)
    if clusters:
        lines.extend(["| Cluster | Documents | Complete Metadata | Tagged |", "|---------|-----------|-------------------|--------|"])
        total_docs = total_complete = total_tagged = 0
        for cluster in sorted(clusters):
            docs = clusters[cluster]
            complete = sum(1 for doc in docs if not doc.get("missing_required"))
            tagged = sum(1 for doc in docs if doc.get("tags"))
            lines.append(f"| {cluster} | {len(docs)} | {complete}/{len(docs)} | {tagged}/{len(docs)} |")
            total_docs += len(docs)
            total_complete += complete
            total_tagged += tagged
        lines.append(f"| **Total** | **{total_docs}** | **{total_complete}/{total_docs}** | **{total_tagged}/{total_docs}** |")
    else:
        lines.append("No managed documents found. Create data points in `docs/` with YAML frontmatter to get started.")
        lines.append("")
        lines.append("See `docs/_bcos-framework/templates/context-data-point.md` for the template.")
    lines.append("")

    _summary_table(lines, "By Zone", index["summaries"].get("zones") or {})
    _summary_table(lines, "By Type", index["summaries"].get("types") or {})
    _summary_table(lines, "By Status", index["summaries"].get("statuses") or {})
    _summary_table(lines, "By Tag", index["summaries"].get("tags") or {}, limit=20)
    _summary_table(lines, "By Path Tag", index["summaries"].get("path_tags") or {}, limit=20)

    if clusters:
        lines.extend(["---", "", "## Documents by Cluster", ""])
        for cluster in sorted(clusters):
            lines.extend([f"### {cluster}", "", "| Document | Domain | Type | Status | Updated | Tags |", "|----------|--------|------|--------|---------|------|"])
            for doc in sorted(clusters[cluster], key=lambda d: d.get("name") or d.get("filename") or ""):
                lines.append(
                    f"| {_link(doc)} | {_fmt(doc.get('domain_statement'))} | {_fmt(doc.get('type'))} "
                    f"| {_fmt(doc.get('status'))} | {_fmt(doc.get('last_updated'))} | {_fmt(doc.get('tags'))} |"
                )
            lines.append("")

    lines.extend(["---", "", "## Metadata Health", ""])
    complete_count = sum(1 for doc in managed if not doc.get("missing_required"))
    lines.append(f"**Complete:** {complete_count}/{len(managed)} active managed documents have all required fields")
    lines.append("")
    if incomplete:
        lines.extend(["**Incomplete:**", "", "| Document | Missing Fields |", "|----------|----------------|"])
        for doc in incomplete:
            lines.append(f"| {_link(doc)} | {_fmt(doc.get('missing_required'))} |")
        lines.append("")
    if warning_docs:
        lines.extend(["**Warnings:**", "", "| Document | Zone | Warnings |", "|----------|------|----------|"])
        for doc in sorted(warning_docs, key=lambda d: d.get("path") or ""):
            lines.append(f"| {_link(doc)} | {doc.get('zone')} | {_fmt(doc.get('warnings'))} |")
        lines.append("")
    else:
        lines.append("No metadata warnings detected.")
        lines.append("")

    lines.extend(["---", "", "## Review Health", ""])
    review_tracked = [doc for doc in index.get("docs", []) if doc.get("review_cycle") or doc.get("last_reviewed") or doc.get("zone") == "wiki"]
    if review_tracked:
        lines.extend(["| Document | Zone | Last Updated | Last Reviewed | Review Cycle | Next Review |", "|----------|------|--------------|---------------|--------------|-------------|"])
        for doc in sorted(review_tracked, key=lambda d: d.get("path") or ""):
            lines.append(
                f"| {_link(doc)} | {doc.get('zone')} | {_fmt(doc.get('last_updated'))} | "
                f"{_fmt(doc.get('last_reviewed'))} | {_fmt(doc.get('review_cycle'))} | {_fmt(doc.get('next_review'))} |"
            )
    else:
        lines.append("No documents currently carry review metadata.")
    lines.append("")

    lines.extend(["---", "", "## Unmanaged Documents", ""])
    if unmanaged:
        lines.extend(["Files found without YAML frontmatter. Consider adding metadata or formalizing as data points:", "", "| File | Size | Last Modified |", "|------|------|---------------|"])
        for doc in unmanaged:
            lines.append(f"| {doc['path']} | {_size(doc)} | {doc.get('modified')} |")
    else:
        lines.append("All active documents have YAML frontmatter. No unmanaged active files detected.")
    lines.append("")

    _folder_section(lines, "Inbox", inbox, "Raw material in `docs/_inbox/` waiting to be processed by `context-ingest`.")
    _folder_section(lines, "Planned", planned, "Polished ideas in `docs/_planned/` -- documented but not yet active reality.")

    lines.extend(["---", "", "## Wiki Pages", ""])
    if wiki_pages:
        by_pt = {}
        for doc in wiki_pages:
            by_pt[doc.get("page_type") or "-"] = by_pt.get(doc.get("page_type") or "-", 0) + 1
        lines.append("**Total:** " + str(len(wiki_pages)) + " page(s) -- " + ", ".join(f"{k}: {v}" for k, v in sorted(by_pt.items())))
        lines.extend(["", "| Page | Page-Type | Cluster | Status | Last Reviewed | Tags |", "|------|-----------|---------|--------|---------------|------|"])
        for doc in sorted(wiki_pages, key=lambda d: (d.get("page_type") or "", d.get("filename") or "")):
            lines.append(f"| {_link(doc)} | {_fmt(doc.get('page_type'))} | {_fmt(doc.get('cluster'))} | {_fmt(doc.get('status'))} | {_fmt(doc.get('last_reviewed'))} | {_fmt(doc.get('tags'))} |")
    else:
        lines.append("No wiki pages yet. Drop URLs in `docs/_wiki/queue.md` and run `/wiki run`, or write pages directly under `docs/_wiki/pages/`.")
    lines.append("")

    lines.extend(["---", "", "## Collections", ""])
    if collection_manifests or sidecars:
        lines.extend(["| Document | Kind | Collection | Schema | Status | Updated | Tags |", "|----------|------|------------|--------|--------|---------|------|"])
        for doc in sorted(collection_manifests + sidecars, key=lambda d: d.get("path") or ""):
            lines.append(
                f"| {_link(doc)} | {doc.get('zone')} | {_fmt(doc.get('collection'))} | "
                f"{_fmt(doc.get('manifest_schema'))} | {_fmt(doc.get('status'))} | {_fmt(doc.get('last_updated'))} | {_fmt(doc.get('tags'))} |"
            )
    else:
        lines.append("No collection manifests or sidecars found.")
    lines.append("")

    _folder_section(lines, "Archive", archive, "Superseded documents in `docs/_archive/`. Kept for reference, not active context.")

    if custom_optout:
        lines.extend(["---", "", "## Skipped (Custom `_*` Folders)", ""])
        folders = sorted({doc.get("folder", "").split("/")[1] for doc in custom_optout if doc.get("folder")})
        lines.append(f"Skipped {len(folders)} underscore-prefixed folder(s), {len(custom_optout)} file(s) total: " + ", ".join(f"`{f}/`" for f in folders))
        lines.append("")
        lines.append("These folders are opted out of indexing, validation, and lint by the underscore convention.")
        lines.append("")

    lines.extend(["## Suggested Cross-References", ""])
    lines.append("Documents with high keyword overlap that are not yet formally linked.")
    lines.append("Review these and add explicit relationships where appropriate.")
    lines.append("")
    lines.extend(_crossref_lines())
    lines.extend(["", AUTO_END, "", "---", "", USER_START, ""])
    lines.append(existing_user_notes if existing_user_notes else _starter_notes())
    lines.extend(["", USER_END])
    return "\n".join(lines) + "\n"


def _summary_table(lines: list[str], title: str, counts: dict[str, int], limit: int | None = None) -> None:
    if not counts:
        return
    lines.extend([f"### {title}", "", "| Value | Count |", "|-------|-------|"])
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for value, count in items[:limit]:
        lines.append(f"| {value} | {count} |")
    if limit is not None and len(items) > limit:
        lines.append(f"| ... | {len(items) - limit} more |")
    lines.append("")


def _folder_section(lines: list[str], title: str, docs: list[dict[str, Any]], intro: str) -> None:
    lines.extend(["---", "", f"## {title}", ""])
    if docs:
        lines.append(intro)
        lines.extend(["", "| Document | Status | Tags | Last Modified |", "|----------|--------|------|---------------|"])
        for doc in sorted(docs, key=lambda d: d.get("path") or ""):
            lines.append(f"| {_link(doc)} | {_fmt(doc.get('status'))} | {_fmt(doc.get('tags'))} | {doc.get('modified')} |")
    else:
        lines.append(f"No {title.lower()} documents found.")
    lines.append("")


def _crossref_lines() -> list[str]:
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "analyze_crossrefs.py"), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return ["*Cross-reference analysis unavailable. Run `python .claude/scripts/analyze_crossrefs.py` manually.*"]
        import json

        suggestions = json.loads(result.stdout)
        if not suggestions:
            return ["No undocumented cross-references found. All related documents are properly linked."]
        lines = ["| Document A | Document B | Overlap | Shared Terms |", "|-----------|------------|---------|--------------|"]
        for suggestion in suggestions[:10]:
            shared = ", ".join(suggestion["shared_terms"][:5])
            lines.append(f"| {suggestion['doc_a']['name']} | {suggestion['doc_b']['name']} | {suggestion['overlap']:.0%} | {shared} |")
        return lines
    except Exception:
        return ["*Cross-reference analysis unavailable.*"]


def _starter_notes() -> str:
    return "\n".join([
        "## Your Notes",
        "",
        "This section is yours. It is **preserved** when the script regenerates the file above.",
        "Use it for context that the auto-scan cannot capture -- human judgment, decisions, and direction.",
        "",
        "### Known Documents Outside This Repo",
        "",
        "<!-- Documents that matter but live elsewhere (Google Drive, Notion, shared drives, etc.) -->",
        "",
        "### Current Priorities",
        "",
        "<!-- What to create, update, or consolidate next and why -->",
        "",
        "### Active Decisions",
        "",
        "<!-- Ownership rulings, boundary decisions, things in flux that Claude should know about -->",
        "",
        "### What's Changing",
        "",
        "<!-- Business changes that context hasn't caught up with yet -->",
    ])


def main() -> int:
    dry_run = "--dry-run" in sys.argv[1:]
    root = REPO_ROOT
    if "--path" in sys.argv:
        idx = sys.argv.index("--path")
        if idx + 1 < len(sys.argv):
            candidate = Path(sys.argv[idx + 1]).resolve()
            root = candidate if (candidate / "docs").is_dir() else REPO_ROOT
    else:
        for arg in sys.argv[1:]:
            if arg.startswith("--path="):
                candidate = Path(arg.split("=", 1)[1]).resolve()
                root = candidate if (candidate / "docs").is_dir() else REPO_ROOT

    index = build_context_index(root)
    existing_notes = None if dry_run else extract_user_notes(str(root / OUTPUT_FILE))
    report = generate_report(index, existing_notes)

    if dry_run:
        print(report)
        return 0

    output = root / OUTPUT_FILE
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    write_context_index(root)
    print(f"Document Index written to {OUTPUT_FILE}")
    print(f"  Managed documents: {len(_docs(index, 'active'))}")
    print(f"  Wiki pages: {len(_docs(index, 'wiki'))}")
    print(f"  Collection manifests: {len(_docs(index, 'collection-manifest'))}")
    print(f"  Metadata warnings: {index.get('counts', {}).get('warnings', 0)}")
    print("  Machine index: .claude/quality/context-index.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

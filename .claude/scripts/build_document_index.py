#!/usr/bin/env python3
"""
Build Document Index - scans docs/ for managed documents, reads YAML frontmatter,
and generates docs/document-index.md with inventory, coverage, and health report.

The generated file has two zones:
  1. AUTO-GENERATED (overwritten every run) - inventory, health, unmanaged docs
  2. USER NOTES (preserved across runs) - your custom annotations, priorities, decisions

Usage:
    python .claude/scripts/build_document_index.py              # Scan docs/, write document-index.md
    python .claude/scripts/build_document_index.py --path .     # Scan everything
    python .claude/scripts/build_document_index.py --dry-run    # Print to stdout, don't write
"""

import os
import re
import sys
import glob
import datetime
from pathlib import Path

# --- Configuration ---

DEFAULT_SCAN_DIR = "docs"
OUTPUT_FILE = "docs/document-index.md"

# Skip these paths (BCOS framework files, not user content)
SKIP_PATHS = {
    "docs/methodology",
    "docs/guides",
    "docs/templates",
    "docs/architecture",
    "docs/document-index.md",
}

# Special directories — reported separately from managed docs
INBOX_DIR = "docs/_inbox"
PLANNED_DIR = "docs/_planned"
ARCHIVE_DIR = "docs/_archive"

REQUIRED_FIELDS = ["name", "type", "cluster", "version", "status", "owner", "created", "last-updated"]

# Zone markers
AUTO_START = "<!-- AUTO-GENERATED SECTION — DO NOT EDIT BELOW THIS LINE -->"
AUTO_END = "<!-- END AUTO-GENERATED SECTION -->"
USER_START = "<!-- USER NOTES — EDIT FREELY BELOW THIS LINE. This section is preserved across runs. -->"
USER_END = "<!-- END USER NOTES -->"

# --- YAML Frontmatter Extraction ---

YAML_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
YAML_FIELD_RE = re.compile(r'^([a-zA-Z][a-zA-Z0-9_-]*):\s*(.+)$', re.MULTILINE)


def extract_frontmatter(filepath):
    """Extract YAML frontmatter from a markdown file. Returns dict or None."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return None

    match = YAML_BLOCK_RE.match(content)
    if not match:
        return None

    yaml_block = match.group(1)
    data = {}
    for field_match in YAML_FIELD_RE.finditer(yaml_block):
        key = field_match.group(1).strip()
        value = field_match.group(2).strip().strip('"').strip("'")
        data[key] = value

    return data if data else None


def get_file_info(filepath):
    """Get file size and last modified date."""
    try:
        stat = os.stat(filepath)
        size = stat.st_size
        size_str = f"{size} B" if size < 1024 else f"{size / 1024:.1f} KB"
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
        return size_str, mtime
    except OSError:
        return "unknown", "unknown"


# --- User Notes Preservation ---

def extract_user_notes(filepath):
    """Read existing file and extract the user notes section."""
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return None

    # Find content between USER_START and USER_END
    start_idx = content.find(USER_START)
    end_idx = content.find(USER_END)

    if start_idx == -1 or end_idx == -1:
        return None

    # Extract everything between the markers (excluding the markers themselves)
    notes = content[start_idx + len(USER_START):end_idx].strip()
    return notes if notes else None


# --- Scanning ---

def should_skip(filepath, scan_dir):
    """Check if file should be skipped."""
    rel = os.path.relpath(filepath).replace("\\", "/")
    for skip in SKIP_PATHS:
        if rel.startswith(skip):
            return True
    if rel == OUTPUT_FILE:
        return True
    return False


def is_inbox(filepath):
    """Check if file is in the _inbox directory."""
    rel = os.path.relpath(filepath).replace("\\", "/")
    return rel.startswith(INBOX_DIR) or ("/_inbox/" in rel)


def is_planned(filepath):
    """Check if file is in the _planned directory."""
    rel = os.path.relpath(filepath).replace("\\", "/")
    return rel.startswith(PLANNED_DIR) or ("/_planned/" in rel)


def is_archive(filepath):
    """Check if file is in the _archive directory."""
    rel = os.path.relpath(filepath).replace("\\", "/")
    return rel.startswith(ARCHIVE_DIR) or ("/_archive/" in rel)


def scan_documents(scan_dir):
    """Scan directory for markdown files, extract metadata."""
    managed = []
    unmanaged = []
    incomplete = []
    inbox = []
    planned = []
    archive = []

    pattern = os.path.join(scan_dir, "**", "*.md")
    files = sorted(glob.glob(pattern, recursive=True))

    for filepath in files:
        filepath = filepath.replace("\\", "/")

        if should_skip(filepath, scan_dir):
            continue

        # Inbox files go to a separate list (raw material, no quality bar)
        if is_inbox(filepath):
            size_str, mtime = get_file_info(filepath)
            inbox.append({
                "path": os.path.relpath(filepath).replace("\\", "/"),
                "size": size_str,
                "modified": mtime,
            })
            continue

        # Planned files — polished ideas, not yet active
        if is_planned(filepath):
            meta = extract_frontmatter(filepath)
            size_str, mtime = get_file_info(filepath)
            planned.append({
                "path": os.path.relpath(filepath).replace("\\", "/"),
                "name": meta.get("name", os.path.basename(filepath)) if meta else os.path.basename(filepath),
                "size": size_str,
                "modified": mtime,
                "meta": meta,
            })
            continue

        # Archive files go to a separate list (historical, not active)
        if is_archive(filepath):
            size_str, mtime = get_file_info(filepath)
            meta = extract_frontmatter(filepath)
            archive.append({
                "path": os.path.relpath(filepath).replace("\\", "/"),
                "name": meta.get("name", os.path.basename(filepath)) if meta else os.path.basename(filepath),
                "size": size_str,
                "modified": mtime,
            })
            continue

        meta = extract_frontmatter(filepath)

        if meta is None:
            size_str, mtime = get_file_info(filepath)
            unmanaged.append({
                "path": filepath,
                "size": size_str,
                "modified": mtime,
            })
            continue

        missing = [f for f in REQUIRED_FIELDS if f not in meta]
        rel_path = os.path.relpath(filepath).replace("\\", "/")

        doc = {
            "path": rel_path,
            "filename": os.path.basename(filepath),
            "meta": meta,
            "missing_fields": missing,
        }

        if missing:
            incomplete.append(doc)
        managed.append(doc)

    return managed, unmanaged, incomplete, inbox, planned, archive


# --- Report Generation ---

def generate_report(managed, unmanaged, incomplete, scan_dir, existing_user_notes, inbox=None, planned=None, archive=None):
    """Generate the Document Index markdown with auto and user zones."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    lines = []

    # --- Header ---
    lines.append("# Document Index")
    lines.append("")
    lines.append(f"> **Generated:** {today} by `build_document_index.py`")
    lines.append("")
    lines.append("This file has two sections:")
    lines.append("- **Auto-generated** — rebuilt every time the script runs. DO NOT edit.")
    lines.append("- **Your Notes** — your annotations, priorities, decisions. Preserved across runs.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # === AUTO-GENERATED ZONE ===
    lines.append(AUTO_START)
    lines.append("")
    lines.append("## DO NOT EDIT THIS SECTION")
    lines.append("")
    lines.append("Everything between here and the end marker is regenerated automatically.")
    lines.append("Your edits WILL be overwritten. Use the **Your Notes** section below for custom content.")
    lines.append("")

    # --- Summary ---
    lines.append("## Summary")
    lines.append("")

    clusters = {}
    for doc in managed:
        cluster = doc["meta"].get("cluster", "_Unassigned_")
        if cluster not in clusters:
            clusters[cluster] = []
        clusters[cluster].append(doc)

    if clusters:
        lines.append("| Cluster | Documents | Complete Metadata |")
        lines.append("|---------|-----------|-------------------|")
        total_docs = 0
        total_complete = 0
        for cluster_name in sorted(clusters.keys()):
            docs = clusters[cluster_name]
            complete = sum(1 for d in docs if not d["missing_fields"])
            lines.append(f"| {cluster_name} | {len(docs)} | {complete}/{len(docs)} |")
            total_docs += len(docs)
            total_complete += complete
        lines.append(f"| **Total** | **{total_docs}** | **{total_complete}/{total_docs}** |")
    else:
        lines.append("No managed documents found. Create data points in `docs/` with YAML frontmatter to get started.")
        lines.append("")
        lines.append("See `docs/templates/context-data-point.md` for the template.")

    lines.append("")

    # By type
    types = {}
    for doc in managed:
        t = doc["meta"].get("type", "unspecified")
        types[t] = types.get(t, 0) + 1

    if types:
        lines.append("### By Type")
        lines.append("")
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for t in sorted(types.keys()):
            lines.append(f"| {t} | {types[t]} |")
        lines.append("")

    # By status
    statuses = {}
    for doc in managed:
        s = doc["meta"].get("status", "unspecified")
        statuses[s] = statuses.get(s, 0) + 1

    if statuses:
        lines.append("### By Status")
        lines.append("")
        lines.append("| Status | Count |")
        lines.append("|--------|-------|")
        for s in sorted(statuses.keys()):
            lines.append(f"| {s} | {statuses[s]} |")
        lines.append("")

    lines.append("---")
    lines.append("")

    # --- Documents by Cluster ---
    if clusters:
        lines.append("## Documents by Cluster")
        lines.append("")

        for cluster_name in sorted(clusters.keys()):
            docs = clusters[cluster_name]
            lines.append(f"### {cluster_name}")
            lines.append("")
            lines.append("| Document | Type | Owner | Version | Status | Last Updated |")
            lines.append("|----------|------|-------|---------|--------|-------------|")
            for doc in sorted(docs, key=lambda d: d["meta"].get("name", d["filename"])):
                meta = doc["meta"]
                name = meta.get("name", doc["filename"])
                doc_type = meta.get("type", "MISSING")
                owner = meta.get("owner", "MISSING")
                version = meta.get("version", "MISSING")
                status = meta.get("status", "MISSING")
                updated = meta.get("last-updated", "MISSING")
                lines.append(f"| [{name}]({doc['path']}) | {doc_type} | {owner} | {version} | {status} | {updated} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    # --- Metadata Health ---
    lines.append("## Metadata Health")
    lines.append("")

    complete_count = sum(1 for d in managed if not d["missing_fields"])
    total = len(managed)
    lines.append(f"**Complete:** {complete_count}/{total} documents have all required fields")
    lines.append("")

    if incomplete:
        lines.append(f"**Incomplete:** {len(incomplete)} documents missing fields:")
        lines.append("")
        lines.append("| Document | Missing Fields |")
        lines.append("|----------|---------------|")
        for doc in incomplete:
            name = doc["meta"].get("name", doc["filename"])
            missing = ", ".join(doc["missing_fields"])
            lines.append(f"| {name} | {missing} |")
        lines.append("")

    lines.append("---")
    lines.append("")

    # --- Unmanaged Documents ---
    lines.append("## Unmanaged Documents")
    lines.append("")
    if unmanaged:
        lines.append("Files found without YAML frontmatter. Consider adding metadata or formalizing as data points:")
        lines.append("")
        lines.append("| File | Size | Last Modified |")
        lines.append("|------|------|--------------|")
        for doc in unmanaged:
            lines.append(f"| {doc['path']} | {doc['size']} | {doc['modified']} |")
    else:
        lines.append("All documents have YAML frontmatter. No unmanaged files detected.")
    lines.append("")

    # --- Inbox (raw material) ---
    if inbox is None:
        inbox = []
    lines.append("---")
    lines.append("")
    lines.append("## Inbox")
    lines.append("")
    if inbox:
        lines.append("Raw material in `docs/_inbox/` waiting to be processed by `context-ingest`:")
        lines.append("")
        lines.append("| File | Size | Last Modified |")
        lines.append("|------|------|--------------|")
        for doc in inbox:
            lines.append(f"| {doc['path']} | {doc['size']} | {doc['modified']} |")
    else:
        lines.append("No files in `docs/_inbox/`. Drop meeting notes, raw dumps, or unprocessed material here.")
    lines.append("")

    # --- Planned (polished ideas) ---
    if planned is None:
        planned = []
    lines.append("---")
    lines.append("")
    lines.append("## Planned")
    lines.append("")
    if planned:
        lines.append("Polished ideas in `docs/_planned/` — documented but not yet active reality:")
        lines.append("")
        lines.append("| Document | Owner | Last Modified |")
        lines.append("|----------|-------|--------------|")
        for doc in planned:
            owner = doc["meta"].get("owner", "—") if doc.get("meta") else "—"
            lines.append(f"| [{doc['name']}]({doc['path']}) | {owner} | {doc['modified']} |")
    else:
        lines.append("No planned documents. Put polished ideas and future plans in `docs/_planned/`.")
    lines.append("")

    # --- Archive ---
    if archive is None:
        archive = []
    lines.append("---")
    lines.append("")
    lines.append("## Archive")
    lines.append("")
    if archive:
        lines.append("Superseded documents in `docs/_archive/`. Kept for reference, not active context:")
        lines.append("")
        lines.append("| Document | Size | Last Modified |")
        lines.append("|----------|------|--------------|")
        for doc in archive:
            lines.append(f"| [{doc['name']}]({doc['path']}) | {doc['size']} | {doc['modified']} |")
    else:
        lines.append("No archived documents. Move superseded docs to `docs/_archive/` instead of deleting them.")
    lines.append("")

    # === END AUTO-GENERATED ZONE ===
    lines.append(AUTO_END)
    lines.append("")
    lines.append("---")
    lines.append("")

    # === USER NOTES ZONE ===
    lines.append(USER_START)
    lines.append("")

    if existing_user_notes:
        # Preserve whatever the user had
        lines.append(existing_user_notes)
    else:
        # First run — provide starter template
        lines.append("## Your Notes")
        lines.append("")
        lines.append("This section is yours. It is **preserved** when the script regenerates the file above.")
        lines.append("Use it for context that the auto-scan cannot capture — human judgment, decisions, and direction.")
        lines.append("")
        lines.append("### Known Documents Outside This Repo")
        lines.append("")
        lines.append("<!-- Documents that matter but live elsewhere (Google Drive, Notion, shared drives, etc.) -->")
        lines.append("<!-- Example: -->")
        lines.append("<!-- - Board deck (Q1 2026): https://docs.google.com/... — source for strategic direction -->")
        lines.append("<!-- - Sales playbook: Notion /sales/playbook — not yet migrated -->")
        lines.append("<!-- - Brand guide PDF: shared drive /marketing/brand-guide-v3.pdf -->")
        lines.append("")
        lines.append("### Current Priorities")
        lines.append("")
        lines.append("<!-- What to create, update, or consolidate next and why -->")
        lines.append("")
        lines.append("### Active Decisions")
        lines.append("")
        lines.append("<!-- Ownership rulings, boundary decisions, things in flux that Claude should know about -->")
        lines.append("<!-- Example: 'Pricing model is being reworked — don't treat current pricing data point as reliable' -->")
        lines.append("<!-- Example: 'We decided competitive-positioning owns market trends, not market-context' -->")
        lines.append("")
        lines.append("### What's Changing")
        lines.append("")
        lines.append("<!-- Business changes that context hasn't caught up with yet -->")
        lines.append("<!-- Example: 'Pivoted to enterprise Q1 — audience and value prop need full rewrite' -->")

    lines.append("")
    lines.append(USER_END)

    return "\n".join(lines)


# --- Main ---

def main():
    scan_dir = DEFAULT_SCAN_DIR
    dry_run = False

    for arg in sys.argv[1:]:
        if arg == "--dry-run":
            dry_run = True
        elif arg.startswith("--path"):
            if "=" in arg:
                scan_dir = arg.split("=", 1)[1]
            elif sys.argv.index(arg) + 1 < len(sys.argv):
                scan_dir = sys.argv[sys.argv.index(arg) + 1]

    if not os.path.isdir(scan_dir):
        print(f"Error: '{scan_dir}' is not a directory")
        sys.exit(1)

    # Preserve user notes from existing file
    existing_notes = extract_user_notes(OUTPUT_FILE) if not dry_run else None

    managed, unmanaged, incomplete, inbox, planned, archive = scan_documents(scan_dir)
    report = generate_report(managed, unmanaged, incomplete, scan_dir, existing_notes, inbox, planned, archive)

    if dry_run:
        print(report)
    else:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Document Index written to {OUTPUT_FILE}")
        print(f"  Managed documents: {len(managed)}")
        print(f"  Unmanaged documents: {len(unmanaged)}")
        print(f"  Incomplete metadata: {len(incomplete)}")
        print(f"  Inbox items: {len(inbox)}")
        print(f"  Planned items: {len(planned)}")
        print(f"  Archived items: {len(archive)}")
        if existing_notes:
            print(f"  User notes: preserved")
        else:
            print(f"  User notes: starter template created")


if __name__ == "__main__":
    main()

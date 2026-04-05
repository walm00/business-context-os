#!/usr/bin/env python3
"""
Build Table of Context - scans docs/ for managed documents, reads YAML frontmatter,
and generates docs/table-of-context.md with inventory, coverage, and health report.

Usage:
    python .claude/scripts/build_table_of_context.py              # Scan docs/, write table-of-context.md
    python .claude/scripts/build_table_of_context.py --path .     # Scan everything
    python .claude/scripts/build_table_of_context.py --dry-run    # Print to stdout, don't write
"""

import os
import re
import sys
import glob
import datetime
from pathlib import Path

# --- Configuration ---

# Default scan directory
DEFAULT_SCAN_DIR = "docs"

# Output file
OUTPUT_FILE = "docs/table-of-context.md"

# Skip these paths (BCOS framework files, not user content)
SKIP_PATHS = {
    "docs/methodology",
    "docs/guides",
    "docs/templates",
    "docs/table-of-context.md",
}

# Required frontmatter fields
REQUIRED_FIELDS = ["name", "type", "cluster", "version", "status", "owner", "created", "last-updated"]

# Valid values
VALID_TYPES = {"context", "process", "policy", "reference", "playbook"}
VALID_STATUSES = {"draft", "active", "under-review", "archived"}

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
        if size < 1024:
            size_str = f"{size} B"
        else:
            size_str = f"{size / 1024:.1f} KB"
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
        return size_str, mtime
    except OSError:
        return "unknown", "unknown"


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


def scan_documents(scan_dir):
    """Scan directory for markdown files, extract metadata."""
    managed = []     # Files with valid frontmatter
    unmanaged = []   # Files without frontmatter
    incomplete = []  # Files with partial frontmatter

    pattern = os.path.join(scan_dir, "**", "*.md")
    files = sorted(glob.glob(pattern, recursive=True))

    for filepath in files:
        filepath = filepath.replace("\\", "/")

        if should_skip(filepath, scan_dir):
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

        # Check completeness
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

    return managed, unmanaged, incomplete


# --- Report Generation ---

def generate_report(managed, unmanaged, incomplete, scan_dir):
    """Generate the Table of Context markdown."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    lines = []

    lines.append("# Table of Context")
    lines.append("")
    lines.append(f"**Generated:** {today}")
    lines.append(f"**Script:** `.claude/scripts/build_table_of_context.py`")
    lines.append(f"**Scanned:** `{scan_dir}/`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Summary ---
    lines.append("## Summary")
    lines.append("")

    # Group by cluster
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
        lines.append("No managed documents found.")

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
    if unmanaged:
        lines.append("## Unmanaged Documents")
        lines.append("")
        lines.append("Files found without YAML frontmatter. Consider adding metadata or formalizing as data points:")
        lines.append("")
        lines.append("| File | Size | Last Modified |")
        lines.append("|------|------|--------------|")
        for doc in unmanaged:
            lines.append(f"| {doc['path']} | {doc['size']} | {doc['modified']} |")
        lines.append("")

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

    managed, unmanaged, incomplete = scan_documents(scan_dir)
    report = generate_report(managed, unmanaged, incomplete, scan_dir)

    if dry_run:
        print(report)
    else:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Table of Context written to {OUTPUT_FILE}")
        print(f"  Managed documents: {len(managed)}")
        print(f"  Unmanaged documents: {len(unmanaged)}")
        print(f"  Incomplete metadata: {len(incomplete)}")


if __name__ == "__main__":
    main()

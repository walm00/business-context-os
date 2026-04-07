#!/usr/bin/env python3
"""
analyze_crossrefs.py - Discover undocumented cross-references between context documents.

Analyzes keyword overlap between active docs to suggest relationships that
should be formally linked (BUILDS_ON, REFERENCES, etc.) but currently aren't.

Usage:
    python .claude/scripts/analyze_crossrefs.py              # Analyze and print suggestions
    python .claude/scripts/analyze_crossrefs.py --threshold 0.2  # Lower overlap threshold
    python .claude/scripts/analyze_crossrefs.py --json        # Output as JSON
"""

import os
import re
import sys
import json
import math
import argparse
from pathlib import Path
from collections import Counter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLD = 0.3   # Minimum keyword overlap ratio to suggest a link
MIN_SHARED_TERMS  = 3     # Minimum shared significant terms

# Skip these — not user content or not worth comparing
SKIP_PATHS = {
    "docs/methodology",
    "docs/guides",
    "docs/templates",
    "docs/architecture",
    "docs/_inbox",
    "docs/_archive",
    "docs/_planned",
    "docs/document-index.md",
}

# Common English stop words to filter out
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "is", "it", "as", "be", "was", "are", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "shall", "this", "that", "these", "those", "not", "no",
    "if", "then", "than", "so", "up", "out", "about", "into", "over", "after",
    "before", "between", "through", "during", "without", "within", "along",
    "each", "every", "all", "both", "few", "more", "most", "other", "some", "such",
    "only", "same", "also", "just", "because", "when", "where", "how", "what",
    "which", "who", "whom", "why", "while", "very", "too", "quite", "rather",
    "here", "there", "their", "they", "them", "its", "our", "your", "his", "her",
    "we", "you", "he", "she", "me", "my", "i", "us",
}

# Also skip common markdown / YAML words
SKIP_TERMS = STOP_WORDS | {
    "true", "false", "none", "null", "yes", "no", "status", "active", "draft",
    "version", "created", "updated", "name", "type", "cluster", "context",
    "document", "section", "see", "use", "using", "used", "make", "made",
}

# ---------------------------------------------------------------------------
# YAML frontmatter parsing (reuse pattern from other scripts)
# ---------------------------------------------------------------------------

YAML_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
YAML_FIELD_RE = re.compile(r'^([a-zA-Z][a-zA-Z0-9_-]*):\s*(.+)$', re.MULTILINE)
WORD_RE = re.compile(r'[a-zA-Z][a-zA-Z0-9-]{2,}')  # 3+ char words


def should_scan(path: str) -> bool:
    """Check if file should be analyzed."""
    p = path.replace("\\", "/")
    for skip in SKIP_PATHS:
        if skip in p:
            return False
    return p.endswith(".md")


def extract_name(content: str, filename: str) -> str:
    """Get document name from frontmatter or filename."""
    match = YAML_BLOCK_RE.match(content)
    if match:
        yaml = match.group(1)
        for m in YAML_FIELD_RE.finditer(yaml):
            if m.group(1) == "name":
                return m.group(2).strip().strip('"').strip("'")
    return filename


def extract_existing_links(content: str) -> set[str]:
    """Find existing cross-references (file paths mentioned in the document)."""
    links = set()
    # Match markdown links: [text](path)
    for m in re.finditer(r'\[.*?\]\(([^)]+\.md)\)', content):
        links.add(os.path.basename(m.group(1)))
    # Match bare .md references
    for m in re.finditer(r'([a-zA-Z0-9_-]+\.md)', content):
        links.add(m.group(1))
    return links


def extract_terms(content: str) -> Counter:
    """Extract significant terms from document body (after frontmatter)."""
    body = YAML_BLOCK_RE.sub("", content)
    words = WORD_RE.findall(body.lower())
    filtered = [w for w in words if w not in SKIP_TERMS and len(w) > 3]
    return Counter(filtered)


def jaccard_overlap(terms_a: Counter, terms_b: Counter) -> tuple[float, list[str]]:
    """Calculate Jaccard similarity and return shared terms."""
    set_a = set(terms_a.keys())
    set_b = set(terms_b.keys())
    intersection = set_a & set_b
    union = set_a | set_b
    if not union:
        return 0.0, []

    # Weight by term frequency (more frequent = more important)
    shared = sorted(intersection, key=lambda t: terms_a[t] + terms_b[t], reverse=True)
    return len(intersection) / len(union), shared


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Analyze keyword overlap between context documents.")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"Minimum overlap ratio to suggest a link (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of formatted text")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    docs_dir = project_root / "docs"

    # Collect all active context docs
    docs = {}
    for filepath in docs_dir.rglob("*.md"):
        rel = str(filepath.relative_to(project_root)).replace("\\", "/")
        if not should_scan(rel):
            continue
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        name = extract_name(content, filepath.name)
        terms = extract_terms(content)
        links = extract_existing_links(content)
        docs[rel] = {
            "name": name,
            "filename": filepath.name,
            "terms": terms,
            "links": links,
        }

    if len(docs) < 2:
        print("Need at least 2 active context documents to analyze cross-references.")
        sys.exit(0)

    # Compare all pairs
    suggestions = []
    paths = sorted(docs.keys())
    for i, path_a in enumerate(paths):
        for path_b in paths[i+1:]:
            doc_a = docs[path_a]
            doc_b = docs[path_b]

            # Skip if already linked
            if doc_b["filename"] in doc_a["links"] or doc_a["filename"] in doc_b["links"]:
                continue

            overlap, shared = jaccard_overlap(doc_a["terms"], doc_b["terms"])

            if overlap >= args.threshold and len(shared) >= MIN_SHARED_TERMS:
                suggestions.append({
                    "doc_a": {"path": path_a, "name": doc_a["name"]},
                    "doc_b": {"path": path_b, "name": doc_b["name"]},
                    "overlap": round(overlap, 3),
                    "shared_terms": shared[:10],  # Top 10
                    "shared_count": len(shared),
                })

    suggestions.sort(key=lambda s: s["overlap"], reverse=True)

    # Output
    if args.json:
        print(json.dumps(suggestions, indent=2))
    else:
        if not suggestions:
            print("No undocumented cross-references found above threshold.")
            print(f"(Threshold: {args.threshold}, Min shared terms: {MIN_SHARED_TERMS})")
        else:
            print(f"Suggested Cross-References ({len(suggestions)} found):\n")
            for s in suggestions:
                shared_preview = ", ".join(s["shared_terms"][:5])
                print(f"  {s['doc_a']['name']}")
                print(f"    <-> {s['doc_b']['name']}")
                print(f"    Overlap: {s['overlap']:.1%} ({s['shared_count']} shared terms: {shared_preview})")
                print()


if __name__ == "__main__":
    main()

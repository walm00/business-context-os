---
name: explore
description: Fast read-only exploration and scanning agent. Used by skills to delegate bulk file reading and keep the main context window clean.
category: Exploration
---

# Explore Agent

## Purpose

**IS:** Fast, read-only exploration — scanning files, reading content, searching keywords, summarizing findings
**IS NOT:** Making changes, auditing quality, making decisions, or planning work

## When Skills Should Delegate Here

Skills delegate to this agent when they need to read many files without filling the main context window. The agent reads, summarizes, and returns compact findings.

| Delegating Skill | What to Delegate | What Agent Returns |
|-----------------|-----------------|-------------------|
| **context-onboarding** | "Scan docs/ for all markdown files. For each, report: path, frontmatter fields, first 3 lines of content." | File inventory with metadata summary |
| **context-audit** | "Read all docs in [cluster]. For each, check: frontmatter complete? owner set? last-updated within 90 days?" | Validation report per document |
| **daydream** | "Read git diffs for these 15 changed files. Summarize what changed in each." | Change summary per file |
| **context-ingest** | "Search all active docs for keyword 'pricing'. Return file paths and matching lines." | Search results with context |
| **doc-lint** | "Validate markdown syntax and cross-references in docs/. Report broken links and formatting issues." | Lint report |

## How to Invoke

From any skill, use the Agent tool:

```
Use the Agent tool (subagent_type: "Explore") to [specific task].
Return: [what you need back — file paths, summaries, validation results].
```

**Be specific about what to return.** The agent runs in its own context window — only its returned summary enters the main window. Ask for compact results.

## Capabilities

- Search for files by glob pattern
- Read file contents
- Search within files for keywords (Grep)
- Read git log and git diff output
- Summarize findings into structured reports

## Constraints

- **Read-only.** Never creates, edits, or deletes files.
- **No other agents.** Cannot invoke other agents or skills.
- **No decisions.** Returns factual findings only — decisions happen in the main window.
- **Compact returns.** Summarize, don't dump raw file content. The main window needs findings, not transcripts.

## Example Queries

**From context-onboarding:**
> "Scan docs/ recursively. For each .md file, extract: path, name from frontmatter (or filename if no frontmatter), status, cluster, last-updated. Return as a table."

**From context-audit:**
> "Read these 12 files: [list]. For each, check if YAML frontmatter has all required fields (name, type, cluster, version, status, created, last-updated). Report which fields are missing per file."

**From daydream:**
> "Run git log --since='2026-03-20' --name-only -- docs/ and read the diffs for each changed file. Summarize what changed in 1-2 sentences per file."

**From context-ingest (triage):**
> "Read this URL/file and extract: what kind of knowledge is this (brand, audience, product, process, market, strategy)? Is it about current reality or future plans? Return a 3-line summary."

**Manual use:**
> "Find all data points that reference competitive-landscape in their BUILDS_ON or REFERENCES sections."

# Context Rules Reference

**Loaded by:** core-discipline, context-audit, context-ingest, ecosystem-manager
**Purpose:** Full CLEAR quality standard. CLAUDE.md has the essentials; this has the detail.

---

## CLEAR Checklist

Before any context modification, verify:

- **Contextual Ownership**: Does this data point have exactly one owner and one source of truth?
- **Linking**: Are relationships to other context points explicitly defined?
- **Elimination**: Have you removed anything this change makes redundant or contradictory?
- **Alignment**: Does this serve an actual business objective?
- **Refinement**: Is this change part of a structured review, or a reactive patch?

## Quality Principles

- **Single Ownership**: Every context point has one owner, one location, one source of truth
- **Explicit Relationships**: Never assume connections — define them
- **Active Elimination**: Removing stale context is as important as adding new context
- **Objective Alignment**: If it does not help make better decisions, it does not belong
- **Structured Refinement**: Systematic review cycles, not ad-hoc fixes

## Document Standard

Every managed document in `docs/` (excluding `_inbox/`, `_archive/`) must have YAML frontmatter:

```yaml
---
name: "Document Name"
type: context              # context | process | policy | reference | playbook
cluster: "Cluster Name"
version: "1.0.0"           # Bump on EVERY change
status: active             # draft | active | under-review | archived
created: "YYYY-MM-DD"      # Set once, NEVER change
last-updated: "YYYY-MM-DD" # MUST update on every edit
---
```

Full spec: `docs/methodology/document-standards.md`

## Key Navigation

| Area | Location | Purpose |
|------|----------|---------|
| Methodology | `docs/methodology/` | CLEAR principles, refinement guides |
| Guides | `docs/guides/` | Getting started, adoption, workflows |
| Skills | `.claude/skills/` | Context management skills |
| Agents | `.claude/agents/` | Automated workflow agents |
| Templates | `docs/templates/` | Data point, cluster, architecture templates |

## Common Workflows

| Task | Skill |
|------|-------|
| Add new context | `context-ingest` |
| Audit context health | `context-audit` |
| Plan significant changes | `clear-planner` |
| Strategic reflection | `daydream` |
| Extract from conversations | `context-mine` |
| Ecosystem maintenance | `ecosystem-manager` |
| Capture lessons | `lessons-consolidate` |

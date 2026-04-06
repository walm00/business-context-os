# CLAUDE.md - AI Assistant Guide for CLEAR Context OS

---

## How to Work

**Match your response to the task. Keep it simple.**

### Simple Tasks (Default)

**Questions, commands, small fixes:**

- Answer questions directly
- Run commands when asked
- Fix single files without ceremony
- Explain context structures when asked

**Small changes (1-3 files):**

- Think briefly about the approach
- Execute the change

### When in Doubt

Ask: "Should I just do this, or would you like me to plan it out first?"

---

## Project Context

CLEAR Context OS is a living system for building and maintaining business context with Claude Code. It uses the CLEAR methodology to prevent context rot -- the gradual degradation of AI context over time.

Your specific business context lives in your own context architecture. This project provides the methodology, skills, agents, and templates to build and maintain that architecture.

---

## Key Navigation

| Area              | Location           | Purpose                                   |
| ----------------- | ------------------ | ----------------------------------------- |
| **Methodology**   | `docs/methodology/`| CLEAR principles, refinement guides       |
| **Guides**        | `docs/guides/`     | Getting started, adoption, workflows      |
| **Skills**        | `.claude/skills/`  | Context management skills                 |
| **Agents**        | `.claude/agents/`  | Automated workflow agents                 |
| **Examples**      | `examples/`        | Data point templates, sample architectures|

### Key Documents

| Document                    | Purpose                                    |
| --------------------------- | ------------------------------------------ |
| `clear-principles.md`       | CLEAR methodology -- the five principles   |
| `context-architecture.md`   | How to structure your business context     |
| `getting-started.md`        | First steps, quick start walkthrough       |

---

## Context Quality Standard

All context changes MUST follow CLEAR principles. This is non-negotiable.

### CLEAR Checklist

Before any context modification, verify:

- **Contextual Ownership**: Does this data point have exactly one owner and one source of truth?
- **Linking**: Are relationships to other context points explicitly defined?
- **Elimination**: Have you removed anything this change makes redundant or contradictory?
- **Alignment**: Does this serve an actual business objective?
- **Refinement**: Is this change part of a structured review, or a reactive patch?

### Quality Principles

- **Single Ownership**: Every context point has one owner, one location, one source of truth
- **Explicit Relationships**: Never assume connections -- define them
- **Active Elimination**: Removing stale context is as important as adding new context
- **Objective Alignment**: If it does not help make better decisions, it does not belong
- **Structured Refinement**: Systematic review cycles, not ad-hoc fixes

---

## Document Standard

Every managed document must have YAML frontmatter with these required fields:

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

See `docs/methodology/document-standards.md` for full spec, optional fields, and quality levels.

---

## Critical Rules

### ALWAYS

- All documents MUST have YAML frontmatter with required fields
- Every document MUST have an Ownership Specification (DOMAIN + EXCLUSIVELY_OWNS at minimum)
- Relationships between documents MUST be defined, not implied
- All changes MUST follow CLEAR principles
- **Compounding rule:** After any significant analysis, synthesis, or research — offer to update the relevant data point with the new insight. Knowledge must not evaporate into chat history. Every task produces two outputs: the answer + context updates.

### NEVER

- NEVER delete content without first placing it in its owning document -- consolidate, then clean up
- NEVER duplicate content across documents -- link to the source
- NEVER change a document without updating `last-updated` and bumping `version`
- NEVER touch the `created` date -- it's immutable
- NEVER add content without checking which document OWNS that topic

---

## Quick Reference

### Session Start: Read These First

At the start of any context-related work, check for these files:

1. **`docs/table-of-context.md`** — The business: who we are, what we do, market position, current phase. Stable, updated monthly.
2. **`docs/current-state.md`** — The operator: priorities this week, what happened, active decisions, what's changing. Fluid, updated weekly.
3. **`docs/document-index.md`** — The inventory: what files exist, metadata health, unmanaged docs. Auto-generated by script.

Together these give you the full picture without reading every data point. Drill into specific data points only when you need detail.

### Folder Structure

| Location | What's there | Trust level |
|----------|-------------|-------------|
| `docs/*.md` | **Active context** — current business reality | High — act on this |
| `docs/_inbox/` | Raw material — meeting notes, brain dumps | Low — needs processing |
| `docs/_planned/` | Polished ideas — may or may not happen | Read, but not current reality |
| `docs/_archive/` | Superseded docs — historical reference | Do not treat as current |

**The folder IS the signal.** When you find a file in `_planned/`, you know it's an idea before opening it.

### Document Index

Rebuild with: `python .claude/scripts/build_document_index.py`

Auto-generated section refreshes from file state. User Notes section is preserved across runs.

### Common Workflows

| Task                          | Approach                                          |
| ----------------------------- | ------------------------------------------------- |
| Add new context               | Check ownership, link relationships, verify alignment |
| Update existing context       | Audit connections, eliminate stale parts, refine   |
| Review context health         | Run CLEAR audit, check for drift and orphans       |
| Reflect on architecture       | Use daydream skill for strategic thinking           |

### Adoption Tiers

| Tier                 | Focus                                                          |
| -------------------- | -------------------------------------------------------------- |
| **1 - Foundation**   | CLEAR principles, context architecture, data points            |
| **2 - Skills**       | Planning, auditing, daydreaming, ecosystem mgmt, lessons       |

---

**Version**: 1.0.0
**Last Updated**: 2026-04-04

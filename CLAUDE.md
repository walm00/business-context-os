# CLAUDE.md - AI Assistant Guide for Business Context OS

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

Business Context OS is a living system for building and maintaining business context with Claude Code. It uses the CLEAR methodology to prevent context rot -- the gradual degradation of AI context over time.

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
owner: "Name or Role"
created: "YYYY-MM-DD"      # Set once, NEVER change
last-updated: "YYYY-MM-DD" # MUST update on every edit
---
```

See `docs/methodology/document-standards.md` for full spec, optional fields, and quality levels.

---

## Critical Rules

### ALWAYS

- All documents MUST have YAML frontmatter with required fields
- Every document MUST have an explicit owner (a person, not a team)
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

### Table of Context

If `docs/table-of-context.md` exists, **read it at the start of context-related work.** It provides:
- The full inventory of managed documents (so you don't have to scan every time)
- Metadata health (which docs are complete, which have gaps)
- **User Notes section** with human decisions, priorities, and context that can't be auto-detected

Rebuild it with: `python .claude/scripts/build_table_of_context.py`

The auto-generated section refreshes from file state. The User Notes section is preserved across runs.

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

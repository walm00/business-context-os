---
name: core-discipline
description: Bootstrap skill - enforces proactive skill discovery and invocation. Automatically check for applicable skills before any action. Always active.
category: meta
---

# Core Discipline: The 1% Rule

> **Inspired by [Superpowers](https://github.com/obra/superpowers) framework**

## The Fundamental Rule

**If there's a reasonable chance a skill applies to what you're doing, CHECK it. Match the overhead to the task.**

- **Small change** (update one data point, fix a typo) → just do it, no ceremony
- **Medium change** (add a new data point, consolidate two docs) → check if context-audit or context-ingest applies
- **Significant change** (restructure a cluster, create new skills) → use clear-planner, run the full workflow

The point is not to invoke every skill every time. The point is to not miss the ones that matter.

---

## Purpose

**This skill IS:**

- A bootstrap discipline enforcing proactive skill discovery before every action
- An always-active overlay that applies throughout any session
- The entry point that ensures other skills are found and invoked when relevant

**This skill IS NOT:**

- A substitute for the specific skills it discovers (it finds them, they do the work)
- A workflow orchestrator (use `clear-planner` for that)
- Something you invoke explicitly -- it is always active

---

## Default Behavior

**Keep it simple. Match response to task.**

| Task Type                 | Action                 |
| ------------------------- | ---------------------- |
| Questions, commands       | Respond directly       |
| Single-file fixes         | Just do it             |
| Small changes (1-3 files) | Think briefly, execute |

**When in doubt:** Ask the user — via `AskUserQuestion`, not prose (see "Decision-point UX" below).

---

## Decision-point UX (cross-cutting)

**Every decision point in every BCOS interaction uses `AskUserQuestion`.** Not prose "should I do X?" questions. Not lists of options typed as text. Structured choice, clickable menu, dashboard-aware session state.

Applies everywhere: onboarding, ingest, audit, tune, migrate, dispatcher output, update confirmations, archival decisions, every skill that offers the user choices.

**Skip only when:**
- Response is information-only, no choice involved
- Decision is a trivial acknowledgement that would add more friction than value
- User needs to TYPE something free-form (a name, custom cron, path) — prose + AskUserQuestion's "Other → free text" fallback works for hybrid cases
- A scheduled dispatcher run finishes clean green with zero findings (one-line summary keeps the dashboard "Ready" status meaningful)

**Canonical pattern + option-wording rules + good/bad examples:** [`references/askuserquestion-pattern.md`](references/askuserquestion-pattern.md).

**Special case — wrapping scripts with built-in prompts** (like `update.py`'s `[y/N]` prompt): invoke the script with `--dry-run` first, parse the output, surface the summary via `AskUserQuestion`, then re-invoke with `--yes` based on the user's choice. This keeps the Claude UX consistent whether the user runs scripts via shell or via Claude.

---

## Key Skills (Invoke When Applicable)

| Skill                  | When to Use                         |
| ---------------------- | ----------------------------------- |
| `context-onboarding`   | First setup, scanning existing repo |
| `context-ingest`       | Integrating new sources into data points |
| `context-mine`         | Extracting context from chat exports, meeting transcripts |
| `context-audit`        | Auditing context architecture       |
| `clear-planner`        | Planning changes                    |
| `daydream`             | Stepping back to reflect            |
| `doc-lint`             | Validating markdown, cross-references, JSON |
| `ecosystem-manager`    | Ecosystem questions                 |
| `lessons-consolidate`  | Knowledge maintenance               |

### Skill Types

**Rigid (Exact Adherence):**

- `context-audit` - CLEAR compliance is non-negotiable

**Flexible (Contextual):**

- `context-ingest` - Integrate new sources into existing data points
- `daydream` - Process scales to need
- `lessons-consolidate` - Process scales to need

---

## The Compounding Rule

**Every significant task produces TWO outputs:**

1. **The deliverable** — the answer, analysis, comparison, or recommendation the user asked for
2. **Context updates** — updates to the relevant data points so the knowledge persists

After any synthesis, analysis, or research:
- Identify which data points are affected
- Offer to update them with the new insight
- Update the Document Index if the landscape changed

**Why:** Without this rule, knowledge evaporates into chat history. With it, every conversation makes the context architecture richer. The system compounds.

> **Quality bar for all updates:** see [`docs/_bcos-framework/methodology/document-standards.md`](../../docs/_bcos-framework/methodology/document-standards.md) — required fields, valid types/statuses, ownership specification rules.
>
> **Architecture docs:** For system design context, see [`docs/_bcos-framework/architecture/system-design.md`](../../docs/_bcos-framework/architecture/system-design.md)

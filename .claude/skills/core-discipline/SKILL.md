---
name: core-discipline
description: Bootstrap skill - enforces proactive skill discovery and invocation. Automatically check for applicable skills before any action. Always active.
category: meta
---

# Core Discipline: The 1% Rule

> **Inspired by [Superpowers](https://github.com/obra/superpowers) framework**

## The Fundamental Rule

**If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.**

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

**When in doubt:** Ask the user.

---

## Key Skills (Invoke When Applicable)

| Skill                  | When to Use                         |
| ---------------------- | ----------------------------------- |
| `context-onboarding`   | First setup, scanning existing repo |
| `context-audit`        | Auditing context architecture       |
| `clear-planner`        | Planning changes                    |
| `daydream`             | Stepping back to reflect            |
| `ecosystem-manager`    | Ecosystem questions                 |
| `lessons-consolidate`  | Knowledge maintenance               |

### Skill Types

**Rigid (Exact Adherence):**

- `context-audit` - CLEAR compliance is non-negotiable

**Flexible (Contextual):**

- `daydream` - Process scales to need
- `lessons-consolidate` - Process scales to need

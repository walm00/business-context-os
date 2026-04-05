---
name: todo-utilities
description: |
  Shared TodoWrite patterns for consistent progress tracking across all BCOS skills.
  This is a PATTERN LIBRARY, not an invocable skill. Skills copy these patterns inline.

  WHY INLINE, NOT INVOKED:
  If todo-utilities were invoked as a Task(), its TodoWrite calls would execute in an
  isolated context — invisible to the user. Patterns must run IN the parent skill's
  main context where TodoWrite is visible.

  WHEN TO REFERENCE:
  - Building a new skill that tracks multi-step progress
  - Adding agent delegation to an existing skill
  - Implementing approval gates or error recovery
---

# Todo Utilities

## Purpose

**This is a PATTERN LIBRARY**, not a skill you invoke.

Skills read these patterns and copy them inline into their own workflows. This ensures every skill tracks progress the same way — consistent user experience, no reinventing the wheel.

**Why not invoke as a Task?** Because TodoWrite calls inside a Task() are invisible to the user. The whole point of progress tracking is user visibility.

---

## Core Principle

**TodoWrite = display layer (what the user sees).**

Always update TodoWrite:
1. **BEFORE** invoking an agent → mark task `in_progress`
2. **AFTER** agent returns → mark task `completed`
3. **On error** → update activeForm to show what's happening, don't hide failures

---

## Patterns

### See: `references/todo-patterns.md`

The full pattern library with examples. Contains:

1. **Sequential Agent Invocation** — Tasks run one after another
2. **Parallel Agent Invocation** — Multiple independent agents
3. **Error Recovery** — Graceful failure with visible retry
4. **Workflow Gate** — User approval required before continuing
5. **Long-Running Progress** — Show progress counts during bulk operations

### See: `references/anti-patterns.md`

What NOT to do. Common mistakes that break user visibility.

---

## How Skills Reference This

Each BCOS skill that uses agent delegation or multi-step workflows should include:

```markdown
### Progress Tracking

This skill follows the TodoWrite patterns from `todo-utilities`.
See `.claude/skills/todo-utilities/references/todo-patterns.md` for the full library.
```

Then copy the relevant pattern inline. The pattern is the source of truth — if it changes, update the patterns doc and all skills inherit the intent.

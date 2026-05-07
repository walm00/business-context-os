# Implementation Plan: MemPalace-Inspired Features

**Session:** 20260407_220000_mempalace-adoption
**Scenario:** AGENTING (primary) + DOCUMENTATION (secondary)
**Status:** awaiting_approval
**Source:** .private/mempalace-competitive-analysis.md

---

## Problem Statement

CLEAR Context OS has strong governance but weak automatic capture. Session intelligence evaporates unless users manually invoke skills. MemPalace solves this with hooks that fire automatically every 15 messages and before context compaction. We adopt their capture automation while preserving CLEAR's governance (everything goes to _inbox for processing, not into permanent storage).

**Design principle:** Scripts handle all mechanical work (file I/O, counting, pruning, moving, templates). AI only does what requires contextual reasoning (deciding what's worth capturing, extracting meaning from content).

---

## Discovery Results

- **Agents:** 1 (explore)
- **Skills:** 10 (clear-planner, context-audit, context-ingest, context-onboarding, core-discipline, daydream, doc-lint, ecosystem-manager, lessons-consolidate, todo-utilities)
- **Existing hooks:** post_edit_frontmatter_check.py (Edit/Write), post_commit_context_check.py (Bash)
- **Lesson:** L-INIT-20260404-009 — Discovery scripts are source of truth
- **Overlap:** Obsidian PRD planned /log-to-context and @context-analyst. Items 1-3 here implement Stage 0 of that pipeline.

---

## Phase 1: Automatic Session Capture (HIGH)

### P1_001 — Create `auto_save_session.sh`

**File:** `.claude/hooks/auto_save_session.sh`
**Hook event:** Stop (fires after every assistant response)
**Behavior:**
1. Read JSON from stdin — extract `stop_hook_active`, `session_id`, `transcript_path`
2. If `stop_hook_active` is true → output `{}`, exit (loop prevention)
3. Parse transcript JSONL, count human messages (exclude `<command-message>`)
4. Read last save count from `.claude/hook_state/{session_id}_last_save`
5. If delta < 15 → output `{}`, exit (not time yet)
6. If delta >= 15 → update save count, output JSON with `"decision": "block"` and `"reason"`:

```
SESSION CHECKPOINT — 15 messages since last save.
Write a session capture to docs/_inbox/sessions/ with this exact structure:

---
type: session-capture
date: {ISO timestamp}
status: raw
---
## Decisions
- [bullet points of decisions made]

## Discoveries
- [bullet points of new information learned]

## Follow-ups
- [ ] [action items identified]

## Files Changed
- [list of file paths modified]

Keep each section to 3-5 bullets maximum. Skip empty sections.
File name: YYYY-MM-DD_HHMM.md
```

7. AI writes the capture, tries to stop again
8. Hook sees `stop_hook_active=true`, passes through

**State directory:** `.claude/hook_state/` (gitignored)

### P1_002 — Create `precompact_save.sh`

**File:** `.claude/hooks/precompact_save.sh`
**Hook event:** PreCompact (fires before context window compression)
**Behavior:**
1. ALWAYS output `"decision": "block"`
2. Reason tells AI to write emergency capture to `docs/_inbox/sessions/YYYY-MM-DD_precompact.md`
3. Same capture template as auto-save but with added instruction: "Include ALL context that would be lost during compaction"
4. No loop prevention needed — PreCompact fires once

### P1_003 — Create `docs/_inbox/sessions/`

```bash
mkdir -p docs/_inbox/sessions
touch docs/_inbox/sessions/.gitkeep
```

### P1_004 — Register hooks in `settings.json`

Add to existing hooks config:

```json
{
  "Stop": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/auto_save_session.sh\"",
          "timeout": 10,
          "statusMessage": "Checking session capture checkpoint..."
        }
      ]
    }
  ],
  "PreCompact": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/precompact_save.sh\"",
          "timeout": 10,
          "statusMessage": "Emergency save before context compaction..."
        }
      ]
    }
  ]
}
```

### P1_005 — Create `prune_sessions.py`

**File:** `.claude/scripts/prune_sessions.py`
**Purpose:** Delete session capture files older than 30 days
**Logic:**
1. Scan `docs/_inbox/sessions/*.md`
2. Parse date from filename (YYYY-MM-DD prefix)
3. If older than 30 days → delete
4. Report: "Pruned X session files older than 30 days"
**Invocation:** `python .claude/scripts/prune_sessions.py` (manual or via scheduled task)

---

## Phase 2: Session Continuity (MEDIUM)

### P2_001 — Create session diary template

**File:** `docs/.session-diary.md` (dot-prefixed = not a managed data point)
**Format:**

```markdown
# Session Diary

Accumulated session notes. Auto-pruned after 30 days.

---

## 2026-04-07

**Focus:** [what was worked on]
**Decisions:** [key decisions, 1-2 bullets]
**Open:** [unresolved questions]

---
```

AI appends a new entry when the auto-save hook fires or at session end. Each entry is ~300-500 bytes.

### P2_002 — Create `prune_diary.py`

**File:** `.claude/scripts/prune_diary.py`
**Purpose:** Remove diary entries older than 30 days
**Logic:**
1. Read `docs/.session-diary.md`
2. Parse `## YYYY-MM-DD` section headers
3. Drop sections where date < today - 30 days
4. Rewrite file with header + remaining entries
**Invocation:** `python .claude/scripts/prune_diary.py`

### P2_003 — Create `generate_wakeup_context.py`

**File:** `.claude/scripts/generate_wakeup_context.py`
**Purpose:** Generate compressed wake-up context (~200 tokens)
**Logic:**
1. Read `docs/table-of-context.md` — extract: name field, 1-line description, current phase
2. Read `docs/current-state.md` — extract: this week's priorities (first 3 bullets), active decisions (first 3 bullets)
3. Read `docs/.session-diary.md` — extract: last 3 entries (date + focus only)
4. Write `docs/.wake-up-context.md`:

```markdown
# Wake-Up Context (auto-generated — do not edit)

**Business:** [name] — [one-line description]. Phase: [phase].

**This week:** [3 bullet priorities]

**Active decisions:** [3 bullet decisions]

**Recent sessions:**
- [date]: [focus]
- [date]: [focus]
- [date]: [focus]
```

5. Target: <200 tokens total
**Invocation:** `python .claude/scripts/generate_wakeup_context.py`

### P2_004 — Update CLAUDE.md session start

Change the "Session Start: Read These First" section to add `.wake-up-context.md` as item 0:

```
0. **`docs/.wake-up-context.md`** — Compressed snapshot (~200 tokens). Read this FIRST
   for instant orientation. Drill into full docs only when you need detail.
```

---

## Phase 3: Knowledge Infrastructure (MEDIUM)

### P3_001 — Create entity registry

**File:** `.claude/registries/entities.json`
**Schema:**

```json
{
  "schemaVersion": "1.0",
  "lastUpdated": "2026-04-07",
  "entities": {
    "people": [
      {
        "canonical": "Guntis Coders",
        "aliases": ["Guntis", "walm00"],
        "role": "Founder / Operator",
        "context": "Creator of CLEAR Context OS"
      }
    ],
    "projects": [
      {
        "canonical": "CLEAR Context OS",
        "aliases": ["BCOS", "business-context-os"],
        "status": "active",
        "context": "Living system for business context management"
      }
    ],
    "terms": [
      {
        "term": "Context rot",
        "definition": "Gradual degradation of AI context over time",
        "seeAlso": "docs/methodology/clear-principles.md"
      }
    ]
  }
}
```

**Maintenance:** AI proposes additions, user reviews. No auto-population.

### P3_002 — Create context-mine skill

**File:** `.claude/skills/context-mine/SKILL.md`
**Purpose:** Accept conversation exports and extract structured context to _inbox
**What AI does:** Read the export, identify decisions/preferences/milestones/problems, write structured summaries
**What script does:** File handling, deduplication check (compare filenames in _inbox)
**Input formats:** Plain text paste, Slack JSON export, meeting transcript
**Output:** One or more files in `docs/_inbox/` with frontmatter:

```yaml
---
type: session-capture
source: slack-export
date: 2026-04-07
status: raw
---
```

**This skill coordinates context-ingest** — it extracts, then hands off to ingest for classification and routing.

---

## Phase 4: Archive Intelligence (LOWER)

### P4_001 — Archive compression convention

Add to `context-audit` skill references: when archiving a document, also append a 2-3 line compressed summary to `docs/_archive/index.md`:

```markdown
## Archive Index

| Date | Document | Summary |
|------|----------|---------|
| 2026-04-07 | pricing-strategy-v1.md | Original flat-rate pricing model. Superseded by usage-based model in v2. |
```

**Who generates the summary line:** AI (requires understanding the document)
**Who appends to the index file:** Script or direct write (mechanical append)

### P4_002 — Create `analyze_crossrefs.py`

**File:** `.claude/scripts/analyze_crossrefs.py`
**Purpose:** Analyze keyword overlap between documents, suggest undiscovered cross-references
**Logic:**
1. Scan all `docs/*.md` files (active context only)
2. Extract significant terms (nouns, proper nouns, domain terms) — simple TF-IDF or keyword extraction
3. Compare term overlap between document pairs
4. Flag pairs with >30% keyword overlap that don't have explicit BUILDS_ON/REFERENCES links
5. Output as a "Suggested Cross-References" section

**Output format:**
```
Suggested Cross-References (not yet linked):
  pricing-strategy.md <-> competitive-positioning.md  (shared: pricing, enterprise, tier)
  customer-insights.md <-> target-audience.md  (shared: persona, segment, pain)
```

### P4_003 — Extend `build_document_index.py`

Add a new section to the auto-generated document index: "Suggested Cross-References" populated by running `analyze_crossrefs.py` logic inline or by reading its output.

---

## Phase 5: Verification & Learnings

### P5_001 — Test all hooks end-to-end

| Test | Expected |
|------|----------|
| Have a 15+ message session | Auto-save fires, creates file in _inbox/sessions/ |
| Trigger context compaction | PreCompact fires, creates emergency save |
| Run prune_sessions.py with old test files | Old files deleted, recent preserved |
| Run generate_wakeup_context.py | .wake-up-context.md created, <200 tokens |
| Run prune_diary.py with old entries | Old entries removed, recent preserved |
| Run analyze_crossrefs.py | Suggestions generated for unlinked related docs |

### P5_002 — Capture learnings

Run ecosystem-manager to:
1. Register new hooks, skill, scripts, registry in ecosystem state
2. Capture lessons learned during implementation
3. Verify no overlap or conflict with existing components

---

## Artifacts

- `plan-manifest.json` — This session's task tracking
- `implementation-plan.md` — This document
- `planning-manifest.json` — Planner workflow state

## Files Created/Modified

| File | Action | Phase |
|------|--------|-------|
| `.claude/hooks/auto_save_session.sh` | CREATE | 1 |
| `.claude/hooks/precompact_save.sh` | CREATE | 1 |
| `.claude/hook_state/.gitkeep` | CREATE | 1 |
| `docs/_inbox/sessions/.gitkeep` | CREATE | 1 |
| `.claude/scripts/prune_sessions.py` | CREATE | 1 |
| `.claude/settings.json` | EDIT (add Stop + PreCompact hooks) | 1 |
| `docs/.session-diary.md` | CREATE | 2 |
| `.claude/scripts/prune_diary.py` | CREATE | 2 |
| `.claude/scripts/generate_wakeup_context.py` | CREATE | 2 |
| `docs/.wake-up-context.md` | CREATE (auto-generated) | 2 |
| `CLAUDE.md` | EDIT (add wake-up context reference) | 2 |
| `.claude/registries/entities.json` | CREATE | 3 |
| `.claude/skills/context-mine/SKILL.md` | CREATE | 3 |
| `.claude/skills/context-audit/SKILL.md` | EDIT (add archive convention) | 4 |
| `.claude/scripts/analyze_crossrefs.py` | CREATE | 4 |
| `.claude/scripts/build_document_index.py` | EDIT (add cross-ref section) | 4 |

**Total: 11 new files, 4 edits to existing files**

---

## Next Actions

- **Approve** → Begin implementation Phase 1
- **Modify [changes]** → Revise specific phases
- **Cancel** → Stop here

# TodoWrite Patterns for BCOS Skills

**Version:** 1.0.0
**Purpose:** Standard patterns for consistent progress tracking across all skills

---

## Pattern 1: Sequential Agent Invocation

**When to use:** Tasks that depend on each other — each needs the previous result.

**Used by:** context-onboarding (phases), context-audit (steps), daydream (phases)

```
# Initialize full task list up front
TodoWrite([
  { content: "Scan repository for context", status: "in_progress", activeForm: "Scanning repository" },
  { content: "Classify and map findings", status: "pending", activeForm: "Classifying findings" },
  { content: "Generate Document Index", status: "pending", activeForm: "Generating Document Index" },
  { content: "Present recommendations", status: "pending", activeForm: "Preparing recommendations" }
])

# Agent does the scanning
Agent(Explore, "Scan docs/ for all .md files...")

# Advance after agent returns
TodoWrite([
  { content: "Scan repository for context", status: "completed", activeForm: "Scanning complete" },
  { content: "Classify and map findings", status: "in_progress", activeForm: "Classifying findings" },
  ...
])
```

**Rules:**
- Initialize the FULL list at the start — user sees the whole journey
- Mark `in_progress` BEFORE agent call
- Mark `completed` AFTER agent returns
- Only ONE task `in_progress` at a time

---

## Pattern 2: Parallel Agent Invocation

**When to use:** Independent tasks that don't depend on each other.

**Used by:** context-onboarding Phase 1 (3 parallel scans), context-audit (cluster batches)

```
# Mark ALL parallel tasks as starting
TodoWrite([
  { content: "Scan docs/ for context files", status: "in_progress", activeForm: "Scanning docs/" },
  { content: "Scan root files for context fragments", status: "in_progress", activeForm: "Scanning root files" },
  { content: "Check git history for strategy commits", status: "in_progress", activeForm: "Checking git history" }
])

# Launch all agents (they run in separate context windows)
Agent(Explore, "Scan docs/...")
Agent(Explore, "Scan README.md, CLAUDE.md...")
Agent(Explore, "Check git log...")

# Mark ALL as completed after all return
TodoWrite([
  { content: "Scan docs/ for context files", status: "completed", activeForm: "Docs scan complete" },
  { content: "Scan root files for context fragments", status: "completed", activeForm: "Root scan complete" },
  { content: "Check git history for strategy commits", status: "completed", activeForm: "Git history checked" }
])
```

**Rules:**
- Mark ALL parallel tasks `in_progress` at once (shows user multiple things happening)
- Mark ALL `completed` after all return
- User sees the batch nature of the work

---

## Pattern 3: Error Recovery

**When to use:** A step fails but the workflow should continue or retry.

**Used by:** Any skill that might encounter missing files, parse errors, or contradictions

```
# Task starts
TodoWrite([
  { content: "Validate frontmatter on all docs", status: "in_progress", activeForm: "Validating frontmatter" },
  { content: "Run CLEAR compliance checks", status: "pending", activeForm: "Running CLEAR checks" }
])

# If validation hits an error:
TodoWrite([
  { content: "Validate frontmatter on all docs", status: "in_progress", activeForm: "Found 3 files with errors — fixing" },
  { content: "Fix: Add missing frontmatter to notes.md", status: "in_progress", activeForm: "Fixing notes.md" },
  { content: "Run CLEAR compliance checks", status: "pending", activeForm: "Running CLEAR checks" }
])

# After fix:
TodoWrite([
  { content: "Validate frontmatter on all docs", status: "completed", activeForm: "Validation complete (3 fixed)" },
  { content: "Fix: Add missing frontmatter to notes.md", status: "completed", activeForm: "Fixed" },
  { content: "Run CLEAR compliance checks", status: "in_progress", activeForm: "Running CLEAR checks" }
])
```

**Rules:**
- Don't hide failures — update activeForm to show what's happening
- Can inject fix tasks dynamically (expand the list)
- User sees the recovery process transparently

---

## Pattern 4: Workflow Gate (Approval Required)

**When to use:** Need user input or approval before continuing.

**Used by:** context-ingest (triage), clear-planner (approval gates), daydream (offer updates)

```
# Present findings and wait
TodoWrite([
  { content: "Analyze incoming content", status: "completed", activeForm: "Analysis complete" },
  { content: "Await triage decision", status: "in_progress", activeForm: "Waiting for your decision: inbox, planned, or integrate?" },
  { content: "Process content", status: "pending", activeForm: "Processing content" }
])

# STOP — present options to user, wait for response

# After user decides:
TodoWrite([
  { content: "Analyze incoming content", status: "completed", activeForm: "Analysis complete" },
  { content: "Await triage decision", status: "completed", activeForm: "Decision: integrate into active docs" },
  { content: "Process content", status: "in_progress", activeForm: "Integrating into competitive-positioning.md" }
])
```

**Rules:**
- Gate task stays `in_progress` until user responds
- activeForm clearly shows what you're waiting for
- Don't auto-advance past approval gates

---

## Pattern 5: Long-Running Progress

**When to use:** Bulk operations (scanning many files, processing batch ingest).

**Used by:** context-onboarding (large repos), context-audit (50+ docs), doc-lint

```
# Start with count
TodoWrite([
  { content: "Validate 47 documents", status: "in_progress", activeForm: "Validating documents (0/47)" }
])

# Update periodically (not every file — every 10 or so)
TodoWrite([
  { content: "Validate 47 documents", status: "in_progress", activeForm: "Validating documents (10/47)" }
])

# ...

TodoWrite([
  { content: "Validate 47 documents", status: "in_progress", activeForm: "Validating documents (40/47)" }
])

# Complete with summary
TodoWrite([
  { content: "Validate 47 documents", status: "completed", activeForm: "Validated 47 documents (3 issues found)" }
])
```

**Rules:**
- Show counts in activeForm: `(10/47)`
- Don't update every single item — batch updates (every 10)
- Final activeForm summarizes the result

---

## Pattern 6: Automatic Handoff

**When to use:** A skill completes and should offer the next logical step.

**Used by:** context-onboarding → audit, context-ingest → index rebuild

```
# Skill's final task includes the handoff offer
TodoWrite([
  { content: "Integrate new content into active docs", status: "completed", activeForm: "Content integrated" },
  { content: "Rebuild Document Index", status: "in_progress", activeForm: "Rebuilding Document Index" }
])

# Run the script (automatic, not optional)
Bash("python .claude/scripts/build_document_index.py")

TodoWrite([
  { content: "Integrate new content into active docs", status: "completed", activeForm: "Content integrated" },
  { content: "Rebuild Document Index", status: "completed", activeForm: "Document Index rebuilt" }
])

# Then OFFER (not force) the next skill:
# "Want me to run a CLEAR audit on the updated docs?"
```

**Rules:**
- Mandatory follow-ups (index rebuild) just happen — no user decision needed
- Optional follow-ups (audit, daydream) are offered with a clear question
- User sees the handoff as a natural progression

---

## Anti-Patterns

### DON'T: Start with empty TodoWrite
```
# BAD — user sees empty list, then sudden appearance
TodoWrite([])
...later...
TodoWrite([{ content: "Task 1", ... }])

# GOOD — initialize full list immediately
TodoWrite([
  { content: "Task 1", status: "pending", ... },
  { content: "Task 2", status: "pending", ... }
])
```

### DON'T: Skip the pre-agent update
```
# BAD — user sees nothing, then task jumps to done
Agent(Explore, "scan docs/...")
TodoWrite([{ content: "Scan docs", status: "completed" }])

# GOOD — user sees task start, then complete
TodoWrite([{ content: "Scan docs", status: "in_progress" }])
Agent(Explore, "scan docs/...")
TodoWrite([{ content: "Scan docs", status: "completed" }])
```

### DON'T: Call TodoWrite from inside a delegated agent
```
# BAD — agent's TodoWrite overwrites parent's list (invisible context)
# Inside agent:
TodoWrite([{ content: "Sub-task", ... }])  # REPLACES parent's list!

# GOOD — agent returns results, parent updates TodoWrite
# Inside agent:
return { findings: [...] }
# In parent:
TodoWrite([{ content: "Scan complete", status: "completed" }])
```

### DON'T: Leave stale tasks
```
# BAD — tasks from a previous workflow still showing
TodoWrite([
  { content: "Old task from last run", status: "completed" },
  { content: "Another old task", status: "completed" },
  { content: "Current task", status: "in_progress" }
])

# GOOD — clean list for current workflow
TodoWrite([
  { content: "Current task", status: "in_progress" },
  { content: "Next task", status: "pending" }
])
```

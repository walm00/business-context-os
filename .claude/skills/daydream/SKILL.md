---
name: daydream
description: Strategic reflection skill. Step back from daily work to think about the bigger picture of your context architecture, identify gaps, and envision improvements.
category: strategic
---

# Daydream

## Purpose

**This skill IS:**
- A structured way to step back and reflect on your context architecture
- A tool for identifying what's missing, what's changed, and what's next
- A creative space for "what if" thinking about your business context
- A bridge between daily maintenance and strategic evolution

**This skill IS NOT:**
- An audit (use context-audit for that)
- A planning tool (use clear-planner for that)
- Something you need to do every day (weekly or when inspiration strikes)

---

## When to Use

- End of week: "What did we learn this week that should change our context?"
- Before strategy sessions: "Is our context architecture ready for the conversation?"
- After market shifts: "Has our world changed enough to rethink our architecture?"
- When feeling stuck: "What are we not seeing?"
- When a new team member joins: "Does our context make sense to a fresh pair of eyes?"

---

## The Daydream Process

### Phase 1: What Changed Since Last Time (5 min)

**Step 1: Find when daydream last ran**

Check `.claude/quality/last-daydream.txt` for the timestamp. If the file doesn't exist, this is the first run — use 2 weeks ago as the baseline.

```bash
# Read last run timestamp (or default to 2 weeks ago)
cat .claude/quality/last-daydream.txt 2>/dev/null || echo "no previous run"
```

**Step 2: Check git for USER DOCUMENT changes only**

Scope to `docs/` only — exclude `.claude/`, sessions, agents, skills, and framework files:

```bash
# Only user documents — NOT agents, skills, sessions, or framework docs
git log --since="{last_daydream_date}" --name-only --pretty=format:"%h %s (%ar)" -- docs/ ':!docs/methodology/' ':!docs/guides/' ':!docs/templates/'
```

This shows ONLY changes to user-created content: data points, table-of-context.md, current-state.md, document-index.md, and any other user docs. Ignores all BCOS framework files and .claude/ internals.

If nothing changed → short daydream. Report "No document changes since last run" and skip to Phase 3 (Imagine) for forward-looking reflection only.

**Step 3: For each changed file, read the diff**

If 10+ files changed, delegate the reading to an explore agent:

```
Agent (Explore): "Read git diffs for these files: [list]. For each, summarize
in 1-2 sentences: what changed, was it content or metadata, does it look like
a routine update or a significant shift?"
```

For fewer files, read directly:

```bash
# What exactly changed in this specific file?
git diff {last_daydream_commit}..HEAD -- docs/path/to/changed-file.md
```

Understand WHAT changed — not just that it was touched. New content? Boundary shift? Metadata bump? Ownership reassignment?

**Step 4: Check for new or disappeared files**

Rebuild the Document Index and compare:

```bash
python .claude/scripts/build_document_index.py --dry-run
```

Compare against existing `docs/document-index.md`:
- New files that weren't there before?
- Files that disappeared?
- New unmanaged docs (no frontmatter)?

**Step 5: Read the context layers**

1. **`docs/.wake-up-context.md`** — Quick orientation. If this doesn't exist, regenerate it:
   ```bash
   python .claude/scripts/generate_wakeup_context.py
   ```
2. **`docs/current-state.md`** — "What Changed Recently" is the human's signal. Any active decisions resolved?
3. **`docs/table-of-context.md`** — Does the business description still match given the changes found?
4. **`docs/.session-diary.md`** — Accumulated session notes. What themes repeat? What keeps coming up?

**Step 5b: Run maintenance scripts**

Daydream is the natural time to run periodic maintenance:

```bash
# Prune session captures older than 30 days
python .claude/scripts/prune_sessions.py

# Prune diary entries older than 30 days
python .claude/scripts/prune_diary.py

# Regenerate wake-up context with latest data
python .claude/scripts/generate_wakeup_context.py

# Check for undocumented cross-references
python .claude/scripts/analyze_crossrefs.py
```

Report what was pruned and any suggested cross-references discovered.

**Step 6: Record this run**

At the END of the daydream session (after Phase 4), save the timestamp:

```bash
echo "{today's date}" > .claude/quality/last-daydream.txt
```

This ensures the next daydream knows exactly where to pick up.

### Phase 2: Reflect on Changes (10 min)

Based on what you found in Phase 1, ask:

**About the changes:**
- Why did these data points change? Was it a routine update or a signal of something bigger?
- Do the changes in one data point create ripple effects in others that haven't been updated yet?
- Are the "Active Decisions" in current-state.md resolved? Do they need to propagate?

**About what's missing:**
- Were any changes made directly to docs WITHOUT going through context-ingest? (Bypassed ownership?)
- Are there new unmanaged files that appeared? What knowledge are they trying to capture?
- What questions keep coming up that no data point answers?

**About the big picture:**
- Does table-of-context.md still describe the business accurately given recent changes?
- Are we still solving the same problems for the same people?
- Has the competitive landscape shifted?
- Have any processes changed without docs catching up?

**About the folder zones:**
- Are any docs in `_planned/` ready to move to active? (Reality caught up — move to `docs/` root)
- Are any active docs that should actually be in `_planned/`? (Not real yet, just an aspiration)
- Are there `_planned/` docs sitting >3 months without progress? (Stale plans = abandoned plans — archive or delete?)
- Is anything in `_inbox/` that's been sitting unprocessed? (Raw material piling up)

**About connections:**
- Did recent changes create new relationships between data points that aren't documented?
- Are there clusters that should exist but don't?
- Is anything isolated that should be integrated?

### Phase 3: Imagine (10 min)

Without constraints, imagine:
- If a new team member joined tomorrow, would our context tell them everything they need to know?
- If we entered a new market, which data points would need to change?
- If our biggest competitor changed strategy, how quickly could we update our context?
- If a key team member left tomorrow, would their knowledge survive in our documentation?
- What would our context architecture look like in 6 months if everything went well?
- Look at docs in `_planned/` — are they still the right future? Has your direction changed enough that some should be archived?

### Phase 4: Capture and Update (5 min)

**Capture insights:**
1. **Insights**: What did you realize?
2. **Gaps**: What's missing from your architecture?
3. **Actions**: What should you do about it? (Create, update, or remove data points)
4. **Lessons**: What should be captured in lessons.json?

**Update the context layers (offer to the user):**
- **`_planned/` folder** — Move realized plans to `docs/` root (active). Move abandoned plans to `_archive/`.
- **`_inbox/` folder** — Process any raw material sitting there. Ingest or discard.
- **table-of-context.md** — If the business picture shifted, update the relevant sections
- **current-state.md** — Refresh "What Changed Recently" based on what was discovered
- **Document Index** — Run `python .claude/scripts/build_document_index.py` if files changed
- **Data points** — Compounding rule: any insights from this reflection that should be filed back into specific data points

---

## Prompts for Claude

You can ask Claude to daydream with you:

- "Let's daydream about our context architecture"
- "Look at my data points and tell me what's missing"
- "If I were entering [new market], what would need to change?"
- "What connections between my data points am I not seeing?"
- "Review my context architecture and challenge my assumptions"
- "What would a fresh pair of eyes notice about our context?"

---

## Output

A daydream session produces:
- A reflection note (informal, conversational)
- A list of suggested changes (optional, not mandatory)
- New lessons for lessons.json (if any insights emerged)

There is no formal template. Daydreaming is deliberately unstructured. The value is in the thinking, not the format.

---

> **Architecture docs:** For maintenance lifecycle context, see [`docs/architecture/maintenance-lifecycle.md`](../../docs/architecture/maintenance-lifecycle.md)

## Tips

- **Don't optimize too early.** The point is to think freely, not to immediately act.
- **Do it regularly.** Monthly at minimum. Context rot starts when you stop reflecting.
- **Involve others.** Share your daydream outputs with team members for fresh perspectives.
- **Keep it short.** 30 minutes max. If it takes longer, you're probably planning, not daydreaming.
- **Capture the surprises.** The most valuable insights are often the ones you didn't expect.

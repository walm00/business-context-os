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

Start by finding what actually moved:

**Step 1: Check git for document changes**

```bash
# What docs changed in the last 2 weeks (or since last daydream)?
git log --since="2 weeks ago" --name-only --pretty=format:"%h %s (%ar)" -- docs/
```

This shows exactly which files changed, when, and the commit messages (which often explain why).

**Step 2: For each changed file, understand what changed**

```bash
# See the actual diff for a specific file
git diff HEAD~5 -- docs/path/to/changed-file.md
```

Read the diffs. Not just "file X was updated" but WHAT changed — new content added? Ownership boundary shifted? Metadata updated?

**Step 3: Check for new or disappeared files**

```bash
# Rebuild the Document Index to catch new/removed files
python .claude/scripts/build_document_index.py --dry-run
```

Compare the output against the existing `docs/document-index.md`. New files? Missing files?

**Step 4: Read the context layers**

1. **`docs/current-state.md`** — What's in flux? Active decisions? "What Changed Recently" section is the human's signal of what's moving.
2. **`docs/table-of-context.md`** — Does the business description still match reality given what changed?
3. **`docs/document-index.md`** — Any metadata going stale? New unmanaged docs?

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

### Phase 4: Capture and Update (5 min)

**Capture insights:**
1. **Insights**: What did you realize?
2. **Gaps**: What's missing from your architecture?
3. **Actions**: What should you do about it? (Create, update, or remove data points)
4. **Lessons**: What should be captured in lessons.json?

**Update the context layers (offer to the user):**
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

## Tips

- **Don't optimize too early.** The point is to think freely, not to immediately act.
- **Do it regularly.** Monthly at minimum. Context rot starts when you stop reflecting.
- **Involve others.** Share your daydream outputs with team members for fresh perspectives.
- **Keep it short.** 30 minutes max. If it takes longer, you're probably planning, not daydreaming.
- **Capture the surprises.** The most valuable insights are often the ones you didn't expect.

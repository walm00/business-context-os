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

### Phase 1: Survey (5 min)

Read the current state of the world:
1. **`docs/table-of-context.md`** — Does the business description still feel right?
2. **`docs/current-state.md`** — What changed recently? What's in flux? What are this week's priorities?
3. **`docs/document-index.md`** — Any new unmanaged docs? Any stale metadata?
4. Scan data point files — anything feel off?

The "What Changed Recently" section in current-state.md is the best starting point. Changes that haven't propagated to data points are where drift starts.

### Phase 2: Question (10 min)

Ask yourself these prompts:

**Completeness:**
- What do we know that isn't captured anywhere?
- What questions do team members keep asking that our context should answer?
- What decisions do we make regularly that don't have context to support them?

**Relevance:**
- Has our market changed since we last updated?
- Are we still solving the same problems for the same people?
- Do our competitive advantages and key differentiators still hold?
- Have any of our core processes changed without the docs catching up?

**Connections:**
- Are there data points that should be connected but aren't?
- Are there clusters that should exist but don't?
- Is anything isolated that should be integrated?

**Evolution:**
- Where is our business heading in the next 6 months?
- What context will we need that we don't have yet?
- What context do we have that we won't need?

### Phase 3: Imagine (10 min)

Without constraints, imagine:
- If a new team member joined tomorrow, would our context tell them everything they need to know?
- If we entered a new market, which data points would need to change?
- If our biggest competitor changed strategy, how quickly could we update our context?
- If a key team member left tomorrow, would their knowledge survive in our documentation?
- What would our context architecture look like in 6 months if everything went well?

### Phase 4: Capture (5 min)

Write down:
1. **Insights**: What did you realize?
2. **Gaps**: What's missing from your architecture?
3. **Actions**: What should you do about it? (Create, update, or remove data points)
4. **Lessons**: What should be captured in lessons.json?

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

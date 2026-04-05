# Scheduling Recurring Maintenance

**Set it and forget it. Let Claude remind you to maintain your context instead of relying on willpower.**

---

## Why Schedule?

The maintenance checklist tells you WHAT to do. The maintenance guide tells you WHY. This guide tells you HOW to make it **automatic** -- so you never forget.

Claude Code supports scheduled tasks that run on a recurring basis. Instead of hoping you remember to audit your context every week, you can set up Claude to do it for you and surface the results.

---

## Choose Your Rhythm

Not everyone needs the same schedule. Your maintenance rhythm depends on how fast your context is changing.

### Which phase are you in?

| Phase | You Are... | Change Pace | Right Rhythm |
|-------|-----------|-------------|-------------|
| **Building** | First 1-2 months. Adding new docs frequently. Still figuring out what data points you need. | High | [Building rhythm](#building-rhythm) |
| **Active** | 3-6 months in. Occasional additions, regular edits. Architecture is taking shape. | Medium | [Active rhythm](#active-rhythm) |
| **Steady** | 6+ months. Mature docs. Changes are infrequent. Mostly maintenance. | Low | [Steady rhythm](#steady-rhythm) |
| **Migration** | Consolidating existing chaos into CLEAR structure. | Burst | [Migration rhythm](#migration-rhythm) |

**Not sure?** Start with the Building rhythm. Move to Active when you stop adding new data points every week. Move to Steady when a month goes by without structural changes.

---

### Building Rhythm

You're creating data points, figuring out boundaries, adding content constantly. Things are messy and that's fine.

| Task | Frequency | What it does |
|------|-----------|-------------|
| **Document Index rebuild** | Daily | `python .claude/scripts/build_document_index.py` — catches new unmanaged docs, tracks metadata health as you add things |
| **Quick health check** | Weekly | Quick CLEAR audit: boundary violations, stale references, naming drift |
| **Lessons capture** | Weekly | What worked this week? What was confusing? Capture while fresh. |

**Skip for now:** Daydream (too early to reflect — you're still building), deep audit (not enough content), quarterly review.

**Prompt:**

> Schedule a daily task: Run `python .claude/scripts/build_document_index.py` to rebuild the Document Index. Then check if any new documents appeared without YAML frontmatter. List them briefly.

> Schedule a weekly task (Monday): Run a quick CLEAR audit across all data points in docs/. Check for boundary violations, broken cross-references, and incomplete metadata. Keep it brief — what needs attention this week?

---

### Active Rhythm

Architecture is taking shape. You're editing more than creating. Time to add reflection.

| Task | Frequency | What it does |
|------|-----------|-------------|
| **Document Index rebuild** | Weekly | Refresh the index, catch new docs |
| **Health check** | Weekly | CLEAR audit + doc-lint + metadata validation |
| **Daydream** | Bi-weekly | Strategic reflection: gaps, relevance, connections |
| **Deep audit + lessons** | Monthly | Thorough cluster audit, lessons consolidation, repo re-scan |

**Prompt:**

> Schedule a weekly task (Monday): Rebuild the Document Index by running `python .claude/scripts/build_document_index.py`. Then run a quick CLEAR audit across all data points. Check for stale content (not updated in 60+ days), boundary violations, and broken references. Produce a brief health summary.

> Schedule a bi-weekly task (Friday): Run a daydream reflection. Review the Document Index and data points. What's changed that our context hasn't caught up with? Any gaps? Any data points becoming irrelevant? Produce a short reflection note.

> Schedule a monthly task (1st Monday): Deep maintenance cycle. (1) Thorough CLEAR audit of one cluster in rotation. (2) Run lessons consolidation. (3) Rebuild Document Index and check for new unmanaged documents. Monthly maintenance report.

---

### Steady Rhythm

Mature architecture. Rare structural changes. Maintenance is about keeping things accurate, not building new.

| Task | Frequency | What it does |
|------|-----------|-------------|
| **Document Index rebuild** | Bi-weekly | Refresh the index |
| **Health check** | Bi-weekly | CLEAR audit, lighter touch |
| **Daydream** | Monthly | Strategic reflection |
| **Deep audit + lessons** | Quarterly | Full architecture review |

**Prompt:**

> Schedule a bi-weekly task (Monday): Rebuild the Document Index and run a CLEAR health check. Focus on staleness — any data points not updated in 90+ days? Any metadata gaps? Brief summary.

> Schedule a monthly task (1st Friday): Daydream reflection. Is the architecture still aligned with business reality? Any clusters that should be added, retired, or restructured?

> Schedule a quarterly task (last week of quarter): Full architecture review. Rebuild Document Index. Comprehensive CLEAR audit across ALL data points. Review ownership assignments. Produce a quarterly report with health score and recommendations.

---

### Migration Rhythm

You're consolidating existing chaos. Heavy activity for 1-3 weeks, then transition.

| Task | Frequency | What it does |
|------|-----------|-------------|
| **Document Index rebuild** | Daily | Track progress as you formalize docs |
| **Quick health check** | Every 2-3 days | Catch contradictions and boundary issues early |
| **Progress review** | Weekly | How many docs migrated? What's left? Any blockers? |

**After migration is complete** (2-3 weeks): Switch to [Active rhythm](#active-rhythm).

**Prompt:**

> Schedule a daily task: Rebuild the Document Index. Report: how many managed documents vs unmanaged? What was added since yesterday?

> Schedule a task every 3 days: Quick CLEAR audit on recently created data points. Check for ownership overlaps and missing boundaries. Flag contradictions between new data points and old documents that haven't been migrated yet.

---

## Every Scheduled Task Includes Document Index Rebuild

`python .claude/scripts/build_document_index.py` runs as part of every scheduled task. It takes seconds. It catches:

- New documents added without metadata
- Metadata that went stale
- Documents that disappeared or were renamed
- Growth or shrinkage of the architecture

The Document Index is always current. No manual maintenance needed.

---

## How to Set Up Schedules

### In Claude Code (CLI)

Ask Claude directly:

> "Schedule a weekly context health check every Monday at 9am"

Claude will use its scheduling capabilities to set up the recurring task. You can list, update, or cancel schedules at any time.

### In Claude Code Desktop / Cowork

Use the scheduled tasks feature:
1. Open the scheduled tasks panel
2. Create a new task
3. Paste the prompt from the relevant section above
4. Set the cron schedule
5. Enable notifications so you see the results

### Cron Expressions Reference

| Task | Cron Expression | Notes |
|------|-----------------|-------|
| Daily | `0 9 * * *` | Every day at 9am |
| Every 3 days | `0 9 */3 * *` | Approximate — runs 1st, 4th, 7th, etc. |
| Weekly (Monday) | `0 9 * * 1` | Monday at 9am |
| Bi-weekly (Friday) | `0 15 * * 5` | Every Friday at 3pm (manually skip alternating weeks) |
| Monthly (1st Monday) | `0 9 1-7 * 1` | First Monday of each month |
| Quarterly | — | Manual trigger recommended |

---

## Always Scheduled vs. Always Manual

| Always Schedule | Always Manual |
|----------------|---------------|
| Document Index rebuild (part of every task) | `clear-planner` (triggered by specific work) |
| Health check (catches silent drift) | `context-ingest` (triggered by new source material) |
| Lessons capture (prevents knowledge evaporation) | `ecosystem-manager` (triggered by ecosystem changes) |
| | Trigger-based reviews (product launch, rebrand, etc.) |

---

## Evolving Your Rhythm

Your schedule is not permanent. As your context architecture matures, adjust:

**Signs to increase frequency:**
- Finding stale content during scheduled checks
- Team members creating docs without metadata
- Business changing faster than context keeps up

**Signs to decrease frequency:**
- Weekly checks consistently find nothing
- Architecture hasn't changed structurally in a month
- Scheduled tasks feel like noise, not signal

**Rule of thumb:** If 3 consecutive scheduled checks find nothing, reduce that task's frequency by half.

---

## Reviewing Scheduled Results

When a scheduled task produces results:

1. **Scan the summary first.** If everything is green, you're done in 30 seconds.
2. **Act on urgents immediately.** Broken references, ownership gaps, contradictions.
3. **Queue non-urgents.** Add to your next planning session or weekly review.
4. **Capture surprises.** If the audit found something unexpected, that's a lesson -- save it.

The goal is not zero findings. The goal is **no surprises**. Regular maintenance means issues are small and expected, not large and alarming.

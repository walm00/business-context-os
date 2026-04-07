# Scheduled Maintenance

**Context that isn't maintained rots.** These 5 scheduled tasks keep your knowledge alive automatically.

Default frequencies are aggressive — daily and weekly. It's better to catch problems while they're small than discover a mess weeks later. If checks consistently find nothing, reduce frequency.

---

## Setup

Tell Claude:

> **Set up CLEAR maintenance schedules. Use the exact task definitions from docs/guides/scheduling.md.**

Or Claude will offer to set them up when it reaches that item on your onboarding checklist.

---

## The 5 Tasks

Claude: when creating scheduled tasks, use these exact definitions. Each block below is one task.

---

### Task 1: Index + Health Check

**ID:** `clear-daily-index`
**Schedule:** Daily (`0 9 * * *`)
**Description:** Daily document index rebuild + CLEAR health check

**Prompt:**

```
Run scheduled CLEAR maintenance: Daily Index + Health Check.

1. Run: python .claude/scripts/build_document_index.py
2. Scan docs/ (excluding _inbox/, _planned/, _archive/) for:
   - New .md files missing YAML frontmatter
   - Missing required metadata fields
   - Boundary violations (content that belongs in a different document)
   - Broken cross-references (links to files that don't exist)
3. Brief report:
   - Total managed documents
   - Issues found (one line each)
   - One-line verdict: "All good" or "X items need attention"

Keep output short. If healthy, say so in one line.
```

---

### Task 2: Daydream + Lessons (Monday)

**ID:** `clear-monday-daydream`
**Schedule:** Monday (`0 9 * * 1`)
**Description:** Weekly daydream reflection + lessons capture + session pruning

**Prompt:**

```
Run scheduled CLEAR maintenance: Monday Daydream + Lessons.

1. Read docs/.wake-up-context.md and docs/.session-diary.md for orientation
2. Run: python .claude/scripts/build_document_index.py
3. Strategic reflection (5-8 bullets max):
   - What changed this week that context hasn't caught up with?
   - Topics we discuss but haven't formalized?
   - Data points that no longer reflect reality?
   - Connections between documents we're not seeing?
4. Lessons capture:
   - Read .claude/quality/ecosystem/lessons.json
   - What worked this week? What was confusing?
   - Any overlapping or stale lessons to consolidate?
5. Run: python .claude/scripts/prune_sessions.py
6. Run: python .claude/scripts/prune_diary.py
7. End with: "Highest-value next action: ..."

Keep it focused and strategic.
```

---

### Task 3: Mid-week Daydream (Wednesday)

**ID:** `clear-wednesday-daydream`
**Schedule:** Wednesday (`0 15 * * 3`)
**Description:** Mid-week standalone daydream — deeper strategic reflection

**Prompt:**

```
Run scheduled CLEAR maintenance: Wednesday Daydream.

1. Read docs/.wake-up-context.md and docs/.session-diary.md for orientation
2. Run: python .claude/scripts/build_document_index.py
3. Run: python .claude/scripts/analyze_crossrefs.py (if it exists)
4. Deeper reflection:
   - What's the biggest gap in our context right now?
   - Any data points that should be split, merged, or retired?
   - What business reality has shifted that our docs don't reflect?
   - Any patterns across recent sessions that suggest a structural change?
5. One concrete recommendation: "The highest-value thing to do next is..."

This is the deeper thinking session. Be strategic, not mechanical.
```

---

### Task 4: Deep Audit + Inbox (Friday)

**ID:** `clear-friday-audit`
**Schedule:** Friday (`0 9 * * 5`)
**Description:** Weekly deep audit, lessons consolidation, and inbox processing

**Prompt:**

```
Run scheduled CLEAR maintenance: Friday Deep Audit + Inbox.

1. Run: python .claude/scripts/build_document_index.py
2. Deep CLEAR audit (pick one cluster in rotation each week):
   - Boundary violations and ownership gaps
   - Stale cross-references (files moved, renamed, or deleted)
   - Duplicate or near-duplicate content across documents
   - Documents that should be archived (superseded or inactive 90+ days)
3. Lessons consolidation:
   - Read .claude/quality/ecosystem/lessons.json
   - Identify overlapping or redundant lessons
   - Flag lessons that are no longer relevant
4. Inbox check:
   - Scan docs/_inbox/ for files older than 7 days
   - List unprocessed items with a suggested action (process, archive, discard)
5. Weekly summary:
   - Top 3 findings
   - Top 3 recommended actions for next week
```

---

### Task 5: Architecture Review (Monthly)

**ID:** `clear-monthly-architecture`
**Schedule:** 1st of month (`0 9 1 * *`)
**Description:** Monthly full architecture + ecosystem review

**Prompt:**

```
Run scheduled CLEAR maintenance: Monthly Architecture Review.

1. Run: python .claude/scripts/build_document_index.py
2. Full CLEAR audit across ALL data points (not just one cluster):
   - Every document's ownership spec — still accurate?
   - Every cross-reference — does it resolve?
   - Ownership gaps — topics that no one owns?
   - Duplicates — content in multiple places?
3. Ecosystem check:
   - Run: python .claude/scripts/analyze_integration.py --staged (if applicable)
   - Compare .claude/quality/ecosystem/state.json against actual files
   - Any skills, hooks, or scripts that are stale or redundant?
4. Lessons review:
   - Read .claude/quality/ecosystem/lessons.json
   - Which lessons have become obvious and can be retired?
   - Which lessons are still being violated?
5. Monthly report:
   - Health score (0-10)
   - Top 5 findings
   - Top 3 recommendations for next month
   - One strategic insight: what's the system getting right, and what needs to improve?
```

---

## Adjusting Later

Your schedule is not permanent. As your context matures:

- **If 3 consecutive checks find nothing** — reduce that task's frequency by half
- **If checks keep finding problems** — increase frequency or fix the root cause
- **Quarterly architecture review** — when things stabilize, switch monthly to quarterly

To change a schedule, tell Claude: "Update my CLEAR [task name] schedule to [new frequency]."

---

## Reviewing Results

When a scheduled task produces results:

1. **Scan the summary.** If everything is green, you're done in 30 seconds.
2. **Act on urgents.** Broken references, ownership gaps, contradictions.
3. **Queue the rest.** Add to your next work session.
4. **Capture surprises.** If the audit found something unexpected, that's a lesson.

The goal is not zero findings. The goal is **no surprises**.

# Scheduling Recurring Maintenance

**Set it and forget it. Let Claude remind you to maintain your context instead of relying on willpower.**

---

## Why Schedule?

The maintenance checklist tells you WHAT to do. The maintenance guide tells you WHY. This guide tells you HOW to make it **automatic** -- so you never forget.

Claude Code supports scheduled tasks that run on a recurring basis. Instead of hoping you remember to audit your context every week, you can set up Claude to do it for you and surface the results.

---

## The Recommended Schedule

These are the recurring tasks that keep your context alive. Set them up once, and they run automatically.

### Weekly: Context Health Check

**What it does:** Runs a quick CLEAR audit across your context data points. Checks for stale content, broken cross-references, ownership gaps, and boundary violations.

**Skills involved:** `context-audit` + `doc-lint`

**Schedule:** Weekly, Monday morning

**Prompt for Claude Code scheduling:**

> Set up a weekly scheduled task: Every Monday morning, run a quick context health check. Scan all data points in the docs/ folder for CLEAR compliance issues. Check for: stale data points (not updated in 60+ days), broken cross-references, ownership gaps, naming inconsistencies, and markdown syntax issues. Produce a brief health summary -- what's fine, what needs attention, and what's urgent. Keep it under 1 page.

**What to expect:** A short health report surfaced every Monday. Most weeks: "All clear." Some weeks: "Brand voice hasn't been updated in 90 days -- is it still accurate?"

---

### Bi-weekly: Strategic Reflection (Daydream)

**What it does:** Steps back and asks the bigger questions. Are your data points still aligned with where the business is heading? Any gaps emerging? Any context that's becoming irrelevant?

**Skills involved:** `daydream`

**Schedule:** Every other Friday afternoon

**Prompt for Claude Code scheduling:**

> Set up a bi-weekly scheduled task: Every other Friday, run a daydream reflection on my context architecture. Review the Table of Context and all data points. Ask: What's changed in the business that our context hasn't caught up with? Are there new topics we should be tracking? Are any data points becoming irrelevant? What connections between data points are we missing? Produce a short reflection note with any suggested actions.

**What to expect:** A reflective note that prompts you to think. Not urgent actions -- more "have you considered..." nudges that prevent strategic drift.

---

### Monthly: Deep Audit + Lessons Consolidation

**What it does:** Runs a thorough audit of one cluster (rotating), consolidates institutional knowledge, and re-scans the repo for undocumented context.

**Skills involved:** `context-audit` (deep mode) + `lessons-consolidate` + `context-onboarding` (re-scan)

**Schedule:** First Monday of each month

**Prompt for Claude Code scheduling:**

> Set up a monthly scheduled task: On the first Monday of each month, run a deep context maintenance cycle. Do three things: (1) Pick the next cluster in rotation and run a thorough CLEAR audit -- check every data point for accuracy, completeness, boundary integrity, and relationship health. (2) Run lessons consolidation -- check lessons.json for stale, overlapping, or contradictory lessons. (3) Re-scan the repo for any new documents or knowledge sources that haven't been formalized into data points. Produce a monthly maintenance report with findings and recommendations.

**What to expect:** A comprehensive monthly report. Takes 10-15 minutes to review. The most important maintenance touchpoint.

---

### Quarterly: Architecture Review

**What it does:** Full architecture health assessment. Reviews whether the entire context architecture still matches business reality.

**Skills involved:** `context-onboarding` (full re-scan) + `context-audit` (full) + `daydream` (strategic)

**Schedule:** Last week of each quarter

**Prompt for Claude Code scheduling:**

> Set up a quarterly scheduled task: In the last week of each quarter, run a full architecture review. (1) Re-scan the entire repo to update the Table of Context. (2) Run a comprehensive CLEAR audit across ALL data points and clusters. (3) Run a strategic daydream focused on: Does our context architecture still match our business direction? Should any clusters be added or retired? Are ownership assignments still correct? Produce a quarterly architecture report with a health score and strategic recommendations.

**What to expect:** A thorough quarterly report. Share this with your team and use it to plan context maintenance for the next quarter.

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

### Suggested Cron Expressions

| Task | Schedule | Cron Expression |
|------|----------|-----------------|
| Weekly health check | Monday 9am | `0 9 * * 1` |
| Bi-weekly daydream | Every other Friday 3pm | `0 15 * * 5` (manually skip alternating weeks, or use a specific date pattern) |
| Monthly deep audit | 1st Monday of month 9am | `0 9 1-7 * 1` |
| Quarterly review | Last Monday of Mar/Jun/Sep/Dec | Manual trigger recommended |

---

## What's Automatic vs. Manual

Not everything should be scheduled. Here's the breakdown:

### Schedule These (Recurring)

| Task | Why Automate? |
|------|---------------|
| **Weekly health check** | Drift happens silently. Catching it early prevents expensive fixes later. |
| **Bi-weekly daydream** | Strategic thinking gets squeezed out by daily urgency. A scheduled prompt makes space for it. |
| **Monthly deep audit** | Nobody remembers to do deep audits. Scheduling removes willpower from the equation. |
| **Monthly lessons consolidation** | Institutional knowledge degrades without active maintenance. |
| **Monthly repo re-scan** | New documents appear that should be formalized. Scheduled scans catch them. |

### Keep Manual (Triggered by Need)

| Task | Why Manual? |
|------|-------------|
| **clear-planner** | Triggered by specific work -- "I need to restructure our audience data points." |
| **ecosystem-manager** | Triggered by ecosystem changes -- "I want to create a new skill." |
| **Trigger-based reviews** | Business events (product launch, rebrand, competitor move) -- can't predict the schedule. |

---

## Starting Simple

Don't set up all schedules on day one. Build up gradually:

**Week 1:** Set up the weekly health check only. See if it's useful.

**Week 3:** Add the bi-weekly daydream if you find the weekly check valuable.

**Month 2:** Add the monthly deep audit + lessons consolidation.

**Quarter 2:** Add the quarterly review once you have a quarter of history.

---

## Reviewing Scheduled Results

When a scheduled task produces results:

1. **Scan the summary first.** If everything is green, you're done in 30 seconds.
2. **Act on urgents immediately.** Broken references, ownership gaps, contradictions.
3. **Queue non-urgents.** Add to your next planning session or weekly review.
4. **Capture surprises.** If the audit found something unexpected, that's a lesson -- save it.

The goal is not zero findings. The goal is **no surprises**. Regular maintenance means issues are small and expected, not large and alarming.

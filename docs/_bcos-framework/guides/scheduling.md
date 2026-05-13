# Scheduled Maintenance

**Context that isn't maintained rots.** BCOS ships one scheduled task per repo that keeps your knowledge alive automatically.

The dispatcher runs once a day. It decides which maintenance jobs are due, runs them in sequence, writes one consolidated digest to `docs/_inbox/daily-digest.md`, and appends to a local history file. You read one report. You don't manage five separate schedules.

---

## Setup

During onboarding, Claude creates a single task named `bcos-{project}` (e.g. `bcos-leverage`). It runs daily at 09:00 local time by default.

To set it up manually, tell Claude:

> **Set up CLEAR maintenance scheduling. Use the schedule-dispatcher skill.**

To adjust it later, tell Claude in natural language:

> "Switch the dispatcher to 08:30."
> "Run the audit twice a week instead of weekly."
> "Turn off the deep daydream for now."
> "Reduce index-health to weekdays only."

Claude uses the `schedule-tune` skill to update `.claude/quality/schedule-config.json` safely. You shouldn't need to hand-edit the config, and the config has natural-language hints inline to explain what each setting does.

---

## The Five Jobs

The dispatcher runs up to five jobs each morning. Each job has a default cadence. You can change any of them.

| Job                   | Default    | What it does                                                       |
|-----------------------|------------|--------------------------------------------------------------------|
| `index-health`        | Daily      | Rebuild document index; scan for frontmatter / metadata / broken xrefs; auto-fix low-risk issues |
| `daydream-lessons`    | Mon        | Weekly strategic reflection + lessons capture + session pruning     |
| `daydream-deep`       | Wed        | Deeper structural reflection — splits, merges, retirements          |
| `audit-inbox`         | Fri        | Deep CLEAR audit (one cluster in rotation) + inbox aging + lessons triage |
| `architecture-review` | 1st        | Full-architecture audit + ecosystem drift + health score + 3 priorities for the month |

Full job specs live in `.claude/skills/schedule-dispatcher/references/job-*.md`. If you want to understand exactly what runs, read those files — they're the authoritative source.

### Why these cadences?

They're **aggressive starting defaults**. Better to catch problems while small than to discover a mess weeks later. As your context matures:

- If `index-health` finds nothing for 3+ days → dispatcher suggests reducing to weekdays
- If `daydream-deep` finds nothing for 3+ weeks → suggests moving to monthly
- If `audit-inbox` keeps finding the same things → suggests increasing frequency or fixing root cause

**The dispatcher only suggests. It never changes cadence automatically.** You approve every change.

---

## What You See

Every morning, the dispatcher writes the full digest to `docs/_inbox/daily-digest.md`. But the primary interface is **your Claude Code session dashboard** — the dispatcher uses session states to pre-triage your attention.

### The dashboard becomes your priority inbox

| Dashboard status | What it means | Your action |
|---|---|---|
| 🟡 **Awaiting input** (yellow) | Dispatcher found something that needs your judgement — action items, frequency suggestions, or an error | Open the session, click through the structured options |
| 🔵 **Ready** (blue) | Clean green run — nothing to act on | Bulk "Mark all read" and move on |

This is the meaningful signal: yellow = attend, blue = dismiss. If every morning's run is clean, you bulk-read-acknowledge a row of blue sessions in one click. If one has findings, it's the only yellow row — impossible to miss.

### When a run has findings (yellow "Awaiting input")

Short chat summary:

```
Maintenance complete — verdict: amber.
3 findings, 2 auto-fixed. Full report: docs/_inbox/daily-digest.md
```

Then a question with 2-4 concrete options you can click:

- Walk me through the action items
- Show full digest
- Dismiss for now

Click "Walk me through" → the dispatcher loads the first action item, explains it, and asks what to do. Click "Show full digest" → the digest appears, then you're asked again with updated options. Click "Dismiss" → done in one click, session marks read.

### When a run is clean (blue "Ready")

One line, no question, nothing to click:

```
Maintenance complete — verdict: green. Nothing to act on.
```

Session auto-marks as Ready. You never have to open it unless curious.

This rule applies to every dispatch path: scheduled morning run, on-demand "run today's maintenance now", and single-job runs like "run audit-inbox now". Questions appear only when something is actually worth your attention.

### The digest file structure

`docs/_inbox/daily-digest.md` is the full report, useful when you want depth:

```markdown
# Daily Maintenance Digest — 2026-04-15

**Overall:** amber — 5 jobs ran, 7 findings, 3 auto-fixed.

## Action needed (4)
- [ ] audit-inbox: 2 inbox files aged > 7 days — triage
- [ ] daydream-lessons: reconcile stage claim in brand-identity vs current-state
- [ ] index-health: docs/new-playbook.md has no frontmatter
- [ ] audit-inbox: lessons X and Y overlap — merge?

## Auto-fixed (3)
- index-health: missing-last-updated in brand-identity.md
- index-health: eof-newline in competitive-positioning.md
- audit-inbox: trailing-whitespace in messaging-framework.md

## Per-job summary
### index-health — green (after fixes)
### daydream-lessons — amber (4 observations)
...

## Frequency suggestions
- daydream-deep has been green 3 runs running. Consider running it less often.
```

You don't HAVE to open this file — the in-chat menu gets you everywhere. The file is there when you want to read the full context in one place.

**Green with zero findings**: you still get a menu (consistent UX), but the default option is "Done, thanks" and a single click closes the cycle.

---

## Auto-Fix Policy

The dispatcher is allowed to apply a short list of structural fixes without asking. The defaults:

- Missing `last-updated` field → set to today
- Frontmatter field order normalization
- Trailing whitespace / EOF newline
- Broken cross-reference where exactly one rename candidate exists

Everything else — missing whole frontmatter blocks, boundary violations, stale content, content contradictions, archive decisions — becomes an action item for you to review.

Full semantics: `.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md`.

To change the whitelist, tell Claude: *"Stop auto-fixing trailing whitespace."* or *"Enable auto-fix for broken cross-references."*

---

## On-Demand Jobs

You don't have to wait for the scheduled time. Any job can be run manually:

> "Run the audit-inbox job now."
> "Do a quick index-health."
> "Run today's maintenance."

On-demand runs **don't** write to the daily digest (that's reserved for the morning scheduled run) and **don't** emit frequency-tuning suggestions. They do log to the diary so the history stays complete.

---

## The Schedule Diary

Every job run appends one line to `.claude/hook_state/schedule-diary.jsonl`:

```json
{"ts":"2026-04-15T09:04:12","job":"index-health","verdict":"green","findings_count":0,"auto_fixed":[],"actions_needed":[],"duration_s":4}
```

The diary is:

- **Gitignored** — local to your machine, doesn't clutter commits
- **Append-only** — never rewritten, corrective entries added if needed
- **Used for tuning suggestions** — the dispatcher reads recent entries to decide when to suggest frequency changes

To ask Claude about history:

> "How has audit-inbox looked over the last month?"
> "What did the dispatcher say last Tuesday?"
> "Has architecture-review ever run red?"

---

## Configuration

The config file is `.claude/quality/schedule-config.json`. You can read it, but you shouldn't hand-edit it — it has a specific schema and the natural-language flow is less error-prone.

Structure (abbreviated):

```json
{
  "version": "1.0",
  "jobs": {
    "index-health":       { "enabled": true, "schedule": "daily" },
    "daydream-lessons":   { "enabled": true, "schedule": "mon"   },
    "daydream-deep":      { "enabled": true, "schedule": "wed"   },
    "audit-inbox":        { "enabled": true, "schedule": "fri"   },
    "architecture-review":{ "enabled": true, "schedule": "1st"   }
  },
  "auto_fix": {
    "enabled": true,
    "whitelist": ["missing-last-updated", "..."]
  },
  "digest": { "write_file": true, "path": "docs/_inbox/daily-digest.md" },
  "tuning": { "suggest_reduce_after_green_runs": 5 }
}
```

Valid `schedule` values: `"daily"`, `"mon"..."sun"`, `"weekdays"`, `"weekends"`, `"1st"`, `"15th"`, `"last"`, `"every-Nd"` (every N days), `"off"`, or a raw cron string.

---

## Why scheduled tasks sometimes get stuck

Scheduled dispatcher runs spawn fresh Claude Code sessions with no human at the keyboard. A permission prompt during one of those runs hangs the task until a human notices. The fix is to ship the right permissions by default.

The authoritative contract lives in [permissions-catalog.md](../architecture/permissions-catalog.md) — what entries BCOS ships, what each one enables, and the bidirectional drift guard (`validate_permissions_catalog.py`) that runs in CI and during onboarding. If you installed BCOS before v1.5 and want to pick up newer dispatcher entries: `python .claude/scripts/update.py` (the `merge_settings_json` step is additive — your customisations stay).

One permission BCOS cannot ship by default: `mcp__scheduled-tasks__create_scheduled_task`, used during onboarding to create the cron task itself. Pick **"Always allow"** the first time so future scheduled runs aren't stuck on it.

### Cross-repo workflows

When BCOS workflows span multiple repos (umbrella + sub-repos, sibling writes), the project-level allowlist isn't enough. Mirror it into `~/.claude/settings.json`:

```bash
python .claude/scripts/install_global_permissions.py --dry-run   # preview
python .claude/scripts/install_global_permissions.py             # apply
```

Trust-model implications, the five-state reconciliation algorithm used by the umbrella plugin's parallel surface, and revocation guidance all live in [permissions-catalog.md > Managed permission surfaces](../architecture/permissions-catalog.md#managed-permission-surfaces).

---

## Multi-Repo Users

Scheduled tasks live in `~/.claude/scheduled-tasks/` — **user-global, not per-repo**. If you run BCOS on multiple repos, each one needs its own dispatcher task with a unique ID.

- Task ID format: `bcos-{project}` where `{project}` is a short slug derived from the repo folder name
- Task prompt includes the absolute repo path so the dispatcher always runs in the right directory
- Onboarding handles both automatically — you should never see collisions

If you want a cross-repo combined digest, that's a separate feature not covered by this guide. Ask in a separate session.

---

## Migration from older versions

If you are on a pre-v1.2 install (five standalone scheduled tasks per repo rather than the single `bcos-{project}` dispatcher), see [CHANGELOG.md § Upgrading from pre-v1.2](../../../CHANGELOG.md#upgrading-from-pre-v12). The short version: update to v1.2.x first (which has the migration helper), then update to the current version. Migration tooling is no longer shipped in current releases.

---

## Adjusting Later

Your schedule is not permanent. Signals to adjust:

- **Job keeps finding nothing** (dispatcher will suggest this) — reduce frequency
- **Job keeps finding the same issue** — fix the root cause instead of running more often
- **Inbox grows faster than weekly triage** — bump `audit-inbox` to twice a week
- **You've stopped reading the digest** — dispatcher is too noisy; reduce depth or frequency
- **A cluster is suddenly active** — consider temporarily increasing `audit-inbox` rotation speed

Tell Claude the signal, Claude handles the config change.

---

## Reviewing Results

When the daily digest lands:

1. **Scan the one-liner.** If green with zero actions, you're done in 5 seconds.
2. **Act on action items.** Open the digest, work through the list.
3. **Apply suggested tuning.** If the dispatcher suggests a frequency change and it makes sense, tell Claude to apply it.
4. **Capture surprises.** If an audit found something unexpected about your business, that's a lesson — tell Claude to capture it.

The goal is not zero findings. The goal is **no surprises**.

---

## References

| Resource                  | Path                                                                          |
|---------------------------|-------------------------------------------------------------------------------|
| Dispatcher skill          | `.claude/skills/schedule-dispatcher/SKILL.md`                                 |
| Job specs                 | `.claude/skills/schedule-dispatcher/references/job-*.md`                      |
| Auto-fix whitelist        | `.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md`         |
| Config                    | `.claude/quality/schedule-config.json` (your repo's live config)              |
| Config template           | `.claude/quality/schedule-config.template.json` (defaults shipped by BCOS)    |
| Diary                     | `.claude/hook_state/schedule-diary.jsonl` (gitignored, machine-local)         |
| Digest                    | `docs/_inbox/daily-digest.md` (overwritten daily)                             |
| Maintenance lifecycle     | `docs/_bcos-framework/architecture/maintenance-lifecycle.md`                  |

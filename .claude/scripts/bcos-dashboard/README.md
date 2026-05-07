# BCOS Dashboard

A local, zero-dependency dashboard for any BCOS-enabled repo. Shows
dispatcher job status, today's actions, and recent run history — with a
freshness canary so silently-skipped maintenance runs surface visibly
instead of corrupting the rest of the view.

## What it shows

The main page is a single **cockpit** — the "one glance" surface for an
average knowledge worker. Detail and admin views live behind explicit
interactions so the front page never piles up.

| Surface | Where | What |
|---|---|---|
| Cockpit headline | `/` | One sentence — "Your system is healthy" / "N things are waiting on a decision from you" / "Heads up — background data is X old". Tone (ok / warn / critical / info / first-run) drives the accent colour. |
| Things waiting on you | `/` | Inline attention list. Each row has a Mark-done button (90-day retention). Job chip opens the per-job drawer. |
| Maintenance routine | `/` | Per-job dot strip — one dot per maintenance job. Core BCOS (`index-health`, `audit-inbox`, `daydream-lessons`, `daydream-deep`, `architecture-review`) + wiki zone (`wiki-stale-propagation`, `wiki-source-refresh`, `wiki-graveyard`, `wiki-coverage-audit`). Click a dot to open its drawer. |
| Per-job drawer | dot click | Slide-in side drawer (bottom sheet on mobile). Schedule, last/next run, today's digest body, last 5 runs, change-frequency presets, technical-details footer. |
| Run history | `/settings/runs` | Last 20 diary entries with filter chips (job / verdict / trigger). |
| File health | `/settings/files` | Frontmatter / xref / stale findings with one-click fixes for whitelisted IDs. |
| Context Atlas | `/atlas` | Context structure lenses plus shared ranked context search over `context-index.json`. |
| Schedules | `/settings/schedules` | Bulk per-job preset editor + auto-fix whitelist toggles. Saves directly to `schedule-config.json`. |
| Technical | `/settings/technical` | Snapshot-freshness canary (verbose), MCP refresh hint with copy-to-clipboard, raw `schedule-config.json` viewer, debug info. |

## Quick start

From the root of any BCOS-enabled repo:

```bash
python .claude/scripts/bcos-dashboard/run.py
```

Then open <http://127.0.0.1:8091>.

The dashboard runs as a long-lived local HTTP server. Leave the tab
open — it auto-refreshes every 30 s.

## Data sources (read-only)

All standard BCOS locations — no special setup required beyond a
working BCOS install:

| Source | Read from | Owned by |
|---|---|---|
| Enabled jobs + cadence | `.claude/quality/schedule-config.json` | `schedule-tune` skill |
| Today's verdicts + actions | `docs/_inbox/daily-digest.md` | `schedule-dispatcher` skill |
| Run history | `.claude/hook_state/schedule-diary.jsonl` | `schedule-dispatcher` skill |
| Next/last run timestamps | `~/.local-dashboard/schedules.json` | Claude (via daily snapshot job) |

One-click writes (mark-done, schedule presets, whitelist toggles, file
fixes) go through dedicated POST endpoints (`/api/actions/resolve`,
`/api/schedule/preset`, `/api/schedule/whitelist`, `/api/file-health/fix`).
The `schedule-tune` skill remains the canonical free-form path; the
dashboard's preset buttons are its deterministic complement.

## Configuration

Environment variables (all optional):

| Variable | Default | Purpose |
|---|---|---|
| `BCOS_DASHBOARD_PORT` | `8091` | HTTP port (bumps to next free port if busy) |
| `BCOS_REPO_ROOT` | `three folders up from run.py` | Override the repo root for data sources |
| `BCOS_TASK_ID` | `bcos-<repo-name>` | Override the scheduled-task ID used to find next/last run in `schedules.json` |

## Keeping `~/.local-dashboard/schedules.json` fresh

The dashboard's §00 canary reports staleness if this file is more than
26h old. Keeping it fresh requires a Claude-executed dispatcher step:

```
Call mcp__scheduled-tasks__list_scheduled_tasks and write the result to
~/.local-dashboard/schedules.json using this schema:

{
  "generated_at": "<ISO-utc>",
  "note": "Snapshot of mcp__scheduled-tasks__list_scheduled_tasks.",
  "tasks": [...]
}

Preserve every field from the MCP response. Don't invent nextRunAt for
disabled tasks.
```

Add this as a daily job in `.claude/quality/schedule-config.json` to
keep the snapshot fresh automatically. See the `schedule-dispatcher`
skill for wiring.

## Architecture

Zero-dependency Python stdlib + a small framework (`server.py`) vendored
from [`local-dashboard-builder`](https://github.com/walm00/local-dashboard-builder).

| Module | Role |
|---|---|
| `server.py` | HTTP server + TTL-cached panel framework |
| `digest_parser.py` | Parse `daily-digest.md` into structured per-job sections |
| `diary_grouper.py` | Normalize + group `schedule-diary.jsonl` by job |
| `freshness.py` | Snapshot-freshness canary collector |
| `single_repo.py` | Compose jobs / actions / history / cockpit / per-job detail from shared `_snapshot()` |
| `labels.py` | Single source of truth for technical-id → human-label translation |
| `actions_resolved.py` | Mark-done persistence (90-day retention, fingerprint-keyed) |
| `schedule_editor.py` | Atomic writes to `schedule-config.json` (preset + whitelist) |
| `file_health.py` | Frontmatter / xref / stale findings + auto-fix execution |
| `run.py` | Entry point — declares the cockpit panel + hidden settings panels + POST/GET routes |
| `dashboard.html/css/js` | Static shell + client-side rendering, routing, and drawer controller |
| `../context_search_service.py` | Shared `/api/context-search` request parsing, index filtering, and result enrichment |

Each collector is a zero-arg callable returning a dict matching the
framework's panel-kind contract. `_snapshot()` caches the heavy reads
once per refresh so the three single-repo collectors don't each re-read
the digest and diary.

## Roadmap

Complete — the seven-step UX rebuild (cockpit + drawer + /settings +
states + a11y/responsive/dark) shipped in this branch. Open follow-ups:

- `/settings/maintenance-history` — heatmap calendar of last 90 days of
  diary entries
- File-level inspection drawer — click a file in `/settings/files` to
  see its full frontmatter, stale-detection rationale, and "open in
  editor"
- `/settings/about` — version, framework docs link, license

See `docs/_bcos-framework/` for the full BCOS methodology. The dashboard
is a visibility and control layer over the existing
`schedule-dispatcher` / `schedule-tune` skill pair — it does not
replace them.

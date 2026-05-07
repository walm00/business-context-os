---
name: BCOS Dashboard — Steps 4-7 (cockpit + drawer + settings + states + a11y)
description: Resumable plan covering the remaining four steps of the BCOS Dashboard cockpit-and-drawer rebuild. A fresh session should be able to start at Phase 1 (Step 4) without reloading prior conversation.
type: plan
session-id: 20260424_203941_bcos-dashboard-steps-4-7
scenario: agenting
status: awaiting_approval
working-repo: business-context-os-dev
working-path: .claude/scripts/bcos-dashboard/
created: 2026-04-25
---

# BCOS Dashboard — Steps 4-7

**Session ID**: `20260424_203941_bcos-dashboard-steps-4-7`
**Scenario**: AGENTING
**Status**: awaiting_approval
**Working repo**: `C:\Users\Mr Coders\Documents\GitHub\business-context-os-dev`
**Working path**: `.claude/scripts/bcos-dashboard/`

---

## 1. Quick context (read first)

The BCOS Dashboard is a standalone, repo-agnostic dashboard shipped as part of the BCOS framework. It surfaces the dispatcher's daily output (digest, diary, schedule-config) for any BCOS-enabled repo. This plan covers Steps 4-7 of a 7-step UX rebuild from technical-log style to a cockpit-and-drawer IA designed for the average knowledge worker.

**Steps 1-3 are shipped.** Steps 4-7 are this plan.

### What the dashboard looks like RIGHT NOW (after Step 3)

Main page contains:

1. **Cockpit** (the hero): headline sentence + inline attention list + 5-dot maintenance strip. Always present.
2. **`jobs_panel`** (standalone panel): per-job cards with verdict, schedule, history, preset buttons. Currently sits below the cockpit.
3. **`snapshot_freshness`** (standalone panel): canary on `~/.local-dashboard/schedules.json` age.
4. **`run_history`** (standalone panel): unified diary timeline with filter chips.
5. **`file_health`** (standalone panel): aggregated frontmatter / xref / stale findings with one-click fixes.

**Steps 4-7 move panels 2-5 into either a click-driven side drawer (jobs panel) or a dedicated `/settings` route (the other three).** The main page becomes pure cockpit.

### Architecture facts (do NOT re-derive in the new session)

| Topic | Status |
|---|---|
| `server.py` | Vendored from `local-dashboard-builder/skills/local-dashboard-builder/templates/server.py`. Diverges from upstream — extended `VALID_KINDS` to include `cockpit / jobs_panel / actions_inbox / run_history / file_health`. Added `do_POST` + `post_routes` kwarg + `(body, ctx)` handler signature. `ctx["invalidate_panel"](id)` busts a panel's TTL cache. |
| `labels.py` | Single source of truth for technical-id → human-label mapping. All collectors call `decorate_*` to attach `display_*` fields. Renderers prefer `display_*` and fall back to raw values. |
| `actions_resolved.py` | Mark-done persistence. `.claude/hook_state/actions-resolved.jsonl`. Fingerprinted by `sha1(normalize(title))[:16]`. 90-day retention. |
| `schedule_editor.py` | Direct JSON editor for `.claude/quality/schedule-config.json`. Atomic writes (`.tmp` + `os.replace`). Schema-validated. |
| `file_health.py` | Reads `docs/`, classifies findings, links auto-fix IDs. Tier-1 fixes whitelisted. |
| `single_repo.py` | Composes the 5 collectors used by the dashboard: `collect_cockpit`, `collect_jobs_panel`, `collect_actions_inbox`, `collect_run_history`, `collect_file_health`. Plus `_humanize_relative` helper. |
| `freshness.py` | Snapshot canary collector. |
| `BCOS_REPO_ROOT` env var | Lets the dashboard run against any BCOS repo. Defaults to three folders up from `run.py`. |
| `BCOS_TASK_ID` env var | Lets the dashboard pin a non-default scheduled-task ID for next/last-run lookup. Defaults to `bcos-<repo-name>`. |
| Cache invalidation | Resolve/unresolve handlers invalidate `actions_inbox` AND `cockpit`. Schedule preset writes invalidate `jobs_panel` AND `cockpit`. Reason: cockpit composes other collectors; without busting it, periodic refresh re-renders stale state and overwrites optimistic UI. |

### Locked design decisions (do NOT re-litigate)

- **Audience**: average knowledge worker (non-technical). Not power user. Not "you" the developer.
- **IA**: cockpit + drawer (chosen over retitle / hybrid).
- **Headline**: "Your knowledge system" (not "Theo's", not personal-name).
- **Maintenance strip**: always visible (Option A — reassurance).
- **Attention items**: just list, no prioritization, no collapse.
- **Settings**: separate route with browser back-button support (chosen over tabs).

---

## 2. Problem statement

After Step 3 the dashboard is half-cockpit, half-old: the cockpit reads beautifully, but four standalone panels still pile up below it, undoing the "one glance" intent. The remaining steps complete the IA migration so the main page becomes only the cockpit, with detail and admin views behind explicit interactions.

## 3. Proposed solution (per Step)

### Step 4 — Per-job drawer

Click a dot on the maintenance strip → a side-drawer slides in from the right at 480px wide on desktop, full-screen bottom sheet on mobile. Esc or click-outside closes. Only one drawer open at a time — opening a different one slides this one out and the next in.

**Drawer body** (top → bottom):

1. Header: human job name + verdict badge + close ×
2. Schedule line: "Runs every weekday at ~9 AM"
3. Last/Next run: "Last ran: this morning · Next run: tomorrow morning"
4. WHAT IT DOES — short description from `JOB_LABELS` hint
5. TODAY'S RESULT — body extracted from today's digest section for this job
6. RECENT RUNS — list of last 5 runs (verdict dot + relative time + verdict + brief notes)
7. CHANGE FREQUENCY — preset buttons (reuse existing `_renderSchedulePresets`)
8. Collapsed "Technical details" footer — raw job ID, schedule-config path, ISO timestamps, fingerprint

**Standalone `jobs_panel` Panel is REMOVED from main page** — its content lives only in the drawer. The cockpit's 5-dot strip stays as the entry point.

### Step 5 — `/settings` route

A real URL with `pushState` + `popstate`. Server.py serves the same HTML for any path that isn't `/api/*` or `/static/*` (SPA fallback). Client-side router decides whether to render the cockpit or the settings layout.

**Settings sub-pages:**
- `/settings/runs` — Run history (current `run_history` panel, full filter bar)
- `/settings/files` — File health (current `file_health` panel, one-click fixes)
- `/settings/schedules` — Schedules: bulk per-job preset editor + auto-fix whitelist toggles
- `/settings/technical` — Snapshot freshness (verbose form), MCP refresh hint with copy-to-clipboard, raw `schedule-config.json` viewer, env vars, debug info

**Layout:**
- Top bar with `[← Back]` button + repo name
- Side nav with the 4 sub-page links
- Main content area swaps based on subpath

**Standalone `snapshot_freshness`, `run_history`, `file_health` Panels REMOVED from main page.** Their collectors still feed `/api/panel/<id>` for the settings sub-pages and remain used by the cockpit (snapshot freshness still surfaces in the headline when stale).

### Step 6 — States

| State | Trigger | Render |
|---|---|---|
| **Empty** | `action_count=0` AND all dots green AND snapshot fresh | Cockpit collapses to one-line confirmation: "Your knowledge system is healthy. Nothing needs your attention." Maintenance strip stays as quiet 5 ● dots. |
| **First-run** | Diary has zero entries | Onboarding copy: "Welcome to BCOS. Your first maintenance check runs tomorrow at 9 AM. Come back to see what it finds." Link to `docs/_bcos-framework/`. |
| **Loading** | Pre-data | Skeleton blocks matching cockpit shape (eyebrow + headline placeholder + 3-row attention placeholder + 5-dot placeholder). Fade out as data arrives. |
| **API error per-section** | A collector returns `{error: ...}` | Small error band: "We couldn't load this section. [Retry]" + "details" disclosure with the trace. Other sections keep working. |
| **Stale snapshot** | `>26h` (warn) / `>48h` (critical) / missing | Already handled by canary — verify the headline-level warning reads naturally. |
| **Partial errors** | 1 of 5 jobs errored in collect | Other 4 dots render normally. The 5th shows ⚠ glyph with hover="collect failed: <reason>". Whole cockpit doesn't go critical. |

### Step 7 — A11y + responsive + dark mode

**Color contrast.** Every text/background combo passes WCAG AA (4.5:1 body, 3:1 large) in both light AND dark mode.

**Screen reader.** Every interactive element gets `aria-label`. Job cards: "Documentation check, healthy, last run earlier this morning". Dots: "Documentation check, healthy". Mark-done: "Mark <title> done". No more `aria-label`-less icon buttons.

**Keyboard nav.** Tab order: skip-to-content → headline → attention items (each row + buttons inside) → dots (left/right arrow nav within strip) → settings link. Drawer traps focus when open.

**Focus indicators.** 2px outline in severity colour. Visible on every interactive element.

**Reduced motion.** All animations (drawer slide, mark-done fade, highlight flash, count badge update, preset save toast) wrapped in `@media (prefers-reduced-motion: reduce)` overrides.

**Mobile (<768px).** Drawer becomes full-screen bottom sheet. Dots become horizontal scroll strip. Attention items collapse to single line + tap to expand. Hit targets ≥44×44px (current preset chips at 22px need uppsizing).

**Dark mode.** `@media (prefers-color-scheme: dark)`. Dark grey base (not pure black). Re-derive `--color-severity-*-bg` for dark surfaces.

---

## 4. Discovery results

**Agents found**: none new for this plan (`explore` exists but not relevant).
**Skills found relevant**: `schedule-dispatcher`, `schedule-tune`, `schedule-migrate`, `daydream`, `ecosystem-manager`. The dashboard reads from artifacts these skills produce (digest, diary, schedule-config) but does not modify any skill in this plan.
**Lessons found**: none recorded (this work will produce some — see Phase 5 task P5_004).

---

## 5. Tasks by phase

### Phase 1 — Step 4: Per-job drawer

| ID | Task | Status |
|---|---|---|
| P1_001 | Add drawer primitives to dashboard.html (verify overlay+aside exist; framework already ships them per local-dashboard-builder template) | pending |
| P1_002 | Create `collect_job_detail(job_id)` in `single_repo.py` | pending |
| P1_003 | Add `GET /api/job/<id>` endpoint in server.py | pending |
| P1_004 | Implement `window.JOB_DRAWER` controller in dashboard.js (open/close/Esc/single-instance/focus-trap) | pending |
| P1_005 | Wire cockpit dot click → `JOB_DRAWER.open(job_id)`. Same for attention items with known `source_job` | pending |
| P1_006 | Drawer body markup (header / schedule / runs / what-it-does / today / recent-runs / change-frequency / technical-details) | pending |
| P1_007 | Drawer CSS (480px desktop, slide-in 250ms, overlay rgba(0,0,0,0.32), reduced-motion override) | pending |
| P1_008 | Remove standalone `jobs_panel` Panel from `run.py` panels() | pending |
| P1_009 | Browser-verify via `preview_eval`: dot clicks, Esc, click-outside, drawer crossfade, mark-done refreshes cockpit | pending |
| P1_010 | Commit: `feat(dashboard): Step 4 — per-job drawer` | pending |

### Phase 2 — Step 5: `/settings` route

| ID | Task | Status |
|---|---|---|
| P2_001 | Add `pushState`/`popstate` routing in dashboard.js | pending |
| P2_002 | Render mode switch in app init (path-aware) | pending |
| P2_003 | Server.py: SPA fallback for non-`/api/*`, non-`/static/*` paths | pending |
| P2_004 | Settings shell: top bar + side nav + content area | pending |
| P2_005 | `/settings/runs` page (wraps `renderRunHistory`) | pending |
| P2_006 | `/settings/files` page (wraps `renderFileHealth`) | pending |
| P2_007 | `/settings/schedules` page (bulk preset editor + auto-fix whitelist toggles + new `/api/schedule/whitelist` endpoint) | pending |
| P2_008 | `/settings/technical` page (canary verbose, MCP refresh copy-paste, raw config viewer, debug info) | pending |
| P2_009 | Add `⚙ Settings` link in cockpit header | pending |
| P2_010 | Remove standalone `snapshot_freshness`, `run_history`, `file_health` Panels from `run.py` panels() | pending |
| P2_011 | Browser-verify: routing works, back button works, refresh on `/settings/foo` loads correct sub-page | pending |
| P2_012 | Commit: `feat(dashboard): Step 5 — /settings route + remove standalone detail panels` | pending |

### Phase 3 — Step 6: States

| ID | Task | Status |
|---|---|---|
| P3_001 | Empty state: tight one-line confirmation when everything healthy | pending |
| P3_002 | First-run state: onboarding copy when diary empty | pending |
| P3_003 | Loading state: skeleton blocks matching final layout | pending |
| P3_004 | API error per-section: small error band + Retry + details disclosure | pending |
| P3_005 | Stale snapshot: verify headline-level warning reads naturally | pending |
| P3_006 | Partial errors: one job errored ≠ whole cockpit critical | pending |
| P3_007 | Browser-verify each state by mocking conditions | pending |
| P3_008 | Commit: `feat(dashboard): Step 6 — empty / first-run / loading / error / partial states` | pending |

### Phase 4 — Step 7: A11y + responsive + dark mode

| ID | Task | Status |
|---|---|---|
| P4_001 | Color contrast audit (WCAG AA) | pending |
| P4_002 | Screen-reader labels on every interactive element | pending |
| P4_003 | Keyboard navigation: Tab order + arrow keys for dot strip | pending |
| P4_004 | Focus indicators (2px severity-coloured outlines) | pending |
| P4_005 | Reduced motion: wrap every animation in `@media (prefers-reduced-motion: reduce)` | pending |
| P4_006 | Mobile <768px: bottom-sheet drawer, scroll dots, collapsed attention items, ≥44px hit targets | pending |
| P4_007 | Dark mode: `@media (prefers-color-scheme: dark)` overrides | pending |
| P4_008 | Manual screen-reader test (NVDA / Narrator) | pending |
| P4_009 | Commit: `feat(dashboard): Step 7 — accessibility, responsive, dark mode` | pending |

### Phase 5 (FIXED END) — Integration audit + ecosystem state + learnings

| ID | Task | Status |
|---|---|---|
| P5_001 | `python .claude/scripts/analyze_integration.py --staged` | pending |
| P5_002 | Update `docs/_bcos-framework/` references to new IA | pending |
| P5_003 | Update `bcos-dashboard/README.md` for cockpit-first IA | pending |
| P5_004 | Capture learnings via `ecosystem-manager` skill | pending |
| P5_005 | Final commit: `docs(dashboard): update README + framework refs + capture learnings` | pending |

---

## 6. Open questions

1. **Drawer for attention items** — should clicking an attention item with a known `source_job` open that job's drawer, or a separate "finding detail" drawer? **Recommendation**: source-job drawer (keeps drawer count low; jobs ARE the natural unit).
2. **Settings sub-pages** — route-per-page (current proposal) or single URL with hash state? Route-per-page = better browser-back behavior, more routing code. Hash-state = simpler. **Open**.
3. **First-run detection** — the proposal says "no diary AND no schedule-config", but a brand-new BCOS install has schedule-config (ships with the framework). Better detector: **diary has zero entries**. Adjust accordingly.
4. **Mobile bottom-sheet drawer height** — full-screen with close handle? 80vh? **Recommendation**: 90vh with handle (allows peek at the cockpit behind).

## 7. Follow-ups (not in this plan)

- **Step 8** — `/settings/maintenance-history` heatmap calendar of last 90 days of diary
- **Step 9** — file-level inspection drawer (click a file in file-health → drawer with full frontmatter + "open in editor")
- **Independent** — `/settings/about` page (version, BCOS framework docs link, license)

---

## 8. Resumption guide for a fresh session

When you open a new session and want to continue this work, the prompt to give yourself is:

> Resume the BCOS Dashboard rebuild from `business-context-os-dev/.claude/quality/sessions/20260424_203941_bcos-dashboard-steps-4-7/`. The plan-manifest and implementation-plan there have everything you need. Start with Phase 1 task `P1_001`. The dashboard runs at http://127.0.0.1:8092 (preview server name `bcos-dashboard` in `theo-portfolio/.claude/launch.json`); restart it with preview_stop + preview_start to pick up Python changes.

The plan is self-contained — you should not need to re-read this conversation.

## 9. Next actions

Answer the Gate 2 question: **Approve** / **Modify** / **Cancel**.

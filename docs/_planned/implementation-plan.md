# Implementation Plan — Context Atlas Visualization

| | |
|---|---|
| **Session ID** | `20260429_151206_context-atlas-viz` |
| **Scenario** | AGENTING |
| **Status** | `awaiting_approval` |
| **Created** | 2026-04-29T15:12:06Z |

---

## Discovery Results

- **Agents found:** `explore` (1)
- **Skills found:** 13 — none overlap (no existing visualization tooling)
- **Lessons:** none captured yet (`lessons-starter.json` empty)
- **Ecosystem health:** HEALTHY (per `state.json` 2026-04-23)
- **Reusable components:**
  - [file_health.py](../../../scripts/bcos-dashboard/file_health.py) — frontmatter parser + doc iterator → extract to shared
  - [single_repo.py](../../../scripts/bcos-dashboard/single_repo.py) — `REPO_ROOT` detection + Panel/collector pattern
  - [bcos_sync.py](../../../scripts/bcos-dashboard/bcos_sync.py) — upstream-tip cache → drift overlay data
  - [server.py](../../../scripts/bcos-dashboard/server.py) — HTTP server + TTL caching framework
  - [labels.py](../../../scripts/bcos-dashboard/labels.py) — id→human-label translations

---

## Problem Statement

The BCOS dashboard currently surfaces dispatcher status, actions, and file-health findings — but the *architecture* of the user's context (who owns what, how docs relate, where stuff is in the lifecycle, what's drifting from upstream) is invisible. A generic repo treemap would miss the point: BCOS's value is in YAML frontmatter semantics, not file structure. The user needs a view that makes ownership, relationships, lifecycle, freshness, CLEAR compliance, and upstream drift legible at a glance — without bloating the cockpit and without adding a JS build step to a Python+vanilla-JS dashboard.

## Proposed Solution

A new top-level page `/atlas` with three lens-tabs over a single shared frontmatter ingestion pass:

1. **Ownership Map** — HTML+CSS squarified treemap. Domains as regions, docs as tiles sized by content, colored by freshness, with duplication badges where `EXCLUSIVELY_OWNS` overlaps.
2. **Lifecycle Flow** — CSS-Grid Kanban: `_inbox → _planned → docs/ → _archive`, with age-stuck flags and one-click promote/archive.
3. **Relationship Graph** — Mermaid graph rendered client-side, edges only from frontmatter `relationships` (no implicit text-similarity noise). Orphans surfaced separately.

Plus four overlays that ride on the same atlas data:
- **CLEAR compliance ring** per domain (CSS conic-gradient donut)
- **Upstream-drift coloring** on framework files (sourced from `bcos_sync.py`'s existing cache — no new fetches)
- **Freshness-vs-volatility** coloring (age relative to per-domain expected cadence)
- **Skill/agent impact halo** on hover (parsed from skill frontmatter)

**Static-first.** HTML+CSS treemap, Mermaid (zero new deps), CSS-Grid Kanban. Escalate to D3 only if static hits its limit. Cockpit gets a small teaser tile linking to `/atlas` — Atlas is a primary view, not a setting.

**Shared ingestion.** A new `atlas_ingest.py` extracts `_iter_docs` + `_parse_frontmatter` from `file_health.py` and extends them to produce a single atlas dict (docs, domains, lifecycle buckets, edges). `file_health.py` becomes a consumer of this shared module — no duplicate scans.

---

## Key Design Decisions

| Decision | Choice | Rejected alternatives |
|---|---|---|
| Ingestion | One shared `atlas_ingest.py`; `file_health.py` consumes it | Two parallel scanners; cron-generated `atlas.json` |
| Caching | TTL panel cache (300-600s) inside existing collector framework | Separate cron job; on-demand recompute every request |
| Rendering | HTML+CSS treemap + Mermaid + CSS-Grid Kanban | D3/Cytoscape; server-side SVG via matplotlib |
| IA | New `/atlas` top-level page + cockpit teaser | Settings sub-page; embed in cockpit |
| Edges | Only frontmatter-declared `relationships` | Implicit text-similarity edges (too noisy, untrustworthy) |
| Drift data | Reuse `bcos_sync.py` upstream cache | New fetch per Atlas refresh |

---

## Open Decisions (resolved during execution)

| ID | Question | Decided in | Approach |
|---|---|---|---|
| OD-1 | Canonical "domain" frontmatter key (`cluster`, `DOMAIN`, `EXCLUSIVELY_OWNS`)? | P1_002 | Inspect 5-10 real docs; default `cluster` (it's REQUIRED), folder-fallback otherwise |
| OD-2 | YAML shape of `relationships` field? | P4_001 | Grep real docs; lock parser to existing shape; document in module |
| OD-3 | Per-domain volatility/cadence model? | P5_002 | Default 90 days; opt-in override via `.claude/quality/atlas-domains.json` |
| OD-4 | Multi-repo umbrella aggregation | OUT OF SCOPE for v1 | Flag as follow-up |

---

## Tasks by Phase

### Phase 1 — Shared Ingestion Module

| ID | Task | Status |
|---|---|---|
| P1_001 | Create `atlas_ingest.py` with `_iter_docs`/`_parse_frontmatter` extracted from `file_health.py` (preserve behavior) | pending |
| P1_002 | Inspect real docs to confirm domain key; codify into `atlas_ingest.domain_of(doc)` | pending |
| P1_003 | Add `atlas_ingest.build_atlas()` returning `{docs, domains, lifecycle_buckets, relationships, generated_at}` | pending |
| P1_004 | Refactor `file_health.py` to import from `atlas_ingest` (no behavior change) | pending |
| P1_005 | Add `/api/atlas` debug endpoint serving raw atlas dict | pending |

### Phase 2 — Ownership Map

| ID | Task | Status |
|---|---|---|
| P2_001 | Implement squarified treemap in `atlas_layout.py` (pure stdlib) | pending |
| P2_002 | Add `collect_atlas_ownership()` collector — content-length sizing, freshness coloring | pending |
| P2_003 | Detect `EXCLUSIVELY_OWNS` overlaps; surface as duplication badges | pending |
| P2_004 | Add `/atlas` page shell + lens-tab nav (Ownership default) | pending |
| P2_005 | Render treemap client-side (HTML+CSS tiles, click → file-detail drawer) | pending |
| P2_006 | Style treemap (regions, freshness ramp, duplication badge) | pending |
| P2_007 | Add cockpit teaser tile linking to `/atlas` | pending |

### Phase 3 — Lifecycle Flow

| ID | Task | Status |
|---|---|---|
| P3_001 | Add `collect_atlas_lifecycle()` — bucket folders, age-stuck flags (>14d in `_inbox`) | pending |
| P3_002 | Render CSS-Grid Kanban (4 cols, cards sorted by age) | pending |
| P3_003 | Add `POST /api/atlas/promote` and `POST /api/atlas/archive` endpoints | pending |
| P3_004 | Wire Kanban action buttons (optimistic UI + cache invalidation) | pending |

### Phase 4 — Relationship Graph

| ID | Task | Status |
|---|---|---|
| P4_001 | Grep real docs for `relationships:`; lock YAML shape; document in `atlas_ingest` | pending |
| P4_002 | Extend `atlas_ingest` to parse relationships into `{from, to, kind}` edges | pending |
| P4_003 | Add `collect_atlas_relationships()` — emit Mermaid graph source | pending |
| P4_004 | Render Mermaid client-side (CDN-pinned or vendored copy) | pending |
| P4_005 | Surface orphan docs (no edges) in a side panel | pending |

### Phase 5 — Compliance + Drift Overlays

| ID | Task | Status |
|---|---|---|
| P5_001 | Define CLEAR-dimension extraction (align with `context-audit` logic) | pending |
| P5_002 | Add `.claude/quality/atlas-domains.json` registry (`cadence_days` per domain) | pending |
| P5_003 | Render CLEAR compliance ring (CSS conic-gradient) per domain | pending |
| P5_004 | Color framework files by upstream-drift state from `bcos_sync` cache | pending |
| P5_005 | Switch freshness coloring to volatility-relative | pending |

### Phase 6 — Skill / Agent Impact Halo

| ID | Task | Status |
|---|---|---|
| P6_001 | Parse `.claude/skills/*/SKILL.md` frontmatter for read/write path patterns | pending |
| P6_002 | Build `doc → skills` index in atlas output | pending |
| P6_003 | Render hover-halo on doc tiles (CSS-only popover) | pending |

### Phase 7 — FIXED END (mandatory)

| ID | Task | Status |
|---|---|---|
| P7_001 | Run `python .claude/scripts/analyze_integration.py --staged`; resolve stale references | pending |
| P7_002 | Update `.claude/quality/ecosystem/state.json` with new modules + surface area | pending |
| P7_003 | Capture learnings via `ecosystem-manager` skill | pending |
| P7_004 | Update `.claude/scripts/bcos-dashboard/README.md` — Atlas section + roadmap | pending |
| P7_005 | Run `doc-lint` on touched files; verify CLAUDE.md cross-refs | pending |

---

## Files

### New
- `.claude/scripts/bcos-dashboard/atlas_ingest.py`
- `.claude/scripts/bcos-dashboard/atlas_layout.py`
- `.claude/scripts/bcos-dashboard/atlas_collectors.py`
- `.claude/quality/atlas-domains.json`

### Modified
- `.claude/scripts/bcos-dashboard/file_health.py` (refactor to import from `atlas_ingest`)
- `.claude/scripts/bcos-dashboard/run.py` (register atlas panels + routes)
- `.claude/scripts/bcos-dashboard/dashboard.html` (add `/atlas` page shell)
- `.claude/scripts/bcos-dashboard/dashboard.js` (atlas renderers + lens-tab routing)
- `.claude/scripts/bcos-dashboard/dashboard.css` (treemap + Kanban + ring styles)
- `.claude/scripts/bcos-dashboard/README.md`
- `.claude/quality/ecosystem/state.json`

### Untouched
- `docs/**` — read-only data source; no docs modified
- Other skills — no skill frontmatter changes

---

## Risks

- **Frontmatter shape drift.** Open Decisions OD-1 / OD-2 / OD-3 land in execution; if real docs don't have a stable `relationships` field yet, the relationships lens degrades to "orphans-only" until the convention is locked in CLAUDE.md.
- **Multi-repo aggregation deferred.** v1 is single-repo only. Umbrella portfolio mode would need an aggregation pass; flagged as follow-up.
- **Mermaid CDN.** Phase 4 default uses CDN-pinned Mermaid — first render needs network. Vendor a minified copy if offline-only is required (sub-task).
- **CLEAR extraction overlap with `context-audit`.** Phase 5 should ideally reuse `context-audit`'s logic rather than duplicate. If extraction is non-trivial, P5 may slip into a follow-up that wires Atlas to consume `context-audit` output instead of recomputing.

---

## Artifacts

- `plan-manifest.json` — `.claude/quality/sessions/20260429_151206_context-atlas-viz/plan-manifest.json`
- `implementation-plan.md` — this file
- `planning-manifest.json` — `.claude/quality/sessions/20260429_151206_context-atlas-viz/planning-manifest.json`

---

## Next Actions

1. **Approve** — start implementation with Phase 1
2. **Modify** — describe what to change (scope, ordering, rendering choice, IA, etc.)
3. **Cancel** — archive session, no further work

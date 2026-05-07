---
sessionId: "20260505_112828_lifecycle-sweep"
scenarioType: agenting
scenarioSecondary: documentation
status: awaiting_approval
revision: 2
created: "2026-05-05"
last-updated: "2026-05-05"
targetRepo: business-context-os-dev
acceptanceInstall: theo-portfolio
---

# Lifecycle-Sweep — Implementation Plan (v2)

> **v2 revision** after verifying autonomy-ux-self-learning is **59/79 complete** (P0-P7 shipped; P8 conditional + P9 fixed-end pending). The infrastructure lifecycle-sweep should plug into is **live and importable**, not "to-be-built". Strategy shifts from "reserve namespace + ship parallel" to "extend live registries inline". Target repo is **business-context-os-dev** (framework). theo-portfolio is the first acceptance-test install via `update.py`.

## Header

- **Session ID:** `20260505_112828_lifecycle-sweep`
- **Target repo:** `business-context-os-dev` (framework)
- **Plan home (canonical):** `theo-portfolio/.claude/quality/sessions/20260505_112828_lifecycle-sweep/`
- **Plan home (mirror, after Gate 2):** `business-context-os-dev/docs/_planned/lifecycle-sweep/`
- **Acceptance install:** `theo-portfolio` (P7)
- **Scenario:** AGENTING (primary) + DOCUMENTATION (secondary)
- **Status:** Awaiting approval (Gate 2)
- **Soft-dep:** `business-context-os-dev/docs/_planned/autonomy-ux-self-learning/` — extend live infra; defer silent-tier promotion until autonomy-ux P8 lands

## Discovery Results

### Autonomy-UX-Self-Learning completion verified

| Phase | Status | What's importable |
|---|---|---|
| P0 Foundation | done | typed-events.md, fixture corpus |
| P1 Typed events + labels | done | `finding_type` enum live; digest_sidecar.py with `parse_sidecar`/`write_sidecar`; SCHEMA_VERSION="1.0.0" |
| P2 Dashboard cards + block_on_red | done | green/amber/red view; cockpit composition; cache-invalidation tests |
| P3 Headless actions | done | `headless-actions.md` with 9 actions; `/api/actions/headless` endpoint |
| P4 resolutions.jsonl | done | 14-field schema; `record_resolution.py` shipped; resolutions.jsonl populated |
| P5 Self-learning v0.1 | done | `promote_resolutions.py` preselect tier; `learned-rules.json` derived |
| P6 Auto-fix auditor v0.1 | done | reversal detection |
| P7 Self-learning v0.2 + auditor v0.2 | done | auto-apply tier with undo; checks 2-3; /settings/learning panel |
| P8 Silent tier (conditional) | pending | requires 6+ weeks auditor-clean — does not block lifecycle-sweep |
| P9 FIXED END | pending | their plan's lint/audit/state/learnings — does not block |

### Skills + capabilities

| | |
|---|---|
| Skills | 19 |
| Agents | 2 (`explore`, `wiki-fetch`) |
| Skills affected | `schedule-dispatcher` (new job), `context-ingest` (lifecycle prompt), `bcos-wiki` (called by sweep), `context-audit` (cross-check) |
| New skills | None — composes existing |
| Scripts extended (no edits) | `digest_sidecar.py` (consumed), `record_resolution.py` (called), `promote_resolutions.py` (auto-picks pairs) |

### Lessons (3 inferred — `find_lessons.py --tags` returned 0)

- **L-LIVE-INFRA-EXTEND**: when soft-dep infra is shipped, extend it directly; concrete wire-in beats parallel-ship
- **L-ZONE-CLASSIFIER-AUTHORITY**: zone is path-derived; never reimplement; import `_zone_for()`
- **L-ROUTING-SKILL-BOUNDARIES**: sweep is classifier+dispatcher only — calls `/wiki promote`, `context-ingest` Path 5; never replicates move logic
- **L-FRAMEWORK-VS-INSTALL**: framework features ship in business-context-os-dev; installs receive via `update.py`; acceptance test runs in real install
- **L-DERIVED-ARTIFACT-INVARIANT** (from autonomy-ux): byte-stable regeneration required for `learned-rules.json`

## Problem Statement

End-user docs accumulate without exit triggers. Today's `index-health` job detects orphans by graph topology (no inbound xrefs) — that's a *symptom*, not a classification. It can't distinguish a shipped audit from a live SOP. We just hand-archived 9 dev-audit docs; an end user running their business will accumulate similar piles (sent proposals, dated analyses, meeting notes, abandoned drafts) with no auto-detection or routing.

**Five gaps:**
1. Frontmatter doesn't carry exit triggers — every doc looks active forever.
2. No content-aware classifier — body markers ("SENT:", "DECISION:") are ignored.
3. No reality cross-check — body claims and repo state are never compared.
4. No declarative routing rules — each move-skill hardcodes its own logic.
5. lifecycle-sweep findings have no native bridge to the dashboard cards / self-learning ladder shipped by autonomy-ux.

## Proposed Solution

Three deliverables, shipped in **business-context-os-dev** as a framework feature:

### 1. `lifecycle:` frontmatter field (optional)

```yaml
---
name: "Acme Proposal v3"
type: process
cluster: outbound
version: "1.0.0"
status: active
created: "2026-05-01"
last-updated: "2026-05-01"
lifecycle:
  archive_when: "proposal-sent"        # body marker SENT: triggers
  fold_into: "docs/operations/sops/onboarding.md"
  expires_after: 30d                    # date-based fallback
  route_to_wiki_after_days: 60          # for research docs
---
```

Trigger types are **deterministic** (date-based) or **marker-based** (body contains "SENT:", a sibling file exists, etc.). All optional. Spec lands in `document-standards.md`.

### 2. `.claude/quality/lifecycle-routing.yml`

Declarative rules table covering the 9 abstract doc patterns (general, no engagement-repo assumption):

| Pattern | Destination zone | Trigger combo |
|---|---|---|
| `outbound-sent` | `archive` (`_archive/outbound/`) | body has "SENT:" OR sibling sent-version exists |
| `outbound-abandoned` | `archive` (`_archive/abandoned/`) | `expires_after` hit, no SENT marker |
| `decision` | `archive` (`_archive/decisions/`) | body has "DECISION:" OR "RESOLVED:" |
| `meeting-notes` | `archive` (folded) OR stay (canonical) | reality: target doc references the date |
| `research-dump` | `wiki` (promote to source-summary) | external URL detected; non-trivial age |
| `snapshot` | `archive` (`_archive/snapshots/`) | next-period snapshot exists |
| `process-experiment` | `archive` (rejected) OR `fold-into-SOP` (adopted) | body markers + sibling SOP |
| `idea-dead` | `archive` (`_archive/abandoned/`) | `_planned/` doc with no edit > 90d |
| `audit-of-shipped` | `archive` | audited artifact has shipped (git log + skill registry check) |

Destinations reference **zone IDs** from `_context-zones.yml.tmpl`, not raw paths. Drift test enforces consistency.

### 3. `lifecycle_sweep.py` (composes existing skills)

```
lifecycle_sweep.py
├── frontmatter trigger evaluator (deterministic)
├── body-signal scanner (regex SENT|OUTCOME|DECISION|RESOLVED|PUBLISHED|ABANDONED + staleness)
├── reality cross-check (git log, sibling-doc existence, _wiki coverage, _collections manifest)
├── classifier → route_decision = {auto|ambiguous|leave_alone, dest, reason, confidence}
├── auto-route executor → calls git mv | /wiki promote | context-ingest Path 5 | fold-into
├── digest_sidecar.write_sidecar() ← imports live API
└── record_resolution() ← imports live API; pairs flow into learned-rules.json
```

**Surface-only mode** (default `auto_fix=false`) for first 2 weeks. After 0 false-positives confirmed, flip to auto-route. `promote_resolutions.py` then automatically promotes consistent `(lifecycle-*, lifecycle-route-*)` pairs into preselect → auto-apply tiers — **no new ladder code**.

### Wire-in to live autonomy-ux infrastructure (Phase 3.5)

**4 new finding_types** added to `typed-events.md` enum:

| ID | Meaning |
|---|---|
| `lifecycle-trigger-fired` | frontmatter trigger evaluated true; ready-to-route |
| `lifecycle-body-marker-confirmed` | body marker (SENT/DECISION/etc.) + reality cross-check passed |
| `lifecycle-route-ambiguous` | signals conflict — needs user decision |
| `lifecycle-orphan-active` | active-zone doc with 0 inbound + no lifecycle field + age threshold |

**4 new headless actions** registered in `headless-actions.md`:

| ID | Type | Reversible-by |
|---|---|---|
| `lifecycle-route-archive` | move | `git mv` back to original path |
| `lifecycle-route-wiki` | move | `/wiki archive <slug>` then restore from git |
| `lifecycle-route-collection` | move | `git mv` from `_collections/` back; remove manifest row |
| `lifecycle-fold-into` | metadata-edit + move | `git revert` of the fold commit |

**Schema-version stays `1.0.0`** — strictly additive change to enum + actions.

## Phases & Tasks

### Phase 0 — Discovery (DONE in planner)

| ID | Task | Status |
|---|---|---|
| P0_001 | Run agent + skill discovery | done |
| P0_002 | Verify autonomy-ux completion state | done — 59/79, infra live |
| P0_003 | Read framework authority docs | done |
| P0_004 | Define wire-in strategy | done — extend, not reserve |

### Phase 1 — `lifecycle:` frontmatter spec (DOC, in bcos-dev)

| ID | Task | Output |
|---|---|---|
| P1_001 | Define field spec + trigger types | `bcos-dev/docs/_bcos-framework/methodology/document-standards.md` |
| P1_002 | Document trigger schema with 5 worked examples | same file |
| P1_003 | Update `context-ingest` to prompt for lifecycle at capture | `bcos-dev/.claude/skills/context-ingest/SKILL.md` |
| P1_004 | Update frontmatter validation hook (warn-only on malformed) | hook |

### Phase 2 — Routing config + schema doc (AGENT, in bcos-dev)

| ID | Task | Output |
|---|---|---|
| P2_001 | Design routing config schema | spec |
| P2_002 | Create `lifecycle-routing.yml` template with 9 default rules | `bcos-dev/.claude/quality/lifecycle-routing.yml` |
| P2_003 | Cross-link with `_context-zones.yml.tmpl` + drift test | config edit + test |
| P2_004 | Schema doc | `bcos-dev/docs/_bcos-framework/architecture/lifecycle-routing.md` |

### Phase 3 — Sweep script + classifier (AGENT, in bcos-dev)

| ID | Task | Output |
|---|---|---|
| P3_001 | Failing wiring test: imports `_zone_for` + `digest_sidecar` + `record_resolution` | `test_lifecycle_sweep.py` |
| P3_002 | Frontmatter trigger evaluator | module |
| P3_003 | Body-signal scanner | module |
| P3_004 | Reality cross-check | module |
| P3_005 | Classifier composing all 4 inputs | module |
| P3_006 | Auto-route executor — calls existing skills, never replicates | module |
| P3_007 | Main entry: walks zones, classifies, routes | `bcos-dev/.claude/scripts/lifecycle_sweep.py` |
| P3_008 | Smoke-test against bcos-dev's own docs/ | test |

### Phase 3.5 — Wire into live autonomy-ux infrastructure (AGENT, in bcos-dev)

| ID | Task | Output |
|---|---|---|
| P3.5_001 | Extend `typed-events.md` enum with 4 new finding_types | `bcos-dev/docs/_bcos-framework/architecture/typed-events.md` |
| P3.5_002 | Define `finding_attrs` shape per new finding_type | same file |
| P3.5_003 | Register 4 new headless-actions (each declares reversible-by, telemetry-event) | `bcos-dev/.claude/skills/schedule-dispatcher/references/headless-actions.md` |
| P3.5_004 | Wire `lifecycle_sweep.py` to `digest_sidecar` (write_sidecar) | code |
| P3.5_005 | Wire auto-route executor to `record_resolution` (14-field row per route) | code |
| P3.5_006 | Verify `promote_resolutions.py` auto-picks lifecycle pairs (no code change) | wiring test |
| P3.5_007 | End-to-end wiring test: emit → record → promote → byte-stable regen | test |

### Phase 4 — Dispatcher integration (AGENT, in bcos-dev)

| ID | Task | Output |
|---|---|---|
| P4_001 | Create `references/job-lifecycle-sweep.md` | reference doc |
| P4_002 | Register in `schedule-config.json` template (Friday weekly, auto_fix=false) | template edit |
| P4_003 | Update `auto-fix-whitelist.md` — declare `lifecycle-route-*` IDs gated behind burn-in | reference edit |
| P4_004 | Wiring test: dispatcher reads job ref, verdict + sidecar shapes conform | test |

### Phase 5 — Authority-doc updates (DOC, in bcos-dev framework)

| ID | Task | Output |
|---|---|---|
| P5_001 | Add lifecycle-sweep row to `maintenance-lifecycle.md` job table | update |
| P5_002 | Add Path 6 (outbound from active) to `content-routing.md` | update |
| P5_003 | Update `context-zones.md` — exit-triggers for active zone | update |
| P5_004 | Bidirectional cross-reference check across 5 framework docs | doc-lint |

### Phase 6 — bcos-dev FIXED END (mandatory)

| ID | Task | Output |
|---|---|---|
| P6_001 | YAML/JSON lint on lifecycle-routing.yml + schedule-config.json + resolutions.jsonl | green |
| P6_002 | Markdown lint on all updated/new framework docs | green |
| P6_003 | Integration audit (`analyze_integration.py --staged`) — check `install.sh` deploys lifecycle-routing.yml | audit output |
| P6_004 | Update `bcos-dev/.claude/quality/ecosystem/state.json` (jobs list) | state.json |
| P6_005 | Capture learnings via `ecosystem-manager` | lessons.json |
| P6_006 | Cross-plan note: append to autonomy-ux session folder citing the 4 finding_types + 4 actions added | `bcos-dev/docs/_planned/autonomy-ux-self-learning/cross-plan-lifecycle-sweep-additions.md` |

### Phase 7 — theo-portfolio acceptance test (NEW)

| ID | Task | Output |
|---|---|---|
| P7_001 | Run `python .claude/scripts/update.py` from theo-portfolio (pulls bcos-dev framework changes) | console output |
| P7_002 | Verify deploy: `lifecycle-routing.yml`, `lifecycle_sweep.py`, `job-lifecycle-sweep.md`, `schedule-config.json` updated, `typed-events.md` + `headless-actions.md` updated | manual check |
| P7_003 | Smoke-test: run sweep manually on theo-portfolio (surface-only). Expected: empty ambiguous list (we just hand-archived); no false-positives on `current-state.md`, `strategic-thesis.md`, `repo-ownership-map.md`, `table-of-context.md`, `project-map.md` | smoke output |
| P7_004 | Manual dispatcher run for Friday slot; verify digest section + sidecar emission + diary append | dispatch run |
| P7_005 | After 2-week burn-in with 0 false-positives: flip burn-in flag → enable auto-routing | config edit (delayed 14d) |

## Artifacts

- Planning manifest: [planning-manifest.json](.claude/quality/sessions/20260505_112828_lifecycle-sweep/planning-manifest.json)
- Plan manifest: [plan-manifest.json](.claude/quality/sessions/20260505_112828_lifecycle-sweep/plan-manifest.json)
- This file: [implementation-plan.md](.claude/quality/sessions/20260505_112828_lifecycle-sweep/implementation-plan.md)
- After Gate 2 approval, copy plan + implementation-plan to `bcos-dev/docs/_planned/lifecycle-sweep/` per bcos-dev convention.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Schema-version drift if autonomy-ux bumps `digest_sidecar.SCHEMA_VERSION` after we ship | All wire-ins use `SCHEMA_VERSION` constant from import, not literal; bumps are caught by the existing tolerance set in digest_sidecar |
| `lifecycle-route-ambiguous` ↔ amber-card threshold drift | P3.5_007 wiring test asserts `lifecycle-route-ambiguous` produces `verdict="amber"` in sidecar |
| Sweep auto-routes too aggressively, false-positives on canonical docs | 2-week surface-only burn-in (default `auto_fix=false`); P3_008 + P7_003 smoke tests must report 0 false-positives before flipping |
| Routing rules diverge from `_context-zones.yml.tmpl` | P2_003 cross-link + drift test: destinations must reference zone IDs from registry |
| Sweep duplicates `bcos-wiki promote` / `context-ingest` Path 5 | P3_006 invokes them; never replicates. Code review checkpoint. |
| `record_resolution` schema mismatch (we miss a field) | Import `record_resolution.RESOLUTION_FIELDS` constant, fail loudly on missing |
| theo-portfolio update.py misses lifecycle-routing.yml | P7_002 explicit deploy verification list; if missing, fix `install.sh` in P6_003 audit |

## Next Actions

Awaiting Gate 2 approval. Options:
- **Approve** → mark approved, begin execution at P1_001 in bcos-dev
- **Modify** → return with feedback
- **Cancel** → archive session

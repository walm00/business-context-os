# Implementation Plan: Galaxy Orbits Upgrade

**Session ID:** `20260501_104136_galaxy-orbits-upgrade`
**Scenario:** AGENTING (touches `.claude/scripts/bcos-galaxy/` only)
**Status:** approved (Gate 1: Proceed · Gate 2: Approve)
**Created:** 2026-05-01

---

## Problem Statement

The Context Galaxy (`.claude/scripts/bcos-galaxy/`) is a working force-graph-with-halos prototype but not yet a navigable space scene. Three structural issues block further work, and five visual/interaction upgrades are needed to reach the goal: an instructable galaxy where the user can navigate through repo documents and context with a real space environment (sun, stars, orbits).

**Fixes blocking progress:**

1. **Library brittleness** — `3d-force-graph@1.74.0` pinned, with a custom render-loop hack bypassing the broken animation cycle. Documented in [galaxy.js](../../../scripts/bcos-galaxy/galaxy.js) lines 12–34, 272–283, 901+. Adding orbits and custom motion will fight the wrapper at every step.
2. **Commit hygiene** — last commit `912a8ab "dfghdgf"` bundles 13 files across two unrelated work streams (galaxy scaffolding + dashboard atlas refactors). Must be split before further commits.
3. **Static one-shot layout** — d3 forces run only at construction. Ambient-toggle and repo-swap currently force a full graph rebuild.

**Upgrades to reach the goal:**

4. **Starfield + skybox** — solid `#03030a` background today; need a `THREE.Points` particle field and optional nebula sprite.
5. **Real orbits** — domain clusters orbit the sun on tilted ellipses; siblings orbit their domain anchor; faint orbit rings drawn via `RingGeometry`. **Headline feature.**
6. **Document navigation** — clicking opens a metadata drawer today. Need camera fly-in, full-pane rendered-markdown preview, next/prev neighbor keys, breadcrumb of visited stars.
7. **Wiki / Collections distinct nodes** — flagged out-of-scope in [wiki-and-collections-zones-rollout.md:67](../../../../docs/_planned/wiki-and-collections-zones-rollout.md). Pull in now while node types are being touched.
8. **Polish** — keyboard nav, touch/pinch, minimap, ambient particles for archived docs.

---

## Discovery Results

| Source | Finding |
|---|---|
| `find_agents.sh` | 1 agent: `explore` — not relevant |
| `find_skills.sh` | 13 skills — none overlap; `ecosystem-manager` invoked in FIXED END |
| `find_lessons.py` | 0 matching lessons (galaxy/dashboard/visualization/agenting tags) |
| Ecosystem overlap | **None** — galaxy is a self-contained internal web app, gitignored from public release ([4f47675](https://github.com/) — local) |
| Working tree state | 3 unrelated WIP files (`update.py`, `job-index-health.md`, `refresh_ecosystem_state.py`) — must be set aside before Phase 0 |

---

## Proposed Solution

Sequenced into 9 phases. Phases 0–2 are structural prerequisites; 3–7 stack the visual/interaction features in dependency order; Phase 8 is the mandatory AGENTING FIXED END.

**Sequencing rationale:**
- **Phase 0 first** — can't pile orbits on a "dfghdgf" commit
- **Phase 1 before 2** — library decision changes how layout is implemented
- **Phase 2 before 4** — orbits need a re-runnable layout pass
- **Phase 3 standalone** — atmosphere is independent; cheap morale win
- **Phase 4 before 5** — node types render on top of orbital positions
- **Phase 5 before 6** — node types should be stable before nav UX is built around them
- **Phase 7 last** — nice-to-haves layered on a working scene

**Recommended library decision (Phase 1):** migrate to raw `three.js` + `d3-force`. The custom render-loop hack already proves the wrapper isn't earning its keep, and Phases 2-7 all benefit from direct THREE access. Final decision happens after spike branches in P1_001 and P1_002.

---

## Tasks by Phase

### Phase 0: Commit Hygiene

| ID | Task | Status |
|---|---|---|
| P0_001 | Stash unrelated WIP (`update.py`, `job-index-health.md`, `refresh_ecosystem_state.py`) | pending |
| P0_002 | Soft-reset 912a8ab; recommit dashboard atlas refactors as separate commit | pending |
| P0_003 | Recommit galaxy scaffolding as second commit with proper message | pending |
| P0_004 | Verify `.gitignore` still excludes `bcos-galaxy` from public release | pending |
| P0_005 | Restore stashed WIP | pending |

### Phase 1: Library Decision

| ID | Task | Status |
|---|---|---|
| P1_001 | Spike branch A: upgrade `3d-force-graph` to latest; test if 1.79+ tickFrame race is fixed | pending |
| P1_002 | Spike branch B: replace with raw three.js + d3-force; validate atlas data still renders | completed - raw Three.js renderer is default; force fallback remains under `?renderer=force` |
| P1_003 | Decision: pick library; document trade-off in `galaxy.js` header comment | completed - raw Three.js selected as migration path |
| P1_004 | If migrating: remove custom render-loop workaround; consolidate THREE imports | pending |
| P1_005 | Verify all current features still work (sun corona, halos, modes, drawer, HUD) | pending |
| P1_006 | Delete `diag.html` / `diag2.html` (no longer needed once main scene is stable) | pending |

### Phase 2: Layout State Machine

| ID | Task | Status |
|---|---|---|
| P2_001 | Extract layout pass into pure function: `atlas → positions[]` | pending |
| P2_002 | Wire ambient toggle to re-run layout without full graph rebuild | pending |
| P2_003 | Wire repo swap to re-run layout (data swap only, scene persists) | pending |
| P2_004 | Smooth-transition camera + node positions on layout change | pending |

### Phase 3: Starfield + Skybox

| ID | Task | Status |
|---|---|---|
| P3_001 | Generate `THREE.Points` starfield (~3000 particles, log-distance falloff) | completed - deterministic 2600-point starfield |
| P3_002 | Add subtle nebula sprite (radial gradient texture, additive blend) | completed - additive radial-gradient nebula sprites |
| P3_003 | Replace solid `#03030a` `backgroundColor` with skybox gradient | completed - textured Three.js sky dome + CSS fallback gradient |
| P3_004 | Tune density / brightness so foreground stars stay readable | completed - browser screenshot verified readable foreground |

### Phase 4: Real Orbits (Headline)

| ID | Task | Status |
|---|---|---|
| P4_001 | Compute orbit parameters per domain: radius (degree-weighted), tilt, phase offset | completed - deterministic radius/tilt/phase per cluster |
| P4_002 | Position domain anchors on orbit around sun (replace force-cluster centroids) | completed - domain planets orbit the sun |
| P4_003 | Position siblings on inner orbits around their domain anchor | completed - documents orbit domain planets as moons/stars |
| P4_004 | Draw faint orbit rings (`THREE.RingGeometry`, dim opacity, additive blend) | completed - solar + local orbit rings drawn as additive line loops |
| P4_008 | Add second-level folder/engagement gravity wells for repos with meaningful folder structure | completed - engagement/folder mini-planets computed and docs orbit them when present |
| P4_005 | Animate orbital rotation (slow; respect `prefers-reduced-motion`) | pending |
| P4_006 | Remove dead d3 cluster-force code; update `layoutCluster()` / `atlasToGraphData()` | pending |
| P4_007 | Verify atlas/lifecycle/freshness modes still work with orbital positions | completed - atlas/freshness orbital + lifecycle orbital bands verified |

### Phase 5: Wiki / Collections Distinct Node Styles

| ID | Task | Status |
|---|---|---|
| P5_001 | Detect node type from path (`_wiki/`, `_collections/`, active) in `atlasToGraphData` | completed - structuralKind detection added |
| P5_002 | Wiki nodes: distinct geometry (e.g. octahedron) + cooler tone | completed - octahedron/cool tone code path added; awaits live `_wiki` docs for visual exercise |
| P5_003 | Collections nodes: distinct geometry (e.g. cube/box) + warmer tone | completed - box/warm tone code path added; awaits live `_collections` docs for visual exercise |
| P5_004 | Update HUD legend to show new node types | completed - structural legend entries render when present |
| P5_005 | Mark `_planned/wiki-and-collections-zones-rollout.md:67` as resolved | pending |

### Phase 6: Document Navigation

| ID | Task | Status |
|---|---|---|
| P6_001 | Add `marked.js` (CDN, pinned version) to `index.html` | completed — pinned `marked@12.0.2` |
| P6_002 | Server: add `/api/doc?path=...` endpoint returning raw markdown | completed — includes repo resolution + docs path containment |
| P6_003 | Drawer: expand to full-pane mode on click; render markdown via marked | completed — preview toggle expands drawer and renders markdown/fallback |
| P6_004 | Camera fly-in animation: focus on clicked star, zoom to surface | completed - custom camera/OrbitControls tween verified |
| P6_005 | Next/prev neighbor keys (J/K or arrows) traverse via edges | completed - J/K and arrow traversal verified |
| P6_006 | Breadcrumb trail of visited stars; back button to retrace | completed - HUD trail and Back verified |
| P6_007 | Esc key + background click exit full-pane mode and zoom out | completed - clears selection/drawer and resets camera |

### Phase 7: Polish

| ID | Task | Status |
|---|---|---|
| P7_001 | Keyboard nav: arrows pan camera, +/- zoom, R reset | partial - +/- zoom and R/0/Home reset verified; arrows remain neighbor traversal |
| P7_002 | Touch/pinch gestures via OrbitControls touch config | pending |
| P7_003 | Minimap (corner overlay, top-down projection of nodes) | pending |
| P7_004 | Ambient particles for archived docs (drifting dust trails) | pending |
| P7_005 | Update README with controls cheatsheet + screenshot | pending |

### Phase 8: FIXED END — Integration Audit + Ecosystem State + Learnings

| ID | Task | Status |
|---|---|---|
| P8_001 | Run `analyze_integration.py --staged` on all galaxy commits | pending |
| P8_002 | Refresh ecosystem state (`find_agents.sh`, `find_skills.sh`, `state.json`) | pending |
| P8_003 | Capture learnings: library decision rationale, orbit math, render-loop hack removal | pending |
| P8_004 | Append session diary entry summarizing the upgrade | pending |

---

## Risks & Trade-offs

| Risk | Mitigation |
|---|---|
| Library migration (Phase 1) larger than estimated | Phase 1 is the gate — if spike B is too big, fall back to spike A (just upgrade) and accept continued workarounds |
| Orbital math drifts from force-graph clustering aesthetics | Phase 4 keeps degree-weighted radius so high-connectivity domains stay close-in (preserves visual hierarchy) |
| `marked.js` adds a second JS dep | Acceptable for an internal-only tool; pinned to a specific version |
| No tests | Verification is visual; not adding a test framework for a one-off dev tool. P1_005 + P4_007 are explicit regression checks |
| Animated orbits hurt perf on big repos (>500 docs) | Throttle rotation to 30fps; pause when `document.hidden`; respect `prefers-reduced-motion` (P4_005) |

---

## Artifacts

- Plan manifest: [`plan-manifest.json`](./plan-manifest.json)
- Planning manifest: [`planning-manifest.json`](./planning-manifest.json)

## Progress Notes

- 2026-05-01: Completed the first document-navigation foundation slice without changing the graph library: shared repo-name resolution, `/api/doc`, pinned `marked.js`, drawer preview toggle, and preview styles. Syntax/API verification passed. Browser/canvas smoke test still needs a proper browser tool or Node >=22.22.0 for the Node REPL Playwright path.
- 2026-05-02: Completed the interaction stabilization slice while keeping `3d-force-graph@1.74.0`: set user `NODE_REPL_NODE_PATH` to bundled Node `v24.14.0`, added canvas-level pointer picking because the native hover/click pipeline is unreliable under the current custom render loop, added HUD search/results, demoted the known cross-origin `Script error`, compacted the status overlay, and added a custom camera fly-in tween. Bundled-Node Playwright verification passed for render/status, hover tooltip, click selection/drawer/camera movement, background clear, drag no-select, search Enter focus, and drawer connection focus. In-app Browser Use still needs a Codex/MCP restart to pick up `NODE_REPL_NODE_PATH`.
- 2026-05-02: Completed the raw Three.js migration spike and layout-state foundation. Galaxy now defaults to a raw Three.js renderer with its own scene/camera/OrbitControls, node/link mesh adapter, halos/corona, shared canvas picking, drawer/search/camera interactions, and deterministic layout state (`buildLayoutState` / `applyLayoutState`). The old `3d-force-graph@1.74.0` path is lazy-loaded only with `?renderer=force`. Verification passed for raw render, status, node/link meshes, hover/click/search/drawer navigation, and force fallback boot. Full orbital layout, d3-force simulation extraction, and visual redesign remain pending.
- 2026-05-04: Added the first true galaxy/orbit visual pass: deterministic starfield, solar orbit rings, domain planets, document moon/star orbits, local moon rings, subtle animated starfield/ring/planet motion, and wider initial camera fit. Browser verification passed for 1 starfield, 5 solar rings, 5 domain planets, 10 local moon rings, 73 document meshes, 55 links, nonblank WebGL pixel sample, hover/click/search interactions, and screenshot capture at `C:/tmp/galaxy-orbit-smoke-2026-05-04.png`.
- 2026-05-04: Completed mode/label/depth polish slice. Added screen-space domain labels plus hovered/selected document labels, additive nebula sprites, lifecycle orbital bands, and mode verification across atlas/lifecycle/freshness plus ambient. Browser verification passed: atlas/freshness share the orbital layout, lifecycle uses distinct bucket bands, ambient expands to 157 docs and 9 planets, labels remain visible, hover/click still work, and screenshot captured at `C:/tmp/galaxy-polish-smoke-2026-05-04.png`.
- 2026-05-04: Completed structural node and navigation polish slice. Added `structuralKind` detection for wiki/collection/planned/archive docs, raw geometry variants (wiki octahedron, collection cube, planned tetrahedron, archive icosahedron), structural legend entries, J/K and arrow neighbor traversal, HUD breadcrumb trail, and Back navigation. Browser verification passed with Ambient: 157 docs, planned/archive structural nodes present, planned/archive geometry verified, legend entries visible, J selects a connected node, Back returns to the prior node, and screenshot captured at `C:/tmp/galaxy-nav-smoke-2026-05-04.png`. Current atlas has no live `_wiki`/`_collections` docs, so those code paths are implemented but not visually exercised with live data.
- 2026-05-04: Completed skybox/mobile/keyboard polish slice. Added a textured Three.js sky dome, CSS fallback background gradient, reset/zoom keyboard shortcuts (R/0/Home, +/-), Esc/background camera reset, and mobile HUD/drawer constraints. Browser verification passed in desktop and mobile viewports with nonblank WebGL pixels, hidden status panel, sky dome presence, keyboard zoom/reset behavior, and screenshots captured at `C:/tmp/galaxy-desktop-next-2026-05-04.png` and `C:/tmp/galaxy-mobile-next-2026-05-04.png`.
- 2026-05-04: Completed core-selection and relation-visibility correction. Galaxy no longer chooses the highest-degree doc as the center; it now prefers canonical BCOS roots in order: `docs/table-of-context.md`, `docs/context-index.md`, `docs/current-state.md`, `docs/document-index.md`, then README/system-context fallback. For Theo this makes `Table of Context` the core instead of Laura's operational role doc. Relation lines are hidden by default and revealed only for the hovered/selected node. Domain labels are hidden by default; `?labels=domains` remains available for diagnostics. Browser verification passed for core id, hidden default links, hover-revealed links, hidden domain labels, desktop/mobile render, and screenshots refreshed at `C:/tmp/galaxy-desktop-next-2026-05-04.png` and `C:/tmp/galaxy-mobile-next-2026-05-04.png`.
- 2026-05-04: Completed custom core visual pass inspired by the `glowing-sun` post-processing direction but without vendoring/copying that repo. Added a procedural photosphere texture, layered corona sprites, rotating flare sprites, smoother low-opacity shell glow, and a pulsing point light around the Galaxy core. Verification now asserts the core texture/sprites/light are present and still passes desktop/mobile render checks.
- 2026-05-04: Completed non-bubble astronomy visual correction after screenshot review. Removed generic additive halo shells from ordinary docs and the core, lowered ambient light so surfaces shade instead of reading as flat UI bubbles, added shader-driven core surface, added procedural terrain/bump textures for docs, added procedural textured domain planets, reduced atmosphere shells, and made solar orbit guides more elliptical/subtle. Browser smoke now verifies textured docs and that non-core bubble halos remain below threshold.
- 2026-05-04: Corrected live-view readability and light-source semantics. Small docs/satellites and domain planets are brighter through material surface emissive and higher ambient starlight, while off-screen directional lights are reduced to faint fill so the visual no longer implies a second sun. The central core point light remains the dominant light source.
- 2026-05-04: Added second-level folder/engagement gravity wells. Galaxy now infers delivery engagement groups from `docs/operations/engagements/<slug>/`, creates mini-planets for every engagement and for larger folders, and orbits documents around the mini-planet when present. Hover/selection labels now name the owning planet/folder/engagement, while the tooltip still names the actual satellite document.

## Design Direction: Context Astronomy Model

The Galaxy should model context structure, not graph-degree trivia:

- **Core / galactic center:** the canonical repo context root. Today that means `table-of-context`, future `context-index`, then `current-state` / `document-index` fallback. This should eventually come directly from `.claude/quality/context-index.json`.
- **Planets / gravity wells:** domain, folder, topic, collection, or hub groups with enough docs/internal references to deserve a local orbital system. Threshold should combine doc count, internal relation count, and metadata semantics, not only folder name.
- **Satellites:** ordinary canonical docs orbiting their owning planet/topic.
- **Moons / stations:** wiki pages, collection manifests, and planned/archive docs can use distinct geometry/texture once the unified metadata model exposes `zone`, `bucket`, `page-type`, `manifest-schema`, tags, and review state.
- **Debris / asteroid belts:** inbox, stale, archive, unindexed, low-trust, or warning-heavy docs should be visually present but peripheral, dimmer, and optionally filtered.
- **Relations / trajectories:** do not render the whole relation web permanently. Show incident paths on hover/selection; cross-system relations should appear as temporary trajectories between mini-galaxies/planet systems.
- **Zoom/focus rule:** a folder/topic becomes a zoomable mini-galaxy when it has enough docs and internal relations to be navigated independently. Cross-mini-galaxy relations remain visible only in focused context.
- **Metadata dependency:** the planned unified metadata/context-index pipeline is the right source for root selection, derived facets, wiki/collection state, review health, tags, and relation semantics. Galaxy should consume that model instead of rediscovering semantics locally.

## Current Visual Semantics

This is the implemented logic today, before the unified context-index pipeline:

- **Core:** chosen from canonical BCOS roots: `table-of-context`, future `context-index`, `current-state`, `document-index`, then system/README fallback.
- **Domain planets:** one planet per `cluster`/domain from frontmatter; bucket/folder fallback when cluster is missing.
- **Folder/engagement mini-planets:** second-level gravity wells inside a domain. Delivery engagements under `docs/operations/engagements/<slug>/` always become mini-planets; other folders become mini-planets when they have enough docs (`>=4` today).
- **Planet size:** based mostly on number of docs in that cluster, via `sqrt(count)`.
- **Mini-planet size:** based on number of docs in that folder/engagement.
- **Satellites/docs:** each document orbits its folder/engagement mini-planet when one exists; otherwise it orbits the domain planet.
- **Satellite size:** based on document `version` plus `size_bytes`; ambient/soft tiers are scaled down.
- **Satellite color:** based on `type` and structural kind (`wiki`, `collection`, `planned`, `archive`); freshness mode overrides this with age color.
- **Hover label:** the floating planet label shows the owning domain/folder/engagement instead of duplicating the satellite document title. The tooltip remains the document title/type/version/age.
- **Orbit placement:** deterministic by cluster/folder grouping, not true relation gravity yet.
- **Relations:** hidden by default; hover/selection shows incident relations only.
- **Current limitation:** Theo currently has `0` declared edges and `55` folder edges, so the scene mostly shows folder/domain structure, not true semantic references yet.

## Target Visual Story

The Galaxy should help the user answer:

- What is the canonical center of this repo?
- Which domains/topics are big enough to act as their own systems?
- Which engagement/folder system am I currently looking at?
- Which docs are canonical satellites versus peripheral debris?
- Where are stale, low-trust, warning-heavy, planned, archive, inbox, wiki, and collection objects?
- Which relations matter when I inspect one object?
- Which folder/topic should be zoomed into as a mini-galaxy?

Once `.claude/quality/context-index.json` exists, Galaxy should map:

- **Core:** canonical context root from index metadata.
- **Planets/gravity wells:** clusters, folders, tags, topics, collections, or wiki areas above a hub threshold using doc count + internal relation density + canonical ownership.
- **Satellites:** managed canonical docs orbiting the owning planet/topic.
- **Stations:** collection manifests, wiki hub pages, or important indexes.
- **Asteroids/debris:** inbox, archive, stale, warning-heavy, missing-frontmatter, or low-trust docs.
- **Comets:** source summaries or externally fetched wiki/source docs whose `last-fetched` drives refresh state.
- **Trajectories:** relation lines shown only in focused context, colored by relation type.

## Files Affected

- `.claude/scripts/bcos-galaxy/galaxy.js` (major)
- `.claude/scripts/bcos-galaxy/galaxy.css` (minor)
- `.claude/scripts/bcos-galaxy/index.html` (minor — add marked.js, possibly remove force-graph CDN)
- `.claude/scripts/bcos-galaxy/generate.py` (minor — node-type field)
- `.claude/scripts/bcos-galaxy/server.py` (minor — `/api/doc` endpoint)
- `.claude/scripts/bcos-galaxy/diag.html`, `diag2.html` (delete)

## Files Untouched

- `docs/**` (no data points modified)
- `.claude/scripts/bcos-dashboard/**` (sibling tool — only touched indirectly via Phase 0 commit split)
- All other `.claude/skills/`, `.claude/agents/`, `.claude/quality/` content

---

## Next Actions

- **Approve** → begin Phase 0 (commit hygiene)
- **Modify** → tell me what to revise
- **Cancel** → stop, archive session

# Context Zones Architecture

How CLEAR Context OS classifies every file under `docs/` into a **zone** — a typed region with its own trust level, freshness model, and source-of-truth role. The zone is what tells the framework whether a doc is canonical truth, derived explanation, frozen evidence, future intent, or historical record.

For the sibling zone mechanics see [`wiki-zone.md`](./wiki-zone.md) and [`collections-zone.md`](./collections-zone.md). For the philosophical placement of zones see [`system-design.md`](./system-design.md). For metadata fields per zone see [`metadata-system.md`](./metadata-system.md).

> **Net summary in one line:** zones are derived from path, not declared in frontmatter. The classifier lives in [`context_index.py`](../../../.claude/scripts/context_index.py) (`_zone_for()`); the declarative companion lives in [`_context-zones.yml.tmpl`](../templates/_context-zones.yml.tmpl). A drift test ([`test_zone_registry.py`](../../../.claude/scripts/test_zone_registry.py)) enforces that the two agree.

---

## Why a Zone Registry Exists

Every layer above the file system needs to know which docs are real, which are derivative, and which are evidence. Search needs to rank canonical truth above explainers. Bundle resolvers need to pull frozen evidence into decision logs and live data into engagement plans. Maintenance schedulers need different freshness windows for `last-updated` vs `last-fetched`. Hooks need to validate base metadata on canonical docs but not on inbox dumps.

Hardcoding "what counts as canonical" inside every script is the failure mode. The zone is the single signal — the folder IS the truth — and every consumer reads from one classifier.

The classifier already exists as Python (`context_index.py._zone_for()`). The registry is the **declarative companion**: a YAML manifest that names the zones, declares their freshness model and source-of-truth role, and gets read by skills, search, bundle resolvers, validators, and any future tooling that needs to reason about zones without re-implementing path logic. A drift test enforces that the YAML and the Python agree.

---

## The Twelve Zones

| Zone | Path pattern | Trust | Freshness signal | Role |
|---|---|---|---|---|
| `active` | `docs/*.md` (top-level) | high | `last-updated` | Canonical business truth — the data points |
| `framework` | `docs/_bcos-framework/**/*.md` | system | `last-updated` | The framework's own spec; ships with BCOS |
| `wiki` | `docs/_wiki/pages/**` + `docs/_wiki/source-summary/**` | high-derived | `last-reviewed` (page) / `last-fetched` (source-summary) | Derived explanation, citation-bearing |
| `wiki-internal` | `docs/_wiki/raw/**`, `docs/_wiki/.archive/**`, `_wiki/{queue,log,overview,README}.md`, `_wiki/.config.yml`, `_wiki/.schema.yml` | system | none | Raw captures + queue + bookkeeping; mechanically managed |
| `collection-manifest` | `docs/_collections/<col>/_manifest.md` | high-derived | `last-updated` | Inventory of evidence in a collection |
| `collection-sidecar` | `docs/_collections/<col>/*.meta.md` | high-derived | `last-updated` | Per-artifact metadata; the file IS the truth |
| `collection-artifact` | `docs/_collections/<col>/*.md` (other) | evidence | none | Raw artifacts (the file IS the truth — never paraphrased) |
| `inbox` | `docs/_inbox/**` | low | none | Triage; raw captures awaiting routing |
| `planned` | `docs/_planned/**` | future | `last-updated` | Polished proposals — intent, not reality |
| `archive` | `docs/_archive/**` | historical | none | Superseded; never treated as current |
| `custom-optout` | `docs/_<other>/**` (any user-created `_`-prefixed folder not in the known set) | opted-out | none | Drafts, experiments, vendor notes — framework-ignored |
| `generated` | `docs/document-index.md`, `docs/_wiki/index.md`, `docs/.wake-up-context.md` | system | none | Auto-generated; never hand-edited |

The path patterns above are illustrative. The authoritative classifier is `context_index.py._zone_for()`; the authoritative declarative form is `_context-zones.yml.tmpl`.

---

## Per-Zone Schema

Every entry in `_context-zones.yml.tmpl` declares the same eight fields:

| Field | Meaning | Example |
|---|---|---|
| `id` | Stable zone name; matches `context_index.py._zone_for()` outputs | `wiki` |
| `path-glob` | Glob expressing the zone's footprint under `docs/` | `docs/_wiki/pages/**/*.md` |
| `frontmatter-fields-required` | Required base metadata — empty list if not enforced | `[name, type, cluster, version, status, created, last-updated]` |
| `freshness-field` | Frontmatter field that tracks staleness; `null` if zone is timeless | `last-reviewed` |
| `freshness-model` | How freshness is interpreted: `update-driven` / `review-driven` / `fetch-driven` / `none` | `review-driven` |
| `source-of-truth-role` | Role this zone plays in cross-zone bundle resolution: `canonical` / `derived` / `evidence` / `future` / `historical` / `system` / `opted-out` | `derived` |
| `addressing` | How callers reference docs here: `slug` / `path` / `manifest+row` / `path-only` | `slug` |
| `optional` | If `true`, the zone may be absent from a fresh repo; bundle resolvers handle `unsatisfied-zone-requirements` gracefully | `true` |

Optional override for zones whose freshness signal varies by page-type:

| Field | Meaning | Example |
|---|---|---|
| `freshness-by-page-type` | Inline list of `page-type=field` overrides. Consumers split each entry on `=` and fall back to `freshness-field` when no page-type matches. | `[explainer=last-reviewed, source-summary=last-fetched]` |

The `wiki` zone uses this to encode the distinction the path classifier flattens: pages track `last-reviewed`, source-summary pages track `last-fetched`. P5 bundle resolvers and any consumer that reasons about wiki freshness must use [`freshness_field_for(entry, page_type)`](../../../.claude/scripts/load_zone_registry.py) — never read `freshness-field` directly for the wiki zone.

This schema is the contract. Any consumer that reads the registry can rely on every entry having these fields populated.

---

## Trust Levels and Their Consequences

The trust level (set by `context_index.py._trust_level()`) drives how downstream tooling treats a doc:

- **`high`** (`active`): edits authoritative; search ranks first; lint enforces full base metadata.
- **`high-derived`** (`wiki`, `collection-manifest`, `collection-sidecar`): treated as authoritative explanation/inventory; lint enforces but with zone-specific schema extensions.
- **`evidence`** (`collection-artifact`): the file IS the truth — never paraphrased, never edited. Lint is minimal; metadata lives in adjacent sidecars.
- **`future`** (`planned`): readable, but always represented as intent. Bundle resolvers tag with `status` so callers know it's not real yet.
- **`historical`** (`archive`): readable but never current. Search de-prioritizes; bundle resolvers exclude unless explicitly requested.
- **`low`** (`inbox`): unstructured triage. Skipped by most validators; not exposed by default in cross-zone search.
- **`system`** (`framework`, `wiki-internal`, `generated`): the framework's own surface. Read for reference; not the user's truth.
- **`opted-out`** (`custom-optout`): the user said "leave this alone." Skipped by all maintenance.

---

## Source-of-Truth Roles in Bundle Resolution

When two zones disagree about a fact, the role determines who wins. The bundle resolver (P5) reads `source-of-truth-role` per zone, plus the per-profile precedence in `_context.task-profiles.yml`, to resolve conflicts deterministically:

- **`canonical`** beats everything else for design/architecture decisions.
- **`evidence`** beats `derived` for legal/contractual facts.
- **`derived`** supports — never overrides — but provides citations.
- **`future`** is excluded from "what is true now" queries unless the profile explicitly asks for plans.
- **`historical`** is excluded from current queries.
- **`system`** never wins a business-fact contest; it only wins for "how does the framework work" questions.

A profile can override this ranking per task. The full prose reference for profile shape, ranking semantics, freshness model, traversal rules, and escalation rules will live in `context-routing.md` once P5 ships; until then the live spec lives in [`docs/_planned/wiki-missing-layers/implementation-plan.md`](../../_planned/wiki-missing-layers/implementation-plan.md) (P5 section).

---

## Freshness Models

Three of the twelve zones carry meaningful freshness signals. The model field tells consumers how to read them:

- **`update-driven`** (`active`, `framework`, `planned`, `collection-manifest`, `collection-sidecar`): `last-updated` advances on every content change. Staleness = age since last update vs. `review-cycle`.
- **`review-driven`** (`wiki` pages): `last-reviewed` advances when a human confirms the doc still matches reality, even with no content change. Used for explainers that build on canonical data points.
- **`fetch-driven`** (`wiki` source-summary pages): `last-fetched` records when the upstream URL or document was last pulled. Used for the wiki refresh quick-check tier.

The other zones are timeless (`inbox`, `archive`, `wiki-internal`, `collection-artifact`, `custom-optout`, `generated`) — they have no expected freshness signal.

---

## How Consumers Read the Registry

Every consumer follows the same load order:

1. If `docs/.context-zones.yml` exists in the current repo, use it (per-repo override).
2. Otherwise, use `docs/_bcos-framework/templates/_context-zones.yml.tmpl` (framework default).

The loader lives at [`.claude/scripts/load_zone_registry.py`](../../../.claude/scripts/load_zone_registry.py). Consumers call `load_zone_registry()` and receive a list of mappings, one per zone, with the eight fields above populated.

This mirrors the per-repo override pattern already used by [`_wiki.schema.yml.tmpl`](../templates/_wiki.schema.yml.tmpl).

### Cross-zone search entry-point

`/context search` (cross-zone) and `/wiki search` (zone-scoped sugar) both ride this registry. The mechanical engine at [`context_search.py`](../../../.claude/scripts/context_search.py) reads the registry to apply per-zone ranking boosts (canonical 1.5×, derived 1.2×, evidence 1.1×, future 0.9×, historical 0.7×, opted-out 0.5×) and to populate `zones-skipped-not-present` when an `optional: true` zone has no docs yet. **D-10 strict:** mechanical default; LLM-touching paths require explicit `--semantic` opt-in. No auto-trigger.

Citation IDs returned by search are `zone:slug` — the same `id` field declared in this registry concatenated with the doc's filename stem. Stable across whitespace edits; reusable across the whole context base.

---

## The Drift Contract

The Python classifier (`context_index.py._zone_for()`) and the YAML registry (`_context-zones.yml.tmpl`) are two expressions of the same truth. They MUST agree. The drift test ([`test_zone_registry.py`](../../../.claude/scripts/test_zone_registry.py)) enforces this:

- Every zone the test fixture exercises must appear in the YAML.
- Every zone declared in the YAML must be exercised by at least one fixture.
- Every YAML entry declares the eight required fields.
- Every declared `freshness-field` is one the context model already knows how to read.
- Zone IDs are unique.
- The `optional` flag is boolean.

If `_zone_for()` learns a new zone, the fixture and the YAML must follow in the same change. If a zone is renamed, the fixture, the YAML, and any consumer must follow. The drift test is the safety net.

---

## How Zones Compose with Other Architecture

- [`metadata-system.md`](./metadata-system.md) — base frontmatter + the warning fields `tags`, `last-reviewed`, `last-fetched` that the registry's `freshness-field` references.
- [`content-routing.md`](./content-routing.md) — how new content lands in the right zone (Path 1: data point, Path 2: wiki, Path 3: collection, Path 4: planned, Path 5: archive, Path 6: inbox, Path 7: custom-optout).
- [`wiki-zone.md`](./wiki-zone.md) — the wiki zone's full schema, lifecycle, and refresh model.
- [`collections-zone.md`](./collections-zone.md) — the collections zone's manifest pattern.
- [`system-design.md`](./system-design.md) — the cross-zone retrieval and bundle resolution layer (cross-references this doc).

---

## Summary

- Twelve zones, each with eight declarative fields.
- The path classifier (`_zone_for`) and the YAML registry are the two agreed-on representations.
- A drift test asserts they stay aligned.
- Per-repo override at `docs/.context-zones.yml`; framework default at `docs/_bcos-framework/templates/_context-zones.yml.tmpl`.
- Every cross-zone consumer (search, bundle resolver, validators, hooks, future skills) reads through one loader.

The zone is the single signal. Everything else — trust, freshness, source-of-truth precedence, addressing — is derived from it.

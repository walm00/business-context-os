# Typed-Event Taxonomy — Digest Sidecar Contract

How the dispatcher's daily digest emits **structured events** alongside the human-readable prose, so the dashboard can render one-click cards without re-parsing strings, and so `resolutions.jsonl` (see [maintenance-lifecycle.md](./maintenance-lifecycle.md)) can carry typed `finding_type` + `finding_attrs` from day 1.

For the bigger picture of how this fits the autonomy + UX + self-learning surface, see [`docs/_planned/autonomy-ux-self-learning/implementation-plan.md`](../../_planned/autonomy-ux-self-learning/implementation-plan.md). This doc is the **contract**; that plan is the **rollout**.

> **Status: schema 1.0.0 (P1 closed).** The `finding_type` enum is harvested from the 9 `job-*.md` reference docs (P1_001) and pinned below. Per-type `finding_attrs` shapes are the canonical contract (P1_002). Sidecars conforming to this doc declare `schema_version: "1.0.0"`; the P0 fixtures still carry `0.1.0-provisional` until they're regenerated against the formal enum at P1_006.

---

## Why typed events

Three problems the prose-only digest cannot solve cleanly:

1. **One-click extraction.** Cards in the dashboard cockpit currently re-parse `### N. inbox aged: docs/_inbox/Q1-notes.md (14 days) — triage` with regex. Typed events make `{finding_type: "inbox-aged", finding_attrs: {file, age_days, ...}}` the source of truth; prose is a render of the typed event, not the other way around.
2. **Audience tiering through one map.** Per `L-DASHBOARD-20260425-010`, every UX-tier flip lives in `bcos-dashboard/labels.py`. Collectors emit raw `finding_type` IDs; renderers prefer the `display_*` form and fall back to raw. One file controls the whole audience layer.
3. **Resolution recording without re-parsing.** When the user clicks "triage", `record_resolution.py` (P4_002) writes the event with `finding_type` + `finding_attrs` *as they were emitted* — not as the renderer happened to phrase them that morning. This is what makes the self-learning ladder safe: the consistency calculation in `promote_resolutions.py` (P5_002) keys on stable IDs, not strings.

---

## The contract (one paragraph)

The dispatcher writes two co-located artifacts on every run:

- `docs/_inbox/daily-digest.md` — the prose digest a human reads
- `docs/_inbox/daily-digest.json` — the **typed-event sidecar** the dashboard consumes

The sidecar is the canonical source. The prose is rendered from the same in-memory structure that produced the sidecar (`digest_sidecar.py`, P1_004). Action counts, verdicts, and per-job summaries must agree across the two — the wiring test in `.claude/scripts/test_digest_typed_events.py` enforces that agreement.

---

## Sidecar shape

Top-level (provisional, hardened in P1):

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Semver of the sidecar contract. `"0.1.0-provisional"` until P1 closes; `"1.0.0"` thereafter. |
| `date` | string | ISO date (`YYYY-MM-DD`); matches the prose H1. |
| `overall_verdict` | enum | `"green" \| "amber" \| "red"`. Drives cockpit takeover view. |
| `run_at` | string | ISO-8601 timestamp; matches the prose `_Run at_` trailer. |
| `findings` | `Finding[]` | Typed action items. Each maps to a card in the cockpit. |
| `auto_fixed` | `AutoFix[]` | Silent fixes applied this run. Hidden from chat by default; cockpit shows under `<details>`. |
| `jobs` | `JobSummary[]` | Per-job verdict + finding count; powers the green-day "All clear" view. |

A `Finding`:

| Field | Type | Description |
|---|---|---|
| `number` | int | 1-based; matches the prose `### N.` heading. |
| `finding_type` | enum | One of the IDs pinned in P1_001 (e.g. `inbox-aged`, `broken-xref`, `stale-propagation`, `source-summary-refresh-due`, `graveyard-stale`, `orphan-page`, `coverage-gap`). |
| `verdict` | enum | `"green" \| "amber" \| "red"` for *this finding*; rolls up into `overall_verdict`. |
| `emitted_by` | string | The job ID that emitted this finding (`audit-inbox`, `index-health`, `wiki-source-refresh`, …). Used by the auditor to scope reversal-rate by rule. |
| `finding_attrs` | object | Typed attributes per `finding_type`; shape pinned in P1_002. Fixture-tier shapes are illustrative, not authoritative. |
| `suggested_actions` | string[] | Action IDs from `headless-actions.md` (P3) the cockpit should surface as primary/secondary buttons. |

An `AutoFix`:

| Field | Type | Description |
|---|---|---|
| `fix_id` | string | One of the IDs in `auto-fix-whitelist.md`. |
| `target` | string | Path the fix touched. |
| `detail` | string | Short human-readable summary of the change. |

A `JobSummary`:

| Field | Type | Description |
|---|---|---|
| `job` | string | Job ID (matches `### {job} — {verdict}` in prose). |
| `verdict` | enum | `"green" \| "amber" \| "red"`. |
| `finding_count` | int | Findings emitted by this job; used for the green-day "0 / 0 / 0" headline. |

---

## `finding_type` enum (canonical)

Harvested from the 9 `job-*.md` reference docs in `.claude/skills/schedule-dispatcher/references/`. **39 distinct IDs** across 9 jobs. Two IDs are dual-emitted (`missing-frontmatter` + `broken-xref` come from both `audit-inbox` and `index-health` — that overlap is intentional: daily lint vs. weekly deep). The enum value is the same in both cases; the emitter is disambiguated by the `emitted_by` field on the `Finding`.

### audit-inbox (8)

| `finding_type` | One-line meaning |
|---|---|
| `missing-frontmatter` | Active doc has no YAML frontmatter or empty block. |
| `boundary-violation` | Data-point content crosses its declared `EXCLUSIVELY_OWNS` boundary. |
| `broken-xref` | Markdown link points to a non-existent file. |
| `stale-marker` | TODO / FIXME / OUTDATED / DEPRECATED token in active doc. |
| `duplication-obvious` | Same heading text appears in 2+ active data points. |
| `inbox-aged` | File in `docs/_inbox/` older than the triage threshold. |
| `lesson-overlap-proposal` | Two lessons with similarity above threshold. |
| `lesson-orphaned` | Lesson tags reference a skill or concept no longer present. |

### index-health (8)

| `finding_type` | One-line meaning |
|---|---|
| `missing-frontmatter` | (Shared with `audit-inbox`.) |
| `missing-required-field` | Required frontmatter field absent. |
| `missing-last-updated` | `last-updated` field absent (other frontmatter present). |
| `frontmatter-field-order` | All required fields present, but order is non-canonical. |
| `broken-xref` | (Shared with `audit-inbox`.) |
| `broken-xref-single-candidate` | Broken xref where exactly one matching basename exists. Auto-fixable. |
| `trailing-whitespace` | Lines ending in spaces or tabs. Auto-fixable. |
| `eof-newline` | File does not end with exactly one newline. Auto-fixable. |

### architecture-review (6)

| `finding_type` | One-line meaning |
|---|---|
| `integration-coverage-gap` | Skill / agent / hook / script on disk not wired into `install.sh`, `settings.json`, `state.json`, or `.gitignore`. |
| `xref-broken-ecosystem` | Cross-reference gap inside the ecosystem layer. |
| `lesson-retirement-candidate` | Lesson >6 months old, stale, not referenced, not recently violated. |
| `lesson-sharp-still` | Lesson actively violated in recent diary; keep prominent. |
| `lesson-merge-candidate` | Multiple lessons say the same thing; consolidation candidate. |
| `lessons-count-high` | `lessons.json` has >50 active lessons without recent consolidation. |

### daydream-deep (6)

| `finding_type` | One-line meaning |
|---|---|
| `architecture-misalignment` | Two docs claim ownership of the same topic. |
| `datapoint-should-split` | Single data point has grown beyond single ownership; topics diverged. |
| `datapoint-should-merge` | Excessive cross-referencing between data points; overlapping domains. |
| `datapoint-should-retire` | Data point no longer reflects business reality. |
| `datapoint-missing` | Knowledge lives in sessions but never made into a structured doc. |
| `cluster-needs-restructuring` | Shape of business has changed; cluster structure no longer fits. |

### daydream-lessons (3)

| `finding_type` | One-line meaning |
|---|---|
| `daydream-observation` | Drift between data points and business reality, surfaced by reflection. |
| `lesson-duplicate-candidate` | New lesson candidate overlaps existing lesson. |
| `lesson-new-capture` | Net-new lesson surfaced from recent sessions. |

### wiki-coverage-audit (3)

| `finding_type` | One-line meaning |
|---|---|
| `coverage-gap-data-point` | Active data point has no wiki explainer (no wiki page lists it in `builds-on`). |
| `coverage-gap-inbox-term` | Term repeats in inbox but no wiki page covers it. |
| `cluster-mismatch` | Wiki page uses a `cluster` value not present in `document-index.md`. |

### wiki-graveyard (3)

| `finding_type` | One-line meaning |
|---|---|
| `graveyard-stale` | Wiki page `last-reviewed` older than `graveyard-days` (default 365). |
| `orphan-pages` | Wiki page has no inbound wiki links and no edits within `orphan-grace-days`. |
| `retired-page-type` | Wiki page uses a page-type that is retired in the schema. |

### wiki-source-refresh (2)

| `finding_type` | One-line meaning |
|---|---|
| `source-summary-upstream-changed` | Source-summary upstream URL changed since last fetch (quick-check tier). |
| `refresh-due` | Source-summary `last-fetched` ≥ `full_threshold_days` ago. |

### wiki-stale-propagation (1)

| `finding_type` | One-line meaning |
|---|---|
| `stale-propagation` | Wiki page's `builds-on` source updated after wiki page `last-reviewed`. |

### lifecycle-sweep (4)

| `finding_type` | One-line meaning |
|---|---|
| `lifecycle-trigger-fired` | Frontmatter `lifecycle.*` trigger evaluated true; doc is ready-to-route per a routing rule with passing reality-checks. |
| `lifecycle-body-marker-confirmed` | Body marker (SENT / DECISION / RESOLVED / etc.) plus reality cross-check confirms the routing decision. |
| `lifecycle-route-ambiguous` | Multiple routing signals or a failing reality check made auto-routing unsafe — surface for user judgement. |
| `lifecycle-orphan-active` | Active-zone doc with no `lifecycle:` field, no inbound xrefs, age past `min_age_days × 8` — likely missing exit triggers. |

### Dispatcher meta (1)

| `finding_type` | One-line meaning |
|---|---|
| `frequency-suggestion` | Job autonomy / cadence tuning suggestion (📈 / 📉). |

### auto-fix-audit (2)

| `finding_type` | One-line meaning |
|---|---|
| `rule-reversal-spike` | A learned rule's reversal rate crossed the 7-day threshold (default 5%). Recommend-only — auditor never auto-disables on this signal alone. |
| `rule-downstream-error` | A fix batch (≥3 events on same rule) preceded an `index-health` verdict flip from green→amber/red within 24h. Recommend-only; user judges causation. |

---

## `finding_attrs` shape (canonical)

Every `Finding` carries a typed `finding_attrs` object. Shapes below are the contract — the dashboard renderer and `record_resolution.py` both depend on these field names being stable.

**Rule (load-bearing):** `finding_attrs` is a flat object of primitive values (string / int / float / bool / null). No nested objects, no arrays of objects. The renderer reads attrs left-to-right into chip rows; nesting breaks that. Anything that wants structure becomes a separate `finding_type`. Arrays of *primitives* (e.g. `string[]`) are allowed where noted.

| `finding_type` | `finding_attrs` shape |
|---|---|
| `missing-frontmatter` | `{file: str}` |
| `boundary-violation` | `{file: str, boundary: str, crossing_content: str}` |
| `broken-xref` | `{file: str, broken_link: str, target_path: str}` |
| `stale-marker` | `{file: str, marker_type: str, marker_location: str}` |
| `duplication-obvious` | `{files: str[], heading_text: str}` |
| `inbox-aged` | `{file: str, age_days: int, size_kb: int \| null, first_heading: str \| null}` |
| `lesson-overlap-proposal` | `{lesson_ids: str[], similarity_score: float}` |
| `lesson-orphaned` | `{lesson_id: str, missing_concept: str}` |
| `missing-required-field` | `{file: str, missing_field: str}` |
| `missing-last-updated` | `{file: str}` |
| `frontmatter-field-order` | `{file: str}` |
| `broken-xref-single-candidate` | `{file: str, broken_link: str, single_candidate_path: str}` |
| `trailing-whitespace` | `{file: str, line_numbers: int[]}` |
| `eof-newline` | `{file: str}` |
| `integration-coverage-gap` | `{file: str, gap_type: str, severity: str}` |
| `xref-broken-ecosystem` | `{file: str, broken_path: str, referenced_by: str}` |
| `lesson-retirement-candidate` | `{lesson_id: str, age_days: int, last_violation_date: str \| null}` |
| `lesson-sharp-still` | `{lesson_id: str, last_violation_date: str, violation_frequency: int}` |
| `lesson-merge-candidate` | `{lesson_ids: str[], overlap_ratio: float}` |
| `lessons-count-high` | `{lesson_count: int}` |
| `architecture-misalignment` | `{file1: str, file2: str, topic: str}` |
| `datapoint-should-split` | `{file: str, split_topics: str[], growth_metric: str}` |
| `datapoint-should-merge` | `{files: str[], overlap_evidence: str}` |
| `datapoint-should-retire` | `{file: str, reason: str}` |
| `datapoint-missing` | `{topic: str, session_refs: str[]}` |
| `cluster-needs-restructuring` | `{cluster_name: str, reason: str}` |
| `daydream-observation` | `{observation_text: str, affected_files: str[]}` |
| `lesson-duplicate-candidate` | `{lesson_text: str, existing_lesson_id: str}` |
| `lesson-new-capture` | `{lesson_text: str}` |
| `coverage-gap-data-point` | `{data_point_file: str}` |
| `coverage-gap-inbox-term` | `{term: str, mention_count: int}` |
| `cluster-mismatch` | `{wiki_file: str, cluster_value: str}` |
| `graveyard-stale` | `{file: str, last_reviewed_date: str, age_days: int, threshold_days: int}` |
| `orphan-pages` | `{wiki_file: str, grace_days_threshold: int}` |
| `retired-page-type` | `{wiki_file: str, retired_type: str}` |
| `source-summary-upstream-changed` | `{wiki_file: str, source_url: str, check_date: str}` |
| `refresh-due` | `{wiki_file: str, last_fetched_date: str, age_days: int}` |
| `stale-propagation` | `{wiki_file: str, source_file: str, source_updated_date: str, last_reviewed_date: str}` |
| `lifecycle-trigger-fired` | `{file: str, rule_id: str, destination_zone: str, destination_bucket: str \| null, confidence: float, trigger_kind: str}` |
| `lifecycle-body-marker-confirmed` | `{file: str, rule_id: str, destination_zone: str, destination_bucket: str \| null, marker: str, confidence: float}` |
| `lifecycle-route-ambiguous` | `{file: str, rule_id: str \| null, conflict_reason: str, confidence: float}` |
| `lifecycle-orphan-active` | `{file: str, age_days: int, inbound_xref_count: int}` |
| `frequency-suggestion` | `{job: str, direction: str, current_schedule: str, suggested_schedule: str, reason: str}` |
| `rule-reversal-spike` | `{rule_id: str, underlying_finding_type: str, underlying_action_taken: str, n_applied: int, n_reverted: int, reversal_rate: float, window_days: int, threshold_percent: int}` |
| `rule-downstream-error` | `{rule_id: str, underlying_finding_type: str, underlying_action_taken: str, downstream_job: str, verdict_before: str, verdict_after: str, batch_size: int, window_hours: int}` |

`str | null` means the field is required to be present (key exists) but the value MAY be null when the emitter cannot determine it. Skipping the key is a contract violation; emit `null` instead.

### Common-key conventions

When a finding_attrs uses these names, they always mean the same thing:

| Key | Meaning |
|---|---|
| `file` / `wiki_file` / `data_point_file` | Repo-relative POSIX path. |
| `*_date` | ISO-8601 date `YYYY-MM-DD` (no time). |
| `*_days` | Integer count of days, ≥0. |
| `lesson_id` / `lesson_ids` | Stable IDs from `lessons.json` (e.g. `L-DASHBOARD-20260425-010`). |
| `*_count` | Non-negative integer. |

---

## How this connects to `resolutions.jsonl`

When a user clicks a card or invokes a headless action, `record_resolution.py` (P4_002) writes one row to `.claude/quality/ecosystem/resolutions.jsonl` with these fields copied from the typed event verbatim:

- `finding_type` (string) — the enum value from the sidecar
- `finding_attrs` (object) — the shape pinned in P1_002
- `action_taken` (string) — which `headless-actions.md` action the user picked
- `action_target` (string) — usually `finding_attrs.file` or its analogue

The remaining 10 fields in the 14-field schema (`ts`, `outcome`, `time_to_resolution_s`, `trigger`, `bulk_id`, `natural_language_command`, `user_specificity`, `applied_diff_summary`, `applied_diff_hash`, `subsequent_validation_status`) are filled by the recorder, not the digest. See [implementation-plan.md §D-02](../../_planned/autonomy-ux-self-learning/implementation-plan.md) for the full contract.

This is the load-bearing reason every `finding_type` and every `finding_attrs` shape is **stable from emission**: when a user has clicked "triage" on `inbox-aged` 5 times in 14 days, the consistency calculation that promotes the rule depends on the type ID being the same string both times. Renaming `inbox-aged` to `inbox-stale` mid-flight breaks the ladder silently.

---

## Test surface

Three tests guard this contract:

- `.claude/scripts/test_digest_typed_events.py` (P0_002) — fixtures round-trip through `digest_parser` *and* `digest_sidecar.parse_sidecar` once that ships at P1_004.
- `.claude/scripts/test_resolutions_jsonl_schema.py` (P0_003) — the 14-field row contract.
- `.claude/scripts/test_card_coverage.py` (P2_010) — every `finding_type` renders for at least one fixture.

The first two are RED at P0 (intentionally; they're the TDD scaffold). They turn GREEN at P1 and P4 respectively.

---

## See also

- [system-design.md](./system-design.md) — the three-layer architecture this contract operates within.
- [maintenance-lifecycle.md](./maintenance-lifecycle.md) — where the dispatcher's daily-digest emission fits in the daily/weekly/monthly cadence.
- [`.claude/skills/schedule-dispatcher/SKILL.md`](../../../.claude/skills/schedule-dispatcher/SKILL.md) — Step 7 of the dispatcher (digest emission). Updated in P1_008 to cite this contract.
- [`.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md`](../../../.claude/skills/schedule-dispatcher/references/auto-fix-whitelist.md) — silent-tier fix IDs; this contract's `auto_fixed[]` array references those IDs.
- [`.claude/quality/fixtures/digests/`](../../../.claude/quality/fixtures/digests/) — green / amber / red fixture pairs (`.md` + `.json`) the test suite reads.

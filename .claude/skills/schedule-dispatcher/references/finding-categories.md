# Finding Categories — Classifier + Identity Tuples

**Schema-version-aware reference for the dispatcher's typed-event emission (1.1.0+).**

Maps every `finding_type` to one of two categories — and defines the "identity tuple" used by Step 4.5 to compute `consecutive_runs` (the load-bearing signal behind the stuck-badge UX).

**Owned by:** `schedule-dispatcher` skill.
**Consumed by:** dispatcher Step 4.5 (stickiness compute), `bcos-dashboard/cockpit.py` (category-aware rendering), `bcos-dashboard/headless_actions.py` (acknowledge handler gating).
**Test surface:** `test_digest_typed_events.py` asserts every `finding_type` in [`typed-events.md`](../../../../docs/_bcos-framework/architecture/typed-events.md) has a category mapping here. Drift fails the wiring test.

---

## Two categories

| Category | Meaning | UX surface |
|---|---|---|
| **`repo-context`** | A finding about the *user's content or repo state*. The LLM and one-click headless actions are allowed to mutate the user's repo to resolve. | Fix button + Snooze + Dismiss in the cockpit. "say 'fix it'" works in chat. |
| **`bcos-framework`** | A finding about the *framework's own state* — a bug, missing-from-install file, contract violation, safety-guard fire. Resolving in a client repo would be overwritten by the next `update.py`. | **Acknowledge-only** card. Mark-read button. No Fix. Footer: "Reported to BCOS — will be fixed in next release." |

The split is **load-bearing**: it's the reason an LLM operating in a client repo cannot be tricked into "fixing" a framework bug locally and creating drift that the next BCOS update will undo. Every finding emitted by the dispatcher MUST declare `category` in 1.1.0; absence defaults to `repo-context` for backward compatibility with 1.0.0 sidecars.

---

## Classifier (all 58 known `finding_type` IDs)

### `repo-context` (49)

| `finding_type` | Emitter | Primary `finding_attrs` key |
|---|---|---|
| `missing-frontmatter` | audit-inbox / index-health | `file` |
| `boundary-violation` | audit-inbox | `file` |
| `broken-xref` | audit-inbox / index-health | `file` |
| `stale-marker` | audit-inbox | `file` |
| `duplication-obvious` | audit-inbox | `files[0]` |
| `inbox-aged` | audit-inbox | `file` |
| `lesson-overlap-proposal` | audit-inbox | `lesson_ids[0]` |
| `lesson-orphaned` | audit-inbox | `lesson_id` |
| `missing-required-field` | index-health | `file` |
| `missing-last-updated` | index-health | `file` |
| `frontmatter-field-order` | index-health | `file` |
| `broken-xref-single-candidate` | index-health | `file` |
| `trailing-whitespace` | index-health | `file` |
| `eof-newline` | index-health | `file` |
| `integration-coverage-gap` | architecture-review | `file` |
| `xref-broken-ecosystem` | architecture-review | `file` |
| `lesson-retirement-candidate` | architecture-review | `lesson_id` |
| `lesson-sharp-still` | architecture-review | `lesson_id` |
| `lesson-merge-candidate` | architecture-review | `lesson_ids[0]` |
| `lessons-count-high` | architecture-review | (no per-instance key — singleton) |
| `architecture-misalignment` | daydream-deep | `file1` |
| `datapoint-should-split` | daydream-deep | `file` |
| `datapoint-should-merge` | daydream-deep | `files[0]` |
| `datapoint-should-retire` | daydream-deep | `file` |
| `datapoint-missing` | daydream-deep | `topic` |
| `cluster-needs-restructuring` | daydream-deep | `cluster_name` |
| `daydream-observation` | daydream-lessons | `observation_text` |
| `lesson-duplicate-candidate` | daydream-lessons | `existing_lesson_id` |
| `lesson-new-capture` | daydream-lessons | `lesson_text` |
| `coverage-gap-data-point` | wiki-coverage-audit | `data_point_file` |
| `coverage-gap-inbox-term` | wiki-coverage-audit | `term` |
| `cluster-mismatch` | wiki-coverage-audit | `wiki_file` |
| `graveyard-stale` | wiki-graveyard | `file` |
| `orphan-pages` | wiki-graveyard | `wiki_file` |
| `retired-page-type` | wiki-graveyard | `wiki_file` |
| `source-summary-upstream-changed` | wiki-source-refresh | `wiki_file` |
| `refresh-due` | wiki-source-refresh | `wiki_file` |
| `stale-propagation` | wiki-stale-propagation | `wiki_file` |
| `wiki-canonical-drift-suggestion` | wiki-canonical-drift | `canonical_file` |
| `wiki-authority-asymmetry` | wiki-ingest-triage | `wiki_file` |
| `wiki-temporal-supersession-candidate` | wiki-ingest-triage | `successor` |
| `wiki-true-contradiction` | wiki-ingest-triage | `wiki_file_a` |
| `lifecycle-trigger-fired` | lifecycle-sweep | `file` |
| `lifecycle-body-marker-confirmed` | lifecycle-sweep | `file` |
| `lifecycle-route-ambiguous` | lifecycle-sweep | `file` |
| `lifecycle-orphan-active` | lifecycle-sweep | `file` |
| `frequency-suggestion` | dispatcher | `job` |
| `rule-reversal-spike` | auto-fix-audit | `rule_id` |
| `rule-downstream-error` | auto-fix-audit | `rule_id` |

### `bcos-framework` (9, added in 1.1.0)

| `finding_type` | Emitter | Primary `finding_attrs` key |
|---|---|---|
| `dispatcher-silent-skip` | dispatcher Step 4b | `job` |
| `job-reference-missing` | dispatcher Step 4 | `job` |
| `node-job-cross-repo-reference` | dispatcher Step 4a (preflight) | `job` |
| `scheduled-task-cwd-mismatch` | `context-onboarding` Step 6e (registration-time) AND `bcos-umbrella` `audit_scheduled_task_cwd.py` (audit-time) | `sibling_id` |
| `schema-validation-failed` | dispatcher Step 7 | `offending_finding_type` |
| `auto-fix-handler-threw` | dispatcher Step 5 | `fix_id` |
| `installer-seed-missing` | dispatcher Step 1/4 | `expected_path` |
| `data-corruption-detected` | any job using `safe_load_jsonl` | `file` |
| `framework-config-malformed` | dispatcher Step 1 | `file` |

---

## Finding-identity tuple (for `consecutive_runs` compute)

The dispatcher's Step 4.5 reads up to the last 30 diary entries and matches today's finding against history by **identity tuple**: `(finding_type, primary_attr_value, emitted_by)`. When all three match an entry from the immediately-prior dispatcher tick, `consecutive_runs` increments. When the prior tick had no match, `consecutive_runs = 1` and `first_seen = today`.

**Why include `emitted_by` in the tuple:** `missing-frontmatter` can come from both `audit-inbox` (weekly deep) and `index-health` (daily lint). Same finding_type, same file — but different emitters and potentially different fix paths. Treating them as separate identities prevents false-merge.

**Why `primary_attr_value` and not the full `finding_attrs`:** the secondary fields (`age_days`, `last_status_code`, `confidence`) drift between runs even when the underlying problem is unchanged. Keying on the primary path/ID/term keeps the tuple stable.

**Singleton findings** (no per-instance primary key — e.g. `lessons-count-high`): the dispatcher uses the string `"singleton"` as the primary_attr_value so identity is just `(finding_type, "singleton", emitted_by)`.

The primary-key column in the classifier tables above is authoritative — any new finding_type added to the enum MUST update both `typed-events.md` (shape) AND this file (category + primary key).

---

## Cross-references

- [`typed-events.md`](../../../../docs/_bcos-framework/architecture/typed-events.md) — `finding_type` enum source of truth + per-type `finding_attrs` shapes.
- [`headless-actions.md`](./headless-actions.md) — one-click action catalog. The `acknowledge` action (added in 1.1.0) is the ONLY action applicable to `category: bcos-framework` findings.
- [`auto-fix-whitelist.md`](./auto-fix-whitelist.md) — silent-tier fix IDs; auto-fixes are always `repo-context` (the dispatcher refuses to auto-fix framework state).
- [`SKILL.md`](../SKILL.md) — dispatcher Step 4.5 (stickiness compute), Step 7 (digest emission), Step 7c (framework-issues.jsonl writer).

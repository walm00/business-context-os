# Headless Actions — One-Click Cards

The set of actions the dashboard can run from a card click without asking Claude for help. Parallel to [`auto-fix-whitelist.md`](./auto-fix-whitelist.md) — that file is the **silent** tier (the dispatcher applies fixes during the daily run); this file is the **one-click** tier (the user clicks a card to apply the fix). Both layers route through the same machinery: the only difference is *who pulled the trigger*.

This file is the source of truth. The actual enforcement list lives in `schedule-config.json > headless_actions.enabled`. An action ID must appear in BOTH this file (defined) AND the user's config (enabled) before the dashboard endpoint will execute it.

For the contract this satisfies, see [`docs/_bcos-framework/architecture/typed-events.md`](../../../../docs/_bcos-framework/architecture/typed-events.md). For the resolutions log every action click writes to, see [`docs/_planned/autonomy-ux-self-learning/implementation-plan.md`](../../../../docs/_planned/autonomy-ux-self-learning/implementation-plan.md) §D-02.

---

## Action schema (every entry MUST declare all fields)

| Field | Type | Meaning |
|---|---|---|
| `id` | kebab-case string | Stable identifier; recorded as `action_taken` in `resolutions.jsonl`. |
| `label` | short string | Human-friendly button label (≤4 words). |
| `applies-to` | `finding_type[]` | One or more canonical IDs from typed-events.md. |
| `type` | `state-change` \| `metadata-edit` \| `move` \| `delete` \| `stub` \| `apply-config` | Coarse class for telemetry + risk grading. |
| `reversible-by` | string | One-line sentence on how to undo. Must reference a real mechanism (git revert, `unmark_resolved`, `git mv` back, etc.). Cannot be "no automatic undo" — if undo is not possible, the action does not belong here; it belongs in the chat-confirm flow. |
| `telemetry-event` | kebab-case string | Stable name written to the diary on success. Wired by P4_004 into resolutions.jsonl as the `outcome` row. |
| `requires-write` | `bool` | True when the action mutates files in `docs/` or `_wiki/`. Used by the auditor to scope reversal-rate detection. |
| `default-trigger` | `dashboard-click` \| `chat-bulk-fix` \| `chat-targeted-fix` \| `scheduled-headless` | Most-likely trigger for this action. Recorded in resolutions.jsonl as the `trigger` field default. |

---

## Chat-intercept mechanism (P3_008 design decision)

The `bulk_id` (P4_005) and `user_specificity` classifier (P4_006) need to know the **natural-language phrase** that triggered a sequence of headless calls. Three options were considered (see `review-notes-2026-05-05.md` section G):

| Option | Cost | Drift risk |
|---|---|---|
| **(a) Assistant-supplied as a parameter to `/api/actions/headless`** | cheapest; works today, no hook changes | drift if assistant rephrases ≠ user intent |
| (b) `UserPromptSubmit` hook captures user text into `.claude/hook_state/pending-commands.jsonl`, drained by next headless call | needs hook + queue + drain | low |
| (c) Skip the field in v0.1; classify `user_specificity` heuristically from `action_target` patterns | zero | high (lossy) |

**Decision:** start with (a). The endpoint accepts an optional `natural_language_command` body field that the assistant fills with the user's verbatim phrase ("fix all the inbox stuff", "archive that one"). Add (b) only if drift exceeds 5% — measurable once P4 has sample data. (c) is the fallback for endpoint calls without an assistant in the loop (e.g. browser-only sessions): the bulk_id is generated fresh per click and `user_specificity` is inferred from how many cards were clicked together.

Endpoint contract for the field:

```json
POST /api/actions/headless
{
  "id": "inbox-aged-triage",
  "finding": { ... full Finding object from sidecar ... },
  "natural_language_command": "fix the inbox stuff" ,  // optional; assistant-filled
  "bulk_id": "8f3a..."                                  // optional; one ID per phrase
}
```

When `natural_language_command` is absent, the recorder writes `null` for that field in resolutions.jsonl. When `bulk_id` is absent, the recorder generates a fresh UUID per request.

---

## The 9 actions (v0.1)

### `inbox-aged-triage`

- **applies-to:** `inbox-aged`
- **type:** `move`
- **label:** "Triage now"
- **reversible-by:** `git mv` the file back to `docs/_inbox/`. The recorder captures the source path so undo is one click.
- **telemetry-event:** `inbox-triaged`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Opens the file in the editor and asks the user where to triage. (v0.1 stub — until the editor-integration ships, this records the intent and surfaces a follow-up card asking for a destination cluster. Full move executes in a follow-up turn.)

---

### `inbox-aged-archive`

- **applies-to:** `inbox-aged`
- **type:** `move`
- **label:** "Archive"
- **reversible-by:** `git mv` from `docs/_archive/` back to `docs/_inbox/`.
- **telemetry-event:** `inbox-archived`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Moves the inbox file under `docs/_archive/{YYYY}/` with `last-archived: {today}` frontmatter added.

---

### `stale-propagation-mark-reviewed`

- **applies-to:** `stale-propagation`
- **type:** `metadata-edit`
- **label:** "Mark reviewed"
- **reversible-by:** `git revert` the single-file commit to roll back the `last-reviewed` frontmatter bump.
- **telemetry-event:** `wiki-marked-reviewed`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Sets `last-reviewed: {today}` on the wiki page named in `finding_attrs.wiki_file`, leaves body unchanged. Lightweight acknowledgment that the user looked and decided no edit was needed.

---

### `source-summary-refresh`

- **applies-to:** `refresh-due`, `source-summary-upstream-changed`
- **type:** `state-change`
- **label:** "Refresh source"
- **reversible-by:** Refresh writes a new revision tagged with timestamp; previous revision retained in git.
- **telemetry-event:** `source-summary-refreshed`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Invokes the `bcos-wiki` skill's refresh path with `--slug={derived-from-wiki-file}`. The skill handles the actual fetch + diff + re-summarize; this action is the trigger.

---

### `graveyard-stale-archive`

- **applies-to:** `graveyard-stale`
- **type:** `move`
- **label:** "Move to private"
- **reversible-by:** `git mv` from `.private/_planned-archive/` back to `docs/_archive/`.
- **telemetry-event:** `graveyard-archived`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Moves the archived file from `docs/_archive/` to `.private/_planned-archive/`, where it leaves the git-tracked surface but stays accessible on disk. Per CLAUDE.md folder convention, `.private/` is gitignored — this is the "completely retire" path.

---

### `orphan-page-archive`

- **applies-to:** `orphan-pages`
- **type:** `move`
- **label:** "Archive page"
- **reversible-by:** `git mv` from `docs/_archive/wiki-pages/` back to `docs/_wiki/pages/`.
- **telemetry-event:** `orphan-archived`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Moves the orphaned wiki page (no inbound `builds-on`, no anchor data point) into `docs/_archive/wiki-pages/{YYYY}/`. The decision to archive is the user's; the move itself is mechanical.

---

### `retired-page-type-migrate`

- **applies-to:** `retired-page-type`
- **type:** `metadata-edit`
- **label:** "Migrate page type"
- **reversible-by:** `git revert` the metadata edit.
- **telemetry-event:** `page-type-migrated`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Updates the wiki page's `page-type:` frontmatter from a retired value to the canonical replacement defined in `docs/_bcos-framework/architecture/wiki-zone.md`. Body untouched.

---

### `coverage-gap-stub`

- **applies-to:** `coverage-gap-data-point`, `coverage-gap-inbox-term`
- **type:** `stub`
- **label:** "Stub explainer"
- **reversible-by:** Delete the stub file (`git rm`). Stubs are clearly marked `status: stub` in frontmatter.
- **telemetry-event:** `coverage-stub-created`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Creates a 5-line stub at `docs/_wiki/pages/{slug}.md` with `builds-on: [{anchor data point}]` and `status: stub`. Lets the user fill body later without losing the explainer slot.

---

### `apply-suggestion`

- **applies-to:** `frequency-suggestion`
- **type:** `apply-config`
- **label:** "Apply"
- **reversible-by:** Re-running `/schedule preset <job> <old-cadence>` or hand-editing `schedule-config.json` back. The schedule-preset endpoint atomic-renames — git tracks the prior value.
- **telemetry-event:** `frequency-suggestion-applied`
- **requires-write:** true (writes to `.claude/quality/schedule-config.json`)
- **default-trigger:** `dashboard-click`

**What it does:** Reads `finding_attrs.job` + `finding_attrs.suggested_schedule` and forwards to the existing `/api/schedule/preset` endpoint. Non-destructive — the underlying writer rewrites schedule-config.json atomically.

---

### `lesson-candidate-add`

- **applies-to:** `lesson-new-capture`, `lesson-duplicate-candidate`
- **type:** `metadata-edit`
- **label:** "Capture lesson"
- **reversible-by:** Removing the lesson via the `lessons-consolidate` skill or hand-editing `lessons.json`.
- **telemetry-event:** `lesson-captured`
- **requires-write:** true (writes to `.claude/quality/ecosystem/lessons.json`)
- **default-trigger:** `dashboard-click`

**What it does:** Appends a new entry to `lessons.json` with the candidate text and current timestamp. For `lesson-duplicate-candidate` it instead bumps the existing lesson's `last-violation-date` rather than creating a duplicate.

---

### `lifecycle-route-archive`

- **applies-to:** `lifecycle-trigger-fired`, `lifecycle-body-marker-confirmed`
- **type:** `move`
- **label:** "Archive"
- **reversible-by:** `git mv docs/_archive/{bucket}/{filename} {original_path}` — the route_decision carries the original path; undo is one click.
- **telemetry-event:** `lifecycle-archived`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Moves the doc from its current zone to `docs/_archive/{rule.destination_bucket}/`. Bucket comes from the routing rule (e.g. `outbound/sent`, `decisions`, `meetings`). Surface-only mode (default for the first 2 weeks) returns the planned move without touching the filesystem.

---

### `lifecycle-route-wiki`

- **applies-to:** `lifecycle-trigger-fired`, `lifecycle-body-marker-confirmed`
- **type:** `move`
- **label:** "Promote to wiki"
- **reversible-by:** `/wiki archive {slug}` then `git revert` of the promote commit. The bcos-wiki skill owns the move; the resolutions log records the slug for quick undo.
- **telemetry-event:** `lifecycle-promoted-to-wiki`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Delegates to `bcos-wiki` skill's `/wiki promote <slug>` path — never duplicates the move logic. The slug is derived from the doc's filename. Sweep flags the candidate; the actual conversion to source-summary shape happens via the wiki skill so frontmatter and citation banners stay correct.

---

### `lifecycle-route-collection`

- **applies-to:** `lifecycle-trigger-fired`, `lifecycle-body-marker-confirmed`
- **type:** `move`
- **label:** "Move to collection"
- **reversible-by:** `git mv` from `docs/_collections/{type}/` back to original path; remove the matching `_manifest.md` row.
- **telemetry-event:** `lifecycle-routed-to-collection`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Delegates to `context-ingest` Path 5 (collections routing). The lifecycle field declares `route_to_collection: <type>`; sweep verifies the manifest exists, then forwards the move to context-ingest so the manifest row is appended atomically with the file move.

---

### `lifecycle-fold-into`

- **applies-to:** `lifecycle-trigger-fired`, `lifecycle-body-marker-confirmed`
- **type:** `metadata-edit`
- **label:** "Fold into target"
- **reversible-by:** `git revert` of the fold commit. Folding produces ONE atomic commit (target edit + source archive) so undo is a single revert.
- **telemetry-event:** `lifecycle-folded`
- **requires-write:** true
- **default-trigger:** `dashboard-click`

**What it does:** Reads `lifecycle.fold_into` target path + the source doc's body, surfaces the proposed merge to the user via chat. The actual fold (append/merge into target + archive source) is chat-confirmed, never silent — fold-into is the highest-judgement of the four lifecycle actions.

---

### `promote-outputs` — added in 1.3.0

- **applies-to:** `job-missing-outputs-declaration`
- **type:** `apply-config`
- **label:** "Promote outputs"
- **reversible-by:** `git revert` of the single commit produced by the writer. `promote_outputs.py` updates `schedule-config.json` AND the matching `references/job-<name>.md` in one logical batch; both files appear in the same auto-commit so one revert covers both.
- **telemetry-event:** `outputs-promoted`
- **requires-write:** true (writes to `.claude/quality/schedule-config.json` AND `.claude/skills/schedule-dispatcher/references/job-<name>.md`)
- **default-trigger:** `chat-targeted-fix`

**What it does:** Reads `finding_attrs.job` + `finding_attrs.undeclared_paths` and invokes `.claude/scripts/promote_outputs.py --job <job> --paths <p1,p2,...>`. The script:

1. Validates each path against the same rules dispatcher Step 7b applies (relative, inside `docs/` or `.claude/`, no `..` segments, total ≤ 20 literals + 5 globs after merge).
2. Idempotently merges the paths into `jobs.<job>.outputs` in `schedule-config.json` (skips already-present entries; preserves order; atomic write).
3. Idempotently appends the paths to the `## Outputs` section of `references/job-<job>.md`. If the section is `(none)`, replaces with the new list.
4. On validation failure, exits non-zero with a single JSON line on stderr matching the `job-outputs-validation-error` `finding_attrs` shape: `{finding_type, job, invalid_entries, reason}`.

**Routing.** The interactive renderer dispatches by the finding's `emitted_by`:

- `dispatcher` → `business-context-os-dev/.claude/scripts/promote_outputs.py`
- `umbrella-dispatcher` → `bcos-umbrella/scripts/promote_outputs.py` (same CLI; adds asymmetric "must resolve inside umbrella repo root" validator on top, rejecting cross-sibling paths with `umbrella-job-write-outside-host`-shape stderr and exit 5)

**Pairing with "No, ignore":** The dispatcher Step 7b silencer reads `resolutions.jsonl` and suppresses re-emit when `(job, path)` appears in a `promote-outputs` row with `outcome: ignored` within the last `outputs_ignore_window_days` (default 30). The two options ("Yes, always" + "No, ignore") together make the chip the complete loop closure — accept or silence — with no manual config edits.

---

### `acknowledge` — added in 1.1.0

- **applies-to:** All 7 `bcos-framework` finding_types: `dispatcher-silent-skip`, `job-reference-missing`, `schema-validation-failed`, `auto-fix-handler-threw`, `installer-seed-missing`, `data-corruption-detected`, `framework-config-malformed`
- **type:** `state-change`
- **label:** "Mark read"
- **reversible-by:** No filesystem mutation occurs — there is nothing to reverse. The resolutions.jsonl row is the only persistence; remove it manually if needed.
- **telemetry-event:** `framework-issue-acknowledged`
- **requires-write:** false
- **default-trigger:** `dashboard-click`

**What it does:** Records the user has seen the framework finding so the cockpit can hide it from the next view. **Does not patch the underlying framework bug** — that work is the framework owner's, via the umbrella's portfolio aggregation of `bcos-framework-issues.jsonl`. This action is the ONLY one the cockpit surfaces for `category: bcos-framework` cards; the Fix-button slot is forcibly absent for them.

**Why no Fix button:** patching framework state (e.g. re-seeding a missing `lifecycle-routing.yml`, hand-editing `schedule-config.json` for missing fields, manually re-creating a job reference file) in a client repo would be overwritten by the next `update.py` run. The owner ships the fix upstream; siblings update; the finding stops emitting. See [`finding-categories.md`](./finding-categories.md) for the load-bearing repo-context vs bcos-framework split.

---

## Cross-reference: `auto-fix-whitelist.md` (silent tier)

| Concern | Whitelist (silent) | Headless (one-click) |
|---|---|---|
| **Who triggers?** | The dispatcher, during a scheduled run. | The user, by clicking a card. |
| **Surface** | `## 🔧 Auto-fixed (M)` block in the digest. | `## ⚠️ Action needed` cards in the cockpit. |
| **Reversal-rate audit** | Tracked weekly by `auto-fix-audit` (P6). | Same auditor, same `applied_diff_hash` field. |
| **Promotion path** | Shipped pre-tier-0 (already trusted). | Climbs the self-learning ladder (P5: preselect → P7: auto-apply with undo → P8: silent). |

The two surfaces share the [`record_resolution.py`](../../../scripts/record_resolution.py) library (P4_002). Whitelisted fixes write `trigger: "auto-fix-whitelist"`; headless clicks write `trigger: "dashboard-click"` (or `chat-bulk-fix` / `chat-targeted-fix` when the assistant routes through the endpoint).

---

## Adding a new action

1. Add an entry to this file with all 8 schema fields.
2. Add a handler under `bcos-dashboard/headless_actions.py` (P3_004) that validates input + executes the change + returns `{ok, applied_diff_summary, applied_diff_hash}`.
3. Add the new ID to `schedule-config.json > headless_actions.enabled`.
4. The wiring test [`test_headless_wiring.py`](../../../scripts/test_headless_wiring.py) (P3_006) auto-validates: every action has a `finding_type` from the canonical enum, every field is present, every `applies-to` ID exists, every action has a handler.

If you can't write a `reversible-by` clause that names a real mechanism, the action does not belong here — it belongs in the chat-confirm flow where the user can preview the destructive operation first.

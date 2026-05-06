# Auto-Fix Whitelist

The set of issue types the dispatcher is permitted to fix silently. Anything NOT on this list must be reported as an action item, regardless of how obvious the fix seems.

This file is the source of truth. The actual enforcement list lives in `schedule-config.json > auto_fix.whitelist`. A fix ID must appear in BOTH this file (defined) AND the user's config (enabled) before the dispatcher will apply it.

---

## Supported fix IDs

### `missing-last-updated`

**Detects:** A doc in `docs/` (excluding `_inbox/`, `_archive/`, `_collections/`, `_bcos-framework/`) whose frontmatter has no `last-updated` field.

**Fix:** Set `last-updated` to today's date in ISO format (`YYYY-MM-DD`).

**Why it's safe:** The missing field is always wrong. Today's date is the best available approximation if the file was just edited. If the file was last edited long ago but never had the field, the fix is still correct — it now has a field, and the value is monotonically valid (future audits can check git blame if precise date matters).

**NOT covered by this rule:** bumping `last-updated` on files that already have a value. That's a separate concern handled by the frontmatter hook at write time.

---

### `frontmatter-field-order`

**Detects:** A doc whose frontmatter block has all required fields present but in a non-canonical order (e.g. `version` appears before `type`).

**Fix:** Reorder to the canonical order defined in `docs/_bcos-framework/methodology/document-standards.md`.

**Why it's safe:** Pure reordering, no content or value change. Round-trips.

**NOT covered:** Adding missing fields. That's ask-only — the values require judgement.

---

### `trailing-whitespace`

**Detects:** Lines ending in spaces or tabs before the newline.

**Fix:** Strip trailing whitespace on affected lines.

**Why it's safe:** Pure formatting. Does not change text meaning. Idempotent.

**NOT covered:** Whitespace inside lines, tabs-vs-spaces indentation, line-ending normalization (CRLF vs LF) — those require editor config alignment, not dispatcher action.

---

### `eof-newline`

**Detects:** A Markdown file in `docs/` that does not end with a single trailing newline.

**Fix:** Add one trailing newline, or trim extra trailing newlines to exactly one.

**Why it's safe:** Standard POSIX-text hygiene. No content change.

---

### `broken-xref-single-candidate`

**Detects:** A Markdown link `[text](relative/path.md)` where the target file no longer exists, AND a `build_document_index.py` scan finds exactly ONE file in the repo with the same basename (e.g. link target was `brand/identity.md`, the file was moved and is now `identity.md` in a different folder — no other `identity.md` exists).

**Fix:** Rewrite the link to the single candidate's current path.

**Why it's safe:** When there is exactly one candidate, ambiguity is impossible. If zero candidates exist, the fix is not applied (issue becomes an action item: "file was renamed or deleted"). If two or more candidates exist, the fix is not applied (issue becomes an action item: "ambiguous rename — which target did you mean?").

**Requires:** The document index must be fresh. `index-health` job runs the builder before this check, so the data is current.

---

### `prune-sessions`

**Detects:** Session capture files in `.claude/quality/sessions/` older than the retention window (default: 30 days) as reported by `python .claude/scripts/prune_sessions.py --dry-run`.

**Fix:** Run `python .claude/scripts/prune_sessions.py` (no flag = apply). The script deletes files past the cutoff and prints a summary line that the dispatcher captures in `auto_fixed`.

**Why it's safe:** The script is deterministic, only touches its own managed directory, and the content is already captured in git via `schedule-diary.jsonl` summaries if needed. Reversible via `git checkout` if the directory is tracked.

---

### `ecosystem-state-refresh`

**Detects:** `.claude/quality/ecosystem/state.json` does not match disk. Either skills/agents have been added, removed, or renamed since the last refresh, or the file's `lastUpdated`/`lastAudit` timestamps are older than today.

**Fix:** Run `python .claude/scripts/refresh_ecosystem_state.py` (no flags = apply). The script regenerates `state.json` from disk by globbing `.claude/skills/*/SKILL.md` and `.claude/agents/*/AGENT.md`. Directories without those marker files become entries in `inventory.utilities`, not skills/agents. Preserves user-authored fields (`overlayCapable`, `discoveryCapable`, `health`, `maintenanceBacklog`).

**Why it's safe:**

1. **Deterministic.** Output is a function of the disk tree only — no judgement calls, no choice between alternatives.
2. **No business-content change.** state.json is a registry of structure (which directories exist), not content. The fix never touches docs, frontmatter, or any user-authored prose.
3. **Idempotent.** Running it twice with no disk changes produces identical output (only `lastUpdated`/`lastAudit` move forward; the rest is byte-stable).
4. **Easy to audit.** A single file changes; `git diff state.json` shows exactly what was reconciled.
5. **Reversible by git.** If the user disagrees with the result, `git checkout state.json` restores the prior version. The refresh script can then be re-run after the user adjusts disk state (e.g., adds a missing SKILL.md).

**Why this is on the whitelist:** Without it, the framework's monthly `architecture-review` job had to flag drift as an action item every run, expecting the user to fix it manually — but the actual repair is purely mechanical. Treating state.json as a derived artifact (lesson L-INIT-20260404-009) means the dispatcher can reconcile it the same way it reconciles `eof-newline` or `trailing-whitespace`.

**Requires:** `python .claude/scripts/refresh_ecosystem_state.py` must exist on disk. The script is shipped by the framework via `update.py`. If absent (e.g., very old install), the fix is skipped silently and the drift becomes an action item as before.

---

### `wiki-index-refresh`

**Detects:** `docs/_wiki/index.md` does not match the on-disk page set. Either pages have been added/removed/renamed under `docs/_wiki/pages/` or `docs/_wiki/source-summary/`, or a page's frontmatter (title, page-type, cluster, status, last-reviewed) has changed since the last refresh.

**Fix:** Run `python .claude/scripts/refresh_wiki_index.py` (no flags = apply). The script regenerates `_wiki/index.md` by reading frontmatter from every page under the two page-bearing folders. Pages are sorted by (page-type, slug) for stable output. The script no-ops cleanly when no `_wiki/` zone exists.

**Why it's safe:**

1. **Deterministic.** Output is a function of the page-frontmatter set only — no judgement calls.
2. **No business-content change.** `index.md` is a registry of pages (which exist + their frontmatter facts), not authored content. The fix never touches page bodies, page frontmatter, or any other user-authored prose.
3. **Idempotent.** Running it twice with no disk changes produces byte-identical output. The script verifies this and skips the write when the new content matches the existing file.
4. **Easy to audit.** A single file changes; `git diff _wiki/index.md` shows exactly what was reconciled.
5. **Reversible by git.** If the result looks wrong, `git checkout _wiki/index.md` restores the prior version. Re-running the script after fixing page frontmatter (the upstream source) produces the corrected index.

**Why this is on the whitelist:** Same derived-artifact pattern as `ecosystem-state-refresh` (lesson L-INIT-20260404-009). The wiki zone has no other authoritative list of pages — `index.md` is the registry, and the registry must mirror disk. Without this auto-fix, every page add/remove/rename would create an action item that's purely mechanical to resolve.

**Why-on-whitelist:** Derived index drift is mechanical registry drift, not content judgement. The dispatcher may repair it whenever `wiki-index-refresh` is enabled.

**Requires:** `python .claude/scripts/refresh_wiki_index.py` must exist on disk. The script is shipped by the framework via `update.py`. If absent (e.g., very old install or pre-wiki repo), the fix is skipped silently. The `_wiki/` zone itself is optional — repos that haven't adopted the wiki get a no-op.

---

### `wiki-mark-queue-ingested`

**Detects:** A URL line in `docs/_wiki/queue.md` that is already represented by a successfully created `source-summary` page but is missing an ingest marker.

**Fix:** Append an HTML comment marker to the exact queue line, e.g. `<!-- ingested 2026-05-04 -->`. The fix never changes the URL text, queue ordering, or any unrelated queue line.

**Why it's safe:** The source-summary page is the proof of completion. The marker is mechanical bookkeeping on the queue line and is idempotent because the job only applies it when no ingest marker is present.

**Why-on-whitelist:** Without this fix, successful Path A runs leave low-value queue cleanup as recurring action items. The queue state should reflect completed ingest without requiring a human to edit comments by hand.

**Requires:** `docs/_wiki/queue.md` must exist, the queue line URL must exactly match a `source-summary` page's `source-url`, and the source-summary page must pass `python .claude/scripts/wiki_schema.py validate`.

---

### `wiki-archive-expired-post-mortem`

**Detects:** A wiki page with `page-type: post-mortem` whose page-type schema defines `auto-archive-after-days`, where the page age exceeds that threshold and `status` is not already `archived`.

**Fix:** Change frontmatter `status: archived`, bump the patch `version`, and set `last-updated` to today's date. The file is not moved, deleted, renamed, or rewritten beyond those frontmatter fields.

**Why it's safe:** Post-mortem expiry is declared in the page-type schema, so the action is deterministic. The fix keeps the page in place and preserves its body, links, and provenance.

**Why-on-whitelist:** Expired post-mortems otherwise become repeated archive-candidate findings even though the schema already encodes the retention rule. The fix only applies the metadata state transition promised by that schema.

**Requires:** `docs/_wiki/.schema.yml` or the framework schema template must register `post-mortem` with `auto-archive-after-days`; the target page must validate before and after the edit.

---

### `wiki-rewrite-citations-on-rename`

**Detects:** A page rename event where the old and new wiki slugs are known from a migration entry, and other wiki pages still reference the old bare slug in intra-zone fields or wikilinks.

**Fix:** Rewrite exact bare-slug references from the old slug to the new slug in wiki frontmatter fields (`references`, `subpages`, `parent-slug`) and exact `[[old-slug]]` wikilinks. It does not rewrite prose text, cross-zone paths, or fuzzy matches.

**Why it's safe:** The migration gives a one-to-one old/new mapping. Exact slug and wikilink replacement is deterministic, scoped to wiki pages, and idempotent after the first rewrite.

**Why-on-whitelist:** Rename migrations should not leave dangling intra-zone references behind. This is the same mechanical consistency repair as `broken-xref-single-candidate`, but constrained to schema-backed wiki rename operations.

**Requires:** A migration record with exactly one `from` and `to` slug, a clean schema validation pass before rewrite, and a clean `python .claude/scripts/wiki_schema.py validate` after rewrite.

---

### `prune-diary`

**Detects:** Session-diary entries in `docs/.session-diary.md` older than the retention window (default: 14 days) as reported by `python .claude/scripts/prune_diary.py --dry-run`.

**Fix:** Run `python .claude/scripts/prune_diary.py` (no flag = apply). The script trims the oldest entries and prints a summary line.

**Why it's safe:** Diary is an append-only convenience log, not a source of truth. Full history lives in git. Script is deterministic and idempotent.

---

## Lifecycle-sweep auto-routes (gated behind 2-week burn-in)

The four `lifecycle-route-*` / `lifecycle-fold-into` actions ship as headless-action handlers but are **NOT yet on the dispatcher's silent auto-fix tier**. They need three independent gates to fire:

1. `.claude/quality/lifecycle-routing.yml` `global.surface_only` must be `false` (default `true`).
2. The action ID must appear in `schedule-config.json` `auto_fix.whitelist` (not present in the shipped template).
3. The matching routing rule's `confidence-tier` must be `1` (no default rule ships at tier 1).

Until all three gates pass, lifecycle-sweep emits findings only — the user clicks dashboard cards to apply each route. This protects canonical docs from a misfired classifier in the early-feedback window. The four IDs are **defined here for completeness** but should not be added to the whitelist before the burn-in clears with 0 false-positives.

### `lifecycle-route-archive`

**Detects:** A routing rule in `lifecycle-routing.yml` matches a doc with passing reality-checks and `confidence-tier: 1`. Typical destination: `docs/_archive/{rule.bucket}/{filename}`.

**Fix:** `git mv` from the doc's current path to `docs/_archive/{bucket}/{filename}`. Original path is recorded in `resolutions.jsonl` for one-click undo.

**Why it's safe (post-burn-in):** Move is reversible via `git mv` back; no content edit; zone classifier (`_zone_for`) recognises archive paths immediately so subsequent jobs skip the doc. Burn-in proves the classifier doesn't fire on canonical docs.

### `lifecycle-route-wiki`

**Detects:** A `research-dump`-style rule fires with passing url-in-body reality-check and `confidence-tier: 1`. Destination: `docs/_wiki/source-summary/{slug}.md` via `bcos-wiki` skill.

**Fix:** Delegates to `/wiki promote {slug}` — sweep never replicates the move logic. The bcos-wiki skill enforces source-summary frontmatter shape and citation banner requirements.

**Why it's safe (post-burn-in):** Wiki promotion is itself a CLEAR-governed action with its own frontmatter validation; lifecycle-sweep just identifies candidates. Reverting is `/wiki archive {slug}` plus `git revert` of the promote commit.

### `lifecycle-route-collection`

**Detects:** A rule fires for a doc declaring `lifecycle.route_to_collection: <type>` with passing manifest-row reality-check and `confidence-tier: 1`.

**Fix:** Delegates to `context-ingest` Path 5 — moves the file to `docs/_collections/{type}/` and appends a manifest row atomically.

**Why it's safe (post-burn-in):** Collections zone has its own manifest validation; the manifest row is the audit trail. Reverting is `git mv` back plus removing the manifest row (one-touch via context-ingest reverse).

### `lifecycle-fold-into`

**Detects:** A `meeting-notes`-style rule fires with passing fold-target-exists reality-check and `confidence-tier: 1`. The doc declares `lifecycle.fold_into: <target_path>`.

**Fix:** Surfaces the proposed fold (append/merge body of source into target) for chat confirmation. **Never silent** — fold-into is the highest-judgement of the four lifecycle actions because it edits TWO docs (target gets new content; source moves to archive).

**Why it's safe (post-burn-in):** Even at tier 1 with auto-fix enabled, fold-into requires user confirmation of the merge content. The whitelist entry only allows the *surfacing*; the actual edit is always chat-driven. Reverting is `git revert` of the single fold commit (target edit + source archive in one commit).

---

## Rules for adding new fix IDs

Any proposed addition must satisfy ALL of the following:

1. **No judgement calls.** The fix must be deterministic from the input — no choice between plausible alternatives.
2. **No business-content change.** Reformatting, renormalizing, or metadata-housekeeping only. Never touches the actual prose or data in a doc.
3. **Idempotent.** Applying it twice produces the same result as applying it once.
4. **Easy to audit.** A diary entry identifying the fix ID and file is enough for the user to verify what happened.
5. **Reversible by git.** If the user ever regrets a fix, `git diff` shows it clearly and `git checkout` restores the prior state.

If a proposed fix fails any of these tests, it stays as an action item — surfaced to the user in the digest, fixed only after user approval.

---

## Explicitly NOT auto-fixable (action items only)

For documentation — these always require user judgement, regardless of how obvious they look:

- Missing frontmatter entirely (whole block absent or mostly empty)
- Ownership boundary violations — content that belongs in a different data point
- Content contradictions between two docs
- Stale content (based on business knowledge, not metadata)
- Archival decisions (moving a doc to `_archive/`)
- Promoting docs from `_planned/` → active
- Inbox file triage (process / archive / discard)
- Lessons consolidation (merge / retire / split)
- Rewriting or improving prose
- Anything in `_bcos-framework/` — framework files only change via `update.py`

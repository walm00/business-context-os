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

### `prune-diary`

**Detects:** Session-diary entries in `docs/.session-diary.md` older than the retention window (default: 14 days) as reported by `python .claude/scripts/prune_diary.py --dry-run`.

**Fix:** Run `python .claude/scripts/prune_diary.py` (no flag = apply). The script trims the oldest entries and prints a summary line.

**Why it's safe:** Diary is an append-only convenience log, not a source of truth. Full history lives in git. Script is deterministic and idempotent.

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

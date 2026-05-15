# Job: wiki-failed-ingest

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** daily (cheap mechanical scan)
**Nature:** dead-letter scan — surface wiki ingest failures the framework otherwise hides
**Boundary:** node — own-repo paths only (no `../`, no absolute paths outside `$CLAUDE_PROJECT_DIR`, no sibling-repo names). Enforced by dispatcher Step 4a preflight.

<!-- emits-finding-types: machine-readable -->
```yaml
emits-finding-types:
  - wiki-failed-ingest:stuck-queue
  - wiki-failed-ingest:provenance-missing
  - wiki-failed-ingest:schema-violation
```

---

## Purpose

The wiki pipeline has three failure modes that historically lived only in lint output and never reached the daily digest:

1. **Stuck queue items** — URLs in `docs/_wiki/queue.md ## Pending` whose line hasn't been touched for N days. Either the user hasn't run `/wiki run`, or fetch keeps failing silently (HTTP error, paywall, schannel revocation).
2. **Provenance-missing source-summaries** — files in `docs/_wiki/source-summary/` whose frontmatter `provenance.source` is absent or empty. Path A's contract says every external summary must cite its source.
3. **Schema-violation drafts** — files in `docs/_wiki/raw/local/` or `docs/_wiki/pages/` whose YAML frontmatter is missing or unterminated. They get dropped from the wiki index silently.

This job is **mechanical-only**. Each issue surfaces as a per-file finding the user resolves manually — re-fetch, edit frontmatter, archive, etc. Auto-fix is intentionally not on the whitelist; these failure modes carry editorial judgement.

---

## Steps

### 1. Run the scanner

```text
python .claude/scripts/wiki_failed_ingest.py --json
```

Default `--stale-days = 14`. The scanner returns a JSON payload with `verdict`, `findings_count`, `actions_needed[]`, and `findings[]`.

### 2. Map scanner output to the dispatcher contract

The scanner already produces the dispatcher-shape. Use its output verbatim as the job result:

```json
{
  "verdict": "amber",
  "findings_count": 3,
  "auto_fixed": [],
  "actions_needed": [
    "stuck-queue: docs/_wiki/queue.md — 4 URL(s) have been in ## Pending for 21 days. Run /wiki run to drain.",
    "provenance-missing: docs/_wiki/source-summary/2025-q3-pricing.md — source-summary file is missing provenance.source.",
    "schema-violation: docs/_wiki/raw/local/notes.md — Wiki file is missing the YAML frontmatter delimiter (---)."
  ],
  "findings": [...],
  "notes": "3 wiki ingest issue(s) found"
}
```

### 3. Wiki-zone not enabled

If `docs/_wiki/` does not exist, the scanner returns `verdict: green` with `notes: "Wiki zone not enabled; failed-ingest scan skipped."` — emit that result and continue to the next job.

---

## Why daily

Failure modes here are cheap to detect (a single tree walk over `_wiki/`). Catching them within 24 hours keeps the user from hitting "I queued that URL last week and forgot" surprises. There's no cost to running it daily even on quiet repos — green output is one line in the digest.

---

## What NOT to do

- **Never auto-fix.** Editing frontmatter or rewriting `queue.md` requires editorial judgement about whether the URL is still wanted, whether the summary is correct, etc.
- **Never delete.** Archive is a separate decision (`wiki-graveyard` job covers that).
- **Don't double-flag.** If `wiki-stale-propagation` already surfaces a finding for the same file, prefer that — failed-ingest is the dead-letter for things the existing wiki jobs miss.

---

## Outputs

Paths this job writes that are eligible for dispatcher auto-commit on a tick where this job runs with verdict ≠ skipped. Globs allowed; resolved against `git status --porcelain` (rename destinations only). Empty list = job writes nothing committable on its own (findings flow to the global digest sidecar, which is already in `GLOBAL_ALLOWED`).

- (none)

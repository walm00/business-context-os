# /wiki lint — wiki-zone health checks

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`.)

This is the **on-demand** form of the wiki lint. The same checks fire automatically:
- Per-page on save (subset) via the PostToolUse frontmatter hook
- Daily via `job-index-health` (Step 5)
- Weekly/monthly/quarterly via the four wiki scheduled jobs (P5)

`/wiki lint` runs the full check suite against the entire zone.

---

## Setup

Read `docs/_wiki/.config.yml` → `domain`. Read `docs/_wiki/.schema.yml` (or framework template fallback) → `lint-checks`, `forbid-builds-on-paths`, `clusters.allow-cluster-not-in-source`, `thresholds`.

Set `today = current date YYYY-MM-DD`. Initialize `findings = []` (each: `{severity, check, file, line?, message}`).

Build the **known-slugs** set from every `*.md` under `docs/_wiki/pages/` and `docs/_wiki/source-summary/` (used by orphan + missing-wikilink checks).

---

## Check execution order

```
A — Check #7  frontmatter shape (cheap, structural — fail fast)
B — Check #8  citation path format
C — Check #5  stale propagation (builds-on.last-updated > self.last-reviewed)
D — Auto-fix  wiki-index-refresh (if whitelisted)
E — Check #3  orphan pages
F — Check #1  citation coverage (banner present)
G — Check #4  missing wikilinks / cross-references
H — Check #9  queue.md consistency
I — Check #11 split-product source pages
J — Check #12 parent-child consistency (umbrella ↔ sub)
K — Check NEW duplication-vs-data-point
L — Check NEW coverage-gap (informational; queries _inbox/)
M — Check NEW cluster-mismatch
N — Check NEW reference-format-mismatch (also enforced by hook)
O — Check NEW forbidden-builds-on-target (configurable)
P — Check NEW provenance-required + provenance-source-missing
Q — Check NEW schema-violation (also enforced by hook)
R — Check NEW source-summary-upstream-changed (HEAD-check, weekly cadence — skip on demand if rate-limited)
```

Checks for contradictions and terminology collisions are **deferred to v2** — call out in report footer.

---

## Step A — Frontmatter shape (ERROR)

For each `wiki/source-summary/*.md`:
- `subpages` AND `parent-slug` both present → ERROR `frontmatter-shape`: cannot be both umbrella and sub.
- `subpages` AND (`companion-urls` OR `raw-files`) → ERROR: umbrella cannot also be unified.
- `parent-slug` AND (`companion-urls` OR `raw-files`) → ERROR: sub cannot also be unified.

For `wiki/overview.md`: missing or null `sources:` → WARN.

(This duplicates hook check `shape-conflict`; lint surfaces existing violations even when the hook didn't see the save.)

## Step B — Citation path format (ERROR)

Scan body for any markdown link that points into `raw/`:
- From `_wiki/source-summary/<slug>.md` → must use `../raw/<type>/<slug>.md` form
- From `_wiki/pages/<slug>.md` → must use `../raw/<type>/<slug>.md` form
- From `_wiki/overview.md` → must use `raw/<type>/<slug>.md` form

Anything else (`/raw/...`, absolute paths, `raw/...` from a sub-folder) → ERROR `citation-path`.

## Step C — Stale propagation (INFO)

For each wiki page with `builds-on:` non-empty:
- For each cross-zone target in `builds-on:`, read its frontmatter `last-updated`.
- If any target's `last-updated > self.last-reviewed` → INFO `stale-propagation`: *"page builds-on `<target>` updated <N> days after last review."*

This propagation-based check supersedes a fixed-day-count threshold — staleness fires when canonical truth advances, not when an arbitrary calendar window elapses.

## Step D — Auto-fix: wiki-index-refresh

If `auto_fix.whitelist` includes `wiki-index-refresh`:
```
python .claude/scripts/refresh_wiki_index.py --quiet
```
Capture the script's summary line. If it changed anything, record an `auto_fixed: ['wiki-index-refresh: <summary>']` entry.

## Step E — Orphans (WARN)

Build inbound-link map: every `[[wikilink]]` in body and frontmatter of every wiki page (and `overview.md`).
Page P is an orphan if:
- No other page contains `[[<P-slug>]]` AND
- `last-updated > thresholds.orphan-grace-days` ago.

Excluded: `index.md` (root, no inbound by design). Included: `overview.md`, `log.md` (must be linked from index — but since index is regenerated, this is informational rather than enforceable).

## Step F — Citation coverage (ERROR/WARN)

Each wiki page (`pages/` + `source-summary/`) MUST contain a banner citation immediately after its summary paragraph. If missing → ERROR `citation-banner-missing`.

`overview.md` SHOULD wikilink at least one source page in its body. If not → WARN `overview-no-sources`.

## Step G — Missing cross-references (WARN)

For each page P, scan body for occurrences of any **known-slug** that isn't already inside a `[[wikilink]]` or markdown link. Match is case-insensitive verbatim against the slug or its frontmatter `name:`.

If a source page has empty `references: []` AND Step G found candidates → consolidate into one finding per page: WARN `missing-references`.

Don't infer or expand abbreviations. Casual mentions don't count.

## Step H — Queue consistency (WARN)

In `queue.md`:
- `- [x]` line under `## Pending` → WARN `queue-checked-but-pending`.
- `- [ ]` line under `## Completed` → WARN `queue-unchecked-but-completed`.
- Duplicate URL across Pending+Completed → WARN `queue-duplicate-url`.

## Step I — Split-product source pages (WARN)

Build `cluster → [{slug, source-url, has_companion_urls}]` from source-summary pages. Skip umbrellas (slug == cluster slug AND has `subpages`). Skip subs (have `parent-slug`).

For each cluster with ≥2 entries and **no** unified entry (no `companion-urls`):
- Classify entries: `source-url` matching `https://github.com/<org>/<repo>` (no path suffix) is a github source; otherwise web.
- If group has BOTH github AND web sources → WARN `split-product`: *"cluster `<X>` has separate web (`<web-slug>`) and github (`<gh-slug>`) source-summary pages; consolidate via `/wiki remove <gh-slug>` then re-add the web URL with companion-fetch enabled."*

Not auto-fixed — consolidation is destructive.

## Step J — Parent-child consistency (ERROR)

Build `umbrella_subs: umbrella_slug → set(subpages)` and `sub_parents: sub_slug → parent_slug`.

For each (umbrella, listed_subs):
- For each `<sub>` in listed_subs: `_wiki/source-summary/<sub>.md` MUST exist AND its `parent-slug:` MUST equal umbrella → else ERROR `parent-child-broken`.

For each (sub, parent):
- `_wiki/source-summary/<parent>.md` MUST exist AND list `<sub>` in `subpages:` → else ERROR `parent-child-broken`.

## Step K — Duplication-vs-data-point (WARN)

For each wiki page with `builds-on:` cross-zone targets, read each target. If the wiki page body contains paragraphs that semantically restate content from the target, → WARN `duplication-vs-data-point`: *"page restates content from `<target>`; replace the restated paragraph with `[<text>](<../target.md>)` to link rather than duplicate."*

**Implementation (P4):** [`.claude/scripts/_wiki_lint.py`](../../scripts/_wiki_lint.py). Mechanical token-Jaccard at paragraph granularity. Default threshold `0.5` (configurable via `_wiki/.config.yml` → `thresholds.duplication-jaccard`). Stopwords filtered; paragraphs with fewer than 8 content tokens skipped to avoid noise on glossary entries. Each match emits a `Finding` with the wiki paragraph, the target paragraph, and the score. False positives are accepted at WARN severity — the rule is "if it looks like a restatement, ask the human."

API:

```python
from _wiki_lint import lint_page, detect_duplication, jaccard
findings = lint_page(wiki_path, builds_on_paths, threshold=0.5)
```

Tests: `test_wiki_stubs.py::WikiDuplicationLintDecisionTests` exercises the helper, the stopword filter, and obvious-restatement detection.

## Step L — Coverage gap (INFO; queries `_inbox/`)

Build the set of active data points (`docs/*.md` with `type` ∈ {context, process, policy, reference, playbook} AND `status: active`).

For each data point:
- Build a "covered-by-wiki" indicator: any wiki page with this data point in `builds-on:`.
- Count occurrences in `_inbox/*.md` content (rough keyword match against the data point's `name:` or filename).

If `inbox_count >= 3` AND `not covered-by-wiki` → INFO `coverage-gap`: *"data point `<name>` mentioned in <N> inbox capture(s) but no wiki page builds-on it. Candidate for a how-to or runbook."*

## Step M — Cluster mismatch (WARN)

For each wiki page:
- If `cluster:` matches none of its `builds-on:` data points' `cluster:` values → WARN `cluster-mismatch`: *"wiki page cluster `<X>` doesn't match any builds-on cluster (`<Y>`, `<Z>`)."*
- Skip when the page has no `builds-on:` (e.g. glossary).
- If `clusters.allow-cluster-not-in-source: false` AND wiki cluster not in `docs/document-index.md` → WARN `cluster-not-in-index`. (Default v1 = true; this WARN is silent unless schema is tightened.)

## Step N — Reference-format mismatch (ERROR; also enforced by hook)

Re-run the hook's check across all pages — catches files saved before the hook was active. See `wiki-zone.md` Reference format rule.

## Step O — Forbidden-builds-on-target (ERROR; also enforced by hook)

For each wiki page, for each path in `builds-on:`:
- For each forbidden root in `forbid-builds-on-paths` (default: `_planned/`, `_inbox/`, `_archive/`):
  - If path contains the forbidden root → ERROR `forbidden-builds-on-target`.

## Step P — Provenance checks

For each Path B page (any `pages/*.md` or non-source-summary `source-summary/*.md`):
- `provenance:` block missing → ERROR `provenance-required`.
- `provenance.kind = local-document` AND `provenance.source` references a local path that does not exist on disk → INFO `provenance-source-missing`.
- `provenance.kind = inbox-promotion` AND `provenance.source` still exists in `_inbox/` (the original wasn't deleted, even though the user chose to delete) → WARN `provenance-inbox-not-deleted`.

## Step Q — Schema violation (ERROR; also enforced by hook)

Re-run hook checks: page-type registered? page-type-specific required-fields present? Schema-version drift?

## Step R — Source-summary upstream changed (INFO; rate-limited)

For each `source-summary/*.md` page:
- If `last-fetched < (today - thresholds.stale-threshold-days)` AND HEAD-check confirms upstream content hash changed → INFO `source-summary-upstream-changed`.

On `/wiki lint` direct invocation (vs scheduled `wiki-source-refresh` job): only HEAD-check pages whose `last-fetched` exceeds threshold. Cap at 20 HEAD requests per invocation to bound cost; if the cap is hit, note in report footer and continue.

---

## Output report

```
Lint report — <domain> wiki
{{TODAY}} | <N> pages | 18 active checks (#2, #6 deferred to v2)

ERRORs (<count>)
  [<check-id>]  <file>:<line>  <message>

WARNs (<count>)
  [<check-id>]  <file>:<line>  <message>

INFOs (<count>)
  [<check-id>]  <file>  <message>

Auto-fixes applied (<count>):
  - <description>

Deferred (v2): contradictions (#2), terminology collisions (#6)

Summary: <N> ERROR, <N> WARN, <N> INFO — <N> auto-fix(es) applied
```

Omit empty severity sections (don't print `ERRORs (0)`). If no findings and no auto-fixes: print `All checks passed.`

---

## Git policy

No agent commits — even after auto-fixes. The human reviews `git diff` and commits. See SKILL.md.

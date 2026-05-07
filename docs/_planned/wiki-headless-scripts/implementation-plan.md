---
name: "Wiki-job headless scripts — Implementation Plan"
type: playbook
cluster: "Framework Evolution"
version: 0.1.0
status: planned
created: 2026-05-05
last-updated: 2026-05-05
authority-docs:
  - .claude/skills/schedule-dispatcher/references/job-wiki-stale-propagation.md
  - .claude/skills/schedule-dispatcher/references/job-wiki-source-refresh.md
  - .claude/skills/schedule-dispatcher/references/job-wiki-graveyard.md
  - .claude/skills/schedule-dispatcher/references/job-wiki-coverage-audit.md
  - docs/_bcos-framework/architecture/wiki-zone.md
  - docs/_bcos-framework/architecture/typed-events.md
  - docs/_planned/autonomy-ux-self-learning/implementation-plan.md
follows-up-on: docs/_planned/autonomy-ux-self-learning/
---

# Wiki-job headless scripts — Implementation Plan

> **Status:** planned (not started). Follow-up to `autonomy-ux-self-learning`. Bundles the four wiki maintenance jobs into standalone Python scripts the dashboard can fire from `[Run now]` cards (instead of falling back to the "Run via chat" hint).

## 1. Why

Today the dashboard's `[Run now]` button only does work for two of the ten maintenance jobs:

| Runs end-to-end from the dashboard | Falls through to "Run via chat" |
|---|---|
| `index-health` | `audit-inbox` (judgement — needs Claude) |
| `auto-fix-audit` | `daydream-lessons` (judgement) |
|  | `daydream-deep` (judgement) |
|  | `architecture-review` (judgement) |
|  | **`wiki-stale-propagation`** *(mechanical — should be headless)* |
|  | **`wiki-source-refresh`** *(mechanical — should be headless)* |
|  | **`wiki-graveyard`** *(mostly mechanical — should be headless)* |
|  | **`wiki-coverage-audit`** *(mechanical — should be headless)* |

The four wiki jobs are all mechanical (frontmatter scans, HEAD/ETag checks, link validation) — there's no judgement step that requires Claude in the loop for the *detection* phase. Today the user clicks `[Run now]` on Wiki staleness and gets `Tell Claude in chat: run the wiki-stale-propagation job`, which works but is needlessly indirect.

Goal: the user clicks `[Run now]` on any of these four cards and the dashboard runs the actual scan, writes the results to `daily-digest.json`, and the cockpit refreshes with new findings within seconds.

## 2. Scope

**In:**
- Four standalone Python scripts under `.claude/scripts/`:
  - `run_wiki_stale_propagation.py`
  - `run_wiki_source_refresh.py`
  - `run_wiki_graveyard.py`
  - `run_wiki_coverage_audit.py`
- A small shared library `.claude/scripts/_wiki_job_runner.py` for diary append + sidecar write
- Dashboard wiring: each script registered in `bcos-dashboard/run.py::SCRIPTABLE`
- Each script emits a typed-event sidecar entry conforming to `typed-events.md` v1.0.0 (`finding_type` enum already covers all four jobs' emissions)
- Per-job verdict + action items written into the daily digest

**Out:**
- The four judgement jobs (`audit-inbox`, daydreams, `architecture-review`) — those genuinely need Claude.
- New finding-type IDs — the existing 9 wiki-related types in `typed-events.md` cover everything these scripts surface.
- Auto-fixes — these scripts are detection-only. Whitelisted auto-fixes still flow through the dispatcher.
- A new `daily-digest.json` writer — extend the existing `digest_sidecar.py::write_sidecar()` from autonomy-ux-self-learning Phase 1.

## 3. The four scripts

### 3.1 `run_wiki_stale_propagation.py`

**What it does.** For every wiki page with a `builds-on:` frontmatter list, compare:

- Each `builds-on` source's last `last-updated` timestamp
- The wiki page's own `last-reviewed` timestamp

If any source was updated *after* the page was reviewed, emit a `stale-propagation` finding.

**Inputs:**
- `docs/_wiki/pages/*.md` (all pages with `builds-on:`)
- The source files referenced by each `builds-on` entry

**Outputs:**
- One `stale-propagation` finding per affected page, with `finding_attrs: {wiki_file, source_file, source_updated_date, last_reviewed_date}`
- Verdict: `green` if zero findings; `amber` otherwise; `red` if any page has ≥3 stale sources (signals a cluster-wide drift event)

**Estimated:** ~80 LOC. The frontmatter parser already exists in `_wiki_yaml.py`. Most of the work is the date math + sorting.

### 3.2 `run_wiki_source_refresh.py`

**What it does.** Two-tier check on every `source-summary` page:

1. **Quick check** at `last_fetched + (refresh_threshold_days / 4)`: HTTP HEAD to the upstream URL. Compare `etag` / `last-modified` / `content-length` against the page's stored values. If mismatch → emit `source-summary-upstream-changed`.
2. **Full refresh** at `last_fetched + refresh_threshold_days`: emit `refresh-due`.

**Inputs:**
- `docs/_wiki/source-summary/*.md` (pages with `source-url:` + `last-fetched:` + `etag:`/`last-modified:`/`content-length:`)
- Network access (HTTP HEAD requests, polite — 3-second timeout, single thread)

**Outputs:**
- Per source: at most one finding — either `source-summary-upstream-changed` (quick-check tier) or `refresh-due` (full tier). The job never *performs* the refresh; that's the user's call via the existing `bcos-wiki refresh --slug` flow.
- Verdict: `green` if all sources fresh; `amber` if any quick-check or refresh-due finding; `red` if any source returned a 4xx/5xx (signals a dead URL).

**Risks:**
- Network calls can be slow or hang — strict 3s timeout per HEAD, total budget cap of 60s for the whole run.
- Some hosts disallow HEAD; fall back to a 1-byte ranged GET on 405. Document in the script.

**Estimated:** ~150 LOC. Stdlib `urllib.request` only — no `requests` dependency.

### 3.3 `run_wiki_graveyard.py`

**What it does.** Three checks on every wiki page:

1. **Stale review.** `last-reviewed` older than `graveyard_days` (default 365) → `graveyard-stale`.
2. **Orphan.** No inbound wiki links AND no edits within `orphan_grace_days` (default 90) → `orphan-pages`.
3. **Retired page-type.** Frontmatter `page-type:` is in the schema's retired list → `retired-page-type`.

**Inputs:**
- `docs/_wiki/pages/*.md`, `docs/_wiki/source-summary/*.md`
- Wiki schema (the canonical retired-page-types list)
- A reverse-link index of `[wiki:slug]` references across all wiki pages

**Outputs:**
- One finding per affected page (a single page can produce multiple findings if it ticks multiple boxes; that's fine).
- Verdict: `green` / `amber` / `red` depending on aggregate counts.

**Estimated:** ~120 LOC. The reverse-link index is the most novel piece — cache it in-memory per run.

### 3.4 `run_wiki_coverage_audit.py`

**What it does.** Cross-zone scan for coverage gaps:

1. **Data points lacking explainers.** For every active data point in `docs/*.md`, check if any wiki page lists it in `builds-on`. If not → `coverage-gap-data-point`.
2. **Inbox terms.** Cheap term-frequency scan over `docs/_inbox/*.md`. Terms appearing in ≥3 inbox files with no wiki page covering them → `coverage-gap-inbox-term`.
3. **Cluster mismatch.** Wiki pages whose `cluster:` value isn't present in `document-index.md` → `cluster-mismatch`.

**Inputs:**
- `docs/document-index.md` (or `docs/.context-index.json` if available)
- `docs/_wiki/pages/*.md`, `docs/_inbox/*.md`
- Active data points list (from frontmatter scan)

**Outputs:**
- One finding per gap. Verdict: always `green` or `amber` — coverage gaps are suggestions, never critical.

**Estimated:** ~100 LOC. The term-frequency check has the most knobs to tune — start with conservative defaults (≥3 mentions, ≥4 chars, stopword-list filtered).

## 4. Shared library — `_wiki_job_runner.py`

Every script ends with the same boilerplate: produce findings, write a per-job entry to the diary, and merge findings into `daily-digest.json` so the cockpit can render them. Factor out:

```python
def run_wiki_job(*, job_id: str, findings: list[dict], notes: str = "",
                 auto_fixed: list[str] = (), trigger: str = "scheduled") -> dict:
    """Append diary entry + merge findings into the digest sidecar.

    Returns a result dict mirroring the dispatcher's per-job contract:
        {verdict, findings_count, auto_fixed, actions_needed, notes}
    """
```

This avoids divergent diary-write behaviour across the four scripts and keeps the sidecar merge logic in one place.

## 5. Dashboard wiring

In `bcos-dashboard/run.py::_post_run_job_now`, extend the `SCRIPTABLE` map:

```python
SCRIPTABLE = {
    "index-health":           ["python", ".claude/scripts/build_document_index.py"],
    "auto-fix-audit":         ["python", ".claude/scripts/auto_fix_audit.py"],
    # New (this plan):
    "wiki-stale-propagation": ["python", ".claude/scripts/run_wiki_stale_propagation.py"],
    "wiki-source-refresh":    ["python", ".claude/scripts/run_wiki_source_refresh.py"],
    "wiki-graveyard":         ["python", ".claude/scripts/run_wiki_graveyard.py"],
    "wiki-coverage-audit":    ["python", ".claude/scripts/run_wiki_coverage_audit.py"],
}
```

Plus widen `single_repo._HEADLESS_RUNNABLE` to include the four wiki jobs once their scripts ship. The cockpit cards then auto-flip from "Run via chat" to "Run now".

## 6. Testing

For each script:

1. **Unit tests** (`.claude/scripts/test_run_wiki_<job>.py`): seed a small fixture under `.claude/quality/fixtures/wiki_<job>/`, run the script with `BCOS_REPO_ROOT` pointing at the fixture, assert findings shape + verdict.
2. **Sidecar contract test** (extend `test_finding_type_coverage.py`): every finding emitted by these scripts uses a canonical `finding_type` ID.
3. **Wiring test** (extend `test_card_coverage.py`): every wiki finding-type renders as a shape-compliant card.
4. **End-to-end smoke** (manual, post-merge): run each script against the real repo, verify the digest sidecar updates, click `[Run now]` on the dashboard and confirm cards refresh.

## 7. Rollout

| Step | Output |
|---|---|
| 1 | `_wiki_job_runner.py` + tests |
| 2 | `run_wiki_stale_propagation.py` + tests + dashboard wiring |
| 3 | `run_wiki_graveyard.py` + tests + dashboard wiring |
| 4 | `run_wiki_coverage_audit.py` + tests + dashboard wiring |
| 5 | `run_wiki_source_refresh.py` + tests + dashboard wiring (last because of network risk) |
| 6 | Update `_HEADLESS_RUNNABLE` set; widen `auto-fix-audit` to also surface wiki-job auto-disable signals |
| 7 | FIXED END: doc-lint, integration audit, lessons capture |

Each step ships independently — the dashboard tolerates partial coverage gracefully (any job not in `SCRIPTABLE` falls through to chat-hint, which is what we have today).

## 8. Estimate

~3 days end-to-end at the discipline level used in `autonomy-ux-self-learning`:

- Day 1: shared library + stale-propagation + graveyard
- Day 2: coverage-audit + source-refresh
- Day 3: tests, dashboard wiring, fixed-end

## 9. Risks + mitigations

| ID | Risk | Mitigation |
|---|---|---|
| R-01 | `wiki-source-refresh` hangs on a slow upstream | Strict 3s timeout per HEAD; 60s total budget; abort cleanly with `error` verdict on budget exceed |
| R-02 | Reverse-link index in `wiki-graveyard` is expensive on big wikis | Cache the index in-memory per run; ship a `--max-pages` flag for very large wikis |
| R-03 | Coverage-audit term-frequency produces too many false positives | Conservative defaults (≥3 mentions, ≥4 chars, English stopwords). Document tuning knobs. |
| R-04 | Network calls hit rate limits | Single-threaded HEAD requests with a 100ms gap between calls. No batch refresh — that's still the user's call |
| R-05 | Sidecar writes race with the dispatcher | `_wiki_job_runner.write_sidecar` uses an atomic temp-file + rename; matches the existing `digest_sidecar.write_sidecar` pattern |

## 10. Open questions

- **Should these scripts also surface their findings as cockpit action cards immediately, or wait for the next dispatcher run?** Probably immediate — the user clicked Run now, they expect the cards to update without waiting until tomorrow morning. This means the script writes to `daily-digest.json` directly, merging with whatever's already there.
- **What happens if a quick-check `wiki-source-refresh` finding fires the same day as a full `refresh-due` finding for the same source?** Suppress the quick-check; the full check supersedes it.
- **Do we need a `--dry-run` flag for these scripts, similar to `auto_fix_audit.py`?** Yes — useful for testing and for the auditor to inspect what would be flagged without writing.

## 11. Out of scope (future)

- Auto-fixes inside the wiki scripts. Today the only wiki auto-fix is `wiki-archive-expired-post-mortem` (handled by the dispatcher's existing whitelist). Adding auto-fixes here would change the safety surface — keep detection-only for v1.
- Replacing the dispatcher's invocation of these jobs. The dispatcher still drives the daily run; these scripts are an additional click-to-run path. The two paths produce the same finding types and write to the same diary/sidecar.
- Cross-repo (portfolio) coverage. Stays a single-repo scope until the per-repo case is rock solid.

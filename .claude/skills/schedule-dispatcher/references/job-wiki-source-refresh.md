# Job: wiki-source-refresh

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** weekly
**Nature:** two-tier source freshness check for `source-summary` pages

---

## Purpose

Keep URL-backed source summaries fresh without refetching expensive sources too
often. Per D-05, this job has two tiers:

- **Quick check:** HEAD-only or equivalent metadata check at
  `stale_threshold_days / 4`.
- **Full refresh:** refresh-must-rediscover at `stale_threshold_days`.

The quick check only asks whether upstream changed. The full refresh re-runs the
capture protocol and must rediscover source shape before writing.

---

## Steps

### 1. Check whether the wiki zone exists

If `docs/_wiki/source-summary/` does not exist, emit green with zero findings
and note that the wiki source-summary folder is absent.

### 2. Read thresholds

Read `thresholds.stale-threshold-days` from `docs/_wiki/.schema.yml`, falling
back to the framework template. Default to `30` if the field is missing.

Compute:

- `quick_threshold_days = max(1, stale-threshold-days / 4)`
- `full_threshold_days = stale-threshold-days`

### 3. Validate schema before network work

Run:

```text
python .claude/scripts/wiki_schema.py validate
```

If validation fails, emit `verdict: red` and put each schema issue in
`actions_needed`.

### 4. Quick-check eligible sources

For each `page-type: source-summary` page whose `last-fetched` is at least
`quick_threshold_days` old but less than `full_threshold_days` old:

1. Run a HEAD-only or equivalent cheap upstream check against `source-url`.
2. If unchanged, record no finding.
3. If changed, emit an INFO action item:
   `source-summary-upstream-changed: <page> changed upstream; full refresh due at <date>`.

Rate-limit checks: do not check more than 20 sources per run unless the user
explicitly asked for a full sweep.

### 5. Full refresh eligible sources

For each `source-summary` page whose `last-fetched` is at least
`full_threshold_days` old:

1. Do not silently overwrite the page.
2. Emit an action item to run `/wiki refresh <slug>`.
3. The refresh flow must follow `refresh.md`: rediscover source type, re-fetch,
   compare, and only write after confirmation when content changes.

### 6. Queue-marking auto-fix

If a Path A ingest or refresh has just completed and the matching
`docs/_wiki/queue.md` line is still unmarked, the job may apply
`wiki-mark-queue-ingested` when that ID is whitelisted.

The fix is limited to appending an HTML comment such as
`<!-- ingested 2026-05-04 -->` to an exact queue URL line already represented by
a source-summary page.

### 7. Determine verdict

- `green` — no upstream changes and no due full refreshes.
- `amber` — upstream changed or full refresh due.
- `red` — schema validation failed or a required `source-url` is missing.
- `error` — network/check logic crashed.

### 8. Emit result

```json
{
  "verdict": "amber",
  "findings_count": 3,
  "auto_fixed": ["wiki-mark-queue-ingested in docs/_wiki/queue.md"],
  "actions_needed": [
    "source-summary-upstream-changed: docs/_wiki/source-summary/vendor-api.md changed upstream",
    "refresh-due: docs/_wiki/source-summary/sdk-docs.md last-fetched 42 days ago; run /wiki refresh sdk-docs"
  ],
  "notes": "Checked 12 source-summary pages; quick threshold 7 days, full threshold 30 days."
}
```

---

## Auto-fixes allowed

- `wiki-mark-queue-ingested`

No source-summary content rewrite is auto-fixable.

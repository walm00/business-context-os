# Job: wiki-canonical-drift

**Invoked by:** `schedule-dispatcher` skill
**Default cadence:** daily
**Nature:** mechanical scan — detect canonical docs that newer wiki captures suggest may be stale
<!-- emits-finding-types: machine-readable; consumed by .claude/scripts/test_finding_type_coverage.py. Schema: docs/_bcos-framework/architecture/typed-events.md -->
```yaml
emits-finding-types:
  - wiki-canonical-drift-suggestion
```

---

## Purpose

Find canonical `docs/*.md` data points that **may be stale**, based on numeric
divergence between newer wiki captures and older canonical claims. This is
schema 1.2 Class D from `_wiki_triage.classify()`, run as a daily mechanical
sweep instead of just at ingest time.

Concretely: for every wiki page with `authority: external-reference` that
declares a `builds-on:` canonical doc, the job compares the wiki page's
numeric facts against the canonical doc's numeric facts. If they diverge AND
the canonical doc's `last-updated` is older than `STALE_CANONICAL_DAYS`
(180 days, ≈ 6 months), the job emits `wiki-canonical-drift-suggestion`.

The job NEVER edits canonical `docs/*.md` files. It only emits findings into
the morning digest sidecar. The user reads, decides, and updates the
canonical doc manually (or asks Claude to do it). Mechanical-first per D-09.

This is the **maintenance-time** sibling of the ingest-time Class D emission
(`bcos-wiki/ingest.md` Step 7.5). Ingest catches drift as it lands; this job
catches drift that accumulated before triage was wired in or after a canonical
doc passed its 6-month staleness threshold.

---

## Steps

### 1. Check whether the wiki zone exists

If `docs/_wiki/` does not exist, emit:

```json
{
  "verdict": "green",
  "findings_count": 0,
  "auto_fixed": [],
  "actions_needed": [],
  "notes": "Wiki zone not enabled; canonical-drift skipped."
}
```

### 2. Run the headless script

```text
python .claude/scripts/run_wiki_canonical_drift.py --root <repo-root> --sidecar-dir <dispatcher-sidecar-dir>
```

The script walks every wiki page under `docs/_wiki/source-summary/` and
`docs/_wiki/pages/`, calls `_wiki_triage.classify()` with cluster-scoping
disabled (canonical drift is inherently cross-page-cross-cluster — the
canonical doc may be in any cluster), filters for Class D findings only,
and writes a sidecar JSON entry per finding.

### 3. Aggregate and verdict

| Class D findings | Verdict |
|---|---|
| 0 | `green` |
| 1–5 | `amber` |
| 6+ | `amber` (still amber — Class D is INFO; never escalates to red) |

### 4. Surface to digest

Each finding renders into the digest as one bullet:

```
[INFO] Canonical doc may be stale: <canonical-file> (last-updated <N> days ago).
       Newer wiki capture: <wiki-file> reports diverging values.
       Recommend reviewing <canonical-file>.
```

The dashboard cockpit groups Class D findings under "Canonical drift to review"
with a per-canonical-doc count.

---

## Idempotency

The script is idempotent on stable input. Re-running on the same wiki +
canonical state produces the same set of findings. No state file is written;
each run reads frontmatter + body afresh.

If the user has updated the canonical doc since the last run (`last-updated`
bumped past `STALE_CANONICAL_DAYS`), the finding clears automatically on the
next run.

---

## What this job does NOT do

- Does NOT auto-edit canonical `docs/*.md` files.
- Does NOT auto-edit wiki pages (Class A annotations are ingest-time only).
- Does NOT escalate to Class C — that's reserved for two canonical-process
  pages; canonical-drift is Class D (canonical doc + external-reference wiki).
- Does NOT consider non-numeric content divergence — those signals are
  noisier and require LLM (deferred per D-09).
- Does NOT modify `wiki-stale-propagation` job behavior — that's a separate
  signal (canonical doc updated AFTER wiki page review). Different triggers,
  separate findings, by design.

---

## Auto-fixes

None. This job emits `INFO` findings only. The user (or a future skilled
helper) decides whether to update the canonical doc.

The complementary auto-fix IDs that DO exist are emitted by ingest-time
triage, not by this maintenance job:

- `wiki-supersession-link-add` — ingest-time Class B auto-link
- `wiki-authority-annotation-add` — ingest-time Class A auto-annotation

---

## Related

- Triage detector: `.claude/scripts/_wiki_triage.py`
- Confidence scoring: `.claude/skills/bcos-wiki/references/triage-confidence.md`
- Schema 1.2: `docs/_bcos-framework/architecture/wiki-zone.md` "Authority semantics" + "Temporal semantics"
- Sibling jobs: `job-wiki-stale-propagation.md`, `job-wiki-source-refresh.md`, `job-wiki-graveyard.md`, `job-wiki-coverage-audit.md`

---
name: Wiki Headless Scripts
description: Architecture, contract, and feedback loop for the four wiki maintenance scripts that bypass chat for cron + dashboard execution.
type: architecture
domain: framework
exclusively-owns: wiki-headless-execution-contract
last-updated: 2026-05-06
version: 1.0.1
created: 2026-05-05
---

# Wiki Headless Scripts

The wiki zone has four maintenance jobs (stale-propagation, source-refresh, graveyard, coverage-audit). Each one has TWO execution paths: a **chat-driven** path that reads the matching `references/job-wiki-*.md` and executes step-by-step, and a **headless** path that runs a Python script in subprocess. This file pins the headless contract.

For the chat-driven contract see [`schedule-dispatcher/SKILL.md`](../../../.claude/skills/schedule-dispatcher/SKILL.md). For the typed-event sidecar shape every script writes see [`typed-events.md`](./typed-events.md). For the wiki zone itself see [`wiki-zone.md`](./wiki-zone.md).

---

## Why headless exists

The chat path is correct, observable, and slow. Three triggers want speed and determinism:

- **Cron** — the daily scheduled task should not require a chat session.
- **Dashboard "Run now"** — `POST /api/job/run` invokes the script in a 120-s subprocess; result lands in the next poll.
- **CI / pre-commit** — `BCOS_OFFLINE=1 python .claude/scripts/run_wiki_<job>.py` is a one-line freshness check.

The chat path is the fallback. The job-spec markdown is still the contract; the script is one implementation of it.

---

## File layout

```text
.claude/scripts/
  _wiki_job_runner.py            # shared: diary append + sidecar merge
  _wiki_yaml.py                  # shared: frontmatter parser
  run_wiki_stale_propagation.py  # daily detector
  run_wiki_source_refresh.py     # weekly two-tier check
  run_wiki_graveyard.py          # monthly archive-candidate scan
  run_wiki_coverage_audit.py     # quarterly cross-zone scan
```

Every `run_wiki_*.py` script exposes the same surface:

```python
def detect_findings(root: Path) -> list[dict]: ...
def main() -> None: ...   # detect + run_wiki_job side-effects
```

`_wiki_job_runner.run_wiki_job(job_id, findings, notes, trigger, root)` is the only side-effecting helper. It computes the verdict, appends to `.claude/hook_state/schedule-diary.jsonl`, and merges into `docs/_inbox/daily-digest.json`. Re-running the same job replaces its prior findings — idempotent.

---

## Dashboard wiring

`single_repo._JOB_SCRIPTS` maps job IDs → script paths. `_can_run_headless(job_id)` checks the file exists. `collect_job_detail()` exposes `can_run_now: bool`. `POST /api/job/run` runs the matching script with `BCOS_REPO_ROOT` pinned, captures stdout/stderr, invalidates the cockpit + jobs_panel caches.

To add a new headless job: add to `_JOB_SCRIPTS`, drop the script, the dashboard picks it up automatically.

---

## Tests

Located alongside the implementations (gitignored — `.claude/scripts/test_*.py` runs locally only):

| Suite | Tests | Coverage |
|---|---|---|
| `test_run_wiki_stale_propagation.py` | 7 | no-zone, up-to-date, 1-stale-amber, 3-stale-red, unresolvable-source, missing-last-reviewed, full integration |
| `test_run_wiki_graveyard.py` | 10 | guards, graveyard-stale, orphan, retired-page-type, integration |
| `test_run_wiki_coverage_audit.py` | 6 | no-zone, gap-emitted, gap-suppressed, inbox-skip, cluster-mismatch positive/negative |
| `test_run_wiki_source_refresh.py` | 5 | no-folder, refresh-due, fresh, quick-range-offline, wrong-page-type |

Run individually with `python .claude/scripts/test_run_wiki_<job>.py -v`. All synthesize a tempdir repo and pin `BCOS_REPO_ROOT` so they never touch real docs. CI sweep: loop the four files, fail if any returns non-zero.

**Gaps to close once feedback arrives**: integration test for `POST /api/job/run`, smoke test for `_can_run_headless()` on a clean clone, golden-file test for the merged sidecar shape.

---

## Documentation entry points

| Audience | Read |
|---|---|
| User running a job manually | The `## Preferred execution path (headless)` block at the top of each `references/job-wiki-*.md` |
| Operator wiring a new job | This file's *File layout* + *Dashboard wiring* sections |
| Auditor checking the contract | [`typed-events.md`](./typed-events.md) for sidecar shape; the test suites for behaviour |
| Schedule-dispatcher (chat) | The fallback steps under each job spec — the script handles them in code |

The job-spec markdowns are now contract reference + fallback playbook, not the primary path.

---

## Measurement loop

Every emitted finding lands in three places: the diary (audit log), the sidecar (today's view), and — once a user acts on it — `resolutions.jsonl`. The metrics that matter:

| Metric | Where | What it tells you |
|---|---|---|
| `findings_per_run` by job | `schedule-diary.jsonl` | Detector tuning — high counts on a quiet zone = noise |
| `verdict` distribution | `schedule-diary.jsonl` | Are reds rare enough to be meaningful? |
| `action_taken` ratio | `resolutions.jsonl` | What fraction of findings get acted on vs. dismissed |
| `reversal_rate` per finding_type | `resolutions.jsonl` (P6 auditor) | False-positive rate — high = detector is wrong |
| `time_to_resolution` | `resolutions.jsonl` (action ts − finding ts) | Are findings actionable or just noise users ignore? |

The `auto-fix-audit` job (Friday safety brake) already reads reversal-rate. The same auditor will eventually drive the wiki-script tuning loop.

---

## Iteration plan (post-feedback)

After two full cycles (≈ 4 weeks for stale-propagation/source-refresh, 8+ weeks for graveyard/coverage), look at:

1. **Per-job dismissal rate.** If users dismiss > 60% of findings from a single job → detector is too aggressive.
   - Stale-propagation: tighten the lag-day window or require a minimum of 2 stale sources (lift the amber floor).
   - Coverage-audit: filter data-point gap by `type: data-point` strictly (currently flags every doc with frontmatter).
   - Inbox term mining: replace substring match with a proper repetition counter (job spec asks for "repeated" — current impl flags first occurrence).
2. **Time-to-resolution by finding_type.** Findings that sit unresolved > 14 days suggest the action-card UX is unclear, not that the detection is wrong.
3. **Per-zone calibration.** The default thresholds (365-day graveyard, 30-day stale, 365-day orphan-grace) come from the schema template. If a user keeps overriding them in `_wiki/.schema.yml`, the defaults are wrong.
4. **Headless vs chat divergence.** The parity test (`test_dispatcher_parity.py`) locks the contract: every headless finding must use a canonical `finding_type`, render into a shape-compliant Card, dispatch to a real handler, and produce a sidecar matching the fixture shape. Re-run the test if either path changes.

When a tuning need is confirmed, prefer adjusting the **threshold in `_wiki/.schema.yml`** over editing the detector — the schema is user-tunable; the detector should be policy-stable.

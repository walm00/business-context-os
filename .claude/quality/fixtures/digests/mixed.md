# Daily Maintenance Digest — 2026-05-12

**🔴 red** · 5 scheduled, 4 ran, 1 silent-skip · 2 repo · 1 framework · 0 auto-fixed · 8m11s

**Headline:** 1 critical: dispatcher-silent-skip on command-center-schedules-snapshot; +2 repo findings.

## ⚠️ Action needed (2)

| # | Job | File / Target | Issue | Stickiness |
|---|---|---|---|---|
| 1 | `wiki-stale-propagation` | `docs/_wiki/pages/pricing-strategy.md` | stale-propagation (16d behind) | 🔁 3rd run |
| 2 | `audit-inbox` | `docs/_inbox/2026-05-07-runaway-terminals-incident.md` | inbox aged 5 days | |

## 🔧 BCOS framework issues (1)

> **Acknowledge-only.** These are framework bugs reported for transparency. Do not attempt to fix in this repo — `update.py` would overwrite. The framework owner is responsible for these.

| # | Finding | Detail | First seen |
|---|---|---|---|
| 1 | `dispatcher-silent-skip` | `command-center-schedules-snapshot` produced no completion record | 2026-05-12 |

## 📊 Jobs (5)

| Job | | Findings | Note |
|---|---|---|---|
| command-center-schedules-snapshot | ⚠️ | 1 | silent-skip |
| audit-inbox | 🟡 | 1 | |
| wiki-stale-propagation | 🟡 | 1 | 🔁 stuck (3x) |
| index-health | 🟢 | 0 | |
| wiki-source-refresh | 🟢 | 0 | |

---
Run at 2026-05-12T09:00:00Z · `.claude/hook_state/schedule-diary.jsonl`
Auto-commit: ✗ skipped (red verdict — block_on_red=true)

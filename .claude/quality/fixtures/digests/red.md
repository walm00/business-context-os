# Daily Maintenance Digest — 2026-05-05

**Overall:** 🔴 red — 6 jobs ran, 1 auto-fix, 5 action items.

## ⚠️ Action needed (5)

### 1. broken xref: docs/strategy/2026-roadmap.md → docs/_archive/old-okrs.md
Cross-reference points to archived document. Source-of-truth violation: active doc must not depend on `_archive/`. Recommend: relink to canonical source or remove reference.

### 2. broken xref: docs/customer-research/personas.md → docs/_inbox/raw-interviews.md
Cross-reference points to `_inbox/` (raw, untriaged). Recommend: triage target file first, then relink.

### 3. orphan page: docs/_wiki/pages/legacy-pricing.md
Page has no inbound `builds-on` references and no source-summary anchor. Recommend: archive or attach to a canonical data point.

### 4. graveyard stale: docs/_archive/2024-q3-positioning.md (412 days)
Archived item past 365-day graveyard threshold. Recommend: move to `.private/_planned-archive/` or delete.

### 5. coverage gap: data point "ICP" (docs/strategy/icp.md) has no wiki explainer
Canonical data point lacks a `_wiki/pages/` explainer. Recommend: stub a page or mark non-explainable in frontmatter.

## 🔧 Auto-fixed (1)

- frontmatter-missing-last-updated: docs/strategy/objectives.md (set to 2026-05-04)

## Per-job summary

### audit-inbox — 🟢 green
0 items aged past triage threshold.

### index-health — 🔴 red
2 broken cross-references; 1 orphan wiki page.

### wiki-coverage-audit — 🔴 red
1 canonical data point missing wiki explainer.

### wiki-graveyard — 🟡 amber
1 archived item past 365-day threshold.

### wiki-stale-propagation — 🟢 green
0 stale builds-on chains.

### wiki-source-refresh — 🟢 green
0 sources past refresh-due window.

---
_Run at 2026-05-05T07:00:00Z. Full history: .claude/hook_state/schedule-diary.jsonl_

# Session Diary

Append-only running notes. Most-recent on top.

---

## 2026-05-11 — Smart-trigger refactor for cross-repo retrieval

**Branch**: `claude/review-claude-md-onboarding-tphvi` (continues 2026-05-10 work)

**Shipped**: Replaced the blunt-instrument cross-repo fallthrough (commit `168ed6e`) with a three-stage filter. Local search across all zones in this repo always wins; cross-repo is consulted only via a cheap metadata-only peek when local is insufficient; sibling deep-fetch happens only when the peek points to a clear winner. Marginal peeks now emit a `cross-repo-suggestions` envelope field so the calling agent can ask the user "want me to look at sibling X?" without the framework paying the cost of a full sibling-corpus BM25 pass.

**Hierarchy locked** (per user directive): always this-repo first, all zones; cross-repo as last resort. Encoded mechanically:
- Local search ranks all zones together via existing role-boost (canonical > derived > evidence > future > historical).
- Cross-repo gate fires on `is_local_insufficient` (mechanical OR-of-signals).
- Default `miss_signals` flipped from `["zero-hit"]` (Day 1) to `["zero-hit", "low-coverage"]` (today) per Gate 1 user decision.
- Explicit `--cross-repo` still bypasses peek → deep-fetch (manual override unchanged).

**Envelope additions**:
- `cross-repo-suggestions` — NEW. Present when peek = marginal. Lists per-sibling metadata matches with `top-citations`, `match-count`, `authoritative-match-count`, `reasons`.
- `cross-repo-status.trigger` — expanded vocabulary: `local-sufficient` (peek not invoked), `peek-empty` (peek ran, no matches), `peek-marginal` (suggestions emitted, no deep-fetch), `auto-fallthrough` (peek-strong → deep-fetch), `explicit-flag`, `explicit-no`, `not-opted-in`.
- `cross-repo-status.local-insufficient-signal` — which signal fired the gate.
- Hit shape: `match-tier` + `coverage` are now always-present fields (no longer hidden behind `--explain`) so the gate evaluators don't need debug mode.

**New config knobs** in `.bcos-umbrella.json.retrieval`:
- `peek_min_strong_matches` (default 1) — # authoritative-field matches required for peek-strong
- `peek_max_strong_rivals` (default 0) — # other siblings tolerated for peek-strong (above = marginal)

**Files** (8 modified, 0 new code files, 0 fixture-doc changes needed):
- `.claude/scripts/cross_repo_fetch.py` — added `PeekResult` + `SiblingPeek`, `peek_sibling_corpora`, `is_local_insufficient`, `peek_strength`, `peek_envelope`. Extended `UmbrellaConfig`.
- `.claude/scripts/context_search.py` — rewrote `_maybe_extend_with_cross_repo` as the three-stage filter; split deep-fetch into a helper.
- `.claude/scripts/context_bundle.py` — same refactor + new `_bundle_query_tokens` helper to translate profile families into peek tokens.
- `.claude/scripts/test_cross_repo_search.py` — 2 existing tests updated for new envelope shape (more informative; no behavioral regressions); 4 new scenarios (N1–N4); 4 new unit tests for peek helpers. **23 tests, all pass.**
- `docs/_bcos-framework/architecture/cross-repo-retrieval.md` — version 1.1.0; three-stage flow diagram; peek schema + threshold defaults; expanded trigger vocab.
- `.claude/skills/context-routing/SKILL.md`, `search.md`, `bundle.md` — updated to describe the three-stage filter and the new suggestions envelope.

**Lessons captured**: L-ECOSYSTEM-20260511-020 (cheap-signal-before-expensive-merge pattern), L-ECOSYSTEM-20260511-021 (OR-vs-AND semantics for multi-signal gates).

**What still needs to happen** (out of scope, won't be done in this repo):
- Umbrella-side: the umbrella host's `umbrella-onboarding` skill should write `retrieval.auto_fallthrough: true` into each registered sibling's `.bcos-umbrella.json` by default. Once that lands, every BCOS repo registered with that umbrella will start using the smart-trigger flow automatically. User confirmed they'll handle this client-side as part of umbrella onboarding.
- Calling-agent UX: actual "should I look at sibling X?" prompting still needs wiring downstream of `cross-repo-suggestions`. The data is in the envelope waiting; consumers can opt in.

**Plan artifact**: `.claude/quality/sessions/20260511_073336_smart-trigger-refactor/` (planning + plan committed at `8f92299`).

---

## 2026-05-10 — Umbrella-aware cross-repo retrieval

**Branch**: `claude/review-claude-md-onboarding-tphvi`

**Shipped**: `/context search` and `/context bundle` are now umbrella-aware via a per-portfolio opt-in. Framework default is unchanged (bit-for-bit identical in any repo with no `.bcos-umbrella.json` or no `retrieval` block); the user flips a portfolio of related BCOS repos into "auto on local-miss" mode by adding a small `retrieval` block to their `.bcos-umbrella.json`. CLI gains `--cross-repo` / `--no-cross-repo` for one-off overrides.

**Reconciliation of intent vs. D-10 strict**: The user's portfolio intent ("auto-fall to sibling repos on local-miss") contradicts D-10 ("no auto-fallback, no hidden cost"). Resolved by per-portfolio opt-in: D-10 invariant preserved at framework level; user agency preserved per-portfolio. Captured as L-ECOSYSTEM-20260510-017.

**Key design choices** (locked in plan manifest, not re-litigated during execution):
- Cross-repo data is **pulled live** per call from sibling `context-index.json` files. No cache. Each call sees fresh sibling state.
- Local-miss = (configurable) `zero-hit` and/or `unsatisfied-zone-requirements != []`. All signals are mechanical; no LLM judgment.
- Sibling-hit citations get `<sibling-id>:<zone>:<slug>` prefix. Local citations unchanged.
- For bundle, sibling data lives in a separate top-level `cross-repo-hits` block — never folded into `by-zone` / `by-family`. Local authority preserved automatically.
- Framework consumes a minimum contract (`projects[].id/path/exposes`) from the umbrella's `projects.json`. Umbrella owns the full schema in its own onboarding skill. Forward-compatible.

**Files** (10 modified, 4 new, 15 tests added — all pass, 0 regressions):
- New: `docs/_bcos-framework/architecture/cross-repo-retrieval.md`, `.claude/scripts/cross_repo_fetch.py`, `.claude/scripts/test_cross_repo_search.py`, `.claude/scripts/fixtures/cross_repo/`
- Modified: `context_search.py`, `context_bundle.py` (both additive), context-routing skill docs, CLAUDE.md (one Retrieval Playbook row), permissions-catalog.md (one cross-repo workflows row), lessons.json (3 lessons captured).

**Finding (surfaced for the user)**: `test_context_search.ContextSearchEscalationTests.test_zero_hit_query_does_not_auto_escalate` was already failing on `HEAD` before my changes — the fixture's `quarterly-roadmap.md` body contains the word "token" which the test query "xyzzy-nonexistent-token" accidentally matches. Verified by `git stash`. Not in scope for this feature; left as-is. Recommend fixing the test (use a truly nonexistent token like `qqzzzqq`) or fixing the fixture (rewrite the body to avoid the word "token") in a separate cleanup.

**Open thread**: This feature is read-only. Cross-repo writes (e.g. dispatcher in repo A writing to repo B's `_inbox`) still need the perms-mirror script. See permissions-catalog.md.

**Plan artifact**: `.claude/quality/sessions/20260510_203353_umbrella-aware-retrieval/`.

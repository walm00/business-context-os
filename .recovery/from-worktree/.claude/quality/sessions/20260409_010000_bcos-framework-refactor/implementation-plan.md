# Implementation Plan: Move Framework Docs to _bcos-framework/

**Session:** 20260409_010000_bcos-framework-refactor
**Scenario:** Mixed (AGENTING + DOCUMENTATION)
**Status:** Awaiting Approval

---

## Problem

Framework documentation folders (`architecture/`, `guides/`, `methodology/`, `templates/`) sit in `docs/` root alongside user content. This:
- Makes docs/ noisy for users (they see framework folders mixed with their data points)
- Creates confusion ("are these my docs or the framework's?")
- Pollutes the space users are supposed to own
- Makes flat-root recommendation harder to enforce when 4 framework folders already break it

## Solution

Move all 4 framework folders under `docs/_bcos-framework/`:
```
docs/architecture/   → docs/_bcos-framework/architecture/
docs/guides/         → docs/_bcos-framework/guides/
docs/methodology/    → docs/_bcos-framework/methodology/
docs/templates/      → docs/_bcos-framework/templates/
```

The underscore prefix follows the existing convention (`_inbox`, `_planned`, `_archive`, `_collections`). The `bcos-` prefix makes it unambiguously framework content.

## Pre-existing bug fix included

`post_edit_frontmatter_check.py` SKIP_PATHS is missing `docs/architecture/`. Fixed as part of this refactor.

---

## Phase 0: Commit Pending Session Fixes

| ID | Task | Status |
|----|------|--------|
| P0_001 | Commit 5 uncommitted files: update.py (settings.json merge, convention dirs, wake-up), build_document_index.py (subdirs), onboarding + ingest (guardrails) | pending |

These are independent of the refactor and should be committed first.

---

## Phase 1: Physical Folder Moves

| ID | Task | Status |
|----|------|--------|
| P1_001 | `mkdir -p docs/_bcos-framework` | pending |
| P1_002 | `git mv docs/architecture docs/_bcos-framework/architecture` | pending |
| P1_003 | `git mv docs/guides docs/_bcos-framework/guides` | pending |
| P1_004 | `git mv docs/methodology docs/_bcos-framework/methodology` | pending |
| P1_005 | `git mv docs/templates docs/_bcos-framework/templates` | pending |

---

## Phase 2: Global Path Replacement

4 search-replace patterns applied across all files:

| Pattern | Files affected |
|---------|---------------|
| `docs/architecture/` → `docs/_bcos-framework/architecture/` | 14 files |
| `docs/guides/` → `docs/_bcos-framework/guides/` | 18 files |
| `docs/methodology/` → `docs/_bcos-framework/methodology/` | 17 files |
| `docs/templates/` → `docs/_bcos-framework/templates/` | 16 files |

| ID | Task | Status |
|----|------|--------|
| P2_001 | Replace all `docs/architecture/` references | pending |
| P2_002 | Replace all `docs/guides/` references | pending |
| P2_003 | Replace all `docs/methodology/` references | pending |
| P2_004 | Replace all `docs/templates/` references | pending |

**Note:** Also handle bare names in Python sets (e.g., `"methodology"` in known_subdirs).

---

## Phase 3: Script and Config Updates

Files that need more than simple path replacement:

| ID | File | What to change | Status |
|----|------|---------------|--------|
| P3_001 | `build_document_index.py` | SKIP_PATHS (4→1 prefix), known_subdirs (4→1), output template string | pending |
| P3_002 | `analyze_crossrefs.py` | SKIP_PATHS (4→1 prefix) | pending |
| P3_003 | `post_edit_frontmatter_check.py` | SKIP_PATHS (3→1 prefix) + fix missing architecture | pending |
| P3_004 | `validate_frontmatter.py` | SKIP_DIRS (4→1 prefix) | pending |
| P3_005 | `install.sh` | mkdir _bcos-framework, update 4 copy loops | pending |
| P3_006 | `README.md` | Update folder tree visual | pending |

---

## Phase 4: update.py Migration Logic

| ID | Task | Status |
|----|------|--------|
| P4_001 | Update FRAMEWORK_DIRS list (4 old paths → 4 new paths) | pending |
| P4_002 | Add migration logic: after applying files, check for old dirs, move contents, remove empties | pending |

Migration logic for existing installs:
```python
OLD_TO_NEW = [
    ("docs/architecture", "docs/_bcos-framework/architecture"),
    ("docs/guides", "docs/_bcos-framework/guides"),
    ("docs/methodology", "docs/_bcos-framework/methodology"),
    ("docs/templates", "docs/_bcos-framework/templates"),
]
# After applying files: if old dir exists and new dir has files, remove old dir
```

---

## Phase 5: Verification

| ID | Check | Must pass? | Status |
|----|-------|-----------|--------|
| P5_001 | `python .github/scripts/validate_frontmatter.py` | Yes | pending |
| P5_002 | `python .github/scripts/validate_references.py` | Yes | pending |
| P5_003 | `python .claude/scripts/analyze_integration.py --ci` | Yes | pending |
| P5_004 | `python .claude/scripts/build_document_index.py --dry-run` | Yes | pending |
| P5_005 | All JSON files validate with `python -m json.tool` | Yes | pending |
| P5_006 | `grep -r "docs/architecture/" --include="*.md" --include="*.py" --include="*.json" --include="*.sh"` returns ZERO matches (excluding _bcos-framework paths) | Yes | pending |
| P5_007 | Same grep for docs/guides/, docs/methodology/, docs/templates/ | Yes | pending |

---

## Phase 6: FIXED END

| ID | Task | Mandatory | Status |
|----|------|-----------|--------|
| P6_001 | Integration audit: `analyze_integration.py --staged` | Yes | pending |
| P6_002 | Ecosystem state: discovery scripts, verify state.json (11 skills) | Yes | pending |
| P6_003 | Lesson capture: framework docs in user root = confusion | Yes | pending |

---

## Artifacts

- Session folder: `.claude/quality/sessions/20260409_010000_bcos-framework-refactor/`
- Planning manifest: `planning-manifest.json`
- This plan: `implementation-plan.md`
- Pre-work reference: `.private/refactor-bcos-framework-folder.md`

# Folder Conventions

**How BCOS organizes folders, and how to add your own without breaking maintenance.**

---

## The Underscore Rule

Any top-level folder under `docs/` whose name starts with `_` is **opted out** of the framework's scanning, validation, indexing, and audit. Files inside `_<name>/` folders:

- are **not** required to have YAML frontmatter
- are **not** scanned by `index-health` for missing fields, broken links, or stale dates
- are **not** validated by `doc-lint`
- are **not** audited by `context-audit`
- are **not** listed individually in the document index

The framework knows they exist (the indexer reports a one-line summary like `Skipped 2 underscore-prefixed folder(s), 8 file(s) total: _drafts/, _vendor-notes/`) but it leaves the contents alone. The folder is the signal.

This is the rule, not a fixed list of names. `_drafts/`, `_experiments/`, `_vendor-notes/`, `_personal-research/` — any prefix you invent works.

---

## Built-in Framework Folders

Six `_`-prefixed folders are reserved for the framework:

| Folder | Purpose | Treatment |
|--------|---------|-----------|
| `docs/_inbox/` | Raw material, session captures, unprocessed dumps | Categorized in document index; audit-inbox job processes it |
| `docs/_planned/` | Polished ideas, not yet active reality | Relaxed validation; flagged if older than 6 months |
| `docs/_archive/` | Superseded documents, kept for reference | Skipped by all maintenance |
| `docs/_collections/` | **Verbatim evidence artifacts** as received or generated — invoices, brand kits, signed agreements, call transcripts, monthly reports, Stripe exports. The file IS the truth — editing it corrupts evidence | Each subdirectory requires `_manifest.md` (rows per file + cross-zone links to data points); optional sidecar `.meta.md` per artifact when the row isn't enough; weekly `collections-scan` job for untracked/orphan/expiry detection. See `architecture/collections-zone.md` |
| `docs/_wiki/` | **Derivative explanatory pages** — runbooks, how-tos, glossaries, post-mortems, FAQs, decision logs, project logs. Cite canonical data points via `builds-on:` frontmatter; never duplicate their content | Standard maintenance skips raw/queue/index/log, but `_wiki/pages/` and `_wiki/source-summary/` have wiki-specific frontmatter, schema, lint, and scheduled jobs. See `architecture/wiki-zone.md` |
| `docs/_bcos-framework/` | Framework code (synced from upstream) | Skipped — never edit by hand; managed by `update.py` |

Don't reuse these names for custom folders.

**Distinguishing collections from wiki:** if I edit this file, am I making it more *wrong* or more *right*? More right (refining explanation) → wiki. More wrong (corrupting evidence) → collection. A signed contract is a collection; a page explaining how to read that contract is a wiki entry.

---

## Custom Folders — Three Patterns

### Pattern A: Active context (no underscore)

```
docs/
└── product-roadmap.md          # scanned, validated, indexed
└── customer-research.md        # scanned, validated, indexed
└── pricing-rules.md            # scanned, validated, indexed
```

**When to use:** content that should be part of your active business context. Treated as current reality. Requires YAML frontmatter. Subject to all maintenance jobs.

### Pattern B: Custom opt-out (`_`-prefixed folder)

```
docs/
└── _drafts/                    # SKIPPED — yours, framework ignores
│   ├── new-pricing-thoughts.md
│   └── q3-strategy-rough.md
└── _vendor-evals/              # SKIPPED — yours, framework ignores
│   └── tool-comparison.md
```

**When to use:** working areas, drafts, experiments, sensitive analysis you want kept inside the repo (committed to git) but outside the maintenance/quality bar. Files don't need frontmatter. The framework will report `Skipped 2 underscore-prefixed folders` in the daily digest so you don't lose track of what's there.

**Caveat:** `_*` folders are still committed to git unless you also gitignore them. The opt-out is from *framework processing*, not from version control.

### Pattern C: Local-only (`.private/`)

```
.private/                       # SKIPPED + GITIGNORED — never leaves your machine
├── pricing-internal.md
├── investor-conversations.md
└── personal-sops.md
```

**When to use:** content that should never be committed. The `.private/` folder is gitignored by default in the BCOS framework's `.gitignore`. See `private-folder-guide.md` for full details.

### Quick decision

- Should this be part of active business context? → no underscore
- Working/draft/experimental, but fine to commit? → `docs/_<name>/`
- Sensitive, never commit? → `.private/`

---

## What If I Create `docs/my-folder/` (No Underscore)?

The framework treats it as **active context with a quirk**:

- Files inside are scanned for missing frontmatter (warnings appear in the daily digest)
- Files are listed in `document-index.md` under "Custom Subdirectories" as a soft warning ("recommended: flat in `docs/` root")
- The recommended pattern is **flat in `docs/` root** with `cluster:` frontmatter for grouping, not subdirectories

If you want a folder for organization (not opt-out), it works — but expect the framework to nudge you toward flat structure. If you want a folder that the framework leaves alone, prefix it with `_`.

**Exception:** `docs/_wiki/` intentionally uses semantic subfolders. Wiki pages live
under `_wiki/pages/`, external captures live under `_wiki/source-summary/`, and
raw source material stays under `_wiki/raw/`. Do not copy this pattern into
normal active context; use flat `docs/*.md` plus `cluster:` there.

---

## What Scanners Actually Do (Quick Reference)

| Scanner | Scans | Skips |
|---------|-------|-------|
| `build_document_index.py` | `docs/**/*.md` | Any `docs/_*/` (silent for `_bcos-framework/`, counted for others) |
| `index-health` (daily job) | Same as indexer | Same as indexer |
| `doc-lint` | User-supplied path | Any `_*/` folder |
| `context-audit` | User-supplied scope | Any `_*/` folder |
| Frontmatter pre-edit hook | Files in `docs/`, plus wiki pages under `_wiki/pages/` and `_wiki/source-summary/` | Framework/internal underscore paths, `_wiki/raw/`, `_wiki/queue.md`, `_wiki/index.md`, `_wiki/log.md` |

The rule is consistent across all of them: **the underscore prefix is the opt-out signal**.

---

## Examples

**Good:** clear separation of active and opted-out content
```
docs/
├── value-proposition.md        # active
├── target-audience.md          # active
├── _drafts/                    # working area, framework ignores
│   └── repositioning-rough.md
├── _inbox/                     # framework folder
└── _archive/                   # framework folder
.private/                       # local-only, never committed
└── investor-prep.md
```

**Risky:** sensitive content in active scope
```
docs/
├── pricing-public.md           # OK — public pricing doc
├── pricing-internal.md         # ⚠️ scanned, indexed, committed
                                # If sensitive, move to .private/ or _drafts/
```

---

## See Also

- [`private-folder-guide.md`](./private-folder-guide.md) — When to use `.private/` instead of `docs/_<custom>/`
- [`maintenance-guide.md`](./maintenance-guide.md) — How the framework keeps active context healthy
- [`scheduling.md`](./scheduling.md) — How scheduled jobs interact with these folders

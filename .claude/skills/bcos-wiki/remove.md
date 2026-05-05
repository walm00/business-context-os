# /wiki remove — hard-delete a wiki page and optional raw files

(Skill-directory paths and the `.config.yml` Guard are defined in `SKILL.md`.)

## Invocation

```text
/wiki remove <slug> [--raw]
```

Use only when the user explicitly asks for hard deletion. Prefer `/wiki archive` for normal cleanup.

## Flow

1. Resolve `<slug>` under `docs/_wiki/pages/` or `docs/_wiki/source-summary/`.
2. Scan for dangling references exactly as `archive.md` does.
3. Require explicit user confirmation before deletion, including a list of files to delete.
4. Delete the page.
5. If `--raw` is present, delete raw files referenced by frontmatter `raw-files:` and the conventional raw path for the page's provenance:
   - `docs/_wiki/raw/web/<slug>.md`
   - `docs/_wiki/raw/github/<slug>.md`
   - `docs/_wiki/raw/youtube/<slug>.md`
   - `docs/_wiki/raw/local/<slug>.*`
6. Remove the URL line from `queue.md` only when it exists under `## Pending`; keep completed history unless the user explicitly asks to scrub it.
7. Run `python .claude/scripts/refresh_wiki_index.py`.
8. Append to `log.md`.

## Output

```text
Removed: <slug>

  Deleted page: <path>
  Deleted raw:  <N> file(s)
  References:   <N> dangling reference(s) reported
  Index:        regenerated
```

No agent commits. See `SKILL.md`.

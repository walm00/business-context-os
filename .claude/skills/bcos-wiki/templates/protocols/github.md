# GitHub Fetch Protocol

Used by `/wiki run` for `https://github.com/<org>/<repo>` URLs.

## Steps

1. Resolve org, repo, branch, and optional path.
2. Fetch repository metadata, README, license, topics, default branch, recent release, and high-signal docs files.
3. In `deep` mode, include package manifests and selected source tree summaries. Use `<!-- clone -->` only when API/source browsing is insufficient and the user allowed it.
4. Apply token guard before writing raw content.
5. Write raw markdown to `docs/_wiki/raw/github/<org>-<repo>.md` with:

```markdown
<!-- wiki-source-stamp
source-url: https://github.com/<org>/<repo>
source-type: github
branch: <branch>
captured-on: <today>
detail-level: <brief|standard|deep>
-->
```

## Output to `run.md`

Return repo metadata, raw path, slug, projected token count, and any branch/path notes.

# Web Fetch Protocol

Used by `/wiki run` for non-GitHub, non-YouTube HTTP(S) URLs.

## Steps

1. Fetch the page HTML and final redirected URL.
2. Prefer structured source hints in this order:
   - `llms.txt`
   - `llms-full.txt`
   - sitemap links
   - canonical docs links
3. Extract readable markdown from the page or discovered docs source.
4. Detect product sections. In `deep` mode, multi-product sites may return `products` for umbrella/subpage generation.
5. Discover one companion GitHub repository URL when present.
6. Estimate tokens before writing raw content. If projected cumulative run size exceeds 200,000 tokens, halt.
7. Write raw markdown to `docs/_wiki/raw/web/<slug>.md` with a source stamp:

```markdown
<!-- wiki-source-stamp
source-url: <url>
source-type: web
captured-on: <today>
detail-level: <brief|standard|deep>
-->
```

## Output to `run.md`

Return `raw_path`, `slug`, `products`, `companion_github_url`, projected token count, and fetch diagnostics.

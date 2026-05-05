# Local Source Protocol

Used by `/wiki promote` and `/wiki create`.

## Supported inputs

- `.md`
- `.txt`
- `.pdf`
- `.docx`
- pasted text

## Steps

1. Copy or extract the source into `docs/_wiki/raw/local/<slug>.md`.
2. For binaries, also copy the original byte-identical file to `docs/_wiki/raw/local/<slug>.<ext>`.
3. Compute SHA-256 over the original content and record the first 16 hex chars in `provenance.notes`.
4. Never write to `docs/_collections/` from this protocol.
5. Return raw markdown path, optional binary path, hash, size, and original source reference.

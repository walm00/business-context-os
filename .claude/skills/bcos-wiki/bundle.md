# /wiki bundle

Zone-scoped sugar over `/context bundle <profile>` — runs the same backend
but filters the resulting bundle to wiki-zone hits only.

For the full mechanical-routing spec see [`context-routing/bundle.md`](../context-routing/bundle.md).

## When to use

- "What wiki context exists for this task?"
- "Bundle just the wiki for `architecture:design`"
- For cross-zone bundles (active + wiki + planned + collections), use `/context bundle <profile>` instead.

## Invocation

```
python .claude/scripts/context_bundle.py --profile <profile-id> [other flags]
```

`/wiki bundle <profile>` is intended as a thin presentation wrapper: callers
post-filter the resulting envelope to retain only `by-zone["wiki"]` entries
and the corresponding `by-family` slices, freshness verdicts, and conflicts
that involve a wiki hit. Every flag from `/context bundle` works identically
— see [`context-routing/bundle.md`](../context-routing/bundle.md#invocation).

## Output

Same envelope as `/context bundle`. Consumers that want strictly wiki-only
output drop everything outside `by-zone["wiki"]`. The full envelope is still
returned because conflicts and traversal hops are inherently cross-zone — a
wiki hit may share `EXCLUSIVELY_OWNS` with an active doc, and that conflict
needs both candidates in the report.

## Guard rails (inherited)

### Wiki-zone guard

Like every `/wiki` subcommand, **bundle reads but never writes**. Pure read.
If `docs/_wiki/.config.yml` is missing in the current repo, `by-zone["wiki"]`
is empty and `unsatisfied-zone-requirements` may include `wiki` (depending on
profile).

### D-10 strict — no auto-trigger

Two LLM-touching paths exist behind explicit flags. Both currently require
`--dry-run`:

- `--resolve-conflicts` — opt-in conflict resolution.
- `--verify-coverage` — opt-in coverage verification.

The default mechanical run **never** auto-fires either. See
[`context-routing/bundle.md`](../context-routing/bundle.md#d-10-strict--no-auto-trigger)
for the full rule.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `by-zone.wiki` empty | Wiki zone not initialized | `/wiki init` |
| `by-zone.wiki` empty but other zones populate | Profile didn't include `wiki` in required-zones | Update the profile or use `/context bundle <profile>` instead |
| `--resolve-conflicts` exits non-zero | Non-dry-run while LLM wiring deferred | Pass `--dry-run` |

## Tests

Bundle behaviour is exercised under `test_context_capability.py` (the same
20 assertions — schema, ranking, conflicts, freshness, traversal, determinism,
escalation gating, CLI smoke). Wiki-specific assertions can be added by
running the resolver against fixtures whose `required-zones` includes only
`wiki`.

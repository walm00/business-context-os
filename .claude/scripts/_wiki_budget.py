#!/usr/bin/env python3
"""
Cumulative token budget guard for `wiki-fetch` sub-agent dispatch (P3).

When a calling skill (e.g., `/wiki run`) projects N parallel sub-agent
invocations, each returning ~K tokens to the main thread, the cumulative
return MUST stay safely below the main-context limit. The pre-existing
guard was per-fetch only — N invocations × per-fetch budget would overshoot
without anyone noticing.

This module makes the math explicit and testable. The decision rule:

    cumulative = N × projected_tokens_per_result
    threshold  = max_main_context × 0.80
    parallel if cumulative <= threshold, else serial

`serial` does not mean "no parallelism" — it means "queue the remaining
invocations after the first batch returns and budget frees up." The calling
skill is responsible for the actual batching loop; this module returns the
strategy decision plus the math so the skill can log what it chose and why.

Public API:
    decide_dispatch_strategy(n_invocations, projected_tokens_per_result, max_main_context, threshold_fraction=0.80) -> Decision

Decision is a small dataclass with the chosen strategy, the cumulative
projection, the threshold, and the max — useful for /wiki run output.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_THRESHOLD_FRACTION = 0.80
DEFAULT_MAX_MAIN_CONTEXT = 200_000  # main context window in tokens
DEFAULT_PROJECTED_RESULT_TOKENS = 4_000  # per the wiki-fetch contract cap


@dataclass(frozen=True)
class Decision:
    strategy: str  # "parallel" | "serial"
    cumulative_tokens: int
    threshold_tokens: int
    max_main_context: int
    n_invocations: int
    projected_tokens_per_result: int
    max_parallel_batch_size: int       # largest N that fits under the threshold
    batches: tuple[tuple[int, ...], ...]  # concrete dispatch plan: each batch is a tuple of 0-based indices


def decide_dispatch_strategy(
    *,
    n_invocations: int,
    projected_tokens_per_result: int = DEFAULT_PROJECTED_RESULT_TOKENS,
    max_main_context: int = DEFAULT_MAX_MAIN_CONTEXT,
    threshold_fraction: float = DEFAULT_THRESHOLD_FRACTION,
) -> Decision:
    """Decide whether N sub-agents should dispatch in parallel or serially,
    AND return a concrete batch plan the caller can iterate.

    The math:
      cumulative = N × per-result projection
      threshold  = max_main_context × threshold_fraction (default 80%)
      max_batch  = floor(threshold / per-result), clamped to [1, n]

    `strategy`:
      - "parallel" when cumulative <= threshold AND n >= 1 — caller dispatches
        all N invocations concurrently.
      - "serial"   otherwise — caller dispatches in `batches` of size
        `max_parallel_batch_size`, awaiting each batch before starting the next.

    `batches`:
      Always populated. For "parallel" it's a single batch with all indices
      [(0, 1, …, N-1)]. For "serial" it's the chunked plan, e.g. for N=10 with
      max_batch=4 → [(0,1,2,3), (4,5,6,7), (8,9)]. Callers don't have to
      compute batching themselves.

    Edge cases:
    - n=0 → strategy="parallel", batches=()
    - n=1 → strategy="parallel" regardless of projection
    - cumulative exactly at threshold → serial (be conservative)
    """
    n = max(0, int(n_invocations))
    per = max(0, int(projected_tokens_per_result))
    max_ctx = max(1, int(max_main_context))
    threshold = int(max_ctx * threshold_fraction)
    cumulative = n * per

    if per == 0:
        # No projected return — every call is free, dispatch all in parallel.
        max_batch = max(n, 1)
    else:
        max_batch = max(1, threshold // per)
    if n > 0:
        max_batch = min(max_batch, n)

    strategy = "parallel" if (cumulative < threshold and n >= 1) else "serial"
    if n == 1:
        strategy = "parallel"
    if n == 0:
        strategy = "parallel"

    batches: tuple[tuple[int, ...], ...]
    if n == 0:
        batches = ()
    elif strategy == "parallel":
        batches = (tuple(range(n)),)
    else:
        batches = tuple(
            tuple(range(start, min(start + max_batch, n)))
            for start in range(0, n, max_batch)
        )

    return Decision(
        strategy=strategy,
        cumulative_tokens=cumulative,
        threshold_tokens=threshold,
        max_main_context=max_ctx,
        n_invocations=n,
        projected_tokens_per_result=per,
        max_parallel_batch_size=max_batch if n > 0 else 0,
        batches=batches,
    )


__all__ = [
    "Decision",
    "decide_dispatch_strategy",
    "DEFAULT_THRESHOLD_FRACTION",
    "DEFAULT_MAX_MAIN_CONTEXT",
    "DEFAULT_PROJECTED_RESULT_TOKENS",
]

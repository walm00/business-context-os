#!/usr/bin/env python3
"""
Task-driven cross-zone bundle resolver (P5).

Reads a task profile from `_context.task-profiles.yml.tmpl` (or per-repo
override) and resolves a structured bundle envelope from
`.claude/quality/context-index.json`. The envelope tells the calling agent
what context exists for the declared task, with freshness verdicts,
source-of-truth conflicts, missing perspectives, and traversal hops.

Mechanical-first (D-10 strict). The default path is pure Python: pattern
matching, deterministic ranking, graph walk over typed edges, freshness
thresholding, structured-field conflict detection. The only LLM-touching
paths are explicit opt-in flags:
  --resolve-conflicts  -> LLM resolves unresolved source-of-truth conflicts
  --verify-coverage    -> LLM verifies prose-perspective coverage

Both raise `LLMEscalationNotImplementedError` when invoked without
`--dry-run`, until the LLM client wiring lands. `--dry-run` records the
opt-in in `escalations` without firing.

Output envelope:
{
  "profile-id": str,
  "generated-at": str,                                # ISO-8601
  "by-zone":      {zone-id: [hit, ...]},
  "by-family":    {family-name: [hit, ...]},
  "freshness":    [{path, verdict, days-since, threshold}, ...],
  "source-of-truth-conflicts": [
    {family, candidates: [hit, ...], resolution: <path>, resolved-by: rank|llm|unresolved, reason}
  ],
  "missing-perspectives": [{family, expected-min, actual}, ...],
  "traversal-hops": [{from, edge, to, depth}, ...],
  "unsatisfied-zone-requirements": [zone-id, ...],
  "escalations": [str, ...]
}

Hits keep a small subset of context-index doc fields:
{path, name, zone, cluster, page-type, type, tags, exclusively_owns,
 last_updated, last_reviewed, age_days}.

Determinism: same fixture → byte-identical envelope (modulo `generated-at`).
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_INDEX = REPO_ROOT / ".claude" / "quality" / "context-index.json"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from load_task_profiles import load_task_profiles  # noqa: E402

HIT_FIELDS = (
    "path",
    "name",
    "zone",
    "cluster",
    "page-type",
    "type",
    "tags",
    "exclusively_owns",
    "last-updated",
    "last-reviewed",
    "age_days",
)


class LLMEscalationNotImplementedError(NotImplementedError):
    """Raised when --resolve-conflicts or --verify-coverage runs without --dry-run.

    The mechanical bundle is always available; LLM-touching paths require
    explicit opt-in AND --dry-run until the client wiring lands.
    """


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def resolve_bundle(
    profile_id: str,
    *,
    profiles: list[dict[str, Any]] | None = None,
    profiles_path: Path | None = None,
    index: dict[str, Any] | None = None,
    index_path: Path | None = None,
    resolve_conflicts: bool = False,
    verify_coverage: bool = False,
    dry_run: bool = False,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Resolve the bundle envelope for `profile_id`."""
    if profiles is None:
        profiles = load_task_profiles(profiles_path)
    profile = _find_profile(profile_id, profiles)
    if profile is None:
        raise ValueError(f"profile not found: {profile_id!r}")

    if index is None:
        target = index_path or DEFAULT_INDEX
        if target.is_file():
            index = json.loads(target.read_text(encoding="utf-8"))
        else:
            index = {"docs": [], "edges": []}

    escalations = _resolve_escalations(
        resolve_conflicts=resolve_conflicts,
        verify_coverage=verify_coverage,
        dry_run=dry_run,
    )

    docs = list(index.get("docs") or [])
    edges = list(index.get("edges") or [])

    # 1. Build the candidate pool: docs in declared zones AND matching at
    #    least one declared content family. Without the family filter, an
    #    optional zone (e.g., planned=false) dumps every doc into the bundle
    #    even when none are task-relevant — that's the regression the audit
    #    flagged. Profiles with zero families (rare) fall back to all-zone-
    #    docs so they aren't silently empty.
    declared_zones = [z["id"] for z in profile.get("required-zones") or []]
    families = profile.get("content-families") or []
    in_zone = [d for d in docs if d.get("zone") in declared_zones]
    if families:
        pool = [d for d in in_zone if _doc_matches_any_family(d, families)]
    else:
        pool = in_zone

    # 2. Walk graph edges from seed pool up to depth-cap.
    traversal_hops = _walk_edges(pool, edges, profile.get("traversal-hints") or [])

    # 3. Group hits by family via pattern matching (subset of pool).
    by_family = _group_by_family(pool, families)

    # 4. Group hits by zone (the matched pool, not every in-zone doc).
    by_zone = _group_by_zone(pool)

    # 5. Freshness verdict per hit.
    freshness = _freshness_verdicts(pool, profile.get("freshness-thresholds") or {}, now)

    # 6. Source-of-truth conflict detection.
    conflicts = _detect_conflicts(by_family, profile.get("source-of-truth-ranking") or [])

    # 7. Coverage gaps: families failing coverage-assertions min-count.
    missing = _missing_perspectives(by_family, profile.get("coverage-assertions") or {})

    # 8. Unsatisfied required zones.
    unsatisfied = _unsatisfied_zones(profile, docs)

    return {
        "profile-id": profile_id,
        "generated-at": _now_iso(now),
        "by-zone": by_zone,
        "by-family": by_family,
        "freshness": freshness,
        "source-of-truth-conflicts": conflicts,
        "missing-perspectives": missing,
        "traversal-hops": traversal_hops,
        "unsatisfied-zone-requirements": unsatisfied,
        "escalations": escalations,
    }


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _find_profile(profile_id: str, profiles: list[dict[str, Any]]) -> dict[str, Any] | None:
    for p in profiles:
        if p.get("id") == profile_id:
            return p
    return None


def _now_iso(now: datetime.datetime | None) -> str:
    moment = now or datetime.datetime.now(datetime.timezone.utc)
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def _hit_view(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field in HIT_FIELDS:
        # Index uses underscores for some keys; honor either form.
        if field in doc:
            out[field] = doc[field]
        elif field.replace("-", "_") in doc:
            out[field] = doc[field.replace("-", "_")]
        else:
            out[field] = None
    return out


def _group_by_zone(pool: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for doc in pool:
        zone = doc.get("zone") or "unknown"
        out.setdefault(zone, []).append(_hit_view(doc))
    return {z: out[z] for z in sorted(out.keys())}


def _group_by_family(
    pool: list[dict[str, Any]], families: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {f["name"]: [] for f in families}
    for doc in pool:
        for family in families:
            if _doc_matches_pattern(doc, family.get("pattern", "")):
                out[family["name"]].append(_hit_view(doc))
    return out


def _doc_matches_any_family(doc: dict[str, Any], families: list[dict[str, Any]]) -> bool:
    """True when `doc` matches at least one declared content-family pattern."""
    for family in families:
        if _doc_matches_pattern(doc, family.get("pattern", "")):
            return True
    return False


def _doc_matches_pattern(doc: dict[str, Any], pattern: str) -> bool:
    """Pattern grammar: `cluster=<v>`, `tag=<v>`, `page-type=<v>`, `type=<v>`."""
    pattern = pattern.strip()
    if "=" not in pattern:
        return False
    key, _, value = pattern.partition("=")
    key = key.strip()
    value = value.strip()
    if key == "cluster":
        return (doc.get("cluster") or "") == value
    if key == "tag":
        return value in (doc.get("tags") or [])
    if key == "page-type":
        return (doc.get("page_type") or doc.get("page-type") or "") == value
    if key == "type":
        return (doc.get("type") or "") == value
    return False


def _freshness_verdicts(
    pool: list[dict[str, Any]],
    thresholds: dict[str, int | None],
    now: datetime.datetime | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for doc in pool:
        zone = doc.get("zone")
        if zone not in thresholds:
            continue
        threshold = thresholds[zone]
        age = doc.get("age_days")
        verdict = _verdict_from_age(age, threshold)
        out.append({
            "path": doc.get("path"),
            "zone": zone,
            "verdict": verdict,
            "days-since": age,
            "threshold": threshold,
        })
    out.sort(key=lambda x: (x.get("path") or ""))
    return out


def _verdict_from_age(age: int | None, threshold: int | None) -> str:
    if threshold is None:
        return "fresh"  # never-stale zones (frozen evidence, framework, etc.)
    if age is None:
        return "unknown"
    if age > threshold:
        return "past-threshold"
    if age > threshold // 2:
        return "stale"
    return "fresh"


def _detect_conflicts(
    by_family: dict[str, list[dict[str, Any]]],
    ranking: list[str],
) -> list[dict[str, Any]]:
    """Mechanical conflict detection: hits in the same family that share ≥1
    `exclusively_owns` key across different zones are CLEAR-violation candidates.

    Resolution uses the profile's `source-of-truth-ranking`: the first zone
    that appears wins. If all candidates are in the same zone, the conflict is
    `unresolved` (mechanical can't decide; agent should escalate).
    """
    rank_index = {z: i for i, z in enumerate(ranking)}
    conflicts: list[dict[str, Any]] = []
    for family, hits in by_family.items():
        # Build owns→[hits] index for this family
        owns_to_hits: dict[str, list[dict[str, Any]]] = {}
        for hit in hits:
            for own in hit.get("exclusively_owns") or []:
                owns_to_hits.setdefault(own, []).append(hit)
        # A conflict is any owns-key with ≥2 hits from different zones.
        for own, group in owns_to_hits.items():
            zones = {h.get("zone") for h in group}
            if len(zones) < 2:
                continue
            # Build canonical conflict candidate set (deduplicate by path)
            seen_paths: set[str] = set()
            candidates: list[dict[str, Any]] = []
            for h in group:
                path = h.get("path")
                if path in seen_paths:
                    continue
                seen_paths.add(path)
                candidates.append(h)
            # Have we already recorded a conflict over the same candidates+family?
            sig = (family, tuple(sorted(seen_paths)))
            if any(_conflict_signature(c) == sig for c in conflicts):
                continue
            resolution_path, resolved_by, reason = _resolve_conflict(candidates, rank_index)
            conflicts.append({
                "family": family,
                "shared-owns": own,
                "candidates": candidates,
                "resolution": resolution_path,
                "resolved-by": resolved_by,
                "reason": reason,
            })
    conflicts.sort(key=lambda c: (c["family"], c.get("shared-owns") or ""))
    return conflicts


def _conflict_signature(c: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    paths = tuple(sorted((h.get("path") or "") for h in c.get("candidates") or []))
    return (c.get("family") or "", paths)


def _resolve_conflict(
    candidates: list[dict[str, Any]],
    rank_index: dict[str, int],
) -> tuple[str | None, str, str]:
    """Return (winning_path, resolved-by, reason).

    Picks the candidate whose zone has the lowest rank index. Ties (same zone
    or no ranking) yield resolved-by="unresolved".
    """
    if not candidates:
        return None, "unresolved", "no candidates"
    if not rank_index:
        return None, "unresolved", "no source-of-truth-ranking declared"
    ranked = sorted(
        candidates,
        key=lambda h: (rank_index.get(h.get("zone") or "", 99), h.get("path") or ""),
    )
    top = ranked[0]
    top_rank = rank_index.get(top.get("zone") or "", 99)
    # If the top is tied with the second by zone-rank, that's an unresolved tie
    if len(ranked) > 1:
        second_rank = rank_index.get(ranked[1].get("zone") or "", 99)
        if top_rank == second_rank:
            return None, "unresolved", "candidates share top zone-rank"
    if top_rank == 99:
        return None, "unresolved", "top candidate's zone not in ranking"
    return top.get("path"), "rank", f"highest-ranked zone: {top.get('zone')}"


def _missing_perspectives(
    by_family: dict[str, list[dict[str, Any]]],
    coverage: dict[str, int],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for family, expected in coverage.items():
        actual = len(by_family.get(family) or [])
        if actual < expected:
            out.append({
                "family": family,
                "expected-min": expected,
                "actual": actual,
            })
    out.sort(key=lambda x: x["family"])
    return out


def _unsatisfied_zones(profile: dict[str, Any], docs: list[dict[str, Any]]) -> list[str]:
    present = {d.get("zone") for d in docs if d.get("zone")}
    out: list[str] = []
    for entry in profile.get("required-zones") or []:
        if not entry.get("required"):
            continue
        if entry.get("id") not in present:
            out.append(entry["id"])
    out.sort()
    return out


def _walk_edges(
    pool: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    hints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Walk typed edges from seed pool up to depth-cap.

    Each hint declares `from-edge` (e.g., builds-on) and `depth-cap`. We BFS
    from every seed path, following only edges of the declared kind, recording
    each hop with its depth.
    """
    if not hints:
        return []

    seed_paths = {d.get("path") for d in pool if d.get("path")}
    edges_by_from: dict[str, list[dict[str, Any]]] = {}
    for e in edges:
        edges_by_from.setdefault(e.get("from") or "", []).append(e)

    hops: list[dict[str, Any]] = []
    for hint in hints:
        edge_kind = hint.get("from-edge")
        depth_cap = hint.get("depth-cap") or 0
        if not edge_kind or depth_cap <= 0:
            continue
        for seed in seed_paths:
            visited = {seed}
            frontier = [(seed, 0)]
            while frontier:
                node, depth = frontier.pop(0)
                if depth >= depth_cap:
                    continue
                for e in edges_by_from.get(node, []):
                    if e.get("kind") != edge_kind:
                        continue
                    target = e.get("to")
                    if not target or target in visited:
                        continue
                    visited.add(target)
                    hops.append({
                        "from": node,
                        "edge": edge_kind,
                        "to": target,
                        "depth": depth + 1,
                    })
                    frontier.append((target, depth + 1))
    # Deduplicate (same from/edge/to retained once at lowest depth)
    seen: dict[tuple, dict[str, Any]] = {}
    for hop in hops:
        key = (hop["from"], hop["edge"], hop["to"])
        if key not in seen or hop["depth"] < seen[key]["depth"]:
            seen[key] = hop
    return sorted(seen.values(), key=lambda h: (h["from"], h["edge"], h["to"]))


def _resolve_escalations(
    *, resolve_conflicts: bool, verify_coverage: bool, dry_run: bool
) -> list[str]:
    """D-10 strict: opt-in flags + --dry-run record opt-in; non-dry-run raises."""
    escalations: list[str] = []
    if resolve_conflicts:
        if not dry_run:
            raise LLMEscalationNotImplementedError(
                "--resolve-conflicts requires --dry-run for now. The LLM "
                "conflict-resolution path is specified by P5 but the LLM "
                "client wiring is deferred. Use --dry-run to validate the "
                "opt-in envelope without firing the LLM."
            )
        escalations.append("resolve-conflicts-dry-run")
    if verify_coverage:
        if not dry_run:
            raise LLMEscalationNotImplementedError(
                "--verify-coverage requires --dry-run for now. The LLM "
                "coverage-verification path is specified by P5 but the LLM "
                "client wiring is deferred."
            )
        escalations.append("verify-coverage-dry-run")
    return escalations


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Task-driven cross-zone bundle resolver."
    )
    p.add_argument("--profile", required=True, help="Profile id (e.g. market-report:write)")
    p.add_argument("--profiles-path", type=Path, default=None, help="Override path to profiles catalog")
    p.add_argument("--index", type=Path, default=None, help="Override path to context-index.json")
    p.add_argument("--index-root", type=Path, default=None, help="Build index from this docs root instead of reading the JSON")
    p.add_argument("--resolve-conflicts", action="store_true")
    p.add_argument("--verify-coverage", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    return p.parse_args(argv)


def _build_index_from_root(root: Path) -> dict[str, Any]:
    from context_index import build_context_index

    return build_context_index(root)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    index = None
    if args.index_root is not None:
        index = _build_index_from_root(args.index_root)
    try:
        bundle = resolve_bundle(
            args.profile,
            profiles_path=args.profiles_path,
            index=index,
            index_path=args.index,
            resolve_conflicts=args.resolve_conflicts,
            verify_coverage=args.verify_coverage,
            dry_run=args.dry_run,
        )
    except LLMEscalationNotImplementedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(bundle, indent=2, ensure_ascii=False))
    else:
        _print_human(bundle)
    return 0


def _print_human(bundle: dict[str, Any]) -> None:
    print(f"profile-id:    {bundle['profile-id']}")
    print(f"generated-at:  {bundle['generated-at']}")
    print(f"by-zone:       " + ", ".join(f"{z}({len(h)})" for z, h in bundle["by-zone"].items()))
    print(f"by-family:     " + ", ".join(f"{f}({len(h)})" for f, h in bundle["by-family"].items()))
    if bundle["source-of-truth-conflicts"]:
        print(f"conflicts:     {len(bundle['source-of-truth-conflicts'])}")
        for c in bundle["source-of-truth-conflicts"]:
            print(f"  - family={c['family']} owns={c['shared-owns']} resolution={c['resolution']} ({c['resolved-by']})")
    if bundle["missing-perspectives"]:
        print(f"missing:       {bundle['missing-perspectives']}")
    if bundle["unsatisfied-zone-requirements"]:
        print(f"unsatisfied:   {bundle['unsatisfied-zone-requirements']}")
    if bundle["escalations"]:
        print(f"escalations:   {bundle['escalations']}")


__all__ = ["resolve_bundle", "LLMEscalationNotImplementedError"]


if __name__ == "__main__":
    raise SystemExit(main())

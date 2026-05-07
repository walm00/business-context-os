"""
generate.py — Build atlas.json for the Context Galaxy visualization.

Reuses the existing `atlas_ingest.build_atlas()` from the bcos-dashboard
package (frontmatter parser, ownership spec, lifecycle bucketing,
declared-edge extraction, orphan detection) and layers two galaxy-specific
post-processing steps on top:

  1. Folder-implicit edges. theo-delivery-os and most BCOS repos do not
     populate `depends-on` / `consumed-by` in frontmatter — the real
     topology is encoded in the folder structure (engagement/, service-
     profiles/, finance/). For each non-singleton active folder we pick
     an anchor doc (engagement-profile.md, service-profile.md, index.md,
     or the oldest-created sibling) and emit `coexists-in` edges from
     each sibling to the anchor. These render as dashed/dim "soft"
     constellations in the viewer; declared edges remain solid/prominent.

  2. Visibility tiers. Framework / inbox / archive lifecycle buckets are
     ambient context — we keep them in the data but flag them so the
     client renders them as dim background particles rather than
     interactive stars. The /api/atlas endpoint takes a `?include` query
     to decide which buckets are emitted at all.

The repo root is selected via the `BCOS_REPO_ROOT` env var — the same
override `single_repo.py` already supports. Default is theo-delivery-os
(the canonical BCOS-mature reference for demo purposes).
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BCOS_DASH = _HERE.parent / "bcos-dashboard"
if str(_BCOS_DASH) not in sys.path:
    sys.path.insert(0, str(_BCOS_DASH))

DEFAULT_REPO = (
    Path.home() / "Documents" / "GitHub" / "theo-delivery-os"
).resolve()


_AMBIENT_BUCKETS = {"_inbox", "_planned", "_archive", "_bcos-framework", "_collections"}
_ANCHOR_NAMES = (
    "engagement-profile.md",
    "service-profile.md",
    "index.md",
    "README.md",
)


def _pick_anchor(siblings: list[dict]) -> dict | None:
    """Pick the anchor doc for a folder of siblings.

    Priority:
      1. Any file matching `_ANCHOR_NAMES` (engagement-profile / service-profile / index)
      2. Otherwise the doc with the oldest `created` date (folder root-of-history)
      3. Otherwise the first sibling (deterministic by sorted path)
    """
    by_basename = {Path(d["path"]).name.lower(): d for d in siblings}
    for name in _ANCHOR_NAMES:
        if name in by_basename:
            return by_basename[name]
    dated = [d for d in siblings if d.get("created")]
    if dated:
        return min(dated, key=lambda d: d["created"])
    return min(siblings, key=lambda d: d["path"])


def _folder_implicit_edges(docs: list[dict]) -> list[dict]:
    """Emit `coexists-in` edges from siblings to a folder anchor.

    Only operates on `active` bucket — folders inside _archive / _inbox etc.
    are noise. Singleton folders (one doc) emit no edges.
    """
    by_folder: dict[str, list[dict]] = defaultdict(list)
    for d in docs:
        if d["bucket"] != "active":
            continue
        folder = str(Path(d["path"]).parent.as_posix())
        by_folder[folder].append(d)

    edges: list[dict] = []
    for folder, sibs in by_folder.items():
        if len(sibs) < 2:
            continue
        anchor = _pick_anchor(sibs)
        if anchor is None:
            continue
        for sib in sibs:
            if sib["path"] == anchor["path"]:
                continue
            edges.append({
                "from": sib["path"],
                "to": anchor["path"],
                "kind": "coexists-in",
                "implicit": True,
            })
    return edges


def _annotate_visibility(docs: list[dict]) -> None:
    """Mark each doc with `tier` so the client knows star vs ambient particle.

    feature  — active bucket, has frontmatter (interactive bright stars)
    soft     — active bucket, no frontmatter (dim interactive)
    ambient  — _inbox / _planned / _archive / _bcos-framework / _collections
               (rendered as background dust, not interactive)
    """
    for d in docs:
        if d["bucket"] in _AMBIENT_BUCKETS:
            d["tier"] = "ambient"
        elif d.get("has_frontmatter"):
            d["tier"] = "feature"
        else:
            d["tier"] = "soft"


def _filter_by_include(atlas: dict, include: set[str]) -> dict:
    """Drop docs from buckets the client didn't ask for.

    `include` is a set of buckets to keep (e.g. {"active"} for the cleanest
    view, or {"active","_planned","_inbox"} for the working surface).
    Edges that reference a dropped doc are also dropped.
    """
    keep_paths = {d["path"] for d in atlas["docs"] if d["bucket"] in include}
    atlas["docs"] = [d for d in atlas["docs"] if d["path"] in keep_paths]
    atlas["edges"] = [
        e for e in atlas["edges"]
        if e["from"] in keep_paths and (
            not isinstance(e["to"], str) or e["to"] in keep_paths or "/" not in e["to"]
        )
    ]
    atlas["lifecycle"] = {
        k: [p for p in v if p in keep_paths]
        for k, v in atlas["lifecycle"].items()
    }
    domains: dict[str, dict] = {}
    for d in atlas["docs"]:
        dom = d.get("cluster") or (
            f"({d['bucket']})" if d["bucket"] != "active" else "(unclassified)"
        )
        b = domains.setdefault(dom, {
            "doc_count": 0, "total_bytes": 0, "_age_sum": 0, "_age_n": 0, "doc_paths": []
        })
        b["doc_count"] += 1
        b["total_bytes"] += d["size_bytes"]
        b["doc_paths"].append(d["path"])
        if d.get("age_days") is not None:
            b["_age_sum"] += d["age_days"]
            b["_age_n"] += 1
    for b in domains.values():
        b["avg_age_days"] = (b["_age_sum"] / b["_age_n"]) if b["_age_n"] else None
        del b["_age_sum"]
        del b["_age_n"]
    atlas["domains"] = domains
    atlas["counts"] = {
        "total": len(atlas["docs"]),
        "with_frontmatter": sum(1 for d in atlas["docs"] if d["has_frontmatter"]),
        "missing_required": sum(1 for d in atlas["docs"] if d["missing_required"]),
    }
    return atlas


def build_galaxy_atlas(
    repo_root: Path | None = None,
    include: set[str] | None = None,
) -> dict:
    """Build atlas.json payload for the galaxy.

    `include` defaults to {"active"} — the cleanest view. Pass a wider
    set to surface more buckets as ambient particles.
    """
    target = (repo_root or DEFAULT_REPO).resolve()
    if not target.is_dir():
        raise FileNotFoundError(f"BCOS_REPO_ROOT not found: {target}")
    os.environ["BCOS_REPO_ROOT"] = str(target)

    # Late import — atlas_ingest reads BCOS_REPO_ROOT at module-import time
    # via single_repo, so the env var must be set before importing.
    if "atlas_ingest" in sys.modules:
        del sys.modules["atlas_ingest"]
    if "single_repo" in sys.modules:
        del sys.modules["single_repo"]
    import atlas_ingest  # noqa: E402

    atlas = atlas_ingest.build_atlas()

    _annotate_visibility(atlas["docs"])
    atlas["edges"].extend(_folder_implicit_edges(atlas["docs"]))

    if include is not None:
        atlas = _filter_by_include(atlas, include)

    atlas["repo_label"] = target.name
    atlas["repo_root"] = str(target)
    return atlas


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Build galaxy atlas.json")
    ap.add_argument("--repo", help="Target BCOS repo (default: theo-delivery-os)")
    ap.add_argument("--include", default="active",
                    help="Comma list of buckets to keep "
                         "(active, _planned, _inbox, _archive, _bcos-framework, _collections, all)")
    ap.add_argument("--out", help="Write JSON here instead of stdout")
    ap.add_argument("--summary", action="store_true",
                    help="Print human summary instead of JSON")
    args = ap.parse_args()

    inc: set[str] | None
    if args.include == "all":
        inc = None
    else:
        inc = {x.strip() for x in args.include.split(",") if x.strip()}

    repo = Path(args.repo).resolve() if args.repo else None
    atlas = build_galaxy_atlas(repo_root=repo, include=inc)

    if args.summary:
        print(f"repo:       {atlas['repo_label']}")
        print(f"docs:       {atlas['counts']['total']}")
        print(f"with FM:    {atlas['counts']['with_frontmatter']}")
        print(f"domains:    {len(atlas['domains'])}")
        print(f"edges:      {len(atlas['edges'])}")
        decl = sum(1 for e in atlas['edges'] if not e.get('implicit'))
        impl = sum(1 for e in atlas['edges'] if e.get('implicit'))
        print(f"  declared: {decl}")
        print(f"  implicit: {impl}")
        print(f"orphans:    {len(atlas['orphans'])}")
        for dom, info in sorted(atlas["domains"].items(),
                                key=lambda kv: -kv[1]["doc_count"]):
            avg = info["avg_age_days"]
            avg_s = f"{avg:.0f}d" if avg is not None else "-"
            print(f"  {dom:40} {info['doc_count']:>3} docs  avg-age {avg_s}")
    else:
        text = json.dumps(atlas, indent=2)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"Wrote {args.out}")
        else:
            print(text)

"""
atlas_collectors.py - Dashboard collectors for Context Atlas views.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from atlas_ingest import build_atlas, parse_frontmatter  # noqa: E402
from atlas_layout import squarify  # noqa: E402
from single_repo import REPO_ROOT  # noqa: E402


SCOPES = [
    ("context", "Context"),
    ("active", "Active"),
    ("inbox", "Inbox"),
    ("planned", "Planned"),
    ("archive", "Archive"),
    ("framework", "Framework"),
    ("all", "All"),
]
LARGE_DOC_BYTES = 12000
SIGNAL_PRIORITY = {
    "no_metadata": 0,
    "ownership_overlap": 1,
    "missing_metadata": 2,
    "stuck_lifecycle": 3,
    "very_stale": 4,
    "stale": 5,
    "isolated": 6,
    "large_doc": 7,
    "unreferenced": 8,
    "stale_artifact": 9,
    "missing_description": 10,
}
SEVERITY_PRIORITY = {"critical": 0, "warn": 1, "info": 2}


def collect_atlas_ownership(scope: str = "context") -> dict:
    """Ownership-map payload for `/atlas`."""
    atlas = build_atlas()
    all_docs = list(atlas.get("docs") or [])
    scope = _normalize_scope(scope)
    docs = _filter_docs(all_docs, scope)
    related_paths = _related_paths(atlas.get("edges") or [])
    duplicates = _duplicate_ownership_items(docs)
    duplicate_by_path: dict[str, list[dict]] = {}
    for dup in duplicates:
        for path in dup["paths"]:
            duplicate_by_path.setdefault(path, []).append({
                "item": dup["item"],
                "also_in": [p for p in dup["paths"] if p != path],
            })

    docs_by_domain: dict[str, list[dict]] = {}
    for doc in docs:
        dom = _domain_name(doc)
        docs_by_domain.setdefault(dom, []).append(doc)

    domains = []
    domain_info = _summarize_domains(docs)
    domain_items = [
        {"id": name, "value": info.get("total_bytes") or info.get("doc_count") or 1}
        for name, info in sorted(domain_info.items())
    ]
    domain_rects = {r["id"]: r for r in squarify(domain_items)}
    for name, info in sorted(domain_info.items()):
        doc_list = sorted(docs_by_domain.get(name, []), key=lambda d: (d.get("name") or d.get("path") or ""))
        doc_rects = {
            r["id"]: r
            for r in squarify([
                {"id": d.get("path"), "value": d.get("size_bytes") or 1}
                for d in doc_list
            ])
        }
        enriched_docs = []
        for d in doc_list:
            path = d.get("path")
            card = _doc_card(d, related_paths=related_paths)
            card.update({
                "path": path,
                "name": d.get("name") or Path(path or "").stem,
                "type": d.get("type"),
                "status": d.get("status"),
                "bucket": d.get("bucket"),
                "size_bytes": d.get("size_bytes") or 0,
                "age_days": d.get("age_days"),
                "freshness": _freshness(d.get("age_days")),
                "has_frontmatter": bool(d.get("has_frontmatter")),
                "missing_required": d.get("missing_required") or [],
                "exclusive_count": len(d.get("exclusively_owns") or []),
                "duplicates": duplicate_by_path.get(path, []),
                "rect": doc_rects.get(path),
            })
            card["signals"] = _doc_signals(d, related_paths=related_paths,
                                           duplicate_count=len(card["duplicates"]))
            card["next_action"] = _next_action(card["signals"])
            enriched_docs.append(card)
        domains.append({
            "name": name,
            "doc_count": info.get("doc_count") or len(enriched_docs),
            "total_bytes": info.get("total_bytes") or 0,
            "avg_age_days": info.get("avg_age_days"),
            "rect": domain_rects.get(name),
            "docs": enriched_docs,
            "freshness": _freshness(info.get("avg_age_days")),
            "missing_frontmatter": sum(1 for d in enriched_docs if not d["has_frontmatter"]),
            "duplicate_count": sum(len(d["duplicates"]) for d in enriched_docs),
        })

    summary = {
        "doc_count": len(docs),
        "domain_count": len(domains),
        "missing_frontmatter": sum(1 for d in docs if not d.get("has_frontmatter")),
        "stale_count": sum(1 for d in docs if _freshness(d.get("age_days")) == "critical"),
        "duplicate_count": len(duplicates),
        "needs_attention": sum(
            1 for d in docs
            if _doc_signals(
                d,
                related_paths=related_paths,
                duplicate_count=len(duplicate_by_path.get(d.get("path"), [])),
            )
        ),
    }
    insights = _atlas_insights(
        docs,
        related_paths=related_paths,
        duplicate_by_path=duplicate_by_path,
        lens="ownership",
    )
    return {
        "kind": "atlas_ownership",
        "generated_at": atlas.get("generated_at"),
        "scope": scope,
        "scopes": _scope_counts(all_docs),
        "summary": summary,
        "insights": insights,
        "domains": domains,
        "duplicates": duplicates,
        "_severity": "warn" if summary["duplicate_count"] else "ok",
    }


def collect_atlas_lifecycle(scope: str = "context") -> dict:
    """Read-only lifecycle view: where docs sit by folder/state."""
    atlas = build_atlas()
    all_docs = list(atlas.get("docs") or [])
    scope = _normalize_scope(scope)
    docs = _filter_docs(all_docs, scope)
    related_paths = _related_paths(atlas.get("edges") or [])
    order = [
        ("_inbox", "Inbox"),
        ("_planned", "Planned"),
        ("active", "Active docs"),
        ("_archive", "Archive"),
        ("_bcos-framework", "Framework"),
        ("_collections", "Collections"),
    ]
    buckets = []
    for bucket, label in order:
        items = [d for d in docs if d.get("bucket") == bucket]
        items.sort(key=lambda d: (_age_sort(d.get("age_days")), d.get("name") or d.get("path") or ""))
        buckets.append({
            "id": bucket,
            "label": label,
            "count": len(items),
            "docs": [_doc_card(d, related_paths=related_paths) for d in items],
            "stuck_count": sum(1 for d in items if _is_stuck(bucket, d.get("age_days"))),
        })
    return {
        "kind": "atlas_lifecycle",
        "generated_at": atlas.get("generated_at"),
        "scope": scope,
        "scopes": _scope_counts(all_docs),
        "summary": {
            "doc_count": len(docs),
            "bucket_count": sum(1 for b in buckets if b["count"]),
            "stuck_count": sum(b["stuck_count"] for b in buckets),
            "needs_attention": sum(1 for d in docs if _doc_signals(d, related_paths=related_paths)),
        },
        "insights": _atlas_insights(docs, related_paths=related_paths,
                                    lens="lifecycle"),
        "buckets": buckets,
        "_severity": "warn" if any(b["stuck_count"] for b in buckets) else "ok",
    }


def collect_atlas_relationships(scope: str = "context") -> dict:
    """Declared relationship view from `depends-on` / `consumed-by` frontmatter."""
    atlas = build_atlas()
    all_docs = list(atlas.get("docs") or [])
    scope = _normalize_scope(scope)
    docs = _filter_docs(all_docs, scope)
    included = {d.get("path") for d in docs}
    doc_by_path = {d.get("path"): d for d in all_docs}
    edges = []
    for edge in atlas.get("edges") or []:
        src = edge.get("from")
        tgt = edge.get("to")
        if src not in included:
            continue
        target_in_scope = tgt in included
        target_doc = doc_by_path.get(tgt)
        edges.append({
            "from": src,
            "from_name": (doc_by_path.get(src) or {}).get("name") or Path(str(src)).stem,
            "to": tgt,
            "to_name": (target_doc or {}).get("name") or Path(str(tgt)).stem,
            "kind": edge.get("kind"),
            "target_in_scope": target_in_scope,
        })

    touched = set()
    for edge in edges:
        touched.add(edge["from"])
        if edge["target_in_scope"]:
            touched.add(edge["to"])
    orphans = [
        _doc_card(d, related_paths=touched)
        for d in sorted(docs, key=lambda x: x.get("name") or x.get("path") or "")
        if d.get("has_frontmatter") and d.get("path") not in touched
    ]
    unmapped = [
        _doc_card(d, related_paths=touched)
        for d in sorted(docs, key=lambda x: x.get("name") or x.get("path") or "")
        if not d.get("has_frontmatter")
    ]
    return {
        "kind": "atlas_relationships",
        "generated_at": atlas.get("generated_at"),
        "scope": scope,
        "scopes": _scope_counts(all_docs),
        "summary": {
            "doc_count": len(docs),
            "edge_count": len(edges),
            "orphan_count": len(orphans),
            "unmapped_count": len(unmapped),
            "needs_attention": len(orphans) + len(unmapped),
        },
        "insights": _atlas_insights(docs, related_paths=touched,
                                    lens="relationships"),
        "graph": _relationship_graph(docs, edges, touched),
        "edges": edges,
        "orphans": orphans,
        "unmapped": unmapped,
        "_severity": "warn" if (orphans or unmapped) and docs else "ok",
    }


def collect_atlas_ecosystem(scope: str = "context") -> dict:
    """Operational Atlas view for skills, scripts, agents, and hooks."""
    artifacts = _collect_ecosystem_artifacts()
    refs = _ecosystem_references(artifacts)
    by_path = {a["path"]: a for a in artifacts}
    for ref in refs:
        target = ref.get("to")
        if target in by_path:
            by_path[target].setdefault("referenced_by", []).append(ref.get("from"))

    for artifact in artifacts:
        artifact["signals"] = _ecosystem_signals(artifact)
        artifact["next_action"] = _ecosystem_next_action(artifact["signals"])

    groups = []
    for kind, label in [
        ("skill", "Skills"),
        ("agent", "Agents"),
        ("script", "Scripts"),
        ("hook", "Hooks"),
        ("registry", "Registries"),
        ("template", "Templates"),
    ]:
        items = sorted(
            [a for a in artifacts if a.get("kind") == kind],
            key=lambda a: (a.get("name") or a.get("path") or ""),
        )
        groups.append({
            "id": kind,
            "label": label,
            "count": len(items),
            "items": items,
        })

    signal_cards: dict[str, dict] = {}
    focus = []
    detail_items: dict[str, list[dict]] = {}
    for artifact in artifacts:
        signals = artifact.get("signals") or []
        if not signals:
            continue
        for sig in signals:
            _add_signal_card(signal_cards, sig)
        focus.append({
            "path": artifact.get("path"),
            "name": artifact.get("name"),
            "kind": artifact.get("kind"),
            "bucket": artifact.get("kind"),
            "size_bytes": artifact.get("size_bytes"),
            "age_days": artifact.get("age_days"),
            "signals": signals,
            "next_action": artifact.get("next_action"),
            "reason": signals[0].get("label") if signals else "Needs attention",
            "_rank": _signal_rank(signals[0] if signals else None),
        })
        for sig in signals:
            sid = str(sig.get("id") or "signal")
            detail_items.setdefault(sid, []).append(dict(focus[-1]))
    focus.sort(key=lambda a: (a.get("_rank", 99), _age_sort(a.get("age_days")), a.get("name") or ""))
    for item in focus:
        item.pop("_rank", None)
    for items in detail_items.values():
        items.sort(key=lambda a: (a.get("_rank", 99), _age_sort(a.get("age_days")), a.get("name") or ""))
        for item in items:
            item.pop("_rank", None)

    summary = {
        "artifact_count": len(artifacts),
        "skill_count": sum(1 for a in artifacts if a.get("kind") == "skill"),
        "script_count": sum(1 for a in artifacts if a.get("kind") == "script"),
        "agent_count": sum(1 for a in artifacts if a.get("kind") == "agent"),
        "hook_count": sum(1 for a in artifacts if a.get("kind") == "hook"),
        "reference_count": len(refs),
        "needs_attention": len(focus),
    }
    return {
        "kind": "atlas_ecosystem",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "ecosystem",
        "scopes": _scope_counts(list(build_atlas().get("docs") or [])),
        "summary": summary,
        "insights": {
            "lens": "ecosystem",
            "cards": _ordered_signal_cards(signal_cards),
            "focus_total": len(focus),
            "focus": focus[:10],
            "details": {
                sid: {
                    "total": len(items),
                    "items": items[:120],
                }
                for sid, items in detail_items.items()
            },
        },
        "groups": groups,
        "references": refs[:120],
        "_severity": "warn" if focus else "ok",
    }


def collect_atlas_teaser() -> dict:
    """Small cockpit teaser payload."""
    try:
        atlas = build_atlas()
        docs = _filter_docs(list(atlas.get("docs") or []), "context")
        return {
            "ok": True,
            "doc_count": len(docs),
            "domain_count": len(_summarize_domains(docs)),
            "missing_frontmatter": sum(1 for d in docs if not d.get("has_frontmatter")),
            "stale_count": sum(1 for d in docs if _freshness(d.get("age_days")) == "critical"),
            "href": "/atlas",
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "href": "/atlas"}


def _freshness(age_days) -> str:
    if age_days is None:
        return "muted"
    try:
        age = float(age_days)
    except (TypeError, ValueError):
        return "muted"
    if age <= 30:
        return "ok"
    if age <= 90:
        return "warn"
    return "critical"


def _duplicate_ownership_items(docs: list[dict]) -> list[dict]:
    owners: dict[str, dict] = {}
    for doc in docs:
        path = doc.get("path")
        for raw in doc.get("exclusively_owns") or []:
            key = _ownership_key(raw)
            if not key:
                continue
            entry = owners.setdefault(key, {"item": raw, "paths": []})
            if path and path not in entry["paths"]:
                entry["paths"].append(path)
    return [
        {"item": v["item"], "paths": sorted(v["paths"])}
        for v in owners.values()
        if len(v["paths"]) > 1
    ]


def _ownership_key(s: str) -> str:
    s = str(s or "").lower()
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def _normalize_scope(scope: str | None) -> str:
    known = {k for k, _ in SCOPES}
    s = str(scope or "context").strip().lower()
    return s if s in known else "context"


def _filter_docs(docs: list[dict], scope: str) -> list[dict]:
    scope = _normalize_scope(scope)
    if scope == "all":
        return list(docs)
    if scope == "context":
        return [
            d for d in docs
            if d.get("bucket") in {"active", "_inbox", "_planned", "_archive"}
        ]
    bucket_by_scope = {
        "active": "active",
        "inbox": "_inbox",
        "planned": "_planned",
        "archive": "_archive",
        "framework": "_bcos-framework",
    }
    bucket = bucket_by_scope.get(scope)
    return [d for d in docs if d.get("bucket") == bucket]


def _scope_counts(docs: list[dict]) -> list[dict]:
    return [
        {"id": key, "label": label, "count": len(_filter_docs(docs, key))}
        for key, label in SCOPES
    ]


def _domain_name(doc: dict) -> str:
    if doc.get("cluster"):
        return doc["cluster"]
    if doc.get("bucket") != "active":
        return f"({doc.get('bucket')})"
    return "(unclassified)"


def _summarize_domains(docs: list[dict]) -> dict:
    domains: dict[str, dict] = {}
    for d in docs:
        name = _domain_name(d)
        bucket = domains.setdefault(name, {
            "doc_count": 0, "total_bytes": 0,
            "_age_sum": 0, "_age_n": 0, "doc_paths": [],
        })
        bucket["doc_count"] += 1
        bucket["total_bytes"] += d.get("size_bytes") or 0
        bucket["doc_paths"].append(d.get("path"))
        if d.get("age_days") is not None:
            bucket["_age_sum"] += d["age_days"]
            bucket["_age_n"] += 1
    for bucket in domains.values():
        bucket["avg_age_days"] = (
            bucket["_age_sum"] / bucket["_age_n"]
            if bucket["_age_n"] else None
        )
        del bucket["_age_sum"]
        del bucket["_age_n"]
    return domains


def _doc_card(doc: dict, related_paths: set[str] | None = None) -> dict:
    signals = _doc_signals(doc, related_paths=related_paths)
    card = {
        "path": doc.get("path"),
        "name": doc.get("name") or Path(str(doc.get("path") or "")).stem,
        "type": doc.get("type"),
        "status": doc.get("status"),
        "bucket": doc.get("bucket"),
        "age_days": doc.get("age_days"),
        "freshness": _freshness(doc.get("age_days")),
        "has_frontmatter": bool(doc.get("has_frontmatter")),
        "missing_required": doc.get("missing_required") or [],
        "size_bytes": doc.get("size_bytes") or 0,
        "actions": _lifecycle_actions(doc),
    }
    card["signals"] = signals
    card["next_action"] = _next_action(signals)
    return card


def _lifecycle_actions(doc: dict) -> list[dict]:
    bucket = doc.get("bucket")
    path = doc.get("path")
    if not path:
        return []
    if bucket == "_inbox":
        return [{"id": "promote", "label": "Promote", "target_bucket": "active"}]
    if bucket == "_planned":
        return [{"id": "activate", "label": "Activate", "target_bucket": "active"}]
    if bucket == "active":
        return [{"id": "archive", "label": "Archive", "target_bucket": "_archive"}]
    if bucket == "_archive":
        return [{"id": "restore", "label": "Restore", "target_bucket": "active"}]
    return []


def _relationship_graph(docs: list[dict], edges: list[dict], touched: set[str]) -> dict:
    nodes = []
    for doc in docs:
        path = doc.get("path")
        signal_count = len(_doc_signals(doc, related_paths=touched))
        nodes.append({
            "id": path,
            "label": doc.get("name") or Path(str(path)).stem,
            "bucket": doc.get("bucket"),
            "status": doc.get("status"),
            "has_frontmatter": bool(doc.get("has_frontmatter")),
            "signal_count": signal_count,
            "degree": sum(
                1 for edge in edges
                if edge.get("from") == path or (edge.get("target_in_scope") and edge.get("to") == path)
            ),
        })
    return {"nodes": nodes, "edges": edges}


def _collect_ecosystem_artifacts() -> list[dict]:
    artifacts: list[dict] = []
    artifacts.extend(_skill_artifacts())
    artifacts.extend(_agent_artifacts())
    artifacts.extend(_file_artifacts(REPO_ROOT / ".claude" / "scripts", "script"))
    artifacts.extend(_file_artifacts(REPO_ROOT / ".claude" / "hooks", "hook"))
    artifacts.extend(_file_artifacts(REPO_ROOT / ".claude" / "registries", "registry"))
    artifacts.extend(_file_artifacts(REPO_ROOT / ".claude" / "templates", "template"))
    return artifacts


def _skill_artifacts() -> list[dict]:
    root = REPO_ROOT / ".claude" / "skills"
    artifacts = []
    if not root.is_dir():
        return artifacts
    for skill_md in sorted(root.glob("*/SKILL.md")):
        artifact = _artifact_from_path(skill_md, "skill")
        meta = parse_frontmatter(_read_text(skill_md) or "") or {}
        artifact["name"] = meta.get("name") or skill_md.parent.name
        artifact["description"] = meta.get("description") or ""
        artifact["folder"] = skill_md.parent.name
        artifacts.append(artifact)
    return artifacts


def _agent_artifacts() -> list[dict]:
    root = REPO_ROOT / ".claude" / "agents"
    artifacts = []
    if not root.is_dir():
        return artifacts
    for agent_md in sorted(root.glob("*/AGENT.md")):
        artifact = _artifact_from_path(agent_md, "agent")
        artifact["name"] = agent_md.parent.name
        text = _read_text(agent_md) or ""
        title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("#")), "")
        artifact["description"] = title
        artifact["folder"] = agent_md.parent.name
        artifacts.append(artifact)
    for finder in sorted(root.glob("*/find_agents.sh")):
        artifacts.append(_artifact_from_path(finder, "agent"))
    return artifacts


def _file_artifacts(root: Path, kind: str) -> list[dict]:
    artifacts = []
    if not root.is_dir():
        return artifacts
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if "__pycache__" in rel_parts or path.suffix == ".pyc":
            continue
        artifacts.append(_artifact_from_path(path, kind))
    return artifacts


def _artifact_from_path(path: Path, kind: str) -> dict:
    rel = path.relative_to(REPO_ROOT).as_posix()
    try:
        stat = path.stat()
        age = (datetime.now(timezone.utc) - datetime.fromtimestamp(stat.st_mtime, timezone.utc)).days
        size = stat.st_size
    except OSError:
        age = None
        size = 0
    return {
        "path": rel,
        "name": path.stem if path.name not in {"SKILL.md", "AGENT.md"} else path.parent.name,
        "kind": kind,
        "extension": path.suffix.lower(),
        "size_bytes": size,
        "age_days": age,
        "description": "",
        "referenced_by": [],
    }


def _ecosystem_references(artifacts: list[dict]) -> list[dict]:
    targets = {a["path"]: a for a in artifacts}
    if not targets:
        return []
    search_roots = [
        REPO_ROOT / "docs",
        REPO_ROOT / ".claude" / "skills",
        REPO_ROOT / ".claude" / "agents",
        REPO_ROOT / ".claude" / "hooks",
        REPO_ROOT / ".claude" / "scripts",
        REPO_ROOT / ".claude" / "registries",
    ]
    refs = []
    seen: set[tuple[str, str]] = set()
    for root in search_roots:
        if not root.is_dir():
            continue
        for src in root.rglob("*"):
            if not src.is_file() or src.suffix.lower() in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico"}:
                continue
            if "__pycache__" in src.parts:
                continue
            text = _read_text(src)
            if not text:
                continue
            src_rel = src.relative_to(REPO_ROOT).as_posix()
            for target_path, artifact in targets.items():
                if src_rel == target_path:
                    continue
                terms = [target_path]
                basename = Path(target_path).name
                if basename not in {"SKILL.md", "AGENT.md", "__init__.py"}:
                    terms.append(basename)
                folder = artifact.get("folder") or artifact.get("name")
                if artifact.get("kind") in {"skill", "agent"} and folder:
                    terms.append(str(folder))
                if any(term and term in text for term in terms):
                    key = (src_rel, target_path)
                    if key in seen:
                        continue
                    seen.add(key)
                    refs.append({
                        "from": src_rel,
                        "to": target_path,
                        "kind": "mentions",
                    })
    return refs


def _ecosystem_signals(artifact: dict) -> list[dict]:
    signals = []
    if artifact.get("kind") in {"skill", "agent"} and not artifact.get("description"):
        signals.append({
            "id": "missing_description",
            "label": "Missing description",
            "severity": "warn",
            "detail": "No summary/description was found.",
        })
    if not artifact.get("referenced_by"):
        signals.append({
            "id": "unreferenced",
            "label": "Unreferenced",
            "severity": "info",
            "detail": "No local docs/skills/scripts mention this artifact.",
        })
    age = artifact.get("age_days")
    if age is not None and age > 180:
        signals.append({
            "id": "stale_artifact",
            "label": "Stale artifact",
            "severity": "warn",
            "detail": f"Last modified {age} days ago.",
        })
    return signals


def _ecosystem_next_action(signals: list[dict]) -> str:
    ids = {s.get("id") for s in signals}
    if "missing_description" in ids:
        return "Add description"
    if "stale_artifact" in ids:
        return "Review artifact"
    if "unreferenced" in ids:
        return "Check usage"
    return "No action"


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _atlas_insights(
    docs: list[dict],
    related_paths: set[str] | None = None,
    duplicate_by_path: dict[str, list[dict]] | None = None,
    lens: str = "ownership",
) -> dict:
    """Small decision layer shared by Atlas lenses."""
    duplicate_by_path = duplicate_by_path or {}
    cards: dict[str, dict] = {}
    focus: list[dict] = []
    detail_items: dict[str, list[dict]] = {}
    for doc in docs:
        path = doc.get("path")
        duplicate_count = len(duplicate_by_path.get(path, []))
        signals = _doc_signals(
            doc,
            related_paths=related_paths,
            duplicate_count=duplicate_count,
        )
        if not signals:
            continue
        for sig in signals:
            _add_signal_card(cards, sig)
        card = _doc_card(doc, related_paths=related_paths)
        card["signals"] = signals
        card["next_action"] = _next_action(signals)
        if duplicate_count:
            card["duplicates"] = duplicate_by_path.get(path, [])
        dominant = _dominant_signal(signals)
        card["reason"] = dominant.get("label") if dominant else "Needs attention"
        card["_rank"] = _signal_rank(dominant)
        focus.append(card)
        for sig in signals:
            sid = str(sig.get("id") or "signal")
            detail_items.setdefault(sid, []).append(dict(card))

    focus.sort(key=lambda d: (
        d.get("_rank", 99),
        _age_sort(d.get("age_days")),
        d.get("name") or d.get("path") or "",
    ))
    for item in focus:
        item.pop("_rank", None)
    for items in detail_items.values():
        items.sort(key=lambda d: (
            d.get("_rank", 99),
            _age_sort(d.get("age_days")),
            d.get("name") or d.get("path") or "",
        ))
        for item in items:
            item.pop("_rank", None)

    return {
        "lens": lens,
        "cards": _ordered_signal_cards(cards),
        "focus_total": len(focus),
        "focus": focus[:8],
        "details": {
            sid: {
                "total": len(items),
                "items": items[:120],
            }
            for sid, items in detail_items.items()
        },
    }


def _add_signal_card(cards: dict[str, dict], sig: dict) -> None:
    sid = str(sig.get("id") or "signal")
    entry = cards.setdefault(sid, {
        "id": sid,
        "label": sig.get("label") or sid.replace("_", " ").title(),
        "count": 0,
        "severity": sig.get("severity") or "info",
        "detail": sig.get("detail") or "",
    })
    entry["count"] += 1
    if _severity_rank(sig) < _severity_rank(entry):
        entry["severity"] = sig.get("severity") or entry["severity"]
        entry["detail"] = sig.get("detail") or entry["detail"]


def _ordered_signal_cards(cards: dict[str, dict]) -> list[dict]:
    ordered = list(cards.values())
    ordered.sort(key=lambda c: (
        SIGNAL_PRIORITY.get(c.get("id"), 99),
        _severity_rank(c),
        c.get("label") or "",
    ))
    return ordered[:6]


def _dominant_signal(signals: list[dict]) -> dict | None:
    if not signals:
        return None
    return sorted(signals, key=_signal_rank)[0]


def _signal_rank(sig: dict | None) -> int:
    if not sig:
        return 99
    return SIGNAL_PRIORITY.get(sig.get("id"), 90) * 10 + _severity_rank(sig)


def _severity_rank(sig: dict | None) -> int:
    if not sig:
        return 99
    return SEVERITY_PRIORITY.get(sig.get("severity"), 3)


def _doc_signals(doc: dict, related_paths: set[str] | None = None,
                 duplicate_count: int = 0) -> list[dict]:
    signals: list[dict] = []
    bucket = doc.get("bucket")
    if bucket not in {"active", "_inbox", "_planned"}:
        return signals
    if _metadata_required(doc) and not doc.get("has_frontmatter"):
        signals.append({
            "id": "no_metadata",
            "label": "No metadata",
            "severity": "critical",
            "detail": "No YAML frontmatter was found.",
        })
        return signals
    missing = doc.get("missing_required") or []
    if not _metadata_required(doc):
        missing = []
    if missing:
        signals.append({
            "id": "missing_metadata",
            "label": "Missing metadata",
            "severity": "warn",
            "detail": ", ".join(missing),
        })
    age = doc.get("age_days")
    if age is not None:
        try:
            age_i = int(age)
        except (TypeError, ValueError):
            age_i = 0
        if age_i > 180:
            signals.append({
                "id": "very_stale",
                "label": "Very stale",
                "severity": "critical",
                "detail": f"Last updated {age_i} days ago.",
            })
        elif age_i > 90:
            signals.append({
                "id": "stale",
                "label": "Stale",
                "severity": "warn",
                "detail": f"Last updated {age_i} days ago.",
            })
    if _is_stuck(bucket, age):
        label = "Inbox aging" if bucket == "_inbox" else "Planned aging"
        signals.append({
            "id": "stuck_lifecycle",
            "label": label,
            "severity": "warn",
            "detail": "This item has been waiting in its lifecycle bucket.",
        })
    if bucket == "active" and (doc.get("size_bytes") or 0) >= LARGE_DOC_BYTES:
        signals.append({
            "id": "large_doc",
            "label": "Large doc",
            "severity": "info",
            "detail": "Large enough to consider splitting if ownership is broad.",
        })
    related_paths = related_paths or set()
    if bucket == "active" and doc.get("path") not in related_paths:
        signals.append({
            "id": "isolated",
            "label": "Isolated",
            "severity": "info",
            "detail": "No declared relationship edges in this scope.",
        })
    if bucket == "active" and duplicate_count:
        signals.append({
            "id": "ownership_overlap",
            "label": "Ownership overlap",
            "severity": "critical",
            "detail": f"{duplicate_count} ownership item(s) also appear elsewhere.",
        })
    return signals


def _metadata_required(doc: dict) -> bool:
    return doc.get("bucket") == "active"


def _next_action(signals: list[dict]) -> str:
    ids = {s.get("id") for s in signals}
    if "no_metadata" in ids:
        return "Add frontmatter"
    if "missing_metadata" in ids:
        return "Complete metadata"
    if "ownership_overlap" in ids:
        return "Resolve ownership"
    if "stuck_lifecycle" in ids:
        return "Triage lifecycle"
    if "very_stale" in ids or "stale" in ids:
        return "Review freshness"
    if "isolated" in ids:
        return "Add relationships"
    if "large_doc" in ids:
        return "Check split"
    return "No action"


def _related_paths(edges: list[dict]) -> set[str]:
    paths: set[str] = set()
    for edge in edges:
        src = edge.get("from")
        tgt = edge.get("to")
        if isinstance(src, str) and "/" in src:
            paths.add(src)
        if isinstance(tgt, str) and "/" in tgt:
            paths.add(tgt)
    return paths


def _age_sort(age_days) -> int:
    return -1 if age_days is None else -int(age_days)


def _is_stuck(bucket: str, age_days) -> bool:
    if age_days is None:
        return False
    try:
        age = int(age_days)
    except (TypeError, ValueError):
        return False
    if bucket == "_inbox":
        return age > 14
    if bucket == "_planned":
        return age > 180
    return False

#!/usr/bin/env python3
"""
BCOS inventory generator.

Builds a developer/agent control map of the local BCOS environment: documents,
skills, agents, scheduled jobs, generated outputs, plans, workflow triggers, and
the file formats they use. The JSON is the source for machines; the Markdown is
the source for humans.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

if str(SCRIPT_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPT_DIR))

from context_index import build_context_index, parse_frontmatter  # noqa: E402


DEFAULT_JSON = Path(".claude/quality/bcos-inventory.json")
DEFAULT_MARKDOWN = Path("docs/bcos-control-map.md")

SCAN_ROOTS = ("docs", ".claude")
IGNORED_PARTS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "worktrees",
}
DATA_SUFFIXES = {".md", ".json", ".jsonl", ".yml", ".yaml", ".sqlite", ".sqlite3", ".db"}

GENERATED_OUTPUTS: dict[str, dict[str, str]] = {
    "docs/bcos-control-map.md": {
        "producer": ".claude/scripts/bcos_inventory.py",
        "source_mode": "mechanical",
        "description": "Human-readable BCOS control map generated from bcos-inventory.json.",
    },
    ".claude/quality/bcos-inventory.json": {
        "producer": ".claude/scripts/bcos_inventory.py",
        "source_mode": "mechanical",
        "description": "Machine-readable BCOS control map.",
    },
    ".claude/quality/context-index.json": {
        "producer": ".claude/scripts/context_index.py",
        "source_mode": "mechanical",
        "description": "Canonical indexed model of docs/.",
    },
    "docs/document-index.md": {
        "producer": ".claude/scripts/build_document_index.py",
        "source_mode": "mechanical",
        "description": "Human-readable document index generated from context-index.",
    },
    "docs/.wake-up-context.md": {
        "producer": ".claude/scripts/generate_wakeup_context.py",
        "source_mode": "mechanical",
        "description": "Session-start compressed context snapshot.",
    },
    "docs/_inbox/daily-digest.md": {
        "producer": "schedule-dispatcher",
        "source_mode": "mixed",
        "description": "Daily maintenance digest; overwritten by scheduled runs.",
    },
    "docs/_inbox/daily-digest.json": {
        "producer": ".claude/scripts/digest_sidecar.py",
        "source_mode": "mechanical",
        "description": "Typed-event sidecar consumed by dashboard cards.",
    },
    ".claude/quality/ecosystem/state.json": {
        "producer": ".claude/scripts/refresh_ecosystem_state.py",
        "source_mode": "mechanical",
        "description": "Skill/agent ecosystem inventory.",
    },
    ".claude/quality/ecosystem/learned-rules.json": {
        "producer": ".claude/scripts/promote_resolutions.py",
        "source_mode": "mechanical",
        "description": "Derived self-learning rule set.",
    },
}

APPEND_ONLY = {
    ".claude/quality/ecosystem/resolutions.jsonl",
    ".claude/hook_state/schedule-diary.jsonl",
}


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _format_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "markdown"
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix in {".yml", ".yaml"}:
        return "yaml"
    if suffix in {".sqlite", ".sqlite3", ".db"}:
        return "sqlite"
    if suffix == ".py":
        return "python"
    if suffix in {".sh", ".ps1"}:
        return "shell"
    return suffix[1:] or "unknown"


def _area_for(rel: str) -> str:
    if rel.startswith("docs/"):
        return "docs"
    if rel.startswith(".claude/skills/"):
        return "skill"
    if rel.startswith(".claude/agents/"):
        return "agent"
    if rel.startswith(".claude/scripts/"):
        return "script"
    if rel.startswith(".claude/quality/"):
        return "quality"
    if rel.startswith(".claude/hooks/"):
        return "hook"
    return rel.split("/", 1)[0]


def _source_mode(rel: str, area: str, doc: dict[str, Any] | None) -> str:
    if rel in GENERATED_OUTPUTS:
        return GENERATED_OUTPUTS[rel]["source_mode"]
    if rel in APPEND_ONLY or rel.endswith(".jsonl"):
        return "append-only-log"
    if area in {"script", "hook"}:
        return "code"
    if area in {"skill", "agent"}:
        return "llm-instruction"
    if area == "quality":
        if rel.endswith((".template.json", ".template.yml", ".template.yaml")):
            return "config-template"
        if "/fixtures/" in rel:
            return "test-fixture"
        return "config-or-derived"
    if doc:
        zone = doc.get("zone")
        if zone == "generated":
            return "mechanical"
        if zone == "inbox":
            return "raw-or-llm"
        if zone in {"active", "framework", "planned", "wiki"}:
            return "human-or-llm"
    return "unknown"


def _artifact_kind(rel: str, area: str, doc: dict[str, Any] | None) -> str:
    if rel in GENERATED_OUTPUTS:
        return "generated-output"
    if rel in APPEND_ONLY or rel.endswith(".jsonl"):
        return "event-log"
    if area == "skill":
        return "skill"
    if area == "agent":
        return "agent"
    if area == "script":
        return "script"
    if area == "hook":
        return "hook"
    if area == "quality":
        if "/sessions/" in rel or "/_planned/" in rel:
            return "plan-or-state"
        return "quality-state"
    if doc:
        return f"doc:{doc.get('zone') or 'unknown'}"
    return "artifact"


def _updated_by(rel: str, source_mode: str) -> str:
    if rel in GENERATED_OUTPUTS:
        return GENERATED_OUTPUTS[rel]["producer"]
    if source_mode == "append-only-log":
        return "runtime append"
    if source_mode in {"code", "llm-instruction", "human-or-llm"}:
        return "developer/AI edit"
    if source_mode == "raw-or-llm":
        return "user/AI capture"
    if source_mode.startswith("config"):
        return "developer/AI config edit"
    return "unknown"


def iter_artifact_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        base = root / root_name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(root).parts
            if any(part in IGNORED_PARTS for part in rel_parts):
                continue
            if path.suffix.lower() in DATA_SUFFIXES or root_name == ".claude":
                files.append(path)
    return sorted(files, key=lambda p: _rel(p, root))


def collect_artifacts(root: Path, docs_by_path: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for path in iter_artifact_files(root):
        rel = _rel(path, root)
        doc = docs_by_path.get(rel)
        area = _area_for(rel)
        source_mode = _source_mode(rel, area, doc)
        stat = path.stat()
        artifacts.append({
            "path": rel,
            "format": _format_for(path),
            "area": area,
            "zone": doc.get("zone") if doc else None,
            "artifact_kind": _artifact_kind(rel, area, doc),
            "source_mode": source_mode,
            "updated_by": _updated_by(rel, source_mode),
            "size_bytes": stat.st_size,
            "modified": _dt.datetime.fromtimestamp(stat.st_mtime).date().isoformat(),
            "append_only": rel in APPEND_ONLY or rel.endswith(".jsonl"),
            "generated": rel in GENERATED_OUTPUTS or bool(doc and doc.get("zone") == "generated"),
            "status": doc.get("status") if doc else None,
            "type": doc.get("type") if doc else None,
            "cluster": doc.get("cluster") if doc else None,
        })
    return artifacts


def collect_skills(root: Path) -> list[dict[str, Any]]:
    out = []
    for skill_dir in sorted((root / ".claude" / "skills").glob("*")):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        meta = parse_frontmatter(_read_text(skill_file)) if skill_file.exists() else None
        out.append({
            "id": skill_dir.name,
            "path": _rel(skill_file, root) if skill_file.exists() else _rel(skill_dir, root),
            "has_skill_md": skill_file.exists(),
            "description": (meta or {}).get("description"),
            "source_mode": "llm-instruction",
        })
    return out


def collect_agents(root: Path) -> list[dict[str, Any]]:
    out = []
    for agent_dir in sorted((root / ".claude" / "agents").glob("*")):
        if not agent_dir.is_dir():
            continue
        agent_file = agent_dir / "AGENT.md"
        out.append({
            "id": agent_dir.name,
            "path": _rel(agent_file, root) if agent_file.exists() else _rel(agent_dir, root),
            "has_agent_md": agent_file.exists(),
            "source_mode": "llm-instruction",
        })
    return out


EMITS_RE = re.compile(r"emits-finding-types:\s*\n(?P<body>(?:\s+-\s+[-a-zA-Z0-9_]+\s*\n?)+)")


def _parse_emits(text: str) -> list[str]:
    match = EMITS_RE.search(text)
    if not match:
        return []
    emits = []
    for line in match.group("body").splitlines():
        _, _, value = line.partition("-")
        value = value.strip()
        if value:
            emits.append(value)
    return emits


def collect_jobs(root: Path) -> list[dict[str, Any]]:
    config = _read_json(root / ".claude" / "quality" / "schedule-config.template.json") or {}
    configured = config.get("jobs") or {}
    refs_dir = root / ".claude" / "skills" / "schedule-dispatcher" / "references"
    job_ids = set(configured)
    job_ids.update(p.stem.removeprefix("job-") for p in refs_dir.glob("job-*.md") if p.is_file())
    jobs = []
    for job_id in sorted(job_ids):
        ref = refs_dir / f"job-{job_id}.md"
        ref_text = _read_text(ref)
        cfg = configured.get(job_id) or {}
        jobs.append({
            "id": job_id,
            "enabled": cfg.get("enabled"),
            "schedule": cfg.get("schedule"),
            "about": cfg.get("_about"),
            "reference": _rel(ref, root) if ref.exists() else None,
            "has_reference": ref.exists(),
            "emits_finding_types": _parse_emits(ref_text),
            "trigger": "schedule-dispatcher",
        })
    return jobs


def collect_plans(root: Path) -> list[dict[str, Any]]:
    plan_files = []
    for base in (root / "docs" / "_planned", root / ".claude" / "quality" / "sessions"):
        if base.exists():
            plan_files.extend(base.rglob("plan-manifest.json"))
    plans = []
    for path in sorted(plan_files):
        data = _read_json(path) or {}
        tasks = data.get("tasks") or data.get("plan", {}).get("tasks") or []
        counts = Counter(str(task.get("status") or "unknown") for task in tasks if isinstance(task, dict))
        plans.append({
            "path": _rel(path, root),
            "session_id": data.get("sessionId"),
            "status": data.get("planStatus") or data.get("status"),
            "scenario": data.get("scenarioType"),
            "task_description": data.get("taskDescription") or data.get("title"),
            "total_tasks": len(tasks),
            "task_status_counts": dict(sorted(counts.items())),
        })
    return plans


def collect_workflows(root: Path, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    workflows = [
        {
            "id": "context-index",
            "trigger": "manual or index-health job",
            "inputs": ["docs/**/*.md"],
            "outputs": [".claude/quality/context-index.json"],
            "mode": "mechanical",
        },
        {
            "id": "document-index",
            "trigger": "manual or index-health job",
            "inputs": [".claude/quality/context-index.json"],
            "outputs": ["docs/document-index.md"],
            "mode": "mechanical",
        },
        {
            "id": "bcos-inventory",
            "trigger": "manual or future index-health job",
            "inputs": ["docs/**", ".claude/**"],
            "outputs": [".claude/quality/bcos-inventory.json", "docs/bcos-control-map.md"],
            "mode": "mechanical",
        },
        {
            "id": "daily-maintenance",
            "trigger": "scheduled bcos-{project} task",
            "inputs": [".claude/quality/schedule-config.json", ".claude/skills/schedule-dispatcher/references/job-*.md"],
            "outputs": ["docs/_inbox/daily-digest.md", "docs/_inbox/daily-digest.json"],
            "mode": "mixed",
        },
        {
            "id": "self-learning",
            "trigger": "dashboard/headless actions record resolutions",
            "inputs": [".claude/quality/ecosystem/resolutions.jsonl"],
            "outputs": [".claude/quality/ecosystem/learned-rules.json"],
            "mode": "mechanical",
        },
    ]
    for job in jobs:
        workflows.append({
            "id": f"job:{job['id']}",
            "trigger": f"{job.get('schedule') or 'unscheduled'} via schedule-dispatcher",
            "inputs": [job.get("reference") or "(missing reference)"],
            "outputs": ["daily digest result", "typed-event findings" if job.get("emits_finding_types") else "job notes"],
            "mode": "mechanical" if job["id"].startswith(("wiki-", "index-", "auto-fix")) else "mixed",
        })
    return workflows


def collect_risks(root: Path, inventory: dict[str, Any]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    docs_by_path = {doc["path"]: doc for doc in inventory["documents"]}
    for required in ("docs/table-of-context.md", "docs/current-state.md"):
        if required not in docs_by_path and not (root / required).exists():
            risks.append({
                "severity": "medium",
                "area": "context-baseline",
                "message": f"Missing canonical context document: {required}",
            })

    disk_skills = {skill["id"] for skill in inventory["skills"] if skill["id"] != "skill-discovery"}
    state = _read_json(root / ".claude" / "quality" / "ecosystem" / "state.json") or {}
    state_skills = set((state.get("inventory") or {}).get("skills", {}).get("list") or [])
    if state_skills and disk_skills != state_skills:
        risks.append({
            "severity": "high",
            "area": "ecosystem-state",
            "message": f"Skill registry drift: disk={len(disk_skills)} state.json={len(state_skills)}",
        })

    for job in inventory["jobs"]:
        if not job["has_reference"]:
            risks.append({
                "severity": "medium",
                "area": "schedule",
                "message": f"Scheduled job has no job reference: {job['id']}",
            })
        if job["has_reference"] and not job["emits_finding_types"] and job["id"] not in {"auto-fix-audit"}:
            risks.append({
                "severity": "low",
                "area": "typed-events",
                "message": f"Job reference does not declare emits-finding-types: {job['id']}",
            })

    for rel, details in GENERATED_OUTPUTS.items():
        if not (root / rel).exists() and rel != ".claude/quality/bcos-inventory.json":
            risks.append({
                "severity": "low",
                "area": "generated-output",
                "message": f"Generated output is absent until first run: {rel} ({details['producer']})",
            })

    return risks


def build_inventory(root: Path | None = None, now: _dt.datetime | None = None) -> dict[str, Any]:
    root = (root or REPO_ROOT).resolve()
    now = now or _dt.datetime.now(_dt.timezone.utc)
    context = build_context_index(root, now)
    docs = context.get("docs", [])
    docs_by_path = {doc.get("path"): doc for doc in docs if doc.get("path")}
    artifacts = collect_artifacts(root, docs_by_path)
    skills = collect_skills(root)
    agents = collect_agents(root)
    jobs = collect_jobs(root)
    plans = collect_plans(root)
    workflows = collect_workflows(root, jobs)

    inventory = {
        "schema_version": 1,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "repo_root": str(root),
        "repo_name": root.name,
        "documents": docs,
        "artifacts": artifacts,
        "skills": skills,
        "agents": agents,
        "jobs": jobs,
        "plans": plans,
        "workflows": workflows,
        "outputs": [
            {"path": path, **details, "exists": (root / path).exists()}
            for path, details in sorted(GENERATED_OUTPUTS.items())
        ],
        "summaries": {
            "artifact_formats": dict(sorted(Counter(a["format"] for a in artifacts).items())),
            "artifact_kinds": dict(sorted(Counter(a["artifact_kind"] for a in artifacts).items())),
            "source_modes": dict(sorted(Counter(a["source_mode"] for a in artifacts).items())),
            "document_zones": context.get("summaries", {}).get("zones", {}),
            "document_types": context.get("summaries", {}).get("types", {}),
            "skills": len(skills),
            "agents": len(agents),
            "jobs": len(jobs),
            "plans": len(plans),
        },
    }
    inventory["risks"] = collect_risks(root, inventory)
    return inventory


def mark_output_paths_written(inventory: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    written = {json_path.as_posix(), markdown_path.as_posix()}
    for output in inventory.get("outputs", []):
        if output.get("path") in written:
            output["exists"] = True


def _fmt(value: Any, fallback: str = "-") -> str:
    if value is None or value == "" or value == []:
        return fallback
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else fallback
    if isinstance(value, dict):
        return ", ".join(f"{k}:{v}" for k, v in value.items()) if value else fallback
    return str(value)


def _table(lines: list[str], headers: list[str], rows: list[list[Any]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(_fmt(cell).replace("\n", " ") for cell in row) + " |")
    lines.append("")


def render_markdown(inventory: dict[str, Any]) -> str:
    today = _dt.date.fromisoformat(inventory["generated_at"][:10]).isoformat()
    summaries = inventory["summaries"]
    lines: list[str] = [
        "---",
        'name: "BCOS Control Map"',
        "type: reference",
        'cluster: "Framework Operations"',
        'version: "1.0.0"',
        "status: active",
        f'created: "{today}"',
        f'last-updated: "{today}"',
        "tags: [bcos, inventory, generated]",
        "---",
        "",
        "# BCOS Control Map",
        "",
        f"> **Generated:** {inventory['generated_at']} by `.claude/scripts/bcos_inventory.py`",
        ">",
        "> Do not hand-edit this file. Regenerate with `python .claude/scripts/bcos_inventory.py`.",
        "",
        "## Ownership Specification",
        "",
        "**DOMAIN:** Developer and AI navigation map for the local BCOS environment.",
        "",
        "**EXCLUSIVELY_OWNS:** Inventory of BCOS artifacts, generated outputs, workflows, triggers, plans, and maintenance risks.",
        "",
        "**STRICTLY_AVOIDS:** Business truth, strategic decisions, and source content owned by canonical data points.",
        "",
        "## At a Glance",
        "",
    ]
    _table(lines, ["Surface", "Count"], [
        ["Documents", len(inventory["documents"])],
        ["Artifacts", len(inventory["artifacts"])],
        ["Skills", summaries["skills"]],
        ["Agents", summaries["agents"]],
        ["Jobs", summaries["jobs"]],
        ["Plans", summaries["plans"]],
        ["Risks", len(inventory["risks"])],
    ])

    lines.extend(["## Artifact Formats", ""])
    _table(lines, ["Format", "Count"], [[k, v] for k, v in summaries["artifact_formats"].items()])

    lines.extend(["## Source Modes", ""])
    _table(lines, ["Mode", "Count", "Meaning"], [
        ["mechanical", summaries["source_modes"].get("mechanical", 0), "Deterministically generated by scripts/jobs."],
        ["human-or-llm", summaries["source_modes"].get("human-or-llm", 0), "Canonical docs edited by user/AI."],
        ["mixed", summaries["source_modes"].get("mixed", 0), "Mechanical scaffold plus human/AI judgment."],
        ["llm-instruction", summaries["source_modes"].get("llm-instruction", 0), "Skills/agents that guide AI behavior."],
        ["code", summaries["source_modes"].get("code", 0), "Executable scripts/hooks."],
        ["config-or-derived", summaries["source_modes"].get("config-or-derived", 0), "Runtime state or editable config."],
        ["append-only-log", summaries["source_modes"].get("append-only-log", 0), "Event logs; append, do not rewrite casually."],
    ])

    lines.extend(["## Generated Outputs", ""])
    _table(lines, ["Path", "Producer", "Mode", "Exists", "Purpose"], [
        [out["path"], out["producer"], out["source_mode"], "yes" if out["exists"] else "no", out["description"]]
        for out in inventory["outputs"]
    ])

    lines.extend(["## Working Document Inventory", ""])
    doc_rows = []
    for doc in sorted(inventory["documents"], key=lambda d: (d.get("zone") or "", d.get("path") or "")):
        doc_rows.append([
            doc.get("path"),
            doc.get("zone"),
            doc.get("type"),
            doc.get("status"),
            doc.get("cluster"),
            doc.get("last_updated") or doc.get("modified"),
            "yes" if doc.get("has_frontmatter") else "no",
        ])
    _table(lines, ["Path", "Zone", "Type", "Status", "Cluster", "Updated", "Frontmatter"], doc_rows)

    lines.extend(["## Skills And Agents", ""])
    _table(lines, ["Kind", "ID", "Path", "Instruction File"], (
        [["skill", s["id"], s["path"], "yes" if s["has_skill_md"] else "no"] for s in inventory["skills"]]
        + [["agent", a["id"], a["path"], "yes" if a["has_agent_md"] else "no"] for a in inventory["agents"]]
    ))

    lines.extend(["## Scheduled Jobs And Triggers", ""])
    _table(lines, ["Job", "Enabled", "Schedule", "Reference", "Finding Types"], [
        [job["id"], job.get("enabled"), job.get("schedule"), job.get("reference"), job.get("emits_finding_types")]
        for job in inventory["jobs"]
    ])

    lines.extend(["## Plans", ""])
    _table(lines, ["Plan", "Status", "Scenario", "Tasks", "Task Status Counts"], [
        [plan["path"], plan.get("status"), plan.get("scenario"), plan.get("total_tasks"), plan.get("task_status_counts")]
        for plan in inventory["plans"]
    ])

    lines.extend([
        "## Workflow Graph",
        "",
        "```mermaid",
        "flowchart TD",
        '  docs["docs/**/*.md"] --> context["context-index.json"]',
        '  context --> docindex["document-index.md"]',
        '  context --> search["context search / bundle / Galaxy"]',
        '  all["docs + .claude"] --> inventory["bcos-inventory.json"]',
        '  inventory --> map["bcos-control-map.md"]',
        '  jobs["schedule-config + job refs"] --> digest["daily digest md/json"]',
        '  digest --> dashboard["dashboard cards"]',
        '  dashboard --> resolutions["resolutions.jsonl"]',
        '  resolutions --> rules["learned-rules.json"]',
        "```",
        "",
        "## Risks And Drift",
        "",
    ])
    if inventory["risks"]:
        _table(lines, ["Severity", "Area", "Message"], [
            [risk["severity"], risk["area"], risk["message"]] for risk in inventory["risks"]
        ])
    else:
        lines.append("No inventory risks detected.")
        lines.append("")

    lines.extend([
        "## Regeneration",
        "",
        "```powershell",
        "python .claude/scripts/bcos_inventory.py",
        "```",
        "",
        "Machine-readable source: `.claude/quality/bcos-inventory.json`.",
        "",
    ])
    return "\n".join(lines)


def write_inventory(root: Path, json_path: Path, markdown_path: Path, now: _dt.datetime | None = None) -> dict[str, Any]:
    inventory = build_inventory(root, now)
    mark_output_paths_written(inventory, json_path, markdown_path)
    json_out = root / json_path
    md_out = root / markdown_path
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(inventory), encoding="utf-8")
    return inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate BCOS control-map inventory.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    inventory = build_inventory(root)
    if args.dry_run:
        print(json.dumps({
            "repo": inventory["repo_name"],
            "documents": len(inventory["documents"]),
            "artifacts": len(inventory["artifacts"]),
            "skills": len(inventory["skills"]),
            "jobs": len(inventory["jobs"]),
            "risks": len(inventory["risks"]),
        }, indent=2))
        return 0

    json_out = root / args.json
    md_out = root / args.markdown
    mark_output_paths_written(inventory, args.json, args.markdown)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(inventory), encoding="utf-8")
    print(f"Wrote {json_out}")
    print(f"Wrote {md_out}")
    print(f"Inventory: {len(inventory['documents'])} docs, {len(inventory['artifacts'])} artifacts, {len(inventory['risks'])} risks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
CLEAR Context OS — Ecosystem State Refresh

Regenerates `.claude/quality/ecosystem/state.json` from disk. Treats state.json
as a derived artifact: it records what discovery found, not authored truth.

This implements lesson L-INIT-20260404-009:
"Discovery scripts are the source of truth for what exists. State files
record what discovery found, not the definition itself."

Classification rule (matches analyze_integration.py):
- skill   = directory in .claude/skills/ containing SKILL.md
- agent   = directory in .claude/agents/ containing AGENT.md
- utility = directory in either tree WITHOUT the marker file

Preservation policy (user-authored fields, kept verbatim or filtered):
- overlayCapable, discoveryCapable: kept, filtered to entries still on disk
- health, maintenanceBacklog: kept verbatim
- lastUpdated, lastAudit: rewritten to today

Usage:
    python .claude/scripts/refresh_ecosystem_state.py            # apply + summary
    python .claude/scripts/refresh_ecosystem_state.py --dry-run  # diff only
    python .claude/scripts/refresh_ecosystem_state.py --json     # JSON to stdout
    python .claude/scripts/refresh_ecosystem_state.py --quiet    # silent unless changed
"""

import argparse
import datetime
import json
import sys
from pathlib import Path


SCHEMA_VERSION = "1.0"
SKILLS_DIR = ".claude/skills"
AGENTS_DIR = ".claude/agents"
STATE_PATH = ".claude/quality/ecosystem/state.json"


def parse_frontmatter(md_path: Path) -> dict:
    """Parse YAML frontmatter from a markdown file. Minimal parser — only
    extracts top-level scalar fields (name, description, category). Returns
    empty dict if no frontmatter or unparseable."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return {}

    if not text.startswith("---"):
        return {}

    lines = text.splitlines()
    if len(lines) < 2:
        return {}

    fields = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            break
        # Match `key: value` (top-level only, no nested or list values)
        if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
            key, _, value = line.partition(":")
            value = value.strip().strip('"').strip("'")
            if value:
                fields[key.strip()] = value

    return fields


def scan_skills(repo_root: Path) -> tuple[list[str], list[str]]:
    """Return (skills, utility_skill_dirs). Skills have SKILL.md;
    utility_skill_dirs are directories without it."""
    skills_dir = repo_root / SKILLS_DIR
    skills = []
    utilities = []

    if not skills_dir.is_dir():
        return skills, utilities

    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        if (entry / "SKILL.md").is_file():
            skills.append(entry.name)
        else:
            utilities.append(entry.name)

    return skills, utilities


def scan_agents(repo_root: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Return (agents_by_category, utility_agent_dirs). Agents have AGENT.md;
    utility_agent_dirs are directories without it. Category is read from
    AGENT.md frontmatter; defaults to 'Uncategorized' if missing."""
    agents_dir = repo_root / AGENTS_DIR
    by_category: dict[str, list[str]] = {}
    utilities: list[str] = []

    if not agents_dir.is_dir():
        return by_category, utilities

    for entry in sorted(agents_dir.iterdir()):
        if not entry.is_dir():
            continue
        agent_md = entry / "AGENT.md"
        if not agent_md.is_file():
            utilities.append(entry.name)
            continue

        meta = parse_frontmatter(agent_md)
        category = meta.get("category", "").strip() or "Uncategorized"
        # Normalize first letter uppercase for consistency with existing convention
        category = category[0].upper() + category[1:] if category else "Uncategorized"

        by_category.setdefault(category, []).append(entry.name)

    # Sort agents within each category for stable output
    for cat in by_category:
        by_category[cat].sort()

    return by_category, utilities


def load_existing_state(state_path: Path) -> dict:
    """Read existing state.json. Return empty scaffold if missing or unparseable."""
    if not state_path.is_file():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def build_state(repo_root: Path, existing: dict) -> dict:
    """Produce the new state.json content from disk + preserved user state."""
    skills, utility_skills = scan_skills(repo_root)
    agents_by_cat, utility_agents = scan_agents(repo_root)

    skill_set = set(skills)

    # Preserve overlayCapable + discoveryCapable, filtered to current skills.
    existing_skills_inv = existing.get("inventory", {}).get("skills", {})
    overlay = [s for s in existing_skills_inv.get("overlayCapable", []) if s in skill_set]
    discovery = [s for s in existing_skills_inv.get("discoveryCapable", []) if s in skill_set]

    today = datetime.date.today().isoformat()
    total_agents = sum(len(v) for v in agents_by_cat.values())
    total_utilities = len(utility_skills) + len(utility_agents)

    return {
        "version": existing.get("version", SCHEMA_VERSION),
        "lastUpdated": today,
        "lastAudit": today,
        "inventory": {
            "skills": {
                "total": len(skills),
                "list": skills,
                "overlayCapable": overlay,
                "discoveryCapable": discovery,
            },
            "agents": {
                "total": total_agents,
                "byCategory": agents_by_cat,
            },
            "utilities": {
                "total": total_utilities,
                "skills": utility_skills,
                "agents": utility_agents,
            },
        },
        "health": existing.get("health", {
            "overall": "HEALTHY",
            "gaps": [],
            "conflicts": [],
            "duplications": [],
        }),
        "maintenanceBacklog": existing.get("maintenanceBacklog", []),
    }


def diff_summary(old: dict, new: dict) -> dict:
    """Compute a human-readable change summary between old and new state."""
    old_skills = set(old.get("inventory", {}).get("skills", {}).get("list", []))
    new_skills = set(new["inventory"]["skills"]["list"])
    old_agents = {
        a for cat in old.get("inventory", {}).get("agents", {}).get("byCategory", {}).values()
        for a in cat
    }
    new_agents = {
        a for cat in new["inventory"]["agents"]["byCategory"].values() for a in cat
    }
    old_util_skills = set(old.get("inventory", {}).get("utilities", {}).get("skills", []))
    new_util_skills = set(new["inventory"]["utilities"]["skills"])
    old_util_agents = set(old.get("inventory", {}).get("utilities", {}).get("agents", []))
    new_util_agents = set(new["inventory"]["utilities"]["agents"])

    return {
        "skills_added":      sorted(new_skills - old_skills),
        "skills_removed":    sorted(old_skills - new_skills),
        "agents_added":      sorted(new_agents - old_agents),
        "agents_removed":    sorted(old_agents - new_agents),
        "utilities_added":   sorted((new_util_skills | new_util_agents) - (old_util_skills | old_util_agents)),
        "utilities_removed": sorted((old_util_skills | old_util_agents) - (new_util_skills | new_util_agents)),
        "lastUpdated_changed": old.get("lastUpdated") != new["lastUpdated"],
        "lastAudit_changed":   old.get("lastAudit") != new["lastAudit"],
    }


def has_meaningful_change(old: dict, new: dict, diff: dict) -> bool:
    """True if anything beyond just lastUpdated/lastAudit changed, OR if old
    lacked those fields entirely."""
    inventory_changed = any([
        diff["skills_added"], diff["skills_removed"],
        diff["agents_added"], diff["agents_removed"],
        diff["utilities_added"], diff["utilities_removed"],
    ])
    if inventory_changed:
        return True
    # Categorical lists or schema additions
    if old.get("inventory", {}).get("skills", {}).get("overlayCapable") != \
       new["inventory"]["skills"]["overlayCapable"]:
        return True
    if old.get("inventory", {}).get("skills", {}).get("discoveryCapable") != \
       new["inventory"]["skills"]["discoveryCapable"]:
        return True
    # New utilities section appearing for the first time
    if "utilities" not in old.get("inventory", {}) and new["inventory"]["utilities"]["total"] > 0:
        return True
    return False


def format_summary(diff: dict, new: dict) -> str:
    """One-line summary suitable for digest 'notes' or stdout."""
    parts = []
    if diff["skills_added"]:
        parts.append(f"+{len(diff['skills_added'])} skill(s)")
    if diff["skills_removed"]:
        parts.append(f"-{len(diff['skills_removed'])} skill(s)")
    if diff["agents_added"]:
        parts.append(f"+{len(diff['agents_added'])} agent(s)")
    if diff["agents_removed"]:
        parts.append(f"-{len(diff['agents_removed'])} agent(s)")
    if diff["utilities_added"]:
        parts.append(f"+{len(diff['utilities_added'])} utility/utilities")
    if diff["utilities_removed"]:
        parts.append(f"-{len(diff['utilities_removed'])} utility/utilities")

    if parts:
        return (
            f"state.json refreshed: {', '.join(parts)} "
            f"(now {new['inventory']['skills']['total']} skills, "
            f"{new['inventory']['agents']['total']} agents, "
            f"{new['inventory']['utilities']['total']} utilities)"
        )
    return (
        f"state.json refreshed: no inventory change "
        f"({new['inventory']['skills']['total']} skills, "
        f"{new['inventory']['agents']['total']} agents, "
        f"{new['inventory']['utilities']['total']} utilities)"
    )


def write_state(state_path: Path, new: dict) -> None:
    """Write state.json with stable formatting (2-space indent, trailing newline)."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as f:
        json.dump(new, f, indent=2)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh .claude/quality/ecosystem/state.json from disk."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print diff, don't write")
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="Output result as JSON to stdout")
    parser.add_argument("--quiet", action="store_true",
                        help="Only print if changes were made")
    parser.add_argument("--repo-root", default=None, metavar="PATH",
                        help="Override repo root (default: script's grandparent dir)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root \
        else Path(__file__).resolve().parent.parent.parent
    state_path = repo_root / STATE_PATH

    existing = load_existing_state(state_path)
    new = build_state(repo_root, existing)
    diff = diff_summary(existing, new)
    changed = has_meaningful_change(existing, new, diff)

    if args.json_out:
        print(json.dumps({
            "changed": changed,
            "diff": diff,
            "state": new,
        }, indent=2))
        return 0

    summary = format_summary(diff, new)

    if args.dry_run:
        if changed:
            print(f"[dry-run] would update — {summary}")
        else:
            print(f"[dry-run] no changes — {summary}")
        return 0

    if changed:
        try:
            write_state(state_path, new)
        except OSError as e:
            print(f"ERROR: could not write {state_path}: {e}", file=sys.stderr)
            return 1
        if not args.quiet:
            print(summary)
        return 0

    # No meaningful change — but still rewrite if lastUpdated/lastAudit need bumping.
    if diff["lastUpdated_changed"] or diff["lastAudit_changed"]:
        try:
            write_state(state_path, new)
        except OSError as e:
            print(f"ERROR: could not write {state_path}: {e}", file=sys.stderr)
            return 1

    if not args.quiet:
        print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())

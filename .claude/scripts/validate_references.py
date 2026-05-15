#!/usr/bin/env python3
"""
CI check: validate all file path references resolve to actual files.

Checks:
  1. Every path in reference-index.json exists on disk
  2. Skill count in state.json matches actual skill directories
  3. Every skill in state.json has a SKILL.md file

Exit 0 = all pass, Exit 1 = failures found.
"""

import glob
import json
import os
import sys


def check_reference_index():
    """Validate all paths in reference-index.json exist."""
    path = ".claude/registries/reference-index.json"
    if not os.path.exists(path):
        print(f"SKIP: {path} (not found)")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = 0
    refs = data.get("references", {})

    for section, entries in refs.items():
        if not isinstance(entries, dict):
            continue
        for key, filepath in entries.items():
            if not isinstance(filepath, str):
                continue
            if os.path.exists(filepath):
                print(f"OK:   [{section}] {key} -> {filepath}")
            else:
                print(f"FAIL: [{section}] {key} -> {filepath} (NOT FOUND)")
                errors += 1

    return errors


def check_state_json():
    """Validate state.json skill count matches reality."""
    path = ".claude/quality/ecosystem/state.json"
    if not os.path.exists(path):
        print(f"SKIP: {path} (not found)")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = 0

    # Navigate the actual schema: inventory.skills.list / inventory.skills.total
    inventory = data.get("inventory", {})
    skills_section = inventory.get("skills", {})
    declared_skills = skills_section.get("list", [])
    declared_count = skills_section.get("total", len(declared_skills))

    # Find actual skill directories on disk
    skill_dirs = [os.path.basename(os.path.dirname(d)) for d in glob.glob(".claude/skills/*/SKILL.md")]
    # DEV_ONLY skills don't ship publicly — see DEV_ONLY_SKILLS below + publish.sh DEV_ONLY_PATHS.
    # Exclude them from the count comparison so the pre-flight reflects the *public* surface.
    _DEV_ONLY = {"ecosystem-planner"}
    shippable_dirs = [n for n in skill_dirs if n not in _DEV_ONLY and n != "skill-discovery"]
    actual_count = len(shippable_dirs)

    if declared_count != actual_count:
        print(f"FAIL: state.json says {declared_count} skills, but {actual_count} shippable SKILL.md files found")
        errors += 1
    else:
        print(f"OK:   state.json skill count ({declared_count}) matches shippable disk count")

    # Check each declared skill exists
    for skill_name in declared_skills:
        skill_path = f".claude/skills/{skill_name}/SKILL.md"
        if os.path.exists(skill_path):
            print(f"OK:   skill '{skill_name}' exists")
        else:
            print(f"FAIL: skill '{skill_name}' declared in state.json but {skill_path} not found")
            errors += 1

    # Check for undeclared skills
    # DEV_ONLY skills live in the dev clone but are stripped at publish time via
    # publish.sh's DEV_ONLY_PATHS — they must NOT be declared in state.json
    # (state.json ships to the public install) AND must NOT block the pre-flight.
    DEV_ONLY_SKILLS = {"ecosystem-planner"}
    for name in skill_dirs:
        if name == "skill-discovery":
            continue  # utility, not a skill
        if name in DEV_ONLY_SKILLS:
            continue  # stripped at publish via publish.sh DEV_ONLY_PATHS
        if name not in declared_skills:
            print(f"FAIL: skill '{name}' exists on disk but not declared in state.json")
            errors += 1

    return errors


def main():
    total_errors = 0

    print("--- Reference Index ---")
    total_errors += check_reference_index()

    print("\n--- Ecosystem State ---")
    total_errors += check_state_json()

    print(f"\n{total_errors} error(s) found")
    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()

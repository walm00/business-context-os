#!/usr/bin/env bash
# Discovers all skills in the CLEAR Context OS ecosystem
# Usage: bash .claude/skills/skill-discovery/find_skills.sh

SKILLS_DIR=".claude/skills"
count=0

for dir in "$SKILLS_DIR"/*/; do
  if [ -f "${dir}SKILL.md" ]; then
    skill_name=$(basename "$dir")
    echo "$skill_name"
    count=$((count + 1))
  fi
done

echo "---"
echo "Total skills: $count"

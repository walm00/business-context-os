#!/usr/bin/env bash
# Discovers all agents in the CLEAR Context OS ecosystem
# Usage: bash .claude/agents/agent-discovery/find_agents.sh

AGENTS_DIR=".claude/agents"
count=0

for dir in "$AGENTS_DIR"/*/; do
  if [ -f "${dir}AGENT.md" ]; then
    agent_name=$(basename "$dir")
    echo "$agent_name"
    count=$((count + 1))
  fi
done

echo "---"
echo "Total agents: $count"

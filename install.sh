#!/usr/bin/env bash
#
# CLEAR Context OS - Installer
#
# Installs BCOS into an existing project by copying the framework files
# into the current directory. Does NOT overwrite existing files.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/walm00/business-context-os/main/install.sh | bash
#
#   Or clone the repo and run:
#   bash /path/to/business-context-os/install.sh
#

set -euo pipefail

# Colors (if terminal supports them)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Where the BCOS source lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$(pwd)"

echo ""
echo -e "${BLUE}CLEAR Context OS - Installer${NC}"
echo "================================"
echo ""
echo "Target: $TARGET_DIR"
echo ""

# ─── Pre-flight checks ──────────────────────────────────────────────

# Check we're not installing into the BCOS repo itself
if [ -f "$TARGET_DIR/install.sh" ] && grep -q "CLEAR Context OS" "$TARGET_DIR/install.sh" 2>/dev/null; then
    echo -e "${RED}Error: You're inside the BCOS repo itself.${NC}"
    echo "Run this from your project directory instead:"
    echo "  cd /path/to/your/project"
    echo "  bash /path/to/business-context-os/install.sh"
    exit 1
fi

# Check source exists
if [ ! -f "$SCRIPT_DIR/CLAUDE.md" ] || [ ! -d "$SCRIPT_DIR/.claude" ]; then
    echo -e "${RED}Error: Can't find BCOS source files.${NC}"
    echo "Make sure you're running this from the business-context-os directory"
    echo "or pass the correct path."
    exit 1
fi

# ─── Track what we do ───────────────────────────────────────────────

COPIED=0
SKIPPED=0
CREATED_DIRS=0

copy_if_missing() {
    local src="$1"
    local dest="$2"

    # Create parent directory if needed
    local dir=$(dirname "$dest")
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        CREATED_DIRS=$((CREATED_DIRS + 1))
    fi

    if [ -f "$dest" ]; then
        echo -e "  ${YELLOW}SKIP${NC}  $dest (already exists)"
        SKIPPED=$((SKIPPED + 1))
    else
        cp "$src" "$dest"
        echo -e "  ${GREEN}COPY${NC}  $dest"
        COPIED=$((COPIED + 1))
    fi
}

# ─── Install .claude/ framework ─────────────────────────────────────

echo -e "${BLUE}Installing .claude/ framework...${NC}"
echo ""

# Skills
for skill_dir in "$SCRIPT_DIR"/.claude/skills/*/; do
    skill_name=$(basename "$skill_dir")
    # Copy SKILL.md
    if [ -f "$skill_dir/SKILL.md" ]; then
        copy_if_missing "$skill_dir/SKILL.md" ".claude/skills/$skill_name/SKILL.md"
    fi
    # Copy find_skills.sh (utility)
    if [ -f "$skill_dir/find_skills.sh" ]; then
        copy_if_missing "$skill_dir/find_skills.sh" ".claude/skills/$skill_name/find_skills.sh"
    fi
    # Copy references
    if [ -d "$skill_dir/references" ]; then
        for ref in "$skill_dir"/references/*; do
            if [ -f "$ref" ]; then
                copy_if_missing "$ref" ".claude/skills/$skill_name/references/$(basename "$ref")"
            fi
        done
    fi
done

# Agents
for agent_dir in "$SCRIPT_DIR"/.claude/agents/*/; do
    agent_name=$(basename "$agent_dir")
    if [ -f "$agent_dir/AGENT.md" ]; then
        copy_if_missing "$agent_dir/AGENT.md" ".claude/agents/$agent_name/AGENT.md"
    fi
    if [ -f "$agent_dir/find_agents.sh" ]; then
        copy_if_missing "$agent_dir/find_agents.sh" ".claude/agents/$agent_name/find_agents.sh"
    fi
done

# Quality infrastructure
copy_if_missing "$SCRIPT_DIR/.claude/quality/ecosystem/config.json" ".claude/quality/ecosystem/config.json"
copy_if_missing "$SCRIPT_DIR/.claude/quality/ecosystem/state.json" ".claude/quality/ecosystem/state.json"
copy_if_missing "$SCRIPT_DIR/.claude/quality/ecosystem/lessons.json" ".claude/quality/ecosystem/lessons.json"
copy_if_missing "$SCRIPT_DIR/.claude/quality/ecosystem/lessons-schema.md" ".claude/quality/ecosystem/lessons-schema.md"
mkdir -p .claude/quality/sessions

# Scripts
copy_if_missing "$SCRIPT_DIR/.claude/scripts/build_document_index.py" ".claude/scripts/build_document_index.py"
copy_if_missing "$SCRIPT_DIR/.claude/scripts/find_lessons.py" ".claude/scripts/find_lessons.py"
copy_if_missing "$SCRIPT_DIR/.claude/scripts/consolidate_lessons.py" ".claude/scripts/consolidate_lessons.py"

# Registries
copy_if_missing "$SCRIPT_DIR/.claude/registries/reference-index.json" ".claude/registries/reference-index.json"

# Ecosystem map
copy_if_missing "$SCRIPT_DIR/.claude/ECOSYSTEM-MAP.md" ".claude/ECOSYSTEM-MAP.md"

# Settings (hooks config — shared, not local)
copy_if_missing "$SCRIPT_DIR/.claude/settings.json" ".claude/settings.json"

echo ""

# ─── Install docs/ ──────────────────────────────────────────────────

echo -e "${BLUE}Installing docs/...${NC}"
echo ""

# Document folder zones (active / inbox / planned / archive)
mkdir -p docs/_inbox docs/_planned docs/_archive
echo -e "  ${GREEN}CREATE${NC}  docs/_inbox/ (raw material landing zone)"
echo -e "  ${GREEN}CREATE${NC}  docs/_planned/ (polished ideas, not yet active)"
echo -e "  ${GREEN}CREATE${NC}  docs/_archive/ (superseded documents)"
echo ""

# Onboarding checklist (self-removes when complete)
copy_if_missing "$SCRIPT_DIR/docs/.onboarding-checklist.md" "docs/.onboarding-checklist.md"

# Methodology
for f in "$SCRIPT_DIR"/docs/methodology/*.md; do
    copy_if_missing "$f" "docs/methodology/$(basename "$f")"
done

# Guides
for f in "$SCRIPT_DIR"/docs/guides/*.md; do
    copy_if_missing "$f" "docs/guides/$(basename "$f")"
done

# Templates
for f in "$SCRIPT_DIR"/docs/templates/*.md; do
    copy_if_missing "$f" "docs/templates/$(basename "$f")"
done

echo ""

# ─── Install examples/ (optional) ───────────────────────────────────

echo -e "${BLUE}Installing examples/...${NC}"
echo ""

# Brand strategy example
for f in "$SCRIPT_DIR"/examples/brand-strategy/*.md; do
    copy_if_missing "$f" "examples/brand-strategy/$(basename "$f")"
done
for f in "$SCRIPT_DIR"/examples/brand-strategy/data-points/*.md; do
    copy_if_missing "$f" "examples/brand-strategy/data-points/$(basename "$f")"
done

echo ""

# ─── CLAUDE.md handling ─────────────────────────────────────────────

echo -e "${BLUE}CLAUDE.md...${NC}"
echo ""

if [ -f "$TARGET_DIR/CLAUDE.md" ]; then
    echo -e "  ${YELLOW}SKIP${NC}  CLAUDE.md (already exists)"
    echo ""
    echo -e "  ${YELLOW}NOTE:${NC} You already have a CLAUDE.md. To add BCOS instructions,"
    echo "        see the BCOS CLAUDE.md for sections to merge into yours:"
    echo "        $SCRIPT_DIR/CLAUDE.md"
    echo ""
    # Copy as reference for manual merge
    copy_if_missing "$SCRIPT_DIR/CLAUDE.md" ".claude/bcos-claude-reference.md"
    SKIPPED=$((SKIPPED + 1))
else
    copy_if_missing "$SCRIPT_DIR/CLAUDE.md" "CLAUDE.md"
fi

# ─── Make scripts executable ────────────────────────────────────────

chmod +x .claude/agents/agent-discovery/find_agents.sh 2>/dev/null || true
chmod +x .claude/skills/skill-discovery/find_skills.sh 2>/dev/null || true

# ─── Summary ────────────────────────────────────────────────────────

echo ""
echo "================================"
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "  Files copied:  $COPIED"
echo "  Files skipped: $SKIPPED (already existed)"
echo "  Dirs created:  $CREATED_DIRS"
echo ""
echo -e "${BLUE}Next step:${NC}"
echo ""
echo "  Open Claude Code and say: \"Help me get started with my business context.\""
echo "  Claude will figure out the rest."
echo ""
if [ "$SKIPPED" -gt 0 ]; then
echo -e "  ${YELLOW}NOTE:${NC} Some files were skipped (already existed)."
echo "  If you have an existing CLAUDE.md, merge the BCOS sections from:"
echo "  .claude/bcos-claude-reference.md"
echo ""
fi

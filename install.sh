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

# Where the BCOS source lives. Tolerate cd failure (e.g. exotic /dev/fd setups
# under `bash <(curl …)`) — the bootstrap block below will recover.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || SCRIPT_DIR=""
TARGET_DIR="$(pwd)"

echo ""
echo -e "${BLUE}CLEAR Context OS - Installer${NC}"
echo "================================"
echo ""
echo "Target: $TARGET_DIR"
echo ""

# ─── Self-bootstrap (curl-pipe path) ────────────────────────────────
# When run via `bash <(curl …)` or `curl … | bash`, SCRIPT_DIR points at a
# process-substitution FD or /tmp with no source tree. Detect that, download a
# tarball of the repo, and re-exec from the extracted copy. Keeps the advertised
# one-liner honest without forcing users to clone first.

# If a previous run already bootstrapped, clean up its temp dir when we exit.
if [ -n "${BCOS_CLEANUP_DIR:-}" ]; then
    trap 'rm -rf "$BCOS_CLEANUP_DIR"' EXIT
fi

if [ -z "${BCOS_BOOTSTRAPPED:-}" ] && { [ ! -f "$SCRIPT_DIR/CLAUDE.md" ] || [ ! -d "$SCRIPT_DIR/.claude" ]; }; then
    for tool in curl tar; do
        if ! command -v "$tool" > /dev/null 2>&1; then
            echo -e "${RED}Error: '$tool' is required for remote install but not found on PATH.${NC}"
            echo "Install it and re-run, or clone the repo and run install.sh locally."
            exit 1
        fi
    done

    echo -e "${BLUE}Downloading CLEAR Context OS…${NC}"

    BOOTSTRAP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t bcos)"
    TARBALL_URL="https://github.com/walm00/business-context-os/archive/refs/heads/main.tar.gz"
    TARBALL="$BOOTSTRAP_DIR/bcos.tar.gz"
    CURL_ERR="$BOOTSTRAP_DIR/curl.err"

    # First attempt — normal TLS. On Windows Schannel, revocation lookups fail
    # on many corporate/VPN networks even for valid certs; detect that specific
    # error and retry with --ssl-no-revoke. Any other failure is a real error.
    if ! curl -fsSL "$TARBALL_URL" -o "$TARBALL" 2>"$CURL_ERR"; then
        if grep -qiE "revocation|CRYPT_E_NO_REVOCATION|CERT_TRUST_REVOCATION" "$CURL_ERR"; then
            echo -e "  ${YELLOW}Windows SSL revocation check failed — retrying with --ssl-no-revoke${NC}"
            if ! curl -fsSL --ssl-no-revoke "$TARBALL_URL" -o "$TARBALL" 2>"$CURL_ERR"; then
                echo -e "${RED}Error: Failed to download BCOS tarball.${NC}"
                cat "$CURL_ERR" >&2
                rm -rf "$BOOTSTRAP_DIR"
                exit 1
            fi
        else
            echo -e "${RED}Error: Failed to download BCOS tarball.${NC}"
            cat "$CURL_ERR" >&2
            rm -rf "$BOOTSTRAP_DIR"
            exit 1
        fi
    fi

    if ! tar -xzf "$TARBALL" -C "$BOOTSTRAP_DIR"; then
        echo -e "${RED}Error: Failed to extract BCOS tarball.${NC}"
        rm -rf "$BOOTSTRAP_DIR"
        exit 1
    fi

    EXTRACTED_DIR="$(find "$BOOTSTRAP_DIR" -maxdepth 1 -type d -name 'business-context-os-*' | head -n1)"
    if [ -z "$EXTRACTED_DIR" ] || [ ! -f "$EXTRACTED_DIR/install.sh" ]; then
        echo -e "${RED}Error: Downloaded archive has unexpected structure.${NC}"
        rm -rf "$BOOTSTRAP_DIR"
        exit 1
    fi

    echo ""
    # Re-exec from the extracted source. cwd is still the user's project dir,
    # so TARGET_DIR will resolve correctly in the new process.
    export BCOS_BOOTSTRAPPED=1
    export BCOS_CLEANUP_DIR="$BOOTSTRAP_DIR"
    exec bash "$EXTRACTED_DIR/install.sh"
fi

# ─── Pre-flight checks ──────────────────────────────────────────────

# Check we're not installing into the BCOS repo itself
if [ -f "$TARGET_DIR/install.sh" ] && grep -q "CLEAR Context OS" "$TARGET_DIR/install.sh" 2>/dev/null; then
    echo -e "${RED}Error: You're inside the BCOS repo itself.${NC}"
    echo "Run this from your project directory instead:"
    echo "  cd /path/to/your/project"
    echo "  bash /path/to/business-context-os/install.sh"
    exit 1
fi

# Check source exists (shouldn't trip after bootstrap, but belt-and-braces)
if [ ! -f "$SCRIPT_DIR/CLAUDE.md" ] || [ ! -d "$SCRIPT_DIR/.claude" ]; then
    echo -e "${RED}Error: Can't find BCOS source files.${NC}"
    echo "Make sure you're running this from the business-context-os directory"
    echo "or pass the correct path."
    exit 1
fi

# Python 3 is required — hooks, validators, and update.py all run on it.
# Fresh macOS installs don't ship python3 until Xcode Command Line Tools are
# installed, so catch the missing interpreter here with a useful hint.
if ! command -v python3 > /dev/null 2>&1; then
    echo -e "${RED}Error: python3 is required but not found on PATH.${NC}"
    echo ""
    echo "BCOS uses Python 3 for hooks, validators, and the update script."
    echo ""
    echo "Install it with one of:"
    echo "  macOS:    xcode-select --install    (Xcode Command Line Tools)"
    echo "            brew install python       (Homebrew)"
    echo "  Linux:    sudo apt install python3  (or your distro's equivalent)"
    echo "  Windows:  https://www.python.org/downloads/"
    echo ""
    echo "Then re-run this installer."
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
copy_if_missing "$SCRIPT_DIR/.claude/quality/ecosystem/lessons-starter.json" ".claude/quality/ecosystem/lessons.json"
copy_if_missing "$SCRIPT_DIR/.claude/quality/ecosystem/lessons-schema.md" ".claude/quality/ecosystem/lessons-schema.md"
mkdir -p .claude/quality/sessions

# Schedule dispatcher template — onboarding uses this as the source for the live
# schedule-config.json. update.py keeps this template in sync across releases.
copy_if_missing "$SCRIPT_DIR/.claude/quality/schedule-config.template.json" ".claude/quality/schedule-config.template.json"

# Hooks
for f in "$SCRIPT_DIR"/.claude/hooks/*; do
    if [ -f "$f" ]; then
        copy_if_missing "$f" ".claude/hooks/$(basename "$f")"
    fi
done

# Scripts
for f in "$SCRIPT_DIR"/.claude/scripts/*.py; do
    if [ -f "$f" ]; then
        copy_if_missing "$f" ".claude/scripts/$(basename "$f")"
    fi
done

# Hook state directory (gitignored, machine-local)
mkdir -p .claude/hook_state
touch .claude/hook_state/.gitkeep

# Registries
copy_if_missing "$SCRIPT_DIR/.claude/registries/reference-index.json" ".claude/registries/reference-index.json"
copy_if_missing "$SCRIPT_DIR/.claude/registries/entities.json" ".claude/registries/entities.json"

# Ecosystem map
copy_if_missing "$SCRIPT_DIR/.claude/ECOSYSTEM-MAP.md" ".claude/ECOSYSTEM-MAP.md"

# Settings (hooks config — shared, not local)
copy_if_missing "$SCRIPT_DIR/.claude/settings.json" ".claude/settings.json"

echo ""

# ─── Install docs/ ──────────────────────────────────────────────────

echo -e "${BLUE}Installing docs/...${NC}"
echo ""

# Document folder zones (active / inbox / planned / archive)
mkdir -p docs/_inbox docs/_inbox/sessions docs/_planned docs/_archive docs/_collections
echo -e "  ${GREEN}CREATE${NC}  docs/_inbox/ (raw material landing zone)"
echo -e "  ${GREEN}CREATE${NC}  docs/_inbox/sessions/ (auto-captured session context)"
echo -e "  ${GREEN}CREATE${NC}  docs/_planned/ (polished ideas, not yet active)"
echo -e "  ${GREEN}CREATE${NC}  docs/_archive/ (superseded documents)"
echo -e "  ${GREEN}CREATE${NC}  docs/_collections/ (high-volume files — transcripts, reports)"
echo ""

# Private folder (gitignored — local-only context)
mkdir -p .private
for f in "$SCRIPT_DIR"/docs/_bcos-framework/templates/private-starter/*.md; do
    copy_if_missing "$f" ".private/$(basename "$f")"
done
echo -e "  ${GREEN}CREATE${NC}  .private/ (local-only context — gitignored, never shared)"
echo ""

# Onboarding checklist (self-removes when complete)
copy_if_missing "$SCRIPT_DIR/docs/.onboarding-checklist.md" "docs/.onboarding-checklist.md"

# Session diary (append-only, auto-pruned after 30 days)
copy_if_missing "$SCRIPT_DIR/docs/.session-diary.md" "docs/.session-diary.md"

# Architecture
for f in "$SCRIPT_DIR"/docs/_bcos-framework/architecture/*.md; do
    copy_if_missing "$f" "docs/_bcos-framework/architecture/$(basename "$f")"
done

# Methodology
for f in "$SCRIPT_DIR"/docs/_bcos-framework/methodology/*.md; do
    copy_if_missing "$f" "docs/_bcos-framework/methodology/$(basename "$f")"
done

# Guides
for f in "$SCRIPT_DIR"/docs/_bcos-framework/guides/*.md; do
    copy_if_missing "$f" "docs/_bcos-framework/guides/$(basename "$f")"
done

# Templates
for f in "$SCRIPT_DIR"/docs/_bcos-framework/templates/*.md; do
    copy_if_missing "$f" "docs/_bcos-framework/templates/$(basename "$f")"
done

# Patterns (project-type Data Point Maps — client project, internal tool, GTM, etc.)
for f in "$SCRIPT_DIR"/docs/_bcos-framework/patterns/*.md; do
    copy_if_missing "$f" "docs/_bcos-framework/patterns/$(basename "$f")"
done

echo ""

# ─── Install examples/ (optional) ───────────────────────────────────
# examples/ was removed in v1.3 — superseded by the Data Point Maps pattern.
# Loop is kept (guarded) so re-adding examples in future releases just works.

if [ -d "$SCRIPT_DIR/examples/brand-strategy" ]; then
    echo -e "${BLUE}Installing examples/...${NC}"
    echo ""
    shopt -s nullglob
    for f in "$SCRIPT_DIR"/examples/brand-strategy/*.md; do
        copy_if_missing "$f" "examples/brand-strategy/$(basename "$f")"
    done
    for f in "$SCRIPT_DIR"/examples/brand-strategy/data-points/*.md; do
        copy_if_missing "$f" "examples/brand-strategy/data-points/$(basename "$f")"
    done
    shopt -u nullglob
    echo ""
fi

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

# ─── README.md handling ─────────────────────────────────────────────

echo -e "${BLUE}README.md...${NC}"
echo ""

if [ -f "$TARGET_DIR/README.md" ]; then
    echo -e "  ${YELLOW}SKIP${NC}  README.md (existing repo — not touched)"
    echo ""
else
    echo -e "  ${YELLOW}NOTE${NC}  No README.md found."
    echo "        Once your context is established, ask Claude to generate one:"
    echo "        \"Create a README for this repository based on my context.\""
    echo ""
fi

# ─── Make scripts executable ────────────────────────────────────────

chmod +x .claude/agents/agent-discovery/find_agents.sh 2>/dev/null || true
chmod +x .claude/skills/skill-discovery/find_skills.sh 2>/dev/null || true
chmod +x .claude/hooks/auto_save_session.sh 2>/dev/null || true
chmod +x .claude/hooks/precompact_save.sh 2>/dev/null || true

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

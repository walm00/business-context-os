#!/usr/bin/env bash
#
# CLEAR Context OS - Installer
#
# Installs BCOS into an existing project by copying the framework files
# into the current directory. Does NOT overwrite existing files.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/walm00/business-context-os/main/install.sh -o /tmp/bcos-install.sh
#   bash /tmp/bcos-install.sh
#
#   (Two steps instead of `curl … | bash` so Claude Code's permission gate
#    auto-approves both commands without dropping out to a terminal.)
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
# `command -v python3` is INSUFFICIENT on Windows: the Microsoft Store stub
# satisfies the check but exits 49 without running anything. We must actually
# execute Python and confirm it produces a version. Fresh macOS installs that
# lack Xcode Command Line Tools also miss `python3` entirely.
#
# Resolution order:
#   1. python3 (POSIX standard; works on macOS/Linux with real Python installed)
#   2. py -3   (Windows Python Launcher — bypasses the MS Store stub)
#   3. python  (fallback when only `python` is on PATH)
PY_CMD=""
PY_ARGS=""
for candidate in "python3" "py" "python"; do
    if command -v "$candidate" > /dev/null 2>&1; then
        if [ "$candidate" = "py" ]; then
            # py -3 (Windows Python Launcher selecting Python 3)
            if py -3 -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" > /dev/null 2>&1; then
                PY_CMD="py"
                PY_ARGS="-3"
                break
            fi
        else
            if "$candidate" -c "import sys; sys.exit(0 if sys.version_info[0]==3 else 1)" > /dev/null 2>&1; then
                PY_CMD="$candidate"
                PY_ARGS=""
                break
            fi
        fi
    fi
done

if [ -z "$PY_CMD" ]; then
    echo -e "${RED}Error: no working Python 3 interpreter found.${NC}"
    echo ""
    echo "BCOS uses Python 3 for hooks, validators, and the update script."
    echo "Tried: python3, py -3, python — none returned a Python 3 version."
    echo ""
    echo "Install it with one of:"
    echo "  macOS:    xcode-select --install    (Xcode Command Line Tools)"
    echo "            brew install python       (Homebrew)"
    echo "  Linux:    sudo apt install python3  (or your distro's equivalent)"
    echo "  Windows:  https://www.python.org/downloads/"
    echo ""
    echo "Windows note: the Microsoft Store 'python3' shortcut does NOT count —"
    echo "it's a launcher stub that exits without running. Disable App Execution"
    echo "Aliases for python.exe/python3.exe in Windows Settings, or install"
    echo "Python from python.org which provides the 'py' launcher."
    echo ""
    echo "Then re-run this installer."
    exit 1
fi

echo "  Python detected: $PY_CMD $PY_ARGS"

# ─── Shim setup ─────────────────────────────────────────────────────
# Create .claude/bin/python3 (POSIX) and .claude/bin/python3.cmd (Windows)
# shims that BCOS callers (hooks, scripts, settings.json hook commands)
# reference via $CLAUDE_PROJECT_DIR/.claude/bin/python3. The shims bypass the
# Windows MS Store stub by using `py -3` directly. POSIX shim is a passthrough
# so callers never branch on OS.
#
# Why a repo-local shim and not a user-global PATH change?
#   - Daily ops simplicity (no shell reload, no env mutation outside the repo)
#   - Each BCOS-installed repo is self-contained
#   - Reversible: deleting .claude/bin/ undoes the change
mkdir -p "$TARGET_DIR/.claude/bin"

# Windows shim — uses Python Launcher which never aliases to the Store stub
cat > "$TARGET_DIR/.claude/bin/python3.cmd" <<'EOF'
@echo off
py -3 %*
exit /b %ERRORLEVEL%
EOF

# POSIX shim — works on macOS, Linux, AND Windows Git Bash / WSL.
# On Git Bash for Windows, `/usr/bin/env python3` inherits Windows PATH and
# hits the MS Store stub same as cmd.exe. So we try the Python Launcher
# (`py -3`) first — it's installed by python.org on Windows and is never
# aliased to the Store stub. On macOS/Linux `py` isn't present, so we fall
# straight through to /usr/bin/env python3.
cat > "$TARGET_DIR/.claude/bin/python3" <<'EOF'
#!/usr/bin/env bash
# BCOS Python shim — passthrough. Generated by install.sh / update.py.
# Do not edit; regenerate via `bash install.sh` or `.claude/bin/python3 .claude/scripts/update.py`.
if command -v py > /dev/null 2>&1; then
    exec py -3 "$@"
fi
exec /usr/bin/env python3 "$@"
EOF
chmod 755 "$TARGET_DIR/.claude/bin/python3"

# From here on in this script, use the SHIM path for any Python invocation
# so the rest of install.sh exercises the same path BCOS will use at runtime.
# Note: $PY is the local-source shim (under SCRIPT_DIR) until TARGET shim is
# available, then we switch. For self-install where SCRIPT_DIR == TARGET_DIR,
# this is the same path.
PY="$TARGET_DIR/.claude/bin/python3"
echo "  Shim installed at $PY"

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

copy_template_if_missing() {
    local src="$1"
    local dest="$2"
    local domain="${3:-Project Wiki}"
    local today
    today="$(date +%F)"

    local dir=$(dirname "$dest")
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        CREATED_DIRS=$((CREATED_DIRS + 1))
    fi

    if [ -f "$dest" ]; then
        echo -e "  ${YELLOW}SKIP${NC}  $dest (already exists)"
        SKIPPED=$((SKIPPED + 1))
    else
        sed -e "s/{{TODAY}}/$today/g" -e "s/TODAY/$today/g" -e "s/{{DOMAIN}}/$domain/g" "$src" > "$dest"
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
    # Copy remaining skill-owned files: references, command siblings, templates,
    # and other support files. This is required for multi-file skills such as
    # bcos-wiki where SKILL.md dispatches to sibling command docs.
    while IFS= read -r f; do
        rel="${f#$skill_dir}"
        case "$rel" in
            SKILL.md|find_skills.sh) continue ;;
        esac
        copy_if_missing "$f" ".claude/skills/$skill_name/$rel"
    done < <(find "$skill_dir" -type f ! -name "*.pyc" ! -path "*/__pycache__/*" 2>/dev/null)
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
copy_if_missing "$SCRIPT_DIR/.claude/quality/ecosystem/lessons-starter.json" ".claude/quality/ecosystem/lessons.json"
copy_if_missing "$SCRIPT_DIR/.claude/quality/ecosystem/lessons-schema.md" ".claude/quality/ecosystem/lessons-schema.md"
mkdir -p .claude/quality/sessions

# Self-learning event log + derived state. These files are gitignored
# (event logs, conflict-prone) and seeded inline as empty defaults on
# first install. The dispatcher / record_resolution.py / promote_resolutions.py
# populate them at runtime.
seed_if_missing() {
    local dest="$1"
    local content="$2"
    local dir
    dir=$(dirname "$dest")
    [ -d "$dir" ] || { mkdir -p "$dir"; CREATED_DIRS=$((CREATED_DIRS + 1)); }
    if [ -f "$dest" ]; then
        echo -e "  ${YELLOW}SKIP${NC}  $dest (already exists)"
        SKIPPED=$((SKIPPED + 1))
    else
        printf '%s' "$content" > "$dest"
        echo -e "  ${GREEN}SEED${NC}  $dest"
        COPIED=$((COPIED + 1))
    fi
}
seed_if_missing ".claude/quality/ecosystem/resolutions.jsonl" ""
seed_if_missing ".claude/quality/ecosystem/learned-rules.json" '{"$schema":"https://json-schema.org/draft/2020-12/schema","schema_version":"1.0.0","rule_count":0,"rules":[]}'
seed_if_missing ".claude/quality/ecosystem/learning-blocklist.json" '{"$schema":"https://json-schema.org/draft/2020-12/schema","schema_version":"1.0.0","blocked":[]}'
seed_if_missing ".claude/quality/ecosystem/state.json" '{"version":"1.0","lastUpdated":"","lastAudit":"","inventory":{}}'

# Schedule dispatcher template — onboarding uses this as the source for the live
# schedule-config.json. update.py keeps this template in sync across releases.
copy_if_missing "$SCRIPT_DIR/.claude/quality/schedule-config.template.json" ".claude/quality/schedule-config.template.json"

# Hooks
for f in "$SCRIPT_DIR"/.claude/hooks/*; do
    if [ -f "$f" ]; then
        copy_if_missing "$f" ".claude/hooks/$(basename "$f")"
    fi
done

# Scripts (recursive — top-level *.py plus subdirs like bcos-dashboard/)
# Skip Python bytecode caches: machine-local artifacts that should never sync.
while IFS= read -r f; do
    rel="${f#$SCRIPT_DIR/.claude/scripts/}"
    copy_if_missing "$f" ".claude/scripts/$rel"
done < <(find "$SCRIPT_DIR/.claude/scripts" -type f ! -name "*.pyc" ! -path "*/__pycache__/*" 2>/dev/null)

# Templates (gitignore profile template, etc.)
if [ -d "$SCRIPT_DIR/.claude/templates" ]; then
    for f in "$SCRIPT_DIR"/.claude/templates/*; do
        if [ -f "$f" ]; then
            copy_if_missing "$f" ".claude/templates/$(basename "$f")"
        fi
    done
fi

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

# Wiki zone scaffold — MANDATORY per plugin-storage-contract.md Rule 2.
# The wiki is BCOS's universal long-form / cross-cutting content destination.
# Active authored pages live under pages/ and source-summary/; raw/ remains
# framework-managed storage for bcos-wiki Path B material. All wiki schedules
# (wiki-stale-propagation, wiki-source-refresh, wiki-graveyard, wiki-coverage-audit,
# wiki-canonical-drift, wiki-failed-ingest) assume this substrate exists.
mkdir -p docs/_wiki/pages docs/_wiki/source-summary docs/_wiki/raw/web docs/_wiki/raw/github docs/_wiki/raw/youtube docs/_wiki/raw/local docs/_wiki/.archive docs/_wiki/.schema.d
echo -e "  ${GREEN}CREATE${NC}  docs/_wiki/ (wiki zone — universal long-form destination)"
copy_template_if_missing "$SCRIPT_DIR/docs/_bcos-framework/templates/_wiki.schema.yml.tmpl" "docs/_wiki/.schema.yml" "Project Wiki"
copy_template_if_missing "$SCRIPT_DIR/docs/_bcos-framework/templates/_wiki.config.yml.tmpl" "docs/_wiki/.config.yml" "Project Wiki"
copy_template_if_missing "$SCRIPT_DIR/.claude/skills/bcos-wiki/templates/README.md.tmpl" "docs/_wiki/README.md" "Project Wiki"
copy_template_if_missing "$SCRIPT_DIR/.claude/skills/bcos-wiki/templates/queue.md.tmpl" "docs/_wiki/queue.md" "Project Wiki"
copy_template_if_missing "$SCRIPT_DIR/.claude/skills/bcos-wiki/templates/overview.md.tmpl" "docs/_wiki/overview.md" "Project Wiki"
copy_template_if_missing "$SCRIPT_DIR/.claude/skills/bcos-wiki/templates/log.md.tmpl" "docs/_wiki/log.md" "Project Wiki"
copy_if_missing "$SCRIPT_DIR/.claude/skills/bcos-wiki/templates/raw/web-README.md.tmpl" "docs/_wiki/raw/web/README.md"
copy_if_missing "$SCRIPT_DIR/.claude/skills/bcos-wiki/templates/raw/github-README.md.tmpl" "docs/_wiki/raw/github/README.md"
copy_if_missing "$SCRIPT_DIR/.claude/skills/bcos-wiki/templates/raw/youtube-README.md.tmpl" "docs/_wiki/raw/youtube/README.md"
copy_if_missing "$SCRIPT_DIR/.claude/skills/bcos-wiki/templates/raw/local-README.md.tmpl" "docs/_wiki/raw/local/README.md"
# .gitkeep on empty wiki subdirs so the structure is preserved across git clone
# even when no pages/captures exist yet.
for wd in "docs/_wiki/pages" "docs/_wiki/source-summary" "docs/_wiki/.archive" "docs/_wiki/.schema.d"; do
    [ ! -f "$wd/.gitkeep" ] && touch "$wd/.gitkeep"
done
if [ ! -f "docs/_wiki/index.md" ]; then
    cat > "docs/_wiki/index.md" <<'EOF'
# Wiki Index

→ [[overview]] | [[log]]

No wiki pages yet. This file is regenerated by `python .claude/scripts/refresh_wiki_index.py`.
EOF
    echo -e "  ${GREEN}CREATE${NC}  docs/_wiki/index.md"
fi
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
copy_if_missing "$SCRIPT_DIR/docs/_bcos-framework/templates/session-diary-starter.md" "docs/.session-diary.md"

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
for f in "$SCRIPT_DIR"/docs/_bcos-framework/templates/*; do
    if [ -f "$f" ]; then
        copy_if_missing "$f" "docs/_bcos-framework/templates/$(basename "$f")"
    fi
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

# Boundary-aware: ensure the BCOS:CORE block is present and current.
# Same logic used by update.py and the context-onboarding self-heal step.
#   missing file       → write shipped template
#   has CORE markers   → replace block contents (saves prior CORE to
#                        .claude/bcos-claude-reference.md if it differed)
#   no CORE markers    → splice the CORE block at the end of the file
mkdir -p "$TARGET_DIR/.claude"
CLAUDE_MD_RESULT=$("$PY" "$SCRIPT_DIR/.claude/scripts/_claude_md.py" \
    --target "$TARGET_DIR/CLAUDE.md" \
    --source "$SCRIPT_DIR/CLAUDE.md" \
    --recovery "$TARGET_DIR/.claude/bcos-claude-reference.md" 2>&1) || {
        echo -e "  ${YELLOW}WARN${NC}  CLAUDE.md helper failed: $CLAUDE_MD_RESULT"
        SKIPPED=$((SKIPPED + 1))
}
CLAUDE_MD_ACTION=$(echo "$CLAUDE_MD_RESULT" | grep '^action=' | cut -d= -f2)
case "$CLAUDE_MD_ACTION" in
    created)
        echo -e "  ${GREEN}OK${NC}    CLAUDE.md (created from template)"
        ;;
    spliced)
        echo -e "  ${GREEN}OK${NC}    CLAUDE.md (BCOS:CORE block appended; your existing content preserved)"
        ;;
    replaced)
        echo -e "  ${GREEN}OK${NC}    CLAUDE.md (BCOS:CORE block refreshed)"
        echo "        Previous CORE saved to .claude/bcos-claude-reference.md"
        ;;
    unchanged)
        echo -e "  ${YELLOW}SKIP${NC}  CLAUDE.md (already current)"
        SKIPPED=$((SKIPPED + 1))
        ;;
esac
echo ""

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
chmod +x .claude/scripts/set_profile.sh 2>/dev/null || true

# ─── Gitignore profile (generate default if none) ───────────────────
# If the target repo has no .gitignore yet, generate one from the "personal"
# profile — the common case for BCOS users (private, single-owner knowledge
# repo synced across workstations). Team / multi-tenant installs can switch
# with:
#   bash .claude/scripts/set_profile.sh shared
GITIGNORE_GENERATED=""
if [ ! -f "$TARGET_DIR/.gitignore" ] && [ -f ".claude/templates/gitignore.template" ] && [ -x ".claude/scripts/set_profile.sh" ]; then
    if bash .claude/scripts/set_profile.sh personal >/dev/null 2>&1; then
        GITIGNORE_GENERATED="personal"
        echo -e "  ${GREEN}CREATE${NC}  .gitignore (profile: personal)"
        echo ""
    fi
fi

# ─── Permissions catalog drift check (advisory) ─────────────────────
# Surfaces drift between docs/_bcos-framework/architecture/permissions-catalog.md
# (SoT) and .claude/settings.json > permissions.allow. Advisory only —
# never blocks install. Multi-plugin contract:
# docs/_bcos-framework/architecture/permissions-write-contract.md
if [ -x ".claude/bin/python3" ] && [ -f ".claude/scripts/validate_permissions_catalog.py" ]; then
    PERMISSIONS_DRIFT=""
    PERMISSIONS_DRIFT=$(.claude/bin/python3 .claude/scripts/validate_permissions_catalog.py --quiet 2>&1) || true
    if [ -n "$PERMISSIONS_DRIFT" ]; then
        echo ""
        echo -e "  ${YELLOW}ADVISORY${NC} $PERMISSIONS_DRIFT"
        echo -e "  ${YELLOW}        ${NC} Detail: .claude/bin/python3 .claude/scripts/validate_permissions_catalog.py"
        echo -e "  ${YELLOW}        ${NC} Contract: docs/_bcos-framework/architecture/permissions-write-contract.md"
        echo ""
    fi
fi

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
if [ "$GITIGNORE_GENERATED" = "personal" ]; then
echo -e "  ${YELLOW}TIP:${NC} A .gitignore was generated using the 'personal' profile"
echo "  (knowledge artifacts tracked — best for private, single-owner knowledge"
echo "  repos synced across workstations). If BCOS is dropped into a team or"
echo "  multi-tenant repo and you want runtime artifacts gitignored, switch to"
echo "  'shared':"
echo ""
echo "      bash .claude/scripts/set_profile.sh shared"
echo ""
fi
if [ "$SKIPPED" -gt 0 ]; then
echo -e "  ${YELLOW}NOTE:${NC} Some files were skipped (already existed)."
echo "  If you have an existing CLAUDE.md, merge the BCOS sections from:"
echo "  .claude/bcos-claude-reference.md"
echo ""
fi

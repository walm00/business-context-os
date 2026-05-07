#!/usr/bin/env bash
#
# pre_commit_validate.sh — BCOS pre-commit validation hook
# bcos-hook-type: git
#
# Runs the same checks as .github/workflows/ci.yml locally, before the commit
# lands. Catches JSON syntax errors, missing frontmatter, stale references,
# and ecosystem drift while they're still easy to fix.
#
# Opt-in: install manually if you want strict blocking validation.
# Not auto-installed — Claude Code hooks provide non-blocking validation.
# Installs to .git/hooks/pre-commit, NOT .claude/settings.json — so the
# ecosystem analyzer skips this file via the `bcos-hook-type: git` marker.
#
# Bypass with:   git commit --no-verify
# Uninstall with:   rm .git/hooks/pre-commit
# Re-install with:  cp .claude/hooks/pre_commit_validate.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
#

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
    # Not in a git repo — silently skip (shouldn't happen via git hook but defensive)
    exit 0
}
cd "$REPO_ROOT"

# Graceful fallback if python3 is missing — don't block commits on environment issues
if ! command -v python3 > /dev/null 2>&1; then
    echo "  BCOS pre-commit: python3 not found — skipping validation."
    echo "  (Install python3 to enable local checks, or bypass with 'git commit --no-verify'.)"
    exit 0
fi

echo "  BCOS pre-commit validation (bypass with --no-verify):"

# ----------------------------------------------------------- 1. JSON validation
JSON_FAILED=0
for f in \
    .claude/quality/ecosystem/state.json \
    .claude/quality/ecosystem/lessons.json \
    .claude/registries/reference-index.json \
    .claude/registries/entities.json \
    .claude/settings.json \
    .claude/quality/schedule-config.template.json \
    .claude/quality/schedule-config.json; do
    if [ -f "$f" ]; then
        if ! python3 -m json.tool "$f" > /dev/null 2>&1; then
            echo "    FAIL: $f is not valid JSON"
            JSON_FAILED=1
        fi
    fi
done
if [ $JSON_FAILED -eq 1 ]; then
    echo ""
    echo "  Commit blocked — invalid JSON above."
    echo "  Fix the files, or run: git commit --no-verify"
    exit 1
fi
echo "    OK: JSON"

# ---------------------------------------------------- 2. Frontmatter validation
if [ -f .claude/scripts/validate_frontmatter.py ]; then
    if ! python3 .claude/scripts/validate_frontmatter.py > /dev/null 2>&1; then
        echo "    FAIL: frontmatter issues"
        python3 .claude/scripts/validate_frontmatter.py 2>&1 | grep -E "^(FAIL|MISSING|INVALID|  ->)" | head -10
        echo ""
        echo "  Commit blocked — frontmatter issues above."
        echo "  Fix the files, or run: git commit --no-verify"
        exit 1
    fi
    echo "    OK: frontmatter"
fi

# --------------------------------- 3. Reference + ecosystem state registry drift
if [ -f .claude/scripts/validate_references.py ]; then
    if ! python3 .claude/scripts/validate_references.py > /dev/null 2>&1; then
        echo "    FAIL: reference / ecosystem state drift"
        python3 .claude/scripts/validate_references.py 2>&1 | grep -E "^(FAIL|MISSING|UNDECLARED|  ->)" | head -15
        echo ""
        echo "  Commit blocked — registry drift above."
        echo "  Common fix: if you added a new skill or agent, register it in"
        echo "  .claude/quality/ecosystem/state.json and .claude/registries/reference-index.json."
        echo "  Or bypass with: git commit --no-verify"
        exit 1
    fi
    echo "    OK: references + state.json"
fi

# ------------------------------------------------- 4. Ecosystem integration
if [ -f .claude/scripts/analyze_integration.py ]; then
    if ! python3 .claude/scripts/analyze_integration.py --ci > /dev/null 2>&1; then
        echo "    FAIL: ecosystem coverage"
        python3 .claude/scripts/analyze_integration.py --ci 2>&1 | tail -10
        echo ""
        echo "  Commit blocked — ecosystem coverage gaps above."
        echo "  Fix the gaps, or run: git commit --no-verify"
        exit 1
    fi
    echo "    OK: ecosystem integration"
fi

echo "  All checks passed."
exit 0

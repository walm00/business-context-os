#!/usr/bin/env bash
# .recovery/promote.sh — promote staged recovery files to canonical paths.
#
# Usage:
#   bash .recovery/promote.sh --dry-run   # preview only (default — safe)
#   bash .recovery/promote.sh --apply     # actually copy files into place
#
# Per the recovery plan in docs/_inbox/2026-05-07-bcos-recovery-plan.md:
# - PROMOTE rows: canonical missing → safe copy
# - NEEDS-MERGE rows: handled per maintainer's per-file decision (encoded below)
# - SKIP rows: identical to canonical → no-op
#
# Maintainer's promotion rules (Guntis 2026-05-07):
# - Ecosystem accumulating state (lessons.json, learned-rules.json,
#   learning-blocklist.json, resolutions.jsonl, state.json) → PROMOTE
#   from .recovery/ (worktree + git have real data; regenerated empties
#   are placeholders).
# - Derived artifacts that just got regenerated freshly (bcos-inventory.json,
#   context-index.json, document-index.md, bcos-control-map.md,
#   .session-diary.md, schedule-config.json) → KEEP REGENERATED, don't
#   overwrite from .recovery/.
# - All PROMOTE rows (canonical doesn't exist) → safe copy.

set -uo pipefail

cd "$(dirname "$0")/.." 2>/dev/null || cd "C:/Users/Mr Coders/Documents/GitHub/business-context-os-dev"

MODE="${1:-}"
if [ "$MODE" != "--dry-run" ] && [ "$MODE" != "--apply" ]; then
    echo "Usage: $0 --dry-run | --apply" >&2
    exit 1
fi

# NEEDS-MERGE per-file decisions
# (key = canonical path, value = "PROMOTE" or "SKIP")
declare -A NEEDS_MERGE_DECISION=(
    ## Promote — accumulating maintainer state worth keeping
    [".claude/quality/ecosystem/state.json"]="PROMOTE"
    [".claude/quality/ecosystem/lessons.json"]="PROMOTE"
    [".claude/quality/ecosystem/learned-rules.json"]="PROMOTE"
    [".claude/quality/ecosystem/learning-blocklist.json"]="PROMOTE"
    [".claude/quality/ecosystem/resolutions.jsonl"]="PROMOTE"
    [".claude/hooks/pre_commit_validate.sh"]="PROMOTE"
    ## Skip — fresh regenerations are correct; recovery sources are stale
    [".claude/quality/bcos-inventory.json"]="SKIP"
    [".claude/quality/context-index.json"]="SKIP"
    [".claude/quality/schedule-config.json"]="SKIP"
    ["docs/document-index.md"]="SKIP"
    ["docs/.session-diary.md"]="SKIP"
    ["docs/bcos-control-map.md"]="SKIP"
    [".claude/quality/schedule-config.template.json"]="SKIP"
)

# Source preference for NEEDS-MERGE PROMOTE entries — when the same path
# appears in multiple .recovery/ subtrees, this decides which wins.
preferred_source() {
    case "$1" in
        ".claude/quality/ecosystem/state.json") echo "from-worktree" ;;
        ".claude/quality/ecosystem/lessons.json") echo "from-worktree" ;;
        ".claude/quality/ecosystem/learned-rules.json") echo "from-git" ;;
        ".claude/quality/ecosystem/learning-blocklist.json") echo "from-git" ;;
        ".claude/quality/ecosystem/resolutions.jsonl") echo "from-git" ;;
        ".claude/hooks/pre_commit_validate.sh") echo "from-siblings" ;;
        *) echo "from-worktree" ;;  # default precedence: worktree > git > siblings
    esac
}

declare -i copied=0 skipped=0 needs_decision=0 errors=0

walk() {
    local source_dir="$1"
    local base=".recovery/$source_dir"
    [ -d "$base" ] || return
    while IFS= read -r f; do
        rel="${f#$base/}"
        # Decide action
        if [ ! -e "$rel" ]; then
            action="PROMOTE"
            reason="canonical missing"
        elif diff -q "$f" "$rel" > /dev/null 2>&1; then
            action="SKIP"
            reason="identical"
        else
            # NEEDS-MERGE: look up decision
            decision="${NEEDS_MERGE_DECISION[$rel]:-UNKNOWN}"
            if [ "$decision" = "PROMOTE" ]; then
                pref=$(preferred_source "$rel")
                if [ "$source_dir" != "$pref" ]; then
                    action="SKIP"
                    reason="not preferred source ($source_dir; want $pref)"
                else
                    action="PROMOTE"
                    reason="needs-merge resolved → promote (per maintainer)"
                fi
            elif [ "$decision" = "SKIP" ]; then
                action="SKIP"
                reason="needs-merge resolved → keep canonical (per maintainer)"
            else
                action="DECIDE"
                reason="UNDECIDED needs-merge — see manifest"
                needs_decision+=1
            fi
        fi
        # Apply or preview
        case "$action" in
            PROMOTE)
                if [ "$MODE" = "--apply" ]; then
                    mkdir -p "$(dirname "$rel")"
                    if cp -p "$f" "$rel" 2>/dev/null; then
                        echo "  COPIED  $rel  ← $source_dir"
                        copied+=1
                    else
                        echo "  ERROR   $rel  (cp failed)"
                        errors+=1
                    fi
                else
                    echo "  WOULD COPY  $rel  ← $source_dir  ($reason)"
                    copied+=1
                fi
                ;;
            SKIP)
                skipped+=1
                # Suppressed in dry-run output unless verbose; show reason for needs-merge
                if [ "$reason" != "identical" ] && [ "$reason" != "not preferred source"* ]; then
                    [ "$MODE" = "--dry-run" ] && echo "  SKIP        $rel  ($reason)"
                fi
                ;;
            DECIDE)
                echo "  DECIDE      $rel  ($reason)"
                ;;
        esac
    done < <(find "$base" -type f 2>/dev/null)
}

echo "=== Mode: $MODE ==="
echo ""
echo "## from-worktree (highest precedence)"
walk from-worktree
echo ""
echo "## from-git"
walk from-git
echo ""
echo "## from-siblings"
walk from-siblings
echo ""
echo "=== Summary ==="
echo "  PROMOTE: $copied"
echo "  SKIP: $skipped"
echo "  DECIDE: $needs_decision"
echo "  ERRORS: $errors"
if [ "$MODE" = "--dry-run" ]; then
    echo ""
    echo "Dry-run only. Re-run with --apply to actually copy files."
fi

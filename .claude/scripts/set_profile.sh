#!/usr/bin/env bash
# set_profile.sh — Generate .gitignore from .claude/templates/gitignore.template
# based on a chosen profile (shared | personal).
#
# Usage:
#   bash .claude/scripts/set_profile.sh shared
#   bash .claude/scripts/set_profile.sh personal
#   bash .claude/scripts/set_profile.sh           # show current profile
#
# Profiles:
#   shared    — BCOS dropped into a multi-tenant/team repo. Runtime artifacts
#               (sessions, lessons, diary, digest, wake-up, doc-index) are
#               gitignored to keep the host codebase clean. (Default.)
#   personal  — BCOS as a personal knowledge repo, never shared. Knowledge
#               artifacts ARE tracked so they sync across machines. Only
#               secrets and machine-local files stay ignored.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

TEMPLATE=".claude/templates/gitignore.template"
PROFILE_FILE=".claude/bcos-profile"
GITIGNORE=".gitignore"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "ERROR: Template not found at $TEMPLATE" >&2
  echo "Has BCOS been installed correctly?" >&2
  exit 1
fi

# No-arg invocation: report current profile and exit
if [[ $# -eq 0 ]]; then
  if [[ -f "$PROFILE_FILE" ]]; then
    echo "Current profile: $(cat "$PROFILE_FILE")"
  else
    echo "Current profile: shared (default — no $PROFILE_FILE)"
  fi
  echo
  echo "Usage: bash $0 <shared|personal>"
  exit 0
fi

PROFILE="$1"
if [[ "$PROFILE" != "shared" && "$PROFILE" != "personal" ]]; then
  echo "ERROR: Unknown profile '$PROFILE'. Must be 'shared' or 'personal'." >&2
  exit 2
fi

# Render template by stripping the inactive profile block.
# The template uses "# === SHARED ONLY ===" and "# === PERSONAL ONLY ==="
# section headers. Everything from a matching header up to the next
# "# === ... ===" header (or EOF) is the block.
RENDERED="$(awk -v profile="$PROFILE" '
  BEGIN { skipping = 0 }
  /^# === ALWAYS ===/        { skipping = 0; print; next }
  /^# === SHARED ONLY ===/   { skipping = (profile != "shared");   print; next }
  /^# === PERSONAL ONLY ===/ { skipping = (profile != "personal"); print; next }
  { if (!skipping) print }
' "$TEMPLATE")"

# Prepend a header so users know not to hand-edit
HEADER="# Generated from .claude/templates/gitignore.template
# Profile: $PROFILE
# Re-generate with: bash .claude/scripts/set_profile.sh <shared|personal>
# DO NOT edit by hand — edit the template instead.
"

NEW_CONTENT="${HEADER}
${RENDERED}"

# Show diff if .gitignore already exists and would change
if [[ -f "$GITIGNORE" ]]; then
  if diff -q <(printf '%s\n' "$NEW_CONTENT") "$GITIGNORE" >/dev/null 2>&1; then
    echo "No changes — $GITIGNORE already matches profile '$PROFILE'."
  else
    echo "Diff (current → new):"
    echo "----------------------------------------"
    diff -u "$GITIGNORE" <(printf '%s\n' "$NEW_CONTENT") || true
    echo "----------------------------------------"
  fi
fi

# Write the new .gitignore and profile marker
printf '%s\n' "$NEW_CONTENT" > "$GITIGNORE"
echo "$PROFILE" > "$PROFILE_FILE"

echo
echo "Wrote $GITIGNORE (profile: $PROFILE)"
echo "Wrote $PROFILE_FILE"
echo
echo "Next steps:"
echo "  git status              # see what's newly tracked or ignored"
echo "  git add .gitignore $PROFILE_FILE"
echo "  git commit -m 'Set BCOS profile: $PROFILE'"
if [[ "$PROFILE" == "personal" ]]; then
  echo
  echo "Personal profile note: knowledge artifacts (session diary, lessons,"
  echo "wake-up context, document index, daily digest) are now tracked. Review"
  echo "before committing — they may contain content you didn't realize was"
  echo "previously gitignored."
fi

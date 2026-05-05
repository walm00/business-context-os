#!/usr/bin/env bash
# =============================================================================
# precompact_save.sh - Claude Code PreCompact hook
#
# Fires before context window compression. ALWAYS blocks to ensure the AI
# saves all session context before detailed information is lost.
#
# Hook event:  PreCompact
# Matcher:     (none — fires on every compaction)
# Behavior:    Always blocks
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_DIR/.claude/hook_state"
SESSIONS_DIR="$PROJECT_DIR/docs/_inbox/sessions"

mkdir -p "$STATE_DIR" "$SESSIONS_DIR"

# Generate timestamp for filename
TIMESTAMP=$(date +%Y-%m-%d_%H%M 2>/dev/null || echo "session")

# ISO-8601 UTC timestamp — portable across GNU date (Linux) and BSD date (macOS).
# BSD date doesn't support `-Iseconds`, so we format explicitly in UTC.
NOW_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo '2026-01-01T00:00:00Z')

# Log the event
echo "${NOW_ISO} PRECOMPACT save triggered" \
    >> "$STATE_DIR/hook.log" 2>/dev/null || true

# Always block — compaction always warrants a save
cat <<HOOKJSON
{
  "decision": "block",
  "reason": "EMERGENCY SAVE — Context compaction imminent.\nEverything not saved will be compressed and may lose detail.\n\nWrite a comprehensive capture to docs/_inbox/sessions/${TIMESTAMP}_precompact.md:\n\n---\ntype: session-capture\ndate: ${NOW_ISO}\nstatus: raw\ntrigger: precompact\n---\n## Session Summary\n- [1-2 sentence overview of what this session accomplished]\n\n## Decisions\n- [ALL decisions made, with rationale]\n\n## Discoveries\n- [ALL new information learned]\n\n## Follow-ups\n- [ ] [ALL action items, even partial ones]\n\n## Files Changed\n- [ALL file paths modified with brief note of what changed]\n\n## Open Threads\n- [Anything in-progress that needs to continue after compaction]\n\nBe thorough — this is your last chance to capture before context is compressed."
}
HOOKJSON

exit 0

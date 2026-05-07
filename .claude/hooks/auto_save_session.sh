#!/usr/bin/env bash
# =============================================================================
# auto_save_session.sh - Claude Code Stop hook
#
# Fires after every assistant response. Every 15 human messages, blocks the AI
# and tells it to save session context to docs/_inbox/sessions/.
#
# Hook event:  Stop
# Matcher:     (none — fires on every stop)
# Behavior:    Blocks every 15 messages, pass-through otherwise
#
# State: .claude/hook_state/{session_id}_last_save
# =============================================================================

set -euo pipefail

SAVE_INTERVAL="${BCOS_SAVE_INTERVAL:-15}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_DIR/.claude/hook_state"
SESSIONS_DIR="$PROJECT_DIR/docs/_inbox/sessions"

mkdir -p "$STATE_DIR" "$SESSIONS_DIR"

# ---------------------------------------------------------------------------
# Read JSON input from stdin
# ---------------------------------------------------------------------------
INPUT=$(cat)

# Extract fields using python (available everywhere, no jq dependency).
# Pipe $INPUT to stdin — never interpolate untrusted hook input into a -c string.
read -r STOP_HOOK_ACTIVE SESSION_ID TRANSCRIPT_PATH <<< "$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read())
except Exception:
    data = {}
active = str(data.get('stop_hook_active', False)).lower()
sid = data.get('session_id', 'unknown')
tp = data.get('transcript_path', '')
print(f'{active} {sid} {tp}')
" 2>/dev/null || echo "false unknown ")"

# ---------------------------------------------------------------------------
# Loop prevention: if we already blocked once, let it through
# ---------------------------------------------------------------------------
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
    echo '{}'
    exit 0
fi

# ---------------------------------------------------------------------------
# Count human messages in transcript
# ---------------------------------------------------------------------------
if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    echo '{}'
    exit 0
fi

# Pass transcript path via env var — never interpolate into source.
EXCHANGE_COUNT=$(BCOS_TRANSCRIPT_PATH="$TRANSCRIPT_PATH" python3 -c "
import json, os
count = 0
path = os.environ.get('BCOS_TRANSCRIPT_PATH', '')
try:
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get('role') == 'user':
                    content = str(entry.get('content', ''))
                    if '<command-message>' not in content:
                        count += 1
            except json.JSONDecodeError:
                continue
except Exception:
    pass
print(count)
" 2>/dev/null || echo "0")

# ---------------------------------------------------------------------------
# Check last save point
# ---------------------------------------------------------------------------
SAVE_FILE="$STATE_DIR/${SESSION_ID}_last_save"

if [ -f "$SAVE_FILE" ]; then
    LAST_SAVE=$(cat "$SAVE_FILE")
else
    LAST_SAVE=0
fi

SINCE_LAST=$((EXCHANGE_COUNT - LAST_SAVE))

# ---------------------------------------------------------------------------
# Decide: block or pass through
# ---------------------------------------------------------------------------
if [ "$SINCE_LAST" -ge "$SAVE_INTERVAL" ]; then
    # Update save point
    echo "$EXCHANGE_COUNT" > "$SAVE_FILE"

    # Log — use UTC Zulu format (portable across GNU and BSD date)
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo 'unknown') AUTO-SAVE triggered: $EXCHANGE_COUNT messages ($SINCE_LAST since last save)" \
        >> "$STATE_DIR/hook.log" 2>/dev/null || true

    # Generate timestamp for filename
    TIMESTAMP=$(date +%Y-%m-%d_%H%M 2>/dev/null || echo "session")

    # ISO-8601 UTC timestamp for the session-capture frontmatter.
    # Using `date -u +"%Y-%m-%dT%H:%M:%SZ"` because BSD date (macOS) doesn't support `-Iseconds`.
    NOW_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo '2026-01-01T00:00:00Z')

    # Block the AI and tell it what to save
    cat <<HOOKJSON
{
  "decision": "block",
  "reason": "SESSION CHECKPOINT — $SINCE_LAST messages since last save.\nWrite a session capture to docs/_inbox/sessions/${TIMESTAMP}.md with this structure:\n\n---\ntype: session-capture\ndate: ${NOW_ISO}\nstatus: raw\n---\n## Decisions\n- [bullet points of decisions made this session]\n\n## Discoveries\n- [bullet points of new information learned]\n\n## Follow-ups\n- [ ] [action items identified]\n\n## Files Changed\n- [list of file paths modified]\n\nKeep each section to 3-5 bullets maximum. Skip empty sections."
}
HOOKJSON
else
    echo '{}'
fi

exit 0

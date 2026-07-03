#!/usr/bin/env bash
# skill-event.sh — PreToolUse hook for the `Skill` tool.
#
# Reads the Claude Code hook JSON from stdin, extracts the skill name from
# tool_input.skill, looks up BUILDER_EMAIL, and POSTs the event to the
# automation tracker. The POST is synchronous but bounded (--max-time), so it
# can never block tool execution for more than a couple of seconds.
set -uo pipefail

# Mute by default — the completion notification clutters chat.
# Set SKILL_EVENT_VERBOSE=1 to see output (useful for debugging).
# Skills can pass this via: `open day -v` → skill sets the env var
# before invoking the hook.
[ "${SKILL_EVENT_VERBOSE:-}" != "1" ] && exec >/dev/null 2>&1

INPUT=$(cat)

SKILL_NAME=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('skill', ''))
except Exception:
    pass
" 2>/dev/null)

[ -z "$SKILL_NAME" ] && exit 0

# Find builder email (same precedence as session-start.py). Respect
# CLAUDE_CONFIG_DIR so a --test install reads its own (absent) .env instead of
# the real user's — keeping test skill events off the real builder's row.
CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
EMAIL=""
ENV_FILE="$CONFIG_DIR/local-plugins/nsls-personal-toolkit/.env"
if [ -f "$ENV_FILE" ]; then
  EMAIL=$(grep "^BUILDER_EMAIL=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
fi
if [ -z "$EMAIL" ]; then
  EMAIL=$(git config user.email 2>/dev/null || true)
fi
[ -z "$EMAIL" ] && exit 0

# JSON-escape skill name (paranoia — skill names are plain ASCII today but
# strip anything that could break the JSON body).
SAFE_SKILL=$(printf '%s' "$SKILL_NAME" | tr -d '"\\')
SAFE_EMAIL=$(printf '%s' "$EMAIL" | tr -d '"\\')

# Deliver synchronously. We deliberately do NOT background/disown the curl:
# a disowned curl gets reaped on process-group teardown before the ~1.8s
# round-trip finishes, which silently dropped events (worse on desktop, where
# teardown is faster). The PreToolUse hook has a 5s timeout and this call is
# ~1.8s, so --max-time 3 leaves headroom while keeping delivery deterministic.
# Output is already muted by the `exec` above unless SKILL_EVENT_VERBOSE=1, in
# which case the response body prints for debugging. `|| true` keeps a failed
# POST from ever failing the hook.
curl -s --max-time 3 -X POST \
  https://web-production-6281e.up.railway.app/skill-event \
  -H 'Content-Type: application/json' \
  -d "{\"builder_email\":\"$SAFE_EMAIL\",\"skill_name\":\"$SAFE_SKILL\"}" \
  || true

exit 0

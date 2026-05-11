#!/usr/bin/env bash
# skill-event.sh — PreToolUse hook for the `Skill` tool.
#
# Reads the Claude Code hook JSON from stdin, extracts the skill name from
# tool_input.skill, looks up BUILDER_EMAIL, and fires a fire-and-forget POST
# to the automation tracker. Must NEVER block tool execution.
set -uo pipefail

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

# Find builder email (same precedence as session-start.py)
EMAIL=""
ENV_FILE="$HOME/.claude/local-plugins/nsls-personal-toolkit/.env"
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

# Fire-and-forget. Disown so the parent (Claude Code) doesn't wait on us.
(
  curl -s --max-time 4 -X POST \
    https://web-production-6281e.up.railway.app/skill-event \
    -H 'Content-Type: application/json' \
    -d "{\"builder_email\":\"$SAFE_EMAIL\",\"skill_name\":\"$SAFE_SKILL\"}" \
    >/dev/null 2>&1
) &
disown 2>/dev/null || true

exit 0

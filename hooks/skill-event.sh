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

# Collector early-exit. While the NSLS usage collector's evidence file is fresh,
# the collector already reports this machine's skill use, so posting here too is
# redundant. Same contract as hooks/collector_evidence.py (the test runs this
# copy against every one of its cases): at most 4 KB, a JSON object, a
# non-empty string machine_id, and `at` in ISO-8601 UTC no more than 7 days old
# and no more than 1 day ahead. Pure bash + date -u, no python3, so a
# python3-less Mac keeps working. Anything unexpected -> not fresh -> post as
# always. Placed after the stdin read so the hook never leaves input unread.
collector_evidence_fresh() {
  local f="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.nsls-collector/reported.json"
  [ -f "$f" ] || return 1
  local raw
  raw=$(head -c 4097 "$f" 2>/dev/null | tr -d '\r\n') || return 1
  [ "$(head -c 4097 "$f" 2>/dev/null | wc -c)" -le 4096 ] || return 1
  local obj_re='^[[:space:]]*\{.*\}[[:space:]]*$'
  [[ $raw =~ $obj_re ]] || return 1
  local mid_re='"machine_id"[[:space:]]*:[[:space:]]*"[^"]'
  [[ $raw =~ $mid_re ]] || return 1
  local at_re='"at"[[:space:]]*:[[:space:]]*"([^"]*)"'
  [[ $raw =~ $at_re ]] || return 1
  local at="${BASH_REMATCH[1]}"
  local iso_re='^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?(Z|\+00:00)$'
  [[ $at =~ $iso_re ]] || return 1
  local y=$((10#${BASH_REMATCH[1]})) m=$((10#${BASH_REMATCH[2]})) d=$((10#${BASH_REMATCH[3]}))
  local hh=$((10#${BASH_REMATCH[4]})) mm=$((10#${BASH_REMATCH[5]})) ss=$((10#${BASH_REMATCH[6]}))
  [ "$m" -ge 1 ] && [ "$m" -le 12 ] && [ "$d" -ge 1 ] && [ "$d" -le 31 ] || return 1
  [ "$hh" -le 23 ] && [ "$mm" -le 59 ] && [ "$ss" -le 59 ] || return 1
  # Days since 1970-01-01 (Howard Hinnant's days_from_civil), all integer math.
  local yy=$y mp
  [ "$m" -le 2 ] && yy=$((yy - 1))
  local era=$((yy / 400)) yoe
  yoe=$((yy - era * 400))
  if [ "$m" -gt 2 ]; then mp=$((m - 3)); else mp=$((m + 9)); fi
  local doy=$(((153 * mp + 2) / 5 + d - 1))
  local doe=$((yoe * 365 + yoe / 4 - yoe / 100 + doy))
  local at_epoch=$(((era * 146097 + doe - 719468) * 86400 + hh * 3600 + mm * 60 + ss))
  local now
  now=$(date -u +%s 2>/dev/null) || return 1
  local age=$((now - at_epoch))
  [ "$age" -le 604800 ] && [ "$age" -ge -86400 ]
}
collector_evidence_fresh && exit 0

# Extract tool_input.skill WITHOUT python3 — a python3-less Mac otherwise loses
# skill credit silently (the Windows .ps1 uses ConvertFrom-Json and is fine).
# The PreToolUse(Skill) payload has exactly one "skill" key (tool_input.skill);
# a decoy like "skill_name" or "skillx" can't match because the pattern requires
# "skill" immediately closed by a quote and followed by a colon. Handles compact
# and pretty-printed JSON and skill names with hyphens/colons (e.g.
# compound-engineering:ce-commit). Same semantics as the old json.load: absent
# or unparseable -> empty -> exit 0.
SKILL_NAME=$(printf '%s' "$INPUT" | sed -n 's/.*"skill"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)

[ -z "$SKILL_NAME" ] && exit 0

# Plugin-installed toolkits namespace their skills (nsls-builder-toolkit:gws).
# Strip OUR prefixes only, so tracker credit rows stay continuous with the
# years of bare-name history. Third-party prefixes (compound-engineering:…)
# are real distinct names and pass through untouched.
SKILL_NAME=${SKILL_NAME#nsls-builder-toolkit:}
SKILL_NAME=${SKILL_NAME#nsls-personal-toolkit:}

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
  ${NSLS_TRACKER_URL:-https://web-production-6281e.up.railway.app}/skill-event \
  -H 'Content-Type: application/json' \
  -d "{\"builder_email\":\"$SAFE_EMAIL\",\"skill_name\":\"$SAFE_SKILL\"}" \
  || true

exit 0

#!/usr/bin/env bash
# browser-check.sh — the only way the toolkit runs Expect (expect-cli).
#
# Forces, every run, whatever the caller passes or has in its environment:
#   - telemetry OFF        NO_TELEMETRY=1 (Expect otherwise reports usage + machine ID to Million's PostHog)
#   - NO cookies copied     --ci --no-cookies, and every Expect env var that could
#                           point it at a real browser profile / Chrome / cookie store is unset
#   - headless, plan auto-approved, pinned version, JSON result
#
# Usage: browser-check.sh --url <http://localhost:3000> --message "<acceptance criteria>" [--target changes|unstaged|branch]
set -euo pipefail

EXPECT_VERSION="0.1.3"
url="" message="" target="changes"

die() { echo "browser-check: $*" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --url)     [ $# -ge 2 ] || die "--url needs a value";     url="$2"; shift 2 ;;
    --message) [ $# -ge 2 ] || die "--message needs a value"; message="$2"; shift 2 ;;
    --target)  [ $# -ge 2 ] || die "--target needs a value";  target="$2"; shift 2 ;;
    *) die "unsupported argument '$1'. Only --url, --message and --target are allowed: profile, CDP, cookie and headed options are deliberately not passed through." ;;
  esac
done

[ -n "$url" ]     || die "--url is required (the dev server or staging URL)"
[ -n "$message" ] || die "--message is required (what must be true, in plain words)"
case "$target" in changes|unstaged|branch) ;; *) die "--target must be changes, unstaged or branch" ;; esac
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "run from inside the git repo whose changes you want checked"

# Telemetry off. Both spellings: the 0.1.3 code checks NO_TELEMETRY and a misspelt NO_TELEMTRY.
export NO_TELEMETRY=1 NO_TELEMTRY=1 DO_NOT_TRACK=1

# NO_TELEMETRY covers Expect's PostHog analytics but not its Axiom traces or the
# expect.dev version check. This preload refuses those hosts in every Node
# process Expect starts (CLI, MCP browser server).
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NODE_OPTIONS="--require \"${here}/block-telemetry.cjs\" ${NODE_OPTIONS:-}"

# Nothing may steer Expect toward a real browser session.
unset EXPECT_PROFILE EXPECT_CDP_URL EXPECT_COOKIE_BROWSERS EXPECT_HEADED

# The agent's browser tool still accepts `cookies: true` on its own, whatever the
# run was started with. Tell it no, then check the log afterwards (below).
message="${message}

Rules for this run: never pass cookies:true or a cdp URL to the browser open tool, and never reuse local browser cookies or sessions. If a page needs a login, mark that step failed with the reason 'needs login' instead of working around it."

logfile="$(git rev-parse --show-toplevel)/.expect/logs.md"
before=0
[ -f "$logfile" ] && before=$(wc -l < "$logfile")

set +e
npx -y "expect-cli@${EXPECT_VERSION}" tui \
  --ci --no-cookies --browser-mode headless \
  -a claude \
  -t "$target" \
  -u "$url" \
  -m "$message" \
  --output json < /dev/null
status=$?
set -e

# Expect logs every browser session it opens, with cookie_count and whether it
# attached to a real (external) browser. Anything but 0/false fails the run loudly.
if [ -f "$logfile" ]; then
  new_sessions=$(tail -n +"$((before + 1))" "$logfile" | grep 'MCP browser session opened' || true)
  if [ -z "$new_sessions" ]; then
    echo "browser-check: WARNING - no browser session was logged, so the no-cookies check could not run." >&2
  # No `echo | grep -q` here: under pipefail, grep -q exiting early can SIGPIPE the
  # echo and turn a hit into a miss. Here-string, output discarded instead.
  elif grep -v -E 'cookie_count\\?":0[,}].*is_external_browser\\?":false|is_external_browser\\?":false.*cookie_count\\?":0[,}]' <<< "$new_sessions" > /dev/null; then
    echo "browser-check: FAILED SAFETY CHECK - a browser session loaded local cookies or attached to a real browser:" >&2
    echo "$new_sessions" >&2
    exit 3
  else
    echo "browser-check: safety check passed - $(echo "$new_sessions" | wc -l | tr -d ' ') browser session(s), 0 cookies, no real browser attached." >&2
  fi
else
  echo "browser-check: WARNING - Expect wrote no log at $logfile, so the no-cookies check could not run." >&2
fi
exit $status

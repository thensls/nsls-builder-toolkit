#!/usr/bin/env bash
# browser-check.sh — the only way the toolkit runs Expect (expect-cli).
#
# Forces, every run, whatever the caller passes or has in its environment:
#   - telemetry OFF        NO_TELEMETRY=1 plus a blocker imported by every Expect entry
#                           point (PostHog, Axiom, expect.dev refused)
#   - NO cookies copied     --ci --no-cookies, Expect's cookie-import branch patched dead,
#                           and every env var that could point it at a real browser unset
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

# Private, pinned install of Expect with the blocker wired into every entry
# point. NODE_OPTIONS (above) does not reach the browser MCP server: the agent
# launches it as `node browser-mcp.js` with an explicit env list. So the
# blocker is imported from the first line of each entry file instead.
install_dir="${XDG_CACHE_HOME:-$HOME/.cache}/nsls-browser-check/expect-cli-${EXPECT_VERSION}"
dist="${install_dir}/node_modules/expect-cli/dist"
mkdir -p "$(dirname "$install_dir")"

# Two checks can start at once (parallel agents). Setup below is serialized with a
# mkdir lock (no flock on macOS), and every file is published with an atomic mv from
# a per-process temp file, so a run never sees, or removes, another run's half-write.
lock="${install_dir}.lock"
waited=0
until mkdir "$lock" 2>/dev/null; do
  # A lock older than 10 minutes is from a run that died mid-setup.
  if [ -n "$(find "$lock" -maxdepth 0 -mmin +10 2>/dev/null)" ]; then rmdir "$lock" 2>/dev/null || true; continue; fi
  [ "$waited" -ge 600 ] && die "timed out waiting for another browser check to finish setting up (${lock})"
  sleep 1; waited=$((waited + 1))
done
trap 'rmdir "$lock" 2>/dev/null || true' EXIT

if [ ! -f "${dist}/index.js" ]; then
  echo "browser-check: installing expect-cli@${EXPECT_VERSION} (first run only)..." >&2
  mkdir -p "$install_dir"
  npm install --prefix "$install_dir" --no-audit --no-fund --loglevel=error \
    "expect-cli@${EXPECT_VERSION}" >&2 || die "npm install of expect-cli@${EXPECT_VERSION} failed"
fi
# Refreshed every run; staged then moved so a running check never imports a partial copy.
cp "${here}/block-telemetry.cjs" "${dist}/nsls-block-telemetry.cjs.tmp.$$"
mv -f "${dist}/nsls-block-telemetry.cjs.tmp.$$" "${dist}/nsls-block-telemetry.cjs"
marker='import "./nsls-block-telemetry.cjs"; // nsls-browser-check'
for entry in index.js browser-mcp.js browser-daemon.js; do
  f="${dist}/${entry}"
  [ -f "$f" ] || die "expected Expect entry point ${entry} is missing; refusing to run unpatched"
  if ! grep -qF "$marker" "$f"; then
    # Keep a shebang on line 1; the import goes right after it.
    tmp="${f}.tmp.$$"
    if head -1 "$f" | grep -q '^#!'; then
      { head -1 "$f"; echo "$marker"; tail -n +2 "$f"; } > "$tmp"
    else
      { echo "$marker"; cat "$f"; } > "$tmp"
    fi
    mv -f "$tmp" "$f"
  fi
  grep -qF "$marker" "$f" || die "could not wire the telemetry blocker into ${entry}; refusing to run"
done

# Switch off Expect's cookie import at the source. Its browser tool imports local
# browser cookies only inside `if(<opts>.cookies&&!<isCdp>){ ... addCookies(...) }`
# (one copy in index.js, one in the server chunk the MCP server loads). Appending
# `&&!1` makes that branch dead, whatever the run flags or the agent ask for.
# Every file that calls addCookies must carry the patch, or nothing runs.
cookie_sites=0
for f in "${dist}"/*.js; do
  grep -q 'addCookies(' "$f" || continue
  if grep -qE 'if\([A-Za-z0-9_$]+\.cookies&&![A-Za-z0-9_$]+\)\{' "$f"; then
    tmp="${f}.tmp.$$"
    perl -pe 's/if\(([A-Za-z0-9_\$]+)\.cookies&&!([A-Za-z0-9_\$]+)\)\{/if($1.cookies&&!$2&&!1){/g' "$f" > "$tmp"
    mv -f "$tmp" "$f"
  fi
  if grep -qE 'if\([A-Za-z0-9_$]+\.cookies&&![A-Za-z0-9_$]+\)\{' "$f" \
     || ! grep -qE 'if\([A-Za-z0-9_$]+\.cookies&&![A-Za-z0-9_$]+&&!1\)\{' "$f"; then
    die "could not switch off cookie import in $(basename "$f"); refusing to run"
  fi
  cookie_sites=$((cookie_sites + 1))
done
[ "$cookie_sites" -ge 1 ] || die "found no cookie-import code to switch off in ${dist}; Expect changed shape, refusing to run"
rmdir "$lock" 2>/dev/null || true
trap - EXIT

# Expect writes .expect/logs.md under its working directory. Run it from the repo
# root so the log it writes is the log audited below, wherever the caller started.
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
logfile="${repo_root}/.expect/logs.md"
before=0
[ -f "$logfile" ] && before=$(wc -l < "$logfile")

set +e
node "${dist}/index.js" tui \
  --ci --no-cookies --browser-mode headless \
  -a claude \
  -t "$target" \
  -u "$url" \
  -m "$message" \
  --output json < /dev/null
status=$?
set -e

# Expect logs every browser session it opens. is_external_browser:true means it
# attached to a real browser (and its logged-in sessions): that fails the run.
# cookie_count is taken AFTER the page loads, so it includes cookies the tested
# site set itself (CSRF, analytics); import is already switched off above, so it
# is reported, not failed on.
if [ -f "$logfile" ]; then
  new_sessions=$(tail -n +"$((before + 1))" "$logfile" | grep 'MCP browser session opened' || true)
  if [ -z "$new_sessions" ]; then
    echo "browser-check: WARNING - no browser session was logged, so the no-cookies check could not run." >&2
  # No `echo | grep -q` here: under pipefail, grep -q exiting early can SIGPIPE the
  # echo and turn a hit into a miss. Here-string, output discarded instead.
  elif grep -v -E 'is_external_browser\\?":false' <<< "$new_sessions" > /dev/null; then
    echo "browser-check: FAILED SAFETY CHECK - a browser session attached to a real browser:" >&2
    echo "$new_sessions" >&2
    exit 3
  else
    site_cookies=$(grep -oE 'cookie_count\\?":[0-9]+' <<< "$new_sessions" | grep -oE '[0-9]+$' | paste -sd, - || true)
    echo "browser-check: safety check passed - $(echo "$new_sessions" | wc -l | tr -d ' ') browser session(s), no real browser attached, cookie import switched off (cookies the site itself set: ${site_cookies:-none})." >&2
  fi
else
  echo "browser-check: FAILED SAFETY CHECK - Expect wrote no log at $logfile, so the no-cookies check could not run. Don't trust this run." >&2
  exit 3
fi
exit $status

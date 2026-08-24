#!/bin/bash
# await-macroscope.sh — wait for the Macroscope correctness check on a PR head, then report.
#
# WHY THIS EXISTS
#
# The skill used to tell you to poll with `gh pr checks "$PR" | grep -i Macroscope`, and to
# improvise a wait loop around it. Both parts bite:
#
#   1. `gh pr checks` renders a `neutral` conclusion as the word **"skipping"**. Macroscope
#      returns `neutral` WHENEVER IT HAS FINDINGS. So a review that found six real bugs prints
#      "skipping", which reads as "didn't run" or "passed". On 2026-08-24 that nearly got a
#      6-finding review reported as clean; the real title was "6 issues identified".
#
#   2. Every hand-rolled wait loop parsed the check-run payload with strict JSON in the shell.
#      The payload contains RAW CONTROL CHARACTERS (Macroscope embeds diffs and code), so
#      `json.load` raises `Invalid control character`. Paired with the reflexive
#      `|| echo '{}'`, the loop then reported "not ready" on every single poll while actually
#      failing to ask — silence that is indistinguishable from "still running". Three separate
#      monitors went quiet that way in one afternoon.
#
# So: all parsing happens in `--jq` (jq tolerates control characters), a failed query is LOUD
# and distinct from "not settled", and `neutral` is reported as findings rather than a pass.
#
# Usage:
#   await-macroscope.sh [--pr N] [--sha SHA] [--timeout SECONDS] [--interval SECONDS] [--quiet]
#
# Defaults: current branch's PR, its head SHA, 600s timeout, 20s interval.
#
# Exit codes:
#   0  settled, conclusion success, zero findings          — clean
#   1  settled, but findings exist (conclusion neutral)    — act on them
#   2  timed out before the check settled
#   3  the check concluded failure/cancelled/timed_out     — infrastructure, not review
#   4  usage or query error (never confused with "not ready")

set -uo pipefail

PR=""; SHA=""; TIMEOUT=600; INTERVAL=20; QUIET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --pr)       PR="$2"; shift 2 ;;
    --sha)      SHA="$2"; shift 2 ;;
    --timeout)  TIMEOUT="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    --quiet)    QUIET=1; shift ;;
    -h|--help)  sed -n '2,36p' "$0"; exit 0 ;;
    *) echo "await-macroscope: unknown argument $1" >&2; exit 4 ;;
  esac
done

say() { [ "$QUIET" = 1 ] || echo "$@"; }
die() { echo "await-macroscope: $*" >&2; exit 4; }

# Validate before the loop. A bad --interval makes `sleep` fail, and the loop then spins with
# no delay and hammers the API instead of returning a usage error.
case "$TIMEOUT" in ''|*[!0-9]*) die "--timeout must be a non-negative integer (got '$TIMEOUT')";; esac
case "$INTERVAL" in ''|*[!0-9.]*|.|*.*.*) die "--interval must be a non-negative number (got '$INTERVAL')";; esac
[ "$INTERVAL" = "0" ] && die "--interval 0 would spin without delay"

command -v gh >/dev/null 2>&1 || die "gh is not on PATH"

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)" \
  || die "could not resolve the repo (is this a gh-authenticated checkout?)"
[ -n "$REPO" ] || die "empty repo name from gh"

if [ -z "$PR" ]; then
  PR="$(gh pr view --json number -q .number 2>/dev/null)" \
    || die "no PR for the current branch; pass --pr N"
fi
[ -n "$PR" ] || die "could not resolve a PR number"

if [ -z "$SHA" ]; then
  SHA="$(gh pr view "$PR" --json headRefOid -q .headRefOid 2>/dev/null)" \
    || die "could not resolve the head SHA for PR #$PR"

  # The API's headRefOid LAGS a fresh push by seconds. Resolving it right after `git push`
  # returns the PREVIOUS commit, and the script then reports that commit's findings as
  # current — reviewing a stale head while looking authoritative. This is the head-anchored
  # trap the whole skill warns about, so the helper must not walk into it.
  #
  # If local HEAD differs and the remote already has it, the API was simply behind: use local
  # HEAD. If the remote does NOT have local HEAD, the real problem is unpushed work — say so
  # rather than silently reviewing the wrong commit.
  # ONLY substitute local HEAD when the checkout is actually on this PR's head branch.
  # Without that guard, `--pr N` run from any other branch substituted whatever local HEAD
  # happened to be — polling checks and counting comments for a commit belonging to a
  # different PR entirely, and reporting it as PR N's verdict. Introduced by the lag fix in
  # the previous commit; caught before it shipped.
  PR_BRANCH="$(gh pr view "$PR" --json headRefName -q .headRefName 2>/dev/null || true)"
  CUR_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [ -n "$PR_BRANCH" ] && [ "$PR_BRANCH" != "$CUR_BRANCH" ]; then
    say "  note: checked out '$CUR_BRANCH' but PR #$PR is '$PR_BRANCH' — using the PR's own"
    say "        head ${SHA:0:8}. Pass --sha to override."
  elif LOCAL="$(git rev-parse HEAD 2>/dev/null)" && [ -n "$LOCAL" ] && [ "$LOCAL" != "$SHA" ]; then
    if gh api "repos/$REPO/commits/$LOCAL" --jq .sha >/dev/null 2>&1; then
      say "  note: the PR API still reports ${SHA:0:8}; local HEAD ${LOCAL:0:8} is already on"
      say "        the remote, so the API is lagging the push. Using local HEAD."
      SHA="$LOCAL"
    else
      echo "await-macroscope: local HEAD ${LOCAL:0:8} is NOT on the remote — you have unpushed" >&2
      echo "  commits. The PR head is ${SHA:0:8}; push first, or pass --sha explicitly." >&2
      exit 4
    fi
  fi
fi
[ -n "$SHA" ] || die "empty head SHA"

say "PR #$PR @ ${SHA:0:8} in $REPO"

# One query, jq-parsed. Echoes "<status>|<conclusion>|<title>" or nothing on a query failure.
probe() {
  gh api "repos/$REPO/commits/$SHA/check-runs" \
    --jq '[.check_runs[] | select(.name | test("Macroscope"; "i"))]
          | if length == 0 then ""
            else (.[0] | "\(.status)|\(.conclusion // "")|\(.output.title // "")") end' 2>/dev/null
}

deadline=$(( $(date +%s) + TIMEOUT ))
last=""
fails=0          # CONSECUTIVE query failures
MAX_FAILS=3
answered=0       # have we ever got a real answer from the API?
while :; do
  if ! out="$(probe)"; then
    # A transient 5xx deserves a retry. A persistent failure is a QUERY ERROR (4) and must
    # never decay into "TIMED OUT" (2) — that would be the exact sin this script exists to
    # stop: a failed question presented as a negative answer. Bounded retries, then exit 4.
    fails=$(( fails + 1 ))
    say "  [query failed (${fails}/${MAX_FAILS}) — retrying; this is NOT 'not ready']"
    if [ "$fails" -ge "$MAX_FAILS" ]; then
      die "the check-runs query failed ${fails} times in a row (auth, permissions, or network).\
 This is a query error, NOT a timeout and NOT a pass."
    fi
    query_failed=1
  else
    fails=0
    answered=1
    query_failed=0
  fi

  # After a failed query we know NOTHING. Don't fall through and report "check not created
  # yet" — that is a failed question wearing the costume of an answer.
  if [ "${query_failed}" = 1 ]; then
    if [ "$(date +%s)" -ge "$deadline" ]; then
      die "the query was still failing at the deadline — query error, not a timeout."
    fi
    sleep "$INTERVAL"
    continue
  fi

  if [ -n "$out" ]; then
    status="${out%%|*}"; rest="${out#*|}"
    conclusion="${rest%%|*}"; title="${rest#*|}"
    if [ "$status" = "completed" ]; then
      break
    fi
    [ "$status" != "$last" ] && say "  status: $status"
    last="$status"
  else
    [ "$last" != "absent" ] && say "  status: check not created yet"
    last="absent"
  fi

  if [ "$(date +%s)" -ge "$deadline" ]; then
    if [ "$answered" = 0 ]; then
      die "never got a successful answer from the API in ${TIMEOUT}s — query error, not a timeout."
    fi
    echo "TIMED OUT after ${TIMEOUT}s — the check never settled (last status: ${last})." >&2
    echo "This is a timeout, not a pass. Re-run or check the PR in the browser." >&2
    exit 2
  fi
  sleep "$INTERVAL"
done

# --- settled: report ------------------------------------------------------------------

# Only MACROSCOPE's comments. Counting every comment on the SHA meant one human review
# note flipped a genuinely clean run to "findings present" and exit 1.
findings="$(gh api "repos/$REPO/pulls/$PR/comments" --paginate \
  --jq "[.[] | select(.commit_id==\"$SHA\") | select(.user.login==\"macroscopeapp[bot]\")] | length" \
  2>/dev/null | awk '{t+=$1} END{print (NR?t:"?")}')" || findings="?"
[ -n "$findings" ] || findings="?"

# PAGINATED. `reviewThreads(first:100)` alone silently undercounts on a long-running PR, so
# a review with unresolved threads past the first page could report a clean count.
unresolved="$(gh api graphql --paginate \
  -F owner="${REPO%%/*}" -F name="${REPO##*/}" -F pr="$PR" \
  -f query='query($owner:String!,$name:String!,$pr:Int!,$endCursor:String){
    repository(owner:$owner,name:$name){ pullRequest(number:$pr){
      reviewThreads(first:100, after:$endCursor){
        pageInfo{ hasNextPage endCursor }
        nodes{ isResolved } } } } }' \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved==false)] | length' \
  2>/dev/null | awk '{t+=$1} END{print (NR?t:"?")}')" || unresolved="?"
[ -n "$unresolved" ] || unresolved="?"

echo
echo "Macroscope: conclusion=${conclusion:-none}"
echo "  title:      ${title:-<none>}"
echo "  findings at this head: ${findings}"
echo "  unresolved threads:    ${unresolved}"

# The title's count is what THIS run found. The head-anchored count is only the comments
# GitHub still pins to this SHA — it re-anchors a comment to a later commit when the line it
# points at survives, so the two legitimately disagree and neither is wrong. Say so, because
# reading the smaller number as "most of them went away" is an easy and costly mistake.
title_n="$(printf '%s' "$title" | sed -n 's/^\([0-9][0-9]*\) issue.*/\1/p')"
if [ -n "$title_n" ] && [ "$findings" != "?" ] && [ "$title_n" != "$findings" ]; then
  echo "  note: this run found ${title_n}; ${findings} still anchor to this SHA. GitHub"
  echo "        re-anchors a comment to a later commit when its line survives — read all"
  echo "        ${title_n} via: gh api repos/$REPO/pulls/$PR/comments --paginate"
fi

case "$conclusion" in
  success)
    # Belt and braces: trust the finding count over the label — but an UNKNOWN count is not
    # a clean one. Treating "?" as zero manufactured a false all-clear whenever the comments
    # query failed, which is the precise failure mode this script exists to prevent.
    if [ "$findings" = "?" ]; then
      echo "  => could not determine the finding count — query error, NOT a clean result." >&2
      exit 4
    fi
    if [ "$findings" = "0" ]; then
      echo "  => CLEAN"
      exit 0
    fi
    echo "  => conclusion says success but ${findings} comments sit on this head — read them." >&2
    exit 1
    ;;
  neutral)
    # `gh pr checks` prints this as "skipping". It means FINDINGS.
    echo "  => FINDINGS PRESENT (conclusion 'neutral'; \`gh pr checks\` mislabels this as \"skipping\")"
    exit 1
    ;;
  failure|cancelled|timed_out|action_required|stale)
    echo "  => CHECK ${conclusion^^} — infrastructure problem, not a review verdict." >&2
    exit 3
    ;;
  *)
    echo "  => unrecognized conclusion '${conclusion}' — inspect the PR directly." >&2
    exit 3
    ;;
esac

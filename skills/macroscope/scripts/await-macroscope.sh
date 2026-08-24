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
while :; do
  if ! out="$(probe)"; then
    # A query error is NOT "not ready". Say so, and keep trying — transient 5xx is common —
    # but never let a failed question look like a negative answer.
    say "  [query failed — retrying; this is not 'not ready']"
    out=""
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
    echo "TIMED OUT after ${TIMEOUT}s — the check never settled (last status: ${last})." >&2
    echo "This is a timeout, not a pass. Re-run or check the PR in the browser." >&2
    exit 2
  fi
  sleep "$INTERVAL"
done

# --- settled: report ------------------------------------------------------------------

findings="$(gh api "repos/$REPO/pulls/$PR/comments" --paginate \
  --jq "[.[] | select(.commit_id==\"$SHA\")] | length" 2>/dev/null)" || findings="?"

unresolved="$(gh api graphql -f query="
{ repository(owner:\"${REPO%%/*}\", name:\"${REPO##*/}\") { pullRequest(number:$PR) {
    reviewThreads(first:100) { nodes { isResolved } } } } }" \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved==false)] | length' \
  2>/dev/null)" || unresolved="?"

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
    # Belt and braces: trust the finding count over the label.
    if [ "$findings" = "0" ] || [ "$findings" = "?" ]; then
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

#!/usr/bin/env python3.12
"""await_macroscope.py — wait for the Macroscope check on a PR head, then report honestly.

WHY THIS EXISTS

The skill used to say "poll with `gh pr checks | grep -i Macroscope`" and left the waiting to
whoever was driving. Both halves produce a wrong "all clear", and on 2026-08-24 both did,
repeatedly, across four PRs in one afternoon:

  1. `gh pr checks` renders a `neutral` conclusion as the word **"skipping"**, and Macroscope
     returns `neutral` WHENEVER IT HAS FINDINGS. A review that found six real bugs printed
     "skipping", which reads as "didn't run" or "passed". The real title was
     "6 issues identified (10 code objects reviewed)".

  2. The check-run payload contains RAW CONTROL CHARACTERS — Macroscope embeds diffs and code
     in `output`. Strict JSON parsing raises `Invalid control character`, and every hand-rolled
     loop paired that with `|| echo '{}'`, so it reported "not ready" on every poll while
     actually failing to ask. Silence indistinguishable from "still running".

A first pass at this lived in bash and drew thirteen review findings over four rounds. Ten were
real; the last four were all bash string-handling footguns — `--timeout 08` failing arithmetic
as octal, `0.0`/`.0`/`00` slipping a zero check, `set -u` exiting 1 instead of the documented 4
when a flag was missing its argument. None was about Macroscope. argparse and int() do not have
those failure modes, and the decision logic below is pure so pytest can pin it.

THE RULE THIS ENCODES: an unknown answer is never a clean one. Every path that cannot determine
the truth exits 4, not 0.

Usage:
    python3.12 await_macroscope.py [--pr N] [--sha SHA] [--timeout S] [--interval S] [--quiet]

Exit codes:
    0  settled, success, zero findings                  — clean
    1  settled with findings (conclusion `neutral`)     — act on them
    2  timed out before the check settled               — NOT a pass
    3  check concluded failure/cancelled/etc            — infrastructure, not a verdict
    4  usage error, query error, or unknown state       — never confused with "not ready"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

CLEAN, FINDINGS, TIMED_OUT, CHECK_ERROR, QUERY_ERROR = 0, 1, 2, 3, 4

BOT = "macroscopeapp[bot]"
MAX_CONSECUTIVE_FAILURES = 3


# ---------------------------------------------------------------------------------------
# pure logic — no I/O, so tests can pin every branch
# ---------------------------------------------------------------------------------------


def parse_json(text):
    """Parse a gh payload. `strict=False` is load-bearing, not defensive.

    Macroscope embeds diffs and code in `output`, so the check-run JSON carries raw control
    characters and strict parsing raises `Invalid control character`. That exception, swallowed
    by a fallback, is what made three separate watchers report "not ready" forever.
    """
    return json.loads(text, strict=False)


def find_macroscope_run(payload):
    """Return the Macroscope check run, or None when it does not exist yet.

    None means "not created yet" — a real, distinct state from "the query failed".
    """
    for run in payload.get("check_runs", []) or []:
        if "macroscope" in (run.get("name") or "").lower():
            return run
    return None


def classify(conclusion, findings):
    """Map a settled conclusion + finding count onto (exit_code, verdict, detail).

    `findings` is an int, or None when it could not be determined.
    """
    if conclusion == "success":
        # An UNKNOWN count is not a clean one. The bash version tested `= "?"` alongside
        # `= "0"` and printed "=> CLEAN", manufacturing a false all-clear whenever the
        # comments query failed — the precise failure this script exists to prevent.
        if findings is None:
            return (
                QUERY_ERROR,
                "UNKNOWN",
                "could not determine the finding count — query error, NOT a clean result",
            )
        if findings == 0:
            return CLEAN, "CLEAN", "no findings"
        return (
            FINDINGS,
            "FINDINGS PRESENT",
            f"conclusion says success but {findings} Macroscope comments sit on this head",
        )

    if conclusion == "neutral":
        return (
            FINDINGS,
            "FINDINGS PRESENT",
            "conclusion 'neutral' — `gh pr checks` mislabels this as \"skipping\"",
        )

    if conclusion in {"failure", "cancelled", "timed_out", "action_required", "stale"}:
        return (
            CHECK_ERROR,
            f"CHECK {conclusion.upper()}",
            "infrastructure problem, not a review verdict",
        )

    return (
        CHECK_ERROR,
        f"UNRECOGNIZED '{conclusion}'",
        "inspect the PR directly",
    )


def resolve_head(api_sha, local_sha, pr_branch, current_branch, remote_has_local):
    """Decide which SHA to inspect. Returns (sha, note) or raises ValueError.

    Two traps, both hit for real:

    * The PR API's `headRefOid` LAGS a fresh push by seconds, so resolving it right after
      `git push` returns the PREVIOUS commit and the tool then reviews a stale head while
      looking authoritative.
    * Substituting local HEAD unconditionally is worse: run with `--pr N` from another
      branch, it polls and counts for a commit belonging to a different PR and reports that
      as PR N's verdict.

    So: substitute only when the checkout is on this PR's own branch AND the remote already
    has the local commit.
    """
    if not api_sha:
        raise ValueError("could not resolve the PR's head SHA")
    if not local_sha or local_sha == api_sha:
        return api_sha, None
    if pr_branch and current_branch and pr_branch != current_branch:
        return api_sha, (
            f"checked out '{current_branch}' but PR head branch is '{pr_branch}' — "
            f"using the PR's own head {api_sha[:8]}. Pass --sha to override."
        )
    if not remote_has_local:
        raise ValueError(
            f"local HEAD {local_sha[:8]} is not on the remote — you have unpushed commits. "
            f"The PR head is {api_sha[:8]}; push first, or pass --sha explicitly."
        )
    return local_sha, (
        f"the PR API still reports {api_sha[:8]}; local HEAD {local_sha[:8]} is already on "
        "the remote, so the API is lagging the push. Using local HEAD."
    )


def title_finding_count(title):
    """The count Macroscope states in its own title, or None."""
    if not title:
        return None
    head = title.strip().split(" ", 1)[0]
    return int(head) if head.isdigit() else None


def discrepancy_note(title, findings, repo, pr):
    """Explain the two counts when they differ, because they legitimately do.

    GitHub re-anchors a comment to a later commit when the line it points at survives, so a
    6-finding run can show 3 comments on that SHA. Reading the smaller number as "most of
    them went away" is an easy and costly mistake.
    """
    stated = title_finding_count(title)
    if stated is None or findings is None or stated == findings:
        return None
    return (
        f"this run found {stated}; {findings} still anchor to this SHA. GitHub re-anchors a "
        f"comment to a later commit when its line survives — read all {stated} via: "
        f"gh api repos/{repo}/pulls/{pr}/comments --paginate"
    )


def positive_number(raw, name, allow_float=False):
    """argparse type: a strictly positive number, base 10, no octal surprises."""
    try:
        value = float(raw) if allow_float else int(raw, 10)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{name} must be a number, got {raw!r}")
    if value <= 0:
        raise argparse.ArgumentTypeError(f"{name} must be greater than zero, got {raw!r}")
    return value


# ---------------------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------------------


class GhError(Exception):
    """A `gh` invocation failed. Distinct from any answer `gh` might give."""


def gh(*args, check=True):
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise GhError((proc.stderr or proc.stdout or "gh failed").strip())
    return proc.stdout.strip()


def git(*args):
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def count_bot_comments(repo, pr, sha):
    """Macroscope comments anchored to this SHA, or None if undeterminable.

    Counts only the bot: counting every comment meant one human note flipped a clean run to
    "findings present". Aggregates across pages: `--paginate` with a `length` jq emits one
    count PER PAGE, so a two-page PR yielded "0\\n0" and a clean head read as non-zero.
    """
    try:
        raw = gh(
            "api",
            f"repos/{repo}/pulls/{pr}/comments",
            "--paginate",
            "--jq",
            f'[.[] | select(.commit_id=="{sha}") | select(.user.login=="{BOT}")] | length',
        )
    except GhError:
        return None
    total = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line.isdigit():
            return None
        total += int(line)
    return total if raw.strip() else None


def count_unresolved_threads(repo, pr):
    """Unresolved review threads, paginated. None if undeterminable."""
    owner, _, name = repo.partition("/")
    query = """query($owner:String!,$name:String!,$pr:Int!,$endCursor:String){
      repository(owner:$owner,name:$name){ pullRequest(number:$pr){
        reviewThreads(first:100, after:$endCursor){
          pageInfo{ hasNextPage endCursor }
          nodes{ isResolved } } } } }"""
    try:
        raw = gh(
            "api", "graphql", "--paginate",
            "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"pr={pr}",
            "-f", f"query={query}",
            "--jq",
            "[.data.repository.pullRequest.reviewThreads.nodes[] "
            "| select(.isResolved==false)] | length",
        )
    except GhError:
        return None
    total = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line.isdigit():
            return None
        total += int(line)
    return total if raw.strip() else None


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Wait for the Macroscope check on a PR head and report honestly.",
        epilog="Exit: 0 clean, 1 findings, 2 timeout, 3 check errored, 4 usage/query error.",
    )
    p.add_argument("--pr", type=lambda v: positive_number(v, "--pr"))
    p.add_argument("--sha")
    p.add_argument("--timeout", type=lambda v: positive_number(v, "--timeout"), default=600)
    p.add_argument(
        "--interval",
        type=lambda v: positive_number(v, "--interval", allow_float=True),
        default=20,
    )
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    def say(*a):
        if not args.quiet:
            print(*a)

    try:
        repo = gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")
        pr = args.pr or int(gh("pr", "view", "--json", "number", "-q", ".number"))
        if args.sha:
            sha, note = args.sha, None
        else:
            api_sha = gh("pr", "view", str(pr), "--json", "headRefOid", "-q", ".headRefOid")
            pr_branch = gh("pr", "view", str(pr), "--json", "headRefName",
                           "-q", ".headRefName", check=False)
            local = git("rev-parse", "HEAD")
            current = git("rev-parse", "--abbrev-ref", "HEAD")
            remote_has_local = bool(local) and subprocess.run(
                ["gh", "api", f"repos/{repo}/commits/{local}", "--jq", ".sha"],
                capture_output=True, text=True,
            ).returncode == 0
            sha, note = resolve_head(api_sha, local, pr_branch, current, remote_has_local)
    except (GhError, ValueError) as exc:
        print(f"await-macroscope: {exc}", file=sys.stderr)
        return QUERY_ERROR

    if note:
        say(f"  note: {note}")
    say(f"PR #{pr} @ {sha[:8]} in {repo}")

    deadline = time.monotonic() + args.timeout
    failures = 0
    answered = False
    last = None
    run = None

    while True:
        try:
            payload = parse_json(gh("api", f"repos/{repo}/commits/{sha}/check-runs"))
            failures = 0
            answered = True
        except (GhError, json.JSONDecodeError) as exc:
            # A failed question is not a negative answer. Bounded retries for transient 5xx,
            # then exit 4 — never let this decay into a timeout or a pass.
            failures += 1
            say(f"  [query failed ({failures}/{MAX_CONSECUTIVE_FAILURES}) — "
                f"retrying; this is NOT 'not ready']")
            if failures >= MAX_CONSECUTIVE_FAILURES:
                print(
                    f"await-macroscope: the check-runs query failed {failures} times in a row "
                    f"({exc}). Query error, NOT a timeout and NOT a pass.",
                    file=sys.stderr,
                )
                return QUERY_ERROR
            if time.monotonic() >= deadline:
                print("await-macroscope: the query was still failing at the deadline — "
                      "query error, not a timeout.", file=sys.stderr)
                return QUERY_ERROR
            time.sleep(args.interval)
            continue

        run = find_macroscope_run(payload)
        status = (run or {}).get("status") or "absent"
        if run and status == "completed":
            break
        if status != last:
            say(f"  status: {'check not created yet' if status == 'absent' else status}")
        last = status

        if time.monotonic() >= deadline:
            if not answered:
                print("await-macroscope: never got a successful answer from the API — "
                      "query error, not a timeout.", file=sys.stderr)
                return QUERY_ERROR
            print(f"await-macroscope: TIMED OUT after {args.timeout}s — the check never "
                  f"settled (last status: {last}). This is a timeout, NOT a pass.",
                  file=sys.stderr)
            return TIMED_OUT
        time.sleep(args.interval)

    conclusion = run.get("conclusion") or ""
    title = ((run.get("output") or {}).get("title") or "").strip()
    findings = count_bot_comments(repo, pr, sha)
    unresolved = count_unresolved_threads(repo, pr)

    code, verdict, detail = classify(conclusion, findings)

    print()
    print(f"Macroscope: conclusion={conclusion or 'none'}")
    print(f"  title:                 {title or '<none>'}")
    print(f"  findings at this head: {'?' if findings is None else findings}")
    print(f"  unresolved threads:    {'?' if unresolved is None else unresolved}")
    note = discrepancy_note(title, findings, repo, pr)
    if note:
        print(f"  note: {note}")
    stream = sys.stdout if code in (CLEAN, FINDINGS) else sys.stderr
    print(f"  => {verdict} ({detail})", file=stream)
    return code


if __name__ == "__main__":
    sys.exit(main())

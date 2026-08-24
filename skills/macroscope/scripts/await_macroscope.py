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
import math
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


def classify(conclusion, findings, unresolved):
    """Map a settled conclusion + counts onto (exit_code, verdict, detail).

    `findings` and `unresolved` are ints, or None when undeterminable.

    On `success`, the actionable signal is UNRESOLVED THREADS — not the raw comment count.
    GitHub re-anchors an already-resolved comment to the new head whenever the line it points
    at survives, so a long-lived PR accumulates resolved comments on every subsequent SHA. An
    earlier version cross-checked the raw count against the conclusion as "belt and braces",
    and dogfooding immediately showed the cost: a run that genuinely reported "No issues
    identified" exited 1 because one resolved, re-anchored comment sat on the head. A tool
    that cries wolf on every clean run stops being read.

    Unresolved threads are still worth failing on, because they mean outstanding work from an
    earlier round even when this run found nothing new.
    """
    if conclusion == "success":
        # An UNKNOWN count is not a clean one. The bash version tested `= "?"` alongside
        # `= "0"` and printed "=> CLEAN", manufacturing a false all-clear whenever the
        # query failed — the precise failure this script exists to prevent.
        if unresolved is None:
            return (
                QUERY_ERROR,
                "UNKNOWN",
                "could not determine the unresolved-thread count — query error, NOT clean",
            )
        if unresolved == 0:
            detail = "no issues, no unresolved threads"
            if findings:
                detail += (
                    f" ({findings} resolved comment(s) re-anchored to this SHA — not findings)"
                )
            return CLEAN, "CLEAN", detail
        return (
            FINDINGS,
            "UNRESOLVED THREADS",
            f"this run found nothing new, but {unresolved} thread(s) are still unresolved",
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


def resolve_head(api_sha, local_sha, pr_branch, current_branch, remote_branch_tip):
    """Decide which SHA to inspect. Returns (sha, note) or raises ValueError.

    Three traps, all hit for real:

    * The PR API's `headRefOid` LAGS a fresh push by seconds, so resolving it right after
      `git push` returns the PREVIOUS commit and the tool reviews a stale head while looking
      authoritative. This is the only reason to prefer local HEAD at all.
    * Substituting local HEAD unconditionally is worse: run with `--pr N` from another branch,
      it polls and counts for a commit belonging to a different PR and reports that as PR N's
      verdict.
    * Asking merely "does the remote HAVE this commit?" is not enough, because that is true of
      any OLD commit. A stale checkout would then substitute an older SHA and confidently
      report a verdict for it. The authoritative question is whether local HEAD IS the remote
      branch's current tip — so that is what we compare against.
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
    if remote_branch_tip and local_sha == remote_branch_tip:
        # Local HEAD is the tip on the remote; the PR API is simply behind.
        return local_sha, (
            f"the PR API still reports {api_sha[:8]}; local HEAD {local_sha[:8]} is the current"
            " tip on the remote, so the API is lagging the push. Using local HEAD."
        )
    if remote_branch_tip:
        raise ValueError(
            f"local HEAD {local_sha[:8]} is not the remote tip ({remote_branch_tip[:8]}) — "
            f"your checkout is stale or has unpushed commits. The PR head is {api_sha[:8]}; "
            "pull/push, or pass --sha explicitly."
        )
    branch_label = pr_branch or "the PR branch"
    raise ValueError(
        f"could not determine the remote tip for '{branch_label}'; local HEAD is "
        f"{local_sha[:8]} and the PR head is {api_sha[:8]}. Pass --sha."
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
    # NaN and inf survive float(): `nan <= 0` is False, so NaN passed the positivity check
    # and reached time.sleep(nan), which raises; inf would sleep forever. Reject both here so
    # they surface as the documented usage error instead of a traceback or a hang.
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError(f"{name} must be finite, got {raw!r}")
    if value <= 0:
        raise argparse.ArgumentTypeError(f"{name} must be greater than zero, got {raw!r}")
    return value


# ---------------------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------------------


class GhError(Exception):
    """A `gh` invocation failed. Distinct from any answer `gh` might give."""


def gh(*args, check=True):
    """Run gh. A missing or unexecutable binary is a GhError, not a traceback.

    subprocess.run raises FileNotFoundError (an OSError) when `gh` is not on PATH, and the
    caller's handler caught only GhError/ValueError — so a machine without gh got a traceback
    instead of the documented exit 4. An unusable tool has to report itself the same way a
    failed query does.
    """
    try:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    except OSError as exc:
        raise GhError(f"could not execute gh: {exc}") from exc
    if check and proc.returncode != 0:
        raise GhError((proc.stderr or proc.stdout or "gh failed").strip())
    return proc.stdout.strip()


def git(*args):
    """Run git. Any failure — including a missing binary — is an empty answer.

    Unlike gh, git is optional here: without a checkout we fall back to the PR API's head,
    which resolve_head handles explicitly.
    """
    try:
        proc = subprocess.run(["git", *args], capture_output=True, text=True)
    except OSError:
        return ""
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

    # argparse exits 2 on a usage error, but 2 is THIS tool's documented TIMED_OUT. A usage
    # error must never wear the timeout's code — that is the same confusion between "I could
    # not answer" and "here is an answer" that the whole script exists to prevent, appearing
    # in its own exit codes. --help still exits 0.
    try:
        args = p.parse_args(argv)
    except SystemExit as exc:
        if exc.code in (0, None):
            return CLEAN
        return QUERY_ERROR

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
            # A detached checkout (CI, `git checkout <sha>`) reports the literal "HEAD",
            # which compares unequal to every real branch name and so looked like a branch
            # MISMATCH — sending it down the "use the PR's own head" path and reporting the
            # stale API SHA right after a push. Unknown is not a mismatch: normalise it away
            # and let the remote-tip comparison decide, which is authoritative anyway.
            if current == "HEAD":
                current = ""
            # The remote branch's CURRENT TIP — not "does this commit exist somewhere".
            remote_tip = ""
            if local and pr_branch:
                remote_tip = gh(
                    "api", f"repos/{repo}/git/ref/heads/{pr_branch}",
                    "--jq", ".object.sha", check=False,
                )
            sha, note = resolve_head(api_sha, local, pr_branch, current, remote_tip)
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
        # Check the deadline BEFORE asking. Otherwise `--timeout 1 --interval 20` slept ~20s
        # and then accepted a completed check, reporting a verdict for a run the caller had
        # already declared itself unwilling to wait for.
        if time.monotonic() >= deadline:
            if not answered:
                print("await-macroscope: never got a successful answer from the API — "
                      "query error, not a timeout.", file=sys.stderr)
                return QUERY_ERROR
            print(f"await-macroscope: TIMED OUT after {args.timeout}s — the check never "
                  f"settled (last status: {last}). This is a timeout, NOT a pass.",
                  file=sys.stderr)
            return TIMED_OUT
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
            time.sleep(max(0.0, min(args.interval, deadline - time.monotonic())))
            continue

        run = find_macroscope_run(payload)
        status = (run or {}).get("status") or "absent"
        if run and status == "completed":
            break
        if status != last:
            say(f"  status: {'check not created yet' if status == 'absent' else status}")
        last = status

        time.sleep(max(0.0, min(args.interval, deadline - time.monotonic())))

    conclusion = run.get("conclusion") or ""
    title = ((run.get("output") or {}).get("title") or "").strip()
    findings = count_bot_comments(repo, pr, sha)
    unresolved = count_unresolved_threads(repo, pr)

    code, verdict, detail = classify(conclusion, findings, unresolved)

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

"""Every case here is a wrong "all clear" that actually happened, or nearly did.

The bash predecessor of this script drew thirteen review findings over four rounds. Ten were
real. Three of them were the script committing the exact sin it exists to prevent — most
sharply, setting `findings="?"` on a query failure and then testing `= "?"` alongside `= "0"`
and printing "=> CLEAN".

The logic is pure so these run with no network and no gh.

Run: python3.12 -m pytest skills/macroscope/tests/test_await_macroscope.py -q
"""

import argparse
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import await_macroscope as am  # noqa: E402


# ---------------------------------------------------------------------------------------
# control characters — trap 2
# ---------------------------------------------------------------------------------------


def test_payload_with_raw_control_characters_parses():
    """Macroscope embeds diffs in `output`, so the payload carries raw control chars.

    Strict json.loads raises `Invalid control character`. Swallowed by a fallback, that made
    three watchers report "not ready" on every poll while failing to ask.
    """
    raw = '{"check_runs":[{"name":"Macroscope","output":{"title":"a\x07b\x01c"}}]}'
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)  # confirms the hazard is real, not hypothetical
    parsed = am.parse_json(raw)
    assert parsed["check_runs"][0]["output"]["title"] == "a\x07b\x01c"


def test_find_macroscope_run_matches_case_insensitively_and_ignores_others():
    payload = {"check_runs": [{"name": "lint"}, {"name": "MACROSCOPE - Correctness Check"}]}
    assert am.find_macroscope_run(payload)["name"].startswith("MACROSCOPE")
    assert am.find_macroscope_run({"check_runs": [{"name": "lint"}]}) is None
    assert am.find_macroscope_run({}) is None, "absent is a real state, not an error"


# ---------------------------------------------------------------------------------------
# classify — trap 1, and "unknown is not clean"
# ---------------------------------------------------------------------------------------


def test_neutral_means_findings_not_skipping():
    """`gh pr checks` prints neutral as "skipping". Macroscope returns neutral WITH findings.

    A six-finding review printed "skipping" and nearly got reported as clean.
    """
    code, verdict, detail = am.classify("neutral", 6, 6)
    assert code == am.FINDINGS
    assert verdict == "FINDINGS PRESENT"
    assert "skipping" in detail, "the mislabelling must be named in the output"


def test_unknown_count_is_never_clean():
    """The High finding against the bash version: `?` was treated as zero."""
    code, verdict, _ = am.classify("success", 0, None)
    assert code == am.QUERY_ERROR
    assert verdict == "UNKNOWN"


def test_success_with_nothing_unresolved_is_clean():
    assert am.classify("success", 0, 0)[0] == am.CLEAN


def test_resolved_comments_re_anchored_to_the_head_do_not_cry_wolf():
    """Found by dogfooding: the tool failed its own clean run.

    GitHub re-anchors an ALREADY-RESOLVED comment to the new head when the line it points at
    survives, so a long-lived PR accumulates resolved comments on every later SHA. Keying the
    verdict on the raw count turned "No issues identified" into exit 1. A tool that cries wolf
    on every clean run stops being read.
    """
    code, verdict, detail = am.classify("success", 1, 0)
    assert code == am.CLEAN
    assert verdict == "CLEAN"
    assert "re-anchored" in detail, "say why the nonzero count is not a finding"


def test_success_with_unresolved_threads_still_fails():
    """Nothing new this run, but earlier findings are still outstanding."""
    code, verdict, detail = am.classify("success", 5, 2)
    assert code == am.FINDINGS
    assert verdict == "UNRESOLVED THREADS"
    assert "2" in detail


def test_neutral_fails_regardless_of_thread_state():
    """The run itself found things; resolution state cannot excuse that."""
    assert am.classify("neutral", 0, 0)[0] == am.FINDINGS


@pytest.mark.parametrize("c", ["failure", "cancelled", "timed_out", "action_required", "stale"])
def test_infrastructure_conclusions_are_not_review_verdicts(c):
    code, _, detail = am.classify(c, 0, 0)
    assert code == am.CHECK_ERROR
    assert "not a review verdict" in detail


def test_unrecognized_conclusion_does_not_fall_through_to_clean():
    assert am.classify("something-new", 0, 0)[0] == am.CHECK_ERROR
    assert am.classify("", 0, 0)[0] == am.CHECK_ERROR


# ---------------------------------------------------------------------------------------
# resolve_head — API lag, and the dangerous substitution
# ---------------------------------------------------------------------------------------


def test_api_lag_after_a_push_uses_local_head():
    """headRefOid lags a fresh push by seconds; using it reviews the previous commit."""
    sha, note = am.resolve_head("old111", "new222", "my-branch", "my-branch", "new222")
    assert sha == "new222"
    assert "lagging" in note


def test_local_head_is_not_substituted_from_a_different_branch():
    """The dangerous one. `--pr N` from another branch reported a foreign commit as PR N."""
    sha, note = am.resolve_head("prhead1", "otherbranchhead", "pr-branch", "main", "prhead1")
    assert sha == "prhead1"
    assert "pr-branch" in note and "main" in note


def test_a_stale_checkout_is_an_error_not_a_verdict_on_an_old_commit():
    """Macroscope on the Python version: "does the remote HAVE it" is true of any OLD commit.

    A stale checkout would then substitute an older SHA and confidently report a verdict for
    it. The authoritative question is whether local HEAD IS the remote branch tip.
    """
    with pytest.raises(ValueError) as e:
        am.resolve_head("newtip9", "oldlocal1", "my-branch", "my-branch", "newtip9")
    msg = str(e.value)
    assert "not the remote tip" in msg
    assert "stale" in msg


def test_unpushed_local_head_is_an_error_not_a_silent_wrong_commit():
    with pytest.raises(ValueError) as e:
        am.resolve_head("prhead1", "localonly", "my-branch", "my-branch", "prhead1")
    assert "not the remote tip" in str(e.value)


def test_unknown_remote_tip_refuses_rather_than_guessing():
    with pytest.raises(ValueError) as e:
        am.resolve_head("prhead1", "somethingelse", "my-branch", "my-branch", "")
    assert "could not determine the remote tip" in str(e.value)


def test_matching_shas_need_no_substitution():
    assert am.resolve_head("same", "same", "b", "b", "same") == ("same", None)


def test_missing_api_sha_raises():
    with pytest.raises(ValueError):
        am.resolve_head("", "local", "b", "b", "tip")


def test_no_local_git_context_falls_back_to_the_api_head():
    """Running outside a checkout must still work."""
    assert am.resolve_head("prhead", "", None, None, "") == ("prhead", None)


# ---------------------------------------------------------------------------------------
# the two finding counts legitimately differ
# ---------------------------------------------------------------------------------------


def test_discrepancy_note_explains_the_gap():
    note = am.discrepancy_note("6 issues identified (10 code objects reviewed).", 3, "o/r", 56)
    assert "found 6" in note and "3 still anchor" in note
    assert "re-anchors" in note


def test_no_note_when_the_counts_agree_or_are_unknown():
    assert am.discrepancy_note("3 issues identified.", 3, "o/r", 1) is None
    assert am.discrepancy_note("3 issues identified.", None, "o/r", 1) is None
    assert am.discrepancy_note("No issues identified.", 0, "o/r", 1) is None


def test_title_finding_count():
    assert am.title_finding_count("6 issues identified (10 code objects reviewed).") == 6
    assert am.title_finding_count("1 issue identified (1 code object reviewed).") == 1
    assert am.title_finding_count("No issues identified.") is None
    assert am.title_finding_count("") is None
    assert am.title_finding_count(None) is None


# ---------------------------------------------------------------------------------------
# argument validation — the whole class of bug that motivated leaving bash
# ---------------------------------------------------------------------------------------


def test_leading_zero_is_base_ten_not_octal():
    """`--timeout 08` broke bash arithmetic with "value too great for base"."""
    assert am.positive_number("08", "--timeout") == 8
    assert am.positive_number("010", "--timeout") == 10


@pytest.mark.parametrize("bad", ["0", "0.0", ".0", "00", "-5", "-0.1"])
def test_every_representation_of_zero_or_negative_is_rejected(bad):
    """`0.0`, `.0` and `00` all slipped the bash zero check and spun the poll loop."""
    with pytest.raises(argparse.ArgumentTypeError):
        am.positive_number(bad, "--interval", allow_float=True)


@pytest.mark.parametrize("bad", ["abc", "", "1e", "1.2.3", "5s"])
def test_non_numeric_is_rejected(bad):
    with pytest.raises(argparse.ArgumentTypeError):
        am.positive_number(bad, "--timeout")


def test_fractional_interval_is_allowed_but_not_for_ints():
    assert am.positive_number("2.5", "--interval", allow_float=True) == 2.5
    with pytest.raises(argparse.ArgumentTypeError):
        am.positive_number("2.5", "--timeout")


def test_a_usage_error_returns_4_not_the_timeout_code():
    """argparse exits 2, but 2 is THIS tool's documented TIMED_OUT.

    A usage error wearing the timeout's code is the same confusion between "I could not
    answer" and "here is an answer" that the script exists to prevent, surfacing in its own
    exit codes. In bash this died with `unbound variable` and exit 1.
    """
    assert am.main(["--pr"]) == am.QUERY_ERROR


@pytest.mark.parametrize("bad", [["--interval", "0"], ["--timeout", "abc"],
                                 ["--interval", "nan"], ["--nonsense"]])
def test_bad_arguments_return_4_without_polling(bad):
    assert am.main(bad) == am.QUERY_ERROR


def test_help_still_exits_zero():
    assert am.main(["--help"]) == am.CLEAN


def test_detached_head_is_not_a_branch_mismatch():
    """A detached checkout reports the literal "HEAD", which compared unequal to every real
    branch name and so looked like a MISMATCH — reporting the stale API SHA after a push.
    Unknown is not a mismatch; the remote-tip comparison is authoritative."""
    sha, note = am.resolve_head("stale111", "newtip22", "my-branch", "", "newtip22")
    assert sha == "newtip22", "a detached checkout on the real tip must still be used"
    assert "lagging" in note


@pytest.mark.parametrize("bad", ["nan", "NaN", "inf", "-inf", "Infinity"])
def test_non_finite_intervals_are_rejected(bad):
    """Macroscope on the Python version: `nan <= 0` is False, so NaN passed the positivity
    check and reached time.sleep(nan), which raises; inf would sleep forever."""
    with pytest.raises(argparse.ArgumentTypeError) as e:
        am.positive_number(bad, "--interval", allow_float=True)
    assert "finite" in str(e.value) or "number" in str(e.value)


# ---------------------------------------------------------------------------------------
# the tools themselves may be missing
# ---------------------------------------------------------------------------------------


def test_missing_gh_is_a_query_error_not_a_traceback(monkeypatch):
    """subprocess.run raises FileNotFoundError when gh is absent, and the caller caught only
    GhError/ValueError — so a machine without gh got a traceback instead of exit 4."""
    def boom(*a, **k):
        raise FileNotFoundError(2, "No such file or directory: 'gh'")
    monkeypatch.setattr(am.subprocess, "run", boom)
    with pytest.raises(am.GhError) as e:
        am.gh("repo", "view")
    assert "could not execute gh" in str(e.value)
    assert am.main(["--pr", "1"]) == am.QUERY_ERROR


def test_missing_git_is_an_empty_answer_not_a_crash(monkeypatch):
    """git is optional: without a checkout we fall back to the PR API head."""
    def boom(*a, **k):
        raise FileNotFoundError(2, "No such file or directory: 'git'")
    monkeypatch.setattr(am.subprocess, "run", boom)
    assert am.git("rev-parse", "HEAD") == ""

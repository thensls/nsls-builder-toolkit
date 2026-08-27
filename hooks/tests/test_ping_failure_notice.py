#!/usr/bin/env python3
"""Rules for when a failed session-ping is worth telling the builder about.

Plain stdlib, no pytest: these run on a stock install, same bar as the hook
they cover. Run with `python3 hooks/tests/test_ping_failure_notice.py`.

The false alarm these exist to prevent (2026-08-20): three sessions opened
inside six seconds each timed out against a tracker that was up and recording,
and the hook told the builder the tracker had been unreachable "for your last
3 sessions" and to raise it in #builders.
"""

import importlib.util
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "session-start.py"

spec = importlib.util.spec_from_file_location("session_start_hook", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

PAYLOAD = {"builder_email": "builder@nsls.org", "toolkit": "both"}


def run(marker, *, unreachable, online, seed=None, raw=None):
    """Call note_ping_failure with the probes stubbed. Returns (stdout, marker)."""
    hook.PING_FAIL_MARKER = marker
    hook._tracker_unreachable = lambda: unreachable
    hook._internet_up = lambda: online
    if raw is not None:
        marker.write_text(raw, encoding="utf-8")
    elif seed is not None:
        marker.write_text(json.dumps(seed), encoding="utf-8")
    buf = io.StringIO()
    with redirect_stdout(buf):
        hook.note_ping_failure(PAYLOAD)
    state = json.loads(marker.read_text(encoding="utf-8"))
    return buf.getvalue(), state


def days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).date().isoformat()


def test_single_failure_stays_quiet(tmp):
    out, state = run(tmp / "m1", unreachable=True, online=True)
    assert out == "", f"one failure should say nothing, got: {out!r}"
    assert state["attempts"] == 1
    assert state["payload"] == PAYLOAD, "payload must survive for the replay"


def test_second_failure_reports_a_real_outage(tmp):
    marker = tmp / "m2"
    run(marker, unreachable=True, online=True)
    out, state = run(marker, unreachable=True, online=True)
    assert "can't be reached" in out, f"expected the outage notice, got: {out!r}"
    assert state["last_notified_at"], "notifying must be recorded"


def test_it_does_not_repeat_inside_24h(tmp):
    marker = tmp / "m3"
    run(marker, unreachable=True, online=True)
    run(marker, unreachable=True, online=True)  # speaks
    out, _ = run(marker, unreachable=True, online=True)
    assert out == "", f"should stay quiet for 24h after speaking, got: {out!r}"


def test_it_speaks_again_after_24h(tmp):
    stale = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    out, _ = run(
        tmp / "m4", unreachable=True, online=True,
        seed={"payload": PAYLOAD, "attempts": 9, "failed_days": [days_ago(1)],
              "last_notified_at": stale},
    )
    assert "can't be reached" in out, "an outage must not go silent forever"


def test_offline_laptop_stays_quiet(tmp):
    marker = tmp / "m5"
    run(marker, unreachable=True, online=False)
    out, _ = run(marker, unreachable=True, online=False)
    assert out == "", f"no network is the builder's problem, not ours: {out!r}"


def test_slow_writes_stay_quiet_for_two_days(tmp):
    out, state = run(
        tmp / "m6", unreachable=False, online=True,
        seed={"payload": PAYLOAD, "attempts": 20, "failed_days": [days_ago(1)]},
    )
    assert out == "", f"a reachable-but-slow tracker loses nothing yet: {out!r}"
    assert len(state["failed_days"]) == 2


def test_slow_writes_report_on_the_third_day(tmp):
    out, _ = run(
        tmp / "m7", unreachable=False, online=True,
        seed={"payload": PAYLOAD, "attempts": 30,
              "failed_days": [days_ago(2), days_ago(1)]},
    )
    assert "too slow" in out, f"three separate days is real loss: {out!r}"
    assert "3 separate days" in out, f"count should be honest: {out!r}"


def test_same_day_bursts_count_once(tmp):
    """The 2026-08-20 false alarm: three failures in six seconds."""
    marker = tmp / "m8"
    for _ in range(3):
        _, state = run(marker, unreachable=False, online=True)
    assert state["failed_days"] == [datetime.now(timezone.utc).date().isoformat()]
    assert state["attempts"] == 3, "attempts still counted, just not as days"


# --- Codex review 2026-08-20: state read back from the marker is hostile ---

MALFORMED = [
    ("not our shape at all", "[]"),
    ("truncated write", '{"payload": {"a": 1}, "attempts":'),
    ("attempts is a word", '{"attempts": "x"}'),
    ("failed_days is a number", '{"failed_days": 3}'),
    ("timestamp is a number", '{"last_notified_at": 0}'),
    ("everything wrong at once",
     '{"attempts": [], "failed_days": {"a": 1}, "last_notified_at": []}'),
]


def test_malformed_marker_never_throws(tmp):
    """SessionStart must fail silently — this runs with nothing above it to catch."""
    for i, (label, blob) in enumerate(MALFORMED):
        marker = tmp / f"bad{i}"
        try:
            _, state = run(marker, unreachable=False, online=True, raw=blob)
        except Exception as exc:
            raise AssertionError(f"{label!r} raised {type(exc).__name__}: {exc}")
        assert state["attempts"] >= 1, f"{label}: counter must recover"
        assert state["failed_days"], f"{label}: today must still be recorded"


def test_future_timestamp_does_not_mute_an_outage(tmp):
    """A clock rollback must not buy more than 24h of silence."""
    ahead = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    out, _ = run(
        tmp / "future", unreachable=True, online=True,
        seed={"payload": PAYLOAD, "attempts": 5, "failed_days": [days_ago(1)],
              "last_notified_at": ahead},
    )
    assert "can't be reached" in out, f"future stamp suppressed the notice: {out!r}"


def test_control_host_http_error_still_means_online(tmp):
    """api.github.com hands out unauthenticated 403s. A 403 is not "no internet".

    If it were read as offline, a genuinely dead tracker would never be
    reported — the silent-forever bug, reintroduced through the control probe.
    """
    import urllib.error
    import urllib.request

    real_which, real_urlopen = hook.shutil.which, urllib.request.urlopen
    hook.shutil.which = lambda _name: None  # force the urllib path

    def forbidden(*_a, **_kw):
        raise urllib.error.HTTPError("https://api.github.com/", 403,
                                     "rate limited", {}, None)

    urllib.request.urlopen = forbidden
    try:
        assert hook._http_probe("https://api.github.com/", timeout=2,
                                any_response=True) is True, \
            "a 403 means the host answered — that is online"
        assert hook._http_probe("https://example.invalid/", timeout=2) is False, \
            "a 403 is NOT a healthy service"
    finally:
        hook.shutil.which, urllib.request.urlopen = real_which, real_urlopen


def test_probe_budget_is_total_not_per_transport(tmp):
    """The failure path can already have burned ~70s of the 90s hook budget."""
    import time as _time
    import urllib.request

    real_which, real_run = hook.shutil.which, hook.subprocess.run
    real_urlopen = urllib.request.urlopen
    called = []

    hook.shutil.which = lambda _name: "/usr/bin/curl"

    def slow_curl(*_a, **kw):
        _time.sleep(1.2)  # eat the whole budget, then fail

        class R:
            returncode, stdout, stderr = 1, "", ""
        return R()

    def record(*_a, **_kw):
        called.append(1)
        raise AssertionError("urllib must not run with no budget left")

    hook.subprocess.run = slow_curl
    urllib.request.urlopen = record
    try:
        started = _time.monotonic()
        assert hook._http_probe("https://example.invalid/", timeout=1) is False
        spent = _time.monotonic() - started
        assert not called, "second transport ran past the deadline"
        assert spent < 3, f"probe overran its budget: {spent:.1f}s"
    finally:
        hook.shutil.which, hook.subprocess.run = real_which, real_run
        urllib.request.urlopen = real_urlopen


# --- Macroscope round, PR #152 ------------------------------------------------
# Two classes: a marker value that is type-checked but never value-checked, and
# a notice that names a cause it never verified.


def test_junk_failed_days_do_not_trip_the_three_day_notice(tmp):
    """`{"failed_days": ["x", "y"]}` used to reach the threshold on one failure."""
    out, state = run(
        tmp / "j1", unreachable=False, online=True,
        seed={"payload": PAYLOAD, "attempts": 1, "failed_days": ["x", "y"]},
    )
    assert out == "", f"two junk strings are not two failed days: {out!r}"
    assert state["failed_days"] == [datetime.now(timezone.utc).date().isoformat()]


def test_future_failed_day_does_not_count(tmp):
    """A day that has not happened cannot have cost anyone their points."""
    ahead = (datetime.now(timezone.utc) + timedelta(days=3)).date().isoformat()
    out, state = run(
        tmp / "j2", unreachable=False, online=True,
        seed={"payload": PAYLOAD, "attempts": 9,
              "failed_days": [days_ago(1), ahead, ahead]},
    )
    assert out == "", f"a future date must not reach the threshold: {out!r}"
    assert ahead not in state["failed_days"]
    assert len(state["failed_days"]) == 2


def test_failed_days_are_stored_canonically(tmp):
    """3.11+ date.fromisoformat takes "20260825"; unnormalised it double-counts."""
    compact = days_ago(1).replace("-", "")
    out, state = run(
        tmp / "j3", unreachable=False, online=True,
        seed={"payload": PAYLOAD, "attempts": 9,
              "failed_days": [compact, days_ago(1)]},
    )
    assert out == "", f"one day written two ways is still one day: {out!r}"
    assert state["failed_days"] == sorted({days_ago(1),
                                           datetime.now(timezone.utc).date().isoformat()})


def test_negative_attempts_cannot_mute_an_outage(tmp):
    """A negative counter never reaches 2, so Branch A stayed silent forever."""
    out, state = run(
        tmp / "j4", unreachable=True, online=True,
        seed={"payload": PAYLOAD, "attempts": -50, "failed_days": [days_ago(1)]},
    )
    assert state["attempts"] == 1, f"attempts must clamp at 0, got {state['attempts']}"
    out, state = run(tmp / "j4", unreachable=True, online=True)
    assert "can't be reached" in out, f"outage must still be reported: {out!r}"


def test_three_offline_days_do_not_claim_the_tracker_is_slow(tmp):
    """The false alarm this PR exists to kill, in its remaining form."""
    out, _ = run(
        tmp / "j5", unreachable=True, online=False,
        seed={"payload": PAYLOAD, "attempts": 1,
              "failed_days": [days_ago(3), days_ago(2), days_ago(1)]},
    )
    assert out == "", f"offline days are not slow tracker writes: {out!r}"


def test_slow_notice_still_fires_when_the_tracker_answers(tmp):
    """The gate must not silence the real case it is guarding."""
    out, _ = run(
        tmp / "j6", unreachable=False, online=True,
        seed={"payload": PAYLOAD, "attempts": 1,
              "failed_days": [days_ago(3), days_ago(2), days_ago(1)]},
    )
    assert "too slow" in out, f"a genuinely slow tracker must be reported: {out!r}"


def test_probes_are_evaluated_at_most_once(tmp):
    """Both branches need them; neither should pay the round-trip twice."""
    calls = {"unreachable": 0, "online": 0}
    marker = tmp / "j7"
    marker.write_text(json.dumps(
        {"payload": PAYLOAD, "attempts": 9,
         "failed_days": [days_ago(3), days_ago(2), days_ago(1)]}), encoding="utf-8")
    hook.PING_FAIL_MARKER = marker

    def count(name, value):
        def probe():
            calls[name] += 1
            return value
        return probe

    hook._tracker_unreachable = count("unreachable", False)
    hook._internet_up = count("online", True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        hook.note_ping_failure(PAYLOAD)
    assert calls == {"unreachable": 1, "online": 1}, f"probe budget blown: {calls}"


def test_corrupt_replay_payload_is_discarded_not_retried(tmp):
    """A non-dict payload used to be POSTed, raise, and keep the marker forever."""
    marker = tmp / "j8"
    marker.write_text(json.dumps({"payload": "not-a-dict"}), encoding="utf-8")
    hook.PING_FAIL_MARKER = marker
    posted = []
    real_post = hook._post_session_ping
    hook._post_session_ping = lambda b: posted.append(b)
    try:
        assert hook.replay_failed_ping() is None
    finally:
        hook._post_session_ping = real_post
    assert posted == [], f"a malformed payload must never be sent: {posted!r}"
    assert not marker.exists(), "malformed marker must be cleared, not retried"


def test_good_replay_payload_still_posts(tmp):
    marker = tmp / "j9"
    marker.write_text(json.dumps({"payload": PAYLOAD}), encoding="utf-8")
    hook.PING_FAIL_MARKER = marker
    posted = []
    real_post = hook._post_session_ping
    hook._post_session_ping = lambda b: posted.append(b)
    try:
        assert hook.replay_failed_ping() == PAYLOAD
    finally:
        hook._post_session_ping = real_post
    assert posted == [PAYLOAD]
    assert not marker.exists()


# --- Macroscope round 2, PR #152 ---------------------------------------------
# The payload must outlive the probes, and the failed-day ledger must outlive
# the retry payload.


def test_payload_is_on_disk_before_the_probes_run(tmp):
    """SessionStart can be killed mid-probe, and nothing replays what was never
    stashed — so the payload must not depend on a network call returning."""
    marker = tmp / "r1"
    # attempts >= 2 so Branch A actually REACHES a probe. With a fresh marker
    # attempts is 1, no probe is called at all, and this test would pass
    # against the very code it is meant to catch.
    marker.write_text(json.dumps({"attempts": 7}), encoding="utf-8")
    hook.PING_FAIL_MARKER = marker

    def killed():
        raise KeyboardInterrupt("SessionStart budget exhausted")

    hook._tracker_unreachable = killed
    hook._internet_up = killed
    try:
        hook.note_ping_failure(PAYLOAD)
    except KeyboardInterrupt:
        pass
    assert marker.exists(), "the payload was lost when the probe did not return"
    state = json.loads(marker.read_text())
    assert state.get("payload") == PAYLOAD, (
        "the payload was not persisted before the probes ran, so a hook killed "
        f"mid-probe drops that session's credit: {state!r}")


def test_a_successful_replay_keeps_the_earlier_failed_days(tmp):
    """Day 1 fails, day 2 replays. Day 1 lost its point and must stay logged."""
    marker = tmp / "r2"
    marker.write_text(json.dumps({
        "payload": PAYLOAD,
        "failed_days": [days_ago(2), days_ago(1)],
    }), encoding="utf-8")
    hook.PING_FAIL_MARKER = marker
    real_post = hook._post_session_ping
    hook._post_session_ping = lambda b: None
    try:
        assert hook.replay_failed_ping() == PAYLOAD
    finally:
        hook._post_session_ping = real_post
    assert marker.exists(), "the replay used to delete the whole ledger"
    state = json.loads(marker.read_text())
    assert state["failed_days"] == [days_ago(2), days_ago(1)]
    assert "payload" not in state, "the payload was delivered; it must not linger"


def test_intermittent_failures_still_reach_the_three_day_notice(tmp):
    """The shape of the bug end to end: fail, replay, fail, replay, fail."""
    marker = tmp / "r3"
    real_post = hook._post_session_ping
    hook._post_session_ping = lambda b: None
    hook.PING_FAIL_MARKER = marker
    try:
        for d in (days_ago(3), days_ago(2)):
            carried = (json.loads(marker.read_text())["failed_days"]
                       if marker.exists() else [])
            marker.write_text(
                json.dumps({"payload": PAYLOAD, "failed_days": carried + [d]}),
                encoding="utf-8")
            hook.replay_failed_ping()
            assert marker.exists(), (
                "the replay deleted the ledger along with the payload — this "
                "is the wipe that stops intermittent failures ever counting")
        state = json.loads(marker.read_text())
        assert state["failed_days"] == [days_ago(3), days_ago(2)], (
            f"both lost days must survive their replays: {state}")
    finally:
        hook._post_session_ping = real_post
    out, _ = run(marker, unreachable=False, online=True,
                 seed={"failed_days": [days_ago(3), days_ago(2)]})
    assert "too slow" in out, (
        f"the third lost day must finally speak; the ledger used to be "
        f"wiped before it could: {out!r}")


def test_todays_credit_landing_clears_today_only(tmp):
    marker = tmp / "r4"
    today = datetime.now(timezone.utc).date().isoformat()
    marker.write_text(json.dumps({
        "payload": PAYLOAD,
        "failed_days": [days_ago(5), today],
        "last_notified_at": "2026-01-01T00:00:00+00:00",
    }), encoding="utf-8")
    hook.PING_FAIL_MARKER = marker
    real_post = hook._post_session_ping
    hook._post_session_ping = lambda b: None
    try:
        hook.replay_failed_ping()  # go through the real path, not the helper
    finally:
        hook._post_session_ping = real_post
    assert marker.exists(), "the ledger must survive a delivery"
    state = json.loads(marker.read_text())
    assert state["failed_days"] == [days_ago(5)], (
        "today was delivered so today is not a lost day; day 5 still is")
    assert "last_notified_at" not in state, (
        "a delivery ends the outage, so the 24h suppression must not survive "
        "it — otherwise a genuine NEW outage inside the window goes unheard")


def test_suppression_survives_an_undelivered_payload(tmp):
    """The flip side: the condition is still on, so don't re-nag."""
    marker = tmp / "r7"
    marker.write_text(json.dumps({
        "payload": "not-a-dict",  # malformed: nothing was delivered
        "failed_days": [days_ago(5)],
        "last_notified_at": "2026-01-01T00:00:00+00:00",
    }), encoding="utf-8")
    hook.PING_FAIL_MARKER = marker
    assert hook.replay_failed_ping() is None
    state = json.loads(marker.read_text())
    assert state["last_notified_at"] == "2026-01-01T00:00:00+00:00"
    assert state["failed_days"] == [days_ago(5)]


def test_an_unreadable_marker_is_never_deleted(tmp):
    """A concurrent SessionStart mid-write looks exactly like corruption.

    Deleting it makes the writer finish into an unlinked inode and the payload
    is gone. Leaving it is free — note_ping_failure treats an unreadable prior
    as {} and overwrites, so it cannot get stuck either.
    """
    marker = tmp / "r8"
    marker.write_text('{"payload": {"a": ', encoding="utf-8")  # truncated write
    hook.PING_FAIL_MARKER = marker
    assert hook.replay_failed_ping() is None
    assert marker.exists(), "a half-written marker must survive the reader"

    hook._tracker_unreachable = lambda: True
    hook._internet_up = lambda: True
    hook.note_ping_failure(PAYLOAD)
    assert json.loads(marker.read_text())["payload"] == PAYLOAD, \
        "and the next failure must be able to overwrite it"


def test_marker_writes_are_atomic(tmp):
    """No reader should ever observe a truncated marker."""
    marker = tmp / "r9"
    hook.PING_FAIL_MARKER = marker
    hook._tracker_unreachable = lambda: True
    hook._internet_up = lambda: True
    hook.note_ping_failure(PAYLOAD)
    first = marker.read_text()

    seen = []
    real_replace = hook.os.replace

    def watching(src, dst):
        # Whatever a concurrent reader sees at this instant must be valid.
        seen.append(marker.read_text() if marker.exists() else None)
        return real_replace(src, dst)

    hook.os.replace = watching
    try:
        hook.note_ping_failure(PAYLOAD)
    finally:
        hook.os.replace = real_replace
    assert seen and seen[0] == first, (
        f"the old marker must still be intact until the swap: {seen!r}")
    leftovers = [p.name for p in marker.parent.iterdir() if p.name != marker.name]
    assert leftovers == [], f"temp files must not be left behind: {leftovers}"


def test_ledger_only_marker_is_not_replayed_and_not_deleted(tmp):
    marker = tmp / "r5"
    marker.write_text(json.dumps({"failed_days": [days_ago(1)]}), encoding="utf-8")
    hook.PING_FAIL_MARKER = marker
    posted = []
    real_post = hook._post_session_ping
    hook._post_session_ping = lambda b: posted.append(b)
    try:
        assert hook.replay_failed_ping() is None
    finally:
        hook._post_session_ping = real_post
    assert posted == [], "there is nothing to replay in a ledger-only marker"
    assert marker.exists(), "a ledger with no payload must survive"


def test_last_lost_day_clearing_removes_the_file(tmp):
    marker = tmp / "r6"
    today = datetime.now(timezone.utc).date().isoformat()
    marker.write_text(json.dumps({"payload": PAYLOAD, "failed_days": [today]}),
                      encoding="utf-8")
    hook.PING_FAIL_MARKER = marker
    real_post = hook._post_session_ping
    hook._post_session_ping = lambda b: None
    try:
        hook.replay_failed_ping()
    finally:
        hook._post_session_ping = real_post
    assert not marker.exists(), "no payload and no lost days: no file"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    with tempfile.TemporaryDirectory() as td:
        for i, fn in enumerate(tests):
            sub = Path(td) / str(i)
            sub.mkdir()
            try:
                fn(sub)
                print(f"  ok   {fn.__name__}")
            except AssertionError as exc:
                failed += 1
                print(f"  FAIL {fn.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

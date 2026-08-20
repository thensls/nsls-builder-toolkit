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

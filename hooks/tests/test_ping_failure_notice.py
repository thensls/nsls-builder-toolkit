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


def run(marker, *, unreachable, online, seed=None):
    """Call note_ping_failure with the probes stubbed. Returns (stdout, marker)."""
    hook.PING_FAIL_MARKER = marker
    hook._tracker_unreachable = lambda: unreachable
    hook._internet_up = lambda: online
    if seed is not None:
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

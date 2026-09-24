#!/usr/bin/env python3
"""The collector's evidence file retires two toolkit credits on its machine.

When `<config dir>/.nsls-collector/reported.json` is fresh, the session ping
tells the tracker `collector_backed: true` (so the tracker skips only the
daily-session credit) and the skill hook posts nothing, because the collector
already reports both. On any other machine, including one whose collector went
quiet eight days ago, both behave exactly as before.

Plain stdlib, no pytest import: runs on a stock install with
`python3 hooks/tests/test_collector_evidence.py`, and pytest collects it too.
"""

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "collector_evidence", HOOKS / "collector_evidence.py")
evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evidence)

_spec = importlib.util.spec_from_file_location(
    "session_start_hook_ce", HOOKS / "session-start.py")
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def ago(**kw):
    return datetime.now(timezone.utc) - timedelta(**kw)


def write_evidence(config_dir, content):
    d = Path(config_dir) / ".nsls-collector"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "reported.json"
    if isinstance(content, (dict, list)):
        content = json.dumps(content)
    p.write_text(content, encoding="utf-8")
    return p


def record(at, machine_id="m-123"):
    return {"machine_id": machine_id, "at": at, "version": "1.0.0"}


# Each case: (name, file content or None for absent, expected fresh()).
CASES = [
    ("fresh", lambda: record(iso(ago(hours=1))), True),
    ("fresh_fractional_offset", lambda: record(
        ago(days=6).strftime("%Y-%m-%dT%H:%M:%S.123456+00:00")), True),
    ("slightly_future_clock_skew", lambda: record(iso(ago(hours=-12))), True),
    ("eight_days_old", lambda: record(iso(ago(days=8))), False),
    ("missing", None, False),
    ("malformed", lambda: '{"machine_id": "m-1", "at": ', False),
    ("not_an_object", lambda: [record(iso(ago(hours=1)))], False),
    ("far_future", lambda: record(iso(ago(days=-2))), False),
    ("numeric_machine_id", lambda: record(iso(ago(hours=1)), machine_id=123), False),
    ("empty_machine_id", lambda: record(iso(ago(hours=1)), machine_id=""), False),
    ("missing_machine_id", lambda: {"at": iso(ago(hours=1))}, False),
    ("non_utc_offset", lambda: record(
        ago(hours=1).strftime("%Y-%m-%dT%H:%M:%S-05:00")), False),
    ("date_only", lambda: record(ago(hours=1).strftime("%Y-%m-%d")), False),
    ("garbage_at", lambda: record("yesterday"), False),
    ("oversized", lambda: dict(record(iso(ago(hours=1))), pad="x" * 5000), False),
]


def _with_case(content_fn):
    tmp = Path(tempfile.mkdtemp(prefix="ce-test-"))
    if content_fn is not None:
        write_evidence(tmp, content_fn())
    return tmp


# ── collector_evidence.fresh() ─────────────────────────────────────────────


def test_fresh_contract_cases():
    for name, content_fn, expected in CASES:
        tmp = _with_case(content_fn)
        try:
            got = evidence.fresh(config_dir=tmp)
            assert got is expected, f"{name}: fresh() -> {got!r}, want {expected!r}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_fresh_honours_claude_config_dir():
    tmp = _with_case(lambda: record(iso(ago(hours=1))))
    old = os.environ.get("CLAUDE_CONFIG_DIR")
    try:
        os.environ["CLAUDE_CONFIG_DIR"] = str(tmp)
        assert evidence.fresh() is True
        assert evidence.evidence_path() == tmp / ".nsls-collector" / "reported.json"
    finally:
        if old is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = old
        shutil.rmtree(tmp, ignore_errors=True)


def test_fresh_never_raises_on_a_directory_or_binary():
    tmp = Path(tempfile.mkdtemp(prefix="ce-test-"))
    try:
        (tmp / ".nsls-collector" / "reported.json").mkdir(parents=True)
        assert evidence.fresh(config_dir=tmp) is False
        shutil.rmtree(tmp / ".nsls-collector")
        p = write_evidence(tmp, "")
        p.write_bytes(b"\xff\xfe\x00{garbage")
        assert evidence.fresh(config_dir=tmp) is False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── session_ping payload ───────────────────────────────────────────────────


def _ping_payload(config_dir):
    """Run session_ping with the network and env stubbed; return the body sent."""
    sent = []
    saved = {k: getattr(hook, k) for k in
             ("CONFIG_DIR", "read_env", "_post_session_ping", "_retire_ping_payload")}
    try:
        hook.CONFIG_DIR = Path(config_dir)
        hook.read_env = lambda key: {"BUILDER_EMAIL": "builder@nsls.org",
                                     "GITHUB_USERNAME": "builder"}.get(key, "")
        hook._post_session_ping = lambda body, *a, **k: sent.append(dict(body)) or {}
        hook._retire_ping_payload = lambda **k: None
        hook.session_ping()
    finally:
        for k, v in saved.items():
            setattr(hook, k, v)
    assert len(sent) == 1, f"expected exactly one ping, got {len(sent)}"
    return sent[0]


def test_session_ping_flags_collector_backed_when_fresh():
    tmp = _with_case(lambda: record(iso(ago(hours=1))))
    try:
        body = _ping_payload(tmp)
        assert body.get("collector_backed") is True, body
        # Everything else in the ping is unchanged.
        assert body["builder_email"] == "builder@nsls.org"
        assert body["github_username"] == "builder"
        assert set(body) == {"builder_email", "toolkit", "github_username",
                             "platform", "collector_backed"}, body
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_session_ping_unflagged_when_stale_missing_or_malformed():
    for name in ("eight_days_old", "missing", "malformed", "far_future",
                 "numeric_machine_id"):
        content_fn = next(c for n, c, _ in CASES if n == name)
        tmp = _with_case(content_fn)
        try:
            body = _ping_payload(tmp)
            assert "collector_backed" not in body, f"{name}: {body}"
            assert set(body) == {"builder_email", "toolkit", "github_username",
                                 "platform"}, f"{name}: {body}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ── skill-event.sh ─────────────────────────────────────────────────────────


def _run_skill_event(config_dir):
    """Run skill-event.sh with a stub curl on PATH. Returns (rc, curl_called)."""
    bindir = Path(tempfile.mkdtemp(prefix="ce-bin-"))
    log = bindir / "curl.log"
    stub = bindir / "curl"
    stub.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\nexit 0\n')
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    envdir = Path(config_dir) / "local-plugins" / "nsls-personal-toolkit"
    envdir.mkdir(parents=True, exist_ok=True)
    (envdir / ".env").write_text("BUILDER_EMAIL=builder@nsls.org\n")
    env = dict(os.environ)
    env["PATH"] = f"{bindir}{os.pathsep}{env.get('PATH', '')}"
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    env["NSLS_TRACKER_URL"] = "http://127.0.0.1:9"
    env.pop("SKILL_EVENT_VERBOSE", None)
    try:
        proc = subprocess.run(
            ["bash", str(HOOKS / "skill-event.sh")],
            input='{"tool_name":"Skill","tool_input":{"skill":"nsls-builder-toolkit:gws"}}',
            capture_output=True, text=True, env=env, timeout=20)
        return proc.returncode, log.exists()
    finally:
        shutil.rmtree(bindir, ignore_errors=True)


def test_skill_event_sh_matches_fresh_for_every_case():
    """The bash check is a second implementation of the same contract, so it
    runs against every fixture the Python one does."""
    for name, content_fn, expected_fresh in CASES:
        tmp = _with_case(content_fn)
        try:
            rc, posted = _run_skill_event(tmp)
            assert rc == 0, f"{name}: exit {rc}"
            assert posted is (not expected_fresh), (
                f"{name}: curl {'called' if posted else 'not called'}, "
                f"evidence fresh={expected_fresh}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_guardrail_gate_untouched():
    """U6 must not change the gate. Compare against the merge base with main."""
    try:
        base = subprocess.run(
            ["git", "merge-base", "HEAD", "origin/main"], cwd=HOOKS,
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        base = ""
    if not base:
        return  # not a git checkout (e.g. a plugin cache) — nothing to compare
    diff = subprocess.run(
        ["git", "diff", "--stat", base, "--", "guardrail-gate.py"], cwd=HOOKS,
        capture_output=True, text=True, timeout=10).stdout.strip()
    assert diff == "", f"guardrail-gate.py changed:\n{diff}"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"ok   {name}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)

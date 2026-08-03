#!/usr/bin/env python3.12
"""API-key auth for the Neon billing source.

Neon's org-scoped billing endpoint takes a plain long-lived API key — no
cookie, no browser, no session that expires every few days:

    GET https://console.neon.tech/api/v2/organizations/{org_id}/billing/invoices
    Authorization: Bearer $NEON_API_KEY

That key is a live credential with a much longer life than a claude.ai
session, which makes leaking it strictly worse. Most of this file exists to
prove the code treats it like one: it is never echoed, never logged, never
interpolated into a message, and the file holding it is refused outright if
anyone else on the machine can read it.

The four failure modes are kept distinct on purpose, because each one is a
DIFFERENT thing the operator has to do:

  * no key stored        -> store one with --set-neon-key
  * no NEON_ORG_ID       -> set that variable (from the Neon Console URL)
  * 401 / 403            -> the key is invalid or is not an ORGANIZATION key
  * 400 "method is
    deprecated"          -> we called the retired endpoint form. That is a
                            code bug, and blaming the user's credentials for
                            it sends them to re-issue a key that was fine.

Hermetic by construction: no network (the `_open` seam is always patched),
no auth, and every key path is redirected into a throwaway temp directory —
no test reads or writes the real ~/.claude-receipts-neon-key. No real API
key and no real Orb token appears anywhere in this file.
"""

import contextlib
import email.message
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sources.neon as neon
from sources.base import SourceUnavailable
from sources.neon import SOURCE

# A value that is never real and never valid. Every error path in this file
# runs with this as "the API key", and every assertion checks it did not come
# back out in the message. If a test here ever fails on the sentinel, the
# code leaked a credential into text a user (or a log, or a ledger) will see.
SENTINEL = "napi_SENTINEL_DO_NOT_PRINT_0123456789abcdef"
ORG = "org-test-example-12345678"

PAYLOAD = {
    "invoices": [
        {"invoice_number": "NLPHVL-00016", "issued_at": "2026-08-01T14:22:13Z",
         "paid_at": "2026-08-01T14:22:23Z", "status": "paid",
         "pdf_url": "https://assets.withorb.com/invoice/16?token=PLACEHOLDER",
         "total": "550.76", "currency": "USD"},
    ],
}

DEPRECATED_BODY = b'{"message":"method is deprecated"}'


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _sandbox(*, stored=None, mode=0o600, org=ORG, env_key=None):
    """Point the module's key file at a throwaway temp path and control the
    environment. Nothing in this file may ever touch the real file."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / ".claude-receipts-neon-key"
        if stored is not None:
            path.write_text(stored + "\n")
            os.chmod(path, mode)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(neon.KEY_ENV, None)
            os.environ.pop(neon.ORG_ENV, None)
            os.environ.pop("RECEIPTS_LOGIN_TEST_NOOP", None)
            if org is not None:
                os.environ[neon.ORG_ENV] = org
            if env_key is not None:
                os.environ[neon.KEY_ENV] = env_key
            with patch.object(neon, "KEY_FILE", str(path)):
                yield path


def _headers(pairs):
    msg = email.message.Message()
    for k, v in (pairs or {}).items():
        msg[k] = v
    return msg


class _FakeRaw:
    def __init__(self, status=200, body=b"{}", headers=None, url=""):
        self.status = status
        self.headers = _headers(headers)
        self._body = body
        self._url = url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body

    def geturl(self):
        return self._url


def _serve(status=200, body=b"{}", headers=None):
    """A fake `_open` that records the urllib.request.Request objects handed
    to it, so tests can assert on the headers the code actually built."""
    calls = []

    def fake(req, timeout=None):
        calls.append(req)
        if status == 200:
            return _FakeRaw(200, body, headers, req.full_url)
        raise urllib.error.HTTPError(
            req.full_url, status, "error", _headers(headers), io.BytesIO(body),
        )

    fake.calls = calls
    return fake


# ---------------------------------------------------------------------------
# Key resolution
# ---------------------------------------------------------------------------

def test_env_key_beats_the_stored_file():
    with _sandbox(stored="from-the-file", env_key=SENTINEL):
        assert neon._stored_key() == SENTINEL


def test_stored_file_is_used_when_the_env_var_is_unset():
    with _sandbox(stored=SENTINEL):
        assert neon._stored_key() == SENTINEL


def test_group_or_world_readable_key_file_is_refused():
    for bad_mode in (0o644, 0o640, 0o604, 0o666):
        with _sandbox(stored=SENTINEL, mode=bad_mode) as path:
            try:
                neon._stored_key()
            except SourceUnavailable as exc:
                msg = str(exc)
                assert "600" in msg, f"say what the mode must be: {msg}"
                assert str(path) in msg, f"name the file: {msg}"
                assert SENTINEL not in msg
            else:
                raise AssertionError(
                    f"mode {bad_mode:04o} is readable by others and must be refused"
                )


def test_a_correctly_locked_down_file_is_accepted():
    with _sandbox(stored=SENTINEL, mode=0o600):
        assert neon._stored_key() == SENTINEL
    with _sandbox(stored=SENTINEL, mode=0o400):
        assert neon._stored_key() == SENTINEL


def test_empty_key_file_is_refused_rather_than_sent_as_a_blank_bearer_token():
    with _sandbox(stored="   ", mode=0o600):
        try:
            neon._stored_key()
        except SourceUnavailable as exc:
            assert "--set-neon-key" in str(exc), str(exc)
            return
    raise AssertionError("an empty key file must raise SourceUnavailable")


def test_key_file_lives_outside_the_repo_so_it_cannot_be_committed():
    repo_root = Path(__file__).resolve().parents[3]
    path = Path(os.path.expanduser(neon.KEY_FILE))
    assert not str(path.resolve()).startswith(str(repo_root) + os.sep), (
        f"the key file must never live inside the repo tree: {path}"
    )
    assert neon.KEY_FILE.startswith("~/"), (
        f"the key file must live in the user's home: {neon.KEY_FILE}"
    )
    assert neon.KEY_FILE == "~/.claude-receipts-neon-key", neon.KEY_FILE


def test_no_author_specific_or_hardcoded_org_id_ships_in_the_module():
    source = Path(neon.__file__).read_text()
    assert "/Users/" not in source, (
        "sources/neon.py must never contain an author-specific literal path"
    )
    # An org id looks like "org-<slug>". The module must read it from the
    # environment — this skill ships org-wide and must never default to one
    # organisation's billing data.
    code = "\n".join(ln for ln in source.splitlines() if not ln.lstrip().startswith("#"))
    import ast
    tree = ast.parse(source)
    for doc in [ast.get_docstring(n) for n in ast.walk(tree)
                if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))]:
        if doc:
            code = code.replace(doc, "")
    assert not re.search(r"['\"]org-[a-z0-9-]{6,}['\"]", code), (
        "a literal Neon org id must never be hardcoded:\n" + code
    )


# ---------------------------------------------------------------------------
# The request itself
# ---------------------------------------------------------------------------

def test_listing_sends_the_key_as_a_bearer_header_against_the_org_scoped_path():
    fake = _serve(200, json.dumps(PAYLOAD).encode())
    with _sandbox(stored=SENTINEL):
        with patch.object(neon, "_open", fake):
            payload = SOURCE._invoices()

    assert payload["invoices"][0]["total"] == "550.76"
    assert fake.calls, "no HTTP request was made"
    req = fake.calls[0]
    assert req.get_header("Authorization") == f"Bearer {SENTINEL}", req.headers
    assert req.full_url == (
        f"https://console.neon.tech/api/v2/organizations/{ORG}/billing/invoices"
    ), req.full_url
    assert SENTINEL not in req.full_url, "the credential must never ride in the URL"
    assert "org_id=" not in req.full_url, (
        "the query-parameter form is the retired endpoint and returns "
        "HTTP 400 'method is deprecated'"
    )


def test_no_cookie_is_ever_sent():
    fake = _serve(200, json.dumps(PAYLOAD).encode())
    with _sandbox(stored=SENTINEL):
        with patch.object(neon, "_open", fake):
            SOURCE._invoices()
    assert fake.calls[0].get_header("Cookie") is None, (
        "this endpoint takes a plain API key — no browser, no session cookie"
    )


# ---------------------------------------------------------------------------
# Four distinct failure modes — never collapsed into one
# ---------------------------------------------------------------------------

def _listing_error(*, sandbox_kwargs=None, **serve_kwargs):
    fake = _serve(**serve_kwargs)
    with _sandbox(**(sandbox_kwargs or {"stored": SENTINEL})):
        with patch.object(neon, "_open", fake):
            try:
                SOURCE._invoices()
            except SourceUnavailable as exc:
                return str(exc)
    raise AssertionError("expected SourceUnavailable")


def test_no_key_stored_names_set_neon_key():
    fake = _serve(200, json.dumps(PAYLOAD).encode())
    with _sandbox():
        with patch.object(neon, "_open", fake):
            try:
                SOURCE._invoices()
            except SourceUnavailable as exc:
                msg = str(exc)
                assert "--set-neon-key" in msg, msg
                assert neon.KEY_ENV in msg, "name the env var alternative too: " + msg
                assert not fake.calls, "no request may be made with no key"
                return
    raise AssertionError("a missing key must raise SourceUnavailable")


def test_missing_org_id_names_the_variable_and_where_to_find_it():
    fake = _serve(200, json.dumps(PAYLOAD).encode())
    with _sandbox(stored=SENTINEL, org=None):
        with patch.object(neon, "_open", fake):
            try:
                SOURCE.fetch("2026-01-01", "2026-12-31")
            except SourceUnavailable as exc:
                msg = str(exc)
                assert "NEON_ORG_ID" in msg, msg
                assert "console" in msg.lower(), (
                    "say where to find it — the Neon Console URL: " + msg
                )
                assert "org-" in msg, "show the shape of the value: " + msg
                assert not fake.calls, "no request may be made without an org id"
                return
    raise AssertionError("a missing NEON_ORG_ID must raise SourceUnavailable")


def test_401_says_the_key_is_invalid_and_asks_for_an_organization_key():
    msg = _listing_error(status=401)
    assert "organization" in msg.lower(), msg
    assert "api key" in msg.lower(), msg
    assert "deprecated" not in msg.lower(), msg
    assert "NEON_ORG_ID" not in msg, (
        "a rejected key is not a missing org id: " + msg
    )
    assert SENTINEL not in msg


def test_403_is_reported_the_same_way_as_401_and_not_as_a_code_bug():
    msg = _listing_error(status=403)
    assert "organization" in msg.lower(), msg
    assert "deprecated" not in msg.lower(), msg
    assert SENTINEL not in msg


def test_deprecated_endpoint_is_named_as_a_code_bug_not_a_credential_problem():
    # HTTP 400 {"message":"method is deprecated"} is what the retired
    # /api/v2/billing/invoices?org_id=… form returns. Telling the operator to
    # re-issue their API key for it sends them to fix something that was
    # never broken.
    msg = _listing_error(status=400, body=DEPRECATED_BODY)
    assert "deprecated" in msg.lower(), msg
    assert "endpoint" in msg.lower(), msg
    assert "--set-neon-key" not in msg, (
        "a wrong endpoint is not fixed by storing a new key: " + msg
    )
    assert "invalid" not in msg.lower(), (
        "must not blame the credential for a code bug: " + msg
    )
    assert SENTINEL not in msg


def test_the_four_failure_modes_all_differ_from_one_another():
    msgs = []

    fake = _serve(200, json.dumps(PAYLOAD).encode())
    with _sandbox():
        with patch.object(neon, "_open", fake):
            try:
                SOURCE._invoices()
            except SourceUnavailable as exc:
                msgs.append(str(exc))

    with _sandbox(stored=SENTINEL, org=None):
        try:
            SOURCE.fetch("2026-01-01", "2026-12-31")
        except SourceUnavailable as exc:
            msgs.append(str(exc))

    msgs.append(_listing_error(status=401))
    msgs.append(_listing_error(status=400, body=DEPRECATED_BODY))

    assert len(msgs) == 4, msgs
    assert len(set(msgs)) == 4, "failure modes were collapsed:\n" + "\n---\n".join(msgs)


def test_an_unexpected_status_is_not_dressed_up_as_one_of_the_four():
    msg = _listing_error(status=500)
    assert "500" in msg, msg
    assert "deprecated" not in msg.lower(), msg
    assert SENTINEL not in msg


def test_a_plain_400_that_is_not_the_deprecation_is_not_called_deprecated():
    msg = _listing_error(status=400, body=b'{"message":"bad request"}')
    assert "deprecated" not in msg.lower(), msg
    assert SENTINEL not in msg


def test_a_transport_failure_is_reported_without_leaking_the_key():
    def boom(req, timeout=None):
        raise urllib.error.URLError("connection reset")

    with _sandbox(stored=SENTINEL):
        with patch.object(neon, "_open", boom):
            try:
                SOURCE._invoices()
            except SourceUnavailable as exc:
                msg = str(exc)
                assert SENTINEL not in msg
                assert "network" in msg.lower(), (
                    "a transport failure is not an auth failure: " + msg
                )
                return
    raise AssertionError("a transport failure must degrade to SourceUnavailable")


def test_a_200_that_is_not_json_is_reported_rather_than_read_as_no_invoices():
    msg = _listing_error(status=200, body=b"<html>nope</html>")
    assert "json" in msg.lower(), msg
    assert SENTINEL not in msg


# ---------------------------------------------------------------------------
# The credential never comes back out
# ---------------------------------------------------------------------------

def test_the_api_key_never_appears_in_any_message_this_module_raises():
    # Every error path, one sentinel, one rule: it is never in the text.
    paths = [
        lambda: _listing_error(status=401),
        lambda: _listing_error(status=403),
        lambda: _listing_error(status=400, body=DEPRECATED_BODY),
        lambda: _listing_error(status=400, body=b'{"message":"bad request"}'),
        lambda: _listing_error(status=429),
        lambda: _listing_error(status=500),
        lambda: _listing_error(status=200, body=b"<html>not json</html>"),
        lambda: _listing_error(sandbox_kwargs={"stored": SENTINEL, "mode": 0o644},
                               status=200, body=b"{}"),
    ]
    for i, run_path in enumerate(paths):
        msg = run_path()
        assert SENTINEL not in msg, f"path {i} leaked the key: {msg}"
        assert "Bearer " not in msg, f"path {i} echoed the auth header: {msg}"


def test_an_error_body_that_echoes_the_key_back_is_scrubbed():
    # A server that reflects the credential into its own error body must not
    # get it printed into a report line or a ledger entry via our message.
    body = json.dumps({"message": f"invalid token {SENTINEL}"}).encode()
    msg = _listing_error(status=401, body=body)
    assert SENTINEL not in msg, msg


def test_fetch_never_leaks_the_key_through_the_truncated_report_line():
    with _sandbox(stored=SENTINEL):
        with patch.object(neon, "_open",
                          _serve(200, json.dumps({**PAYLOAD, "has_more": True}).encode())):
            with patch.object(SOURCE, "_download", return_value=b"%PDF-1.4"):
                SOURCE.fetch("2026-01-01", "2026-12-31")
    note = getattr(SOURCE, "truncated", "") or ""
    assert SENTINEL not in note, note


# ---------------------------------------------------------------------------
# --set-neon-key: store the credential safely, and only if it works
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _no_echo():
    """getpass must be what reads the value — never input(), which echoes to
    the terminal and (in a shell one-liner) lands in history."""
    def forbidden(*a, **k):
        raise AssertionError("the key must be read with getpass, never input()")

    with patch("builtins.input", forbidden):
        yield


def test_set_neon_key_stores_a_validated_value_with_mode_0600():
    fake = _serve(200, json.dumps(PAYLOAD).encode())
    out = io.StringIO()
    with _sandbox() as path:
        with patch.object(neon, "_open", fake), _no_echo(), \
             patch("getpass.getpass", return_value=SENTINEL + "\n") as gp, \
             contextlib.redirect_stdout(out):
            code = neon._set_neon_key()

        assert code == 0, out.getvalue()
        gp.assert_called_once()
        assert path.exists(), "a validated key must actually be stored"
        assert path.read_text().strip() == SENTINEL
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600, f"stored credential must be 0600, got {mode:04o}"
        assert fake.calls, "the value must be validated with a live call before storing"
        assert fake.calls[0].get_header("Authorization") == f"Bearer {SENTINEL}"


def test_set_neon_key_writes_atomically_through_a_same_directory_temp_file():
    fake = _serve(200, json.dumps(PAYLOAD).encode())
    seen = []
    real_replace = os.replace

    def spy(src, dst):
        seen.append((str(src), str(dst)))
        return real_replace(src, dst)

    with _sandbox() as path:
        with patch.object(neon, "_open", fake), _no_echo(), \
             patch("getpass.getpass", return_value=SENTINEL), \
             patch("os.replace", spy), \
             contextlib.redirect_stdout(io.StringIO()):
            neon._set_neon_key()

        assert seen, "the write must go through os.replace, like the ledger's"
        src, dst = seen[-1]
        assert dst == str(path)
        assert os.path.dirname(src) == os.path.dirname(str(path)), (
            "the temp file must sit in the destination directory or os.replace "
            f"is not atomic across filesystems: {src} -> {dst}"
        )
        assert not list(path.parent.glob(".claude-receipts-neon-key.*")), (
            "the temp file must not be left behind next to the credential"
        )


def test_set_neon_key_rejects_an_invalid_value_instead_of_storing_it():
    fake = _serve(401)
    out, err = io.StringIO(), io.StringIO()
    with _sandbox() as path:
        with patch.object(neon, "_open", fake), _no_echo(), \
             patch("getpass.getpass", return_value=SENTINEL), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = neon._set_neon_key()

        combined = out.getvalue() + err.getvalue()
        assert code != 0, "an unusable key must not report success"
        assert not path.exists(), (
            "an invalid key must never be stored — the user would discover it "
            "on the next real run instead of right now"
        )
        assert "organization" in combined.lower(), (
            "say why it was rejected, not just that it was: " + combined
        )
        assert SENTINEL not in combined, combined


def test_set_neon_key_never_prints_the_value_it_was_given():
    fake = _serve(200, json.dumps(PAYLOAD).encode())
    out, err = io.StringIO(), io.StringIO()
    with _sandbox():
        with patch.object(neon, "_open", fake), _no_echo(), \
             patch("getpass.getpass", return_value=SENTINEL), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            neon._set_neon_key()

    combined = out.getvalue() + err.getvalue()
    assert combined.strip(), "storing a credential must confirm it worked"
    assert SENTINEL not in combined, "the stored value was echoed back: " + combined


def test_set_neon_key_prints_where_to_create_the_key():
    fake = _serve(200, json.dumps(PAYLOAD).encode())
    out = io.StringIO()
    with _sandbox():
        with patch.object(neon, "_open", fake), _no_echo(), \
             patch("getpass.getpass", return_value=SENTINEL), \
             contextlib.redirect_stdout(out):
            neon._set_neon_key()

    text = out.getvalue().lower()
    for needle in ("neon console", "organization settings", "api key"):
        assert needle in text, f"the instructions must name {needle!r}: {out.getvalue()}"


def test_set_neon_key_refuses_to_prompt_at_all_without_an_org_id():
    def forbidden(*a, **k):
        raise AssertionError("must not prompt when the value cannot be validated")

    err = io.StringIO()
    with _sandbox(org=None) as path:
        with patch("getpass.getpass", forbidden), _no_echo(), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = neon._set_neon_key()

        assert code != 0
        assert "NEON_ORG_ID" in err.getvalue()
        assert not path.exists()


def test_set_neon_key_stores_nothing_when_the_prompt_comes_back_empty():
    err = io.StringIO()
    with _sandbox() as path:
        with patch.object(neon, "_open", _serve(200, b"{}")), _no_echo(), \
             patch("getpass.getpass", return_value="   "), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = neon._set_neon_key()

        assert code != 0
        assert not path.exists()


# ---------------------------------------------------------------------------
# The recovery command must actually run, not just read correctly. Same bug
# class this module's sibling hit three times: a documented fix that only
# resolved from one working directory.
# ---------------------------------------------------------------------------

_SET_KEY_RE = re.compile(r"python3\.12 (\S+) --set-neon-key")


def test_set_neon_key_cmd_embeds_an_absolute_path_derived_at_runtime():
    with _sandbox():
        try:
            neon._stored_key()
        except SourceUnavailable as exc:
            m = _SET_KEY_RE.search(str(exc))
            assert m, f"no 'python3.12 <path> --set-neon-key' command in: {exc}"
            assert os.path.isabs(m.group(1)), m.group(1)
        else:
            raise AssertionError("a missing key must raise SourceUnavailable")

    expected = Path(neon.__file__).resolve().parent.parent / "run.py"
    assert neon._RUN_PY == expected, (
        f"run.py must resolve from neon.py's own __file__: {neon._RUN_PY} != {expected}"
    )


def test_the_emitted_recovery_command_actually_runs_from_an_unrelated_cwd():
    with _sandbox():
        try:
            neon._stored_key()
        except SourceUnavailable as exc:
            path = _SET_KEY_RE.search(str(exc)).group(1)
        else:
            raise AssertionError("expected SourceUnavailable")

    assert os.path.isfile(path), f"the emitted path does not exist on disk: {path}"

    with tempfile.TemporaryDirectory() as unrelated_cwd:
        proc = subprocess.run(
            [sys.executable, path, "--set-neon-key"],
            cwd=unrelated_cwd,
            # Deliberately no NEON_ORG_ID and no NEON_API_KEY: the org-id
            # check fires before anything touches the key file, the network,
            # or a credential prompt.
            env={"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")},
            capture_output=True, text=True, timeout=30,
        )

    combined = proc.stdout + proc.stderr
    assert "No such file or directory" not in combined, combined
    assert "ImportError" not in combined, combined
    assert "Traceback" not in combined, combined
    assert proc.returncode == 2, (
        f"expected a clean exit 2 (missing NEON_ORG_ID), not a path failure: "
        f"returncode={proc.returncode}\n{combined}"
    )
    assert "NEON_ORG_ID" in combined, combined


def test_run_py_set_neon_key_dispatches_without_prompting():
    # The documented entry point. RECEIPTS_LOGIN_TEST_NOOP short-circuits
    # before the prompt or any network call, exactly as it does for
    # --set-session, so this stays hermetic.
    run_py = Path(neon.__file__).resolve().parent.parent / "run.py"
    with tempfile.TemporaryDirectory() as cwd:
        proc = subprocess.run(
            [sys.executable, str(run_py), "--set-neon-key"],
            cwd=cwd,
            env={"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
                 "RECEIPTS_LOGIN_TEST_NOOP": "1"},
            capture_output=True, text=True, timeout=30,
        )
    combined = proc.stdout + proc.stderr
    assert "Traceback" not in combined, combined
    assert proc.returncode == 0, combined
    assert "RECEIPTS_LOGIN_TEST_NOOP set" in combined, combined


def test_run_py_refuses_to_combine_set_neon_key_with_send():
    run_py = Path(neon.__file__).resolve().parent.parent / "run.py"
    with tempfile.TemporaryDirectory() as cwd:
        proc = subprocess.run(
            [sys.executable, str(run_py), "--set-neon-key", "--send"],
            cwd=cwd,
            env={"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
                 "RECEIPTS_LOGIN_TEST_NOOP": "1"},
            capture_output=True, text=True, timeout=30,
        )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 2, combined
    assert "--set-neon-key" in combined and "--send" in combined, combined


def test_run_py_refuses_to_store_both_credentials_in_one_invocation():
    # Two different credentials for two different sources. Doing both from
    # one invocation would prompt for two secrets back to back with no way to
    # tell which prompt is asking for which.
    run_py = Path(neon.__file__).resolve().parent.parent / "run.py"
    with tempfile.TemporaryDirectory() as cwd:
        proc = subprocess.run(
            [sys.executable, str(run_py), "--set-neon-key", "--set-session"],
            cwd=cwd,
            env={"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
                 "RECEIPTS_LOGIN_TEST_NOOP": "1"},
            capture_output=True, text=True, timeout=30,
        )
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 2, combined
    assert "--set-neon-key" in combined and "--set-session" in combined, combined


if __name__ == "__main__":
    print("Running neon API-key tests")
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            f(); print(f"  ok {n}")
    print("\nAll neon API-key tests passed.")

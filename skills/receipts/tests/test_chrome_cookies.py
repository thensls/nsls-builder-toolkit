"""Reading the claude.ai session out of Chrome, and trying it before the stored one.

Nothing here touches a real Chrome profile or the keychain: conftest sets the
opt-out for the whole suite, and the tests that exercise the Chrome path turn it
back off against a temp tree with a fake keychain.

Ciphertexts below were produced with the `openssl` CLI (an independent AES), not
with this module, so a bug in the decrypt can't be hidden by a matching bug in an
encrypt written beside it.
"""

import hashlib
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from sources import anthropic as anth
from sources import chrome_cookies as cc
from sources.base import SourceUnavailable

PASSWORD = "test-password"
VALUE = "sk-ant-sid01-FAKEVALUE"
OTHER = "sk-ant-sid01-OTHERVALUE"
# AES-128-CBC, key = PBKDF2-SHA1(PASSWORD, "saltysalt", 1003, 16), IV = 16 spaces.
V10_PLAIN = bytes.fromhex("0a702945a79364795349e867f4e28cbf041dfeac2e0449be60104386850f1d4d")
V10_HASHED = bytes.fromhex(
    "cba8d8b3b813f784aae46dea9258b58b3d19f5f789dc4778df01527afd73e93e"
    "9ebc4405b61caee4fc9db1e2d0d6c7253c3e7aca13c1c82f6fd27635488689a6")
V10_OTHER = bytes.fromhex("db18afebd803ffe9e7b24c5099ed616b55a7b86f2efe2479c1de688dec2d5f4d")


# ---- the AES itself ---------------------------------------------------------

def test_aes_matches_the_fips_197_block_vector():
    rk = cc._expand_key(bytes(range(16)))
    ct = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
    assert cc._decrypt_block(ct, rk).hex() == "00112233445566778899aabbccddeeff"


def test_aes_cbc_matches_the_nist_sp800_38a_vector():
    key = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
    iv = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    block = bytes.fromhex("7649abac8119b246cee98e9b12e9197d")
    plain = cc._decrypt_block(block, cc._expand_key(key))
    assert bytes(a ^ b for a, b in zip(plain, iv)).hex() == "6bc1bee22e409f96e93d7e117393172a"


def test_aes_rejects_a_ciphertext_that_is_not_whole_blocks():
    with pytest.raises(ValueError):
        cc.aes128_cbc_decrypt(bytes(16), b" " * 16, b"short")


# ---- decrypting a cookie ----------------------------------------------------

def test_decrypts_a_plain_v10_cookie():
    key = cc._derive_key(PASSWORD)
    assert cc.decrypt_cookie(b"v10" + V10_PLAIN, ".claude.ai", key) == VALUE


def test_strips_the_host_hash_chrome_prepends_in_newer_versions():
    key = cc._derive_key(PASSWORD)
    assert cc.decrypt_cookie(b"v10" + V10_HASHED, ".claude.ai", key) == VALUE


def test_a_hash_for_a_different_host_is_not_stripped_and_so_is_not_accepted():
    """The 32 hash bytes are binary, so leaving them in fails the text check —
    a value bound to another host must not come out as a usable session."""
    key = cc._derive_key(PASSWORD)
    with pytest.raises(ValueError):
        cc.decrypt_cookie(b"v10" + V10_HASHED, "other.example", key)


def test_the_wrong_password_is_an_error_not_a_garbage_session():
    wrong = cc._derive_key("not-the-password")
    with pytest.raises(ValueError):
        cc.decrypt_cookie(b"v10" + V10_PLAIN, ".claude.ai", wrong)


def test_a_non_v10_cookie_is_refused():
    with pytest.raises(ValueError):
        cc.decrypt_cookie(b"v11" + V10_PLAIN, ".claude.ai", cc._derive_key(PASSWORD))


# ---- finding it in a profile ------------------------------------------------

def _profile(root: Path, name: str, rows, nested=True) -> Path:
    d = root / name / ("Network" if nested else "")
    d.mkdir(parents=True)
    conn = sqlite3.connect(d / "Cookies")
    conn.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, encrypted_value BLOB, "
                 "last_access_utc INTEGER)")
    conn.executemany("INSERT INTO cookies VALUES (?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return d / "Cookies"


@pytest.fixture
def chrome(tmp_path, monkeypatch):
    """A temp Chrome tree with the browser path enabled and a fake keychain."""
    monkeypatch.delenv(cc.DISABLE_ENV, raising=False)
    monkeypatch.setattr(cc.sys, "platform", "darwin")
    monkeypatch.setattr(cc, "CHROME_DIR", str(tmp_path))
    monkeypatch.setattr(cc, "_keychain_password", lambda: PASSWORD)
    return tmp_path


def test_the_opt_out_skips_chrome_entirely_and_says_nothing(chrome, monkeypatch):
    _profile(chrome, "Default", [(".claude.ai", "sessionKey", b"v10" + V10_PLAIN, 5)])
    monkeypatch.setenv(cc.DISABLE_ENV, "1")
    assert cc.claude_sessions() == ([], None)


def test_finds_the_session_in_a_profile(chrome):
    _profile(chrome, "Default", [(".claude.ai", "sessionKey", b"v10" + V10_PLAIN, 5)])
    assert cc.claude_sessions() == ([VALUE], None)


def test_reads_the_older_flat_cookie_layout_too(chrome):
    _profile(chrome, "Default", [(".claude.ai", "sessionKey", b"v10" + V10_PLAIN, 5)],
             nested=False)
    assert cc.claude_sessions()[0] == [VALUE]


def test_most_recently_used_profile_is_tried_first(chrome):
    _profile(chrome, "Default", [(".claude.ai", "sessionKey", b"v10" + V10_OTHER, 100)])
    _profile(chrome, "Profile 1", [(".claude.ai", "sessionKey", b"v10" + V10_PLAIN, 900)])
    assert cc.claude_sessions()[0] == [VALUE, OTHER]


def test_the_same_session_in_two_profiles_is_returned_once(chrome):
    row = (".claude.ai", "sessionKey", b"v10" + V10_PLAIN, 1)
    _profile(chrome, "Default", [row])
    _profile(chrome, "Profile 1", [row])
    assert cc.claude_sessions()[0] == [VALUE]


def test_only_the_claude_ai_sessionkey_is_ever_selected(chrome):
    _profile(chrome, "Default", [
        (".claude.ai", "otherCookie", b"v10" + V10_OTHER, 9),
        (".example.com", "sessionKey", b"v10" + V10_OTHER, 9),
        (".claude.ai", "sessionKey", b"v10" + V10_PLAIN, 1),
    ])
    assert cc.claude_sessions()[0] == [VALUE]


def test_a_profile_not_signed_in_says_so_in_words(chrome):
    _profile(chrome, "Default", [])
    values, note = cc.claude_sessions()
    assert values == [] and "signed in to claude.ai" in note


def test_no_chrome_at_all_says_so_and_does_not_raise(tmp_path, monkeypatch):
    monkeypatch.delenv(cc.DISABLE_ENV, raising=False)
    monkeypatch.setattr(cc.sys, "platform", "darwin")
    monkeypatch.setattr(cc, "CHROME_DIR", str(tmp_path / "nope"))
    values, note = cc.claude_sessions()
    assert values == [] and "no Chrome profile" in note


def test_a_denied_keychain_is_a_note_not_a_failure(chrome, monkeypatch):
    _profile(chrome, "Default", [(".claude.ai", "sessionKey", b"v10" + V10_PLAIN, 5)])

    def denied():
        raise RuntimeError("macOS did not give access to Chrome's keychain item")
    monkeypatch.setattr(cc, "_keychain_password", denied)
    values, note = cc.claude_sessions()
    assert values == [] and "keychain" in note


def test_a_corrupt_cookie_is_a_note_not_a_crash(chrome):
    _profile(chrome, "Default", [(".claude.ai", "sessionKey", b"v10" + b"\x01" * 16, 5)])
    values, note = cc.claude_sessions()
    assert values == [] and "could not be decrypted" in note


def test_the_notes_never_contain_a_session_value(chrome):
    _profile(chrome, "Default", [(".claude.ai", "sessionKey", b"v10" + b"\x01" * 16, 5)])
    _values, note = cc.claude_sessions()
    assert VALUE not in note and OTHER not in note


def test_the_live_database_is_left_untouched_and_no_copy_is_left_behind(chrome, tmp_path):
    db = _profile(chrome, "Default", [(".claude.ai", "sessionKey", b"v10" + V10_PLAIN, 5)])
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    leftovers = set(Path(__import__("tempfile").gettempdir()).glob("receipts-cookies-*"))
    cc.claude_sessions()
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    assert set(Path(__import__("tempfile").gettempdir()).glob("receipts-cookies-*")) == leftovers


def test_non_macos_is_unsupported_and_says_so(monkeypatch):
    monkeypatch.delenv(cc.DISABLE_ENV, raising=False)
    monkeypatch.setattr(cc.sys, "platform", "win32")
    values, note = cc.claude_sessions()
    assert values == [] and "macOS" in note


# ---- the order the Anthropic source tries them in ---------------------------

class _Listing:
    """A fake _fetch_listing: the sessions in `good` work, every other is expired."""
    def __init__(self, good):
        self.good, self.tried = set(good), []

    def __call__(self, org, session, page="", limit=100):
        self.tried.append(session)
        if session not in self.good:
            raise anth.SessionExpired("The stored claude.ai session has expired")
        return {"invoices": []}


@pytest.fixture
def source(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_ORG_UUID", "org-test")
    monkeypatch.delenv("CLAUDE_SESSION_KEY", raising=False)
    monkeypatch.setattr(anth, "SESSION_FILE", str(tmp_path / "stored"))
    return anth.AnthropicSource()


def _stored(tmp_path, value):
    p = tmp_path / "stored"
    p.write_text(value)
    p.chmod(0o600)


def test_chrome_is_tried_before_the_stored_session(source, tmp_path):
    _stored(tmp_path, "STORED")
    fake = _Listing(good={"FROMCHROME", "STORED"})
    with patch.object(anth, "_chrome_sessions", return_value=(["FROMCHROME"], None)), \
            patch.object(anth, "_fetch_listing", fake):
        source._listing()
    assert fake.tried == ["FROMCHROME"] and source.session_source == "chrome"


def test_a_dead_chrome_session_falls_through_to_the_stored_one(source, tmp_path):
    _stored(tmp_path, "STORED")
    fake = _Listing(good={"STORED"})
    with patch.object(anth, "_chrome_sessions", return_value=(["STALE"], None)), \
            patch.object(anth, "_fetch_listing", fake):
        source._listing()
    assert fake.tried == ["STALE", "STORED"] and source.session_source == "stored"


def test_the_explicit_environment_session_is_used_alone(source, tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_SESSION_KEY", "ENVVALUE")
    _stored(tmp_path, "STORED")
    fake = _Listing(good={"STORED"})
    with patch.object(anth, "_chrome_sessions", return_value=(["FROMCHROME"], None)) as chrome_fn, \
            patch.object(anth, "_fetch_listing", fake):
        with pytest.raises(SourceUnavailable):
            source._listing()
    assert fake.tried == ["ENVVALUE"] and not chrome_fn.called


def test_only_a_dead_session_falls_through_not_a_cloudflare_or_permission_failure(source, tmp_path):
    """A challenge or an admin-403 says nothing about whether another credential
    would work; trying more would bury the real cause."""
    _stored(tmp_path, "STORED")
    calls = []

    def blocked(org, session, page="", limit=100):
        calls.append(session)
        raise SourceUnavailable("Cloudflare challenged the request")
    with patch.object(anth, "_chrome_sessions", return_value=(["FROMCHROME"], None)), \
            patch.object(anth, "_fetch_listing", blocked):
        with pytest.raises(SourceUnavailable, match="Cloudflare"):
            source._listing()
    assert calls == ["FROMCHROME"]


def test_everything_dead_reports_expiry_with_what_was_tried_and_the_recovery(source, tmp_path):
    _stored(tmp_path, "STORED")
    with patch.object(anth, "_chrome_sessions", return_value=(["STALE"], None)), \
            patch.object(anth, "_fetch_listing", _Listing(good=set())):
        with pytest.raises(anth.SessionExpired) as err:
            source._listing()
    msg = str(err.value)
    assert "expired" in msg and "chrome" in msg and "stored" in msg
    assert anth.SET_SESSION_CMD in msg


def test_no_chrome_and_no_stored_session_keeps_the_original_recovery_message(source):
    with patch.object(anth, "_chrome_sessions", return_value=([], "no Chrome profile was found")):
        with pytest.raises(SourceUnavailable) as err:
            source._listing()
    msg = str(err.value)
    assert anth.SET_SESSION_CMD in msg and "no Chrome profile was found" in msg


def test_without_chrome_behaviour_is_exactly_the_old_stored_session_path(source, tmp_path):
    _stored(tmp_path, "STORED")
    fake = _Listing(good={"STORED"})
    with patch.object(anth, "_chrome_sessions", return_value=([], None)), \
            patch.object(anth, "_fetch_listing", fake):
        source._listing()
    assert fake.tried == ["STORED"]


def test_a_fetch_reuses_the_proven_session_across_pages_and_forgets_it_after(source, tmp_path):
    _stored(tmp_path, "STORED")
    pages = [{"invoices": [], "has_more": True, "next_page": "p1"}, {"invoices": []}]
    calls = []

    def listing(org, session, page="", limit=100):
        calls.append(session)
        return pages.pop(0)
    chrome_fn = patch.object(anth, "_chrome_sessions", return_value=(["FROMCHROME"], None))
    with chrome_fn as chrome_mock, patch.object(anth, "_fetch_listing", listing):
        source.fetch("2026-01-01", "2026-12-31")
    assert calls == ["FROMCHROME", "FROMCHROME"] and chrome_mock.call_count == 1
    assert source._session is None  # not left behind on the singleton


def test_a_direct_listing_call_leaves_no_session_on_the_source(source, tmp_path):
    _stored(tmp_path, "STORED")
    with patch.object(anth, "_chrome_sessions", return_value=(["FROMCHROME"], None)), \
            patch.object(anth, "_fetch_listing", _Listing(good={"FROMCHROME"})):
        source._listing()
    assert source._session is None

#!/usr/bin/env python3.12
"""Read the claude.ai `sessionKey` out of the user's own Chrome (macOS only).

WHY THIS EXISTS
---------------
The Anthropic billing source needs a claude.ai session, and a hand-copied
cookie goes stale on claude.ai's schedule, not the builder's. Chrome is already
signed in and keeps that session fresh every time the builder uses claude.ai, so
reading it from there removes the recurring paste. The paste (`--set-session`)
stays as the fallback for machines with no Chrome, no keychain access, or no
signed-in profile.

WHAT IT TOUCHES
---------------
* Chrome's cookie database for each profile — COPIED to a private temp
  directory first (Chrome holds the original open) and read from the copy.
* One macOS keychain item, "Chrome Safe Storage", which holds the password
  Chrome encrypts cookies with. The first run makes macOS ask for permission;
  "Always Allow" makes it silent from then on. Denying it is fine: the source
  falls back to the stored session and says so.
* Only cookies named `sessionKey` on claude.ai. No other cookie is selected,
  decrypted, or kept.

THE VALUE IS A CREDENTIAL
-------------------------
Same rules as sources/anthropic.py: it is never printed, logged, or put in an
exception or report line. Every message this module produces describes WHAT
happened (no profile, keychain denied, decrypt failed) and never carries a
value. The temp copy of the cookie database is deleted before returning.

THE CRYPTO
----------
Chrome on macOS encrypts a cookie as `b"v10" + AES-128-CBC(key, iv, value)`,
with key = PBKDF2-HMAC-SHA1(keychain password, b"saltysalt", 1003, 16) and an
IV of sixteen spaces. The standard library has no AES, and the toolkit
deliberately takes no pip dependency, and the `openssl` CLI would need the key on
its command line (visible in `ps`). So this file carries a small DECRYPT-ONLY
AES-128 — checked against the FIPS-197 and NIST SP 800-38A vectors in
tests/test_chrome_cookies.py. It decrypts a ~100-byte local value; it is not a
general-purpose crypto library and must not grow into one.
"""

import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

# Opt-out. Set to anything non-empty to skip Chrome entirely (the test suite
# sets it so no test can ever reach a real browser profile or the keychain).
DISABLE_ENV = "RECEIPTS_NO_BROWSER_SESSION"

# Deliberately stored unexpanded and expanded at use time (same reason as
# SESSION_FILE in anthropic.py): tests point this at a temp tree.
CHROME_DIR = "~/Library/Application Support/Google/Chrome"
KEYCHAIN_SERVICE = "Chrome Safe Storage"
KEYCHAIN_ACCOUNT = "Chrome"
# macOS shows a permission dialog on the first read; give a human time to answer.
KEYCHAIN_TIMEOUT_SECONDS = 120

_HOSTS = ("claude.ai", ".claude.ai")
_COOKIE = "sessionKey"
_PRINTABLE = re.compile(r"[\x21-\x7e]+")


# ---------------------------------------------------------------------------
# Decrypt-only AES-128
# ---------------------------------------------------------------------------

def _build_sboxes() -> tuple[list[int], list[int]]:
    sbox = [0] * 256
    p = q = 1
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)   # p *= 3 in GF(2^8)
        q ^= (q << 1) & 0xFF                                    # q /= 3 in GF(2^8)
        q ^= (q << 2) & 0xFF
        q ^= (q << 4) & 0xFF
        if q & 0x80:
            q ^= 0x09
        rot = lambda v, n: ((v << n) | (v >> (8 - n))) & 0xFF
        sbox[p] = q ^ rot(q, 1) ^ rot(q, 2) ^ rot(q, 3) ^ rot(q, 4) ^ 0x63
        if p == 1:
            break
    sbox[0] = 0x63
    inv = [0] * 256
    for i, v in enumerate(sbox):
        inv[v] = i
    return sbox, inv


_SBOX, _INV_SBOX = _build_sboxes()


def _gmul(a: int, b: int) -> int:
    out = 0
    while b:
        if b & 1:
            out ^= a
        a = ((a << 1) & 0xFF) ^ (0x1B if a & 0x80 else 0)
        b >>= 1
    return out


def _expand_key(key: bytes) -> list[list[int]]:
    """AES-128 key schedule -> 11 round keys of 16 bytes."""
    if len(key) != 16:
        raise ValueError("AES-128 key must be 16 bytes")
    words = [list(key[i:i + 4]) for i in range(0, 16, 4)]
    rcon = 1
    for i in range(4, 44):
        t = list(words[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [_SBOX[b] for b in t]
            t[0] ^= rcon
            rcon = ((rcon << 1) & 0xFF) ^ (0x1B if rcon & 0x80 else 0)
        words.append([words[i - 4][j] ^ t[j] for j in range(4)])
    return [sum(words[r * 4:r * 4 + 4], []) for r in range(11)]


def _decrypt_block(block: bytes, round_keys: list[list[int]]) -> bytes:
    s = [b ^ k for b, k in zip(block, round_keys[10])]
    for rnd in range(9, -1, -1):
        # InvShiftRows: state is column-major, byte index = row + 4*col.
        t = [0] * 16
        for r in range(4):
            for c in range(4):
                t[r + 4 * ((c + r) % 4)] = s[r + 4 * c]
        s = [_INV_SBOX[b] for b in t]                                   # InvSubBytes
        s = [b ^ k for b, k in zip(s, round_keys[rnd])]                 # AddRoundKey
        if rnd:
            m = [0] * 16                                                # InvMixColumns
            for c in range(4):
                a0, a1, a2, a3 = s[4 * c:4 * c + 4]
                m[4 * c + 0] = _gmul(a0, 14) ^ _gmul(a1, 11) ^ _gmul(a2, 13) ^ _gmul(a3, 9)
                m[4 * c + 1] = _gmul(a0, 9) ^ _gmul(a1, 14) ^ _gmul(a2, 11) ^ _gmul(a3, 13)
                m[4 * c + 2] = _gmul(a0, 13) ^ _gmul(a1, 9) ^ _gmul(a2, 14) ^ _gmul(a3, 11)
                m[4 * c + 3] = _gmul(a0, 11) ^ _gmul(a1, 13) ^ _gmul(a2, 9) ^ _gmul(a3, 14)
            s = m
    return bytes(s)


def aes128_cbc_decrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    """AES-128-CBC decrypt with PKCS#7 unpadding. Raises ValueError on bad input."""
    if not data or len(data) % 16 or len(iv) != 16:
        raise ValueError("ciphertext is not a whole number of AES blocks")
    round_keys = _expand_key(key)
    out, prev = bytearray(), iv
    for i in range(0, len(data), 16):
        block = data[i:i + 16]
        plain = _decrypt_block(block, round_keys)
        out += bytes(a ^ b for a, b in zip(plain, prev))
        prev = block
    pad = out[-1]
    if not 1 <= pad <= 16 or bytes(out[-pad:]) != bytes([pad]) * pad:
        raise ValueError("bad padding — wrong key or corrupt value")
    return bytes(out[:-pad])


# ---------------------------------------------------------------------------
# Chrome
# ---------------------------------------------------------------------------

def _derive_key(password: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha1", password.encode(), b"saltysalt", 1003, 16)


def decrypt_cookie(encrypted_value: bytes, host_key: str, key: bytes) -> str:
    """Decrypt one Chrome-for-macOS cookie value. Raises ValueError if it can't."""
    if not encrypted_value.startswith(b"v10"):
        raise ValueError("not a v10 (macOS keychain) cookie")
    plain = aes128_cbc_decrypt(key, b" " * 16, encrypted_value[3:])
    # Chrome >= 24 prepends SHA-256(host_key) to the plaintext to bind the value
    # to its host. Strip it when (and only when) it is really there.
    if len(plain) > 32 and plain[:32] == hashlib.sha256(host_key.encode()).digest():
        plain = plain[32:]
    try:
        text = plain.decode("ascii").strip()
    except UnicodeDecodeError:
        raise ValueError("decrypted value is not text — wrong key") from None
    if not _PRINTABLE.fullmatch(text):
        raise ValueError("decrypted value is not a cookie string — wrong key")
    return text


def _keychain_password() -> str:
    """Chrome's cookie password from the macOS keychain. Raises RuntimeError.

    The password is passed to nothing but PBKDF2 in this process; it is never
    printed or put in a command line (`security -w` writes it to our pipe).
    """
    try:
        proc = subprocess.run(
            ["security", "find-generic-password", "-w",
             "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT],
            capture_output=True, text=True, timeout=KEYCHAIN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise RuntimeError("the macOS keychain permission prompt for "
                           "\"Chrome Safe Storage\" was not answered in time") from None
    except OSError as exc:
        raise RuntimeError(f"could not run the macOS `security` tool "
                           f"({type(exc).__name__})") from None
    pw = proc.stdout.strip()
    if proc.returncode != 0 or not pw:
        raise RuntimeError("macOS did not give access to Chrome's \"Chrome Safe "
                           "Storage\" keychain item (denied, or Chrome has never "
                           "run here)")
    return pw


def _cookie_dbs(chrome_dir: Path) -> list[Path]:
    out = []
    for profile in sorted(chrome_dir.iterdir()) if chrome_dir.is_dir() else []:
        if not (profile.name == "Default" or profile.name.startswith("Profile ")):
            continue
        for rel in ("Network/Cookies", "Cookies"):
            db = profile / rel
            if db.is_file():
                out.append(db)
                break
    return out


def _uri(path: Path, mode: str) -> str:
    # quote(): Chrome's real path contains a space ("Application Support"), which
    # a bare `file:` URI does not reliably survive.
    return f"file:{quote(str(path))}?mode={mode}"


def _snapshot(db: Path, copy: Path) -> None:
    """Make `copy` a consistent, private snapshot of Chrome's live cookie DB.

    Preferred: SQLite's own backup API from a read-only connection. Chrome writes
    and checkpoints this file while it runs, so copying the main file and its
    -wal/-shm as three separate steps can capture a database and a log from
    different moments — a snapshot that fails to open or reads wrong, which used
    to discard a perfectly good signed-in profile. The backup API reads under
    SQLite's own locking and is consistent by construction.

    Fallback: if the backup itself fails (the live file is busy or locked right
    now), copy the files instead — a possibly-torn snapshot beats none, and
    anything unreadable is still reported by the caller as a note, not a crash.
    """
    try:
        source = sqlite3.connect(_uri(db, "ro"), uri=True, timeout=5)
        try:
            target = sqlite3.connect(copy)
            try:
                source.backup(target)
            finally:
                target.close()
        finally:
            source.close()
        return
    except sqlite3.Error:
        if copy.exists():
            copy.unlink()
    shutil.copy2(db, copy)
    for suffix in ("-wal", "-shm", "-journal"):
        side = Path(str(db) + suffix)
        if side.is_file():
            shutil.copy2(side, Path(str(copy) + suffix))


def _read_rows(db: Path) -> list[tuple]:
    """(host_key, encrypted_value, last_access_utc) for claude.ai sessionKey rows.

    Reads a private snapshot, never the live file: Chrome keeps it open, and
    querying it directly can fail or interfere with the running browser.
    """
    with tempfile.TemporaryDirectory(prefix="receipts-cookies-") as tmp:
        os.chmod(tmp, 0o700)
        copy = Path(tmp) / "Cookies"
        _snapshot(db, copy)
        conn = sqlite3.connect(_uri(copy, "ro"), uri=True)
        try:
            return conn.execute(
                "SELECT host_key, encrypted_value, last_access_utc FROM cookies "
                "WHERE name = ? AND host_key IN (?, ?)", (_COOKIE, *_HOSTS)).fetchall()
        finally:
            conn.close()


def claude_sessions() -> tuple[list[str], str | None]:
    """Candidate claude.ai session values from Chrome, freshest first.

    Returns (values, note). `note` says, in words and never with a value, why
    the list is empty or short — None when there is nothing worth saying (the
    opt-out is set, or it simply worked). Never raises: an unreadable Chrome is
    an unavailable convenience, not a failed run, because the stored session is
    still behind it.
    """
    if os.environ.get(DISABLE_ENV):
        return [], None
    if sys.platform != "darwin":
        return [], "reading the session from Chrome is only supported on macOS"

    chrome_dir = Path(os.path.expanduser(CHROME_DIR))
    try:
        dbs = _cookie_dbs(chrome_dir)
    except OSError:
        # Unlistable (permissions, or a profile directory vanishing mid-scan).
        # Same contract as every other failure here: a note, never a raise —
        # the stored session is still behind this one.
        return [], "Chrome's profile folder could not be listed"
    if not dbs:
        return [], "no Chrome profile was found on this Mac"

    found: list[tuple[int, bytes, str]] = []
    problems = 0
    for db in dbs:
        try:
            for host, enc, last in _read_rows(db):
                if enc:
                    found.append((int(last or 0), bytes(enc), host))
        except (OSError, sqlite3.Error):
            problems += 1
    if not found:
        why = (f"{problems} Chrome profile(s) could not be read" if problems else
               "no Chrome profile is signed in to claude.ai")
        return [], why

    try:
        key = _derive_key(_keychain_password())
    except RuntimeError as exc:
        return [], str(exc)

    values: list[str] = []
    undecryptable = 0
    for _last, enc, host in sorted(found, key=lambda r: r[0], reverse=True):
        try:
            value = decrypt_cookie(enc, host, key)
        except ValueError:
            undecryptable += 1
            continue
        if value not in values:
            values.append(value)
    note = None
    if not values:
        note = (f"Chrome has a claude.ai session but it could not be decrypted "
                f"({undecryptable} cookie(s)) — Chrome's encryption may have changed")
    return values, note

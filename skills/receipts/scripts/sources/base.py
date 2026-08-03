#!/usr/bin/env python3.12
"""Contract every receipt source implements."""

import hashlib
import importlib
import os
import pkgutil
import re
import stat
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path


class SourceUnavailable(Exception):
    """Source could not run — auth, network, config. Never a match failure."""


# ---------------------------------------------------------------------------
# Stored credentials
#
# Two sources now hold a long-lived secret on disk (a claude.ai session, a
# Neon API key) and both have exactly the same obligations: refuse a file
# other accounts can read, write atomically at 0600, and never let the value
# reach a message. Those three things live here so the two sources cannot
# drift apart on them — the messages stay per-source, because "the stored
# claude.ai session expired" and "re-issue this as an organization API key"
# are different instructions and must not be homogenised.
# ---------------------------------------------------------------------------

SECRET_MODE = 0o600
# Any group or other permission bit at all. Read is the dangerous one, but a
# credential file nobody else should touch has no business being group-
# writable or executable either.
UNSAFE_MODE_BITS = stat.S_IRWXG | stat.S_IRWXO


def scrub_secret(text, secret: str | None) -> str:
    """Defensive redaction. No source deliberately interpolates a credential
    into a message — but text that arrives from elsewhere (an OSError, a
    urllib exception, a server's own error body) can carry anything, and it
    is about to be shown to a user or written to a log. Assume any string
    being interpolated may reach a log and take the secret out of it first.
    """
    out = str(text)
    if secret:
        out = out.replace(secret, "<redacted credential>")
    return out


def secret_file_mode(path: Path) -> int:
    """The file's permission bits. Raises OSError like stat() does."""
    return stat.S_IMODE(path.stat().st_mode)


def secret_file_is_unsafe(mode: int) -> bool:
    return bool(mode & UNSAFE_MODE_BITS)


def write_secret_file(value: str, path: Path, prefix: str) -> None:
    """Write a credential atomically at mode 0600.

    Same shape as the ledger's write: a temp file in the *destination
    directory* (os.replace is only atomic within one filesystem), permissions
    set on the file descriptor before a single byte of the secret is written,
    then an atomic rename. A half-written credential file would fail
    confusingly on the next run; a briefly world-readable one would be a leak.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=prefix)
    try:
        os.fchmod(fd, SECRET_MODE)
        with os.fdopen(fd, "w") as fh:
            fh.write(value + "\n")
        os.chmod(tmp, SECRET_MODE)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


@dataclass(frozen=True)
class Receipt:
    merchant: str        # normalized
    amount_cents: int
    date: str            # ISO yyyy-mm-dd
    pdf_bytes: bytes
    provenance: str      # e.g. "anthropic:invoice 2026-07-19 108500"


def normalize_merchant(name: str) -> str:
    """Fold a merchant name to a comparable key.

    Two failures the naive `[^a-z0-9]` strip produced, both silent:

    * Accented Latin lost its letters instead of folding them. Ramp's
      "München" became "mnchen" while a receipt's "Munchen" became "munchen",
      so a real receipt for a real charge came back UNFOUND. NFKD decomposes
      the letter into base + combining mark; dropping only the marks keeps
      the base letter.
    * Merchants written entirely in a non-Latin script collapsed to "" — and
      so compared EQUAL to every other such merchant, and to a blank name.
      That is the dangerous direction: equal keys make one vendor's receipt an
      automatic upload against another vendor's charge. When nothing survives
      the fold, fall back to a per-name key that only ever equals itself.

    The result is always [a-z0-9]*, so normalize_merchant is idempotent —
    match.py re-normalizes already-normalized Receipt.merchant values.
    """
    decomposed = unicodedata.normalize("NFKD", name or "")
    folded = "".join(c for c in decomposed if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]", "", folded.lower())
    if slug:
        return slug

    # Nothing survived. A name that is genuinely blank stays blank — there is
    # no merchant to distinguish. A name with real content gets a stable,
    # process-independent sentinel built only from [a-z0-9], so re-normalizing
    # it is a no-op and no two different names can ever collide into "".
    stripped = " ".join((name or "").split())
    if not stripped:
        return ""
    return "x" + hashlib.sha1(stripped.casefold().encode("utf-8")).hexdigest()[:16]


def load_sources(errors: list | None = None) -> list:
    """Every sources/*.py module exposing a SOURCE singleton.

    One source failing at import — a missing dependency, a syntax error, a
    module-level side effect that raises — must not end discovery for the
    others. Failures are appended to `errors` as "NAME: reason" so the caller
    can announce them the same way it announces a source that was skipped at
    fetch time. Swallowing them silently would leave a run that found fewer
    receipts than it should looking exactly like a clean one.
    """
    import sources

    found = []
    for mod in pkgutil.iter_modules(sources.__path__):
        if mod.name == "base":
            continue
        try:
            module = importlib.import_module(f"sources.{mod.name}")
        except Exception as exc:
            if errors is not None:
                errors.append(f"{mod.name.upper()}: import failed — {type(exc).__name__}: {exc}")
            continue
        if hasattr(module, "SOURCE"):
            found.append(module.SOURCE)
    return found

"""Shared test setup.

The Anthropic source retries a Cloudflare challenge with a real backoff. That
is correct in production and wrong in a unit suite: every test that simulates a
challenge would sit through the wait, which took this suite from ~2s to ~97s.
Zero the backoff everywhere instead of shortening it in prod — the retry LOGIC
is what the tests are for, and the durations are a live-behaviour choice that no
test should silently redefine.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture(autouse=True)
def _no_cloudflare_backoff(monkeypatch):
    from sources import anthropic as anth
    monkeypatch.setattr(anth, "_CF_BACKOFF_SECONDS", (0, 0, 0), raising=False)


@pytest.fixture(autouse=True)
def _no_real_browser_session(monkeypatch):
    """No test may ever reach a real Chrome profile or the macOS keychain.

    The Anthropic source now reads the session from Chrome before the stored
    file. On a builder's Mac that would make every session test depend on whoever
    is signed in to claude.ai in their browser, and prompt the keychain mid-run.
    Tests that exercise the Chrome path opt back in explicitly and point it at a
    temp tree with a fake keychain.
    """
    monkeypatch.setenv("RECEIPTS_NO_BROWSER_SESSION", "1")

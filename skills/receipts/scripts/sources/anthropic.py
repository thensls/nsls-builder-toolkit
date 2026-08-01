#!/usr/bin/env python3.12
"""Anthropic (claude.ai) billing source.

Anthropic emails receipts for the subscription charges but NOTHING for
usage-credit auto-recharges — those are 15 of the 22 gaps. The listing call
needs a claude.ai session; the PDF URLs it returns are Stripe secret-token URLs
that resolve with no authentication at all (verified 2026-08-01).

ANTHROPIC_ORG_UUID must be set in the environment — this module ships in an
org-wide toolkit and must never default to one specific organisation's ID.
Playwright is an optional runtime prerequisite (not a declared dependency of
this toolkit); when it's missing, this source degrades to SourceUnavailable
instead of raising ModuleNotFoundError, so a missing Playwright install only
takes out the Anthropic source, not the whole /receipts run.

Both `_login()` and `_listing()` drive real, installed Google Chrome
(`channel="chrome"`) instead of Playwright's bundled Chromium — Cloudflare
fingerprints bundled Chromium (navigator.webdriver, CDP artifacts) and serves
an endless verification loop for it. Google Chrome should be installed on
this machine. If it isn't, `_launch_context()` falls back to bundled
Chromium and prints a loud warning explaining why the Cloudflare loop may
still happen and that installing Chrome is the fix — never silently, since a
silent fallback lands the user right back in the loop with no idea why.
"""

import datetime as dt
import hashlib
import json
import os
import sys
import urllib.request

try:
    from .base import Receipt, SourceUnavailable
except ImportError:
    # Running this file directly (`python3.12 sources/anthropic.py --login`)
    # gives it no parent package, so the relative import above fails with
    # "attempted relative import with no known parent package" — before this
    # module's own `if __name__ == "__main__":` block at the bottom ever
    # runs. That command used to be exactly what the SourceUnavailable
    # message below and SKILL.md told a user to run for a dead claude.ai
    # session, so the fix for the failure was itself unreachable. `run.py
    # --login` is the documented entry point now (it already resolves
    # imports correctly), but this direct-script form may still be in
    # someone's notes or muscle memory — make it work too: put this file's
    # parent directory (the `scripts/` dir) on sys.path so `sources` is
    # importable as a real top-level package, then import the same module
    # absolutely. `python3.12 -m sources.anthropic --login` already runs with
    # a package context, so this branch never triggers there.
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from sources.base import Receipt, SourceUnavailable

LISTING = "https://claude.ai/api/stripe/{org}/invoices?limit=100&page={page}"
PROFILE = os.path.expanduser("~/.claude-receipts-profile")
PAGE_GUARD = 20  # pages (100 invoices/page = 2,000 invoices) — see fetch()

# Cloudflare fingerprints Playwright's bundled Chromium (navigator.webdriver,
# CDP artifacts) and serves an endless verification loop for it. Real, fully
# installed Chrome does not trip the same fingerprint. This flag is the most
# obvious remaining automation signal once channel="chrome" is in play.
_ANTI_AUTOMATION_ARGS = ["--disable-blink-features=AutomationControlled"]

# Cloudflare challenge pages (the "Just a moment…" interstitial and its
# variants) reliably contain one of these markers in the body, or set one of
# these response headers on the mitigated request. Neither is guaranteed to
# be exhaustive — Cloudflare changes challenge markup over time — but this
# covers the documented, currently-observed forms.
_CF_BODY_MARKERS = ("cf-chl", "just a moment", "attention required! | cloudflare",
                    "challenge-platform")
_CF_HEADER_MARKERS = ("cf-mitigated", "cf-chl-bypass")


def _launch_context(p, *, headless: bool):
    """Launch the persistent Playwright context, preferring the user's real,
    installed Google Chrome over Playwright's bundled Chromium.

    `channel="chrome"` tells Playwright to drive the actual Chrome install on
    this machine instead of its own bundled build; Playwright resolves the
    executable itself, so this never hardcodes an install path — this
    toolkit ships org-wide, and the path differs by OS and user.

    Not every machine has Chrome installed, though, and this ships to
    colleagues who may not have it. If the chrome-channel launch fails for
    any reason, fall back to bundled Chromium — but never silently: a silent
    fallback launches Chromium, Cloudflare challenges it the same way it
    always has, and the user lands right back in the infinite-verification
    loop with zero idea why. So the fallback prints a loud, specific warning
    naming the cause and the remedy every time it fires.
    """
    try:
        return p.chromium.launch_persistent_context(
            PROFILE, headless=headless, channel="chrome", args=_ANTI_AUTOMATION_ARGS,
        )
    except Exception as exc:
        print(
            f"WARNING: could not launch Google Chrome ({type(exc).__name__}: {exc}). "
            "Falling back to Playwright's bundled Chromium for the Anthropic "
            "billing source. Cloudflare fingerprints bundled Chromium and may "
            "serve an endless verification loop instead of letting the login "
            "through. Install Google Chrome (https://www.google.com/chrome/) "
            "to fix this.",
            file=sys.stderr,
        )
        return p.chromium.launch_persistent_context(
            PROFILE, headless=headless, args=_ANTI_AUTOMATION_ARGS,
        )


def _is_cloudflare_challenge(resp) -> bool:
    """True when `resp` looks like a Cloudflare bot-detection challenge
    rather than a genuine response from claude.ai — a 403 whose body is the
    Cloudflare interstitial page, or a response carrying one of Cloudflare's
    own mitigation headers. Distinguishing this from a real 401 (expired
    session) or a real 403 (not an org admin) matters: telling someone stuck
    in a Cloudflare loop to "log in again" sends them right back into the
    same loop, and telling an org-admin user their session merely expired
    hides the one fact — a fingerprinted automated browser — they can
    actually act on.
    """
    if resp is None:
        return False
    headers = getattr(resp, "headers", None) or {}
    header_blob = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
    if any(marker in header_blob for marker in _CF_HEADER_MARKERS):
        return True
    if resp.status == 403:
        try:
            body = (resp.text() or "").lower()
        except Exception:
            body = ""
        if any(marker in body for marker in _CF_BODY_MARKERS):
            return True
    return False


class AnthropicSource:
    MERCHANTS = ("anthropic", "anthropicpbc")
    # Set during fetch() to a human-readable reason whenever this source
    # returned LESS than it was asked for but did not fail outright: the page
    # guard fired with more pages pending, the cursor went missing, or an
    # invoice PDF could not be downloaded. None otherwise. run.py reads it via
    # getattr and prints "SOURCE ANTHROPIC: TRUNCATED (...)" — the same channel
    # GmailSource already uses. Without it, a partial search returns quietly
    # and every unmatched transaction reads as a genuine gap.
    truncated: str | None = None

    def parse_invoices(self, payload: dict) -> list[dict]:
        rows = []
        for inv in payload.get("invoices", []):
            if inv.get("status") != "paid" or not inv.get("invoice_pdf_url"):
                continue
            date = dt.datetime.fromtimestamp(inv["created_ts"], dt.UTC).date().isoformat()
            # invoice_pdf_url is unique per invoice (…/live_A/pdf vs …/live_B/pdf).
            # Fold a stable, deterministic slice of it into provenance so that
            # same-date, same-amount invoices — e.g. four $214.56 Anthropic
            # charges within six minutes — don't collide. Must be stable across
            # runs (never random/time-based): the per-upload idempotency key
            # derives from provenance, and a changing key would defeat Ramp's
            # duplicate collapsing.
            token = hashlib.sha1(inv["invoice_pdf_url"].encode()).hexdigest()[:8]
            rows.append({
                "amount_cents": int(inv["total"]),
                "date": date,
                "pdf_url": inv["invoice_pdf_url"],
                "provenance": f"anthropic:invoice {date} {inv['total']} {token}",
            })
        return rows

    def _listing(self, page: str = "") -> dict:
        org = os.environ.get("ANTHROPIC_ORG_UUID")
        if not org:
            raise SourceUnavailable(
                "ANTHROPIC_ORG_UUID is not set. Set it to your claude.ai "
                "organization UUID (Settings > Organization) before running "
                "the Anthropic source."
            )

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise SourceUnavailable(
                "Playwright is required for the Anthropic source. Install with: "
                "python3.12 -m pip install --user --break-system-packages playwright "
                "&& python3.12 -m playwright install chromium"
            ) from exc

        url = LISTING.format(org=org, page=page)
        with sync_playwright() as p:
            # _listing() runs on every invocation, not just --login — it must
            # never pop a visible browser window, so this stays headless=True
            # regardless of which browser _launch_context ends up using.
            ctx = _launch_context(p, headless=True)
            try:
                pg = ctx.new_page()
                resp = pg.goto(url)
                # Cloudflare's bot-detection challenge, not a real response
                # from claude.ai. This must be checked before the 403 branch
                # below — Cloudflare mitigations most often ride on a 403 —
                # and reported as its own distinct failure: it is neither an
                # authorization refusal (the 403-not-admin case) nor an
                # expired session (the 401 case), and re-running --login with
                # bundled Chromium would only repeat the same loop.
                if _is_cloudflare_challenge(resp):
                    raise SourceUnavailable(
                        f"claude.ai could not verify this session for organization {org}: "
                        f"Cloudflare challenged the automated browser itself, fingerprinting "
                        f"it as a bot, instead of letting the request through to a normal "
                        f"claude.ai response. This is neither a stale login nor an "
                        f"authorization refusal — re-run python3.12 "
                        f"skills/receipts/scripts/run.py --login using real Chrome, which is "
                        f"what this toolkit drives by default (this loop shows up when real "
                        f"Chrome isn't installed and it falls back to bundled Chromium) — "
                        f"install Google Chrome (https://www.google.com/chrome/) if that's "
                        f"the case."
                    )
                # 403 is authorization, not authentication: the session is
                # fine, the account just isn't an org admin. Telling that user
                # to log in again sends them around a loop that can never
                # succeed and hides the one fact they can act on.
                if resp is not None and resp.status == 403:
                    raise SourceUnavailable(
                        f"claude.ai refused the billing invoice listing for organization "
                        f"{org} (HTTP 403). This account is not an org admin there, and "
                        f"only an org admin can read billing invoices — signing in again "
                        f"will not change it. Ask an org owner for admin access, or unset "
                        f"ANTHROPIC_ORG_UUID to run without this source."
                    )
                if resp is None or resp.status != 200:
                    raise SourceUnavailable(
                        "claude.ai session expired. Run: python3.12 "
                        "skills/receipts/scripts/run.py --login"
                    )
                return json.loads(pg.inner_text("pre") or "{}")
            finally:
                ctx.close()

    @staticmethod
    def _download(url: str) -> bytes:
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
        if not data.startswith(b"%PDF"):
            raise SourceUnavailable(f"Expected PDF from {url[:60]}…, got {data[:16]!r}")
        return data

    def fetch(self, since: str, until: str) -> list[Receipt]:
        self.truncated = None
        notes: list[str] = []

        rows: list[dict] = []
        page, payload = "", {}
        for _ in range(PAGE_GUARD):
            payload = self._listing(page)
            rows.extend(self.parse_invoices(payload))
            if not payload.get("has_more"):
                break
            next_page = payload.get("next_page") or ""
            # has_more with no usable cursor used to leave `page` at "" and
            # re-request the identical first page until the guard ran out —
            # up to 20 Playwright browser launches returning the same rows,
            # making no progress and saying nothing. Stop, and say so.
            if not next_page or next_page == page:
                notes.append(
                    f"the invoice listing reported more pages but returned no usable "
                    f"next_page cursor after {len(rows)} invoices — results are incomplete"
                )
                break
            page = next_page
        else:
            # Guard exhausted with more pages still pending. Keep what we have,
            # but this is a partial search, not a complete one.
            if payload.get("has_more"):
                notes.append(
                    f"hit the {PAGE_GUARD}-page cap, {len(rows)} invoices fetched, "
                    f"results incomplete — narrow the date range and re-run"
                )

        # Per-invoice download. One expired URL, non-PDF response, or network
        # blip used to abort the whole list comprehension and discard every
        # valid invoice already gathered — one stale row took the entire
        # Anthropic source down. Keep the good ones; report the losses.
        out: list[Receipt] = []
        failures: list[str] = []
        for r in rows:
            if not (since <= r["date"] <= until):
                continue
            try:
                pdf = self._download(r["pdf_url"])
            except Exception as exc:
                failures.append(
                    f"{r['date']} ${r['amount_cents'] / 100:,.2f} ({type(exc).__name__})"
                )
                continue
            out.append(Receipt(
                merchant="anthropic",
                amount_cents=r["amount_cents"],
                date=r["date"],
                pdf_bytes=pdf,
                provenance=r["provenance"],
            ))

        if failures:
            shown = ", ".join(failures[:5])
            more = f" (+{len(failures) - 5} more)" if len(failures) > 5 else ""
            notes.append(
                f"{len(failures)} invoice PDF(s) failed to download and were skipped: "
                f"{shown}{more}"
            )

        self.truncated = "; ".join(notes) or None
        return out


SOURCE = AnthropicSource()


def _login():
    """Open a real browser, let the user sign in, and save the persistent
    Playwright profile at PROFILE. Called by `run.py --login` (the
    documented entry point) and by this module's own `--login` when invoked
    directly — both call this same function so the interactive login logic
    lives in exactly one place.

    RECEIPTS_LOGIN_TEST_NOOP short-circuits before Playwright or a browser is
    ever touched. Tests that need to prove the --login dispatch path — import
    succeeds, argument parsing reaches this call — actually works set this to
    prove it without opening a real browser, which would not be hermetic.
    """
    if os.environ.get("RECEIPTS_LOGIN_TEST_NOOP"):
        print("RECEIPTS_LOGIN_TEST_NOOP set — dispatch reached _login(), skipping real browser login")
        return

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # Interactive: the user needs to actually see the browser to sign in,
        # so this stays headless=False regardless of which browser
        # _launch_context ends up using.
        ctx = _launch_context(p, headless=False)
        ctx.new_page().goto("https://claude.ai/login")
        input("Sign in, then press Enter here to save the session… ")
        ctx.close()


if __name__ == "__main__":
    if "--login" in sys.argv:
        _login()

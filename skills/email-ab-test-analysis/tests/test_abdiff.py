#!/usr/bin/env python3
"""Tests for the copy diff and the attribution gate — pure, no I/O.

Counting the changes is what decides whether a cause may be named at all, so
the count has to be right and the failure to read something has to be loud.
"Nothing differs" and "nothing was looked at" produce the same clean report and
mean opposite things; the tests below pin them apart.

Hermetic: builds arm dicts in memory.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from abdiff import check_shape, compare, render


def arm(name, subject="Same subject", preheader="Same preheader",
        body="<p>Body one.</p>", cta="CTA ONE", href="https://x.test/j"):
    return {"id": name, "name": name, "subject": subject,
            "preheader": preheader,
            "body_html": f"<html>{body}<a href='{href}'>{cta}</a></html>"}


# --- counting ---------------------------------------------------------------

def test_one_element_changed_allows_attribution():
    r = compare(arm("A"), arm("B", cta="CTA TWO"))
    assert r["n_changed"] == 1 and r["elements_changed"] == ["cta"]
    assert r["attribution_allowed"]
    assert "YES" in render(r)


def test_two_elements_changed_refuses_single_element_attribution():
    r = compare(arm("A"), arm("B", cta="CTA TWO", subject="Different"))
    assert r["n_changed"] == 2 and not r["attribution_allowed"]
    out = render(r)
    assert "ATTRIBUTABLE TO ONE ELEMENT?  NO" in out
    assert "likely drove the result" in out, (
        "refusing is not enough — it must still ask for the likely driver")


def test_the_gate_speaks_plainly_rather_than_in_jargon():
    """A marketer reads this output; 'ATTRIBUTION: REFUSED' means nothing."""
    out = render(compare(arm("A"), arm("B", cta="Go", subject="Other")))
    assert "IS THE DIFFERENCE IN PERFORMANCE ATTRIBUTABLE TO ONE ELEMENT?" in out


def test_invisible_characters_do_not_read_as_a_copy_change():
    """Zero-width space, em space and hair space are everywhere in marketing
    HTML. Untested, the stripping can vanish in a reformat and every diff
    silently starts reporting identical copy as different.

    Escapes, never literals — written literally they would be invisible here
    too, and this test would be as fragile as the thing it protects.
    """
    for invisible in ("\u200b", "\u2003", "\u200a"):
        a = arm("A", body=f"<p>One{invisible}two</p>")
        b = arm("B", body="<p>One two</p>")
        assert compare(a, b)["n_changed"] == 0, (
            f"U+{ord(invisible):04X} must not count as a body edit")


def test_identical_copy_points_outside_the_message():
    r = compare(arm("A"), arm("B"))
    assert r["n_changed"] == 0
    assert "outside the message" in render(r)


def test_each_element_is_counted_once_and_named():
    r = compare(arm("A"), arm("B", subject="S2", preheader="P2",
                              body="<p>Different body.</p>", cta="Go",
                              href="https://y.test/j"))
    assert set(r["elements_changed"]) == {"subject", "preheader", "body",
                                          "cta", "links"}


def test_the_cta_is_scored_apart_from_the_body_it_sits_in():
    """The CTA sits inside the body markup but is its own element, so a change
    to it must count once, as a CTA change, and not also as a body change."""
    r = compare(arm("A"), arm("B", cta="CTA TWO"))
    assert r["elements_changed"] == ["cta"]


# --- refusing to read what it cannot see ------------------------------------

def test_a_payload_using_the_wrong_body_key_is_refused_not_reported_as_equal():
    bad = [{"name": "A", "subject": "S", "body": "<p>one</p>"},
           {"name": "B", "subject": "S", "body": "<p>two</p>"}]
    with pytest.raises(SystemExit) as e:
        check_shape(bad)
    assert "body_html" in str(e.value) or "keys above" in str(e.value)


def test_the_refusal_names_the_key_it_expected(capsys):
    with pytest.raises(SystemExit):
        check_shape([{"name": "A", "body": "<p>x</p>"},
                     {"name": "B", "body": "<p>y</p>"}])
    err = capsys.readouterr().err
    assert "did you mean body_html" in err


def test_a_missing_body_is_reported_as_unknown_rather_than_unchanged(capsys):
    check_shape([{"name": "A", "subject": "S"}, {"name": "B", "subject": "S"}])
    err = capsys.readouterr().err
    assert "UNKNOWN" in err and "not unchanged" in err


def test_harmless_metadata_does_not_trip_the_refusal():
    check_shape([{"name": "A", "body_html": "<p>x</p>", "campaign_id": "9"},
                 {"name": "B", "body_html": "<p>y</p>", "campaign_id": "9"}])

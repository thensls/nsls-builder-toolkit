"""Tests for the PENDING SUGGESTIONS warning in skills/gdoc-edit/scripts/gdoc.py.

Run from the repo root: python3 skills/gdoc-edit/tests/test_suggestion_warning.py

Only `read` used to count pending suggestions. `replace`, `insert-after`,
`remove` and `batch` edited a redlined doc without a word, and the API only
makes direct edits, so an anchor edit on a line holding a colleague's
suggestion replaced it. The editing actions now print a warning first. gws is
replaced by a fake that serves a doc and records the edits, so nothing here
touches Google.
"""
import contextlib
import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "gdoc.py"
spec = importlib.util.spec_from_file_location("gdoc", SCRIPT)
gdoc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gdoc)

# What `read` printed before this change, copied from main. It must not move.
READ_WARNING = ("⚠️  PENDING SUGGESTIONS: 1 inserted and 1 deleted text run(s) below "
                "are UNACCEPTED edits, shown inline. What follows is a redline, not the live "
                "document. Re-run with --suggestions accepted (or rejected) to see one "
                "resolved version.")
EDIT_WARNING = "⚠️  PENDING SUGGESTIONS: this document has 1 inserted and 1 deleted"


def run(text, ins=None, dele=None):
    out = {"textRun": {"content": text}}
    if ins:
        out["textRun"]["suggestedInsertionIds"] = [ins]
    if dele:
        out["textRun"]["suggestedDeletionIds"] = [dele]
    return out


def doc(*paras):
    """A Docs API body: each para is a list of runs; indices are filled in."""
    content, i = [], 1
    for runs in paras:
        start = i
        for r in runs:
            r["startIndex"] = i
            i += len(r["textRun"]["content"])
            r["endIndex"] = i
        content.append({"startIndex": start, "endIndex": i, "paragraph": {"elements": runs}})
    return {"body": {"content": content}}


# Line 1 holds a colleague's suggestion: "Q4" proposed in place of "Q3".
REDLINED = doc([run("Launch in "), run("Q4", ins="s1"), run("Q3", dele="s2"), run(".\n")],
               [run("Owner: Dana\n")])
CLEAN = doc([run("Launch in Q3.\n")], [run("Owner: Dana\n")])


class Fake:
    def __init__(self, served, fail_on_edit=False):
        self.served, self.fail_on_edit = served, fail_on_edit
        self.gets, self.edits = 0, []

    def __call__(self, args, params=None, body=None):
        if args[:3] == ["docs", "documents", "get"]:
            self.gets += 1
            return copy.deepcopy(self.served)
        if args[:3] == ["docs", "documents", "batchUpdate"]:
            if self.fail_on_edit:
                sys.exit("gws: batchUpdate failed")
            self.edits.append(body["requests"])
            return {"replies": []}
        raise AssertionError("unexpected gws call: %r" % (args,))


def main_out(served, *argv, fail_on_edit=False):
    fake = Fake(served, fail_on_edit)
    buf = io.StringIO()
    old_gws, old_argv = gdoc.gws, sys.argv
    gdoc.gws, sys.argv = fake, ["gdoc.py", *argv]
    try:
        with contextlib.redirect_stdout(buf):
            try:
                gdoc.main()
            except SystemExit:
                if not fail_on_edit:
                    raise
    finally:
        gdoc.gws, sys.argv = old_gws, old_argv
    return buf.getvalue(), fake


class SuggestionWarning(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.batch = Path(self.tmp.name) / "edits.json"
        self.batch.write_text(json.dumps({"edits": [
            {"label": "quarter", "anchor": "Launch in", "replace": "Launch in Q1.", "marker": "Q1"}]}))

    def tearDown(self):
        self.tmp.cleanup()

    def edit_actions(self):
        return {
            "replace": ["replace", "--doc", "D", "--find", "Owner", "--replace", "Lead"],
            "replace --regex": ["replace", "--doc", "D", "--find", "Own.r", "--replace", "Lead", "--regex"],
            "insert-after": ["insert-after", "--doc", "D", "--anchor", "Owner", "--text", "New line"],
            "remove": ["remove", "--doc", "D", "--anchor", "Owner"],
            "batch": ["batch", "--doc", "D", "--file", str(self.batch)],
        }

    def test_read_warning_is_unchanged(self):
        out, _ = main_out(REDLINED, "read", "--doc", "D")
        self.assertEqual(out.split("\n")[0], READ_WARNING)

    def test_read_of_a_clean_doc_prints_only_the_text(self):
        out, _ = main_out(CLEAN, "read", "--doc", "D")
        self.assertEqual(out, "Launch in Q3.\nOwner: Dana\n")

    def test_every_editing_action_warns_first_on_a_redlined_doc(self):
        for name, argv in self.edit_actions().items():
            with self.subTest(action=name):
                out, fake = main_out(REDLINED, *argv)
                self.assertTrue(out.startswith(EDIT_WARNING), out[:200])
                self.assertIn("replaces that suggestion", out.split("\n")[0])
                self.assertTrue(fake.edits, "the edit should still run")

    def test_no_warning_on_a_clean_doc(self):
        for name, argv in self.edit_actions().items():
            with self.subTest(action=name):
                out, fake = main_out(CLEAN, *argv)
                self.assertNotIn("PENDING SUGGESTIONS", out)
                self.assertTrue(fake.edits)

    def test_single_edits_fetch_the_doc_once(self):
        for name in ("replace --regex", "insert-after", "remove"):
            with self.subTest(action=name):
                _, fake = main_out(REDLINED, *self.edit_actions()[name])
                self.assertEqual(fake.gets, 1)

    def test_warning_survives_a_failed_edit(self):
        out, _ = main_out(REDLINED, *self.edit_actions()["replace"], fail_on_edit=True)
        self.assertTrue(out.startswith(EDIT_WARNING), out[:200])

    def test_append_and_insert_top_stay_quiet(self):
        # They add text at the ends of the doc and can't touch a suggestion.
        for argv in (["append", "--doc", "D", "--text", "x"],
                     ["insert-top", "--doc", "D", "--title", "Changelog"]):
            with self.subTest(action=argv[0]):
                out, _ = main_out(REDLINED, *argv)
                self.assertEqual(out, "ok\n")


if __name__ == "__main__":
    unittest.main()

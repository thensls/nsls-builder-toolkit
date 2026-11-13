"""Tests for skills/quicknote/scripts/sweep_sessions.py.

Run from the repo root: python3 skills/quicknote/tests/test_sweep_sessions.py

A Windows console prints in cp1252, which can't encode arrows, emoji or most
non-Latin letters. The sweep prints people's own words with ensure_ascii=False,
so until main() forced UTF-8 output, a week with one "→" in it ended in a
UnicodeEncodeError traceback instead of a session list. The test reproduces
that console on any OS by setting PYTHONIOENCODING=cp1252.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "sweep_sessions.py"
SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"
ASK = "Move the board → Friday ✅ and tell José"


class SweepOnALegacyConsole(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        proj = home / ".claude" / "projects" / "-work-proj"
        proj.mkdir(parents=True)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        rows = [
            {"type": "user", "timestamp": now, "cwd": "/work/proj",
             "message": {"role": "user", "content": ASK}},
            {"type": "assistant", "timestamp": now, "cwd": "/work/proj",
             "message": {"role": "assistant", "content": [{"type": "text", "text": "Done — moved."}]}},
        ]
        (proj / "s1.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        self.env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        self.env.update(HOME=str(home), USERPROFILE=str(home), PYTHONIOENCODING="cp1252")
        self.env.pop("PYTHONUTF8", None)

    def tearDown(self):
        self.tmp.cleanup()

    def test_non_ascii_asks_print_as_utf8(self):
        today = datetime.now().date().isoformat()
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--start", today, "--end", today],
            capture_output=True, env=self.env, timeout=60,
        )
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        out = json.loads(r.stdout.decode("utf-8"))
        self.assertEqual(out["sessions_found"], 1)
        self.assertEqual(out["sessions"][0]["asks"], [ASK])


class SkillRunsTheLauncher(unittest.TestCase):
    def test_skill_never_tells_windows_to_use_python3(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("nsls-python scripts/sweep_sessions.py", text)
        self.assertNotIn("python3 scripts/sweep_sessions.py", text)
        self.assertNotIn("use `python` if `python3` isn't found", text)


if __name__ == "__main__":
    unittest.main()

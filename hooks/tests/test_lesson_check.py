#!/usr/bin/env python3
# windows-ci: python | Lesson check helper: on/off, status, and skill backups that refuse skills the builder does not own
"""The lesson check's helper turns on and off, reports status, and backs up only
the builder's own skills.

Plain stdlib: `python3 hooks/tests/test_lesson_check.py`.

The compound skill can patch one of the builder's skills when they approve a
lesson. The backup is taken by this helper so an undo always exists, and it
refuses toolkit, plugin, pointer and claude.ai-synced skills, whose next update
would silently overwrite the edit.

Every subprocess runs with its own config dir: nothing here touches the real
~/.claude.
"""
import collector_off  # noqa: F401  (first: no test may install the real collector)
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
WINDOWS = os.name == "nt"
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


def git_bash():
    if not WINDOWS:
        return shutil.which("bash")
    git = shutil.which("git")
    for cand in ([Path(git).resolve().parents[1] / "bin" / "bash.exe"] if git else []) + [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"]:
        if cand.is_file():
            return str(cand)
    return None


TMP = Path(tempfile.mkdtemp(prefix="lesson-test-"))
CFG = TMP / "home" / ".claude"
CFG.mkdir(parents=True)
ENV = dict(os.environ, HOME=str(TMP / "home"), USERPROFILE=str(TMP / "home"), CLAUDE_CONFIG_DIR=str(CFG),
           PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
ENV.pop("NSLS_LESSON_CHECK", None)


def helper(*args, env=None):
    r = subprocess.run([sys.executable, str(HOOKS / "lesson-check.py"), *args], env=env or ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=30)
    return r.returncode, r.stdout.strip()


def make_skill(path, body="---\nname: x\ndescription: test\n---\nStep one.\n"):
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(body, encoding="utf-8")
    return path / "SKILL.md"


print("on / off")
code, out = helper("status")
check("on by default", code == 0 and out.startswith("Lesson checks are ON"), out)
code, out = helper("off")
check("off says so", code == 0 and "off" in out, out)
code, out = helper("status")
check("status shows OFF after off", out.startswith("Lesson checks are OFF"), out)
code, out = helper("on")
code, out = helper("status")
check("on again", out.startswith("Lesson checks are ON"), out)
code, out = helper("status", env=dict(ENV, NSLS_LESSON_CHECK="off"))
check("NSLS_LESSON_CHECK=off wins for that shell", out.startswith("Lesson checks are OFF"), out)
(CFG / ".nsls-lesson-check" / "config.json").write_text("{not json", encoding="utf-8")
code, out = helper("status")
check("a corrupt config reads as on, not a crash", code == 0 and out.startswith("Lesson checks are ON"), out)

print("backup and undo of the builder's own skill")
own = make_skill(CFG / "skills" / "my-skill")
code, out = helper("backup", str(own))
check("own skill is backed up", code == 0 and out.startswith("Backed up.") and "lesson undo " in out, out)
bid = out.rsplit(" ", 1)[-1]
own.write_text("---\nname: x\ndescription: test\n---\nStep one, patched.\n", encoding="utf-8")
code, out = helper("undo", bid)
check("undo restores the original text", out.startswith("Undone") and "patched" not in own.read_text(encoding="utf-8"),
      out)
leftovers = [p.name for p in (CFG / "skills").iterdir() if p.name != "my-skill"]
check("undo leaves no stray folder behind", not leftovers, str(leftovers))
code, out = helper("undo", "no-such-backup")
check("unknown undo id is a plain refusal", code == 0 and out.startswith("Not undone"), out)
code, out = helper("status")
check("status lists the backup with its undo id", bid in out, out)

print("refusals: skills the builder does not own")
plugin = make_skill(CFG / "plugins" / "cache" / "nsls-toolkit" / "nsls-builder-toolkit" / "9.9.9" / "skills" / "plan")
code, out = helper("backup", str(plugin))
check("toolkit plugin skill refused", out.startswith("Not backed up") and "plugin" in out, out)
local = make_skill(CFG / "local-plugins" / "nsls-builder-toolkit" / "skills" / "plan")
code, out = helper("backup", str(local))
check("local plugin clone refused", out.startswith("Not backed up") and "plugin" in out, out)
pointer = make_skill(CFG / "skills" / "plan",
                     "---\nname: plan\ndescription: x\n---\nRead and follow the full skill at `~/.claude/x/SKILL.md`.\n")
code, out = helper("backup", str(pointer))
check("toolkit pointer stub refused", out.startswith("Not backed up") and "pointer" in out, out)
synced = make_skill(CFG / "skills" / "synced" / "org_123" / "board")
code, out = helper("backup", str(synced))
check("claude.ai-synced skill refused", out.startswith("Not backed up") and "claude.ai" in out, out)
outside = make_skill(TMP / "repo" / "skills" / "thing")
code, out = helper("backup", str(outside))
check("skill outside the skills folder refused", out.startswith("Not backed up") and "outside" in out, out)
code, out = helper("backup", str(CFG / "skills" / "nope"))
check("missing skill refused", out.startswith("Not backed up") and "no SKILL.md" in out, out)
if not WINDOWS:  # symlinks need extra rights on Windows
    link = CFG / "skills" / "linked-plan"
    os.symlink(local.parent, link)
    code, out = helper("backup", str(link))
    check("a link from skills/ into a plugin is still a plugin skill", "plugin" in out, out)

print("never a non-zero exit, never a traceback")
code, out = helper()
check("no arguments prints usage", code == 0 and out.startswith("Usage"), out)
code, out = helper("frobnicate")
check("unknown command prints usage", code == 0 and out.startswith("Usage"), out)

print("through the launcher")
bash = git_bash()
if bash:
    r = subprocess.run([bash, str(HOOKS / "run-hook.sh"), "lesson", "status"], env=ENV, capture_output=True,
                       text=True, encoding="utf-8", timeout=60)
    check("run-hook.sh lesson status runs the helper", r.returncode == 0 and "Lesson checks are" in r.stdout,
          r.stdout + r.stderr)
else:
    print("  skip (no bash)")

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{'FAILED: ' + ', '.join(failures) if failures else 'all passed'}")
sys.exit(1 if failures else 0)

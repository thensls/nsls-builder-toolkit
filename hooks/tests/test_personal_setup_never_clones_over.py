#!/usr/bin/env python3
"""/personal-setup's install step never clones over a folder that holds anything.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_personal_setup_never_clones_over.py`.

skills/personal-setup/SKILL.md (the bootstrapper) carries a bash block that
installs the Personal Toolkit from GitHub when Claude does not deliver it. To
clone, it first removes whatever is at the toolkit's path. That was written for
one case: a folder holding only a .env that /nsls-setmeup wrote earlier.

A folder Claude keeps current is not a git checkout (its .git is a placeholder
file), so the block took it for that case and would have deleted it: the
person's settings apart, everything in it, including files of theirs that an
update had set aside. This runs the block exactly as the skill carries it,
against each kind of folder, and checks what is left.

The clone itself is pointed at a path that does not exist, so it fails at once
and nothing reaches a network.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


if os.name == "nt":
    print("skipped on Windows: the block is the skill's Mac/Linux one")
    sys.exit(0)

skill = (ROOT / "skills" / "personal-setup" / "SKILL.md").read_text(encoding="utf-8")
found = re.search(r'```bash\n(PT="\$HOME/\.claude/local-plugins/nsls-personal-toolkit"\n# Repo/branch overridable.*?)```',
                  skill, re.S)
check("the install block is where this test expects it", found is not None)
if found is None:
    sys.exit(1)
BLOCK = found.group(1)


def run(prepare):
    """(last line printed, the folder's files before, the folder's files after)."""
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        folder = home / ".claude" / "local-plugins" / "nsls-personal-toolkit"
        prepare(folder)

        def listing():
            return {str(p.relative_to(home)): (p.read_bytes() if p.is_file() else None) for p in sorted(home.rglob("*"))}

        before = listing()
        env = dict(os.environ, HOME=str(home), NSLS_PERSONAL_REPO="file:///nonexistent/nsls-personal-toolkit.git",
                   GIT_TERMINAL_PROMPT="0")
        r = subprocess.run(["bash", "-c", BLOCK], env=env, capture_output=True, text=True, timeout=60)
        lines = r.stdout.strip().splitlines()
        return (lines[-1] if lines else ""), before, listing()


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def kept_current_by_claude(folder):
    put(folder / ".delivered-by-claude.json", "{}")
    put(folder / ".git", "gitdir: .git.delivered-by-claude\n")
    put(folder / ".env", "SECRET=1\n")
    put(folder / "skills" / "mine" / "SKILL.md", "a skill of their own\n")
    put(folder / ".set-aside" / "20261112-000000-abc123" / "README.md", "their version, set aside by an update\n")


def a_copy_from_somewhere(folder):
    put(folder / "skills" / "open-day" / "SKILL.md", "copied by hand\n")
    put(folder / ".env", "SECRET=1\n")


def only_a_prewritten_env(folder):
    put(folder / ".env", "BUILDER_EMAIL=someone@example.invalid\n")


print("the install block, run as the skill carries it")
said, before, after = run(kept_current_by_claude)
check("a folder Claude keeps current is never cloned over: it is named and left exactly as it is",
      said == "DELIVERED_FOLDER" and after == before, f"{said} {sorted(after)}")
said, before, after = run(a_copy_from_somewhere)
check("a folder holding anything else but a .env is not this step's to delete either",
      said == "FOLDER_NOT_EMPTY" and after == before, f"{said} {sorted(after)}")
said, before, after = run(only_a_prewritten_env)
check("only a pre-written .env: the clone is tried, and the .env survives it failing",
      said == "CLONE_FAILED" and after == before, f"{said} {sorted(after)}")
said, before, after = run(lambda folder: None)
check("nothing there: the clone is tried", said == "CLONE_FAILED", said)

print()
if failures:
    print(f"FAILED: {len(failures)}")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")

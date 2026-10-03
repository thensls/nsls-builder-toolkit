#!/usr/bin/env python3
"""Mac/Linux pointer sync only refreshes its own pointers, never a builder's skill.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_py_pointer_marker.py`.

session-start.py, install.sh and hooks/sync-pointers.sh write skill pointers
into ~/.claude/skills/<name>/SKILL.md. Each decided "this existing file is our
pointer, safe to overwrite" by looking for a toolkit path ANYWHERE in the file,
so a builder's own skill that merely mentioned one was overwritten. Now all
three share is_own_pointer() in session-start.py: the file must BE a pointer to
this skill, in one of the two shapes the toolkit writes. Windows twin:
test_ps1_pointer_marker.py.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
REPO = HOOKS.parent
failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


spec = importlib.util.spec_from_file_location("session_start_hook", HOOKS / "session-start.py")
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)
own = hook.is_own_pointer

FM = "---\nname: brainstorm\ndescription: >-\n  Explore an idea.\n---\n\n"
ORG = "local-plugins/nsls-builder-toolkit/skills/brainstorm/SKILL.md"
PERSONAL = "local-plugins/nsls-personal-toolkit/skills/brainstorm/SKILL.md"
PLAIN = FM + f"Read and follow the full skill at `~/.claude/{ORG}`.\n"


def credit(skill_path, hook_path="/Users/b/.claude/local-plugins/nsls-builder-toolkit/hooks/skill-event.sh"):
    return (
        FM + hook.POINTER_CREDIT + "\n\n```bash\n"
        + "echo '{\"tool_input\":{\"skill\":\"brainstorm\"}}' | bash " + hook_path + "\n```\n\n"
        + f"Then read and follow the full skill at `{skill_path}`.\n"
    )


print("the predicate: what counts as ours")
check("plain pointer (install.sh / sync-pointers.sh shape)", own(PLAIN, "brainstorm"))
check("credit pointer (session-start.py shape)", own(credit(f"/Users/b/.claude/{ORG}"), "brainstorm"))
check("credit pointer from before the hook path was absolute",
      own(credit(f"/Users/b/.claude/{ORG}", "$HOME/.claude/local-plugins/nsls-builder-toolkit/hooks/skill-event.sh"),
          "brainstorm"))
check("a pointer to the personal copy of THIS skill (org may replace it)",
      own(FM + f"Read and follow the full skill at `~/.claude/{PERSONAL}`.\n", "brainstorm"))
check("CRLF, a BOM and Windows backslashes",
      own("\ufeff" + PLAIN.replace("~/.claude/", "C:\\Users\\b\\.claude\\")
          .replace("local-plugins/", "local-plugins\\").replace("\n", "\r\n"), "brainstorm"))

print("the predicate: what is left alone")
check("a builder's skill that credits the toolkit skill",
      not own(FM + "# My brainstorm\n\nAdapted from "
              f"`~/.claude/{ORG}`, with my own steps.\n\n1. Think.\n", "brainstorm"))
check("a pointer the builder added notes to",
      not own(PLAIN + "\nAlso: always ask about budget first.\n", "brainstorm"))
check("notes above the Read line",
      not own(FM + "My note.\n\n" + f"Read and follow the full skill at `~/.claude/{ORG}`.\n", "brainstorm"))
check("a pointer to a DIFFERENT skill",
      not own(PLAIN.replace("skills/brainstorm/", "skills/plan/"), "brainstorm"))
check("a path that only ends like ours",
      not own(PLAIN.replace("local-plugins/nsls-builder-toolkit", "local-plugins/my-nsls-builder-toolkit"),
              "brainstorm"))
check("a credit block with an extra command in the fence",
      not own(credit(f"/Users/b/.claude/{ORG}").replace("```bash\n", "```bash\nrm -f notes\n"), "brainstorm"))
check("body text between two --- lines is not front matter",
      not own("---\nname: x\n---\nMy own notes.\n---\n" + f"Read and follow the full skill at `~/.claude/{ORG}`.\n",
              "brainstorm"))
check("a pointer the builder added a front-matter key to",
      not own(PLAIN.replace("description: >-", "model: opus\ndescription: >-"), "brainstorm"))
check("a pointer whose description the builder made multi-line",
      not own(PLAIN.replace("  Explore an idea.\n", "  Explore an idea.\n  Mine: ask about budget.\n"),
              "brainstorm"))
check("no front matter at all",
      not own(f"Read and follow the full skill at `~/.claude/{ORG}`.\n", "brainstorm"))
check("install.sh's org-only check rejects a personal-copy pointer",
      not own(FM + f"Read and follow the full skill at `~/.claude/{PERSONAL}`.\n", "brainstorm",
              ("nsls-builder-toolkit",)))


def fake_config(root):
    """A config dir with the org toolkit holding two skills, plus the hooks."""
    cfg = root / ".claude"
    plugin = cfg / "local-plugins" / "nsls-builder-toolkit"
    for skill in ("brainstorm", "plan"):
        d = plugin / "skills" / skill
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: >-\n  NEW description of {skill}.\n---\n\nBody.\n")
    (plugin / "hooks").mkdir()
    for f in ("session-start.py", "sync-pointers.sh"):
        shutil.copy(HOOKS / f, plugin / "hooks" / f)
    return cfg


MINE = FM + "# My brainstorm\n\nBuilt on `~/.claude/" + ORG + "`, but these are my steps.\n"
STALE = PLAIN.replace("Explore an idea.", "OLD description.").replace("brainstorm", "plan")


def seed(cfg):
    for skill, text in (("brainstorm", MINE), ("plan", STALE)):
        (cfg / "skills" / skill).mkdir(parents=True)
        (cfg / "skills" / skill / "SKILL.md").write_text(text)


def read(cfg, skill):
    return (cfg / "skills" / skill / "SKILL.md").read_text()


print("session-start.py sync_pointers(), for real")
with tempfile.TemporaryDirectory() as td:
    cfg = fake_config(Path(td))
    seed(cfg)
    hook.CONFIG_DIR, hook.SKILLS_DIR = cfg, cfg / "skills"
    hook.org_plugin_active = lambda: False
    hook.sync_pointers()
    check("the builder's own skill is untouched", read(cfg, "brainstorm") == MINE)
    check("our stale pointer is refreshed", "NEW description of plan" in read(cfg, "plan"))
    check("and the refresh is still ours next session", own(read(cfg, "plan"), "plan"))

print("hooks/sync-pointers.sh, for real")
with tempfile.TemporaryDirectory() as td:
    cfg = fake_config(Path(td))
    seed(cfg)
    env = {**os.environ, "HOME": td}
    r = subprocess.run(["bash", str(cfg / "local-plugins/nsls-builder-toolkit/hooks/sync-pointers.sh")],
                       env=env, capture_output=True, text=True)
    check("it runs", r.returncode == 0, r.stderr)
    check("the builder's own skill is untouched", read(cfg, "brainstorm") == MINE)
    check("our stale pointer is refreshed", "NEW description of plan" in read(cfg, "plan"))
    check("and the refresh is still ours next time", own(read(cfg, "plan"), "plan"))

print("install.sh, its check and its pointer")
src = (REPO / "install.sh").read_text()
func = re.search(r"^is_own_pointer\(\) \{\n.*?\nPYEOF\n\}\n", src, re.S | re.M)
check("install.sh defines is_own_pointer", func is not None)
check("the same definition as sync-pointers.sh",
      func is not None and func.group(0) in (HOOKS / "sync-pointers.sh").read_text())
template = re.search(r'cat > "\$dest/SKILL\.md" << POINTER\n(.*?\n)POINTER\n', src, re.S)
check("install.sh's pointer template found", template is not None)
if func and template:
    with tempfile.TemporaryDirectory() as td:
        cfg = fake_config(Path(td))
        seed(cfg)
        plugin_dir = cfg / "local-plugins" / "nsls-builder-toolkit"
        script = (func.group(0)
                  + 'name=plan; desc="A plan."; skill=plan\n'
                  + 'cat > "$1" << POINTER\n' + template.group(1) + "POINTER\n"
                  + 'is_own_pointer "$1" plan && echo fresh-ours\n'
                  + 'is_own_pointer "$2" brainstorm || echo mine-left\n')
        r = subprocess.run(["bash", "-c", script, "t", str(Path(td) / "fresh.md"),
                            str(cfg / "skills/brainstorm/SKILL.md")],
                           env={**os.environ, "PLUGIN_DIR": str(plugin_dir)}, capture_output=True, text=True)
        check("a pointer install.sh writes counts as ours", "fresh-ours" in r.stdout, r.stdout + r.stderr)
        check("a builder's skill does not", "mine-left" in r.stdout, r.stdout + r.stderr)

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")

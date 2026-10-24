#!/usr/bin/env python3
# windows-ci: python | A builder's no is remembered outside a git repo too (keyed by folder)
"""A builder's "no" is remembered outside a git repo too.

Plain stdlib: `python3 hooks/tests/test_guardrail_memory_folders.py`.

guardrail-memory.py keyed a build by its git remote and returned no key at all
outside git, so `record` quietly did nothing: no local memory, and no
guardrail_proceeded event. Work in a doc folder, a dashboard directory or
~/Documents was asked the same question every session. Outside git the key is
now the folder, and since a folder can hold several builds its listing says so.

Runs sandboxed (own config dir, no git identity, dead tracker URL): `record`
reports the decline to the tracker, and a test must never write a real row.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    home = tmp / "home"
    (home / ".claude").mkdir(parents=True)
    gitcfg = tmp / "gitconfig"
    gitcfg.write_text("", encoding="utf-8")
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), CLAUDE_CONFIG_DIR=str(home / ".claude"),
               GIT_CONFIG_GLOBAL=str(gitcfg), GIT_CONFIG_NOSYSTEM="1", NSLS_TRACKER_URL="http://127.0.0.1:9",
               PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

    def memory(*args, cwd):
        return subprocess.run([sys.executable, str(HOOKS / "guardrail-memory.py"), *args], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", env=env, cwd=str(cwd), timeout=60)

    folder = tmp / "docs work"
    folder.mkdir()
    print("outside git, a decline is now remembered")
    memory("record", "registration", "--note", "the onboarding checklist doc is just for me", cwd=folder)
    out = memory("list", cwd=folder).stdout
    check("it reads back in the same folder", "registration" in out and "onboarding checklist" in out, repr(out))
    check("and the listing says a folder may hold several builds",
          "not a git repo" in out and "the build its note describes" in out, repr(out))
    other = tmp / "elsewhere"
    other.mkdir()
    check("another folder is not affected", memory("list", cwd=other).stdout.strip() == "")

    print("\na decline saved after Claude moved into a subfolder still shows from the top")
    # Session start lists from the folder the session started in, but Claude
    # records a decline from wherever it has `cd`'d to. Keyed by that subfolder,
    # the decline used to vanish from the next session's list.
    proj = tmp / "proj"
    deep = proj / "drafts" / "q4 plan"
    deep.mkdir(parents=True)
    memory("record", "mentor-check", "--note", "the Q4 deck is a solo draft", cwd=deep)
    memory("record", "registration", "--note", "proj-wide: just my notes", cwd=proj)
    sibling = tmp / "proj-old"
    sibling.mkdir()
    memory("record", "design-doc", "--note", "the archived one", cwd=sibling)
    out = memory("list", cwd=proj).stdout
    check("the subfolder's decline is listed from the session folder",
          "mentor-check" in out and "Q4 deck" in out, repr(out))
    check("it says which subfolder it came from", "in drafts/q4 plan/" in out, repr(out))
    check("the folder's own decline is still listed", "proj-wide" in out, repr(out))
    check("a sibling folder sharing the name's start is not included",
          "archived" not in out, repr(out))
    check("a subfolder does not list its parent's declines",
          "proj-wide" not in memory("list", cwd=deep).stdout)

    lots = tmp / "lots"
    for i in range(12):
        (lots / f"d{i:02d}").mkdir(parents=True)
        memory("record", "design-doc", "--note", f"n{i:02d}", cwd=lots / f"d{i:02d}")
    out = memory("list", cwd=lots).stdout
    check("subfolder declines are capped so session context can't flood",
          out.count("- design-doc") == 8 and "and 4 older ones in subfolders" in out, repr(out))

    print("\nWindows: case is ignored, one folder name at a time")
    import importlib.util
    spec = importlib.util.spec_from_file_location("guardrail_memory", HOOKS / "guardrail-memory.py")
    gm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gm)
    gm._FOLD = str.lower  # what Windows uses, whatever this runner is
    decl = {"t": {"at": "2026-10-24", "note": ""}}
    data = {"dir:C:/Users/Ana/İstanbul": {}, "dir:c:/users/ana/İSTANBUL/drafts": decl,
            "dir:C:/Users/Ana/İstanbul-old/x": decl}
    lines = gm._subfolder_lines("dir:C:/Users/Ana/İstanbul", data)
    check("a subfolder spelled in another case is found, and named whole",
          lines == ["- t (declined 2026-10-24, in drafts/)"], lines)
    lines = gm._subfolder_lines("dir:C:", {"dir:C:/proj/sub": decl})
    check("from a drive root, the whole path below it is the subfolder",
          lines == ["- t (declined 2026-10-24, in proj/sub/)"], lines)

    print("\ninside a repo, nothing changes")
    repo = tmp / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], env=env, timeout=30)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", "https://github.com/example/tool.git"],
                   env=env, timeout=30)
    memory("record", "design-doc", "--note", "not yet", cwd=repo)
    out = memory("list", cwd=repo).stdout
    check("a repo decline still reads as this build's", out.startswith("This build has already declined")
          and "design-doc" in out, repr(out))
    sub = repo / "src"
    sub.mkdir()
    check("from anywhere inside the repo", "design-doc" in memory("list", cwd=sub).stdout)

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")

#!/usr/bin/env python3
"""A push through the PowerShell tool is judged with PowerShell's rules.

Plain stdlib: `python3 hooks/tests/test_gate_powershell_paths.py`.

The gate tokenized every command the bash way, where a backslash is an escape.
PowerShell treats it as an ordinary character, so `git -C C:\\Users\\x\\repo
push origin main` sent through the PowerShell tool became `C:Usersxrepo` to the
gate, repo_root() found nothing, and a real push went out unchallenged (PC test,
2026-09-30). Through the Bash tool the same unquoted path is mangled by Git
Bash too, so nothing is pushed, and bash rules stay right there. The other
shapes below came from Codex review: backtick escapes and continuations,
here-strings, `Git`/`git.exe`/a full path, and Set-Location.

End to end on any OS: macOS and Linux allow a backslash inside a file name, so
a repo directory literally named `nsls\\thing` stands in for a Windows path.
No network: NSLS_GUARDRAIL_EVENT_LOG sends the event emitter to a file.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "hooks" / "guardrail-gate.py"
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


sys.path.insert(0, str(ROOT / "hooks"))
spec = importlib.util.spec_from_file_location("gate_mod", GATE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print("the tokenizer follows the shell that will run the command")
cmd = r"git -C C:\Users\x\repo push origin main"
mod._POWERSHELL = False
check("bash rules: a backslash escapes, as Git Bash would run it",
      mod.command_segments(cmd) == [["git", "-C", "C:Usersxrepo", "push", "origin", "main"]],
      f"({mod.command_segments(cmd)})")
mod._POWERSHELL = True
check("PowerShell rules: the Windows path survives whole",
      mod.command_segments(cmd) == [["git", "-C", r"C:\Users\x\repo", "push", "origin", "main"]],
      f"({mod.command_segments(cmd)})")
check("a quoted path and the call operator still split correctly",
      mod.command_segments(r'git -C "C:\Users\x\repo" push origin main; & git push') ==
      [["git", "-C", r"C:\Users\x\repo", "push", "origin", "main"], ["git", "push"]],
      f"({mod.command_segments(r'git -C \"C:\\Users\\x\\repo\" push origin main; & git push')})")
mod._POWERSHELL = False


def call(cwd, env, tool, command, n):
    payload = {"tool_name": tool, "tool_input": {"command": command}, "tool_use_id": f"toolu_ps_{n}"}
    return subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload),
                          capture_output=True, text=True, cwd=cwd, env=env, timeout=30)


def denied(r):
    try:
        out = json.loads(r.stdout or "{}")
    except Exception:
        return False
    return out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


print("\nend to end, with a repo whose path holds a backslash")
with tempfile.TemporaryDirectory() as tmp:
    parent = Path(tmp) / "work"
    repo = parent / "nsls\\thing"          # one directory, backslash in its name
    repo.mkdir(parents=True)
    (repo / "README.md").write_text("# NSLS chapter dashboard\nInternal NSLS tool.\n")
    run = lambda *a: subprocess.run(a, cwd=repo, capture_output=True, text=True)
    run("git", "init", "-q")
    run("git", "remote", "add", "origin", "https://github.com/someones-personal-account/nsls-thing.git")
    neutral = Path(tmp) / "elsewhere"
    neutral.mkdir()
    cfg = Path(tmp) / "claude"
    cfg.mkdir()
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(cfg), NSLS_GUARDRAIL_EVENT_LOG=str(Path(tmp) / "ev.jsonl"))
    env.pop("NSLS_GUARDRAILS_DISABLED", None)

    unquoted = f"git -C {repo} push origin main"
    quoted = f'git -C "{repo}" push origin main'
    r = call(neutral, env, "PowerShell", unquoted, 1)
    check("PowerShell, unquoted backslash path: denied (was the hole)", denied(r), r.stdout[:200])
    r = call(neutral, env, "PowerShell", quoted, 2)
    check("PowerShell, quoted path: denied", denied(r), r.stdout[:200])
    r = call(neutral, env, "PowerShell", f"cd {repo}; git push origin main", 3)
    check("PowerShell, cd into it first: denied", denied(r), r.stdout[:200])
    r = call(neutral, env, "Bash", quoted, 4)
    check("Bash, quoted path: denied", denied(r), r.stdout[:200])
    r = call(neutral, env, "Bash", unquoted, 5)
    check("Bash, unquoted: bash mangles the path exactly as Git Bash would, so no repo and no push",
          not denied(r), r.stdout[:200])

    print("\nother ways PowerShell runs the same push (Codex review)")
    spaced = parent / "nsls my\\thing"    # a space and a backslash in one name
    spaced.mkdir()
    (spaced / "README.md").write_text("# NSLS tool\n")
    subprocess.run(["git", "init", "-q"], cwd=spaced, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin",
                    "https://github.com/someones-personal-account/x.git"], cwd=spaced, capture_output=True)
    esc = str(spaced).replace(" ", "` ")
    shapes = [
        ("a backtick-escaped space in the path", f"git -C {esc} push origin main", repo),
        ("a backtick line continuation", f"git -C {repo} `\npush origin main", repo),
        ("Git, capitalised", f"Git -C {repo} push origin main", repo),
        ("git.exe", f"git.exe -C {repo} push origin main", repo),
        ("the call operator with a full path to git.exe",
         f'& "C:\\Program Files\\Git\\cmd\\git.exe" -C "{repo}" push origin main', repo),
        ("Set-Location first", f"Set-Location {repo}; git push origin main", repo),
        ("Set-Location -Path first", f"Set-Location -Path {repo}; git push origin main", repo),
        ("a here-string before the push",
         f"$msg = @'\nnot a command: git push origin main\n'@\ngit -C {repo} push origin main", repo),
    ]
    for n, (label, command, _) in enumerate(shapes, start=10):
        r = call(neutral, env, "PowerShell", command, n)
        check(f"PowerShell, {label}: denied", denied(r), r.stdout[:200] or r.stderr[-200:])
    r = call(neutral, env, "PowerShell", "$msg = @'\ngit -C " + str(repo) + " push origin main\n'@", 30)
    check("a push that only appears inside a here-string is data, not a push", not denied(r), r.stdout[:200])

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")

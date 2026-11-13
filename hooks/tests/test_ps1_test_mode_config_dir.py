#!/usr/bin/env python3
"""install.ps1 -Test must point the claude CLI at the test dir, and only for the run.

Plain stdlib: `python3 hooks/tests/test_ps1_test_mode_config_dir.py`.

Found 2026-10-15. install.sh exports CLAUDE_CONFIG_DIR in test mode, so every
`claude plugin ...` call lands in the test dir. install.ps1 never set it: a test
install wrote its own files to the test dir but sent the toolkit plugin,
superpowers and compound-engineering into the builder's real .claude, and its
own reads of the plugin registry looked in the test dir and found nothing.

install.ps1 now sets the variable right after it chooses the config dir, opens a
`try` that runs to the end of the file, and takes the variable back off in the
`finally`. A pasted `iwr | iex` runs in the builder's own window, so the variable
must not outlive the script, however it ends. The checks below are textual;
when `pwsh` is on PATH (GitHub's Mac and Linux runners have it) the installer's
real opening and closing lines also run around a stand-in body, once for each
way out. The whole installer runs under Windows PowerShell 5.1 and 7 in
hooks/tests/windows/install-test-mode-config-dir.ps1.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


raw = (REPO / "install.ps1").read_bytes()
lines = raw.decode("utf-8").splitlines()


def code(i):
    """Line i, or '' when it is a comment."""
    s = lines[i].strip()
    return "" if s.startswith("#") else s


def where(pattern, start=0):
    return [i for i in range(start, len(lines)) if re.search(pattern, code(i))]


print("install.ps1 points the claude CLI at a test install's dir")
sets = where(r"^if \(\$Test -and -not \$env:CLAUDE_CONFIG_DIR\) \{$")
check("sets CLAUDE_CONFIG_DIR in test mode, only when it isn't already set", len(sets) == 1, f"({sets})")
s = sets[0] if sets else 0
close = next((i for i in range(s, len(lines)) if lines[i] == "}"), len(lines) - 1)
check("to the dir it chose", bool(sets) and "    $env:CLAUDE_CONFIG_DIR = $ConfigDir" in lines[s:close],
      f"({str(lines[s:close])[:200]})")
resolved = where(r"^\s*\$ConfigDir = ")
check("after it has chosen that dir", resolved and max(resolved) < s, f"({resolved} vs {s})")

# The body under the try is not indented, so these two are at column 0; the
# script's other top-level try blocks are too, which is why position decides.
opened = close + 1 < len(lines) and lines[close + 1] == "try {"
fins = [i for i, l in enumerate(lines) if l.startswith("} finally {")]
check("opens a try right after setting it", opened, f"(line after the set: {lines[close + 1:close + 2]})")
check("whose finally ends the file", bool(fins), "(no '} finally {' at column 0)")
t = close + 1 if opened else 0
f = fins[-1] if fins else len(lines)
tries = [t] if opened else []
claude_calls = where(r"(&|Invoke-Native)\s+\$ClaudeBin\b")
check("every claude CLI call is inside it", claude_calls and t < min(claude_calls) and max(claude_calls) < f,
      f"({claude_calls} vs {t}..{f})")
stops = where(r"\bexit \d|\{ return \}")
check("every way the script stops is inside it", stops and all(t < i < f for i in stops), f"({stops} vs {t}..{f})")

tail = [l for l in lines[f:] if l.strip()]
check("the finally takes the variable off, only if it put it on",
      any(re.search(r"if \(\$SetConfigDirForTest\) \{ Remove-Item Env:CLAUDE_CONFIG_DIR\b", l) for l in tail),
      f"({tail})")
check("and nothing runs after it", tail[-1:] == ["}"] and len(tail) <= 5, f"({tail})")
check("install.ps1 is ASCII only", all(b < 128 for b in raw),
      f"(first non-ASCII byte at {next((i for i, b in enumerate(raw) if b >= 128), -1)})")

sh = (REPO / "install.sh").read_text(encoding="utf-8")
check("install.sh does the same (parity)",
      re.search(r'export CLAUDE_CONFIG_DIR="\$\{CLAUDE_KIT_TEST_DIR:-\$HOME/\.claude-kit-test\}"', sh) is not None)

pwsh = shutil.which("pwsh")
print(f"\nthe real opening and closing lines, run around a stand-in body ({pwsh or 'no pwsh here: skipped'})")
if pwsh and tries and fins:
    head, foot = "\n".join(lines[:t + 1]), "\n".join(lines[f:])
    bodies = {
        "end": 'Write-Output "IN=[$env:CLAUDE_CONFIG_DIR]"\nif ($RunningFromFile) { exit 0 } else { return }',
        "stop": 'Write-Output "IN=[$env:CLAUDE_CONFIG_DIR]"\nif ($RunningFromFile) { exit 1 } else { return }',
        "error": 'Write-Output "IN=[$env:CLAUDE_CONFIG_DIR]"\nGet-Item -LiteralPath "/no/such/nsls-path"',
    }
    # The way a paste runs it: inside the caller's own PowerShell, which is then asked
    # what is left in its environment.
    # -Command takes everything after it as script, so -Test travels in the environment.
    paste = ("$a = @{}; if ($env:NSLS_T_TEST) { $a.Test = $true }; "
             "try { & ([scriptblock]::Create([IO.File]::ReadAllText($env:NSLS_T_SCRIPT))) @a } "
             "catch { Write-Output 'THREW' }; Write-Output ('AFTER=[' + $env:CLAUDE_CONFIG_DIR + ']')")

    with tempfile.TemporaryDirectory() as tmp:
        kit, pre = str(Path(tmp) / "kit"), str(Path(tmp) / "preset")

        def run(body, args=("-Test",), preset=None, as_file=False):
            script = Path(tmp) / f"install-{body}.ps1"
            script.write_text(f"{head}\n{bodies[body]}\n{foot}\n", encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
            env.update(CLAUDE_KIT_TEST_DIR=kit, USERPROFILE=tmp, NSLS_T_SCRIPT=str(script),
                       NSLS_T_TEST="1" if "-Test" in args else "")
            if preset:
                env["CLAUDE_CONFIG_DIR"] = preset
            cmd = [pwsh, "-NoProfile", "-NonInteractive"]
            cmd += ["-File", str(script), *args] if as_file else ["-Command", paste]
            p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
            return p.returncode, p.stdout

        for body in bodies:
            rc, out = run(body)
            check(f"{body}: the body sees the test dir", f"IN=[{kit}]" in out, f"({out!r})")
            check(f"{body}: and the caller's window has no CLAUDE_CONFIG_DIR afterwards", "AFTER=[]" in out,
                  f"({out!r})")
        check("an error still reaches the caller", "THREW" in run("error")[1])

        rc, out = run("end", preset=pre)
        check("a CLAUDE_CONFIG_DIR the caller set is used and left as it was",
              f"IN=[{pre}]" in out and f"AFTER=[{pre}]" in out, f"({out!r})")
        rc, out = run("end", args=())
        check("a normal install doesn't set it at all", "IN=[]" in out and "AFTER=[]" in out, f"({out!r})")
        rc, out = run("stop", as_file=True)
        check("an early stop under -File still exits 1", rc == 1 and f"IN=[{kit}]" in out, f"(rc {rc}, {out!r})")
        rc, out = run("end", as_file=True)
        check("and a clean run still exits 0", rc == 0, f"(rc {rc}, {out!r})")

print()
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    sys.exit(1)
print("all checks passed")

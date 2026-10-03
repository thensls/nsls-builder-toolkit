#!/usr/bin/env python3
"""The Windows hook's Python step can start, and says so when it cannot.

Plain stdlib: `python3 hooks/tests/test_guardrails_entry.py`.

session-start.ps1 reached session-start.py's __guardrails__ block with
`py -3 -c "<program>"`. Windows PowerShell 5.1 strips double quotes from a
native argument, so Python received `run_name=__guardrails__`, a NameError,
and the whole step (guardrails context, plugin stage A, freshness check) never
ran on a PC. A PC test on 2026-09-30 found it. The step now runs a file,
guardrails_entry.py, and checks the exit code.

There is no PowerShell here; hooks/tests/windows/shim-python-step.ps1 runs the
real hook under 5.1 in CI. This file checks the entry point itself, pins the
script to it, and shows why the old form could never have worked.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
PS1 = (HOOKS / "session-start.ps1").read_text(encoding="utf-8")
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


print("the old inline form could never survive Windows PowerShell 5.1")
old = 'import runpy, sys\nrunpy.run_path(sys.argv[1], run_name="__guardrails__")'
as_received = old.replace('"', "")   # what 5.1 hands the native program
saved_argv = sys.argv
sys.argv = ["-c", "/nonexistent/session-start.py"]   # as the PC passed it
try:
    exec(compile(as_received, "<string>", "exec"), {})
    broke = None
except NameError as e:
    broke = str(e)
except Exception as e:
    broke = f"other: {e!r}"
finally:
    sys.argv = saved_argv
check("with its quotes stripped it raises the NameError the PC saw",
      broke == "name '__guardrails__' is not defined", f"({broke})")

print("\nthe entry point runs the guardrails block")
with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, HOME=tmp, USERPROFILE=tmp, CLAUDE_CONFIG_DIR=str(Path(tmp) / ".claude"),
               NSLS_NO_PLUGIN_MIGRATION="1")
    (Path(tmp) / ".claude").mkdir()
    r = subprocess.run([sys.executable, str(HOOKS / "guardrails_entry.py"), str(HOOKS / "session-start.py")],
                       capture_output=True, text=True, env=env, timeout=60)
    check("it exits 0", r.returncode == 0, f"({r.returncode}: {r.stderr[-300:]!r})")
    check("and prints the guardrail policy", "org guardrail policy" in r.stdout, f"({r.stdout[:200]!r})")

print("\nthe hook is pinned to it")
check("no inline `-c` program is left in session-start.ps1", not re.search(r"&\s*\$pyExe[^\n]*\s-c\s", PS1))
check("both interpreter branches run the entry file",
      """$psi.Arguments = $(if ($pyExe -eq 'py') { '-3 ' } else { '' }) + ('"{0}" "{1}"' -f $entryPy, $startPy)""" in PS1)
check("the exit code is checked", "$pyExit = $proc.ExitCode" in PS1 and "if ($pyExit -ne 0)" in PS1)
check("Python's output is read and re-emitted as UTF-8, not through the console code page",
      "$psi.StandardOutputEncoding = $utf8" in PS1 and "[Console]::OpenStandardOutput()" in PS1
      and "$psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'" in PS1)
check("no Python at all is reported too", "Report-ShimStuck -Reason 'no Python was found'" in PS1)
section4 = "\n".join(l for l in PS1.split("# --- 4.")[1].splitlines() if not l.lstrip().startswith("#"))
check("stderr goes to a local log, never discarded", "2>$null" not in section4
      and "$psi.RedirectStandardError = $true" in section4 and "WriteAllText($ShimPyLog, $pyErr" in section4)
notice = re.search(r'Write-Output \(\"\[NSLS Builder Toolkit\] Setup could not finish(.*?)\"\)\n', PS1, re.S)
check("the notice interpolates only the toolkit-authored reason, never the raw detail",
      notice is not None and "$Reason" in notice.group(0) and "$Detail" not in notice.group(0)
      and "$clean" not in notice.group(0), f"({notice.group(0)[:120] if notice else None!r})")
check("only its own stage is cleared on success", "if ($prev.stage -eq 'shim-python')" in PS1)
check("the record lives where Python keeps it (CLAUDE_CONFIG_DIR first)",
      "$ShimStateDir = if ([string]::IsNullOrWhiteSpace($env:CLAUDE_CONFIG_DIR))" in PS1
      and "$ShimStatus = Join-Path $ShimStateDir" in PS1)
smoke = (HOOKS / "tests" / "windows" / "shim-python-step.ps1").read_text(encoding="utf-8")
check("the Windows smoke test stubs the ping and collector out", "session-ping.ps1', 'collector_bootstrap.ps1'" in smoke)
check("session-start.ps1 is ASCII-only", all(ord(c) < 128 for c in PS1))

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")

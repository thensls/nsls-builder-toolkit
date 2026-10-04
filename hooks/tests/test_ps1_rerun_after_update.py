#!/usr/bin/env python3
"""The Windows hook re-runs its new copy in the session whose update changed it.

Plain stdlib. There is no PowerShell here; hooks/tests/windows/rerun-after-update.ps1
runs the real thing under Windows PowerShell 5.1 in CI. This pins the guard.
"""
import sys
from pathlib import Path

PS1 = (Path(__file__).resolve().parents[1] / "session-start.ps1").read_text(encoding="utf-8")
failures = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        failures.append(name)


before = PS1.index("$ownBefore = (Get-FileHash")
update = PS1.index("    Update-Checkout -Dir $dir")
rerun = PS1.index("if ($ownBefore -and $env:NSLS_SESSION_START_RERUN -ne '1')")
check("the script is hashed before the update and compared after it", before < update < rerun)
check("the guard is set before the new copy starts, so it can never start a third",
      PS1.index("$env:NSLS_SESSION_START_RERUN = '1'") < PS1.index("[System.Diagnostics.Process]::Start($psi)", rerun))
check("the new copy's output passes through as raw bytes",
      "$proc.StandardOutput.BaseStream.CopyTo($stdout)" in PS1)
check("this copy stops after the new one finishes", "exit $proc.ExitCode" in PS1)
check("the re-run happens before any other work",
      rerun < PS1.index("# --- 1b. personal-toolkit forks"))
check("session-start.ps1 is ASCII-only", all(ord(c) < 128 for c in PS1))
check("a copy that has started is never followed by this one doing the work again",
      "$started = $true" in PS1 and "if ($started) { exit 0 }" in PS1
      and PS1.index("$started = $true") > PS1.index("[System.Diagnostics.Process]::Start($psi)", PS1.index("$started = $false")))
check("the re-run copy does not pull again",
      "if ($env:NSLS_SESSION_START_RERUN -ne '1') {\n    foreach ($dir in @($BuilderDir, $PersonalDir))" in PS1)

print()
if failures:
    print(f"FAILED: {len(failures)}"); sys.exit(1)
print("all checks passed")

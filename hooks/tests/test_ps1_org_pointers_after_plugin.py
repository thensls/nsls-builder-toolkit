#!/usr/bin/env python3
"""The Windows hook stops writing org pointers once the plugin is active.

Plain stdlib. hooks/tests/windows/pointers-after-plugin.ps1 runs the real
functions under Windows PowerShell 5.1 in CI; this pins the wiring anywhere.
"""
import sys
from pathlib import Path

PS1 = (Path(__file__).resolve().parents[1] / "session-start.ps1").read_text(encoding="utf-8")
failures = []


def check(name, cond):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    if not cond:
        failures.append(name)


check("the org toolkit is synced note-only when the plugin is active",
      "$null = Sync-Pointers -PluginDir $BuilderDir -NoteOnly:(Test-OrgPluginActive)" in PS1)
check("the personal toolkit is always synced", "$null = Sync-Pointers -PluginDir $PersonalDir\n" in PS1)
check("note-only writes nothing", "if ($NoteOnly) { continue }" in PS1
      and PS1.index("if ($NoteOnly) { continue }") < PS1.index("[System.IO.File]::WriteAllText($destMd"))
check("but still notes the builder's own skills before skipping",
      PS1.index("$script:OwnSkills[$skillFolder.Name] = $true; continue") < PS1.index("if ($NoteOnly) { continue }"))
check("a plugin the builder switched off is not active",
      "$prop.Value -eq $false) { return $false }" in PS1)
check("session-start.ps1 is ASCII-only", all(ord(c) < 128 for c in PS1))
print()
if failures:
    print(f"FAILED: {len(failures)}"); sys.exit(1)
print("all checks passed")

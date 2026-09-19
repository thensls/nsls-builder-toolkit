# The fork-check lock on a real PC. Claim-Lock and Release-Lock are lifted out
# of session-start.ps1 by AST (its top level pulls and pings, so it is never
# dot-sourced) and proven to admit one holder at a time: PowerShell against
# PowerShell, Python against Python, and each against the other, because a PC
# with Python runs both copies of the check against this same file. Also the
# compatibility with the lock this one replaced: a token file left by a hook
# still on the previous code. Run by .github/workflows/windows-hooks.yml under
# PowerShell 7 (ProcessStartInfo.ArgumentList needs .NET Core).
$ErrorActionPreference = 'Stop'
$hooks  = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script = Join-Path $hooks 'session-start.ps1'
$pyHook = Join-Path $hooks 'session-start.py'
$probe  = Join-Path $PSScriptRoot 'lock-probe.py'

$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($script, [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw "session-start.ps1 does not parse: $($errors[0].Message)" }
$fns = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and @('Claim-Lock', 'Release-Lock') -contains $n.Name }, $true)
if ($fns.Count -ne 2) { throw "expected Claim-Lock and Release-Lock in session-start.ps1, found $($fns.Count)" }
foreach ($f in $fns) { Invoke-Expression $f.Extent.Text }

$script:failures = 0
function Check([string]$Label, [bool]$Cond) {
    if ($Cond) { Write-Host "ok   $Label" } else { Write-Host "FAIL $Label"; $script:failures++ }
}
function Start-Probe([string]$Mode) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'python'
    foreach ($a in @($probe, $pyHook, $lock, $Mode)) { $psi.ArgumentList.Add($a) }
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    return [System.Diagnostics.Process]::Start($psi)
}
function Read-Probe($Proc) {
    $Proc.WaitForExit(30000) | Out-Null
    $out = $Proc.StandardOutput.ReadToEnd()
    $err = $Proc.StandardError.ReadToEnd()
    if ($err) { Write-Host $err }
    return @($out -split "`r?`n" | Where-Object { $_ -ne '' })
}

$lock = Join-Path ([System.IO.Path]::GetTempPath()) ("fork-check-{0}.lock" -f [guid]::NewGuid().ToString('N'))

# --- PowerShell against PowerShell --------------------------------------------
$a = Claim-Lock -Path $lock
Check 'PS: the first claim returns a handle' ($null -ne $a)
Check 'PS: a second claim while held is refused' ($null -eq (Claim-Lock -Path $lock))
Release-Lock -Handle $a
$b = Claim-Lock -Path $lock
Check 'PS: a claim after release succeeds' ($null -ne $b)
Release-Lock -Handle $b
Check 'PS: the lock file is never deleted' (Test-Path $lock)

# --- compatibility with the previous, token-in-a-file lock --------------------
[System.IO.File]::WriteAllText($lock, '4242-1700000000-deadbeef')
Check 'PS: a fresh old-style token (an old hook mid-check) is yielded to' ($null -eq (Claim-Lock -Path $lock))
Check '...and its token is left intact for its own release' ([System.IO.File]::ReadAllText($lock) -eq '4242-1700000000-deadbeef')
[System.IO.File]::SetLastWriteTime($lock, (Get-Date).AddSeconds(-300))
$c = Claim-Lock -Path $lock
Check 'PS: a stale old-style token (a dead old hook) does not block' ($null -ne $c)
Check '...and the file is left empty' ($null -ne $c -and $c.Length -eq 0)
Check '...with a fresh write time, so an old hook looking now sees a live lock' (((Get-Date) - (Get-Item $lock).LastWriteTime).TotalSeconds -lt 30)
Release-Lock -Handle $c

# --- Python against Python, and Python holding while PowerShell tries ---------
$p = Start-Probe 'hold'
$first = $p.StandardOutput.ReadLine()
$second = $p.StandardOutput.ReadLine()
Check 'PY: the first claim returns a handle' ($first -eq 'held')
Check 'PY: a second claim through another descriptor is refused' ($second -eq 'second-refused')
Check 'PS: refused while Python holds' ($null -eq (Claim-Lock -Path $lock))
$p.StandardInput.WriteLine('go')
$null = Read-Probe $p
Check 'PY: released cleanly' ($p.ExitCode -eq 0)
$d = Claim-Lock -Path $lock
Check 'PS: claims once Python has released' ($null -ne $d)

# --- PowerShell holding while Python tries ------------------------------------
$lines = Read-Probe (Start-Probe 'try')
Check 'PY: refused while PowerShell holds' ($lines[0] -eq 'refused')
Release-Lock -Handle $d
$lines = Read-Probe (Start-Probe 'try')
Check 'PY: claims once PowerShell has released' ($lines[0] -eq 'held')

# --- Python: a stale old-style token is cleared, a fresh one is yielded to ----
[System.IO.File]::WriteAllText($lock, '4242-1700000000-deadbeef')
$lines = Read-Probe (Start-Probe 'try')
Check 'PY: a fresh old-style token (an old hook mid-check) is yielded to' ($lines[0] -eq 'refused')
[System.IO.File]::SetLastWriteTime($lock, (Get-Date).AddSeconds(-300))
$lines = Read-Probe (Start-Probe 'try')
Check 'PY: a stale old-style token (a dead old hook) does not block' ($lines[0] -eq 'held')
Check '...and the file is left empty' ($lines -contains 'size=0')

Write-Host ''
if ($script:failures -gt 0) { Write-Host "$($script:failures) FAILED"; exit 1 }
Write-Host 'all Windows lock checks passed'

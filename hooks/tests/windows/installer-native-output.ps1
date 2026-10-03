# install.ps1's Invoke-Native must hand back git's own words, not a PowerShell
# error dump. Under Windows PowerShell 5.1, `2>&1 | Out-String` renders each
# stderr line as a NativeCommandError record ("+ CategoryInfo ..."), and a failed
# toolkit update showed builders that noise instead of git's message (PC Test 4,
# 2026-10-03). Run under `shell: powershell` (5.1) and `pwsh`.
$ErrorActionPreference = 'Stop'   # what install.ps1 runs under
$root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))

# Load ONLY the function from install.ps1: running the script would install things.
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'install.ps1'), [ref]$null, [ref]$null)
$fn = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Invoke-Native' }, $true) | Select-Object -First 1
if (-not $fn) { Write-Host 'FAIL: Invoke-Native not found in install.ps1'; exit 1 }
. ([ScriptBlock]::Create($fn.Extent.Text))

$repo = Join-Path $env:TEMP ("native-out-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $repo | Out-Null
& git -C $repo init -q 2>$null
& git -C $repo remote add origin $repo 2>$null

$out = Invoke-Native 'git' @('-C', $repo, 'fetch', 'origin', 'no-such-branch', '--quiet')
$code = $LASTEXITCODE
Write-Host "PowerShell $($PSVersionTable.PSVersion); exit $code"
Write-Host "--- output ---`n$out`n--------------"

$fail = @()
if ($code -eq 0) { $fail += 'the fetch of a missing branch reported success' }
if ($out -notmatch "couldn't find remote ref no-such-branch") { $fail += "git's own message is missing" }
if ($out -match 'NativeCommandError|CategoryInfo|FullyQualifiedErrorId') { $fail += 'output is a PowerShell error dump' }
if ($fail) { $fail | ForEach-Object { Write-Host "FAIL: $_" }; exit 1 }
Write-Host 'PASS: Invoke-Native returns git''s own message'

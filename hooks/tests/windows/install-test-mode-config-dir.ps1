# windows-ci: ps51 ps7 | install.ps1 -Test sends the claude CLI to the test dir, and leaves no CLAUDE_CONFIG_DIR behind
# install.ps1 -Test, the whole installer, run for real under Windows PowerShell
# 5.1 and 7. Before 2026-10-15 a test install sent everything to the test dir
# except the claude CLI calls, which never heard about it: the toolkit plugin,
# superpowers and compound-engineering went into the builder's real .claude.
# Each run here happens the way a paste runs, inside one PowerShell process,
# which then reports what CLAUDE_CONFIG_DIR it is left with. A stand-in
# `claude` records the config dir every call saw. Nothing reaches the network:
# the toolkit is cloned from a local copy of this checkout, the tracker ping
# goes to a closed port, and PATH holds only git and the stand-ins.
# ASCII only, PS 5.1 compatible.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$installer = Join-Path $repo 'install.ps1'
$shell = (Get-Process -Id $PID).Path

$script:failures = 0
function Check([string]$Label, [bool]$Cond, [string]$Detail = '') {
    if ($Cond) { Write-Host "ok   $Label" } else { Write-Host "FAIL $Label"; if ($Detail) { Write-Host "     saw: $Detail" }; $script:failures++ }
}

$scratch = Join-Path ([IO.Path]::GetTempPath()) ('nsls-tcd-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$bin = Join-Path $scratch 'bin'
New-Item -ItemType Directory -Path $bin, (Join-Path $scratch 'home') -Force | Out-Null
$log = Join-Path $scratch 'claude.log'
$ascii = New-Object System.Text.ASCIIEncoding
# One line per call: the config dir it saw, then the subcommand. In a .cmd an
# unset variable expands to nothing, so a call that saw none logs "[]".
[IO.File]::WriteAllText((Join-Path $bin 'claude.cmd'), "@echo off`r`n>>`"$log`" echo [%CLAUDE_CONFIG_DIR%] %1 %2`r`nexit /b 0`r`n", $ascii)
# Present, so Step 0 doesn't download the real one.
[IO.File]::WriteAllText((Join-Path $bin 'gws.cmd'), "@echo gws 0.0.0-stand-in`r`n", $ascii)

# The toolkit to clone: this checkout's commit, as branch main of a local repo.
# CI's checkout is shallow, and a fetch from it drops the branch ("shallow roots
# are not allowed to be updated") yet exits 0, so --update-shallow, and check
# the branch is there rather than the exit code.
$src = Join-Path $scratch 'src.git'
& git init -q --bare $src 2>$null
& git -C $src fetch -q --update-shallow $repo 'HEAD:refs/heads/main' 2>$null
& git -C $src rev-parse -q --verify refs/heads/main 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host 'FAIL could not make a local copy of this checkout to install from'; exit 1 }

$gitDir = Split-Path (Get-Command git).Source
$base = @{
    CLAUDE_CONFIG_DIR = $null
    NSLS_TOOLKIT_REPO = $src
    NSLS_TOOLKIT_BRANCH = $null
    NSLS_TRACKER_URL = 'http://127.0.0.1:9'
    USERPROFILE = Join-Path $scratch 'home'
    APPDATA = Join-Path $scratch 'home\AppData\Roaming'
    LOCALAPPDATA = Join-Path $scratch 'home\AppData\Local'
    PATH = "$bin;$gitDir;$env:SystemRoot\System32;$env:SystemRoot\System32\WindowsPowerShell\v1.0"
}

# Runs install.ps1 -Test in a fresh PowerShell the way a paste does (no -File,
# so the installer stops with `return`, not `exit`) and returns everything it
# printed, ending with AFTER=[<CLAUDE_CONFIG_DIR left in that process>].
function Invoke-TestInstall([hashtable]$Vars) {
    $cmd = "`$ProgressPreference = 'SilentlyContinue'; " +
        "try { & ([scriptblock]::Create([IO.File]::ReadAllText(`$env:NSLS_T_INSTALLER))) -Test } " +
        "catch { Write-Output ('THREW: ' + `$_) }; Write-Output ('AFTER=[' + `$env:CLAUDE_CONFIG_DIR + ']')"
    $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))
    $all = @{ NSLS_T_INSTALLER = $installer }
    foreach ($k in $base.Keys) { $all[$k] = $base[$k] }
    foreach ($k in $Vars.Keys) { $all[$k] = $Vars[$k] }
    $saved = @{}
    foreach ($k in $all.Keys) { $saved[$k] = [Environment]::GetEnvironmentVariable($k); [Environment]::SetEnvironmentVariable($k, $all[$k]) }
    try {
        $out = & $shell -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $enc 2>&1 | ForEach-Object { "$_" } | Out-String
    } finally {
        foreach ($k in $saved.Keys) { [Environment]::SetEnvironmentVariable($k, $saved[$k]) }
    }
    return $out
}

function Tail([string]$Out) { (($Out -split "`r?`n") | Where-Object { $_ } | Select-Object -Last 6) -join ' / ' }

Write-Host "PowerShell $($PSVersionTable.PSVersion)"
try {
    # 1. A whole install, with no CLAUDE_CONFIG_DIR set beforehand.
    $kit = Join-Path $scratch 'kit'
    $out = Invoke-TestInstall @{ CLAUDE_KIT_TEST_DIR = $kit }
    $calls = @(if (Test-Path $log) { Get-Content $log | Where-Object { $_ } })
    Check 'a whole test install runs to the end' ($out -match '=== TEST INSTALL ===' -and $out -notmatch 'THREW') (Tail $out)
    Check 'it installs the plugins through the claude CLI' (@($calls | Where-Object { $_ -match '\] plugin install' }).Count -eq 3) ($calls -join ' / ')
    $stray = @($calls | Where-Object { -not $_.StartsWith("[$kit] ") })
    Check 'every claude call is pointed at the test dir' ($calls.Count -gt 0 -and $stray.Count -eq 0) ($stray -join ' / ')
    Check 'and the window has no CLAUDE_CONFIG_DIR afterwards' ($out -match 'AFTER=\[\]') (Tail $out)
    Check 'the installer wrote its settings into the test dir' (Test-Path (Join-Path $kit 'settings.json'))
    Check 'the banner says how to start claude against it' ($out -match [regex]::Escape("`$env:CLAUDE_CONFIG_DIR = `"$kit`"")) (Tail $out)

    # 2. An early stop: the toolkit can't be downloaded.
    $out = Invoke-TestInstall @{ CLAUDE_KIT_TEST_DIR = (Join-Path $scratch 'kit-stop'); NSLS_TOOLKIT_REPO = (Join-Path $scratch 'no-such-repo') }
    Check 'an early stop leaves no CLAUDE_CONFIG_DIR behind' ($out -match "couldn't download the toolkit" -and $out -match 'AFTER=\[\]') (Tail $out)

    # 3. An error: a settings.json that isn't JSON stops the installer in Step 2.
    $kitErr = Join-Path $scratch 'kit-error'
    New-Item -ItemType Directory -Path $kitErr -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $kitErr 'settings.json'), 'not json', $ascii)
    $out = Invoke-TestInstall @{ CLAUDE_KIT_TEST_DIR = $kitErr }
    Check 'an error leaves no CLAUDE_CONFIG_DIR behind' ($out -match 'THREW' -and $out -match 'AFTER=\[\]') (Tail $out)

    # 4. A CLAUDE_CONFIG_DIR the builder set themselves is used, and left as it was.
    $preset = Join-Path $scratch 'preset'
    $out = Invoke-TestInstall @{ CLAUDE_CONFIG_DIR = $preset; NSLS_TOOLKIT_REPO = (Join-Path $scratch 'no-such-repo') }
    Check 'a CLAUDE_CONFIG_DIR set beforehand is used and left alone' ($out -match [regex]::Escape("installing into $preset") -and $out -match [regex]::Escape("AFTER=[$preset]")) (Tail $out)
} finally {
    Remove-Item -Recurse -Force -LiteralPath $scratch -ErrorAction SilentlyContinue
}

if ($script:failures -gt 0) { Write-Host "$($script:failures) check(s) failed"; exit 1 }
Write-Host 'all checks passed'

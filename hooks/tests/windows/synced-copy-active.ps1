# windows-ci: ps51 ps7 | A copy delivered by NSLS's Claude organization counts as an active plugin, so the Windows hook stops writing org pointers
# Organization sync puts the toolkit on a machine with no record in
# installed_plugins.json. The Windows hook asked only that registry whether the
# plugin was active, so it would have kept writing a pointer file for every
# toolkit skill beside the real ones. The functions are lifted out of
# session-start.ps1 by AST, so this never tests a copy.
$ErrorActionPreference = 'Continue'
$hooks = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $hooks 'session-start.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw "session-start.ps1 does not parse: $($errors[0].Message)" }
$want = @('Get-SyncedAccountFolder', 'Test-SyncedToolkitCopy', 'Get-SyncedToolkitRoot', 'Test-SyncedToolkitActive', 'Test-OrgPluginActive')
$fns = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $want -contains $n.Name }, $true)
if ($fns.Count -ne $want.Count) { throw "expected $($want.Count) functions, found $($fns.Count)" }
foreach ($f in $fns) { Invoke-Expression $f.Extent.Text }

$script:failures = 0
function Check([string]$Label, [bool]$Cond, [string]$Detail = '') {
    if ($Cond) { Write-Host "ok   $Label" } else { Write-Host "FAIL $Label"; if ($Detail) { Write-Host "     saw: $Detail" }; $script:failures++ }
}

$org = '11111111-2222-3333-4444-555555555555'
$acct = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
$mine = "${org}_${acct}"
$other = "${org}_99999999-0000-0000-0000-000000000000"
$savedProfile = $env:USERPROFILE

function New-Machine {
    $root = Join-Path ([IO.Path]::GetTempPath()) ('synced-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path (Join-Path $root '.claude') -Force | Out-Null
    return $root
}
function Set-Text([string]$Path, [string]$Text) {
    New-Item -ItemType Directory -Path (Split-Path $Path -Parent) -Force | Out-Null
    [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding $false))
}
function Add-Copy([string]$Folder, [string]$Name = 'nsls-builder-toolkit', [bool]$HooksJson = $true) {
    $copy = Join-Path (Join-Path (Join-Path (Join-Path $ClaudeDir 'plugins') 'synced') $Folder) 'nsls-builder-toolkit'
    Set-Text (Join-Path (Join-Path $copy '.claude-plugin') 'plugin.json') ('{"name": "' + $Name + '", "version": "3.50.0"}')
    if ($HooksJson) { Set-Text (Join-Path (Join-Path $copy 'hooks') 'hooks.json') '{}' }
    return $copy
}
# Two project paths that differ only by case: Windows PowerShell 5.1's
# ConvertFrom-Json refuses this file outright, which is why the hook reads it
# as text.
$accountJson = '{"projects": {"C:/Users/x": {}, "c:/users/x": {}}, "oauthAccount": {"accountUuid": "' + $acct + '", "ccOnboardingFlags": {"a": 1}, "organizationUuid": "' + $org + '"}}'

$made = @()
try {
    # 1. Nothing synced: exactly the old answers.
    $root = New-Machine; $made += $root
    $env:USERPROFILE = $root; $ClaudeDir = Join-Path $root '.claude'
    Set-Text (Join-Path $root '.claude.json') $accountJson
    Check 'no synced copy, no registry: not active (as before)' (-not (Test-OrgPluginActive))
    Set-Text (Join-Path (Join-Path $ClaudeDir 'plugins') 'installed_plugins.json') '{"plugins": {"nsls-builder-toolkit@nsls-toolkit": [{"installPath": "x"}]}}'
    Check 'a marketplace install: active (as before)' (Test-OrgPluginActive)
    Set-Text (Join-Path $ClaudeDir 'settings.json') '{"enabledPlugins": {"nsls-builder-toolkit@nsls-toolkit": false}}'
    Check 'switched off by the builder: not active (as before)' (-not (Test-OrgPluginActive))
    Set-Text (Join-Path $ClaudeDir 'settings.json') '{"enabledPlugins": {"nsls-builder-toolkit@nsls-toolkit": true, "nsls-builder-toolkit@synced": false}}'
    Check "the synced copy's switch does not disable a marketplace install" (Test-OrgPluginActive)

    # 2. The organization's copy, for the signed-in account.
    $root = New-Machine; $made += $root
    $env:USERPROFILE = $root; $ClaudeDir = Join-Path $root '.claude'
    Set-Text (Join-Path $root '.claude.json') $accountJson
    Check 'the account folder is read from .claude.json as text' ((Get-SyncedAccountFolder) -eq $mine) "$(Get-SyncedAccountFolder)"
    $copy = Add-Copy $mine
    Check "a whole copy in the account's folder is found" ((Get-SyncedToolkitRoot) -eq $copy) "$(Get-SyncedToolkitRoot)"
    Check 'and makes the plugin active with no registry at all' (Test-OrgPluginActive)
    Set-Text (Join-Path $ClaudeDir 'settings.json') '{"syncClaudeAiPlugins": false}'
    Check 'syncClaudeAiPlugins off: not active' (-not (Test-OrgPluginActive))
    Set-Text (Join-Path $ClaudeDir 'settings.json') '{"enabledPlugins": {"nsls-builder-toolkit@synced": false}}'
    Check "the plugin's own switch off: not active" (-not (Test-OrgPluginActive))
    Set-Text (Join-Path (Split-Path $copy -Parent) 'nsls-builder-toolkit.meta.json') '{"installation_preference": "required"}'
    Check "required by NSLS: the builder's switch does not stop it" (Test-OrgPluginActive)
    Set-Text (Join-Path $ClaudeDir 'settings.json') '{not json'
    Check 'settings that cannot be read are not a switch' (Test-OrgPluginActive)

    # 3. A copy another account left behind.
    $root = New-Machine; $made += $root
    $env:USERPROFILE = $root; $ClaudeDir = Join-Path $root '.claude'
    Set-Text (Join-Path $root '.claude.json') $accountJson
    $null = Add-Copy $other
    Check "another account's copy does not count" (-not (Test-OrgPluginActive))
    $null = Add-Copy $mine.ToUpper()
    Check 'the account folder matches whatever its letter case' (Test-OrgPluginActive)

    # 4. Account unreadable.
    $root = New-Machine; $made += $root
    $env:USERPROFILE = $root; $ClaudeDir = Join-Path $root '.claude'
    $null = Add-Copy $other
    Check 'account unreadable, one copy: it counts' (Test-OrgPluginActive)
    $null = Add-Copy $mine
    Check 'account unreadable, two copies: neither is assumed' (-not (Test-OrgPluginActive))

    # 5. Not whole, or not this plugin.
    $root = New-Machine; $made += $root
    $env:USERPROFILE = $root; $ClaudeDir = Join-Path $root '.claude'
    Set-Text (Join-Path $root '.claude.json') $accountJson
    $null = Add-Copy $mine 'nsls-builder-toolkit' $false
    Check 'a copy with no hooks.json does not count' (-not (Test-OrgPluginActive))
    $root = New-Machine; $made += $root
    $env:USERPROFILE = $root; $ClaudeDir = Join-Path $root '.claude'
    Set-Text (Join-Path $root '.claude.json') $accountJson
    $null = Add-Copy $mine 'some-other-plugin'
    Check 'a folder holding a different plugin does not count' (-not (Test-OrgPluginActive))
} finally {
    $env:USERPROFILE = $savedProfile
    foreach ($r in $made) { Remove-Item -Recurse -Force $r -ErrorAction SilentlyContinue }
}
if ($script:failures -gt 0) { Write-Host "$($script:failures) check(s) failed"; exit 1 }
Write-Host 'all checks passed'

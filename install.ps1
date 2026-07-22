<#
install.ps1 — NSLS Builder Toolkit installer for Windows (full native).

Windows counterpart to install.sh. Bash isn't on a stock Windows box, so this
does the whole install in PowerShell — no bash, no python required (the Windows
hooks are native PowerShell):

  1. Clone / update the org plugin
  2. Enable it + register the PowerShell hooks in settings.json
  3. Fire an install event to the Automation Tracker (platform: windows)
  4. Install the superpowers + compound-engineering marketplace plugins
  5. Register bundled MCP servers (stdio directly; http via --transport http,
     deferring token-gated servers to /signal-setup)
  6. Sync slash-command pointer skills
  7. Print next steps (desktop-first)

Self-bootstrapping — safe to run piped straight from the web:
  powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -useb https://raw.githubusercontent.com/thensls/nsls-builder-toolkit/main/install.ps1 | iex"
It clones the repo itself (Step 1) before needing any file from it, so it never
depends on $PSScriptRoot. Also runs from a local checkout.

Idempotent: re-running updates the clone and no-ops anything already in place.
  -Test   install into a throwaway $HOME\.claude-kit-test (or $env:CLAUDE_CONFIG_DIR)
#>
param([switch]$Test)
$ErrorActionPreference = 'Stop'

# --- Config dir resolution (mirrors install.sh) ---
if ($env:CLAUDE_CONFIG_DIR) {
    $ConfigDir = $env:CLAUDE_CONFIG_DIR
} elseif ($Test) {
    $ConfigDir = if ($env:CLAUDE_KIT_TEST_DIR) { $env:CLAUDE_KIT_TEST_DIR } else { Join-Path $env:USERPROFILE '.claude-kit-test' }
} else {
    $ConfigDir = Join-Path $env:USERPROFILE '.claude'
}

$LocalDir  = Join-Path $ConfigDir 'local-plugins'
$PluginDir = Join-Path $LocalDir  'nsls-builder-toolkit'
$HooksDir  = Join-Path $PluginDir 'hooks'
$Settings  = Join-Path $ConfigDir 'settings.json'
$SkillsDir = Join-Path $ConfigDir 'skills'
# Repo/branch overridable for fork testing (install a feature branch from a fork
# before it merges to thensls/main). Defaults are production.
$RepoUrl    = if ($env:NSLS_TOOLKIT_REPO) { $env:NSLS_TOOLKIT_REPO } else { 'https://github.com/thensls/nsls-builder-toolkit.git' }
$RepoBranch = if ($env:NSLS_TOOLKIT_BRANCH) { $env:NSLS_TOOLKIT_BRANCH } else { 'main' }
$Tracker   = if ($env:NSLS_TRACKER_URL) { $env:NSLS_TRACKER_URL } else { 'https://web-production-6281e.up.railway.app' }

Write-Host ""
Write-Host "=== NSLS Builder Toolkit (Windows) ==="
if ($Test) { Write-Host "  (TEST MODE — installing into $ConfigDir; your real .claude is untouched)" }
Write-Host ""

# --- Prerequisites ---
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Error: git is not installed."
    Write-Host "  Install Git for Windows first: https://git-scm.com/download/win"
    exit 1
}

if ($Test) {
    New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
} elseif (-not (Test-Path $ConfigDir)) {
    Write-Host "Error: Claude Code doesn't appear to be set up ($ConfigDir not found)."
    Write-Host "  Install Claude Code first, then re-run this script."
    exit 1
}

# --- Step 1: Clone / update the org toolkit ---
Write-Host "Step 1: Installing org skills..."
New-Item -ItemType Directory -Path $LocalDir -Force | Out-Null
if (Test-Path (Join-Path $PluginDir '.git')) {
    Write-Host "  Updating existing installation..."
    & git -C $PluginDir fetch origin $RepoBranch --quiet 2>$null
    & git -C $PluginDir reset --hard "origin/$RepoBranch" --quiet 2>$null
} else {
    Write-Host "  Cloning plugin..."
    & git clone --branch $RepoBranch $RepoUrl $PluginDir --quiet
}
Write-Host "  Done."

# --- Find the claude CLI (best-effort; several steps need it) ---
$ClaudeBin = (Get-Command claude -ErrorAction SilentlyContinue).Source
if (-not $ClaudeBin) {
    foreach ($c in @(
        (Join-Path $env:APPDATA 'npm\claude.cmd'),
        (Join-Path $env:APPDATA 'npm\claude.ps1'),
        (Join-Path $env:USERPROFILE '.local\bin\claude.exe'),
        (Join-Path $env:USERPROFILE '.claude\bin\claude.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\claude\claude.exe')
    )) { if ($c -and (Test-Path $c)) { $ClaudeBin = $c; break } }
}

# --- Step 2: Enable plugin + register hooks in settings.json ---
Write-Host ""
Write-Host "Step 2: Enabling plugin and registering hooks..."

# Seed a fresh test config dir with an empty settings.json.
if ($Test -and -not (Test-Path $Settings)) { '{}' | Set-Content -Path $Settings -Encoding utf8 }

$ssCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$HooksDir\session-start.ps1`""
$ptCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$HooksDir\skill-event.ps1`""

if (Test-Path $Settings) {
    $cfg = Get-Content $Settings -Raw | ConvertFrom-Json
} else {
    $cfg = [pscustomobject]@{}
}

# Enable the local plugin (merge; preserve other enabledPlugins).
if (-not ($cfg.PSObject.Properties.Name -contains 'enabledPlugins') -or $null -eq $cfg.enabledPlugins) {
    $cfg | Add-Member -NotePropertyName enabledPlugins -NotePropertyValue ([pscustomobject]@{}) -Force
}
$cfg.enabledPlugins | Add-Member -NotePropertyName 'nsls-builder-toolkit@local' -NotePropertyValue $true -Force

if (-not ($cfg.PSObject.Properties.Name -contains 'hooks') -or $null -eq $cfg.hooks) {
    $cfg | Add-Member -NotePropertyName hooks -NotePropertyValue ([pscustomobject]@{}) -Force
}

# Drop any prior NSLS entries for an event (matched by script filename) so
# re-running never duplicates and stale registrations get replaced; non-NSLS
# hooks are kept. @(...) forces an array (PS unrolls a single match to a scalar).
function Without-Matching {
    param($EventArray, [string]$Needle)
    if ($null -eq $EventArray) { return @() }
    @($EventArray | Where-Object {
        $cmds = (@($_.hooks | ForEach-Object { $_.command })) -join "`n"
        $cmds -notlike "*$Needle*"
    })
}

# SessionStart timeout 90s: must clear git pull + a replayed ping + the live ping
# on a Railway cold start (parity with install.sh, which was killed at 15s).
$ss = @(Without-Matching $cfg.hooks.SessionStart 'session-start.ps1')
$ss += , @{ matcher = 'startup'; hooks = @(@{ type = 'command'; command = $ssCmd; timeout = 90; statusMessage = 'Syncing NSLS toolkit...' }) }

$pt = @(Without-Matching $cfg.hooks.PreToolUse 'skill-event.ps1')
$pt += , @{ matcher = 'Skill'; hooks = @(@{ type = 'command'; command = $ptCmd; timeout = 5; statusMessage = 'Logging skill use so you get NSLS credit (nothing else)…' }) }

$cfg.hooks | Add-Member -NotePropertyName SessionStart -NotePropertyValue $ss -Force
$cfg.hooks | Add-Member -NotePropertyName PreToolUse  -NotePropertyValue $pt -Force

$cfg | ConvertTo-Json -Depth 12 | Set-Content -Path $Settings -Encoding utf8
Write-Host "  Enabled plugin + registered SessionStart / PreToolUse(Skill) hooks."

# --- Step 2.5: Fire an install event to the Automation Tracker (best-effort) ---
$InstallEmail = ""
$EnvFile = Join-Path $LocalDir 'nsls-personal-toolkit\.env'
if (Test-Path $EnvFile) {
    $line = (Get-Content $EnvFile | Where-Object { $_ -match '^BUILDER_EMAIL=' } | Select-Object -First 1)
    if ($line) { $InstallEmail = ($line -replace '^BUILDER_EMAIL=', '').Trim('"') }
}
if (-not $InstallEmail) { $InstallEmail = (& git config user.email 2>$null) }
if (-not $InstallEmail) { $InstallEmail = "$($env:USERNAME)@$($env:COMPUTERNAME)" }
$InstallGh = (& gh api user --jq .login 2>$null)
try {
    $body = @{ builder_email = $InstallEmail; github_username = $InstallGh;
               platform = 'windows'; install_source = 'cc-builder-kit' } | ConvertTo-Json -Compress
    Invoke-RestMethod -Uri "$Tracker/install-event" -Method Post -Body $body `
        -ContentType 'application/json' -TimeoutSec 40 | Out-Null
} catch { }  # a failed ping never blocks the install

# --- Step 3: Install marketplace plugins ---
Write-Host ""
Write-Host "Step 3: Installing recommended plugins..."
if ($ClaudeBin) {
    function Install-Plugin {
        param([string]$Name, [string]$Spec, [string]$Market)
        $installed = (& $ClaudeBin plugin list 2>$null | Out-String)
        if ($installed -match [regex]::Escape($Name)) { Write-Host "  ${Name}: already installed"; return }
        # A native command's non-zero exit does NOT trip try/catch and Out-Null
        # hides the message — check $LASTEXITCODE and warn explicitly.
        if ($Market) {
            & $ClaudeBin plugin marketplace add $Market 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) { Write-Host "  Warning: failed to add $Name marketplace. Retry: claude plugin marketplace add $Market"; return }
        }
        Write-Host "  Installing $Name..."
        & $ClaudeBin plugin install $Spec 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Host "  Warning: '$Name' install failed. Retry: claude plugin install $Spec" }
    }
    # Migrate compound off the renamed 'every-marketplace' (parity with install.sh).
    if ((& $ClaudeBin plugin marketplace list 2>$null | Out-String) -match 'every-marketplace') {
        Write-Host "  Migrating compound-engineering off 'every-marketplace'..."
        foreach ($scope in 'local','project','user') {
            & $ClaudeBin plugin disable compound-engineering@every-marketplace --scope $scope 2>$null | Out-Null
        }
        & $ClaudeBin plugin uninstall compound-engineering@every-marketplace 2>$null | Out-Null
        & $ClaudeBin plugin uninstall compound-engineering 2>$null | Out-Null
        & $ClaudeBin plugin marketplace remove every-marketplace 2>$null | Out-Null
    }
    Install-Plugin 'superpowers' 'superpowers' ''
    Install-Plugin 'compound-engineering' 'compound-engineering@compound-engineering-plugin' `
        'https://github.com/EveryInc/compound-engineering-plugin.git'
} else {
    Write-Host "  Could not find the 'claude' CLI. After your next Claude Code session, run /setup."
}

# --- Step 3.5: Register bundled MCP servers (A1 parity: stdio + http) ---
Write-Host ""
Write-Host "Step 3.5: Registering bundled MCP servers..."
$McpJson = Join-Path $PluginDir '.mcp.json'
if ($ClaudeBin -and (Test-Path $McpJson)) {
    function Expand-Vars {
        param([string]$v)
        if ($null -eq $v) { return $v }
        $v = $v -replace [regex]::Escape('${CLAUDE_PLUGIN_ROOT}'), $PluginDir
        [regex]::Replace($v, '\$\{([A-Z0-9_]+)\}', {
            param($m) $val = [Environment]::GetEnvironmentVariable($m.Groups[1].Value)
            if ($val) { $val } else { $m.Value }
        })
    }
    function Has-Unresolved { param([string]$v) $v -match '\$\{[A-Z0-9_]+\}' }

    $servers = (Get-Content $McpJson -Raw | ConvertFrom-Json).mcpServers
    $new = 0; $skipped = @()
    foreach ($p in $servers.PSObject.Properties) {
        $name = $p.Name; $s = $p.Value
        $stype = if ($s.PSObject.Properties.Name -contains 'type') { $s.type } else { 'stdio' }
        if ($stype -eq 'http') {
            # http servers take a URL + auth header, NOT a command. The bearer
            # tokens don't exist on a fresh machine — defer to /signal-setup
            # rather than register a server that 401s silently.
            $url = Expand-Vars $s.url
            $headerArgs = @(); $blocked = (Has-Unresolved $url)
            if ($s.PSObject.Properties.Name -contains 'headers') {
                foreach ($h in $s.headers.PSObject.Properties) {
                    $hv = Expand-Vars $h.Value
                    if (Has-Unresolved $hv) { $blocked = $true }
                    $headerArgs += @('--header', "$($h.Name): $hv")
                }
            }
            if ($blocked) { $skipped += $name; continue }
            $mcpArgs = @('mcp','add','--transport','http',$name,$url,'--scope','user') + $headerArgs
        } else {
            $cmd = Expand-Vars $s.command
            $sargs = @(); if ($s.PSObject.Properties.Name -contains 'args') { $sargs = @($s.args | ForEach-Object { Expand-Vars $_ }) }
            $mcpArgs = @('mcp','add',$name,'--scope','user','--env',"CLAUDE_PLUGIN_ROOT=$PluginDir")
            if ($s.PSObject.Properties.Name -contains 'env') {
                foreach ($e in $s.env.PSObject.Properties) { $mcpArgs += @('--env', "$($e.Name)=$(Expand-Vars $e.Value)") }
            }
            $mcpArgs += @('--', $cmd) + $sargs
        }
        $out = (& $ClaudeBin @mcpArgs 2>&1) -join "`n"
        if ($out -match 'already exists') { Write-Host "  ${name}: already registered" }
        elseif ($out -match 'Added') { Write-Host "  ${name}: registered (user scope)"; $new++ }
        else { Write-Host "  ${name}: registration failed — $out" }
    }
    Write-Host "  $new MCP server(s) newly registered (restart Claude Code to load)"
    if ($skipped.Count) { Write-Host "  Deferred (needs an access token): $($skipped -join ', ') — run /signal-setup to connect these." }
} else {
    Write-Host "  Skipped — 'claude' CLI or .mcp.json not found."
}

# --- Step 4: Sync slash-command pointer skills ---
Write-Host ""
Write-Host "Step 4: Creating slash-command pointers..."
New-Item -ItemType Directory -Path $SkillsDir -Force | Out-Null
$count = 0
foreach ($skillFolder in Get-ChildItem (Join-Path $PluginDir 'skills') -Directory) {
    $src = Join-Path $skillFolder.FullName 'SKILL.md'
    if (-not (Test-Path $src)) { continue }
    $content = Get-Content $src -Raw -Encoding UTF8
    $fmName = [regex]::Match($content, '(?m)^name:\s*(.+)$')
    if (-not $fmName.Success) { continue }
    $name = $fmName.Groups[1].Value.Trim()
    $destDir = Join-Path $SkillsDir $skillFolder.Name
    $destMd  = Join-Path $destDir 'SKILL.md'
    if (Test-Path $destMd) {
        $existing = Get-Content $destMd -Raw -Encoding UTF8
        if ($existing -notmatch 'local-plugins[\\/]nsls-builder-toolkit') { continue }
    }
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
    $ptr = "~/.claude/local-plugins/nsls-builder-toolkit/skills/$($skillFolder.Name)/SKILL.md"
    $pointer = @"
---
name: $name
description: >-
  NSLS Builder Toolkit skill: $($skillFolder.Name)
---

Read and follow the full skill at ``$ptr``.
"@
    Set-Content -Path $destMd -Value $pointer -Encoding UTF8
    $count++
}
Write-Host "  $count skill pointers synced"

# --- Done ---
$skillTotal = (Get-ChildItem (Join-Path $PluginDir 'skills') -Directory).Count
Write-Host ""
Write-Host "==============================="
Write-Host "  NSLS Builder Toolkit installed!"
Write-Host "==============================="
Write-Host ""
Write-Host "  ORG SKILLS ($skillTotal skills), plus superpowers + compound-engineering."
Write-Host ""
if ($Test) {
    Write-Host "=== TEST INSTALL ==="
    Write-Host "  Everything went into: $ConfigDir (your real .claude was NOT touched)."
    Write-Host "  NOTE: -Test is only usable from the terminal via CLAUDE_CONFIG_DIR; the"
    Write-Host "  desktop app always launches against your real .claude."
    Write-Host "  Reset with:  Remove-Item -Recurse -Force `"$ConfigDir`""
} else {
    Write-Host "=== NEXT STEP ==="
    Write-Host "  1. Restart Claude Code (quit and reopen — a restart loads the MCP servers"
    Write-Host "     and hooks). In the desktop app, click Code (top left) when it reopens."
    Write-Host "  2. Say:  /setup"
    Write-Host "     It connects your tools (Slack, Google Drive, Calendar, Gmail, Fathom —"
    Write-Host "     one at a time, with you) and offers the personal productivity skills."
}
Write-Host ""

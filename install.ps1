<#
install.ps1 — Windows installer for the NSLS Builder Toolkit.

Does two things Windows builders otherwise miss (install.sh, the macOS/Linux
installer, does both natively):

  1. Installs the marketplace plugins — Superpowers and Compound Engineering —
     and migrates anyone stranded on Every's renamed 'every-marketplace'.
  2. Registers the PowerShell hook equivalents in ~/.claude/settings.json,
     because the bundled hooks use python3/bash which Windows lacks:
       SessionStart  -> hooks/session-start.ps1   (pull + sync pointers + ping)
       PreToolUse    -> hooks/skill-event.ps1      (log skill usage, deduped)

Idempotent: re-running skips already-installed plugins and replaces only the
NSLS hook entries, preserving everything else in settings.json. Run once on a
Windows machine after cloning the toolkit:
  powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
#>
$ErrorActionPreference = 'Stop'

# --- Install marketplace plugins (Superpowers + Compound Engineering) --------
# Mirror of install.sh Step 2. Wrapped so a plugin hiccup can't abort the hook
# registration below (install.sh uses `|| true` for the same reason).
try {
    $claude = $null
    $cmd = Get-Command claude -ErrorAction SilentlyContinue
    if ($cmd) { $claude = $cmd.Source }
    if (-not $claude) {
        foreach ($c in @(
            (Join-Path $env:USERPROFILE '.local\bin\claude.exe'),
            (Join-Path $env:USERPROFILE '.claude\bin\claude.exe'),
            (Join-Path $env:APPDATA 'npm\claude.cmd'))) {
            if ($c -and (Test-Path $c)) { $claude = $c; break }
        }
    }

    if (-not $claude) {
        Write-Host "  Could not find the 'claude' CLI in PATH. Install plugins manually:"
        Write-Host "    claude plugin install superpowers"
        Write-Host "    claude plugin marketplace add https://github.com/EveryInc/compound-engineering-plugin.git"
        Write-Host "    claude plugin install compound-engineering@compound-engineering-plugin"
    } else {
        function Install-Plugin {
            param([string]$Name, [string]$Spec, [string]$Market)
            # Grep key is the bare plugin id, matched against `plugin list`.
            $installed = (& $claude plugin list 2>$null | Out-String)
            if ($installed -match [regex]::Escape($Name)) {
                Write-Host "  ${Name}: already installed"
                return
            }
            if ($Market) {
                Write-Host "  Adding $Name marketplace..."
                & $claude plugin marketplace add $Market 2>&1 | Out-Null
            }
            Write-Host "  Installing $Name..."
            & $claude plugin install $Spec 2>&1 | Out-Null
        }

        # Every renamed 'every-marketplace' -> 'compound-engineering-plugin' and
        # bumped to 3.x. Builders installed before the rename are pinned to the
        # stale registration; clear it before installing so the current plugin
        # is pulled. Removing the marketplace cascades to drop its plugin, so the
        # migration completes even if the uninstall calls are no-ops.
        function Migrate-CompoundMarketplace {
            if ((& $claude plugin marketplace list 2>$null | Out-String) -notmatch 'every-marketplace') { return }
            Write-Host "  Migrating compound-engineering off the renamed 'every-marketplace'..."
            foreach ($scope in 'local', 'project', 'user') {
                & $claude plugin disable compound-engineering@every-marketplace --scope $scope 2>$null | Out-Null
            }
            & $claude plugin uninstall compound-engineering@every-marketplace 2>$null | Out-Null
            & $claude plugin uninstall compound-engineering 2>$null | Out-Null
            & $claude plugin marketplace remove every-marketplace 2>$null | Out-Null
            if ((& $claude plugin marketplace list 2>$null | Out-String) -match 'every-marketplace') {
                Write-Host "  Warning: could not fully remove 'every-marketplace'. Run manually:"
                Write-Host "    claude plugin uninstall compound-engineering; claude plugin marketplace remove every-marketplace"
            }
        }

        Write-Host "Installing recommended plugins..."
        Install-Plugin 'superpowers' 'superpowers' ''
        Migrate-CompoundMarketplace
        Install-Plugin 'compound-engineering' 'compound-engineering@compound-engineering-plugin' `
            'https://github.com/EveryInc/compound-engineering-plugin.git'
    }
} catch {
    Write-Host "  Note: plugin install step failed ($($_.Exception.Message)) — run the manual commands above later."
}

$ClaudeDir   = Join-Path $env:USERPROFILE '.claude'
$Settings    = Join-Path $ClaudeDir 'settings.json'
$HooksDir    = Join-Path $ClaudeDir 'local-plugins\nsls-builder-toolkit\hooks'

$ssCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$HooksDir\session-start.ps1`""
$ptCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$HooksDir\skill-event.ps1`""

# Load existing settings (preserve all other keys) or start fresh.
if (Test-Path $Settings) {
    $cfg = Get-Content $Settings -Raw | ConvertFrom-Json
} else {
    New-Item -ItemType Directory -Path $ClaudeDir -Force | Out-Null
    $cfg = [pscustomobject]@{}
}
if (-not ($cfg.PSObject.Properties.Name -contains 'hooks') -or $null -eq $cfg.hooks) {
    $cfg | Add-Member -NotePropertyName hooks -NotePropertyValue ([pscustomobject]@{}) -Force
}

# Drop any prior NSLS entries for an event (so re-running doesn't duplicate and
# stale local-path registrations get replaced), keeping non-NSLS hooks intact.
# Matched by script filename so it catches both toolkit and older local paths.
# @(...) forces an array (PowerShell unrolls a single match to a scalar).
function Without-Matching {
    param($EventArray, [string]$Needle)
    if ($null -eq $EventArray) { return @() }
    @($EventArray | Where-Object {
        $cmds = (@($_.hooks | ForEach-Object { $_.command })) -join "`n"
        $cmds -notlike "*$Needle*"
    })
}

$ss = @(Without-Matching $cfg.hooks.SessionStart 'session-start.ps1')
$ss += , @{ matcher = 'startup'; hooks = @(@{ type = 'command'; command = $ssCmd; timeout = 15; statusMessage = 'Syncing NSLS toolkit...' }) }

$pt = @(Without-Matching $cfg.hooks.PreToolUse 'skill-event.ps1')
$pt += , @{ matcher = 'Skill'; hooks = @(@{ type = 'command'; command = $ptCmd; timeout = 5 }) }

$cfg.hooks | Add-Member -NotePropertyName SessionStart -NotePropertyValue $ss -Force
$cfg.hooks | Add-Member -NotePropertyName PreToolUse  -NotePropertyValue $pt -Force

$cfg | ConvertTo-Json -Depth 12 | Set-Content -Path $Settings -Encoding utf8
Write-Host "Registered NSLS Windows hooks in $Settings"
Write-Host "  SessionStart -> session-start.ps1 (pull + sync + ping)"
Write-Host "  PreToolUse(Skill) -> skill-event.ps1 (skill logging)"
Write-Host "Restart Claude Code for the hooks to take effect."

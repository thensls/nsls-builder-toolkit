<#
install.ps1 — Windows installer for the NSLS Builder Toolkit hooks.

The toolkit's plugin hooks (hooks/hooks.json) use python3 (SessionStart) and
bash (PreToolUse skill logging), neither of which runs on Windows — so Windows
builders never pinged the tracker or logged skill usage. This registers the
PowerShell equivalents in ~/.claude/settings.json:

  SessionStart  -> hooks/session-start.ps1   (pull + sync pointers + ping)
  PreToolUse    -> hooks/skill-event.ps1      (log skill usage, deduped)

Idempotent: re-running replaces only the NSLS entries, preserving everything
else in settings.json. Run once on a Windows machine after cloning the toolkit:
  powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1
#>
$ErrorActionPreference = 'Stop'

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

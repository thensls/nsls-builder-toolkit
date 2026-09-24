# collector_evidence.ps1 - dot-sourced by skill-event.ps1 and session-ping.ps1.
# Windows copy of hooks/collector_evidence.py; same contract, same rules.
#
# The NSLS usage collector writes
#   <CLAUDE_CONFIG_DIR or %USERPROFILE%\.claude>\.nsls-collector\reported.json
# containing exactly {machine_id, at, version}, and only after a clean run.
# While it is fresh the collector already reports this machine's daily session
# and skill use, so session-ping.ps1 adds collector_backed=true (the tracker
# then skips ONLY the daily-session credit) and skill-event.ps1 posts nothing.
#
# Fresh = at most 4096 bytes, parses as a JSON object, machine_id is a
# non-empty string, and at is ISO-8601 UTC (YYYY-MM-DDTHH:MM:SS[.fff] then Z
# or +00:00) no more than 7 days old and no more than 1 day in the future.
# Untrusted input: anything unexpected returns $false, never throws.
#
# ASCII only, PowerShell 5.1 compatible, no BOM.

function Test-CollectorEvidenceFresh {
    $ErrorActionPreference = 'Stop'
    try {
        $cfg = $env:CLAUDE_CONFIG_DIR
        if ([string]::IsNullOrWhiteSpace($cfg)) { $cfg = Join-Path $env:USERPROFILE '.claude' }
        $path = Join-Path (Join-Path $cfg '.nsls-collector') 'reported.json'
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
        if ((Get-Item -LiteralPath $path).Length -gt 4096) { return $false }
        $raw = [System.IO.File]::ReadAllText($path)
        $obj = $raw | ConvertFrom-Json
        if (-not ($obj -is [System.Management.Automation.PSCustomObject])) { return $false }
        $mid = $obj.machine_id
        if (-not ($mid -is [string]) -or $mid.Length -eq 0) { return $false }
        # Read `at` from the raw text: PowerShell 7's ConvertFrom-Json turns
        # date-like strings into DateTime and loses the UTC marker we check.
        $m = [regex]::Match($raw, '"at"\s*:\s*"([^"]*)"')
        if (-not $m.Success) { return $false }
        $t = [regex]::Match($m.Groups[1].Value, '^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?(Z|\+00:00)\z')
        if (-not $t.Success) { return $false }
        $g = $t.Groups
        $at = [DateTime]::new([int]$g[1].Value, [int]$g[2].Value, [int]$g[3].Value,
                              [int]$g[4].Value, [int]$g[5].Value, [int]$g[6].Value,
                              [DateTimeKind]::Utc)
        $ageDays = ([DateTime]::UtcNow - $at).TotalDays
        return ($ageDays -le 7 -and $ageDays -ge -1)
    } catch {
        return $false
    }
}

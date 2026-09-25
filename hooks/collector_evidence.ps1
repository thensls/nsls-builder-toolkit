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
# Fresh = a regular file (not a reparse point, pipe or device, so the read
# cannot block) of at most 4096 bytes whose WHOLE text is one flat JSON object
# of EXACTLY the keys machine_id, at and version, each once, any order, each
# value a plain printable-ASCII string with no escapes (nesting, duplicates,
# extra or missing keys and trailing commas all fail closed); machine_id
# non-empty; at a real UTC calendar time YYYY-MM-DDTHH:MM:SS[.fff] then Z or
# +00:00, no more than 7 days old and no more than 1 day in the future.
# The grammar is the same regex as collector_evidence.py and skill-event.sh.
# Untrusted input: anything unexpected returns $false, never throws.
#
# ASCII only, PowerShell 5.1 compatible, no BOM.

function Test-CollectorEvidenceFresh {
    param([Nullable[DateTime]]$Now = $null)
    $ErrorActionPreference = 'Stop'
    try {
        $cfg = $env:CLAUDE_CONFIG_DIR
        if ([string]::IsNullOrWhiteSpace($cfg)) { $cfg = Join-Path $env:USERPROFILE '.claude' }
        $path = Join-Path (Join-Path $cfg '.nsls-collector') 'reported.json'
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
        $item = Get-Item -LiteralPath $path -Force
        if (-not ($item -is [System.IO.FileInfo])) { return $false }
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { return $false }
        if ($item.Length -gt 4096) { return $false }
        $bytes = [System.IO.File]::ReadAllBytes($path)
        if ($bytes.Length -gt 4096) { return $false }
        foreach ($b in $bytes) { if ($b -gt 127) { return $false } }
        $raw = [System.Text.Encoding]::ASCII.GetString($bytes)
        $ws = '[ \t\r\n]*'
        $str = '"([\x20\x21\x23-\x5B\x5D-\x7E]*)"'
        $member = $ws + $str + $ws + ':' + $ws + $str + $ws
        $doc = [regex]::Match($raw, '\A' + $ws + '\{' + $member + ',' + $member + ',' + $member + '\}' + $ws + '\z')
        if (-not $doc.Success) { return $false }
        $fields = @{}
        foreach ($i in 1, 3, 5) {
            $k = $doc.Groups[$i].Value
            if (@('machine_id', 'at', 'version') -cnotcontains $k) { return $false }
            if ($fields.ContainsKey($k)) { return $false }
            $fields[$k] = $doc.Groups[$i + 1].Value
        }
        if ($fields['machine_id'].Length -eq 0) { return $false }
        $t = [regex]::Match($fields['at'], '\A([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?(Z|\+00:00)\z')
        if (-not $t.Success) { return $false }
        $g = $t.Groups
        # Throws (-> $false) on Feb 30, hour 24 and the like.
        $at = [DateTime]::new([int]$g[1].Value, [int]$g[2].Value, [int]$g[3].Value,
                              [int]$g[4].Value, [int]$g[5].Value, [int]$g[6].Value,
                              [DateTimeKind]::Utc)
        $clock = if ($null -ne $Now) { $Now.Value.ToUniversalTime() } else { [DateTime]::UtcNow }
        $ageDays = ($clock - $at).TotalDays
        return ($ageDays -le 7 -and $ageDays -ge -1)
    } catch {
        return $false
    }
}

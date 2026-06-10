# session-ping.ps1 — Windows session ping (run DETACHED by session-start.ps1).
# Windows counterpart to the session_ping() in session-start.py. POSTs to the
# tracker /session-ping so merged-PR credits, stage advancement, and the daily
# session point are recorded. Launched detached so the proxy's cold-start
# latency (15-27s) never delays session start. Fails silently; logs any
# credit/stage messages to nsls-session-ping.log (not shown inline).
$ErrorActionPreference = 'SilentlyContinue'
$ProxyUrl = 'https://web-production-6281e.up.railway.app'
$LogFile  = Join-Path $env:USERPROFILE '.claude\hooks\nsls-session-ping.log'

function Read-EnvValue {
    param([string]$EnvPath, [string]$Key)
    if (-not (Test-Path $EnvPath)) { return '' }
    foreach ($line in Get-Content $EnvPath -Encoding UTF8) {
        if ($line -match ('^' + [regex]::Escape($Key) + '=(.*)$')) { return $Matches[1].Trim().Trim('"') }
    }
    return ''
}

$envFile = Join-Path $env:USERPROFILE '.claude\local-plugins\nsls-personal-toolkit\.env'
$email = Read-EnvValue -EnvPath $envFile -Key 'BUILDER_EMAIL'
if (-not $email) { try { $email = (& git config user.email) } catch {} }
$email = "$email".Trim()
if ([string]::IsNullOrWhiteSpace($email)) { exit 0 }
$github = Read-EnvValue -EnvPath $envFile -Key 'GITHUB_USERNAME'
$builderDir = Join-Path $env:USERPROFILE '.claude\local-plugins\nsls-builder-toolkit'
$toolkit = if (Test-Path $builderDir) { 'both' } else { 'personal' }

$payload = @{ builder_email = $email; toolkit = $toolkit; github_username = $github; platform = 'windows' } | ConvertTo-Json -Compress
try {
    $resp = Invoke-RestMethod -Uri "$ProxyUrl/session-ping" -Method Post -Body $payload -ContentType 'application/json' -TimeoutSec 30 -ErrorAction Stop
} catch { exit 0 }

$out = @()
foreach ($pr in @($resp.new_pr_credits)) { if ($pr) { $out += "PR $($pr.pr) to $($pr.repo) credited." } }
if ($resp.stage_advanced) { $out += "Advanced to $($resp.stage_advanced.to)." }
if ($out.Count -gt 0) {
    Add-Content -Path $LogFile -Value ("[" + (Get-Date).ToString('s') + "] " + ($out -join ' '))
}
exit 0

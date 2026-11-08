# windows-ci: ps51 ps7 | Student-data activity log through run-hook.sh: logs record lookups, never an input value, always exits 0
# Runs the student-data log the way hooks.json runs it on a PC: PowerShell pipes
# the payload into Git Bash, run-hook.sh resolves a Python, the hook writes the
# log. Proves, end to end on Windows:
#   1. a registered vendor server is logged by host; the same name on another
#      host is not;
#   2. a HubSpot connector record tool is logged and a reviewed content tool is
#      not; PostHog, Customer.io and Hex connector tools are logged;
#   3. a Drive call mentioning a roster is logged with the detector label;
#   4. no input value ever reaches the log;
#   5. malformed stdin and a missing .claude.json exit 0 and print nothing.
# Everything runs against a scratch HOME and config dir. ASCII only, PS 5.1
# compatible. All values are made up.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path

$script:failures = 0
function Check([string]$Label, [bool]$Cond, [string]$Detail = '') {
    if ($Cond) { Write-Host "ok   $Label" } else { Write-Host "FAIL $Label"; if ($Detail) { Write-Host "     saw: $Detail" }; $script:failures++ }
}

function Find-Bash {
    if ($env:OS -eq 'Windows_NT') {
        $git = Get-Command git -ErrorAction SilentlyContinue
        if ($git) {
            $cand = Join-Path (Split-Path (Split-Path $git.Source -Parent) -Parent) 'bin\bash.exe'
            if (Test-Path -LiteralPath $cand) { return $cand }
        }
        if ($env:ProgramFiles) {
            $pf = Join-Path $env:ProgramFiles 'Git\bin\bash.exe'
            if (Test-Path -LiteralPath $pf) { return $pf }
        }
    }
    $b = Get-Command bash -ErrorAction SilentlyContinue
    if ($b) { return $b.Source }
    return $null
}

$bash = Find-Bash
Check 'bash is available (install.ps1 requires Git for Windows)' ($null -ne $bash)
if (-not $bash) { exit 1 }
$launcher = (Join-Path $repo 'hooks/run-hook.sh') -replace '\\', '/'
# What this shell puts on a pipe, so a lane that differs shows why (5.1 can add
# a byte-order mark; the hook tolerates one).
$probe = 'A' | & $bash -c 'od -An -tx1' | Out-String
Write-Host "info bytes this shell pipes for 'A':$($probe.TrimEnd())"

$scratch = Join-Path ([System.IO.Path]::GetTempPath()) ('nsls-sdlog-' + [guid]::NewGuid().ToString('N'))
$home2 = Join-Path $scratch 'home'
$cfg = Join-Path $home2 '.claude'
New-Item -ItemType Directory -Path $cfg -Force | Out-Null
$claudeJson = Join-Path $home2 '.claude.json'
$log = Join-Path $cfg '.nsls-student-data-log.jsonl'
$utf8 = New-Object System.Text.UTF8Encoding $false

$saved = @{}
foreach ($k in 'HOME', 'USERPROFILE', 'CLAUDE_CONFIG_DIR', 'CLAUDE_PLUGIN_ROOT', 'CLAUDE_PROJECT_DIR') {
    $saved[$k] = [Environment]::GetEnvironmentVariable($k)
}

function Get-LogLines {
    if (-not (Test-Path -LiteralPath $log)) { return @() }
    return @(Get-Content -LiteralPath $log | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })
}

# One hook run: returns @(exit code, stdout, new log records).
function Invoke-Hook([string]$Payload) {
    $before = @(Get-LogLines).Count
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = $Payload | & $bash $launcher student-data-log | Out-String
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $prev }
    $all = @(Get-LogLines)
    $new = @()
    if ($all.Count -gt $before) { $new = @($all[$before..($all.Count - 1)]) }
    return @($code, $out, $new)
}

function Payload([string]$Tool, [string]$InputJson = '{}') {
    return '{"session_id":"sess-ps","hook_event_name":"PreToolUse","tool_name":"' + $Tool + '","tool_input":' + $InputJson + '}'
}

function Expect([string]$Label, [string]$Tool, [string]$InputJson, [string]$Want) {
    # $Want: '' for "nothing logged", else "route/platform/detector".
    $r = Invoke-Hook (Payload $Tool $InputJson)
    $got = (@($r[2]) | ForEach-Object { "$($_.route)/$($_.platform)/$($_.detector)" }) -join ','
    Check $Label (($r[0] -eq 0) -and ($r[1].Trim() -eq '') -and ($got -eq $Want)) "(exit $($r[0]); out '$($r[1].Trim())'; logged '$got')"
}

try {
    $env:HOME = $home2
    $env:USERPROFILE = $home2
    $env:CLAUDE_CONFIG_DIR = $cfg
    $env:CLAUDE_PLUGIN_ROOT = $repo -replace '\\', '/'
    Remove-Item Env:CLAUDE_PROJECT_DIR -ErrorAction SilentlyContinue

    [System.IO.File]::WriteAllText($claudeJson, '{"mcpServers":{"hubspot-records":{"type":"http","url":"https://mcp.hubspot.com"},"hubspot-pilot":{"type":"http","url":"https://mcp.hubspot.com"},"posthog-records":{"type":"http","url":"https://evil.example.com/mcp"}}}', $utf8)

    $secret = '{"zz_input_key":"Zzyzx Testperson","email":"zz.test@example-state.edu","id":"rec-424242"}'
    Expect 'a registered server on its record host is logged' 'mcp__hubspot-records__search_crm_objects' $secret 'registered/hubspot/host'
    Expect 'a record host under another name (hubspot-pilot) is logged' 'mcp__hubspot-pilot__get_crm_objects' '{}' 'registered/hubspot/host'
    Expect 'the same name on another host is not logged' 'mcp__posthog-records__query-run' $secret ''
    Expect 'a HubSpot connector record tool is logged' 'mcp__claude_ai_HubSpot__search_crm_objects' $secret 'connector/hubspot/name'
    Expect 'a HubSpot connector record tool (desktop id) is logged' 'mcp__39bb8873-bcdf-4c02-95b1-59fd7ba9b014__query_crm_data' $secret 'connector/hubspot/id'
    Expect 'a HubSpot content tool is not logged' 'mcp__claude_ai_HubSpot__manage_blog_post' '{}' ''
    Expect 'a PostHog connector tool is logged' 'mcp__claude_ai_PostHog__query-run' $secret 'connector/posthog/name'
    Expect 'a Customer.io connector tool is logged' 'mcp__claude_ai_Customer_io__get_customer' $secret 'connector/customerio/name'
    Expect 'a Hex connector tool is logged' 'mcp__claude_ai_Hex__run_project' $secret 'connector/hex/name'
    Expect 'Drive with "roster" logs the detector' 'mcp__claude_ai_Google_Drive__search_files' '{"query":"fall roster"}' 'carrier/google_drive/roster'
    Expect 'an ordinary Drive search is not logged' 'mcp__claude_ai_Google_Drive__search_files' '{"query":"budget plan"}' ''

    $text = ''
    if (Test-Path -LiteralPath $log) { $text = [System.IO.File]::ReadAllText($log) }
    $leaks = @('Zzyzx', 'example-state', '@', 'rec-424242', 'zz_input_key', 'fall roster') | Where-Object { $text.Contains($_) }
    Check 'the log never holds an input value' (($text.Length -gt 0) -and (@($leaks).Count -eq 0)) "(leaked: $($leaks -join ', '))"
    $fields = 'detector,platform,route,server,session_id,tool,toolkit_version,ts'
    $bad = @(Get-LogLines | Where-Object { (($_.PSObject.Properties.Name | Sort-Object) -join ',') -ne $fields })
    Check 'every line has exactly the agreed fields' ($bad.Count -eq 0) "($($bad.Count) lines differ)"

    foreach ($raw in '{not json', '[1, 2]', '') {
        $r = Invoke-Hook $raw
        Check "malformed stdin '$raw' exits 0 silently" (($r[0] -eq 0) -and ($r[1].Trim() -eq '') -and (@($r[2]).Count -eq 0)) "(exit $($r[0]); out '$($r[1].Trim())')"
    }
    Remove-Item -LiteralPath $claudeJson -Force
    Expect 'with no .claude.json a named server exits 0 and is not logged' 'mcp__hubspot-records__search_crm_objects' '{}' ''
    Expect 'and connector tools are still logged' 'mcp__claude_ai_Hex__search_projects' '{}' 'connector/hex/name'
}
finally {
    # The scratch folder is left in the temp directory to age out.
    foreach ($k in $saved.Keys) { [Environment]::SetEnvironmentVariable($k, $saved[$k]) }
}

if ($script:failures -gt 0) { Write-Host "`n$($script:failures) check(s) FAILED"; exit 1 }
Write-Host "`nall checks passed"
exit 0

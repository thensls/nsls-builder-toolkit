# windows-ci: ps51 ps7 | install.ps1 never updates a toolkit copy from a fork: it keeps it aside and clones NSLS fresh
# install.ps1's Step 1, run for real. A copy cloned from a builder's own fork
# "updated" from that fork: never NSLS's releases, and a reset onto a main
# hundreds of commits old, reported as installed (a builder's Mac, 2026-11; a
# PC with a fork is in the same position). Now a copy whose origin is not NSLS
# is kept aside untouched and a fresh copy cloned, download first, so a failed
# download changes nothing. The block is lifted from install.ps1 between its
# own markers and run in a child PowerShell, so it can never test a copy and
# an early `exit` stays in the child.
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$src = Get-Content (Join-Path $repo 'install.ps1') -Raw
$start = $src.IndexOf('# --- Step 1: Clone / update the org toolkit ---')
$end = $src.IndexOf('# --- Find the claude CLI')
$fnStart = $src.IndexOf('function Invoke-Native')
$fnEnd = $src.IndexOf("`n}", $fnStart)
if ($start -lt 0 -or $end -le $start -or $fnStart -lt 0 -or $fnEnd -le $fnStart) {
    Write-Host 'FAIL could not find Step 1 or Invoke-Native in install.ps1'; exit 1
}
$block = $src.Substring($start, $end - $start)
$invokeNative = $src.Substring($fnStart, $fnEnd + 2 - $fnStart)
$shell = (Get-Process -Id $PID).Path

$script:failures = 0
function Check([string]$Label, [bool]$Cond, [string]$Detail = '') {
    if ($Cond) { Write-Host "ok   $Label" } else { Write-Host "FAIL $Label"; if ($Detail) { Write-Host "     saw: $Detail" }; $script:failures++ }
}

$scratch = Join-Path ([IO.Path]::GetTempPath()) ('keepsfork-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
$saved = @{ GIT_CONFIG_GLOBAL = $env:GIT_CONFIG_GLOBAL; GIT_CONFIG_NOSYSTEM = $env:GIT_CONFIG_NOSYSTEM; GIT_TERMINAL_PROMPT = $env:GIT_TERMINAL_PROMPT }
$gitconfig = Join-Path $scratch 'gitconfig'
Set-Content -LiteralPath $gitconfig -Value "[user]`n`tname = T`n`temail = t@t.test`n[commit]`n`tgpgsign = false`n[init]`n`tdefaultBranch = main`n[protocol `"file`"]`n`tallow = always`n[core]`n`tautocrlf = false"
$env:GIT_CONFIG_GLOBAL = $gitconfig
$env:GIT_CONFIG_NOSYSTEM = '1'
$env:GIT_TERMINAL_PROMPT = '0'

function G([string]$Dir) { $out = (& git -C $Dir @args 2>&1 | ForEach-Object { "$_" }) -join "`n"; return $out.Trim() }

function New-World([string]$Name) {
    $root = Join-Path $scratch $Name
    $seed = Join-Path $root 'seed'
    New-Item -ItemType Directory -Path $seed -Force | Out-Null
    $null = G $seed init --quiet
    Set-Content -LiteralPath (Join-Path $seed 'skill.md') -Value 'v1'
    $null = G $seed add .
    $null = G $seed commit --quiet -m v1
    $fork = Join-Path $root 'fork.git'
    $null = G $root clone --quiet --bare $seed $fork
    Set-Content -LiteralPath (Join-Path $seed 'skill.md') -Value 'v2, released by NSLS after the fork'
    $null = G $seed add .
    $null = G $seed commit --quiet -m v2
    $nsls = Join-Path $root 'nsls.git'
    $null = G $root clone --quiet --bare $seed $nsls
    $cfg = Join-Path $root '.claude'
    New-Item -ItemType Directory -Path (Join-Path $cfg 'local-plugins') -Force | Out-Null
    return @{ Root = $root; Nsls = $nsls; Fork = $fork; Cfg = $cfg; Local = (Join-Path $cfg 'local-plugins');
              Plugin = (Join-Path $cfg 'local-plugins\nsls-builder-toolkit') }
}

function Invoke-Step1($World, [string]$RepoUrl) {
    $runner = Join-Path $World.Root 'runner.ps1'
    $q = { param($s) "'" + ($s -replace "'", "''") + "'" }
    $text = "`$RunningFromFile = `$true`n" +
            "`$ConfigDir = $(& $q $World.Cfg)`n" +
            "`$LocalDir = Join-Path `$ConfigDir 'local-plugins'`n" +
            "`$PluginDir = Join-Path `$LocalDir 'nsls-builder-toolkit'`n" +
            "`$RepoUrl = $(& $q $RepoUrl)`n" +
            "`$RepoBranch = 'main'`n" + $invokeNative + "`n" + $block
    Set-Content -LiteralPath $runner -Value $text -Encoding UTF8
    $out = (& $shell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $runner 2>&1 | ForEach-Object { "$_" }) -join "`n"
    return @{ Code = $LASTEXITCODE; Out = $out }
}

function Kept($World) { @(Get-ChildItem -LiteralPath $World.Local -Directory | Where-Object { $_.Name -like 'nsls-builder-toolkit.kept-*' }) }

try {
    # The builder's fork, on a feature branch, with an edit never committed.
    $w = New-World 'fork-copy'
    $null = G $w.Local clone --quiet $w.Fork $w.Plugin
    $null = G $w.Plugin checkout --quiet -b add-my-skill
    Set-Content -LiteralPath (Join-Path $w.Plugin 'mine.md') -Value 'the builder''s own skill'
    $null = G $w.Plugin add .
    $null = G $w.Plugin commit --quiet -m mine
    Set-Content -LiteralPath (Join-Path $w.Plugin 'skill.md') -Value 'an edit the builder never committed'
    $r = Invoke-Step1 $w $w.Nsls
    $kept = Kept $w
    Check 'a copy from a fork: the installer finishes' ($r.Code -eq 0) $r.Out
    Check 'the toolkit folder is now a fresh copy of NSLS, on main' (
        (G $w.Plugin remote get-url origin) -eq $w.Nsls -and
        (G $w.Plugin rev-parse HEAD) -eq (G $w.Nsls rev-parse main) -and
        (G $w.Plugin rev-parse --abbrev-ref HEAD) -eq 'main') $r.Out
    Check 'the old copy is kept beside it' ($kept.Count -eq 1) "$($kept.Count)"
    if ($kept.Count -eq 1) {
        $old = $kept[0].FullName
        Check 'with its branch, its commit and the uncommitted edit' (
            (G $old rev-parse --abbrev-ref HEAD) -eq 'add-my-skill' -and
            (G $old log -1 --format=%s) -eq 'mine' -and
            (Get-Content -LiteralPath (Join-Path $old 'skill.md') -Raw).Trim() -eq 'an edit the builder never committed')
        Check 'the installer says where it went' ($r.Out -like "*$old*" -and $r.Out -like "*never got NSLS's releases*") $r.Out
    }
    Check 'no half-finished download is left behind' (@(Get-ChildItem -LiteralPath $w.Local -Directory | Where-Object { $_.Name -like '*.new-*' }).Count -eq 0)

    # A copy that follows NSLS, with the fork as a second remote: updated in place.
    $w = New-World 'nsls-copy'
    $null = G $w.Local clone --quiet $w.Nsls $w.Plugin
    $null = G $w.Plugin reset --quiet --hard HEAD~1
    $null = G $w.Plugin remote add fork $w.Fork
    $r = Invoke-Step1 $w $w.Nsls
    Check 'a copy that follows NSLS is updated in place, never moved' (
        $r.Code -eq 0 -and (Kept $w).Count -eq 0 -and
        (G $w.Plugin rev-parse HEAD) -eq (G $w.Nsls rev-parse main) -and
        (G $w.Plugin remote get-url fork) -eq $w.Fork) $r.Out

    # Macroscope on PR #343: a sign-in in the old address is never printed.
    $w = New-World 'signin'
    $null = G $w.Local clone --quiet $w.Fork $w.Plugin
    $null = G $w.Plugin remote set-url origin 'https://x-access-token:SECRET123@github.com/bdoyer-nsls/nsls-builder-toolkit.git'
    $r = Invoke-Step1 $w $w.Nsls
    Check 'a sign-in in the old copy''s address is never printed' (
        $r.Code -eq 0 -and $r.Out -notlike '*SECRET123*' -and $r.Out -notlike '*x-access-token*' -and
        $r.Out -like '*https://github.com/bdoyer-nsls/nsls-builder-toolkit.git*') $r.Out

    # Macroscope on PR #343: an extra working folder made from the old copy survives the move.
    $w = New-World 'worktree'
    $null = G $w.Local clone --quiet $w.Fork $w.Plugin
    $extra = Join-Path $w.Root 'my-other-checkout'
    $null = G $w.Plugin worktree add --quiet -b side-work $extra
    $r = Invoke-Step1 $w $w.Nsls
    $kept = Kept $w
    $null = & git -C $extra status --short 2>&1
    $linkedOk = ($LASTEXITCODE -eq 0)
    Check 'an extra working folder made from the old copy still works after the move' (
        $r.Code -eq 0 -and $kept.Count -eq 1 -and $linkedOk) $r.Out

    # A fresh copy that cannot be downloaded: the old folder stays exactly as it was.
    $w = New-World 'offline'
    $null = G $w.Local clone --quiet $w.Fork $w.Plugin
    $before = G $w.Plugin rev-parse HEAD
    $r = Invoke-Step1 $w (Join-Path $w.Root 'unreachable.git')
    $left = @(Get-ChildItem -LiteralPath $w.Local -Directory | ForEach-Object { $_.Name })
    Check 'a download that fails: stops, and changes nothing' (
        $r.Code -eq 1 -and $r.Out -like '*Nothing was changed*' -and
        $left.Count -eq 1 -and $left[0] -eq 'nsls-builder-toolkit' -and
        (G $w.Plugin rev-parse HEAD) -eq $before -and
        (G $w.Plugin remote get-url origin) -eq $w.Fork) "$($left -join ', ') | $($r.Out)"

    # The same repository written another way is the same; a fork is not.
    $keyFn = $src.Substring($src.IndexOf('function Get-RepoKey'))
    $keyFn = $keyFn.Substring(0, $keyFn.IndexOf("`n}") + 2)
    Invoke-Expression $keyFn
    $nslsUrl = 'https://github.com/thensls/nsls-builder-toolkit.git'
    $same = @('https://github.com/thensls/nsls-builder-toolkit', 'git@github.com:thensls/nsls-builder-toolkit.git',
              'ssh://git@github.com/thensls/nsls-builder-toolkit', 'https://x-access-token:abc@github.com/thensls/nsls-builder-toolkit.git',
              'https://github.com/TheNSLS/nsls-builder-toolkit/')
    $differ = @('https://github.com/bdoyer-nsls/nsls-builder-toolkit.git', 'https://github.com/thensls/nsls-builder-toolkit-old', '')
    Check 'https, ssh, a sign-in, .git, capitals and a trailing slash are all NSLS' (
        @($same | Where-Object { (Get-RepoKey $_) -ne (Get-RepoKey $nslsUrl) }).Count -eq 0)
    Check 'a fork, another repository, or no origin are not' (
        @($differ | Where-Object { (Get-RepoKey $_) -eq (Get-RepoKey $nslsUrl) }).Count -eq 0)
} finally {
    foreach ($k in $saved.Keys) { if ($null -eq $saved[$k]) { Remove-Item -Path "Env:$k" -ErrorAction SilentlyContinue } else { Set-Item -Path "Env:$k" -Value $saved[$k] } }
    Remove-Item -Recurse -Force -LiteralPath $scratch -ErrorAction SilentlyContinue
}

if ($script:failures -gt 0) { Write-Host "$($script:failures) check(s) failed"; exit 1 }
Write-Host 'all checks passed'

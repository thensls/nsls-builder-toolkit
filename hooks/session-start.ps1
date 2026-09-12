# session-start.ps1 - Windows SessionStart hook for the NSLS toolkits.
# Windows counterpart to session-start.py (which needs python3 that Windows
# lacks). Does the same three things:
#   1. git pull both toolkits to get latest
#   2. re-sync pointer skills into ~/.claude/skills/
#   3. fire the tracker session ping (detached, non-blocking)
# Fast and silent on failure. Registered in settings.json by install.ps1.
$ErrorActionPreference = 'SilentlyContinue'

$ClaudeDir   = Join-Path $env:USERPROFILE '.claude'
$SkillsDir   = Join-Path $ClaudeDir 'skills'
$LocalDir    = Join-Path $ClaudeDir 'local-plugins'
$BuilderDir  = Join-Path $LocalDir  'nsls-builder-toolkit'
$PersonalDir = Join-Path $LocalDir  'nsls-personal-toolkit'
$Marker      = 'local-plugins\nsls-'

# --- 1. git pull (direct call; the prior Start-Process form failed silently on
#        Windows, freezing toolkits weeks behind). ff-only never merges.
#        Bare pull (no remote/refspec) follows each checkout's configured
#        upstream, so a customized fork (NSLS_PERSONAL_REPO/BRANCH) or a pinned
#        checkout is never fast-forwarded onto a branch it doesn't track.
#        A pull refused by the checkout's own state (divergence, dirty tree) is
#        announced on stdout - SessionStart stdout reaches the model's context -
#        so a frozen toolkit is never silent. Offline failures stay quiet. ---
$env:GIT_TERMINAL_PROMPT = '0'   # credentialed remotes fail fast, never prompt-hang the hook
foreach ($dir in @($BuilderDir, $PersonalDir)) {
    if (-not (Test-Path $dir)) { continue }
    $pullOut = (& git -C $dir pull --ff-only --quiet 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0 -and $pullOut -match 'fast-forward|would be overwritten|unmerged|not concluded') {
        # Two gates, not one - matching session-start.py's `_checkout_blocks_update`.
        # The regex says git's complaint LOOKS checkout-local; this checks whether it
        # IS. Clean, up-to-date checkouts were reported FROZEN every session, sending
        # builders to back up local changes that did not exist.
        $dirty  = (& git -C $dir status --porcelain 2>$null | Out-String).Trim()
        $ahead  = (& git -C $dir rev-list --count '@{u}..HEAD' 2>$null | Out-String).Trim()
        # `@{u}`, not origin/main: a fork checkout tracks something else, and the
        # pull being diagnosed follows the same upstream.
        $commits = 0
        if ($LASTEXITCODE -eq 0 -and $ahead -match '^\d+$') { $commits = [int]$ahead }
        $blocker = $null
        if ($commits -gt 0 -and $dirty) { $blocker = "$commits local commit(s) and uncommitted edits" }
        elseif ($commits -gt 0)         { $blocker = "$commits local commit(s) not in its upstream" }
        elseif ($dirty)                 { $blocker = 'uncommitted local edits' }
        # $null means verified clean and level, or unknowable - either way NOT frozen.
        # Staying quiet costs one session's update; the next pull picks it up.
        if ($blocker) {
            # Which phrase matched, never git's raw text: everything written here
            # reaches the model's context, and git echoes attacker-controlled
            # content (`remote:` lines come verbatim from the server; branch, ref
            # and URL names appear in error text). $matched is one of OUR OWN four
            # literals, so it carries the diagnostic value with none of the surface.
            $matched = @('fast-forward','would be overwritten','unmerged','not concluded') |
                Where-Object { $pullOut -match [regex]::Escape($_) } | Select-Object -First 1
            Write-Output ("WARNING - $(Split-Path $dir -Leaf) could not self-update: the checkout at $dir has $blocker, so automatic updates are FROZEN and this toolkit is going stale. Tell the user at the first natural moment and offer the fix: preserve their local changes on a backup branch, then fast-forward the checkout to its upstream. (Skills in ~/.claude/skills are the right place for personal edits and are unaffected.) git refused with: '$matched'")
        }
    }
}

# --- 1b. personal-toolkit forks: measured against NSLS, not against their own copy ---
# The block above speaks only when a pull FAILS. A fork's pull succeeds - the
# fork genuinely has nothing new - so a builder whose personal toolkit is their
# own GitHub fork was reported healthy every session while nothing NSLS shipped
# ever reached them (196 commits behind on a real machine, 2026-09-09).
# Windows parity with session-start.py's report_personal_fork_drift(): same
# remote name, same stamp, same wording. Python is not guaranteed on a PC, so
# this is the ONLY place the check runs on Windows - and this script self-updates
# from NSLS on every machine, which is what lets it reach a fork at all (the
# fork's own hook is a file inside the fork, so the fork can never receive it).
$PersonalUpstreamUrl    = 'https://github.com/thensls/nsls-personal-toolkit.git'
$PersonalUpstreamRemote = 'nsls-upstream'   # a name WE own - never 'upstream', which may already be theirs
$PersonalUpstreamStamp  = Join-Path $ClaudeDir '.nsls-personal-upstream-check'
$PersonalCheckEveryH    = 12

function Test-CanonicalOrigin {
    param([string]$Url)
    # True only for NSLS's own repository on github.com, in any spelling git
    # accepts (https, ssh://, scp-like; user info, port, www., trailing slash,
    # .git, any case). Host and path are compared exactly - a substring test
    # called a mirror on another host, or a longer-named repo under the same
    # owner, canonical, and skipped the check for it.
    $u = if ($Url) { $Url.Trim() } else { '' }
    $hostName = $null
    $repoPath = $null
    $m = [regex]::Match($u, '^[A-Za-z][A-Za-z0-9+.-]*://(?:[^@/]*@)?([^/:]+)(?::\d+)?/(.*)$')
    if ($m.Success) {
        $hostName = $m.Groups[1].Value
        $repoPath = $m.Groups[2].Value
    } else {
        $m = [regex]::Match($u, '^(?:[^@/:]+@)?([^/:]+):(?!//)/?(.*)$')
        if ($m.Success) {
            $hostName = $m.Groups[1].Value
            $repoPath = $m.Groups[2].Value
        }
    }
    if ($null -eq $hostName) { return $false }
    if ($hostName -match '^www\.') { $hostName = $hostName.Substring(4) }
    $repoPath = $repoPath.Trim('/')
    if ($repoPath -match '\.git$') { $repoPath = $repoPath.Substring(0, $repoPath.Length - 4) }
    # -eq and -match are case-insensitive in PowerShell, which is what GitHub names need.
    return (($hostName -eq 'github.com') -and ($repoPath.TrimEnd('/') -eq 'thensls/nsls-personal-toolkit'))
}

function Invoke-GitQuiet {
    param([string]$Dir, [string[]]$GitArgs, [int]$TimeoutMs = 3000)
    # git with its output DISCARDED and a hard time limit; returns the exit code,
    # or -1 when git timed out or could not start. Everything this hook prints
    # is the model's context and git echoes server-controlled text, so none of
    # git's own output is ever surfaced from here - only our literals and a
    # verified integer. The direct `& git` form has no time limit, and a fetch
    # can hang for a minute on a captive portal or a firewall that drops packets.
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = 'git'
        $parts = @('-C', $Dir) + $GitArgs
        $psi.Arguments = (($parts | ForEach-Object { if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }) -join ' ')
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $psi.EnvironmentVariables['GIT_TERMINAL_PROMPT'] = '0'
        $p = [System.Diagnostics.Process]::Start($psi)
        # Drain both pipes asynchronously (no handlers needed: unsubscribed output
        # is discarded) - a chatty child deadlocks on a full pipe otherwise.
        $p.BeginOutputReadLine()
        $p.BeginErrorReadLine()
        if (-not $p.WaitForExit($TimeoutMs)) {
            try { $p.Kill() } catch { }
            return -1
        }
        return $p.ExitCode
    } catch {
        return -1
    }
}

function Report-PersonalForkDrift {
    param([string]$Dir)
    if (-not (Test-Path (Join-Path $Dir '.git'))) { return }
    $origin = (& git -C $Dir remote get-url origin 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $origin) { return }   # no origin: nothing to measure against
    if (Test-CanonicalOrigin $origin) { return }            # NSLS's own repo: the freeze check above owns it

    # One fetch per 12h, bounded at BOTH ends: a stamp dated in the future
    # (clock skew, a restored backup) would otherwise read as fresh forever.
    $ageH = $null
    try {
        if (Test-Path $PersonalUpstreamStamp) {
            $ageH = ((Get-Date) - (Get-Item $PersonalUpstreamStamp).LastWriteTime).TotalHours
        }
    } catch { }
    if ($null -ne $ageH -and $ageH -ge 0 -and $ageH -lt $PersonalCheckEveryH) { return }

    # Claim the slot BEFORE fetching: the Python hook, where present, keys on this
    # same stamp, and SessionStart hooks start concurrently.
    try { [System.IO.File]::WriteAllText($PersonalUpstreamStamp, '') } catch { }

    $remotes = @((& git -C $Dir remote 2>$null | Out-String) -split '\r?\n' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($LASTEXITCODE -ne 0) { return }
    if ($remotes -contains $PersonalUpstreamRemote) {
        # We own this name, so we may enforce its URL - that also repairs a
        # checkout left pointing at a moved or mistyped repo.
        $null = Invoke-GitQuiet -Dir $Dir -GitArgs @('remote', 'set-url', $PersonalUpstreamRemote, $PersonalUpstreamUrl)
    } else {
        $null = Invoke-GitQuiet -Dir $Dir -GitArgs @('remote', 'add', $PersonalUpstreamRemote, $PersonalUpstreamUrl)
    }

    # Bounded, best-effort: offline, blocked or slow all mean "say nothing this session".
    if ((Invoke-GitQuiet -Dir $Dir -GitArgs @('fetch', $PersonalUpstreamRemote, 'main', '--quiet') -TimeoutMs 8000) -ne 0) { return }
    $count = (& git -C $Dir rev-list --count "HEAD..$PersonalUpstreamRemote/main" 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $count -notmatch '^\d+$') { return }
    $behind = [int]$count
    if ($behind -eq 0) { return }

    # Same prefix and wording as the personal toolkit's own hook, so Claude sees
    # one identical line whichever of the two spoke first.
    Write-Output ("[NSLS Personal Toolkit] This builder's toolkit is their OWN FORK and is $behind commit(s) behind NSLS - nothing shipped upstream has reached them, and their auto-update never will, because it follows their fork. Tell them in ONE plain sentence at the start of your first reply - e.g. `"Your toolkit is your own copy, so NSLS updates haven't been reaching you - want me to catch it up?`" - and if they agree: run /update-personal-productivity if this machine has it; otherwise merge $PersonalUpstreamRemote/main into the checkout at $Dir yourself, preserving their own commits, then read and follow skills/update-personal-productivity/SKILL.md from the freshly merged checkout to walk them through what's new (the slash command itself appears after their next restart). NEVER hand them a git command.")
}
Report-PersonalForkDrift -Dir $PersonalDir

function Parse-Frontmatter {
    param([string]$Path)
    $content = Get-Content $Path -Raw -Encoding UTF8
    $m = [regex]::Match($content, '^---\r?\n(.*?)\r?\n---', 'Singleline')
    if (-not $m.Success) { return @{ name = $null; desc = $null } }
    $block = $m.Groups[1].Value
    $nameMatch = [regex]::Match($block, '^name:\s*(.+)$', 'Multiline')
    $name = if ($nameMatch.Success) { $nameMatch.Groups[1].Value.Trim() } else { $null }
    # '*' not '+': an empty folded block still belongs to the folded branch.
    # With '+' it fell through to the plain branch, which then captured the
    # literal '>-' and used it as the description.
    $folded = [regex]::Match($block, 'description:\s*>-?\s*\r?\n((?:[ \t]+.+\r?\n?)*)')
    if ($folded.Success) {
        $lines = $folded.Groups[1].Value -split "\r?\n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }
        $d = ($lines -join ' ')
    } else {
        # Single-line scalar: reject a bare block indicator, then strip YAML
        # quotes and decode double-quoted escapes in ONE left-to-right pass.
        # Parity with the .py / .sh extractors.
        $plain = [regex]::Match($block, '^description:[ \t]*(.+)$', 'Multiline')
        $d = if ($plain.Success) { $plain.Groups[1].Value.Trim() } else { '' }
        if (@('>', '>-', '>+', '|', '|-', '|+') -contains $d) {
            $d = ''
        } elseif ($d.Length -gt 1) {
            $q = $d[0]
            if ($d[$d.Length - 1] -eq $q -and ($q -eq '"' -or $q -eq "'")) {
                $inner = $d.Substring(1, $d.Length - 2)
                if ($q -eq '"') {
                    $inner = [regex]::Replace($inner,
                        '\\x([0-9a-fA-F]{2})|\\u([0-9a-fA-F]{4})|\\U([0-9a-fA-F]{8})|\\(.)',
                        {
                            param($mm)
                            foreach ($g in 1, 2, 3) {
                                if ($mm.Groups[$g].Success) {
                                    # ConvertFromUtf32, not [char]: a valid \U
                                    # escape above U+FFFF (e.g. \U0001F600)
                                    # overflows System.Char and would throw,
                                    # killing the whole pointer sync. This
                                    # returns the surrogate pair instead.
                                    return [char]::ConvertFromUtf32([Convert]::ToInt32($mm.Groups[$g].Value, 16))
                                }
                            }
                            # switch -CaseSensitive, NOT a hashtable: PowerShell
                            # hashtable keys are case-INsensitive, so 'n' and 'N'
                            # collide and @{...} fails to parse outright. YAML
                            # needs both (\n = newline, \N = next-line), and the
                            # same applies to the \L / \P pair.
                            # [char] codes, not backtick escapes: `e and `v don't
                            # exist in Windows PowerShell 5.1, which runs this.
                            $c = $mm.Groups[4].Value
                            switch -CaseSensitive ($c) {
                                '0' { return [char]0 }
                                'a' { return [char]7 }
                                'b' { return [char]8 }
                                't' { return [char]9 }
                                'n' { return [char]10 }
                                'v' { return [char]11 }
                                'f' { return [char]12 }
                                'r' { return [char]13 }
                                'e' { return [char]27 }
                                'N' { return [char]133 }
                                '_' { return [char]160 }
                                'L' { return [char]8232 }
                                'P' { return [char]8233 }
                            }
                            # Anything else (\" \\ \/ \space) stands for itself.
                            return $c
                        })
                } else {
                    $inner = $inner.Replace("''", "'")
                }
                $d = $inner
            }
        }
    }
    # Map decoded control chars (NUL, BEL, ESC) to spaces - they would make the
    # generated pointer unparseable - then collapse whitespace, because the
    # caller embeds this as one indented line under description: >-.
    # Blank means "no description" so the caller's default stands.
    $d = [regex]::Replace($d, '[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' ')
    $d = ($d -split '\s+' | Where-Object { $_ }) -join ' '
    $desc = if ([string]::IsNullOrWhiteSpace($d)) { $null } else { $d }
    return @{ name = $name; desc = $desc }
}

function Sync-Pointers {
    param([string]$PluginDir)
    $skillsRoot = Join-Path $PluginDir 'skills'
    if (-not (Test-Path $skillsRoot)) { return 0 }
    $count = 0
    $pluginName = [System.IO.Path]::GetFileName($PluginDir)
    foreach ($skillFolder in Get-ChildItem $skillsRoot -Directory) {
        $src = Join-Path $skillFolder.FullName 'SKILL.md'
        if (-not (Test-Path $src)) { continue }
        $fm = Parse-Frontmatter -Path $src
        if (-not $fm.name) { continue }
        $desc = if ($fm.desc) { $fm.desc } else { "NSLS toolkit skill: $($skillFolder.Name)" }
        $destDir = Join-Path $SkillsDir $skillFolder.Name
        $destMd  = Join-Path $destDir   'SKILL.md'
        if (Test-Path $destMd) {
            $existing = Get-Content $destMd -Raw -Encoding UTF8
            if ($existing -notmatch [regex]::Escape($Marker)) { continue }
        }
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
        $pointerPath = "~/.claude/local-plugins/$pluginName/skills/$($skillFolder.Name)/SKILL.md"
        $pointer = @"
---
name: $($fm.name)
description: >-
  $desc
---

Read and follow the full skill at ``$pointerPath``.
"@
        # BOM-less write (matches install.ps1): PS 5.1 `Set-Content -Encoding
        # utf8` prepends a BOM. Harmless-looking on a pointer, but this hook runs
        # every session, so a BOM here would silently re-introduce one on files
        # install.ps1 just wrote clean.
        [System.IO.File]::WriteAllText($destMd, ($pointer + "`r`n"), (New-Object System.Text.UTF8Encoding $false))
        $count++
    }
    return $count
}

# --- 2. sync pointer skills ---
if (-not (Test-Path $SkillsDir)) { New-Item -ItemType Directory -Path $SkillsDir -Force | Out-Null }
$null = Sync-Pointers -PluginDir $BuilderDir
$null = Sync-Pointers -PluginDir $PersonalDir

# --- 2b. surface announcements stashed by the previous detached ping ---
# session-ping.ps1 runs detached, so it can't print to session context itself;
# it dismisses announcements and writes their text here. We read + print it
# synchronously (this hook's stdout IS session context on every surface),
# wrapped in the same directive prefix session-start.py uses so it shows on the
# desktop app too, then delete the file. One session's lag, but it surfaces.
$AnnounceFile = if (Test-Path $BuilderDir) {
    Join-Path $BuilderDir '.pending-announcements'
} else {
    Join-Path $ClaudeDir '.pending-announcements'
}
if (Test-Path $AnnounceFile) {
    $block = (Get-Content $AnnounceFile -Raw -Encoding UTF8).Trim()
    Remove-Item $AnnounceFile -Force -ErrorAction SilentlyContinue
    if ($block) {
        Write-Output "[NSLS Builder Toolkit - surface the following to the user verbatim at the start of your first reply, then proceed with their request:]`n`n$block"
    }
}

# --- 3. session ping (detached, non-blocking) ---
# The proxy is idempotent, so repeated pings never duplicate. Detached so its
# cold-start latency never delays session start; output -> nsls-session-ping.log.
$pingScript = Join-Path $PSScriptRoot 'session-ping.ps1'
if (Test-Path $pingScript) {
    Start-Process powershell -WindowStyle Hidden -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $pingScript
    ) | Out-Null
}

# --- 4. Builder Guardrails context + plugin freshness ---
# Windows parity with session-start.py's emit_guardrails_context(). Without
# this, Windows builders got the four hard gates (the hook is registered for
# them) but none of the conversational half - tiers, escalation triggers, the
# voice guide, remembered declines - which is the same
# configuration-present-but-not-loaded failure this project has hit three times.
# Delegated to the Python emitter rather than reimplemented: one copy of the
# section-extraction and path-resolution logic, not two that can drift.
# The same Python entry point also runs ensure_plugin_fresh(): the daily
# `claude plugin update` plus the commit-level drift check and self-heal. The
# plugin's own hooks.json hook invokes `python3`, which on stock Windows is a
# Store alias that exits without running, so THIS script is the only place the
# freshness step reliably fires on Windows. It is a no-op unless the plugin is
# installed and enabled; clone-only machines stay fresh via the git pull above.
# Interpreter: the stock Windows `python3` is a Store alias that exits without
# running anything, so falling back to it emitted nothing at all - worse than
# failing loudly. Prefer the launcher, then the toolkit-provisioned runtime,
# and give up quietly only when there is genuinely no Python.
$pyExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $pyExe = 'py' }
elseif (Test-Path (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe')) {
    $pyExe = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
}
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyExe = 'python' }

$startPy = Join-Path $PSScriptRoot 'session-start.py'
if ($pyExe -and (Test-Path $startPy)) {
    # The path goes in as an ARGUMENT, never interpolated into Python source:
    # a Windows profile containing an apostrophe (O'Brien) made the inline
    # program a SyntaxError, and the empty catch swallowed it - the guardrail
    # context just silently vanished for that person.
    $emitter = @'
import runpy, sys
runpy.run_path(sys.argv[1], run_name="__guardrails__")
'@
    try {
        if ($pyExe -eq 'py') { & $pyExe -3 -c $emitter $startPy 2>$null }
        else { & $pyExe -c $emitter $startPy 2>$null }
    } catch { }
}

# windows-ci: ps51 ps7 | A Personal Toolkit folder that follows the copy Claude delivers is left alone by the Windows hook, and git never climbs past it
# Once the folder follows the delivered copy (hooks/personal_delivery.py) it is
# no longer a checkout, but the Windows hook still walks it: its update loop
# runs `git -C <folder> fetch` and a fast-forward on every toolkit folder that
# exists. With no .git there at all, git climbs to the nearest repository above
# (a person's dotfiles in their home folder) and that is the one it updates.
# The folder therefore carries a placeholder .git FILE naming a repository that
# does not exist. This proves what the placeholder buys: the hook says nothing,
# and the repository above is neither fetched nor moved. Update-Checkout and its
# helpers are lifted out of session-start.ps1 by AST, so this never tests a copy.
$ErrorActionPreference = 'SilentlyContinue'
$hooks  = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $hooks 'session-start.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw "session-start.ps1 does not parse: $($errors[0].Message)" }
$want = @('Get-GitRepoEnv', 'Clear-GitRepoEnv', 'Test-GitPath', 'Get-FastForwardArgs', 'Invoke-GitBounded', 'Update-Checkout')
$fns = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $want -contains $n.Name }, $true)
if ($fns.Count -ne $want.Count) { throw "expected $($want.Count) functions in session-start.ps1, found $($fns.Count)" }
foreach ($f in $fns) { Invoke-Expression $f.Extent.Text }
$lists = $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$GitOpState' }, $true)
if ($lists.Count -ne 1) { throw "expected one `$GitOpState in session-start.ps1, found $($lists.Count)" }
Invoke-Expression ('$script:' + $lists[0].Extent.Text.Substring(1))
Clear-GitRepoEnv
$env:GIT_TERMINAL_PROMPT = '0'

# The placeholder's text comes from the module that writes it, never a copy.
$module = Get-Content -LiteralPath (Join-Path $hooks 'personal_delivery.py') -Raw
if ($module -notmatch 'TOMBSTONE = "(gitdir: [^"\\]+)\\n"') { throw 'TOMBSTONE not found in personal_delivery.py' }
$placeholder = $Matches[1] + "`n"

$script:failures = 0
function Check([string]$Label, [bool]$Cond, [string]$Detail = '') {
    if ($Cond) { Write-Host "ok   $Label" } else { Write-Host "FAIL $Label"; if ($Detail) { Write-Host "     saw: $Detail" }; $script:failures++ }
}
function TGit {
    $dir = $args[0]; $rest = @($args | Select-Object -Skip 1)
    $out = & git -C $dir @rest 2>$null
    if ($LASTEXITCODE -ne 0) { throw "git $($rest -join ' ') failed (exit $LASTEXITCODE) in $dir" }
    return (($out | Out-String).Trim())
}
function Commit([string]$Repo, [string]$Name, [string]$Text) {
    Set-Content -Path (Join-Path $Repo $Name) -Value $Text -NoNewline
    TGit $Repo add -A | Out-Null
    TGit $Repo commit --quiet -m "add $Name" | Out-Null
}

# A home folder that is itself a repository with an update waiting, and the
# Personal Toolkit folder inside it.
$root = Join-Path ([IO.Path]::GetTempPath()) ('delivered smoke-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $root | Out-Null
try {
    $seed = Join-Path $root 'seed'
    & git init --quiet -b main $seed 2>$null
    TGit $seed config user.email t@example.com | Out-Null
    TGit $seed config user.name t | Out-Null
    Commit $seed 'dotfile' "v1`n"
    $remote = Join-Path $root 'dotfiles.git'
    & git clone --quiet --bare $seed $remote 2>$null
    $userHome = Join-Path $root 'home'
    & git clone --quiet $remote $userHome 2>$null
    Commit $seed 'dotfile' "v2`n"
    TGit $seed push --quiet $remote 'HEAD:main' | Out-Null

    $folder = Join-Path $userHome '.claude\local-plugins\nsls-personal-toolkit'
    New-Item -ItemType Directory -Path (Join-Path $folder 'skills') -Force | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $folder '.git'), $placeholder, (New-Object System.Text.UTF8Encoding $false))

    $headBefore   = TGit $userHome rev-parse HEAD
    $remoteBefore = TGit $userHome rev-parse 'refs/remotes/origin/main'
    $said = (Update-Checkout -Dir $folder | Out-String)
    Check 'the update loop says nothing about a folder that follows the delivered copy' ($said.Trim() -eq '') $said
    Check 'the repository above it was not fetched' ((TGit $userHome rev-parse 'refs/remotes/origin/main') -eq $remoteBefore)
    Check 'and was not moved' ((TGit $userHome rev-parse HEAD) -eq $headBefore)
    & git -C $folder rev-parse --show-toplevel 2>$null | Out-Null
    Check 'git itself refuses the folder outright' ($LASTEXITCODE -ne 0)
} finally {
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:failures -gt 0) { Write-Host "FAILED: $($script:failures)"; exit 1 }
Write-Host 'all checks passed'

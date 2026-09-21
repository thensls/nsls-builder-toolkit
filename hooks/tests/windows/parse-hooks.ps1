# Parse every hook script with PowerShell's own parser, without running any of
# it. The Macs that write these files have no PowerShell, so a typo or a quoting
# slip used to travel all the way to a builder's PC before anyone saw it.
# Run by .github/workflows/windows-hooks.yml under both Windows PowerShell 5.1
# and PowerShell 7; also fine to run by hand on any PC.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$bad = 0
Get-ChildItem -Path $root -Filter *.ps1 -Recurse | Sort-Object FullName | ForEach-Object {
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors) | Out-Null
    if ($errors.Count -gt 0) {
        $bad += $errors.Count
        foreach ($e in $errors) {
            Write-Host ("FAIL {0}:{1}: {2}" -f $_.FullName, $e.Extent.StartLineNumber, $e.Message)
        }
    } else {
        Write-Host ("ok   {0} (PowerShell {1})" -f $_.Name, $PSVersionTable.PSVersion)
    }
}
if ($bad -gt 0) {
    Write-Host "$bad parse error(s)"
    exit 1
}

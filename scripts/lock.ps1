<#
.SYNOPSIS
    Record the fully resolved dependency set in requirements-lock.txt.

.DESCRIPTION
    Run this from a clean environment created by scripts/bootstrap.ps1, so the lock
    reflects what requirements.txt actually resolves to rather than whatever has
    accumulated locally.

    The interpreter is resolved through scripts/_python.ps1 rather than a bare
    `conda run`, because conda init lives in the user's PowerShell profile and is not
    loaded by non-interactive shells - CI, task runners, and agents all miss it.
#>
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\_python.ps1"
$script:VerityPython = Resolve-VerityPython -RepoRoot $repoRoot

$lines = & $script:VerityPython[0] -m pip freeze --all
if ($LASTEXITCODE -ne 0) { throw "pip freeze failed" }

$header = @(
    "# Fully resolved dependency set for the agent-dev environment.",
    "# Generated $(Get-Date -Format yyyy-MM-dd) from requirements.txt on Python 3.11.",
    "# Regenerate with: powershell -File scripts/lock.ps1"
)
# Windows PowerShell 5.1 writes a BOM with -Encoding utf8, which does not belong in a
# requirements file. Write UTF-8 without one explicitly.
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines("$repoRoot\requirements-lock.txt", @($header + $lines), $utf8NoBom)
Write-Host "Wrote requirements-lock.txt ($($lines.Count) packages)"

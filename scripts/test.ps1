<#
.SYNOPSIS
    Lint, type-check, and test. Prefers the agent-dev conda environment.

.PARAMETER Docker
    Also run the container isolation suite (needs a running Docker daemon). Without it
    those tests skip themselves rather than failing.
#>
param(
    [switch]$Docker
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\_python.ps1"
$script:VerityPython = Resolve-VerityPython -RepoRoot $repoRoot
$testTempRoot = Join-Path $repoRoot ".pytest_tmp\test-script-$PID"
$pytestTemp = Join-Path $testTempRoot "pytest"
$runtimeTemp = Join-Path $testTempRoot "runtime"
$previousTemp = [Environment]::GetEnvironmentVariable("TEMP", "Process")
$previousTmp = [Environment]::GetEnvironmentVariable("TMP", "Process")

Invoke-VerityPython @("-m", "ruff", "check", ".")
Invoke-VerityPython @("-m", "ruff", "format", "--check", ".")
Invoke-VerityPython @("-m", "mypy", "verity", "app")

try {
    New-Item -ItemType Directory -Path $runtimeTemp -Force | Out-Null
    $env:TEMP = $runtimeTemp
    $env:TMP = $runtimeTemp
    $pytestArgs = @(
        "-m", "pytest", "-q", "--basetemp", $pytestTemp, "-p", "no:cacheprovider"
    )
    if (-not $Docker) {
        $pytestArgs += @("-m", "not docker")
    }
    Invoke-VerityPython $pytestArgs
} finally {
    if ($null -eq $previousTemp) {
        Remove-Item -LiteralPath "Env:TEMP" -ErrorAction SilentlyContinue
    } else {
        $env:TEMP = $previousTemp
    }
    if ($null -eq $previousTmp) {
        Remove-Item -LiteralPath "Env:TMP" -ErrorAction SilentlyContinue
    } else {
        $env:TMP = $previousTmp
    }
    $resolvedRoot = [System.IO.Path]::GetFullPath($repoRoot)
    $resolvedTemp = [System.IO.Path]::GetFullPath($testTempRoot)
    if (-not $resolvedTemp.StartsWith(
        $resolvedRoot + [System.IO.Path]::DirectorySeparatorChar,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Refusing to clean a test path outside the repository: $resolvedTemp"
    }
    if (Test-Path -LiteralPath $resolvedTemp) {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
    }
}

if ($Docker) {
    Invoke-VerityPython @("scripts/validate_docker_isolation.py")
}

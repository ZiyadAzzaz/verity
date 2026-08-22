<#
.SYNOPSIS
    Lint, type-check, and test. Uses agent-dev if conda is present, otherwise .venv.

.PARAMETER Docker
    Also run the container isolation suite (needs a running Docker daemon). Without it
    those tests skip themselves rather than failing.
#>
param(
    [switch]$Docker
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

if (Get-Command conda -ErrorAction SilentlyContinue) {
    $python = @("conda", "run", "--no-capture-output", "-n", "agent-dev", "python")
} elseif (Test-Path "$repoRoot\.venv\Scripts\python.exe") {
    $python = @("$repoRoot\.venv\Scripts\python.exe")
} else {
    throw "No environment found. Run scripts/bootstrap.ps1 first."
}

function Invoke-Python {
    param([string[]]$Arguments)
    & $python[0] @($python[1..($python.Length - 1)] + $Arguments)
    if ($LASTEXITCODE -ne 0) { throw "failed: $($Arguments -join ' ')" }
}

Invoke-Python @("-m", "ruff", "check", ".")
Invoke-Python @("-m", "ruff", "format", "--check", ".")
Invoke-Python @("-m", "mypy", "verity", "app")

if ($Docker) {
    Invoke-Python @("-m", "pytest", "-q")
    Invoke-Python @("scripts/validate_docker_isolation.py")
} else {
    Invoke-Python @("-m", "pytest", "-q", "-m", "not docker")
}

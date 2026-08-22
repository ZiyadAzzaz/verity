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

Invoke-VerityPython @("-m", "ruff", "check", ".")
Invoke-VerityPython @("-m", "ruff", "format", "--check", ".")
Invoke-VerityPython @("-m", "mypy", "verity", "app")

if ($Docker) {
    Invoke-VerityPython @("-m", "pytest", "-q")
    Invoke-VerityPython @("scripts/validate_docker_isolation.py")
} else {
    Invoke-VerityPython @("-m", "pytest", "-q", "-m", "not docker")
}

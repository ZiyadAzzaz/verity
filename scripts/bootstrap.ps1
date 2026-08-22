<#
.SYNOPSIS
    Create the agent-dev environment and the Verity sandbox image.

.DESCRIPTION
    Prefers conda (the documented setup: `conda create -n agent-dev python=3.11`). If no
    conda installation can be found, falls back to a plain Python 3.11 venv in .venv —
    the code has no conda dependency, only a 3.11 one.

    Also builds the sandbox runtime image when Docker is running. The Environment Agent
    builds it on demand too; doing it here just moves a slow first run out of the demo.
#>
param(
    [switch]$SkipImage
)

$ErrorActionPreference = "Stop"
$environmentName = "agent-dev"
$repoRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\_python.ps1"

$condaRoot = Find-CondaRoot
if ($condaRoot) {
    $conda = Join-Path $condaRoot "Scripts\conda.exe"
    Write-Host "Found conda at $conda"
    $envPython = Join-Path $condaRoot "envs\$environmentName\python.exe"
    if (-not (Test-Path $envPython)) {
        Write-Host "Creating the $environmentName environment..."
        & $conda create -n $environmentName python=3.11 -y
        if ($LASTEXITCODE -ne 0) { throw "conda create failed" }
    }
    if (-not (Test-Path $envPython)) { throw "$environmentName has no python.exe" }
    & $envPython -m pip install --upgrade pip
    & $envPython -m pip install -r "$repoRoot\requirements.txt"
    if ($LASTEXITCODE -ne 0) { throw "dependency install failed" }
    & $envPython -m pip check
    Write-Host "agent-dev is ready. Activate it with: conda activate agent-dev"
} else {
    Write-Host "No conda installation found; falling back to a Python 3.11 venv in .venv"
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw "Install Python 3.11 (or conda) first."
    }
    if (-not (Test-Path "$repoRoot\.venv")) {
        py -3.11 -m venv "$repoRoot\.venv"
    }
    & "$repoRoot\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & "$repoRoot\.venv\Scripts\python.exe" -m pip install -r "$repoRoot\requirements.txt"
    & "$repoRoot\.venv\Scripts\python.exe" -m pip check
    Write-Host "Environment ready. Activate it with: .\.venv\Scripts\Activate.ps1"
}

if (-not (Test-Path "$repoRoot\.env")) {
    Copy-Item "$repoRoot\.env.example" "$repoRoot\.env"
    Write-Host "Created .env - add your GEMINI_API_KEY from https://aistudio.google.com/"
}

if ($SkipImage) { return }

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Warning "Docker was not found. Verity refuses to run untrusted third-party code on the host, so verification jobs will not start until Docker is installed."
    return
}
docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "The Docker daemon is not running. Start Docker Desktop, then: docker build -f Dockerfile.runner -t verity-sandbox-runner:1 ."
    return
}
Write-Host "Building the sandbox runtime image..."
docker build -f "$repoRoot\Dockerfile.runner" -t verity-sandbox-runner:1 $repoRoot
Write-Host "Sandbox image verity-sandbox-runner:1 is ready."

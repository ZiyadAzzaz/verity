<#
.SYNOPSIS
    Create the agent-dev environment and the Verity sandbox image.

.DESCRIPTION
    Prefers conda (the documented setup: `conda create -n agent-dev python=3.11`). If
    conda is not installed, falls back to a plain Python 3.11 venv in .venv so the local
    pipeline is still reachable — the code has no conda dependency, only a 3.11 one.

    Also builds the sandbox runtime image when Docker is running. The Environment Agent
    builds it on demand too; doing it here just moves a slow first run out of the demo.
#>
param(
    [switch]$SkipImage
)

$ErrorActionPreference = "Stop"
$environmentName = "agent-dev"
$repoRoot = Split-Path -Parent $PSScriptRoot

if (Get-Command conda -ErrorAction SilentlyContinue) {
    $existing = conda env list --json | ConvertFrom-Json
    $names = $existing.envs | ForEach-Object { Split-Path $_ -Leaf }
    if ($names -notcontains $environmentName) {
        conda create -n $environmentName python=3.11 -y
    }
    conda run -n $environmentName python -m pip install -r "$repoRoot\requirements.txt"
    conda run -n $environmentName python -m pip check
    Write-Host "agent-dev is ready. Activate it with: conda activate agent-dev"
    $python = "conda run -n $environmentName python"
} else {
    Write-Host "conda was not found; falling back to a Python 3.11 venv in .venv"
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $launcher) { throw "Install Python 3.11 (or conda) first." }
    if (-not (Test-Path "$repoRoot\.venv")) {
        py -3.11 -m venv "$repoRoot\.venv"
    }
    & "$repoRoot\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & "$repoRoot\.venv\Scripts\python.exe" -m pip install -r "$repoRoot\requirements.txt"
    & "$repoRoot\.venv\Scripts\python.exe" -m pip check
    Write-Host "Environment ready. Activate it with: .\.venv\Scripts\Activate.ps1"
    $python = "$repoRoot\.venv\Scripts\python.exe"
}

if (-not (Test-Path "$repoRoot\.env")) {
    Copy-Item "$repoRoot\.env.example" "$repoRoot\.env"
    Write-Host "Created .env — add your GEMINI_API_KEY from https://aistudio.google.com/"
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

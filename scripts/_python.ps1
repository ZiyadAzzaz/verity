<#
.SYNOPSIS
    Resolve the Python interpreter Verity should run under. Dot-source this.

.DESCRIPTION
    Sets $VerityPython to an argument array whose first element is the executable.
    Invoke it with Invoke-VerityPython.

    Order of preference:
      1. The agent-dev conda environment (the documented setup).
      2. A local .venv (the fallback bootstrap.ps1 creates when conda is absent).
      3. Whatever `python` is on PATH, if it is 3.11.

    `conda` is deliberately NOT located with Get-Command alone. conda init installs
    itself into the user's PowerShell *profile*, so an interactive prompt has it but a
    non-interactive shell — CI, a task runner, an agent — does not. Probing CONDA_EXE
    and the common install roots (including non-system drives) is what makes these
    scripts behave the same in both.
#>

function Find-CondaRoot {
    if ($env:CONDA_EXE -and (Test-Path $env:CONDA_EXE)) {
        return Split-Path -Parent (Split-Path -Parent $env:CONDA_EXE)
    }
    $onPath = Get-Command conda -ErrorAction SilentlyContinue
    if ($onPath) {
        return Split-Path -Parent (Split-Path -Parent $onPath.Source)
    }
    $roots = @()
    foreach ($drive in (Get-PSDrive -PSProvider FileSystem).Name) {
        $roots += "${drive}:\Anaconda", "${drive}:\Miniconda", "${drive}:\Miniforge3"
    }
    $roots += "$env:USERPROFILE\anaconda3", "$env:USERPROFILE\miniconda3",
              "$env:USERPROFILE\miniforge3", "$env:LOCALAPPDATA\anaconda3",
              "$env:LOCALAPPDATA\miniconda3", "C:\ProgramData\anaconda3",
              "C:\ProgramData\miniconda3"
    foreach ($root in $roots) {
        if (Test-Path (Join-Path $root "Scripts\conda.exe")) { return $root }
    }
    return $null
}

function Resolve-VerityPython {
    param([string]$RepoRoot, [string]$EnvironmentName = "agent-dev")

    $condaRoot = Find-CondaRoot
    if ($condaRoot) {
        $envPython = Join-Path $condaRoot "envs\$EnvironmentName\python.exe"
        if (Test-Path $envPython) {
            Write-Host "Using conda environment '$EnvironmentName' ($envPython)"
            return , @($envPython)
        }
    }
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        Write-Host "Using .venv ($venvPython)"
        return , @($venvPython)
    }
    $onPath = Get-Command python -ErrorAction SilentlyContinue
    if ($onPath) {
        $version = & $onPath.Source -c "import sys;print('%d.%d' % sys.version_info[:2])"
        if ($version -eq "3.11") {
            Write-Host "Using python on PATH ($($onPath.Source))"
            return , @($onPath.Source)
        }
    }
    throw "No Python 3.11 environment found. Run: powershell -File scripts/bootstrap.ps1"
}

function Invoke-VerityPython {
    param([string[]]$Arguments)
    & $script:VerityPython[0] @Arguments
    if ($LASTEXITCODE -ne 0) { throw "failed: python $($Arguments -join ' ')" }
}

$ErrorActionPreference = "Stop"
$lines = conda run -n agent-dev python -m pip freeze --all
$header = @(
    "# Fully resolved from environment.yml on $(Get-Date -Format yyyy-MM-dd)",
    "# Regenerate with: powershell -File scripts/lock.ps1"
)
@($header + $lines) | Set-Content -LiteralPath requirements-lock.txt -Encoding utf8
Write-Host "Wrote requirements-lock.txt"


<#
.SYNOPSIS
    Run Verity's cloud adapters against Google's official local emulators.

.DESCRIPTION
    Starts digest-pinned Firestore and Pub/Sub emulator containers with fake project data,
    runs only the emulator integration suite, prints emulator logs on failure, and removes
    the containers afterward. No credentials or real Google Cloud project are used.

.PARAMETER KeepContainers
    Leave the two emulator containers running after the test for manual inspection.
#>
param(
    [switch]$KeepContainers
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $repoRoot "docker-compose.emulators.yml"
$composeProject = "verity-emulator-tests"
$pytestTemp = Join-Path $repoRoot ".pytest_tmp\emulators"
. "$PSScriptRoot\_python.ps1"
$script:VerityPython = Resolve-VerityPython -RepoRoot $repoRoot

function Invoke-Docker {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($DockerArgs -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Restore-ProcessEnvironment {
    param([string]$Name, [AllowNull()][string]$Value)
    if ($null -eq $Value) {
        Remove-Item -LiteralPath "Env:$Name" -ErrorAction SilentlyContinue
    } else {
        [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    }
}

$previousFirestoreHost = [Environment]::GetEnvironmentVariable(
    "FIRESTORE_EMULATOR_HOST", "Process"
)
$previousPubSubHost = [Environment]::GetEnvironmentVariable(
    "PUBSUB_EMULATOR_HOST", "Process"
)
$previousPubSubProject = [Environment]::GetEnvironmentVariable(
    "PUBSUB_PROJECT_ID", "Process"
)
$previousVerityProject = [Environment]::GetEnvironmentVariable(
    "VERITY_EMULATOR_PROJECT", "Process"
)
$testPassed = $false

try {
    Invoke-Docker info '--format={{.ServerVersion}}'
    Invoke-Docker compose '--project-name' $composeProject '--file' $composeFile `
        'up' '--detach' '--wait' '--wait-timeout' '120'

    $env:FIRESTORE_EMULATOR_HOST = "127.0.0.1:18080"
    $env:PUBSUB_EMULATOR_HOST = "127.0.0.1:18085"
    $env:PUBSUB_PROJECT_ID = "verity-emulator-test"
    $env:VERITY_EMULATOR_PROJECT = "verity-emulator-test"

    Invoke-VerityPython @(
        "-m", "pytest", "tests/test_cloud_emulators.py", "-q", "-m", "emulator",
        "--basetemp", $pytestTemp, "-p", "no:cacheprovider"
    )
    $testPassed = $true
} finally {
    Restore-ProcessEnvironment "FIRESTORE_EMULATOR_HOST" $previousFirestoreHost
    Restore-ProcessEnvironment "PUBSUB_EMULATOR_HOST" $previousPubSubHost
    Restore-ProcessEnvironment "PUBSUB_PROJECT_ID" $previousPubSubProject
    Restore-ProcessEnvironment "VERITY_EMULATOR_PROJECT" $previousVerityProject

    if (-not $testPassed) {
        & docker compose '--project-name' $composeProject '--file' $composeFile `
            'logs' '--no-color' '--tail' '200'
    }
    if (-not $KeepContainers) {
        & docker compose '--project-name' $composeProject '--file' $composeFile `
            'down' '--volumes' '--remove-orphans'
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Emulator container cleanup failed with exit code $LASTEXITCODE"
        }
    }
    $resolvedRoot = [System.IO.Path]::GetFullPath($repoRoot)
    $resolvedTemp = [System.IO.Path]::GetFullPath($pytestTemp)
    if (-not $resolvedTemp.StartsWith(
        $resolvedRoot + [System.IO.Path]::DirectorySeparatorChar,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Refusing to clean an emulator test path outside the repository: $resolvedTemp"
    }
    if (Test-Path -LiteralPath $resolvedTemp) {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
    }
}

if ($testPassed) {
    Write-Output "Official Firestore and Pub/Sub emulator integration tests passed."
}

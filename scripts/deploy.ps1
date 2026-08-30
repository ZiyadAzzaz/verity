param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')][string]$ProjectId,
    [ValidatePattern('^[a-z]+-[a-z0-9]+[0-9]$')][string]$Region = "us-central1",
    [string]$ReportRepo
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $true
}
$repoRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\_python.ps1"
$script:VerityPython = Resolve-VerityPython -RepoRoot $repoRoot

# Guard transition authority: docs/CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md records execution
# verity-sandbox-rcxvn with all six sensitive APIs denied 403 under the zero-role identity.
# This script intentionally ends with a private service. scripts/publish_production.ps1 is the
# only production path that can grant allUsers, and it requires the owner's Phase 8 approval.

function Import-RequiredEnvironment {
    $envFile = Join-Path $repoRoot '.env'
    if (-not (Test-Path -LiteralPath $envFile)) { return }
    $allowed = @('VERITY_API_KEY', 'VERITY_JUDGE_TEST_KEY', 'VERITY_GITHUB_TOKEN', 'VERITY_REPORT_REPO')
    foreach ($rawLine in Get-Content -LiteralPath $envFile) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith('#') -or -not $line.Contains('=')) { continue }
        $parts = $line.Split('=', 2)
        $name = $parts[0].Trim()
        if ($name -notin $allowed -or [Environment]::GetEnvironmentVariable($name, 'Process')) {
            continue
        }
        $value = $parts[1].Trim()
        if ($value.Length -ge 2 -and (($value[0] -eq '"' -and $value[-1] -eq '"') -or ($value[0] -eq "'" -and $value[-1] -eq "'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

function Invoke-Checked {
    param([Parameter(Mandatory=$true)][string]$File, [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$File failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

function Invoke-Text {
    param([Parameter(Mandatory=$true)][string]$File, [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    $output = & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$File failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
    return (($output | Out-String).Trim())
}

function Test-Native {
    param([Parameter(Mandatory=$true)][string]$File, [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    # gcloud.ps1 emits a PowerShell error record for normal negative existence
    # probes. Suppress it locally so NOT_FOUND is returned as false without
    # weakening fail-fast behavior for mutation commands.
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "SilentlyContinue"
        & $File @Arguments *> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Invoke-AgentsCliIsolated {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    # google-agents-cli intentionally copies every key in the project-root .env into
    # Cloud Run. Verity's .env contains production secrets, so invoke image deployment
    # from a fresh OS temp directory and pass only the explicit non-secret environment
    # plus Secret Manager references. Running from anywhere below the repository would
    # still let its project-root discovery find .env.
    $isolatedRoot = Join-Path ([System.IO.Path]::GetTempPath()) "verity-agents-cli-$([guid]::NewGuid().ToString('N'))"
    New-Item -ItemType Directory -Path $isolatedRoot | Out-Null
    try {
        Push-Location $isolatedRoot
        try {
            Invoke-Checked $script:AgentsCli @Arguments
        }
        finally {
            Pop-Location
        }
    }
    finally {
        $resolvedTemp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
        $resolvedIsolated = [System.IO.Path]::GetFullPath($isolatedRoot)
        if (-not $resolvedIsolated.StartsWith($resolvedTemp, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean an agents-cli directory outside the OS temp root: $resolvedIsolated"
        }
        Remove-Item -LiteralPath $resolvedIsolated -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Import-RequiredEnvironment
if (-not $ReportRepo) { $ReportRepo = $env:VERITY_REPORT_REPO }

$apiKey = $env:VERITY_API_KEY
$judgeTestKey = $env:VERITY_JUDGE_TEST_KEY
$githubToken = $env:VERITY_GITHUB_TOKEN
if (-not $apiKey -or $apiKey.Length -lt 24) { throw "Set VERITY_API_KEY to at least 24 random characters." }
if ($judgeTestKey -and $judgeTestKey.Length -lt 24) { throw "Set VERITY_JUDGE_TEST_KEY to at least 24 random characters when provided." }
if ($judgeTestKey -and $judgeTestKey -ceq $apiKey) { throw "VERITY_JUDGE_TEST_KEY must differ from VERITY_API_KEY." }
if (-not $githubToken) { throw "Set VERITY_GITHUB_TOKEN to a fine-grained token with Issues: write." }
if (-not $ReportRepo -or $ReportRepo -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { throw "Set VERITY_REPORT_REPO as owner/repository." }
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) { throw "Google Cloud SDK (gcloud) is required." }
$agentsCliCommand = Get-Command agents-cli -ErrorAction SilentlyContinue
if ($agentsCliCommand) {
    $script:AgentsCli = $agentsCliCommand.Source
}
else {
    $pythonDirectory = Split-Path -Parent $script:VerityPython
    $candidate = Join-Path $pythonDirectory 'Scripts\agents-cli.exe'
    if (-not (Test-Path -LiteralPath $candidate)) { throw "Install requirements-deploy.txt in agent-dev first." }
    $script:AgentsCli = $candidate
}
$workingTree = Invoke-Text git status '--porcelain'
if ($workingTree) { throw "Commit or stash all changes before building deployment images." }

Invoke-Checked gcloud config set project $ProjectId
Invoke-Checked gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com cloudasset.googleapis.com firestore.googleapis.com pubsub.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com cloudtrace.googleapis.com logging.googleapis.com

$billingAccount = (Invoke-Text gcloud billing projects describe $ProjectId '--format=value(billingAccountName)').Replace('billingAccounts/','')
if (-not $billingAccount) { throw "The project must be linked to a billing account before deployment." }

if (-not (Test-Native gcloud firestore databases describe '--database=(default)')) {
    Invoke-Checked gcloud firestore databases create '--database=(default)' "--location=$Region" '--type=firestore-native'
}
if (-not (Test-Native gcloud artifacts repositories describe verity "--location=$Region")) {
    Invoke-Checked gcloud artifacts repositories create verity '--repository-format=docker' "--location=$Region" '--description=Verity containers'
}

function Ensure-ServiceAccount([string]$Name, [string]$DisplayName) {
    $email = "$Name@$ProjectId.iam.gserviceaccount.com"
    if (-not (Test-Native gcloud iam service-accounts describe $email)) {
        Invoke-Checked gcloud iam service-accounts create $Name "--display-name=$DisplayName"
    }
    return $email
}

$appServiceAccount = Ensure-ServiceAccount 'verity-app' 'Verity orchestrator and agents'
$sandboxServiceAccount = Ensure-ServiceAccount 'verity-sandbox' 'Verity no-role evaluation tasks'
$pushServiceAccount = Ensure-ServiceAccount 'verity-pubsub' 'Verity authenticated Pub/Sub push'
$pubsubAudience = "https://verity.internal/pubsub/$ProjectId"

foreach ($role in 'roles/datastore.user','roles/pubsub.publisher','roles/aiplatform.user','roles/cloudtrace.agent','roles/logging.logWriter','roles/logging.viewer') {
    Invoke-Checked gcloud projects add-iam-policy-binding $ProjectId "--member=serviceAccount:$appServiceAccount" "--role=$role" '--condition=None' '--quiet'
}

# Migrate any project previously touched by the unsafe blueprint, then enforce zero direct
# project roles for the sandbox identity. Inherited/effective access is tested with a stolen
# metadata token after the job is deployed.
$projectPolicy = (Invoke-Text gcloud projects get-iam-policy $ProjectId '--format=json') | ConvertFrom-Json
$sandboxMember = "serviceAccount:$sandboxServiceAccount"
$legacyBinding = @($projectPolicy.bindings | Where-Object { $_.role -eq 'roles/datastore.user' -and $_.members -contains $sandboxMember })
if ($legacyBinding.Count -gt 0) {
    Invoke-Checked gcloud projects remove-iam-policy-binding $ProjectId "--member=$sandboxMember" '--role=roles/datastore.user' '--condition=None' '--quiet'
    $projectPolicy = (Invoke-Text gcloud projects get-iam-policy $ProjectId '--format=json') | ConvertFrom-Json
}
$sandboxRoles = @($projectPolicy.bindings | Where-Object { $_.members -contains $sandboxMember } | ForEach-Object { $_.role })
if ($sandboxRoles.Count -gt 0) {
    throw "Sandbox identity must have zero direct project roles; found: $($sandboxRoles -join ', ')"
}
$sandboxResourceBindings = Invoke-Text gcloud asset search-all-iam-policies "--scope=projects/$ProjectId" "--query=policy:$sandboxServiceAccount" '--format=value(resource)'
if ($sandboxResourceBindings) {
    throw "Sandbox identity must have zero resource-level IAM bindings; found: $sandboxResourceBindings"
}

function Set-Secret([string]$Name, [string]$Value) {
    if (-not (Test-Native gcloud secrets describe $Name)) {
        Invoke-Checked gcloud secrets create $Name '--replication-policy=automatic'
    }
    $temporaryFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($temporaryFile, $Value, [System.Text.UTF8Encoding]::new($false))
        Invoke-Checked gcloud secrets versions add $Name "--data-file=$temporaryFile"
    }
    finally {
        Remove-Item -LiteralPath $temporaryFile -Force -ErrorAction SilentlyContinue
    }
}

Set-Secret 'verity-api-key' $apiKey
Set-Secret 'verity-github-token' $githubToken
Set-Secret 'verity-sandbox-deny-probe' 'This sentinel is deliberately non-sensitive.'
$judgeSecretAvailable = $false
if ($judgeTestKey) {
    Set-Secret 'verity-judge-test-key' $judgeTestKey
    $judgeSecretAvailable = $true
}
elseif (Test-Native gcloud secrets describe 'verity-judge-test-key') {
    # Preserve a separately provisioned judge credential without reading or rotating its value.
    $judgeSecretAvailable = $true
}
$applicationSecretNames = @('verity-api-key','verity-github-token')
if ($judgeSecretAvailable) { $applicationSecretNames += 'verity-judge-test-key' }
foreach ($secret in $applicationSecretNames) {
    Invoke-Checked gcloud secrets add-iam-policy-binding $secret "--member=serviceAccount:$appServiceAccount" '--role=roles/secretmanager.secretAccessor' '--quiet'
}

$sourceRevision = Invoke-Text git rev-parse --short=12 HEAD
Invoke-Checked gcloud builds submit '--config=cloudbuild.yaml' "--substitutions=_REGION=$Region,_REPOSITORY=verity,_TAG=$sourceRevision" .
$apiImageTag = "$Region-docker.pkg.dev/$ProjectId/verity/verity-api:$sourceRevision"
$sandboxImageTag = "$Region-docker.pkg.dev/$ProjectId/verity/verity-sandbox:$sourceRevision"
$apiImage = Invoke-Text gcloud artifacts docker images describe $apiImageTag '--format=value(image_summary.fully_qualified_digest)'
$sandboxImage = Invoke-Text gcloud artifacts docker images describe $sandboxImageTag '--format=value(image_summary.fully_qualified_digest)'
if ($apiImage -notmatch '@sha256:[0-9a-f]{64}$' -or $sandboxImage -notmatch '@sha256:[0-9a-f]{64}$') {
    throw "Artifact Registry did not return immutable image digests."
}

# Deploy and prove the unprivileged boundary before exposing the application or pipeline.
Invoke-Checked gcloud run jobs deploy verity-sandbox "--image=$sandboxImage" "--region=$Region" "--service-account=$sandboxServiceAccount" '--task-timeout=3600' '--max-retries=0' '--memory=4Gi' '--cpu=2' '--clear-env-vars' '--clear-secrets' '--clear-volumes' '--clear-volume-mounts' '--clear-network' '--quiet'
Invoke-Checked gcloud run jobs add-iam-policy-binding verity-sandbox "--region=$Region" "--member=serviceAccount:$appServiceAccount" '--role=roles/run.jobsExecutorWithOverrides' '--quiet'
if (-not (Test-Native gcloud pubsub topics describe verification-jobs)) {
    Invoke-Checked gcloud pubsub topics create verification-jobs
}
Invoke-VerityPython @('-m', 'scripts.validate_cloud_sandbox_identity', '--project', $ProjectId, '--region', $Region, '--job', 'verity-sandbox', '--service-account', $sandboxServiceAccount, '--image', $sandboxImage)

$commonEnvironment = "VERITY_ENV=cloud,VERITY_ENVIRONMENT=production,VERITY_GEMINI_MODEL=gemini-3.5-flash,VERITY_REPORT_REPO=$ReportRepo,GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_CLOUD_LOCATION=$Region,GOOGLE_CLOUD_VERTEX_LOCATION=global,GOOGLE_GENAI_USE_VERTEXAI=true,VERITY_PUBSUB_OIDC_AUDIENCE=$pubsubAudience,VERITY_PUBSUB_SERVICE_ACCOUNT=$pushServiceAccount,AGENT_VERSION=$sourceRevision"
$applicationSecretMappings = @(
    'VERITY_API_KEY=verity-api-key:latest',
    'VERITY_GITHUB_TOKEN=verity-github-token:latest'
)
if ($judgeSecretAvailable) {
    $applicationSecretMappings += 'VERITY_JUDGE_TEST_KEY=verity-judge-test-key:latest'
}
$applicationSecrets = $applicationSecretMappings -join ','

Invoke-AgentsCliIsolated deploy '--deployment-target' 'cloud_run' '--project' $ProjectId '--region' $Region '--service-name' 'verity' '--service-account' $appServiceAccount '--image' $apiImage '--memory' '2Gi' '--cpu' '1' '--min-instances' '0' '--max-instances' '2' '--concurrency' '4' '--secrets' $applicationSecrets '--update-env-vars' $commonEnvironment '--no-confirm-project'

Invoke-Checked gcloud run jobs deploy verity-pipeline "--image=$apiImage" "--region=$Region" "--service-account=$appServiceAccount" '--command=python' '--args=-m,verity.worker,placeholder' '--task-timeout=3600' '--max-retries=0' '--memory=2Gi' '--cpu=1' "--set-secrets=$applicationSecrets" "--set-env-vars=$commonEnvironment" '--quiet'
Invoke-Checked gcloud run jobs add-iam-policy-binding verity-pipeline "--region=$Region" "--member=serviceAccount:$appServiceAccount" '--role=roles/run.jobsExecutorWithOverrides' '--quiet'

$serviceUrl = Invoke-Text gcloud run services describe verity "--region=$Region" '--format=value(status.url)'
Invoke-Checked gcloud run services add-iam-policy-binding verity "--region=$Region" "--member=serviceAccount:$pushServiceAccount" '--role=roles/run.invoker' '--quiet'

$projectNumber = Invoke-Text gcloud projects describe $ProjectId '--format=value(projectNumber)'
$pubsubServiceAgent = "service-$projectNumber@gcp-sa-pubsub.iam.gserviceaccount.com"
Invoke-Checked gcloud iam service-accounts add-iam-policy-binding $pushServiceAccount "--member=serviceAccount:$pubsubServiceAgent" '--role=roles/iam.serviceAccountTokenCreator' '--quiet'
if (-not (Test-Native gcloud pubsub subscriptions describe verity-worker)) {
    Invoke-Checked gcloud pubsub subscriptions create verity-worker '--topic=verification-jobs' "--push-endpoint=$serviceUrl/internal/pubsub" "--push-auth-service-account=$pushServiceAccount" "--push-auth-token-audience=$pubsubAudience" '--ack-deadline=600' '--message-retention-duration=1d'
}
else {
    Invoke-Checked gcloud pubsub subscriptions modify-push-config verity-worker "--push-endpoint=$serviceUrl/internal/pubsub" "--push-auth-service-account=$pushServiceAccount" "--push-auth-token-audience=$pubsubAudience"
}

Write-Host "Verity deployed privately: $serviceUrl"
Write-Host "No allUsers binding was granted. Phase 8 requires separate explicit owner approval."

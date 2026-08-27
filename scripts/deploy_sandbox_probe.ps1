param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')][string]$ProjectId,
    [ValidatePattern('^[a-z]+-[a-z0-9]+[0-9]$')][string]$Region = "us-central1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $true
}
$repoRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\_python.ps1"
$script:VerityPython = Resolve-VerityPython -RepoRoot $repoRoot

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

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) { throw "Google Cloud SDK (gcloud) is required." }
$workingTree = Invoke-Text git status '--porcelain'
if ($workingTree) { throw "Commit or stash all changes before building the security-proof image." }

$activeAccount = Invoke-Text gcloud auth list '--filter=status:ACTIVE' '--format=value(account)'
if (-not $activeAccount) { throw "Authenticate first with: gcloud auth login" }
Invoke-Checked gcloud config set project $ProjectId
$billingAccount = (Invoke-Text gcloud billing projects describe $ProjectId '--format=value(billingAccountName)').Replace('billingAccounts/','')
if (-not $billingAccount) { throw "The project must be linked to a billing account." }

Invoke-Checked gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com cloudasset.googleapis.com logging.googleapis.com secretmanager.googleapis.com pubsub.googleapis.com firestore.googleapis.com aiplatform.googleapis.com storage.googleapis.com

if (-not (Test-Native gcloud artifacts repositories describe verity "--location=$Region")) {
    Invoke-Checked gcloud artifacts repositories create verity '--repository-format=docker' "--location=$Region" '--description=Verity containers'
}

$sandboxServiceAccount = "verity-sandbox@$ProjectId.iam.gserviceaccount.com"
if (-not (Test-Native gcloud iam service-accounts describe $sandboxServiceAccount)) {
    Invoke-Checked gcloud iam service-accounts create verity-sandbox '--display-name=Verity no-role evaluation tasks'
}

# This policy assertion deliberately fails instead of silently removing an unexpected grant.
$projectPolicy = (Invoke-Text gcloud projects get-iam-policy $ProjectId '--format=json') | ConvertFrom-Json
$sandboxMember = "serviceAccount:$sandboxServiceAccount"
$sandboxRoles = @($projectPolicy.bindings | Where-Object { $_.members -contains $sandboxMember } | ForEach-Object { $_.role })
if ($sandboxRoles.Count -gt 0) {
    throw "Sandbox identity must have zero direct project roles; remove and review: $($sandboxRoles -join ', ')"
}
$sandboxResourceBindings = Invoke-Text gcloud asset search-all-iam-policies "--scope=projects/$ProjectId" "--query=policy:$sandboxServiceAccount" '--format=value(resource)'
if ($sandboxResourceBindings) {
    throw "Sandbox identity must have zero resource-level IAM bindings; remove and review: $sandboxResourceBindings"
}

if (-not (Test-Native gcloud secrets describe verity-sandbox-deny-probe)) {
    Invoke-Checked gcloud secrets create verity-sandbox-deny-probe '--replication-policy=automatic'
}
$sentinelFile = [System.IO.Path]::GetTempFileName()
try {
    [System.IO.File]::WriteAllText($sentinelFile, 'This sentinel is deliberately non-sensitive.', [System.Text.UTF8Encoding]::new($false))
    Invoke-Checked gcloud secrets versions add verity-sandbox-deny-probe "--data-file=$sentinelFile"
}
finally {
    Remove-Item -LiteralPath $sentinelFile -Force -ErrorAction SilentlyContinue
}
if (-not (Test-Native gcloud pubsub topics describe verification-jobs)) {
    Invoke-Checked gcloud pubsub topics create verification-jobs
}

$sourceRevision = Invoke-Text git rev-parse --short=12 HEAD
Invoke-Checked gcloud builds submit '--config=cloudbuild.sandbox-probe.yaml' "--substitutions=_REGION=$Region,_REPOSITORY=verity,_TAG=$sourceRevision" .
$sandboxImageTag = "$Region-docker.pkg.dev/$ProjectId/verity/verity-sandbox:$sourceRevision"
$sandboxImage = Invoke-Text gcloud artifacts docker images describe $sandboxImageTag '--format=value(image_summary.fully_qualified_digest)'
if ($sandboxImage -notmatch '@sha256:[0-9a-f]{64}$') {
    throw "Artifact Registry did not return an immutable sandbox image digest."
}
Invoke-Checked gcloud run jobs deploy verity-sandbox "--image=$sandboxImage" "--region=$Region" "--service-account=$sandboxServiceAccount" '--task-timeout=3600' '--max-retries=0' '--memory=4Gi' '--cpu=2' '--clear-env-vars' '--clear-secrets' '--clear-volumes' '--clear-volume-mounts' '--clear-network' '--quiet'

Invoke-VerityPython @('scripts/validate_cloud_sandbox_identity.py', '--project', $ProjectId, '--region', $Region, '--job', 'verity-sandbox', '--service-account', $sandboxServiceAccount, '--image', $sandboxImage)
Write-Host "Sandbox-only proof passed. The privileged Verity app was not deployed."
Write-Host "Keep scripts/deploy.ps1 and the production configuration guard closed until the owner reviews this evidence."

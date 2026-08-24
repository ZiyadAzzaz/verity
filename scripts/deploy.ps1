param(
    [Parameter(Mandatory=$true)][string]$ProjectId,
    [string]$Region = "us-central1",
    [decimal]$BudgetUsd = 25,
    [string]$ReportRepo = $env:VERITY_REPORT_REPO
)

throw @"
Cloud deployment is intentionally disabled by the 2026-08-24 security audit.
The current Cloud Run sandbox executes untrusted repository code with outbound network
access and a service-account identity that can reach Firestore. That is not equivalent to
the tested local Docker boundary. Implement a credential-free brokered request/result
handoff and evaluation egress controls, then remove this guard only after cloud isolation
tests pass. No Google Cloud resources were changed by this invocation.
"@

$ErrorActionPreference = "Stop"
$apiKey = $env:VERITY_API_KEY
$pubsubToken = $env:VERITY_PUBSUB_VERIFICATION_TOKEN
$githubToken = $env:VERITY_GITHUB_TOKEN
if (-not $apiKey -or $apiKey.Length -lt 24) { throw "Set VERITY_API_KEY to at least 24 random characters." }
if (-not $pubsubToken -or $pubsubToken.Length -lt 24) { throw "Set VERITY_PUBSUB_VERIFICATION_TOKEN to an independent random value." }
if (-not $githubToken) { throw "Set VERITY_GITHUB_TOKEN to a fine-grained token with Issues: write." }
if (-not $ReportRepo -or $ReportRepo -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { throw "Set VERITY_REPORT_REPO as owner/repository." }
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) { throw "Google Cloud SDK (gcloud) is required." }
if (-not (Get-Command agents-cli -ErrorAction SilentlyContinue)) { throw "Install requirements-deploy.txt in agent-dev first." }

gcloud config set project $ProjectId
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com pubsub.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com cloudtrace.googleapis.com logging.googleapis.com

$billingAccount = (gcloud billing projects describe $ProjectId --format='value(billingAccountName)').Replace('billingAccounts/','')
if (-not $billingAccount) { throw "The project must be linked to a billing account before deployment." }
$budgetExists = gcloud billing budgets list --billing-account=$billingAccount --filter='displayName=Verity hackathon budget' --format='value(name)'
if (-not $budgetExists) {
    gcloud billing budgets create --billing-account=$billingAccount --display-name='Verity hackathon budget' --budget-amount="${BudgetUsd}USD" --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
}

gcloud firestore databases describe --database='(default)' 2>$null
if ($LASTEXITCODE -ne 0) { gcloud firestore databases create --database='(default)' --location=$Region --type=firestore-native }

gcloud artifacts repositories describe verity --location=$Region 2>$null
if ($LASTEXITCODE -ne 0) { gcloud artifacts repositories create verity --repository-format=docker --location=$Region --description='Verity containers' }

function Ensure-ServiceAccount([string]$Name, [string]$DisplayName) {
    $email = "$Name@$ProjectId.iam.gserviceaccount.com"
    gcloud iam service-accounts describe $email 2>$null
    if ($LASTEXITCODE -ne 0) { gcloud iam service-accounts create $Name --display-name=$DisplayName }
    return $email
}
$appServiceAccount = Ensure-ServiceAccount 'verity-app' 'Verity orchestrator and agents'
$sandboxServiceAccount = Ensure-ServiceAccount 'verity-sandbox' 'Verity isolated evaluation tasks'
$pushServiceAccount = Ensure-ServiceAccount 'verity-pubsub' 'Verity authenticated Pub/Sub push'

gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$appServiceAccount" --role='roles/datastore.user' --condition=None
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$appServiceAccount" --role='roles/pubsub.publisher' --condition=None
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$appServiceAccount" --role='roles/cloudtrace.agent' --condition=None
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$appServiceAccount" --role='roles/logging.logWriter' --condition=None
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$sandboxServiceAccount" --role='roles/datastore.user' --condition=None

function Set-Secret([string]$Name, [string]$Value) {
    gcloud secrets describe $Name 2>$null
    if ($LASTEXITCODE -ne 0) { gcloud secrets create $Name --replication-policy=automatic }
    $Value | gcloud secrets versions add $Name --data-file=-
}
Set-Secret 'verity-api-key' $apiKey
Set-Secret 'verity-pubsub-token' $pubsubToken
Set-Secret 'verity-github-token' $githubToken
foreach ($secret in 'verity-api-key','verity-pubsub-token','verity-github-token') {
    gcloud secrets add-iam-policy-binding $secret --member="serviceAccount:$appServiceAccount" --role='roles/secretmanager.secretAccessor'
}

$sourceRevision = (git rev-parse --short HEAD 2>$null)
if (-not $sourceRevision) { $sourceRevision = 'manual' }
gcloud builds submit --config=cloudbuild.yaml --substitutions="_REGION=$Region,_REPOSITORY=verity,_TAG=$sourceRevision" .
$apiImage = "$Region-docker.pkg.dev/$ProjectId/verity/verity-api:$sourceRevision"
$sandboxImage = "$Region-docker.pkg.dev/$ProjectId/verity/verity-sandbox:$sourceRevision"

agents-cli deploy --deployment-target cloud_run --project $ProjectId --region $Region --service-name verity --service-account $appServiceAccount --image $apiImage --memory 2Gi --cpu 1 --min-instances 0 --max-instances 2 --concurrency 4 --secrets 'VERITY_API_KEY=verity-api-key:latest,VERITY_PUBSUB_VERIFICATION_TOKEN=verity-pubsub-token:latest,VERITY_GITHUB_TOKEN=verity-github-token:latest' --update-env-vars "VERITY_ENV=cloud,VERITY_ENVIRONMENT=production,VERITY_GEMINI_MODEL=gemini-3.5-flash,VERITY_REPORT_REPO=$ReportRepo,GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_CLOUD_LOCATION=$Region,GOOGLE_GENAI_USE_VERTEXAI=true"

gcloud run jobs deploy verity-sandbox --image=$sandboxImage --region=$Region --service-account=$sandboxServiceAccount --task-timeout=3600 --max-retries=0 --memory=4Gi --cpu=2 --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId"
gcloud run jobs add-iam-policy-binding verity-sandbox --region=$Region --member="serviceAccount:$appServiceAccount" --role='roles/run.developer'
gcloud run jobs deploy verity-pipeline --image=$apiImage --region=$Region --service-account=$appServiceAccount --command=python --args=-m,verity.worker,placeholder --task-timeout=3600 --max-retries=0 --memory=2Gi --cpu=1 --set-secrets="VERITY_API_KEY=verity-api-key:latest,VERITY_PUBSUB_VERIFICATION_TOKEN=verity-pubsub-token:latest,VERITY_GITHUB_TOKEN=verity-github-token:latest" --set-env-vars="VERITY_ENV=cloud,VERITY_ENVIRONMENT=production,VERITY_GEMINI_MODEL=gemini-3.5-flash,VERITY_REPORT_REPO=$ReportRepo,GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_CLOUD_LOCATION=$Region,GOOGLE_GENAI_USE_VERTEXAI=true"
gcloud run jobs add-iam-policy-binding verity-pipeline --region=$Region --member="serviceAccount:$appServiceAccount" --role='roles/run.developer'

gcloud run services add-iam-policy-binding verity --region=$Region --member='allUsers' --role='roles/run.invoker'
$serviceUrl = gcloud run services describe verity --region=$Region --format='value(status.url)'
gcloud run services add-iam-policy-binding verity --region=$Region --member="serviceAccount:$pushServiceAccount" --role='roles/run.invoker'

gcloud pubsub topics describe verification-jobs 2>$null
if ($LASTEXITCODE -ne 0) { gcloud pubsub topics create verification-jobs }
$projectNumber = gcloud projects describe $ProjectId --format='value(projectNumber)'
$pubsubServiceAgent = "service-$projectNumber@gcp-sa-pubsub.iam.gserviceaccount.com"
gcloud iam service-accounts add-iam-policy-binding $pushServiceAccount --member="serviceAccount:$pubsubServiceAgent" --role='roles/iam.serviceAccountTokenCreator'
gcloud pubsub subscriptions describe verity-worker 2>$null
if ($LASTEXITCODE -ne 0) {
    gcloud pubsub subscriptions create verity-worker --topic=verification-jobs --push-endpoint="$serviceUrl/internal/pubsub?token=$pubsubToken" --push-auth-service-account=$pushServiceAccount --push-auth-token-audience=$serviceUrl --ack-deadline=600 --message-retention-duration=1d
} else {
    gcloud pubsub subscriptions modify-push-config verity-worker --push-endpoint="$serviceUrl/internal/pubsub?token=$pubsubToken" --push-auth-service-account=$pushServiceAccount --push-auth-token-audience=$serviceUrl
}

Write-Host "Verity deployed: $serviceUrl"
Write-Host "The URL is public but all job API calls require VERITY_API_KEY. Keep that key private."

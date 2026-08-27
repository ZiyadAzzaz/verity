param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')][string]$ProjectId,
    [ValidatePattern('^[a-z]+-[a-z0-9]+[0-9]$')][string]$Region = "us-central1",
    [Parameter(Mandatory=$true)][switch]$OwnerApprovedPhase8
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $true
}

if (-not $OwnerApprovedPhase8) {
    throw "Phase 8 requires the owner's explicit approval after reviewing the private checkpoint."
}

$service = gcloud run services describe verity "--project=$ProjectId" "--region=$Region" '--format=json' | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Could not read the private Verity service." }
$serviceAccount = $service.spec.template.spec.serviceAccountName
if ($serviceAccount -ne "verity-app@$ProjectId.iam.gserviceaccount.com") {
    throw "Unexpected Verity runtime identity: $serviceAccount"
}
$policy = gcloud run services get-iam-policy verity "--project=$ProjectId" "--region=$Region" '--format=json' | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Could not read the Verity service IAM policy." }
$alreadyPublic = @($policy.bindings | Where-Object { $_.role -eq 'roles/run.invoker' -and $_.members -contains 'allUsers' })
if ($alreadyPublic.Count -gt 0) { throw "Verity is already public; refusing an ambiguous Phase 8 transition." }

gcloud run services add-iam-policy-binding verity "--project=$ProjectId" "--region=$Region" '--member=allUsers' '--role=roles/run.invoker' '--quiet'
if ($LASTEXITCODE -ne 0) { throw "The Phase 8 allUsers binding failed." }
Write-Host "Phase 8 public Run Invoker binding granted to Verity."

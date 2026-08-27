# Verity Live Sandbox Identity Proof

- **Date:** 2026-08-27
- **Project:** `verity-506800`
- **Region:** `us-central1`
- **Source revision:** `1b0ff95c74d074518da9c4512273a531339834d8`
- **Build:** `9e9ee62b-552c-428a-a983-0dcd0a3570b0`
- **Execution:** `verity-sandbox-rcxvn`
- **Result:** **PASS — six explicit IAM denials**

## Exact validator output

```json
{
  "api_denials": {
    "cloud_run_execute": 403,
    "cloud_storage_list": 403,
    "firestore_write": 403,
    "pubsub_publish": 403,
    "secret_manager_read": 403,
    "vertex_ai_list": 403
  },
  "execution": "projects/verity-506800/locations/us-central1/jobs/verity-sandbox/executions/verity-sandbox-rcxvn",
  "metadata_token_obtained": true,
  "passed": true,
  "service_account": "verity-sandbox@verity-506800.iam.gserviceaccount.com"
}
```

## Bound artifact and runtime

- Immutable image:
  `us-central1-docker.pkg.dev/verity-506800/verity/verity-sandbox@sha256:615e71df55395e0ec84e875bf943bda22d6e84d62d95835a59965cc7c12853b3`
- Identity: `verity-sandbox@verity-506800.iam.gserviceaccount.com`
- Direct project IAM roles: zero
- Discovered resource-level IAM bindings: zero
- Task: one
- CPU/memory: 2 vCPU / 4 GiB
- Execution result: one succeeded task in 89.433 seconds
- Metadata token: obtained inside the sandbox, never printed or persisted

## Acceptance decision

The proof meets the previously fixed acceptance rule: every targeted API returned an explicit
authentication/authorization denial. No 2xx, 404, timeout, network failure, or inconclusive result
was accepted. The result proves that untrusted sandbox code can obtain its workload token but
cannot use it to write Firestore, read the sentinel secret, publish Pub/Sub, execute Cloud Run,
list Vertex AI models, or list Cloud Storage buckets.

This proof does not itself authorize production deployment. Both production guards remained
closed after the result and require separate owner approval.

## Cost statement

- Fourth build raw equivalent: approximately `$0.008153`
- Fourth Cloud Run execution raw equivalent: approximately `$0.003935`
- Fourth probe total raw equivalent: approximately `$0.012088`
- Cumulative probe build/compute raw equivalent: approximately `$0.029848`
- Firestore creation: `freeTier: true`, observed provisioning cost `$0.00`

The measured usage is inside published free-tier quantities. Posted Billing data can lag and must
be checked separately in Google Cloud Billing Reports before claiming the final invoice amount.

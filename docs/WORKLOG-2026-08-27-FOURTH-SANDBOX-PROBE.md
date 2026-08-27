# Work Record — Firestore Creation and Fourth Sandbox Probe

- **Date:** 2026-08-27
- **Repository:** `ZiyadAzzaz/verity`
- **Branch:** `main`
- **Cloud project:** `verity-506800`
- **Region:** `us-central1`
- **Probe source revision:** `1b0ff95c74d074518da9c4512273a531339834d8`
- **Outcome:** **PASS — validator produced six explicit 403 denials**
- **Production status:** not deployed; both fail-closed guards remain active

## Authorized scope

The owner authorized:

1. creation of the Standard Native-mode `(default)` Firestore database in `us-central1`;
2. one consolidated precondition sweep;
3. one fourth sandbox-probe invocation if every precondition passed; and
4. preparation, but not execution, of the post-pass production deployment plan.

No billing configuration, payment method, budget, alert, quota, plan, or production resource was
authorized or changed.

## Firestore immutable-location precheck

Read-only checks before creation found:

- Firestore database list: empty;
- `(default)` describe: `NOT_FOUND`;
- App Engine application: absent;
- legacy `*.appspot.com` default bucket: absent; and
- expected project/account and billing-enabled status: confirmed.

Those are the known resources that can lock the shared default Google Cloud resource location. No
conflicting location was discovered.

## Firestore creation

The exact authorized action was:

```powershell
gcloud firestore databases create `
  --database='(default)' `
  --location=us-central1 `
  --edition=standard `
  --type=firestore-native `
  --project=verity-506800 `
  --quiet
```

Observed response:

- name: `projects/verity-506800/databases/(default)`;
- location: `us-central1`;
- edition: Standard;
- type: `FIRESTORE_NATIVE`;
- free tier: true;
- creation time: `2026-08-27T09:47:36.972923Z`;
- PITR: disabled;
- App Engine integration: disabled; and
- delete protection: disabled by the service default.

Observed provisioning cost: **`$0.00`**. The database was empty, its response explicitly reported
`freeTier: true`, and no user document operation occurred during creation.

## Consolidated precondition sweep

Every dependency was enumerated before the fourth invocation:

| Precondition | Evidence | Result |
|---|---|---|
| Account/project/billing | expected account, `verity-506800`, billing enabled | Pass |
| CLI and ADC credentials | both could mint a token; values suppressed | Pass |
| Git source | clean local/remote `1b0ff95` | Pass |
| Required APIs | Run, Build, Artifact, Asset, Logging, Secret, Pub/Sub, Firestore, Vertex, Storage | Pass |
| Firestore | `(default)`, Standard Native, `us-central1`, free tier | Pass |
| Artifact Registry | Docker repository `verity` | Pass |
| Sandbox identity | expected service account exists | Pass |
| Sandbox IAM | zero project roles and zero discovered resource bindings | Pass |
| Sentinel secret | present with two pre-run versions | Pass |
| Sentinel topic | `verification-jobs` exists | Pass |
| Cloud Run Job | private, no public IAM | Pass |
| Cloud Build pool | no private-pool marker; default pool | Pass |
| Validator launch | module help/import passed | Pass |
| Logging reader | corrected reader retrieved the prior real report | Pass |
| Production absence | no Run service, Pub/Sub subscription, or production secrets | Pass |
| Production guards | deployment and configuration guards active | Pass |
| Local quality gate | Ruff, 111 formatted files, mypy 32 files, 265 tests | Pass |

The first combined tool connection ended after item 7 while the underlying read-only sweep entered
the job check. Items 8–13 were immediately completed as the remainder of the same precondition
phase. No cloud mutation occurred during either segment, and every item produced an explicit pass
before the probe began.

## Cost gate before invocation

Projected incremental raw build/compute usage was about `$0.012`, with cumulative raw probe usage
around `$0.03`. This was below the ~$25 project target, the `$10` single-action stop gate, and the
`$50` cumulative check-in gate.

## Fourth probe chronology

The command was invoked once:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\deploy_sandbox_probe.ps1 `
  -ProjectId verity-506800 -Region us-central1
```

Observed progression:

1. existing repository, service account, secret, topic, and job were reused;
2. non-sensitive sentinel version `3` was added;
3. default-pool build `9e9ee62b-552c-428a-a983-0dcd0a3570b0` succeeded;
4. build start/finish duration was **81.533 seconds**;
5. immutable digest
   `sha256:615e71df55395e0ec84e875bf943bda22d6e84d62d95835a59965cc7c12853b3`
   was resolved;
6. private job `verity-sandbox` was updated to that digest;
7. validator created exactly one execution, `verity-sandbox-rcxvn`;
8. the execution completed with one succeeded task in **89.433 seconds**; and
9. the corrected Logging reader retrieved and decoded the exact structured report.

There was no retry and no unexpected result.

## Exact security result

| Probe | Status | Result |
|---|---:|---|
| Firestore write | 403 | Pass |
| Secret Manager read | 403 | Pass |
| Pub/Sub publish | 403 | Pass |
| Cloud Run execution | 403 | Pass |
| Vertex AI listing | 403 | Pass |
| Cloud Storage listing | 403 | Pass |

Additional validator fields:

- `metadata_token_obtained: true`;
- expected service account: true;
- `passed: true`; and
- full execution name:
  `projects/verity-506800/locations/us-central1/jobs/verity-sandbox/executions/verity-sandbox-rcxvn`.

The exact JSON is preserved in
[CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md](CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md).

## Post-action inventory and cost

| Meter | Observed usage | Raw list-price equivalent |
|---|---:|---:|
| Firestore creation | free-tier empty database | `$0.00` |
| Cloud Build | 81.533 seconds | `$0.008153` |
| Cloud Run CPU | 178.865 vCPU-seconds | `$0.003220` |
| Cloud Run memory | 357.731 GiB-seconds | `$0.000715` |
| Fourth probe total | build plus execution | **`$0.012088`** |
| All probe build/compute | cumulative | **`$0.029848`** |

Other observations:

- Artifact Registry: 444.338 MB, still below the first 0.5 GiB-month allowance;
- latest source archive: 2,532,894 bytes;
- Secret Manager: three active sentinel versions, below the first six-version allowance;
- Pub/Sub publish by sandbox: denied, so no successful message throughput;
- sandbox IAM after the pass: zero project and discovered resource grants; and
- production services/subscriptions: absent.

The first read-only execution-detail command included an unsupported `--job` flag and returned no
data. It was corrected to the supported execution-name syntax; no resource changed.

Expected credit draw remains `$0.00` if account-level free-tier aggregates were available. The
agent could not access posted Billing Reports, so `$0.029848` is the conservative measured raw
equivalent, not an invoice claim.

## Production and financial boundary

- No production API or pipeline job was deployed.
- No public endpoint was created.
- No production secret was created.
- No Pub/Sub subscription was created.
- No production IAM role was granted.
- No production guard was removed.
- No billing/payment/budget/quota/plan configuration was touched.

## Production-readiness findings

Read-only preparation found two local prerequisites for the next phase:

1. `google-agents-cli` / `agents-cli` is not installed in `agent-dev`.
2. `.env` contains the GitHub token and report repository keys, but lacks `VERITY_API_KEY`, the
   separate random application-authentication secret. No secret value was printed.

The API image also copies source without installing the `verity-agent` distribution. Current
module imports work, but the declared console entry points are absent. The next phase must resolve
this with an explicit package-install step and container smoke tests before guard removal.

A second worker-specific blocker was found during plan review: `verity/worker.py` defines `main()`
but has no `if __name__ == "__main__"` call. The deployed pipeline blueprint uses
`python -m verity.worker <job_id>`, which would currently import the module and exit without
processing the job. This must be fixed and regression-tested before deployment; a zero-exit no-op
must not be mistaken for a successful worker.

## Professional assessment

This is the decisive least-privilege evidence the project was waiting for. It is stronger than a
policy inspection alone: real untrusted-container code obtained its workload token and six live
Google APIs independently refused it. The strict rule correctly rejected the prior 404 and now
accepts only the six real 403 responses.

The security proof justifies moving to an owner review of production deployment; it does not
justify silently opening production. The remaining risks have shifted from sandbox credential
isolation to deployment correctness: packaging, secrets, IAM ordering, OIDC push, service health,
pipeline execution, evidence publication, and cost tracking. Those are addressed in the prepared
plan, but execution remains separately gated.

## Next step

The owner should review this record and the exact JSON, inspect posted Billing data, then explicitly
authorize implementation of
[POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md](POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md).

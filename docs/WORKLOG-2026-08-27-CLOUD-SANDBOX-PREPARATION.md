# Work Record — Live-Cloud Sandbox Preparation

- **Date:** 2026-08-27
- **Repository:** `ZiyadAzzaz/verity`
- **Branch:** `main`
- **Cloud project:** `verity-506800`
- **Region:** `us-central1`
- **Operator account:** `ziyadazzazdesigner@gmail.com`
- **Starting revision:** `b1782be`
- **Current revision before this record:** `b0aadbc`
- **Authorized rerun revision:** `b3a3e0e`
- **Validator-launch correction:** `0a43e8e`
- **Status:** superseded by the completed third-attempt record; production approval remains closed

**Follow-up:**
[WORKLOG-2026-08-27-THIRD-SANDBOX-PROBE.md](WORKLOG-2026-08-27-THIRD-SANDBOX-PROBE.md)
records the local pre-flight, packaging assessment, real execution, five explicit denials,
Firestore 404, logging-reader repair, cost, and next owner decision.

## Objective and boundary

The authorized objective was to confirm cloud readiness and run only the no-role sandbox identity
probe described in `docs/history/verity-cloud-live-hard-rule-prompt.md`. The probe must prove that
a stolen sandbox metadata token is denied by six sensitive Google Cloud APIs.

The following were explicitly outside scope and were not deployed: the Verity API, pipeline
worker, Gemini key, GitHub token, Pub/Sub push subscription, public endpoint, production
application identity, and P1/P2 audit work. Production guards must remain closed until the owner
reviews a complete passing proof and separately approves the next step.

## Financial rule applied

- The true promotional credit is **$450**.
- The project target is approximately **$25 or less** total spend.
- Stop before any action projected above **$10** or if cumulative actual spend crosses **$50**.
- Never modify billing, payments, budgets, alerts, spend caps, quota, or plan configuration.
- Report the closest observable actual cost after every cloud action.

The sandbox probe was conservatively projected below **$1**, even without assuming free-tier
coverage. The primary possible charge was one default Cloud Build at the published rate of
`$0.006/minute`; the expected remaining resources were free-tier or penny-scale.

## Readiness checks

Observed before mutation:

- Google Cloud SDK `582.0.0` was installed.
- The active `gcloud` account was the expected operator account.
- `gcloud` configuration and project visibility both reported `verity-506800` as active.
- Billing was enabled; only read-only billing status was inspected.
- CLI and Application Default Credentials were available; no token value was printed or saved.
- Docker was installed but its local daemon was stopped. This did not block the remote Cloud
  Build path.
- The base PATH Python lacked required Google Cloud packages.
- `D:\Anaconda\envs\agent-dev\python.exe` had the required packages and `pip check` passed.

## Findings and decisions

### 1. Wrong Python interpreter in the deployment scripts

**Finding:** `deploy_sandbox_probe.ps1` called PATH `python`, which resolved to the base Anaconda
environment and could not import the required Google Cloud libraries.

**Decision:** use the repository's existing `_python.ps1` resolver and execute the validator with
`Invoke-VerityPython`. This selects the verified `agent-dev` environment and fails closed when no
supported Python 3.11 environment exists.

### 2. Forbidden billing-budget mutation in the dormant production blueprint

**Finding:** `scripts/deploy.ps1` contained logic that listed and automatically created a Cloud
Billing budget. The production script was already blocked by a fail-closed guard, so the logic had
not run during this session, but keeping it violated the owner's absolute financial boundary.

**Decision:** remove the `BudgetUsd` parameter and all billing-budget list/create commands. The
script may read whether the project is linked to billing, but cannot change financial settings.

### 3. First live probe stopped on an expected missing resource

The first authorized probe invocation was:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy_sandbox_probe.ps1 `
  -ProjectId verity-506800 -Region us-central1
```

Required service APIs were enabled successfully. The next read-only check correctly found that the
`verity` Artifact Registry repository did not yet exist, but `gcloud.ps1` emitted the expected
`NOT_FOUND` as a PowerShell error record. Global terminating-error behavior stopped the script
before it could enter the intended create-if-missing branch.

This was a local error-handling defect, not an IAM denial result. In accordance with the hard rule,
the cloud action was stopped and was not retried.

**Decision:** make `Test-Native` locally suppress error records only while performing a negative
existence query, capture the native exit code, and restore `ErrorActionPreference=Stop` in a
`finally` block. Mutation commands retain strict fail-fast behavior.

## Cloud action inventory and cost

Read-only post-failure inspection confirmed:

| Item | Observed state |
|---|---|
| Approved Google service APIs | Enabled |
| `verity` Artifact Registry repository | Absent |
| `verity-sandbox` service account | Absent |
| Sandbox sentinel secret | Not created by this run |
| `verification-jobs` sentinel topic | Not created by this run |
| Cloud Build executions | None |
| Sandbox container images | None created by this run |
| `verity-sandbox` Cloud Run Job | Absent |
| Sandbox job executions | None |
| Six stolen-token denial checks | **Not executed** |

Enabling an API does not itself consume the metered service. With no build, storage, job, or
execution usage observed, the calculated cost of this partial action is **$0.00**. No posted
invoice-level cost line was available at inspection time, so this is an observed-usage calculation,
not a claim that delayed billing data was queried successfully. Cumulative observed cost added by
this action is **$0.00**.

## Files changed

- `scripts/deploy_sandbox_probe.ps1`: resolve the verified Python environment and safely handle
  negative resource-existence checks.
- `scripts/deploy.ps1`: apply the same interpreter/error-handling correction and remove all
  budget mutation logic; the production fail-closed guard remains.
- `tests/test_production_guardrails.py`: enforce interpreter selection, absence of billing-budget
  commands, sandbox-only scope, and restoration of strict PowerShell error behavior.
- `docs/CLOUD-LIVE-SAFETY.md`: record the true credit, spend target, hard gates, forbidden billing
  actions, and initially authorized resource boundary.
- `docs/history/verity-cloud-live-hard-rule-prompt.md`: preserve the owner's source instruction.
- `README.md` and `docs/STATE.md`: surface the current cloud safety rule.

No `.env` value was read into documentation, committed, printed, or pushed.

## Validation evidence

Before the first probe:

- Ruff lint: passed.
- Ruff formatting check: 107 files passed.
- Strict mypy: 32 source files passed.
- PowerShell AST parsing: both deployment scripts passed.
- Python dependency consistency: `pip check` passed in `agent-dev`.
- Full non-Docker suite: **264 passed, 3 skipped, 9 deselected**, with two upstream warnings.
- Targeted production guardrails: **28 passed**.

After correcting `Test-Native`:

- Targeted production guardrails: **28 passed**.
- PowerShell AST parsing: both scripts passed.
- Real read-only missing-repository check returned `False` and restored
  `ErrorActionPreference=Stop`, proving the expected negative lookup no longer aborts the script.

A mistakenly invoked targeted test under base Anaconda produced three configuration-related
failures because that was not the locked project environment. The identical suite passed 28/28
under `agent-dev`; this reinforces why the deployment script now resolves the project environment
explicitly.

## Git record

| Commit | Purpose | Remote state |
|---|---|---|
| `94ce060` | Enforce the live-cloud financial boundary and fix Python selection | Pushed to `origin/main` |
| `b0aadbc` | Handle absent sandbox resources safely | Pushed to `origin/main` |
| `b3a3e0e` | Verify every sandbox lookup and enforce the default Cloud Build pool | Pushed to `origin/main` |
| `0a43e8e` | Launch the cloud identity validator as an import-safe repository module | Pushed to `origin/main` |

At the end of the initial implementation, local and remote `main` both resolved to
`b0aadbca41899301a40554d86e12cb281d5226ea`.

## Security status and residual risk

- No production service or privileged identity was deployed.
- No secrets or credential values were exposed.
- No billing or payment configuration was changed.
- Both production fail-closed guards remain active.
- The core live security claim is still unproven because all six token-denial checks have not run.
- A passing local regression test reduces deployment-script risk but cannot replace live IAM
  evidence.

## Professional assessment

Stopping was the correct decision. Retrying immediately would have violated the explicit rule for
unexpected cloud behavior and could have hidden a reproducibility defect. The defect is narrow,
understood, corrected, and validated. The resulting script is safer than the initial version
because it distinguishes expected negative lookups from failed mutations without weakening global
error handling.

The project is now technically ready for one fresh sandbox-only probe. Confidence in the local
preconditions is high; confidence in the cloud isolation claim must remain pending until the real
JSON contains six explicit `401` or `403` results.

## Recommended next step

Wait for the owner to explicitly authorize a fresh sandbox probe. After authorization:

1. reconfirm clean local/remote revision and project identity;
2. restate the sandbox-only scope and sub-$1 projection;
3. run the probe once with no automatic retry;
4. treat any result other than explicit `401` or `403` for any of the six checks as failure;
5. inventory real resource usage and report the closest observable actual cost;
6. write the complete JSON evidence and decision into this record or a linked follow-up record;
7. keep production guards closed until the owner separately reviews and approves the next phase.

## Authorized rerun — second attempt

The owner supplied and authorized
`docs/history/verity-rerun-probe-prompt.md`. Before the rerun, two specific conditions were
confirmed and committed:

1. the shared `Test-Native` helper was used for Artifact Registry, the sandbox service account,
   the sentinel secret, and the Pub/Sub topic; an explicit Cloud Run Job existence check was added
   through the same helper so every expected absent resource followed the corrected path; and
2. `cloudbuild.sandbox-probe.yaml` declared no `pool`, `workerPool`, or private-pool option, so
   Cloud Build would use the default worker pool. Regression tests now enforce this condition.

Targeted guardrails passed **28/28**, PowerShell AST parsing passed, the worktree was clean, and
local and remote `main` both resolved to
`b3a3e0e21f4e4b0ff5ec3019ac1ef6c93d8f2c13`. The expected account, project, billing-enabled
status, and both production guards were reconfirmed. Projected cost remained below **$1**, so the
$10 per-action gate did not trigger.

### Exact single invocation

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\deploy_sandbox_probe.ps1 `
  -ProjectId verity-506800 -Region us-central1
```

There was no automatic retry.

### Successful progression

The single invocation successfully:

- confirmed the active project and billing-enabled status without changing billing;
- created the `verity` Docker repository in `us-central1`;
- created `verity-sandbox@verity-506800.iam.gserviceaccount.com`;
- proved the sandbox identity had zero direct project roles and zero discovered resource IAM
  bindings;
- created `verity-sandbox-deny-probe` with one deliberately non-sensitive version;
- created the `verification-jobs` sentinel topic;
- completed default-pool Cloud Build `65d041cb-3b3f-4422-b023-a9682cc266cc` successfully;
- built revision tag `b3a3e0e21f4e` in **60.914 seconds**;
- produced immutable image digest
  `sha256:a8dba0655a6c35f3dac2fa99818dae91319b915f8c28e252c7ddc8ebb50f9822`; and
- created the private `verity-sandbox` Cloud Run Job with no execution.

### Second stop condition

After the job definition was created, the local validator was launched as a file path:

```text
python scripts/validate_cloud_sandbox_identity.py ...
```

Python placed `scripts/`, rather than the repository root, at the front of its import path. The
validator therefore stopped with:

```text
ModuleNotFoundError: No module named 'verity'
```

This occurred before `JobsClient.run_job`, so the sandbox container never started and no metadata
token was requested. Read-only Cloud Run inspection confirmed an empty execution list. The six
required denial results are therefore **not executed**, not passed, and this attempt is **not a
valid live security proof**. The command was not retried.

### Local correction after the stop

Both deployment scripts now launch the validator as a repository module:

```text
python -m scripts.validate_cloud_sandbox_identity ...
```

This keeps the repository root importable. A direct local `--help` invocation succeeded, the
validator/guardrail selection passed **35/35**, both deployment scripts passed PowerShell AST
parsing, and the complete non-Docker gate passed:

- Ruff lint: passed;
- Ruff format: **110 files** already formatted;
- strict mypy: **32 source files** passed; and
- pytest: **264 passed, 3 emulator tests skipped, 9 Docker tests deselected**, with two upstream
  deprecation warnings.

No cloud validator or job execution was used to test this correction, because that would have
constituted an unauthorized retry.

## Second-attempt resource and cost record

| Resource or operation | Observed usage | Free-tier/credit assessment |
|---|---:|---|
| Cloud Build default pool | 60.914 seconds | Raw list price **$0.006091**; eligible for the account's first 2,500 free default-pool minutes |
| Artifact Registry | 179.128 MB | Below the first 0.5 GiB-month free allowance, subject to billing-account aggregate usage |
| Cloud Build source archive | 2,520,513 bytes | Penny-scale storage; posted charge not yet visible |
| Secret Manager | 1 active version, management only | Within the first 6 active versions and 10,000 access operations if account allowance remains |
| Pub/Sub | 1 topic, zero throughput | No throughput charge; first 10 GiB/month is free |
| Cloud Run Job | Definition only, zero executions | **$0.00 compute usage** |
| Service account and API enablement | Configuration only | No metered workload observed |

The in-app browser had no attached browser surface, so the authenticated Billing console could not
be inspected. No billing export or configuration was created as a workaround. Consequently:

- **posted invoice cost:** unavailable because the Billing UI was inaccessible and costs can lag;
- **observed raw list-price upper bound:** approximately **$0.0061**, plus negligible short-lived
  storage;
- **likely credit draw:** **$0.00** if the billing account's published free-tier aggregates were
  still available; and
- **conservative recorded cumulative cost for these probe attempts:** less than **$0.01**, far
  below the ~$25 target and the $10/$50 check-in gates.

Official pricing references used for the calculation:

- https://cloud.google.com/build/pricing
- https://cloud.google.com/artifact-registry/pricing
- https://cloud.google.com/secret-manager/pricing
- https://cloud.google.com/pubsub/pricing
- https://cloud.google.com/run/pricing

Free tiers are aggregated by billing account. Without the posted Billing report, eligibility based
on this project's measured usage must not be misrepresented as proof that another project on the
same billing account did not consume part of an allowance.

## Updated professional assessment

The cloud-side progression was clean and the most important isolation precondition remains true:
the deployed sandbox identity has no direct or discovered resource-level IAM grant. The second
failure was local and deterministic, not a cloud-permission ambiguity. Stopping again was required
because proceeding through a manually modified validator command would have been a retry outside
the authorized single invocation.

The module-launch correction is small and now has stronger validation than the failed path had.
The existing cloud resources are suitable for a rerun: create-if-missing steps should observe and
reuse them, the image is immutable, and no Cloud Run execution has yet occurred. Nevertheless, the
central security claim remains unproven until one execution returns six explicit `401` or `403`
responses.

## Updated recommended next step

Obtain explicit owner approval for one new sandbox-probe invocation. On approval:

1. reconfirm the pushed module-launch correction, local/remote revision, account, project,
   zero-role identity, default pool, and cost
   projection;
2. run the complete probe once without manual continuation or automatic retry;
3. require explicit `401` or `403` for Firestore write, Secret Manager read, Pub/Sub publish,
   Cloud Run execution, Vertex AI listing, and Cloud Storage listing;
4. preserve the exact JSON and execution name;
5. measure actual execution duration and update this cost record; and
6. keep production guards closed for separate owner review regardless of the outcome.

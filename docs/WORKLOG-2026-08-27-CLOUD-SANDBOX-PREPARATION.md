# Work Record — Live-Cloud Sandbox Preparation

- **Date:** 2026-08-27
- **Repository:** `ZiyadAzzaz/verity`
- **Branch:** `main`
- **Cloud project:** `verity-506800`
- **Region:** `us-central1`
- **Operator account:** `ziyadazzazdesigner@gmail.com`
- **Starting revision:** `b1782be`
- **Current revision before this record:** `b0aadbc`
- **Status:** preparation fixed and pushed; live proof stopped pending explicit rerun approval

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

At the end of implementation, local and remote `main` both resolved to
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

# Work Record — Third Live Sandbox Probe

- **Date:** 2026-08-27
- **Repository:** `ZiyadAzzaz/verity`
- **Branch:** `main`
- **Cloud project:** `verity-506800`
- **Region:** `us-central1`
- **Authorized source revision:** `c58134b391db5f98771b89c7a3435318a72c4a31`
- **Post-run logging fix:** `f9eac4c825c3689024eab2ce1f8c3d2236585846`
- **Outcome:** failed acceptance — five explicit 403 denials; Firestore returned 404
- **Production status:** both fail-closed guards remain active

**Follow-up:**
[WORKLOG-2026-08-27-FOURTH-SANDBOX-PROBE.md](WORKLOG-2026-08-27-FOURTH-SANDBOX-PROBE.md)
records creation of the authorized database and the passing six-denial proof.

## Objective and authorization

The owner authorized one third invocation of the sandbox-only identity probe after a mandatory
local dry run and an assessment of whether the prior `verity` import failure could also affect the
future API or worker deployment.

The authorized command was:

```powershell
powershell -File scripts/deploy_sandbox_probe.ps1 `
  -ProjectId verity-506800 -Region us-central1
```

The acceptance rule remained strict: Firestore write, Secret Manager read, Pub/Sub publish, Cloud
Run execution, Vertex AI listing, and Cloud Storage listing must each return explicit `401` or
`403`. Any other response is failure. Only one invocation was authorized, with no retry or manual
job continuation after an unexpected result.

## Step 1 — Local-only pre-flight

No `gcloud`, Cloud Build, Cloud Run, or other cloud action was used for the dry run.

The corrected launch path executed successfully:

```powershell
D:\Anaconda\envs\agent-dev\python.exe `
  -m scripts.validate_cloud_sandbox_identity --help
```

Observed results:

- module launch: passed;
- `scripts.validate_cloud_sandbox_identity` import: passed;
- `verity` import: resolved to the repository's `verity/__init__.py`;
- validator `main()` callable: true;
- API module import: passed;
- API `create_app` callable: true;
- worker `main` callable: true; and
- validator/production-guardrail tests: **35 passed**.

This caught no remaining launch or import failure, so the local pre-flight gate passed.

## Step 2 — Packaging assessment

The previous `ModuleNotFoundError` was specific to launching a repository script by file path.
That invocation put `scripts/`, rather than the repository root, on Python's import path.

The current production API image does not use that path:

- `Dockerfile` sets `WORKDIR /app`;
- it copies `app/` and `verity/` beneath `/app`; and
- it starts `uvicorn app.fast_api_app:app` from that working directory.

The sandbox image similarly sets `WORKDIR /opt/verity`, copies `verity/`, and uses
`python -m verity.sandbox_runner`. Its build already succeeded. The current cloud worker flow is a
Pub/Sub push to the API's `/internal/pubsub` endpoint; it does not invoke the `verity-worker`
console command.

### Residual packaging risk

The project itself is not installed as a Python distribution in the current images. Dependencies
are installed, source is copied, and `pyproject.toml` is copied, but the Dockerfile does not run
`pip install .`. Consequently, the existing source-import API command is valid, but the
`verity-api` and `verity-worker` console entry points declared in `pyproject.toml` are not installed
in that environment.

Professional assessment:

- **Risk to the current API command:** low; its source-import path is explicit and locally smoke
  tested.
- **Risk to a future separately launched `verity-worker`:** real; invoking the console command
  would fail unless the project is installed or the worker is changed to a module launch.
- **Required before full production deployment:** install the project with a controlled
  `pip install --no-deps .` step or standardize every component on `python -m`, then container-smoke
  both API and worker entry points.

This hardening was recorded rather than mixed into the sandbox probe because it does not affect
the current sandbox image and production deployment remains separately blocked.

## Final pre-run checks

Immediately before the cloud action:

- active account: `ziyadazzazdesigner@gmail.com`;
- configured and visible project: `verity-506800`;
- billing-enabled status: true, inspected read-only;
- local and remote `main`: identical at `c58134b`;
- worktree: clean;
- sandbox service account project roles: zero;
- discovered resource-level bindings: zero;
- existing sandbox executions: zero;
- Cloud Build configuration: default pool; and
- both production guards: active.

Projected incremental raw usage was below `$0.02`, far below the `$10` per-action stop gate.

## Third invocation chronology

The command was invoked exactly once.

1. Existing Artifact Registry repository, service account, sentinel secret, Pub/Sub topic, and
   Cloud Run Job were detected and reused.
2. Non-sensitive secret version `2` was created.
3. Default-pool Cloud Build `0d14ddb8-148d-45dd-87e9-02604c0129a9` succeeded.
4. The build ran from `09:23:23.557Z` through `09:24:28.698Z`, approximately **65.141 seconds**.
5. The image tag was `verity-sandbox:c58134b391db`.
6. The deployed immutable digest was:

   ```text
   sha256:9b2ac0c9e082e69453a4fadf18d9da5f3baa4681718cf7800decc7151b11f907
   ```

7. The existing private `verity-sandbox` Job was updated to that digest.
8. The corrected validator launched successfully and created execution `verity-sandbox-fmg7n`.
9. The execution used one task, 2 vCPU, 4 GiB, zero retries, and the intended
   `--verify-identity verity-506800:us-central1` override.
10. The container execution completed successfully in **1m57.14s** with one succeeded task.
11. The validator then failed while querying Cloud Logging with
    `400 order_by must be on timestamp`.
12. The invocation stopped. No second execution, rerun, or manual job continuation was issued.

## Recovered immutable identity report

A read-only query of the already-written stdout log recovered the sandbox's structured report.
The metadata token was obtained for the expected identity:

```text
verity-sandbox@verity-506800.iam.gserviceaccount.com
```

Results:

| Probe | HTTP status | Acceptance result |
|---|---:|---|
| Firestore write | **404** | **Fail/inconclusive** — `(default)` database does not exist |
| Secret Manager read | **403** | Pass — explicit IAM denial |
| Pub/Sub publish | **403** | Pass — explicit IAM denial |
| Cloud Run execution | **403** | Pass — `run.jobs.run` denied |
| Vertex AI listing | **403** | Pass — `aiplatform.models.list` denied |
| Cloud Storage listing | **403** | Pass — `storage.buckets.list` denied |

The report proves five sensitive APIs deny the stolen token. It does **not** prove Firestore IAM
isolation: Firestore returned `404 NOT_FOUND` because the database was absent, so authorization
was not evaluated at a real database resource. Under the owner's rule, the third probe is a
failure, not a partial pass.

## Cloud Logging reader defect and correction

Two production-relevant reader defects were found:

1. `order_by="DESCENDING"` is not a valid Cloud Logging order expression; and
2. Cloud Run labels the execution as `run.googleapis.com/execution_name`, not
   `execution_name`.

The reader now uses:

```text
order_by="timestamp desc"
labels."run.googleapis.com/execution_name"="<exact execution>"
```

A regression test asserts both values and confirms the exact execution filter. After correction:

- Ruff lint: passed;
- Ruff formatting: **111 files** passed;
- strict mypy: **32 source files** passed; and
- full non-Docker pytest selection: **265 passed, 3 emulator tests skipped, 9 Docker tests
  deselected**, with two upstream deprecation warnings.

The first quality-gate attempts stopped on import ordering and deterministic Ruff formatting in
the new test. Those local formatting issues were corrected before the final passing gate. No cloud
action was involved.

Commit `f9eac4c` containing the reader correction was pushed to `origin/main`.

## Observed cost

### Third invocation

| Meter | Observed usage | Raw list-price calculation |
|---|---:|---:|
| Default-pool Cloud Build | 65.141 seconds | approximately `$0.006514` |
| Cloud Run CPU | 234.285 vCPU-seconds | approximately `$0.004217` |
| Cloud Run memory | 468.571 GiB-seconds | approximately `$0.000937` |
| Cloud Run execution total | 117.143 seconds | approximately `$0.005154` |
| Third invocation compute | build + job | approximately **`$0.011668`** |

Artifact Registry now reports approximately **311.733 MB**, still below the first 0.5 GiB-month
free storage allowance. Secret Manager has two active versions, below its first six-version free
allowance. Pub/Sub recorded no successful sandbox publish because the attempted request was denied.

### Running probe total

The prior successful build's raw list-price equivalent was approximately `$0.006091`. Including
the third build and execution, cumulative raw build/compute equivalent is approximately
**`$0.017760`**, plus negligible source/archive storage. This remains below `$0.02`, the ~$25
project target, the `$10` single-action gate, and the `$50` cumulative check-in gate.

Published free tiers include 2,500 default-pool Cloud Build minutes per billing account and, for
Cloud Run instance-based billing, 240,000 vCPU-seconds and 450,000 GiB-seconds per month. This
project's measured probe usage is far inside those quantities. However, free tiers are aggregated
by billing account, and the Billing UI was not available to the agent, so the record does not claim
that posted invoice data has confirmed a `$0.00` credit draw. The closest defensible statement is:

- **raw usage equivalent:** approximately `$0.017760` cumulative;
- **expected posted cost:** `$0.00` if the account-level free allowances were available; and
- **posted Billing report:** still requires the owner to inspect it using
  [GOOGLE-CLOUD-CONSOLE-INSPECTION.md](GOOGLE-CLOUD-CONSOLE-INSPECTION.md).

Official pricing references:

- https://cloud.google.com/build/pricing
- https://cloud.google.com/run/pricing
- https://cloud.google.com/artifact-registry/pricing
- https://cloud.google.com/secret-manager/pricing

## Security and production status

- The sandbox metadata token was obtained without being printed or persisted.
- Five sensitive APIs returned explicit IAM denials.
- Firestore remains unproven because no default database exists.
- The sandbox identity still has zero project and discovered resource-level grants.
- No production API, worker, public endpoint, Gemini key, GitHub token, or Pub/Sub push
  subscription was deployed.
- Both production fail-closed guards remain active.
- The recovered report contains no access token or secret value.

## Professional assessment

This attempt crossed the important boundary the first two did not: the real no-role container ran,
stole its own metadata token, and exercised all six target APIs. Five explicit 403 responses are
strong live evidence that the identity boundary is working. The Firestore 404 is an environment
precondition failure, not evidence of excess permission and not evidence of denial.

The result must remain a failed acceptance test because relaxing the rule after seeing five good
responses would weaken the security claim. The next correct action is to create the actual default
Firestore database required by both the probe and the future Verity cloud store, then rerun once
through the now-corrected logging reader.

Creating Firestore is a meaningful one-time decision because its location cannot be changed after
provisioning. The recommended configuration is:

- database ID: `(default)`;
- edition: Standard;
- mode: Firestore Native;
- location: `us-central1`, colocated with the Cloud Run resources; and
- expected probe-scale cost: inside Firestore's one-free-database project quota.

This recommendation is not authorization. No database was created during this work session.
See Google's [Firestore location guidance](https://docs.cloud.google.com/firestore/native/docs/locations)
and [Firestore free-quota pricing](https://cloud.google.com/firestore/pricing).

## Required owner decision and next steps

The owner must explicitly approve the permanent Firestore location and a new probe. Recommended
authorization wording:

```text
Authorize creation of the Standard Native-mode (default) Firestore database in us-central1,
then authorize one new sandbox probe invocation after read-only verification and cost gating.
```

After approval:

1. reconfirm that the project has no existing default database or locked default-resource location
   conflict;
2. project the Firestore action cost and stop if any unexpected configuration appears;
3. create only the `(default)` Standard Native database in `us-central1`;
4. report observed cost after database creation;
5. run local reader/validator tests again;
6. authorize and invoke the sandbox probe once;
7. require six explicit 401/403 results in validator-produced JSON;
8. record execution duration, resource usage, posted/estimated cost, and exact evidence; and
9. leave both production guards closed for separate owner review.

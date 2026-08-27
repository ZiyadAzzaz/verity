# Post-Probe Production Deployment Plan — Authorized Through Private Checkpoint

- **Prepared:** 2026-08-27
- **Project:** `verity-506800`
- **Region:** `us-central1`
- **Security gate:** live sandbox proof passed 6/6
- **Owner authorization:** 2026-08-27, Phases 0–7 and private OIDC validation
- **Execution status:** paused at the Phase 4 hard stop after a rejected build submission; Phase 8
  remains closed

## Goal

Deploy the real Verity API and pipeline safely after resolving packaging/tooling prerequisites,
while preserving the proven no-role sandbox boundary, authenticated Pub/Sub delivery, immutable
images, fail-fast behavior, cost reporting, and evidence quality.

## Required owner inputs before work begins

The owner does not need to send secret values in chat. Before the approved deployment session:

1. add a new random value of at least 32 bytes as `VERITY_API_KEY` in local `.env`; this is the
   Verity HTTP API authentication key, not a Gemini key;
2. retain the existing fine-grained `VERITY_GITHUB_TOKEN` with Issues write access only to the
   intended reports repository;
3. retain `VERITY_REPORT_REPO` for the intended repository; and
4. confirm the Billing Report for `verity-506800` has no unexpected charge.

All three inputs were confirmed present locally by presence and length only. Deployment code loads
only these allow-listed values and never prints them. `agents-cli` must run from an isolated OS
temporary directory because version 1.4.0 otherwise copies every repository `.env` entry into
Cloud Run as plaintext environment variables.

## Phase 0 — Save the proof and open the implementation gate

1. Confirm local/remote `main` contains
   [CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md](CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md).
2. Re-read the six 403 values and execution/digest binding.
3. Obtain explicit owner approval for this plan.
4. Create a focused implementation commit; do not edit historical evidence.

Stop if the proof file, execution, image digest, or zero-role IAM state no longer matches.

## Phase 1 — Resolve packaging and deployment tooling locally

### Package installation inside the API image

Update `Dockerfile` after copying `app/`, `verity/`, `pyproject.toml`, and `README.md`:

```dockerfile
RUN python -m pip install --no-cache-dir --no-deps .
```

Keep the existing explicit Uvicorn command unless container tests show a reason to change it. The
install step must create `verity-agent` metadata and both declared console entry points without
introducing a second dependency resolution.

Add tests that fail unless:

- the Dockerfile installs the local project;
- `verity-api` and `verity-worker` entry points are present in installed metadata;
- `python -m verity.worker --help` succeeds;
- `verity-worker --help` succeeds inside the image; and
- `app.fast_api_app` and `verity.api` import inside the built image.

### Make module-launched worker execution real

`verity/worker.py` currently defines `main()` but does not call it when executed as a module. Add:

```python
if __name__ == "__main__":
    main()
```

Add a subprocess regression test proving `python -m verity.worker --help` emits the argparse help
text. A mere zero exit with empty output is a failure. Add a unit test proving a supplied job ID
reaches `_run(job_id)`. This is mandatory because the pipeline job and its runtime overrides use
`python -m verity.worker <job_id>`.

### Install deployment CLI locally

After approval, in `agent-dev`:

```powershell
D:\Anaconda\envs\agent-dev\python.exe -m pip install -r requirements-deploy.txt
agents-cli deploy --help
```

Record the installed version and `pip check` result. Do not invoke deployment during this step.

### Guard transition

Only in the approved implementation commit:

1. remove the top-level fail-closed `throw` from `scripts/deploy.ps1`;
2. remove only the unconditional live-proof error from `Settings.validate_production`;
3. keep every requirement for cloud, Firestore, Pub/Sub, Cloud Run, project, API key, OIDC
   audience/account, GitHub token, and report repository;
4. replace the old “must reject production” test with a test that accepts only the complete secure
   production configuration; and
5. retain tests rejecting local, Docker, host-subprocess, wrong-project, missing-secret, and
   malformed-resource configurations.

The production guard transition and packaging changes must be reviewed together before any cloud
mutation.

## Phase 2 — Local release gates

Run, in order:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1 -Docker
```

Then build and smoke the API image locally:

```powershell
docker build -t verity-api:predeploy .
docker run --rm --entrypoint python verity-api:predeploy -c `
  "import app.fast_api_app, verity.api, verity.worker; print('imports-ok')"
docker run --rm --entrypoint verity-worker verity-api:predeploy --help
```

Run the API container locally with non-production test settings and verify `/healthz`. Do not pass
the real GitHub token into a local container smoke test.

Additional mandatory checks:

- PowerShell AST parse for `deploy.ps1`;
- `git diff --check`;
- `.dockerignore` and `.gcloudignore` still exclude `.env`, credentials, databases, and Git state;
- `agents-cli deploy --help` supports every flag used by the script;
- the stable configured model `gemini-3.5-flash` is available through the Vertex AI `global`
  endpoint while Cloud Run and Firestore remain in `us-central1`, using metadata discovery or one
  explicitly cost-bounded smoke call;
- process environment contains the three required production values without printing them;
- Git worktree clean and local/remote revision identical; and
- no token or secret appears in Git diff or build context.

Stop on any failure. Do not “test” a fix directly in production.

## Phase 3 — Read-only cloud preflight and cost gate

Confirm:

- project/account/billing-enabled status;
- `(default)` Standard Native Firestore in `us-central1`;
- all required APIs, including Cloud Trace;
- existing `verity` Artifact Registry repository;
- sandbox service account still has zero project/resource bindings;
- latest sandbox execution still shows six 403 denials;
- no existing production service, pipeline job, Pub/Sub subscription, or production secrets unless
  they are expected from a partially completed approved run;
- billing report/cumulative spend remains below the project thresholds; and
- projected full deployment action remains below `$10`.

Expected raw deployment cost is under `$1`: one default-pool two-image build, tiny Cloud Run smoke
traffic, secret versions, and one controlled pipeline/demo verification. Artifact storage is
already 444.338 MB and will likely cross the 0.5 GiB-month free allowance when the larger API image
is stored; at `$0.10/GiB-month` beyond the allowance, expected storage draw is still cents, but it
must be measured and reported rather than called free.

## Phase 4 — Build immutable release images

After all local changes are committed and pushed:

```powershell
gcloud builds submit `
  --config=cloudbuild.yaml `
  --substitutions=_REGION=us-central1,_REPOSITORY=verity,_TAG=<12-char-git-revision> `
  .
```

Require success, record build ID/duration, and resolve both tags to exact SHA-256 digests:

- `verity-api@sha256:...`
- `verity-sandbox@sha256:...`

Stop if either digest is absent, mutable, or not built from the approved clean revision. Report
observed build/storage cost before continuing.

## Phase 5 — Reprove sandbox before privileged deployment

Deploy the new sandbox digest with:

- `verity-sandbox` no-role service account;
- 2 vCPU / 4 GiB;
- max retries 0;
- no environment, secrets, volumes, mounts, or VPC attachment.

Run the validator again and require six explicit 401/403 values. Then grant only the application
service account `roles/run.jobsExecutorWithOverrides` on the individual sandbox job. Reconfirm the
sandbox identity itself still has zero grants.

Stop if any API result, image, identity, or job definition differs.

## Phase 6 — Create least-privilege production identities and secrets

Create/reuse:

- `verity-app@verity-506800.iam.gserviceaccount.com`;
- `verity-pubsub@verity-506800.iam.gserviceaccount.com`;
- secrets `verity-api-key` and `verity-github-token`.

Grant the app identity only the roles currently justified by code:

- Firestore user;
- Pub/Sub publisher;
- Vertex AI user;
- Cloud Trace agent;
- Logging writer and viewer; and
- resource-level executor-with-overrides on `verity-sandbox` and `verity-pipeline`.

Grant Secret Manager accessor only on the two application secrets, not at project scope. Grant the
Pub/Sub service agent token-creator only on the dedicated push identity. Record every binding and
stop on any unexpected inherited or broad role.

Secret values must travel through temporary files with cleanup and must never appear in command
arguments, logs, Markdown, Git, or build context.

## Phase 7 — Deploy privately in dependency order

1. Deploy the API image to Cloud Run service `verity` with min instances 0, max 2, concurrency 4,
   1 vCPU, 2 GiB, application identity, exact environment, and Secret Manager bindings.
2. Keep the service private initially.
3. Deploy `verity-pipeline` from the same immutable API digest, command `python`, placeholder args
   `-m,verity.worker,placeholder`, max retries 0, 1 vCPU, and 2 GiB.
4. Grant the app identity executor-with-overrides only on the pipeline job.
5. Verify the deployed job override contract changes only args to
   `-m verity.worker <job_id>` and keeps command `python`.
6. Invoke authenticated `/healthz` as the operator and require healthy Firestore, Pub/Sub, Vertex,
   and configuration startup.

Stop while the service is still private if health, configuration, image digest, identity, or
secret wiring is wrong.

## Private checkpoint after Phase 7 — authenticated delivery evidence

1. Grant the dedicated push identity Run Invoker on service `verity` while it remains private.
2. Grant the Google-managed Pub/Sub service agent token-creator on that push identity.
3. Create subscription `verity-worker` against topic `verification-jobs` with:
   - push endpoint `<service-url>/internal/pubsub`;
   - Google OIDC push identity `verity-pubsub@...`;
   - exact configured audience;
   - 600-second ack deadline; and
   - one-day retention.
4. Verify a real Pub/Sub delivery against `/internal/pubsub/oidc-probe` is accepted only with valid
   Google OIDC; this probe performs the same verification as the worker route but launches no job.
5. Verify direct unauthenticated and wrong-audience requests are rejected.
6. Record private health, exact IAM, image digests, OIDC evidence, rejection evidence, and
   cumulative cost. Stop for explicit owner review.

## Phase 8 — Public API access, separately approved

Only after the owner reviews the private checkpoint, run `scripts/publish_production.ps1` with its
mandatory `-OwnerApprovedPhase8` switch to grant `allUsers` Run Invoker. The main private deploy
script contains no `allUsers` mutation. Then confirm protected endpoints still require the
separate `VERITY_API_KEY`; `/healthz` and static demo pages may remain intentionally public.

Public access is last so a broken or weakly authenticated deployment is never exposed during
assembly.

## Phase 9 — Controlled end-to-end proof

Run one bounded verification job and record:

- submission HTTP response and job ID;
- Firestore job/trace state;
- Pub/Sub delivery/OIDC result;
- `verity-pipeline` execution name, identity, digest, and status;
- nested `verity-sandbox` execution digest and zero-role identity;
- Vertex AI model calls and bounded repair-attempt count;
- final verdict and evidence provenance;
- GitHub Issue URL in `verity-reports` if the job reaches reporting; and
- dedup/cache behavior on one repeat submission.

Use a deliberately bounded source and stop if projected cost exceeds `$10`, retries exceed the
configured maximum, or any output becomes unverifiable. Never fabricate or replace a missing
metric.

## Phase 10 — Post-deployment evidence and cost

After each cloud mutation, record the closest observable posted cost or measured raw equivalent.
Final evidence must include:

- build and execution durations;
- Artifact Registry size and expected monthly storage draw;
- Cloud Run service/job usage;
- Firestore/Pub/Sub/Secret/Logging/Trace usage;
- Vertex AI request/token cost;
- cumulative project cost against the ~$25 target;
- exact Git revision and all immutable digests;
- IAM policy summaries;
- public/authentication behavior; and
- production guard transition commit.

Update `docs/STATE.md`, create a dated production-deployment work record, commit, and push to
`verity/main`.

## Hard stop conditions

Stop immediately and do not retry automatically if:

- any single action projects above `$10` or cumulative spend crosses `$50`;
- billing/payment/budget/quota/plan changes appear necessary;
- sandbox IAM is nonzero or any denial is not 401/403;
- image digest/source revision does not match;
- a secret appears in output, Git, command arguments, or build context;
- production configuration does not validate;
- private health checks fail;
- Pub/Sub OIDC verification fails;
- public protected endpoints accept no/incorrect API keys;
- pipeline or sandbox retries exceed zero at the infrastructure layer; or
- an end-to-end result cannot be defended from captured evidence.

Do not delete, roll back, make public, or alter IAM to recover from a stop without reporting the
exact state and obtaining any new authority required.

## Google Agent Framework submission narrative

The durable runtime uses real typed Google ADK `LlmAgent` instances for Parser and Debug model
reasoning through `verity.llm`. Environment and Reporter are deterministic Python by design:
Environment executes and measures an already selected reproduction plan inside the isolation
boundary, while Reporter compares recorded evidence and persists a verdict. Adding model reasoning
to those two steps would reduce determinism without adding useful agency. The separate declarative
graph is illustrative; the real Parser/Debug calls are the framework-backed runtime evidence.

## Exact Phase 8 approval gate

Phases 0–7 are authorized. Public exposure is not. Recommended owner wording after reviewing the
private checkpoint:

```text
Authorize Phase 8 public exposure for the private Verity deployment described in the checkpoint
report, then proceed through Phases 9–10 subject to the standing stop rules.
```

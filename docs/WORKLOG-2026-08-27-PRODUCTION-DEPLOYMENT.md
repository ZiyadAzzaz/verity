# Verity Production Deployment Work Record — 2026-08-27

## Objective and authorization boundary

The owner authorized implementation and execution of
`POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md` in project `verity-506800`, region `us-central1`, through
the private Phase 0–7 checkpoint. Granting `allUsers` Cloud Run Invoker is explicitly excluded
until the owner reviews the private evidence and approves Phase 8. Billing, payment, budget,
quota, and plan configuration remain permanently out of scope.

## Starting state and recovery reconciliation

- Repository: Verity, branch `main`.
- Starting/local/remote revision: `7941911fcab20f8b9c432b427b16587f149b1dc1`.
- Live `origin/main` was verified with `git ls-remote` and matched the local revision.
- Active account: `ziyadazzazdesigner@gmail.com`.
- The resumed worktree contained nine intended mid-implementation files; none had been committed
  or pushed.
- No production cloud mutation had occurred during the interrupted session.

The read-only recovery inventory found only the previously approved sandbox foundation:

- Firestore `(default)`: Native mode, `us-central1`;
- topic `verification-jobs`;
- identity `verity-sandbox@verity-506800.iam.gserviceaccount.com`;
- secret `verity-sandbox-deny-probe`, versions 1–3 enabled;
- job `verity-sandbox`, immutable digest
  `sha256:615e71df55395e0ec84e875bf943bda22d6e84d62d95835a59965cc7c12853b3`, 2 vCPU,
  4 GiB, zero retries, and no job IAM bindings; and
- latest successful execution `verity-sandbox-rcxvn`.

The inventory confirmed absence of Cloud Run services, `verity-pipeline`, `verity-app`,
`verity-pubsub`, production secrets, Pub/Sub subscriptions, Verity project IAM bindings, and
resource-level IAM bindings for all three Verity identities. All ten required APIs, including
Cloud Trace, are enabled. Therefore the actual recovery point was Phase 1/2 local implementation,
not a partial Phase 4–7 deployment.

## Prerequisites and secret handling

The local `.env` is Git-ignored. Presence/length-only checks found:

- `VERITY_API_KEY`: present, 64 characters;
- `VERITY_GITHUB_TOKEN`: present, 93 characters; and
- `VERITY_REPORT_REPO`: present, 25 characters.

No value was printed, recorded, passed in a container smoke, or added to Git. `google-agents-cli`
1.4.0 was installed in the dedicated `agent-dev` environment. `pip check` reported no broken
requirements, and `agents-cli deploy --help` completed successfully.

## Defects and security findings

1. **Critical — module worker silently did nothing.** `python -m verity.worker <job_id>` exited
   successfully without calling `main()`. The pipeline job uses this exact launch path. Added the
   main guard and a regression that proves the supplied ID reaches `_run(job_id)`.
2. **High — API image lacked installed package metadata and console scripts.** Added a no-dependency
   local package install after copying the project so `verity-api` and `verity-worker` exist.
3. **High — private deploy granted public access too early.** The original script granted
   `allUsers` before authenticated push assembly. The private script now contains no such mutation;
   an approval-gated `publish_production.ps1` owns the future Phase 8 transition.
4. **High — Agents CLI could propagate secrets as plaintext.** Version 1.4.0 automatically copies
   every project-root `.env` key into Cloud Run. A dry run correctly rejected the collision between
   plaintext `VERITY_API_KEY`/`VERITY_GITHUB_TOKEN` and Secret Manager mappings. Deployment now
   invokes Agents CLI from a fresh OS temporary directory and passes only explicit non-secret
   environment values plus named Secret Manager references. A repeated dry run showed
   `--no-allow-unauthenticated`, masked non-secret env values, and masked `--update-secrets` only.
5. **Medium — CLI path assumption.** The executable is installed under the Conda environment but
   not global `PATH`. Deployment now resolves it relative to the selected Verity Python.
6. **Validation design — OIDC proof must not start Phase 9.** Added an internal OIDC-only probe
   route that shares the real worker token verifier but launches no pipeline job.
7. **High — compute region was incorrectly coupled to model location.** The preflight returned 417
   for `gemini-3.5-flash` in `us-central1`, while a zero-generation Vertex `countTokens` request
   succeeded at `global` with four input tokens. Added a separately validated
   `GOOGLE_CLOUD_VERTEX_LOCATION=global`; Firestore and both Cloud Run jobs stay in
   `us-central1`.

## Implementation and decisions

- Enabled the production cloud profile only because the preserved live record proves six explicit
  403 denials for the zero-role sandbox.
- Kept all requirements rejecting local, Docker, host-subprocess, missing-auth, and wrong-project
  production configurations.
- Kept the API Uvicorn command explicit and installed project metadata without resolving runtime
  dependencies a second time.
- Added the 12-character source revision as `AGENT_VERSION` for deployed traceability.
- Separated the global Gemini endpoint from the regional data/compute location instead of moving
  Firestore or Cloud Run away from `us-central1`.
- Chose an isolated OS temporary working directory for Agents CLI instead of copying or renaming
  `.env`; this makes secret exclusion structural and leaves the owner's local file untouched.
- Added exact temp-root validation before cleaning the generated CLI directory.

## Local validation evidence

- Focused security/worker/Pub/Sub suite: 38 passed.
- Complete `scripts/test.ps1 -Docker` gate:
  - Ruff lint: passed;
  - Ruff format: 117 files formatted correctly;
  - strict mypy: 32 source files, no issues;
  - latest pytest rerun: 281 passed, 3 official-emulator-only skips, 2 dependency deprecation
    warnings;
  - Docker escape validation: all eight boundary checks passed.
- Local API image: `verity-api:predeploy`, manifest-list digest
  `sha256:169881ff661fc826c253b51c2dbef4c1f192e9a28a7c7f7d11a36ed3a551d1c2`,
  128,931,623 bytes.
- Image imports, `verity-agent` metadata, and both console entry points: passed.
- `verity-worker --help` and `python -m verity.worker --help`: passed with non-empty argparse help.
- Local direct HTTP `/healthz`: `status=ok`, memory store, asyncio queue, host-subprocess smoke
  backend, no setup error, and no real credential present.
- The in-app browser surface exposed no browser instance, so the local health gate was HTTP-only;
  no visual-browser pass is claimed.
- PowerShell AST parse, `git diff --check`, ignore-file secret exclusions, and local build context:
  passed.

## Cost record

All actions in this implementation/recovery portion were local, read-only cloud queries, or one
zero-generation `countTokens` availability check. Observed cloud cost for this portion is `$0.00`.
No billing configuration was read beyond enabled
status and no billing/payment/budget/quota/plan setting was changed. The prior raw sandbox
build/compute equivalent remains `$0.0298481044886`; it is historical, not new spend from this
session.

## Professional assessment and next steps

The resumed state is consistent and safe to continue. The most important new finding was the
Agents CLI `.env` behavior: without the isolated invocation, a convenience tool could have
undermined Secret Manager even though the application configuration was correct. Local release
confidence is now high, but production is not yet deployed.

Next: commit and push the clean release revision, perform the final read-only cost/model/preflight
gate, build immutable images once, re-prove the new sandbox digest, then create least-privilege
identities/secrets and deploy API, pipeline, and OIDC push privately. Update this record with exact
build IDs, digests, IAM, private health/OIDC evidence, and observed cost. Stop before Phase 8.

## Phase 4 submission hard stop

Two implementation revisions were committed and pushed before cloud execution:

- `0782a4420f02b4d1f9f16e1a8eaf933370ac0fa9` — private deployment hardening; and
- `1cc45ee04507ab93f18d093b89e6df0fed8c4c43` — separate global Vertex model location.

Local `HEAD`, live `origin/main`, and the 12-character build tag all matched the second revision,
the worktree was clean, and the 156-file upload context contained no `.env` or `.git` entry. The
single Phase 4 submission then stopped with `INVALID_ARGUMENT` before Google created a build. In
the ad hoc PowerShell invocation, the comma-separated `--substitutions` value was not quoted as one
argument, so PowerShell split it and Cloud Build received a malformed image name. This is a launch
defect, not a container or application failure.

Observed post-stop state:

- no new Cloud Build ID exists;
- no `1cc45ee04507` API or sandbox image/tag exists;
- no Cloud Run service, pipeline, app/push identity, production secret, subscription, or new IAM
  binding exists;
- the proven `verity-sandbox` job and foundation remain unchanged; and
- one source archive exists at
  `gs://verity-506800_cloudbuild/source/1787843200.48887-83a5e27cd5d64c009501abb858569b92.tgz`,
  2,549,568 bytes in the `US` Cloud Build bucket.

No build worker ran, so observed build-compute cost is `$0.00`. The closest conservative raw
list-price exposure for retaining 2.43 MiB in US multi-region Standard storage for a full month,
plus one Class A write, is below `$0.00008` using the official
[Cloud Storage pricing](https://cloud.google.com/storage/pricing); posted billing is not available
through the current CLI surface. This leaves cumulative new exposure from the production attempt
effectively `$0.00` and the project far below both the ~$25 target and every stop threshold.

The hard-stop rule was honored: there was no corrected retry. Evidence-only commits after the stop
advance `main`, so the next authorized attempt must build from a clean detached worktree of the
tested release commit, not from the current `.` while labeling it as an older revision. It must
also pass the entire substitutions flag as one quoted PowerShell argument:

```powershell
$releaseRoot = Join-Path ([System.IO.Path]::GetTempPath()) 'verity-release-1cc45ee04507'
git worktree add --detach $releaseRoot 1cc45ee04507ab93f18d093b89e6df0fed8c4c43
Push-Location $releaseRoot
gcloud builds submit --project=verity-506800 --config=cloudbuild.yaml `
  '--substitutions=_REGION=us-central1,_REPOSITORY=verity,_TAG=1cc45ee04507' .
Pop-Location
```

After the authorized attempt is fully recorded, remove only that exact validated temporary
worktree. Do not delete or rewrite the source release commit.

Professional assessment: cloud state is consistent and recoverable, but Phase 4 is incomplete.
Obtain explicit owner approval for exactly one corrected submission, then resume at Phase 4; do
not skip ahead to identities, secrets, private deployment, or Phase 8.

## Authorized corrected Phase 4 through Phase 7 attempt

### Objective and boundary

The owner authorized one corrected build from detached release
`1cc45ee04507ab93f18d093b89e6df0fed8c4c43`, then private Phases 5–7 if their gates passed.
Phase 8, `allUsers`, public exposure, judge submissions, and production GitHub Issue creation were
not authorized. The account remained `ziyadazzazdesigner@gmail.com`, project `verity-506800`,
region `us-central1`, and local branch `main` at
`8c1abcb2fd17e2374a9fe15b1fac70fc417839cd` when execution resumed.

### Phase 4 — corrected immutable build: passed

The exact OS-temp path `C:\Users\Lenovo\AppData\Local\Temp\verity-release-1cc45ee04507` was
confirmed absent and inside the OS temp root, then registered as a detached worktree at the tested
release. The substitutions flag was passed as one quoted argument.

- Build ID: `2cb7068d-e078-4f01-99b7-ce3a96638dab`
- Status: `SUCCESS`
- Created: `2026-08-27T15:28:59.132440192Z`
- Started: `2026-08-27T15:29:00.293699686Z`
- Finished: `2026-08-27T15:31:24.943347Z`
- Reported duration: `2m25s`
- API digest:
  `sha256:6a708965b91b6eab0602d17aa7b11807675c6c22f15d47bcd7a08647077f6326`
- Sandbox digest:
  `sha256:eee3ffa087db242d6ea2d688853c53b172f3b427861f999f0912ee9b37b75afc`

The observed build used the default pool. At the published `e2-standard-2` default-pool rate of
`$0.006/minute`, the full 145.81-second wall-time raw ceiling is `$0.014581`; the billing account's
monthly Cloud Build free allowance may reduce the posted charge to zero. Billing posting is not
real-time, so the raw usage calculation is recorded separately from posted cost.

Artifact Registry now reports five images totaling 846,261,710 compressed bytes (0.78816 GiB)
before shared-layer deduplication. Above a 0.5 GiB-month allowance, the conservative no-dedup raw
storage ceiling is about `$0.02882/month` at `$0.10/GiB-month`. This is a storage run-rate, not a
charge attributed entirely to this action.

### Phase 5 — immutable sandbox re-proof: passed

Before deployment, the sandbox identity had zero project roles and the sandbox job had no IAM
bindings. The job was updated to the new immutable sandbox digest with 2 vCPU, 4 GiB, retries 0,
and no environment, secrets, volumes, mounts, or network attachment. The validator was invoked
once and returned:

```json
{
  "cloud_run_execute": 403,
  "cloud_storage_list": 403,
  "firestore_write": 403,
  "pubsub_publish": 403,
  "secret_manager_read": 403,
  "vertex_ai_list": 403,
  "passed": true
}
```

- Execution: `verity-sandbox-7qgm6`
- Service account: `verity-sandbox@verity-506800.iam.gserviceaccount.com`
- Metadata token obtained: yes
- Infrastructure retries: `0`
- Completion: `2026-08-27T15:34:29.140991Z`
- Reported execution duration: `1m14.56s`

Post-run IAM again showed zero sandbox project roles. The only job binding added afterward grants
`verity-app` `roles/run.jobsExecutorWithOverrides`; it grants nothing to the sandbox identity.
Using published Tier 1 instance rates and the observed 74.56 seconds, the raw execution ceiling is
approximately `$0.003281` before Cloud Run's monthly free tier. The job deployment itself did not
execute compute.

### Phase 6 — identities, IAM, and secrets: passed

Created:

- `verity-app@verity-506800.iam.gserviceaccount.com`;
- `verity-pubsub@verity-506800.iam.gserviceaccount.com`;
- secret `verity-api-key`, version 1; and
- secret `verity-github-token`, version 1.

The app identity has exactly these direct project roles:

- `roles/aiplatform.user`;
- `roles/cloudtrace.agent`;
- `roles/datastore.user`;
- `roles/logging.logWriter`;
- `roles/logging.viewer`; and
- `roles/pubsub.publisher`.

Each production secret grants `roles/secretmanager.secretAccessor` only to `verity-app`; there is
no project-level Secret Manager grant. Secret values moved from local `.env` through separate
UTF-8 OS-temp files, never appeared in arguments/output, and the exact temporary files were
removed in `finally`. The push and sandbox identities have zero direct project roles. IAM and
Secret Manager control-plane operations have no direct usage charge; the project has five active
secret versions total, within the documented six-version monthly free allowance.

### Phase 7 — private resources created; health gate failed

The first isolated wrapper invocation stopped locally before directory creation because this
Windows PowerShell does not implement `New-Item -LiteralPath`. No CLI/cloud request occurred. The
hard-stop list was audited: no secret, IAM, cloud action, security mismatch, or production
configuration was involved. A local create/enter/remove preflight using `New-Item -Path` passed,
after which the first actual Agents CLI deployment ran from a fresh OS-temp directory. The CLI
masked all values and confirmed `--no-allow-unauthenticated`.

Private API evidence:

- Service/revision: `verity` / `verity-00001-twb`
- URL returned by deploy: `https://verity-291098081728.us-central1.run.app`
- Separate `status.url`: `https://verity-7pauedpknq-uc.a.run.app`
- Immutable image: API digest recorded above
- Identity: `verity-app@verity-506800.iam.gserviceaccount.com`
- Resources: 1 vCPU, 2 GiB, concurrency 4, min 0, max 2
- Secret references: `verity-api-key:latest`, `verity-github-token:latest`
- Vertex location: `global`; compute/Firestore location: `us-central1`
- Service IAM: empty; no `allUsers`, no push invoker
- Revision status: Ready; container healthy in 7.27 seconds; Uvicorn listening on port 8080

The Agents CLI safely added `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` and `APP_URL` pointing to
the deployment-returned URL. No plaintext secret was propagated from `.env`.

Private pipeline evidence:

- Job: `verity-pipeline`, Ready
- Immutable image: same API digest
- Command: `python`
- Args: `-m`, `verity.worker`, `placeholder`
- Identity: `verity-app@verity-506800.iam.gserviceaccount.com`
- Resources: 1 vCPU, 2 GiB, timeout 3600 seconds, max retries 0
- Job IAM: only `verity-app` with `roles/run.jobsExecutorWithOverrides`
- No pipeline execution was started

The first authenticated health request used the service-reported `status.url`. It returned a
Google-front-end `404`; it did not return the Verity `/healthz` JSON. This is a private-health hard
stop. No alternate URL request, unauthenticated request, IAM recovery, redeploy, push binding,
subscription creation, or OIDC probe followed.

Read-only diagnosis found:

- the immutable image contains `GET /healthz`, and local tests cover it;
- the revision is Ready and its startup TCP probe passed;
- Uvicorn logged application startup complete; and
- Cloud Run has no request log for the failed request, so the 404 occurred before the container.

The leading hypothesis is a Cloud Run front-end URL/routing distinction or propagation issue
between `status.url` and the deployment-returned URL, not an application-route failure. This is an
inference, not a passed diagnosis. The safe next action is one separately authorized authenticated
request to `https://verity-291098081728.us-central1.run.app/healthz`, with no redeploy or IAM
change first.

### State after the stop

- Phases 4, 5, and 6 passed.
- Phase 7 created the correct private service and pipeline but did not pass health/OIDC.
- `verity-worker` subscription is absent.
- Service `verity` has no IAM binding; `allUsers` is absent.
- Push identity has no IAM binding; Pub/Sub token-creator was not granted.
- No public endpoint, verification job, or production GitHub Issue was created.
- Phase 8 remains unauthorized and closed.

The service rollout started one 1-vCPU/2-GiB instance for health initialization. A read-only Cloud
Monitoring query observed `227.61233597877103` billable instance-seconds for revision
`verity-00001-twb` through the most recently available minute. At the published Tier 1
instance-based rates, that observed usage has a raw value of approximately `$0.005007`; later
metric minutes and Cloud Billing posting can still lag. The Agents CLI selected
`--no-cpu-throttling`, so the service uses instance-based billing while an instance exists; min
instances 0 still permits scale-to-zero. Pipeline deployment created metadata only and did not
execute compute. The failed request did not reach the container. Combined raw measured/list-price
compute recorded in this continuation is approximately `$0.02287`, plus a conservative Artifact
Registry run-rate of `$0.02882/month`; all remain far below the ~$25 target, `$10` per-action gate,
and `$50` cumulative stop threshold.

### Judge simulation and judging-period retention

[JUDGE-SIMULATION-TEST-PLAN.md](JUDGE-SIMULATION-TEST-PLAN.md) is prepared but was not executed. It
requires a separate local `VERITY_JUDGE_TEST_KEY`, two fresh public sources, terminal verdict and
Issue-link evidence, one duplicate/cache proof, and unauthenticated resolution of every Devpost
link. The plan keeps the service at min instances 0 and explicitly prohibits teardown or generic
cost cleanup from September 1 through October 1. No judge key, public IAM, request, or Issue was
created in this session.

### Files and decision record

Changed documentation only after the stop:

- this work record: exact action/evidence/cost/stop chronology;
- `docs/STATE.md`: current partial private deployment and judging-period retention rule;
- `docs/POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md`: execution status advanced to the Phase 7 stop;
  and
- `docs/JUDGE-SIMULATION-TEST-PLAN.md`: post-Phase-8 checklist, prepared only.

Professional assessment: the security architecture and immutable deployment evidence remain
strong. The decisive sandbox proof passed again, secrets stayed out of plaintext deployment, IAM
is narrow, and the public boundary remains closed. The remaining defect is currently a delivery
URL/health invocation problem, not evidence that the application failed to start. It must still be
resolved and proven before any OIDC configuration or Phase 8 approval.

## Authorized private-health continuation

The owner authorized exactly one authenticated request to
`https://verity-291098081728.us-central1.run.app/healthz`, with no redeployment or IAM change, and
authorized the remaining private Phase 7 gates only if that request passed.

Preconditions were unchanged:

- local `HEAD` and `origin/main` matched
  `d2df9c08e802af79fa259af14a75a6474a284088` with a clean worktree;
- revision `verity-00001-twb` remained Ready on the approved immutable API digest;
- identity remained `verity-app@verity-506800.iam.gserviceaccount.com`; and
- service IAM remained empty.

The one authorized request used the signed-in operator's output from
`gcloud auth print-identity-token`. It returned the same Google-front-end 404 page and no Verity
JSON. Therefore the conditional authorization to continue was not satisfied. No unauthenticated
probe, push IAM, Pub/Sub token-creator binding, `verity-worker` subscription, OIDC probe, or Phase
8 action followed.

### Confirmed cause

The identity token was decoded locally without printing or retaining it. Its safe claims showed:

- issuer: `https://accounts.google.com`;
- subject email: `ziyadazzazdesigner@gmail.com`; and
- audience: `32555940559.apps.googleusercontent.com`.

That audience is the gcloud OAuth client, not either Cloud Run URL. The token was valid but was not
audience-bound to service `verity`, explaining why the Google front end rejected it before the
container. This supersedes the earlier tentative URL-propagation hypothesis.

Two no-request preparation checks then established the available paths:

1. `gcloud auth print-identity-token <human> --audiences=<service-url>` fails locally with
   `Invalid account type for --audiences; requires valid service account`.
2. Impersonating `verity-app` with the correct audience fails because the operator intentionally
   lacks `iam.serviceAccounts.getAccessToken` / `roles/iam.serviceAccountTokenCreator` on that
   identity.

No IAM was added to bypass these controls. The official gcloud-supported path for testing an
IAM-private Cloud Run service with human credentials is `gcloud run services proxy`, which exposes
an authenticated localhost proxy. Its help/launch path was inspected only; it was not started and
no third health request was sent.

### Post-stop evidence and cost

Read-only state after the stop confirms:

- service IAM: empty;
- push identity IAM: empty;
- subscription `verity-worker`: absent; and
- no `allUsers` binding.

Cloud Run request logs contain unauthenticated browser/favicon requests returning expected 403,
but contain no record of either direct scripted `/healthz` request. The authorized request did not
start container work, identity-token issuance has no direct usage charge, and the closest observed
incremental cost is `$0.00`.

Professional assessment: this is now a diagnosed operator-authentication defect, not an API health
failure. The safe next action is one explicitly authorized localhost `/healthz` request through
`gcloud run services proxy`, with no IAM/redeploy change. If that passes, continue the original
private unauthenticated rejection and OIDC gates; Phase 8 must remain closed.

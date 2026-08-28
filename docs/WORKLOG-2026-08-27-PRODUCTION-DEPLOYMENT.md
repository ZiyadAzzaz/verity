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

## Authorized gcloud-proxy health continuation

The owner authorized exactly one private `/healthz` request through
`gcloud run services proxy verity`, with no IAM or deployment change, and authorized later private
Phase 7 work only on a passing health response.

Prechecks again showed a clean repository at
`344b74e25f1d434b83b2f9c0d0dc6e01e7838b46`, unchanged ready revision
`verity-00001-twb`, the approved image digest and app identity, and empty service IAM.

### Local proxy prerequisite

The first proxy launch revealed that gcloud component `cloud-run-proxy` was absent. The automatic
install/restart path did not leave a listener and initially still reported the component absent.
An explicit non-interactive install failed because the bundled Python updater requires an
interactive console. The official component was then installed interactively and verified as
`Installed`. This changed only the local Google Cloud SDK; it did not call the service, mutate a
cloud resource, or incur cloud cost.

The proxy then started successfully:

```text
http://127.0.0.1:18080 proxies to https://verity-7pauedpknq-uc.a.run.app
```

Exactly one GET was sent to `http://127.0.0.1:18080/healthz`. It returned the same Google-front-end
404 HTML and no Verity JSON. The proxy was terminated immediately. Because health did not pass,
no unauthenticated gate, IAM binding, subscription, OIDC delivery, or Phase 8 action followed.

### Correction to the previous diagnosis

The previous section treated the human token's OAuth-client audience as the confirmed cause. The
official proxy uses the active account's identity token and is Google's recommended private-test
path, yet it produced the same result. That hypothesis is therefore not sufficient and must be
treated as superseded, not as established root cause.

Additional read-only evidence:

- Google's current documentation says gcloud-generated developer ID tokens can invoke Cloud Run
  when the account has `run.routes.invoke`.
- The live `roles/owner` definition includes `run.routes.invoke`, and the project policy assigns
  that role to the active account.
- Service ingress is `all`; no annotation disables the default URL.
- Unauthenticated browser requests to the deployment URL appear in Cloud Run request logs with
  expected 403 responses, proving the URL can route to the service front end.
- The official VPC Service Controls `run.googleapis.com/HttpIngress` policy-log query returned no
  entries.
- The Policy Troubleshooter API is disabled. It was not enabled because doing so would be a new
  cloud mutation outside this diagnostic need.

The failure is now isolated to authenticated requests from the current Windows/gcloud client path,
but its exact cause is unresolved. The next bounded no-IAM diagnostic should change the HTTP client
instead of repeating `Invoke-WebRequest` or the proxy: use `curl.exe` with a fresh gcloud token
stored only in a cleaned OS-temp curl configuration so the credential never appears in process
arguments, output, Markdown, or Git.

### State and cost after the third stop

- Service, revision, digest, job configuration, secrets, and IAM remain unchanged.
- `verity-worker`, push invoker, Pub/Sub token creator, and `allUsers` remain absent.
- The request did not appear in Cloud Run request logs and did not start measured container work.
- Local SDK component installation and read-only queries have no cloud usage charge.
- Closest observed incremental cloud cost: `$0.00`.

Professional assessment: stopping remains correct. The healthy revision and logged 403 browser
traffic argue against an application or general URL outage, but private authenticated health is
still unproven. Do not assemble OIDC or expose Phase 8 until one client path returns the actual
Verity health JSON.

## Authorized direct-curl health continuation

The owner authorized exactly one direct private `/healthz` request using Windows `curl.exe`, with
a fresh gcloud identity token stored only in a securely cleaned OS-temp curl configuration. No IAM
or deployment change was authorized; remaining private Phase 7 work was conditional on health.

Preflight passed:

- `curl.exe` 8.20.0 with Schannel was available;
- local `HEAD` and `origin/main` matched
  `832d63eeb39b0471bdec10b64116b89c8d054c39` with a clean tree;
- revision, immutable digest, and app identity were unchanged; and
- service IAM remained empty.

The request targeted
`https://verity-291098081728.us-central1.run.app/healthz`. The token never appeared in the command
text, process arguments, output, Markdown, or Git: it was written as an Authorization header inside
a random OS-temp curl config, cleared from memory variables, and the exact file was removed in a
`finally` block before reporting.

Observed result:

```json
{
  "curlExit": 0,
  "httpStatus": 404,
  "verityJson": false,
  "bodyKind": "google-front-end-html",
  "tempConfigRemoved": true
}
```

Because the response was not Verity health JSON, the conditional Phase 7 continuation remained
closed. No rejection probe, IAM binding, subscription, OIDC action, or Phase 8 action followed.

### Server-side read-only proof after curl

Cloud Run v2 Admin API returned:

- URI `https://verity-7pauedpknq-uc.a.run.app`;
- ingress `INGRESS_TRAFFIC_ALL`;
- default URI not disabled;
- invoker IAM enforcement not disabled;
- no custom audience; and
- effective operator permission `run.routes.invoke` on the exact service.

A fresh ID token inspection showed `RS256`, a Google key ID, a normal 342-character signature
segment, and `signatureRedacted=false`; the credential was never printed. The official Cloud Run
404 checks for internal ingress, disabled default URI, VPC Service Controls, missing invoke
permission, and redacted signature are therefore not supported by the observed state. The exact
cause remains unresolved.

### Next bounded diagnostic

Do not repeat another Windows request or mutate IAM speculatively. The next useful discriminator is
one request from Google Cloud Shell, which changes both client network and credential execution
environment while preserving the private service and its IAM. The owner should run:

```bash
gcloud config set project verity-506800
gcloud run services proxy verity --region=us-central1 --port=8080 >/tmp/verity-proxy.log 2>&1 &
proxy_pid=$!
trap 'kill "$proxy_pid" 2>/dev/null || true' EXIT
sleep 5
curl -i --max-time 120 http://127.0.0.1:8080/healthz
```

Send back only the HTTP status and body/error; never send a token or credential file. A healthy
Verity JSON response permits resuming the remaining private Phase 7 gates under the prior owner
authorization. Another front-end 404 would justify escalation to Google Cloud support/service
health rather than more client retries or IAM changes.

Incremental cloud cost remains `$0.00`: the curl request did not reach the container, and Admin API
reads/token issuance have no direct usage charge.

## Owner-run Google Cloud Shell health continuation

The owner ran the documented official proxy sequence from Google Cloud Shell in project
`verity-506800`, region `us-central1`, and returned only safe HTTP evidence. The proxy started with
PID 1172, waited five seconds, and exactly one request was sent to localhost `/healthz`.

Observed at `2026-08-27T17:31:08Z`:

```text
HTTP/1.1 404 Not Found
Content-Type: text/html; charset=UTF-8
The requested URL /healthz was not found on this server.
```

The body was the same Google-front-end error page, not Verity JSON. A final read-only Cloud Run
request-log query for `healthz` returned an empty list. This fifth result removes the local Windows
network/client environment as a sufficient explanation. It does not authorize any continuation:
push IAM, subscription, OIDC delivery, production jobs, GitHub Issues, and Phase 8 remain untouched.

The Cloud Shell proxy is a user-session process, not a cloud project resource. The owner should run
`kill "$proxy_pid"` or exit the shell so the registered EXIT trap stops it. It has no direct Google
Cloud usage charge.

### Recommended final private-health discriminator

Google's
[IAM service-account authentication documentation](https://cloud.google.com/iam/docs/service-account-permissions)
provides a narrower role than Service Account Token Creator:
`roles/iam.serviceAccountOpenIdTokenCreator` contains only
`iam.serviceAccounts.getOpenIdToken`. The next technically distinct test should use the existing
`verity-pubsub` identity because it is already intended to become a service-level Cloud Run
Invoker during private Phase 7:

1. Grant `verity-pubsub` Run Invoker only on service `verity`.
2. Temporarily grant the operator OpenID Connect Identity Token Creator only on
   `verity-pubsub`—never at project scope.
3. Call IAM Credentials `generateIdToken` with audience equal to the canonical service URI.
4. Keep the token out of arguments/output and send exactly one `/healthz` request.
5. Remove the operator's temporary OIDC-token-creator binding in `finally` under every outcome.
6. On failure, also remove the early push Run Invoker binding and stop. On success, retain that
   already-planned push binding and continue the private Phase 7 OIDC gates.

This requires new explicit authority because it changes two resource IAM policies, even though one
binding is already planned and the other is temporary. It is preferable to project-level Token
Creator, service-account keys, making the service public, or another identical human-token retry.

Observed incremental cloud cost for the owner-run Cloud Shell check: `$0.00`. Professional
assessment: the hard stop remains valid; the final diagnostic should be audience-bound and
least-privilege, or the issue should be escalated to Google Cloud support without further retries.

## Authorized service-account OIDC health proof

The owner authorized one bounded proof using
`verity-pubsub@verity-506800.iam.gserviceaccount.com`, with two temporary/conditional IAM changes,
one token mint, at most one `/healthz` request, mandatory cleanup on failure, and no Phase 8 action.

### Read-only preconditions

- Local `main` and `origin/main` both resolved to
  `42df3872400937442d9b9b24c5b30f3780f4a053`; the worktree was clean.
- Cloud Run reported canonical URI `https://verity-7pauedpknq-uc.a.run.app` and ready revision
  `verity-00001-twb` on immutable API digest
  `sha256:6a708965b91b6eab0602d17aa7b11807675c6c22f15d47bcd7a08647077f6326`.
- The service IAM policy was empty, the push identity's resource IAM policy was empty, and
  subscription `verity-worker` was absent.

### Bounded mutations and result

1. Granted `roles/run.invoker` to the push identity only on Cloud Run service `verity`.
2. Granted `roles/iam.serviceAccountOpenIdTokenCreator` to
   `user:ziyadazzazdesigner@gmail.com` only on the push service account.
3. Requested one Google-signed ID token from IAM Credentials `generateIdToken`, with the canonical
   Cloud Run URI as audience and `includeEmail=true`.

The token-mint request returned HTTP `403`. No ID token was obtained, so **no `/healthz` request
was sent**. The authorized one-request allowance was therefore not consumed at the HTTP service,
and no API-health or Cloud Run routing conclusion can be drawn from this attempt. The failure was
unexpected and was not retried.

The cleanup path then ran exactly as authorized:

- removed the operator's temporary OpenID Connect Identity Token Creator binding;
- removed the push identity's early Run Invoker binding because health had not passed; and
- verified both resulting IAM policies were empty again.

No `verity-worker` subscription, Pub/Sub service-agent grant, OIDC delivery probe, wrong-audience
probe, pipeline execution, sandbox execution, GitHub Issue, public binding, deployment, or billing
configuration change followed.

### Read-only diagnosis after rollback

- IAM Service Account Credentials API is enabled.
- A post-cleanup `testIamPermissions` call reported
  `iam.serviceAccounts.getOpenIdToken` as currently granted to the operator. This means the
  temporary role may have been redundant under the operator's existing effective permissions; it
  does **not** explain why `generateIdToken` returned 403.
- Both raw and URL-encoded service-account resource forms resolved to the same push identity.
- The available audit-log query returned no `GenerateIdToken` entry; this method is a Data Access
  event, so absence from the current logs is not proof that the request did not occur.

The exact 403 cause remains unresolved. Permission propagation is one possible explanation, but it
was not proven and must not be reported as fact. A new token mint would be a retry after an
unexpected security-gate failure and therefore requires fresh explicit authorization.

### Cost, state, and professional assessment

Observed incremental cost is `$0.00`: IAM policy changes, IAM policy reads, permission tests, and
the rejected token-mint request have no observed billable workload; no request reached Cloud Run
and no job/build was started. This stays well below both cost check-in thresholds.

The system is restored to its exact pre-attempt exposure state: the API remains private, service
Invoker IAM is empty, push-identity resource IAM is empty, `verity-worker` is absent, and Phase 8
is unauthorized. Stopping is the correct result. The safest next step is a separately authorized,
diagnostic token-mint attempt that captures the non-secret IAM Credentials error details and uses
an explicit permission precheck; it must still stop without a health retry if minting fails. If
that independently fails, escalate the evidence to Google Cloud support rather than adding broader
IAM or making the service public.

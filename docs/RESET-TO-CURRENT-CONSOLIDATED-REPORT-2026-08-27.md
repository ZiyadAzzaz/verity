# Verity — Reset-to-Current Consolidated Report

**Period covered:** resumed session after the usage-limit reset through 2026-08-27  
**Repository:** `https://github.com/ZiyadAzzaz/verity`  
**Branch:** `main`  
**Google Cloud project:** `verity-506800`  
**Region:** `us-central1`  
**Active operator:** `ziyadazzazdesigner@gmail.com`  
**Starting Git revision for this report:** `b7b954c75a7d0f2799c458123864abbd8e5267f9`  
**Production exposure:** private; Phase 8 has never been executed

## Executive summary

After the usage-limit reset, work did not resume from memory. Local Git, `origin/main`, and every
possibly partial Google Cloud resource from production Phases 0–7 were inventoried again. That
reconstruction showed that the release code and local validation were complete, but the first
production build submission had been rejected before a Cloud Build was created. No production API,
pipeline, identities, application secrets, or push subscription existed at that checkpoint.

The owner then authorized one corrected build from the exact tested release commit. That build
succeeded, both release images were resolved to immutable digests, and the new sandbox image passed
the decisive live security proof: all six sensitive APIs returned explicit 403 denials under the
zero-role sandbox identity. Least-privilege production identities, secret references, the private
API, and the private pipeline were then created successfully.

The deployment is currently stopped at the private `/healthz` gate. Five separately authorized
client paths, including Google Cloud Shell, returned a Google-front-end 404 before reaching the
container. The Cloud Run revision
itself is Ready, its startup probe passed, Uvicorn started, the route exists in the immutable image,
and Cloud Run's Admin API confirms open ingress, an enabled default URI, normal invoker IAM
enforcement, and effective `run.routes.invoke` permission for the operator. The exact authenticated
front-end failure is therefore unresolved. No speculative IAM change, blind retry, push
subscription, OIDC delivery, or public exposure followed.

The final distinct token proof has now also run. Direct IAM Credentials minting succeeded after a
60.009-second propagation wait, and the audience, push-identity email, and email-verification claim
all matched. The one request nevertheless returned the same unlogged Google-front-end 404. Both
scoped IAM bindings were removed. The token question is resolved; the Cloud Run front-end/routing
anomaly remains, and Phase 8 stays closed.

## Standing instructions preserved throughout

- Never change billing, payment, budget, quota, plan, or credit configuration.
- Actual available credit is `$450`; the project target is approximately `$25` total.
- Stop before any single action projected above `$10` or cumulative spend above `$50`.
- Report the closest observable real usage/cost after cloud actions; do not call estimates posted
  billing.
- Do not retry an unexpected cloud/security failure blindly.
- Keep the sandbox identity at zero project/resource IAM.
- Require all six sandbox API checks to return explicit 401/403; 5/6 is a failure.
- Keep production private until the owner reviews the complete Phase 7 checkpoint.
- Phase 8 is the only point that can grant `allUsers` Cloud Run Invoker and always requires separate
  explicit approval.
- The original workflow required permission before `verity-reports` Issue writes; the owner later
  explicitly broadened that authority when an Issue is genuinely needed. This did not authorize a
  production judge/demo Issue before the Phase 8/9 gates. Routine pushes to `verity/main` are
  authorized and should be performed automatically.
- Never print, commit, document, or pass `.env` credential values through command arguments.
- Every material session must update a professional Markdown work record and end with the agent's
  assessment and next steps.
- Once Phase 8 and final validation eventually pass, keep the submitted service publicly testable
  through the September 1–October 1 judging period with min instances 0.

## What the owner requested and how the work responded

| Sequence | Owner direction | Result |
|---|---|---|
| 1 | After the reset, reconstruct Git and cloud state rather than assuming the prior stopping point | Completed; local/remote Git matched and no hidden partial production deployment existed |
| 2 | Continue authorized production Phases 0–7, but stop before Phase 8 | Followed; Phases 4–6 passed and private Phase 7 resources were created, then work stopped at health |
| 3 | Correct Phase 4 using a detached worktree at tested release `1cc45ee...` and quote substitutions as one argument | Completed; build `2cb7068d-e078-4f01-99b7-ce3a96638dab` succeeded |
| 4 | Continue Phases 5–7 if clean; prepare but do not run judge simulation | Sandbox, IAM, secrets, API, and pipeline completed; judge plan created but not executed |
| 5 | Preserve public availability through judging and prevent accidental cleanup | Added to `STATE.md` and the judge plan; no teardown is planned before October 2 after publication |
| 6 | Authorize one direct authenticated health request to the deployment URL | Returned unlogged Google-front-end 404; no conditional continuation |
| 7 | Authorize one official `gcloud run services proxy` health request | Official proxy installed locally and started; the single request returned the same 404 |
| 8 | Authorize one secure direct `curl.exe` health request | Token stayed in a cleaned temp config; request again returned the same 404 |
| 9 | Produce one consolidated Markdown report through the current state | This document |
| 10 | Run the official proxy from Google Cloud Shell and return only safe HTTP evidence | Cloud Shell independently returned the same unlogged Google-front-end 404 |
| 11 | Authorize the first bounded push-service-account proof | Direct token mint returned 403 before HTTP; both scoped IAM grants were removed |
| 12 | Run Step A, then Step B only on real failure, with at least 60 seconds for propagation | Step A rejected human-account audiences; Step B waited 60.017 seconds but gcloud required unauthorized access-token permission; no HTTP request occurred and cleanup passed |
| 13 | Try direct `generateIdToken` with the narrow role after a 60-second propagation wait | Mint passed, claims matched, one health request returned unlogged Google-front-end 404, and both grants were removed |
| 14 | Explicitly verify latest revision readiness and traffic before accepting a routing anomaly | `verity-00001-twb` and all container/service conditions are True; it is latest-ready and receives 100% traffic |
| 15 | Isolate project/region behavior from the existing `verity` service with Google's disposable sample | Private sample returned and logged authenticated HTTP 200; temporary IAM was removed and the service was deleted |

### 2026-08-28 combined-attempt update

The current Cloud Run `status.url` is `https://verity-7pauedpknq-uc.a.run.app`. It differs from the
earlier deployment-returned regional URL and matches the canonical v2 Admin API URI. Step A failed
with `Invalid account type for --audiences. Requires valid service account.` Step B then applied
only the approved service Run Invoker and resource-level OpenID-token-creator bindings, waited
60.017 seconds, and made one mint attempt. That gcloud impersonation path failed because
`iam.serviceAccounts.getAccessToken` was not granted. No token and no HTTP request resulted.

Both bindings were removed and read back as empty. `verity-worker` remains absent,
`verity-pipeline` has no executions, observed incremental cost is `$0.00`, and Phase 8 remains
closed. Full evidence and the professional recommendation are in
[WORKLOG-2026-08-28-PRIVATE-OIDC-HEALTH-PROOF.md](WORKLOG-2026-08-28-PRIVATE-OIDC-HEALTH-PROOF.md).

The final direct-API combination was then authorized. After the same two narrow grants and a
60.009-second wait, IAM Credentials returned HTTP 200. Local checks confirmed exact audience,
service-account email, and `email_verified=true`. Exactly one canonical `/healthz` request returned
Google-front-end 404 HTML at `2026-08-28T02:20:33Z` and did not appear in the revision's recent
request logs. Both grants were removed and verified empty; observed cost remained `$0.00`. This
diagnostic line is now exhausted.

A final read-only readiness precondition check then confirmed `verity-00001-twb` is the only,
latest-created, and latest-ready revision. Revision `Ready`, `Active`, `ContainerHealthy`,
`ContainerReady`, and `ResourcesAvailable` are all `True`; service `Ready`,
`ConfigurationsReady`, and `RoutesReady` are also `True`. Exactly 100% of traffic targets that
revision. The startup probe passed on declared port 8080, so failed startup or traffic
misallocation does not explain the unlogged 404. Incremental observed cost was `$0.00`.

The decisive project-vs-service test then deployed Google's known-good private sample as
`verity-diagnostic-test` in the same project and region. Direct ID-token minting passed, its claims
matched, and the one authenticated request returned HTTP 200. Cloud Run logged the request against
revision `verity-diagnostic-test-00001-2br` with 5.156796ms latency. Both temporary grants were
removed and the service was deleted immediately. The problem is therefore specific to the
existing `verity` service path, not general project/region/private-auth routing. Recreating
`verity` from its pinned image is the pragmatic next action but requires a new destructive-action
approval.

## Starting state reconstructed after the reset

### Git

- Local `main` and live `origin/main` were reconciled rather than inferred.
- The tested deployment release was
  `1cc45ee04507ab93f18d093b89e6df0fed8c4c43`.
- The first rejected-build evidence had already advanced documentation commits beyond the release,
  so the release could not safely be rebuilt from the current working directory while labeled with
  the older tag.
- The correct solution was an exact detached worktree from `1cc45ee...` under the OS temp root.

### Cloud

Observed before the corrected production build:

- Firestore `(default)`: Standard Native mode in `us-central1`.
- Pub/Sub topic: `verification-jobs`.
- Existing no-role identity: `verity-sandbox@verity-506800.iam.gserviceaccount.com`.
- Existing sandbox job: `verity-sandbox`, retries 0.
- Existing proof: six API denials under the sandbox identity.
- Artifact Registry repository: `verity`.
- Required APIs, including Cloud Trace: enabled.
- Production API service: absent.
- Production pipeline job: absent.
- App and push identities: absent.
- Production secrets: absent.
- Push subscription `verity-worker`: absent.
- `allUsers` Cloud Run binding: absent.

This proved the interrupted session had not partially crossed into production.

## Local release work already completed and reconfirmed

The resumed release inherited and verified these important corrections:

- `verity/worker.py` includes `if __name__ == "__main__": main()`.
- The regression test proves the supplied job ID reaches `_run(job_id)`; it does not merely prove a
  zero exit code.
- The installed package exposes both production console entry points.
- Agents CLI 1.4.0 was installed in the dedicated `agent-dev` environment and `pip check` passed.
- Agents CLI is always invoked from a fresh OS-temp directory so its automatic `.env` discovery
  cannot propagate plaintext repository secrets into Cloud Run.
- Docker builds install the package and entry points rather than running source incidentally.
- Compute/Firestore stay in `us-central1`; Vertex model traffic uses `global`, where the configured
  model availability smoke passed.
- Pub/Sub OIDC verification is implemented; URL secrets are not used.
- The pipeline and sandbox infrastructure retry counts are 0.
- The main deploy script contains no `allUsers` mutation. Public exposure exists only in the
  guarded Phase 8 script.
- Parser and Debug use real typed Google ADK agents for model reasoning. Environment and Reporter
  remain deterministic Python intentionally because those steps execute/measure and compare/store
  evidence rather than requiring model reasoning.

Final local release gates before cloud execution:

- Ruff check: passed.
- Ruff format: 117 files correctly formatted.
- Strict mypy: 32 source files, no issues.
- Pytest: 281 passed, 3 emulator-only skips, 2 dependency warnings.
- Docker escape validation: all eight checks passed.
- Image imports, metadata, and console entry points: passed.
- `.env`, credentials, databases, and Git state: excluded from build contexts.
- Git diff and source-context secret checks: passed.

## Production execution chronology

### Corrected Phase 4 — passed

The exact temporary worktree was created at the tested release and the substitutions flag was
passed as one quoted argument.

- Build ID: `2cb7068d-e078-4f01-99b7-ce3a96638dab`
- Status: `SUCCESS`
- Duration: `2m25s`
- Source revision: `1cc45ee04507ab93f18d093b89e6df0fed8c4c43`
- API digest:
  `sha256:6a708965b91b6eab0602d17aa7b11807675c6c22f15d47bcd7a08647077f6326`
- Sandbox digest:
  `sha256:eee3ffa087db242d6ea2d688853c53b172f3b427861f999f0912ee9b37b75afc`

After evidence capture, only the exact clean temporary worktree was removed. The source commit was
verified still present.

### Phase 5 — live sandbox proof passed

The new sandbox digest was deployed with:

- identity `verity-sandbox@verity-506800.iam.gserviceaccount.com`;
- 2 vCPU and 4 GiB;
- retries 0;
- no environment variables or secrets;
- no volumes, mounts, network attachment, or project IAM.

Execution `verity-sandbox-7qgm6` returned:

| Sensitive operation | Status |
|---|---:|
| Firestore write | 403 |
| Secret Manager read | 403 |
| Pub/Sub publish | 403 |
| Cloud Run execution | 403 |
| Vertex AI listing | 403 |
| Cloud Storage listing | 403 |

Validator result: `passed: true`. Post-run checks again found zero project roles for the sandbox
identity. The app identity was later granted only resource-level
`roles/run.jobsExecutorWithOverrides` on the sandbox job; that grant does not give the sandbox
identity access.

### Phase 6 — least-privilege identities and secrets passed

Created:

- `verity-app@verity-506800.iam.gserviceaccount.com`;
- `verity-pubsub@verity-506800.iam.gserviceaccount.com`;
- `verity-api-key`, version 1; and
- `verity-github-token`, version 1.

Exact app project roles:

- `roles/aiplatform.user`;
- `roles/cloudtrace.agent`;
- `roles/datastore.user`;
- `roles/logging.logWriter`;
- `roles/logging.viewer`; and
- `roles/pubsub.publisher`.

The app identity has Secret Manager accessor only on the two named application secrets. No secret
value appeared in arguments, output, Git, Markdown, or build context; each value moved through a
separate UTF-8 OS-temp file removed in `finally`.

The push and sandbox identities still have no project role.

### Phase 7 — private resources created, checkpoint not passed

Private API:

- Service: `verity`.
- Revision: `verity-00001-twb`, Ready.
- Image: exact API digest above.
- Identity: `verity-app@verity-506800.iam.gserviceaccount.com`.
- Resources: 1 vCPU, 2 GiB, concurrency 4.
- Scaling: min 0, max 2.
- Secret references: named Secret Manager versions, not plaintext.
- Vertex location: `global`.
- Compute/Firestore location: `us-central1`.
- Service IAM: empty.
- `allUsers`: absent.

Private pipeline:

- Job: `verity-pipeline`, Ready.
- Image: same immutable API digest.
- Identity: `verity-app@verity-506800.iam.gserviceaccount.com`.
- Command: `python`.
- Args: `-m`, `verity.worker`, `placeholder`.
- Runtime override contract: resource-level app execution with overrides.
- Resources: 1 vCPU, 2 GiB.
- Timeout: 3600 seconds.
- Retries: 0.
- No production pipeline execution has been started.

## Private health investigation

### What is known healthy

- Cloud Run reports revision `verity-00001-twb` Ready.
- Image import completed successfully.
- Container startup TCP probe passed.
- Uvicorn logged application startup complete on port 8080.
- The immutable code defines `GET /healthz`.
- Local tests exercise `/healthz` successfully.
- Unauthenticated browser requests reach the Cloud Run service and produce logged 403 responses.

### Five bounded attempts

| Attempt | Authorized client path | Result | Container request log |
|---|---|---|---|
| 1 | `Invoke-WebRequest` to Cloud Run `status.url` | Google-front-end 404 | absent |
| 2 | `Invoke-WebRequest` to deployment-returned URL | Google-front-end 404 | absent |
| 3 | Official `gcloud run services proxy`, one localhost request | Google-front-end 404 | absent |
| 4 | `curl.exe`, token held only in cleaned OS-temp config | Google-front-end 404 | absent |
| 5 | Owner-run official proxy from Google Cloud Shell | Google-front-end 404 | absent |

Each authorization permitted later Phase 7 work only if real healthy Verity JSON was returned.
That condition never became true, so each attempt stopped without a downstream mutation.

### Hypotheses tested honestly

The initial direct-token audience looked suspicious because the human token audience was the
gcloud OAuth client. That was recorded as a likely cause, then explicitly retracted when Google's
official proxy produced the same 404.

Read-only evidence now confirms:

- Cloud Run v2 URI is the documented service URI.
- Ingress is `INGRESS_TRAFFIC_ALL`.
- Default URI is not disabled.
- Invoker IAM enforcement is not disabled.
- No custom audience is configured.
- The operator has effective `run.routes.invoke` on the exact service.
- The operator's `roles/owner` definition includes that permission.
- The VPC Service Controls `HttpIngress` policy-log query returned no denial.
- Fresh identity tokens use RS256, include a Google key ID, and have a normal non-redacted
  signature.
- The Policy Troubleshooter API is disabled and was not enabled merely to continue diagnosis.

The exact reason authenticated requests from the current local path receive an unlogged 404 is not
yet proven. It must not be mislabeled as an application failure, permission failure, or Cloud Run
incident without evidence.

## Defects and security findings discovered during this period

| Finding | Severity | Resolution/status |
|---|---|---|
| PowerShell split an unquoted Cloud Build substitutions value | High deployment-integrity risk | Corrected with one quoted argument and detached tested source; build passed |
| Building from current documentation HEAD while labeling an older tested release would break source integrity | High | Detached worktree bound build bytes to `1cc45ee...`; source commit preserved |
| Missing worker module main guard could produce silent no-op success | Critical runtime correctness | Fixed and regression-tested before release |
| Agents CLI discovers and copies project `.env` values | Critical secret-handling risk | Always run from isolated OS-temp directory with explicit secret references |
| Agents CLI injects `--no-cpu-throttling` | Low cost-efficiency concern | Recorded; min instances 0 still permits scale-to-zero; revisit after health proof |
| Local wrapper used unsupported `New-Item -LiteralPath` on this PowerShell | Local tooling defect | No cloud request occurred; corrected to `-Path` after local-only preflight |
| Direct, proxy, curl, and Cloud Shell health paths return unlogged GFE 404 | Current P0 blocker | Human-account path exhausted; next proof requires a separately authorized audience-bound service-account token |

No secret was exposed and no security boundary was weakened to recover from any stop.

## Cost record

These figures distinguish measured usage/list-price calculations from delayed posted billing:

| Action | Closest observed cost evidence |
|---|---:|
| Corrected Cloud Build, 145.81 seconds | approximately `$0.014581` raw before monthly allowance |
| Sandbox execution, 74.56 seconds at 2 vCPU/4 GiB | approximately `$0.003281` raw before free tier |
| API rollout observed through Cloud Monitoring, 227.612 billable instance-seconds | approximately `$0.005007` raw |
| IAM, service accounts, secret containers/versions, job metadata deployments | `$0.00` direct usage charge observed |
| Failed front-end health requests and read-only Admin API queries | `$0.00` incremental container usage observed |
| Five registry images, conservative no-dedup storage above 0.5 GiB | approximately `$0.02882/month` run-rate ceiling |

Combined raw measured/list-price compute for the production continuation is approximately
`$0.02287`, plus the small storage run-rate. This is far below the approximately `$25` target,
`$10` single-action gate, `$50` cumulative review gate, and actual `$450` available credit.

No billing/payment/budget/quota/plan setting was modified.

## Git history produced during the resumed work

| Commit | Purpose |
|---|---|
| `0782a44` | Harden private production release path |
| `1cc45ee` | Separate global Vertex model location from regional compute location |
| `78bf87a` | Record the initially rejected production build submission |
| `8c1abcb` | Preserve tested release source integrity for corrected build |
| `d2df9c0` | Record successful Phases 4–6 and private Phase 7 health stop; add judge plan |
| `344b74e` | Record direct private-health authentication diagnosis |
| `832d63e` | Record official proxy health stop and correct the earlier hypothesis |
| `b7b954c` | Record secure direct-curl health stop and Cloud Shell handoff |
| `b95dd63` | Add the consolidated reset-to-current report |

At the start of this report, the worktree was clean and local `HEAD` matched `origin/main` at
`b7b954c75a7d0f2799c458123864abbd8e5267f9`.

## Exact current state

| Area | Current state |
|---|---|
| Firestore | `(default)`, Standard Native, `us-central1` |
| Topic | `verification-jobs` exists |
| Sandbox job | Exists on immutable sandbox digest; retries 0; latest proof 6/6 denied |
| Sandbox IAM | Zero project roles; no sensitive resource grants |
| API service | `verity`, revision Ready, private, min 0/max 2 |
| Pipeline job | `verity-pipeline`, Ready, never executed in production |
| App IAM | Exact six project roles plus resource-level secret/job bindings |
| Push identity | Exists; no project or resource IAM yet |
| Production secrets | Two named secrets, version 1, app-only access |
| Service invokers | None on the service policy |
| `verity-worker` subscription | Absent |
| Pub/Sub service-agent token creator | Not granted on push identity |
| OIDC valid-delivery proof | Not run |
| OIDC wrong-audience rejection | Not run |
| Public `allUsers` | Absent; Phase 8 closed |
| Production verification jobs | None submitted |
| Production GitHub Issues | None created by the deployed service |
| Judge key | Planned only; not created or deployed |
| Teardown | Not performed and not authorized |

## What remains before Phase 8

1. Review the final successful direct mint plus unlogged 404. Token generation and claim accuracy
   are now proven; the remaining blocker is at the Cloud Run front-end/service-routing boundary.
   Decide whether to perform a browser/Console check or escalate to Google Cloud support. Do not
   retry, broaden IAM, redeploy, or expose publicly without a new owner decision.

2. If—and only if—the response is actual healthy Verity JSON, resume the previously authorized
   private Phase 7 sequence:

   - prove direct unauthenticated requests are rejected;
   - grant only the push identity Run Invoker on `verity`;
   - grant only the Google-managed Pub/Sub service agent token-creator on the push identity;
   - create `verity-worker` with the exact endpoint, identity, audience, 600-second ack deadline,
     and one-day retention;
   - prove valid OIDC acceptance on the non-executing probe endpoint;
   - prove wrong-audience rejection;
   - confirm no pipeline/sandbox execution was launched by the OIDC probe;
   - capture exact IAM, digests, retries, logs, and cost; and
   - stop for owner review.

3. Phase 8 remains a separate explicit approval. Do not run
   `scripts/publish_production.ps1 -OwnerApprovedPhase8` before that approval.

4. After Phase 8, execute the prepared
   [judge-simulation plan](JUDGE-SIMULATION-TEST-PLAN.md): two fresh public claims, terminal verdicts,
   real Issue links, one live dedup proof, and all Devpost links.

## Owner input needed now

Review the final successful-token/unlogged-404 evidence and choose the next direction. No
credential needs to be sent in chat. No additional diagnostic or Phase 8 action is currently
authorized.

## Professional assessment

The resumed work achieved the highest-risk objectives without weakening controls: the tested
release was built immutably, the no-role sandbox boundary passed all six live denial checks, secrets
stayed in Secret Manager, least-privilege identities were created, and the API/pipeline are deployed
privately with retries disabled. The team also caught and corrected serious worker-entry-point,
source-integrity, and CLI plaintext-secret risks before public exposure.

The current blocker is narrow but real: private authenticated delivery has not produced application
health evidence despite a healthy container and correct server-side configuration. Windows, Cloud
Shell, and a correctly minted audience-bound service-account token all produced unlogged front-end
404 responses. The scoped grants were removed, and this diagnostic line is exhausted. The owner
should now choose a parallel Console/browser inspection or Google Cloud support escalation rather
than another retry, broader IAM, or premature public exposure.

## Related sources of truth

- [Current state](STATE.md)
- [Detailed production work record](WORKLOG-2026-08-27-PRODUCTION-DEPLOYMENT.md)
- [Production deployment plan](POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md)
- [Passing sandbox proof](CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md)
- [Judge-simulation plan](JUDGE-SIMULATION-TEST-PLAN.md)
- [Cloud Console inspection guide](GOOGLE-CLOUD-CONSOLE-INSPECTION.md)
- [Cloud live-safety rules](CLOUD-LIVE-SAFETY.md)

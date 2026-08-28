# Verity — Current State and Next Steps

**Audited:** 2026-08-24; scoped cloud-security and emulator validation updated 2026-08-25

**Audit implementation:** `696cdfd3989633e80e7fd0b98c6e21794cabcd1d`

**Security report:** `01b73df9b1957b0c8f9364424a0bbf3fa612a89a`

**Code:** https://github.com/ZiyadAzzaz/verity (public)

**Verdicts:** https://github.com/ZiyadAzzaz/verity-reports (public)

**Live cloud project:** `verity-506800`; $450 promotional credit available; target total spend
approximately $25; hard review gates are documented in
[CLOUD-LIVE-SAFETY.md](CLOUD-LIVE-SAFETY.md).

**Latest work record:**
[WORKLOG-2026-08-28-UVICORN-ISOLATION.md](WORKLOG-2026-08-28-UVICORN-ISOLATION.md).
Every future material session follows [WORK-RECORD-STANDARD.md](WORK-RECORD-STANDARD.md).

**Reset-to-current consolidated report:**
[RESET-TO-CURRENT-CONSOLIDATED-REPORT-2026-08-27.md](RESET-TO-CURRENT-CONSOLIDATED-REPORT-2026-08-27.md)
summarizes every owner authorization, action, result, cost, Git checkpoint, and the exact current
state from the resumed session through the latest private-health stop.

**Google Cloud visual inspection:**
[GOOGLE-CLOUD-CONSOLE-INSPECTION.md](GOOGLE-CLOUD-CONSOLE-INSPECTION.md) gives the owner exact
read-only Console steps, expected values, prohibited controls, and a response template.

This is the current source of truth. Older status, review, handover, and completion documents
are historical snapshots and retain their original evidence, dates, and test counts.

**CI status:** the failed run on `6b8d337` was caused solely by a transient Docker Hub timeout
resolving `python:3.11.15-slim`. Its failed job was rerun without changing or weakening the
workflow; every lint, format, type, unit, Docker build, Docker test, and isolation gate passed in
2m26s. Current main also has an independent successful CI run. See
[WORKLOG-2026-08-28-CI-RECOVERY.md](WORKLOG-2026-08-28-CI-RECOVERY.md).

## Bottom line

The local product is a credible, working MVP with unusually strong evidence around its Docker
boundary, bounded debug loop, durable cache, and honest empty-result behavior. The audited cloud
credential flaw now has a scoped implementation: the sandbox receives bounded request arguments,
returns a bounded platform-collected log envelope, imports no cloud client, and is assigned a
service account with zero project or discovered resource-level IAM bindings. Pub/Sub now validates
Google OIDC instead of a
URL secret.

The live least-privilege gate is now **passed**. After creating the authorized free-tier Standard
Native `(default)` Firestore database in `us-central1`, a full precondition sweep passed and the
fourth no-role sandbox execution returned six explicit 403 denials in validator-produced JSON.
The proof is bound to the exact execution, identity, source revision, and immutable image digest.
The immutable production API and pipeline are now deployed **privately**, but the Phase 7 health
gate is not passed: the first authenticated request to the service-reported `status.url` returned
a Google-front-end 404 and did not reach the container. The hard-stop rule prevented an automatic
request to the alternate Cloud Run URL. Push IAM, the `verity-worker` subscription, OIDC delivery
proof, and public `allUsers` access remain absent. See
[CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md](CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md) and
[POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md](POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md).

The Firestore and Pub/Sub adapters have now also passed Google's official local emulators with no
account or credentials. This reduces adapter and transaction risk but is not live-cloud evidence.
See [EMULATOR-VALIDATION-2026-08-25.md](EMULATOR-VALIDATION-2026-08-25.md).

## Verified evidence

| Area | Current evidence |
|---|---|
| Public repositories | `verity` and `verity-reports` both return public GitHub metadata |
| Repository base before this validation | local `main` and public `origin/main` resolved to security commit `7aa52ce` |
| Python environment | `agent-dev`, Python 3.11.15; exact locked package set; `pip check` clean |
| Static gates | Ruff check, Ruff format check, and strict mypy pass after the audit changes |
| Full non-Docker selection | **264 passed, 3 emulator tests skipped, 9 Docker tests deselected**, 2 upstream deprecation warnings |
| Full Docker-inclusive suite | **273 passed, 3 emulator tests skipped**, 2 upstream deprecation warnings |
| Total unique tests with emulators | **276 passed**: 273 standard/Docker tests plus 3 official-emulator tests |
| Real isolation probe | 8/8 attacks blocked: host files, rootfs write, eval network, privilege, Docker socket, PID cap; install network and workspace write behave as designed |
| Immutable revision smoke | a real public GitHub commit was fetched by full SHA, checked out detached in Docker, evaluated, and recorded without drift |
| Local HTTP smoke | `/`, `/architecture`, `/healthz`, submission, cache lookup, verdict, and trace paths returned correctly against a writable copy of the demo DB |
| Demo cache | Five jobs, four historical outcomes, instant and zero model calls; read-only inspection creates no WAL/SHM sidecars |
| GitHub artifacts | Issues #1–#5 exist; #1, #3, #4, and #5 are real verdict artifacts, while #2 is explicitly a synthetic wiring probe |
| Runtime cleanup | no verification containers left running after the gates |
| Cloud-adapter emulators | **3 passed** against official Firestore 1.22.0 and Pub/Sub 0.8.35 emulators; exact containers removed afterward |

The in-app Browser had no attached tab/surface during this audit. HTTP behavior and generated
assets were checked, but a fresh interactive click/render pass is still a human-assisted step.

## Live catalogue: what actually happened

The 2026-08-25 scoped-fix regression produced new evidence:

- Whisper completed in a fresh database as `could_not_verify`, asserted no observed number, used
  exactly three bounded attempts, and recorded the malformed/unsafe second proposal as
  `attempt_rejected`. Its trace has 14 events, and dedup returned immediately without execution.
- A final fresh eight-source run completed the ResNet source as `could_not_verify`, with no
  observed number, three attempts, and 13 trace events.
- Source 2 then hit the configured AI Studio account's explicit `gemini-3.5-flash` free-tier limit
  of 20 requests. The run was stopped during parsing so later sources would not be mislabeled as
  claim failures. The full eight-source rerun therefore remains incomplete.

Exact scoped-fix evidence is in
[SCOPED-SECURITY-VALIDATION-2026-08-25.md](SCOPED-SECURITY-VALIDATION-2026-08-25.md).

The following is the preserved historical pre-fix catalogue baseline.

The preserved `E:\wsl\verity-gate4.db` contains 11 job records. Seven catalogue sources have
completed verdicts:

| Source | Stored outcome |
|---|---|
| ResNet paper | `could_not_verify` |
| Attention paper | `could_not_verify` |
| DETR | `could_not_verify` |
| YOLOv5 v7 | `could_not_verify` |
| Requests | `verified` with observed value 200 |
| NVIDIA H100 page | `could_not_verify` |
| Gemini 3.5 Flash page | `could_not_verify` |

The eighth historical catalogue source, Whisper, is `failed` with no verdict because Gemini proposed the
unsafe path `../venv/pip.conf`; Pydantic correctly rejected it, but that historical run predates
the pipeline behavior that counts a rejected proposal as one bounded attempt. Therefore the
old claim “full 8-source gate completed” was false. The rejection path is covered by tests, but
the rejection path has now been rerun successfully for Whisper; only the complete eight-source
rerun remains blocked by external quota.

## Verdict taxonomy

| Verdict | Meaning |
|---|---|
| `verified` | An attributable value was observed within the explicit 2% tolerance |
| `contradicted` | An attributable, comparable value was observed outside tolerance |
| `inconclusive` | The process succeeded but emitted no attributable metric |
| `conditions_not_comparable` | A value was observed, but material hardware/runtime equivalence was not established |
| `could_not_verify` | The evaluation was genuinely attempted and did not complete after the bounded loop |
| `no_verifiable_claim_found` | The source asserted no headline result; nothing was executed |
| `environment_incompatible` | The offline evaluation sandbox could not host the repository; the claim was never tested |

Timing, throughput, resource, power, and cost metrics now use
`conditions_not_comparable`. The historical tqdm Issue #5 remains an immutable record of the
older code and should not be cited as a sound contradiction.

## Improvements made in this audit

- Time-boxed model-provided regular expressions in a disposable child process; require exactly
  one numeric capture, finite output, and the final occurrence.
- Prevent a number printed by a failed process from becoming `verdict.actual_value`.
- Added `conditions_not_comparable` for hardware/runtime-sensitive scalar comparisons.
- Removed overly broad `ssl` and `read timed out` environment-incompatibility markers.
- Revalidate parser and GitHub publisher URLs rather than bypassing typed URL validation with
  `model_copy`.
- Roll back a patch bundle and replacement command when patch application fails, so one bad
  exact-match edit cannot poison later attempts; do not report an unapplied patch as applied.
- Apply artifact-filing failure policy consistently to both normal and short-circuit verdicts.
- Treat sandbox/control-plane infrastructure failures as failed jobs without spending three
  Debug Agent calls or producing a claim verdict.
- Fix cached and deep-linked frontend polling; display condition-sensitive values as
  “Observed,” not “Reproduced.”
- Open shipped/reference SQLite databases in immutable read-only mode, preventing inspection
  from mutating WAL/SHM sidecars.
- Neutralize GitHub mentions and escape/dynamically fence all untrusted Markdown fields in
  filed Issues.
- Make `verity.agents` imports lazy so the minimal sandbox image does not import the ADK/HTTP
  stack; make the sandbox handoff explicitly Firestore rather than accidental SQLite.
- Configure telemetry in the standalone pipeline worker and convert Cloud Run operation errors
  into typed infrastructure results.
- Resolve the first repository commit, persist it on the job, fetch exact SHAs detached on every
  repair attempt, and turn revision drift into an infrastructure failure.
- Leave publication failures queued and republish an existing queued job on repeat submission;
  atomically complete the Firestore job and claim-memory record.
- Added the Apache-2.0 `LICENSE` file declared by the package metadata.
- Made the cloud production profile and deployment script fail closed.
- Added digest-pinned official Firestore/Pub/Sub emulators and verified real transaction,
  serialization, publish, delivery, acknowledgement, and duplicate-claim behavior.

## Release blockers

### P0 — live proof of the scoped cloud trust boundary

The Firestore-capable sandbox design has been replaced locally. The trusted pipeline now passes
bounded public request arguments, reads a bounded result from the exact execution's Cloud Logging
records, and alone persists Firestore state. The sandbox image contains no Google Cloud client or
application secret. The deployment blueprint removes the legacy Firestore role, fails on any
remaining project binding, searches project-scoped resource policies with Cloud Asset Inventory,
clears ambient job capabilities, and runs a metadata-token abuse probe before deploying the
privileged app.

Required evidence before removing either production guard:

1. Run `scripts/deploy_sandbox_probe.ps1` to deploy only the sandbox job under
   `verity-sandbox@PROJECT.iam.gserviceaccount.com`.
2. Confirm its job definition contains exactly one container with the expected image, default
   entrypoint, and identity, and no declared environment, secret, volume, or VPC attachment.
3. Obtain its metadata token and require explicit denial of a Firestore write, Secret Manager
   read, Pub/Sub publish, Cloud Run execution, Vertex AI listing, and Cloud Storage listing.
4. Review inherited IAM and ensure the project exposes no sensitive private network to the task.
5. Preserve the honest residual-risk statement: no-role IAM closes credential blast radius but
   does not provide offline evaluation, malicious-code attestation, or kernel-exploit immunity.

### P0 — private production deployment stopped at health gate

The corrected build `2cb7068d-e078-4f01-99b7-ce3a96638dab` succeeded from detached release
`1cc45ee04507ab93f18d093b89e6df0fed8c4c43`. Its immutable API and sandbox images are deployed;
the new sandbox execution `verity-sandbox-7qgm6` proved all six sensitive APIs denied with 403.
The app identity, push identity, two production secrets, private API revision
`verity-00001-twb`, and private `verity-pipeline` job now exist with the reviewed least-privilege
configuration. The service has no invoker binding; the push identity has no binding; and
subscription `verity-worker` does not exist.

Five separately authorized private `/healthz` requests—one to `status.url`, one to the
deployment-returned URL, one through the local official `gcloud run services proxy`, one direct
`curl.exe` request with its token confined to a cleaned temp config, and one owner-run proxy from
Google Cloud Shell—returned Google-front-end 404 pages and produced no Cloud Run request log. The
proxy, curl, and Cloud Shell results disprove the
earlier conclusion that the direct client's token audience alone was the confirmed cause. The
operator's existing Owner role includes `run.routes.invoke`, ingress is `all`, unauthenticated
browser requests reach Cloud Run and return logged 403, the default URL is active, and the official
VPC Service Controls policy-log query returned no denial. The revision remains healthy; the
authenticated local-client/environment explanation. Cloud Run's v2 Admin API directly
confirmed effective `run.routes.invoke`, `INGRESS_TRAFFIC_ALL`, enabled default URI, normal invoker
IAM enforcement, and no custom audience. The fresh ID token was fully Google-signed rather than
signature-redacted. No IAM was changed to work around the failure. Public `allUsers` access
remains a separate Phase 8 owner checkpoint.

### P1 — evidence comparability

The Reporter compares most non-timing metrics numerically but does not persist observed dataset,
checkpoint, dependency lock, hardware, precision, or protocol provenance. A scalar alone cannot
prove those conditions matched. The new timing status prevents the clearest false contradiction;
general provenance enforcement is still required.

### P1 — durability and scale

- A worker dying after `claim_job` can leave a job permanently in progress; there is no lease,
  heartbeat, recovery sweep, or transactional outbox.
- Full outputs/diagnostic files can exceed Firestore's 1 MiB document limit.
- Repository repair attempts are pinned to the first resolved commit. Fetched source bytes and the
  runner image are not pinned, and URL-cache entries do not expire, so a later submission can still
  evaluate different inputs under the same claim key.
- Model transport retries nest inside the three repair attempts without a per-job token budget.

### P2 — remaining local boundary limitations

- Install-time Python build code has bridge networking and can probe reachable networks.
- URL validation occurs before the HTTP client's independent DNS resolution, leaving a DNS
  rebinding time-of-check/time-of-use gap.
- The local `asyncio.Queue` is intentionally not crash-durable.
- The declarative four-agent graph in `app/agent.py` has no tools and is not the durable runtime;
  actual Parser/Debug model calls do use typed ADK agents through `verity.llm`.

## Next steps, in order

**Latest Phase 7 checkpoint:** the 2026-08-28 combined attempt sent no HTTP request. Step A's
human-account mint rejected audience selection. Step B applied both authorized scoped IAM grants,
waited 60.017 seconds, then stopped because gcloud impersonation required the broader, unauthorized
`iam.serviceAccounts.getAccessToken` permission. Both grants were removed and verified absent;
`verity-worker` remains absent, pipeline executions remain zero, and Phase 8 is unauthorized. See
[the latest work record](WORKLOG-2026-08-28-PRIVATE-OIDC-HEALTH-PROOF.md).

**Final diagnostic update:** the direct IAM Credentials call was then authorized with the same
narrow grants and a 60.009-second wait. It minted successfully (HTTP 200); local validation proved
the exact `aud`, push-service-account `email`, and `email_verified=true`. Exactly one `/healthz`
request still returned unlogged Google-front-end 404 HTML at `2026-08-28T02:20:33Z`. Both grants
were removed and verified absent. This diagnostic line is exhausted; no further retry, IAM
broadening, deployment, or Phase 8 action is authorized.

**Revision readiness precondition cleared:** read-only revision and service describes show
`verity-00001-twb` has `Ready=True`, `Active=True`, `ContainerHealthy=True`, and
`ContainerReady=True`; the service has `Ready=True`, `ConfigurationsReady=True`, and
`RoutesReady=True`. It is both latest-created and latest-ready, and receives exactly 100% of
traffic. There is no revision failure, port/startup-probe failure, split, zero allocation, or older
traffic target to explain the unlogged 404.

**Project-vs-service isolation is decisive:** a new private Google sample service in the same
project/region accepted the same direct-minted, audience-matched `verity-pubsub` token and returned
HTTP 200. Its revision log recorded the exact request with 5.16ms latency. The temporary service
and both grants were then removed and verified absent/empty. The failure is scoped to service
`verity`, not project, region, account, private Cloud Run, IAM Credentials, or local network.
Recreating `verity` from its pinned digest is the pragmatic next step but remains destructive and
requires explicit owner approval.

**Clean recreation and rename fallback both failed:** service `verity` was backed up, deleted, and
recreated from the exact pinned digest/configuration under a new UID. Its authenticated health
request still returned an unlogged front-end 404. Identical private fallback `verity-app` then
failed the same way. Both temporary IAM cycles were removed; all three policies are empty and
`verity-worker` remains absent. Stale service-object state and exact service name are ruled out.
The common remaining discriminator is the Verity image/configuration path, although no specific
root cause is yet proven.

**Four-test process isolation completed:** unused `verity-app` was deleted. Inside the same pinned
Verity image/configuration, `python -m http.server 8080 --bind 0.0.0.0` returned and logged HTTP
200. Direct Uvicorn, Uvicorn with lifespan off, and Uvicorn forced to asyncio+h11 each returned the
same unlogged front-end 404. Every failed override was reverted; final `verity` revision
`verity-00009-ltc` uses image defaults, is private/Ready, and both temporary IAM policies are
empty. Binding, `$PORT`, Host/CORS middleware, wrapper/shell, lifespan, and optimized Uvicorn
backends are ruled out as fixes. The remaining boundary is the ASGI/Uvicorn process in this pinned
image.

The implementation-ready schemas, trust boundaries, crash windows, and acceptance tests for these
steps are in [NEXT-IMPLEMENTATION.md](NEXT-IMPLEMENTATION.md).
The current execution evidence is in
[WORKLOG-2026-08-28-PRIVATE-OIDC-HEALTH-PROOF.md](WORKLOG-2026-08-28-PRIVATE-OIDC-HEALTH-PROOF.md).

1. Local static, unit, Docker, image, and isolation gates are complete.
2. The live no-role sandbox proof is complete: six sensitive APIs returned explicit 403 denials.
3. `VERITY_API_KEY` is present locally; Agents CLI 1.4.0, package installation, the module worker,
   and the local/Docker gates are resolved and validated.
4. Review the bounded Uvicorn isolation proof. Decide whether to authorize one new immutable
   minimal-ASGI image/build isolation plan or preserve the evidence for support. Do not continue
   Phase 7 or Phase 8.
5. If health passes, continue the still-private Phase 7 unauthenticated rejection and OIDC push
   gates, then stop with full IAM/digest/cost evidence before Phase 8.
6. After that approval, run one unseen source through the real deployed path, confirm
   Firestore/Pub/Sub/Trace/Logging evidence and an autonomously filed Issue, then run all deployed
   catalogue URLs plus dedup.
7. Add broader provenance, recovery leases/outbox, image-digest pinning, and stronger egress after
   the hackathon submission unless a live test exposes an earlier need.
8. Attach an in-app Browser tab for final interactive UI, architecture-page, and screenshot QA.

The post-Phase-8 checklist is prepared in
[JUDGE-SIMULATION-TEST-PLAN.md](JUDGE-SIMULATION-TEST-PLAN.md). The submitted service must remain
publicly testable throughout the official September 1–October 1 judging period. Keep min instances
at zero and do not include the live resources in cost cleanup or teardown before October 2 without
owner approval.

## Inputs needed from the project owner

Do not paste credentials into chat. Before public exposure:

- attach/open the in-app Browser when you want the visual interaction pass;
- inspect the posted Billing Report using the Console guide;
- review the private Phase 0–7 checkpoint and explicitly approve Phase 8;
- allow the configured AI Studio quota to reset or replace the key locally in `.env` so the final
  eight-source catalogue can run; never paste the key into chat;
- keep `gcloud` authenticated.

Describe Verity as a **locally proven MVP with a live-validated no-role cloud sandbox boundary**
until the private deployment evidence is complete. Do not describe it as public or
submission-complete until Phase 8 and the end-to-end evidence pass.

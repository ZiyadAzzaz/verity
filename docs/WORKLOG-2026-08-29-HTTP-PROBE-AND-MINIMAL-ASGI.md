# Verity — HTTP Probe and Minimal ASGI Diagnostic

**Date:** 2026-08-29
**Repository:** `https://github.com/ZiyadAzzaz/verity`
**Branch:** `main`
**Starting revision:** `c9618714c8121a34977fc0fde858989df0114ead`
**Operator:** `ziyadazzazdesigner@gmail.com`
**Google Cloud project:** `verity-506800`
**Region:** `us-central1`
**Phase 8:** not authorized and not executed

## Objective and authorization

Continue the previously blocked two-priority diagnostic:

1. enable Cloud Resource Manager, replace the production TCP startup probe with the exact
   owner-specified HTTP `/healthz` probe, and test private health if the revision became Ready;
2. if Priority 1 did not resolve health, build and deploy one minimal FastAPI/Uvicorn image with
   a static `/healthz` response; if that also failed, stop further engineering mutation and
   prepare Google Cloud Support evidence.

No public access, broader IAM, billing/payment/budget/quota/plan change, or Phase 8 action was
authorized.

## Priority 1 — HTTP startup probe

### API enablement

The owner explicitly authorized:

```powershell
gcloud services enable cloudresourcemanager.googleapis.com --project=verity-506800
```

Operation `operations/acat.p2-291098081728-a4fa428a-0476-43a3-af46-6aafae21676b` completed
successfully, and enabled-service read-back returned
`cloudresourcemanager.googleapis.com`. This changed only project API activation and did not alter
billing configuration.

### Service replacement

The prepared [cloudrun.http-probe.yaml](../cloudrun.http-probe.yaml) was applied once. It preserved
the pinned image, production identity, environment, Secret Manager references, resources,
concurrency, scaling, ingress, and traffic declaration. The intended behavioral change was only
TCP-to-HTTP startup probing:

```yaml
startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 1
  periodSeconds: 240
  timeoutSeconds: 240
```

Cloud Run created revision `verity-00010-7ft`, but it never became Ready:

```text
reason: HealthCheckContainerError
Ready: False
ContainerReady: True
ContainerHealthy: False
```

The exact platform log was:

```text
STARTUP HTTP probe failed 1 time consecutively for container "verity-api-1"
on port 8080 path "/healthz". The instance was not started.
Connection failed with status ERROR_CONNECTION_FAILED.
```

Timing evidence:

- instance-start log: `2026-08-28T22:28:30.263895Z`;
- failed-probe log: `2026-08-28T22:28:30.484983Z`;
- elapsed: approximately **0.221 seconds**.

Traffic remained 100% on the previous Ready revision `verity-00009-ltc`. Because the HTTP-probe
revision never became Ready, no authenticated health request was possible and no temporary IAM
window was opened.

## Priority 2 — one minimal FastAPI/Uvicorn image

### Source and local gate

The diagnostic image source is under [diagnostics/minimal_asgi](../diagnostics/minimal_asgi):

- `python:3.11.15-slim`;
- declared dependencies only `fastapi==0.141.1` and `uvicorn==0.52.4`;
- one static `GET /healthz` route returning
  `{"status":"ok","diagnostic":"minimal-fastapi-uvicorn"}`;
- Uvicorn bound to `0.0.0.0:${PORT}`;
- non-root UID 10001; and
- no Verity import, environment, secret, cloud client, agent, model, database, or Pub/Sub code.

Python syntax compilation passed. A local import request could not run because the host Python
environment does not have FastAPI installed; this was reported rather than treated as a pass. The
clean Cloud Build installed the two pinned requirements and supplied the executable image gate.

### One build

Cloud Build ID: `6b53a00e-a63b-4764-b28d-9f4560ed2788`

```text
status: SUCCESS
start: 2026-08-28T22:30:44.866736030Z
finish: 2026-08-28T22:31:13.556688Z
duration: approximately 29 seconds
```

Immutable image:

```text
us-central1-docker.pkg.dev/verity-506800/verity/minimal-asgi@sha256:20c31500e1c946e4296b4463890438c72cd11b558e2d37178c07492f36dd398e
```

No second diagnostic image was built.

### One deployment

The image was deployed once as private service `verity-asgi-diagnostic`, using the existing
no-role `verity-sandbox` runtime identity, 512 MiB memory, one CPU, max scale 1, and HTTP
`/healthz` startup probing. The deployment manifest is
[cloudrun.minimal-asgi.yaml](../cloudrun.minimal-asgi.yaml).

Revision `verity-asgi-diagnostic-00001-88h` imported the image but never became Ready:

```text
reason: HealthCheckContainerError
Ready: False
ContainerReady: True
ContainerHealthy: False
```

The exact platform log was:

```text
STARTUP HTTP probe failed 1 time consecutively for container "minimal-asgi-1"
on port 8080 path "/healthz". The instance was not started.
Connection failed with status ERROR_CONNECTION_FAILED.
```

Timing evidence:

- instance-start log: `2026-08-28T22:32:31.732961Z`;
- failed-probe log: `2026-08-28T22:32:31.968142Z`;
- elapsed: approximately **0.236 seconds**.

The service has no Ready revision, no traffic, and an empty IAM policy. It could not receive the
planned authenticated request, so no invoker/token-creator grant or ID token was created.

## Critical interpretation correction

The minimal image and Verity image failed at the same internal probe boundary, but this does
**not** yet prove Uvicorn/ASGI is broken on Cloud Run. Both probes used:

```text
initialDelaySeconds: omitted (Cloud Run default 0)
failureThreshold: 1
```

The first connection-refused response therefore met the entire failure threshold about 0.22
seconds after instance start. `periodSeconds: 240` controls the interval between attempts; it does
not delay the first attempt. `timeoutSeconds: 240` does not keep retrying a connection that was
immediately refused.

Google's current service documentation says the default initial delay is zero and the default
failure threshold is three. Its HTTP startup-probe service example uses a 10-second initial delay,
five failures, and a three-second period:

- https://docs.cloud.google.com/run/docs/configuring/healthchecks
- https://docs.cloud.google.com/run/docs/samples/cloudrun-healthchecks-startup-probe-http

Consequently, the owner-specified one-attempt probe configuration is too aggressive to distinguish
normal Uvicorn startup latency from a real server defect. The test accurately proves only that
neither container accepted an HTTP connection within roughly 0.23 seconds.

## Final cloud and security state

| Resource or boundary | Final state |
|---|---|
| Cloud Resource Manager API | Enabled as explicitly authorized |
| `verity` template | Pinned Verity image with HTTP `/healthz` startup probe |
| `verity` latest created | Failed `verity-00010-7ft` |
| `verity` live traffic | 100% remains on Ready `verity-00009-ltc` |
| `verity-asgi-diagnostic` | Exists privately; failed revision only; no traffic |
| Diagnostic service IAM | Empty |
| `verity` service IAM | Empty |
| Push identity resource IAM | Empty |
| Temporary authentication grants/tokens | None created in this sequence |
| `verity-worker` / Phase 7 delivery | Absent / not executed |
| `allUsers` / Phase 8 | Absent / closed |

The failed diagnostic service and immutable image were retained as support evidence because the
owner's stop rule prohibited further engineering mutations after the minimal failure.

## Cost record

| Action | Closest observed actual usage |
|---|---|
| API enablement | Successful control-plane operation; no billable workload |
| Verity probe revision | One failed startup lasting seconds; no traffic |
| Cloud Build | One successful build, approximately 29 seconds |
| Artifact Registry | One small diagnostic image |
| Minimal service revision | One failed startup lasting seconds; no traffic |
| IAM, requests, jobs, models, data | No temporary IAM; no authenticated request; no job/model/database/Pub/Sub work |

No posted billing charge was available in real time. A conservative incremental estimate remains
below `$0.05`, far below the `$10` per-action review gate. No billing account or billing
configuration was accessed or changed.

## Professional assessment and next decision

Further deployment changes stopped exactly where authorized. The attached support packet preserves
the full evidence trail, but the new minimal-image result should not be presented to Google as
proof of a platform-level ASGI defect without disclosing the zero-delay, one-failure probe.

The cheapest technically valid next test would change the probe timing only—for example, add a
10-second initial delay and allow multiple attempts—then apply it first to the already-built
minimal image. That change was not authorized and was not made. If the minimal image still fails
with a reasonable probe window, support escalation becomes substantially stronger. If it passes,
apply the same corrected probe timing to Verity before returning to private Phase 7.

## Authorized corrected-timing final control

The owner subsequently authorized redeployment of the same immutable minimal image with Google's
documented example timing:

```yaml
startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  failureThreshold: 5
  periodSeconds: 3
  timeoutSeconds: 3
```

No build occurred. [cloudrun.minimal-asgi.yaml](../cloudrun.minimal-asgi.yaml) changed only those
probe-timing values and retained digest
`sha256:20c31500e1c946e4296b4463890438c72cd11b558e2d37178c07492f36dd398e`.

### Corrected minimal revision

The redeployment created `verity-asgi-diagnostic-00002-xlm`. It became Ready and received 100%
traffic. The container log establishes the internal application path independently:

```text
2026-08-28T23:54:54.771636Z  Application startup complete.
2026-08-28T23:54:54.772526Z  Uvicorn running on http://0.0.0.0:8080
2026-08-28T23:55:02.016751Z  GET /healthz HTTP/1.1 200 OK
2026-08-28T23:55:02.017232Z  STARTUP HTTP probe succeeded after 1 attempt
```

This confirms the prior minimal revision failed only because its first probe was too early. It
also proves the minimal FastAPI/Uvicorn image is healthy inside Cloud Run.

### One authenticated external request

The standard narrow private-health flow then ran once:

1. granted `verity-pubsub` Run Invoker only on `verity-asgi-diagnostic`;
2. granted the operator OpenID Token Creator only on `verity-pubsub`;
3. read both policies back with exactly one binding/member and no condition;
4. waited **60.015 seconds**;
5. direct `generateIdToken` succeeded on attempt 1;
6. local claims checks confirmed exact canonical audience and service-account email; and
7. sent exactly one `Invoke-WebRequest GET /healthz`.

Observed external result:

```text
HTTP 404
Google generic Error 404 (Not Found) HTML
The requested URL /healthz was not found on this server.
```

The response was not the static diagnostic JSON. The request did not appear in the revision's
request log or Uvicorn access log; the only `/healthz` access entry is the successful internal
startup probe above.

Both temporary IAM grants were removed with exit 0 and independently read back as empty. No token
or authorization header was written to disk or output.

### Final branch decision

The owner's condition for updating production required both Ready state **and** real authenticated
diagnostic JSON. Ready passed, but the external request failed. Therefore:

- corrected timing was **not** applied to production `verity`;
- no production authentication window was opened;
- Phase 7 subscription/OIDC gates were not run;
- `verity-worker` remains absent; and
- Phase 8 remains closed.

This final control separates the two problems cleanly:

1. the original one-attempt HTTP probe was too aggressive; and
2. independently, a Ready minimal application that internally serves `/healthz` still receives an
   unlogged Google-front-end 404 for a correctly authenticated external request.

The second result contains no Verity imports, startup hooks, middleware, dependencies, secrets, or
application logic. Together with the known-good Google sample service, it is now appropriate to
escalate the private custom-container routing behavior to Google Cloud Support. The diagnostic
service and failed/Ready revisions remain intact as requested.

### Final incremental cost

This continuation created one Ready revision, performed four temporary IAM policy mutations, one
successful token mint, and one external request. It performed no build, image push, production
revision, job, model, database, or Pub/Sub operation. No posted charge was available in real time;
the closest observable incremental cost remains below `$0.01`. No billing resource was accessed
or changed.

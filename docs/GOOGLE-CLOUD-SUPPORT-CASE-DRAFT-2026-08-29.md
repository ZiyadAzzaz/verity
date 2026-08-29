# Google Cloud Support Case Draft — Verity Cloud Run Routing and Startup Evidence

**Status:** finalized for owner submission, not submitted because no authenticated in-app
browser tab was attached to the agent session

## Case summary

Project `verity-506800`, region `us-central1`, has repeatedly returned Google-front-end HTTP 404
for correctly authenticated requests to private Cloud Run service `verity`, without corresponding
revision request logs. Authentication, audience, identity, service IAM, service recreation,
project/region sample-container routing, image command variants, and HTTP client construction have
been independently tested.

The latest HTTP startup-probe experiment produced a new finding: both the production Verity image
and a minimal FastAPI/Uvicorn image failed an HTTP `/healthz` startup probe with
`ERROR_CONNECTION_FAILED`. However, both probes used zero initial delay and a failure threshold of
one, and the platform attempted them about 0.22 seconds after instance start. This timing must be
disclosed because it may fully explain the probe failures and prevents treating them alone as
proof of a Cloud Run platform defect.

## Environment

- Project: `verity-506800` (`291098081728`)
- Region: `us-central1`
- Production service: `verity`
- Canonical URL: `https://verity-7pauedpknq-uc.a.run.app`
- Production failed HTTP-probe revision: `verity-00010-7ft`
- Last Ready production revision: `verity-00009-ltc`
- Minimal service: `verity-asgi-diagnostic`
- Minimal failed revision: `verity-asgi-diagnostic-00001-88h`
- Minimal image digest:
  `sha256:20c31500e1c946e4296b4463890438c72cd11b558e2d37178c07492f36dd398e`
- Minimal build ID: `6b53a00e-a63b-4764-b28d-9f4560ed2788`

## Strongest established evidence

1. Google's known-good sample container returned and logged authenticated HTTP 200 in the same
   project and region.
2. The exact Verity image returned and logged HTTP 200 when its command was replaced with Python's
   built-in HTTP server.
3. Direct Uvicorn, lifespan-disabled Uvicorn, and asyncio+h11 Uvicorn variants returned unlogged
   Google-front-end 404.
4. A direct IAM Credentials token had the correct audience and service-account email.
5. `Invoke-WebRequest` and curl used the exact same validated token and both returned identical
   unlogged Google-front-end 404 bodies.
6. Deleting and recreating `verity`, and deploying the image under a different service name, did
   not change the external symptom.
7. Production HTTP startup probe log:

   ```text
   STARTUP HTTP probe failed 1 time consecutively for container "verity-api-1"
   on port 8080 path "/healthz". The instance was not started.
   Connection failed with status ERROR_CONNECTION_FAILED.
   ```

8. Minimal FastAPI/Uvicorn startup probe log:

   ```text
   STARTUP HTTP probe failed 1 time consecutively for container "minimal-asgi-1"
   on port 8080 path "/healthz". The instance was not started.
   Connection failed with status ERROR_CONNECTION_FAILED.
   ```

## Probe-timing caveat

Both failed probe configurations omitted `initialDelaySeconds` and set `failureThreshold: 1`.
Observed first-failure timing was approximately 0.221 seconds for Verity and 0.236 seconds for the
minimal image. Official Cloud Run documentation states the default initial delay is zero; the
official service sample uses an initial delay and multiple failures:

- https://docs.cloud.google.com/run/docs/configuring/healthchecks
- https://docs.cloud.google.com/run/docs/samples/cloudrun-healthchecks-startup-probe-http

Before asserting a platform defect, the recommended final control is to rerun the already-built
minimal image with a reasonable initial delay and multiple permitted failures.

## Final corrected-timing control

That control is now complete. The same immutable minimal image was redeployed with:

```text
initialDelaySeconds: 10
failureThreshold: 5
periodSeconds: 3
timeoutSeconds: 3
```

Revision `verity-asgi-diagnostic-00002-xlm` became Ready with 100% traffic. Its logs show:

```text
Application startup complete.
Uvicorn running on http://0.0.0.0:8080
GET /healthz HTTP/1.1 200 OK
STARTUP HTTP probe succeeded after 1 attempt
```

The operator then applied exactly scoped temporary IAM, waited 60.015 seconds, directly minted a
Google-signed ID token on the first attempt, and verified exact audience and service-account email
claims. Exactly one external `GET /healthz` returned Google's generic HTTP 404 HTML instead of
`{"status":"ok","diagnostic":"minimal-fastapi-uvicorn"}`. That request produced no Cloud Run
revision request log and no Uvicorn access log. Both temporary IAM grants were removed and read
back as empty.

This corrected result supersedes the probe-timing caveat as the final control: the minimal
application is internally healthy and serves the exact path, but the correctly authenticated
external request does not reach it.

## Final execution-environment and region controls

Two additional low-cost controls used the same immutable image, gen2 execution environment,
no-role runtime identity, corrected startup probe, resources, scaling, and private IAM boundary.

### Explicit gen2 in `us-central1`

Before the update, the service had no explicit
`run.googleapis.com/execution-environment` annotation. Updating only
`--execution-environment=gen2` created Ready revision
`verity-asgi-diagnostic-00003-k6r`, with 100% traffic and the annotation read back as `gen2`.
Internal logs showed application startup, Uvicorn on `0.0.0.0:8080`, and startup-probe
`GET /healthz` HTTP 200.

The first narrow authentication window stopped before a request when the single token mint
returned HTTP 403; both grants were removed. In a second narrow window, the previously approved
bounded 403-only mint rule succeeded on attempt 3 after a 60.003-second propagation wait. Token
claims matched the canonical audience and push-service-account email. The only external
`GET /healthz` still returned generic Google HTTP 404 HTML and did not appear in the revision's
request or Uvicorn logs. Both temporary grants were removed and read back absent.

### Same gen2 service in `us-east1`

A fresh private service, `verity-asgi-diagnostic-east1`, was deployed in `us-east1` with the exact
same image digest and configuration. Revision
`verity-asgi-diagnostic-east1-00001-pf5` became Ready with 100% traffic. Internal logs again showed
Uvicorn listening and startup-probe `GET /healthz` HTTP 200.

One local PowerShell launch typo stopped the first authentication window before token minting or
HTTP; cleanup removed both grants. The corrected run waited 60.007 seconds, received HTTP 403 on
mint attempt 1, succeeded on attempt 2, and verified matching audience, email, and
`email_verified=true`. Its only external `GET /healthz` returned the same generic Google HTTP 404
HTML and was absent from revision and Uvicorn logs. Cleanup read-back showed both exact bindings
absent.

These controls rule out an explicit gen2 switch and a move from `us-central1` to `us-east1` as
fixes. They also show the symptom is not confined to one of those regions. The `us-east1` service
is retained privately, at scale to zero and with empty IAM, as support evidence.

## Questions for Google Cloud Support

1. Why do correctly authenticated, audience-matched requests sometimes receive an unlogged Google
   front-end 404 while unauthenticated requests to the same service are logged as 403?
2. Why does the Ready minimal service's internal HTTP probe receive 200 while an audience-matched
   external request receives an unlogged Google-front-end 404?
3. Is an immediate HTTP startup probe approximately 0.22 seconds after instance-start expected
   when `initialDelaySeconds` is omitted, and does `failureThreshold: 1` intentionally terminate
   on that first refusal?
4. Are there known interactions between private Cloud Run routing and custom Uvicorn/ASGI images
   that could explain the same authenticated unlogged 404 in both `us-central1` and `us-east1`,
   including with explicit gen2?

## Attachments and records

- [Primary work record](WORKLOG-2026-08-29-HTTP-PROBE-AND-MINIMAL-ASGI.md)
- [Gen2 and region isolation](WORKLOG-2026-08-29-GEN2-AND-REGION-ISOLATION.md)
- [Same-token client comparison](WORKLOG-2026-08-29-SAME-TOKEN-CLIENT-COMPARISON.md)
- [Uvicorn isolation record](WORKLOG-2026-08-28-UVICORN-ISOLATION.md)
- [Cloud Run sample isolation](WORKLOG-2026-08-28-CLOUD-RUN-SERVICE-ISOLATION.md)
- [Clean recreation and fallback](WORKLOG-2026-08-28-CLEAN-RECREATE-AND-FALLBACK.md)
- [Private OIDC proof](WORKLOG-2026-08-28-PRIVATE-OIDC-HEALTH-PROOF.md)
- [Production backup](BACKUP-VERITY-SERVICE-BEFORE-RECREATE-2026-08-28.md)

Do not include access tokens, `.env`, API keys, secret values, billing identifiers, or temporary
curl configurations in a support attachment.

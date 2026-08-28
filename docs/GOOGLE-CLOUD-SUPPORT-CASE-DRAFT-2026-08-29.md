# Google Cloud Support Case Draft — Verity Cloud Run Routing and Startup Evidence

**Status:** prepared, not submitted

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

## Questions for Google Cloud Support

1. Why do correctly authenticated, audience-matched requests sometimes receive an unlogged Google
   front-end 404 while unauthenticated requests to the same service are logged as 403?
2. Is an immediate HTTP startup probe approximately 0.22 seconds after instance-start expected
   when `initialDelaySeconds` is omitted?
3. Does `failureThreshold: 1` intentionally terminate the instance on that first connection
   refusal without waiting `periodSeconds`?
4. Are there known interactions between private Cloud Run routing and Uvicorn/ASGI containers in
   `us-central1` that could explain the earlier authenticated unlogged 404s?

## Attachments and records

- [Primary work record](WORKLOG-2026-08-29-HTTP-PROBE-AND-MINIMAL-ASGI.md)
- [Same-token client comparison](WORKLOG-2026-08-29-SAME-TOKEN-CLIENT-COMPARISON.md)
- [Uvicorn isolation record](WORKLOG-2026-08-28-UVICORN-ISOLATION.md)
- [Cloud Run sample isolation](WORKLOG-2026-08-28-CLOUD-RUN-SERVICE-ISOLATION.md)
- [Clean recreation and fallback](WORKLOG-2026-08-28-CLEAN-RECREATE-AND-FALLBACK.md)
- [Private OIDC proof](WORKLOG-2026-08-28-PRIVATE-OIDC-HEALTH-PROOF.md)
- [Production backup](BACKUP-VERITY-SERVICE-BEFORE-RECREATE-2026-08-28.md)

Do not include access tokens, `.env`, API keys, secret values, billing identifiers, or temporary
curl configurations in a support attachment.

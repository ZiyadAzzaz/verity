# Verity — HTTP Startup Probe Attempt Blocked Before Mutation

**Date:** 2026-08-29
**Repository:** `https://github.com/ZiyadAzzaz/verity`
**Branch:** `main`
**Starting revision:** `b4287f552a3f1e55984d362d2a82ccd1335420fc`
**Operator:** `ziyadazzazdesigner@gmail.com`
**Google Cloud project:** `verity-506800`
**Region:** `us-central1`
**Service:** `verity`
**Phase 8:** not authorized and not executed

## Objective and authorization

The owner authorized two priorities in order:

1. replace only the existing TCP startup probe with HTTP `GET /healthz` on port 8080 and run one
   authenticated private health check; and
2. only if that completed test still failed, build and test one minimal FastAPI/Uvicorn image.

The owner explicitly required a stop if an action outside this scope became necessary. Enabling a
previously disabled Google Cloud API, using a different mutation mechanism, broader IAM, public
access, and Phase 8 were not included.

## Preflight and prepared manifest

- Local and `origin/main` matched `b4287f5`; the worktree was clean.
- Active gcloud project/account were `verity-506800` and the expected operator.
- The live service export confirmed private Ready revision `verity-00009-ltc`, 100% traffic, the
  pinned image digest, and the original TCP startup probe.
- [cloudrun.http-probe.yaml](../cloudrun.http-probe.yaml) was prepared from the live exported
  service configuration.
- Identity, environment, secret references, resources, concurrency, scaling, ingress, image,
  port, and traffic were preserved. The only intended service behavior change is:

  ```yaml
  startupProbe:
    failureThreshold: 1
    httpGet:
      path: /healthz
      port: 8080
    periodSeconds: 240
    timeoutSeconds: 240
  ```

No credential or secret value is stored in the manifest; it contains only Secret Manager
references already present in the live service.

## Replace attempt and exact blocker

One authorized command was invoked:

```powershell
gcloud run services replace cloudrun.http-probe.yaml `
  --region=us-central1 --project=verity-506800 --quiet
```

It failed before creating a revision or updating the service:

```text
Cloud Resource Manager API has not been used in project verity-506800 before or it is disabled.
service: cloudresourcemanager.googleapis.com
reason: SERVICE_DISABLED
```

The command requested enabling `cloudresourcemanager.googleapis.com` and retrying. That API
enablement is a new project mutation outside the authorized two priorities. No automatic enable,
alternative REST/CLI mutation, or retry was attempted.

## Read-only post-failure verification

Read-back proved:

- latest created and Ready revision are still `verity-00009-ltc`;
- traffic remains 100% on that revision;
- the exact pinned Verity image is unchanged;
- the startup probe remains TCP port 8080 with the original thresholds;
- `verity` service IAM remains empty;
- push-service-account resource IAM remains empty; and
- the Cloud Resource Manager API is not in the enabled-services result.

No authenticated health window was opened because the probe change never applied. Priority 1 is
therefore **blocked, not failed as a diagnostic**. Priority 2 was not reached and no image was
built.

## Cost and security record

Projected cost for the replacement was effectively `$0.00`. The mutation was rejected before a
revision existed. Observed chargeable usage was zero: no revision, container, request, token mint,
build, image, model, database operation, or Pub/Sub delivery occurred. The closest observable
incremental cost is `$0.00`. No billing/payment/budget/quota/plan resource was accessed or changed.

There were no temporary IAM grants, credentials on disk, or cleanup obligations from this failed
precondition.

## Professional assessment and required owner action

The prepared replacement is ready, but execution now requires one additional authorization:

```powershell
gcloud services enable cloudresourcemanager.googleapis.com --project=verity-506800
```

After the API reports enabled, retry the same single `gcloud run services replace` command, verify
the new revision and HTTP probe, and continue the already authorized priority sequence. Do not
start the minimal-image build before Priority 1 produces a real health result.

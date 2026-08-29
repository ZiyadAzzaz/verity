# Verity — Cloud Run Gen2 and Region Isolation

**Date:** 2026-08-29

**Repository:** `https://github.com/ZiyadAzzaz/verity`

**Branch:** `main`

**Starting revision:** `d93ea9ff849a6548b9891adaae56192d00742289`

**Operator:** `ziyadazzazdesigner@gmail.com`

**Project:** `verity-506800`

**Production region:** `us-central1`

**Phase 8:** not authorized and not executed

## Objective and boundary

Test two previously unisolated, low-cost variables on the pinned minimal FastAPI/Uvicorn image:

1. explicitly switch the existing `us-central1` diagnostic service to Cloud Run gen2; and
2. if that did not return real diagnostic JSON externally, deploy the identical gen2 diagnostic
   in `us-east1` and test it once.

No image build, production deployment, public access, broad IAM, Secret Manager change, Pub/Sub
creation, billing/payment/budget/quota/plan action, or Phase 8 action was authorized. Temporary
IAM had to be removed after every authentication window.

## Starting preconditions

- Git was clean at `d93ea9f`.
- Active account and project were the expected operator and `verity-506800`.
- `verity-asgi-diagnostic-00002-xlm` was Ready and received 100% traffic.
- Its service and the `verity-pubsub` service account had empty IAM policies.
- The service template did not contain an explicit
  `run.googleapis.com/execution-environment` annotation before the test. This is recorded as an
  absent/default setting, not falsely reported as an explicit `gen1` value.
- The immutable image digest was
  `sha256:20c31500e1c946e4296b4463890438c72cd11b558e2d37178c07492f36dd398e`.

## Test 1 — explicit gen2 in `us-central1`

The only intended service change was:

```powershell
gcloud run services update verity-asgi-diagnostic `
  --region=us-central1 --project=verity-506800 `
  --execution-environment=gen2
```

Cloud Run created `verity-asgi-diagnostic-00003-k6r`. It became Ready, received 100% traffic, and
read-back showed `run.googleapis.com/execution-environment: gen2`. Internal logs proved:

```text
Application startup complete.
Uvicorn running on http://0.0.0.0:8080
GET /healthz HTTP/1.1 200 OK
STARTUP HTTP probe succeeded after 1 attempt
```

### Authentication windows

The first narrow window applied exactly one Run Invoker member on the diagnostic service and one
OpenID Token Creator member on `verity-pubsub`, waited 60.020 seconds, then received HTTP 403 on
the single direct `generateIdToken` call. No health request occurred. Cleanup commands exited 0;
an exact follow-up policy read showed no bindings.

Because this endpoint has previously shown transient first-attempt 403 and the owner had already
established a bounded 403-only rule, a second narrow window allowed at most three mint attempts
while preserving the one-request limit. After a 60.003-second wait:

```text
mint attempt 1: HTTP 403
mint attempt 2: HTTP 403
mint attempt 3: HTTP 200
audience match: true
email match: true
email_verified: true
external GET /healthz: HTTP 404, Google generic HTML
```

The external request did not appear in the revision request log or Uvicorn access log. Both exact
temporary bindings were removed and read back absent.

**Result:** explicit gen2 did not fix the authenticated external routing failure.

## Test 2 — identical service in `us-east1`

The service was confirmed absent before creation. The new manifest
[cloudrun.minimal-asgi.us-east1.yaml](../cloudrun.minimal-asgi.us-east1.yaml) changes the location
and service name while retaining:

- the exact pinned image digest;
- explicit gen2;
- `verity-sandbox` no-role runtime identity;
- private IAM;
- 1 CPU, 512 MiB, concurrency 4, timeout 60, max scale 1; and
- corrected `/healthz` probe timing: initial delay 10, threshold 5, period 3, timeout 3 seconds.

Revision `verity-asgi-diagnostic-east1-00001-pf5` became Ready with 100% traffic. Its internal logs
again showed Uvicorn listening on `0.0.0.0:8080`, startup-probe `/healthz` HTTP 200, and probe
success.

### Tooling stop and corrected execution

The first IAM window waited 60.015 seconds but a local PowerShell typo concatenated the
`-ContentType` parameter and its value. No token request and no health request occurred. The
unconditional cleanup removed both grants, and exact read-back showed zero matching bindings.

The launch typo was corrected without changing cloud configuration or scope. The still-unperformed
test then ran in a new narrow window:

```text
exact IAM read-back: one authorized member on each policy
propagation wait: 60.007 seconds
mint attempt 1: HTTP 403
mint attempt 2: HTTP 200
audience match: true
email match: true
email_verified: true
external GET /healthz: HTTP 404, Google generic HTML
cleanup read-back: zero exact bindings
```

The external `/healthz` request did not appear in the service's request or Uvicorn logs. A separate
unauthenticated browser-generated `/favicon.ico` received a normally logged 403; it is not the
authorized health request and is not counted as evidence for application health.

**Result:** changing from `us-central1` to `us-east1` did not fix the failure.

## Final cloud and security state

| Resource or boundary | Final observed state |
|---|---|
| `verity-asgi-diagnostic` | Private, Ready revision `00003-k6r`, 100%, explicit gen2 |
| `verity-asgi-diagnostic-east1` | Private, Ready revision `00001-pf5`, 100%, explicit gen2 |
| Both diagnostic service IAM policies | Empty |
| `verity-pubsub` resource IAM | Empty |
| Production `verity` | Unchanged; `verity-00009-ltc` remains Ready at 100% |
| `verity-worker` | Absent |
| Public `allUsers` binding | Not created |
| Phase 7 | Still blocked before push/OIDC gates |
| Phase 8 | Closed and unauthorized |

The `us-east1` diagnostic service was not deleted. It is private, scale-to-zero, has empty IAM,
and is retained as support evidence. Deletion requires a later explicit cleanup decision after
the evidence is no longer needed.

## Cost record

| Cloud action | Closest observable actual usage |
|---|---|
| One gen2 `us-central1` revision | One deployment startup and internal probe |
| One new `us-east1` service/revision | One deployment startup and internal probe |
| Authentication windows | Temporary IAM mutations, bounded token mints, two actual health requests total |
| Builds/images | No build; reused the existing immutable image |
| Production/data/model work | None |

Google Cloud did not expose a posted line-item charge in real time. Based on the directly observed
two short scale-to-zero revision startups and request counts, the conservative incremental
estimate is below `$0.02`. This is far below the `$10` action gate and the approximately `$25`
project target. No billing resource or configuration was accessed or changed.

## Findings and professional assessment

Both cheap variables are conclusively exhausted. The same minimal static route is internally
healthy under explicit gen2 in two regions, but a correctly signed, audience-matched service
account request receives Google-front-end 404 before reaching either revision. This rules out an
explicit gen2 switch and a region move between `us-central1` and `us-east1` as fixes. It does not
justify weakening IAM or making the service public as a diagnostic shortcut.

The support case is now the appropriate documentation path, but it should not be treated as a
near-term hackathon dependency. A product fallback decision is required: either alter the hosting
architecture with a separately reviewed proof plan or submit/demo the locally and privately
validated system without claiming a public Cloud Run endpoint.

## Documentation and owner action

- Support packet updated:
  [GOOGLE-CLOUD-SUPPORT-CASE-DRAFT-2026-08-29.md](GOOGLE-CLOUD-SUPPORT-CASE-DRAFT-2026-08-29.md)
- Exact submission steps:
  [GOOGLE-CLOUD-SUPPORT-SUBMISSION-STEPS.md](GOOGLE-CLOUD-SUPPORT-SUBMISSION-STEPS.md)
- The agent attempted to attach to the in-app browser for authorized Console submission, but no
  browser tab/backend was available. No alternate browser or credential workaround was used.
- Owner action: attach an authenticated Google Cloud Console tab or submit the prepared case
  manually, then return the case ID and response text. Never paste credentials or tokens.

## Git status

This manifest, work record, support packet, submission guide, and state update are committed and
pushed together to `origin/main` as the final session step. The exact final revision and CI run are
reported in the handoff and remain independently visible in GitHub history.

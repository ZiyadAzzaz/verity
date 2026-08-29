# Verity — Cloud Run Reserved Health-Path Fix

**Date:** 2026-08-29

**Repository:** `https://github.com/ZiyadAzzaz/verity`

**Branch:** `main`

**Starting revision:** `e6ba36440e1b269c6ac6ace727edbaa21540f33c`

**Operator:** `ziyadazzazdesigner@gmail.com`

**Project:** `verity-506800`

**Region:** `us-central1`

**Phase 8:** not authorized and not executed

## Objective and authorization

Verify Google's documented reserved-path behavior, rename the health endpoint from `/healthz` to
`/health`, prove the change first on the minimal private diagnostic, and proceed to the private
production rebuild and remaining Phase 7 gates only if the minimal test returned exact application
JSON. Public access, billing/payment/budget/quota/plan changes, and Phase 8 remained prohibited.

## Root-cause confirmation

Google Cloud Run's official known-issues page states that some URL paths ending in `z` are reserved
and recommends avoiding every path ending in `z`:

- https://docs.cloud.google.com/run/docs/known-issues#ah

This applies directly to `/healthz` and explains the established pattern: Google-front-end 404,
no Cloud Run request log, no container access log, correct IAM and audience, Ready revision, and
successful internal startup probe.

## Minimal single-variable proof

The minimal FastAPI application route and Cloud Run startup probe changed from `/healthz` to
`/health`. The local TestClient gate proved exact JSON at `/health` and confirmed the removed
`/healthz` route returned local 404.

One Cloud Build ran with no retry:

```text
Build ID: fbdad2fc-fe81-41ba-90d0-25aab8262fca
Status: SUCCESS
Duration: 30 seconds
Source archive: 1.2 KiB
Image digest: sha256:a3866912b99eb854d4a23faaf4c1fb7dd82e7217673b623dbc489a3feb6e0b1c
```

The pinned image was deployed as revision `verity-asgi-diagnostic-00004-88p`, preserving explicit
gen2, runtime identity, resource limits, concurrency, scaling, ingress, and corrected startup
timing. It became Ready with 100% traffic and the `/health` startup probe passed.

The standard private authentication proof then:

1. applied exactly one service-level Run Invoker binding and one service-account OpenID Token
   Creator binding;
2. read both exact members back;
3. waited 60.004 seconds;
4. minted one ID token successfully on attempt 1;
5. verified exact audience, service-account email, and `email_verified=true` locally;
6. sent exactly one external `GET /health`; and
7. removed both grants and read both exact bindings back absent.

Observed result:

```text
HTTP 200
Content-Type: application/json
{"status":"ok","diagnostic":"minimal-fastapi-uvicorn"}
```

This holds every previously tested variable constant except the path and conclusively identifies
Cloud Run's reserved `/healthz` interception as the root cause.

## Production implementation

Active code, tests, manifests, and user-facing instructions now use `/health`. Historical worklogs
continue to name `/healthz` because they are immutable evidence of the investigation. The
production startup probe also uses the already-proven realistic timing: 10-second initial delay,
five failures, three-second period, and three-second timeout.

Files changed include:

- `verity/api.py` and `tests/test_api_local.py`;
- `cloudrun.http-probe.yaml`, both minimal diagnostic manifests, and the minimal app;
- `README.md`, local-demo/handover/status/project documentation, deployment plan, and state;
- the superseded Support draft and submission guide, which are retained but explicitly marked not
  to submit.

## Local verification

The first full run stopped at Ruff formatting because the edited Python lines had mixed line
endings. Ruff reformatted `verity/api.py`; no behavior changed. The next sandboxed pytest run was
invalidated by Windows `WinError 5` on its repository-local temporary directory and was not counted
as a test result. The identical full gate was rerun with workspace permissions and passed:

```text
ruff check: passed
ruff format --check: 133 files formatted
mypy: no issues in 32 source files
pytest: 272 passed, 3 emulator skips, 9 Docker deselections
```

## Cost record so far

Observed cloud work consists of one 30-second minimal build, one scale-to-zero diagnostic revision,
temporary IAM mutations, one token mint, and one request. No posted line-item charge was available
in real time. The conservative incremental estimate is below `$0.05`, below every review gate. No
billing resource or setting was accessed or changed.

## Current decision boundary

The minimal proof passed, so the owner-authorized next action is a commit-pinned production API
build, private deployment using `/health`, and one private authenticated health proof. Only if that
returns real Verity JSON may the remaining private Phase 7 OIDC gates proceed. Phase 8 remains a
mandatory separate owner checkpoint.

## Professional assessment

The evidence now explains every earlier failure without weakening IAM or invoking a speculative
platform anomaly. The safe response is the narrow route rename, not broader roles, public access,
or another hosting architecture. Support escalation is superseded unless a new independent fault
appears after the production rename.

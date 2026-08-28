# Verity — Bounded Uvicorn and Container Configuration Isolation

**Date:** 2026-08-28
**Repository:** `https://github.com/ZiyadAzzaz/verity`
**Branch:** `main`
**Starting revision:** `40b2af253d5d918e20d8527075b31dfc65350d17`
**Google Cloud project:** `verity-506800`
**Region:** `us-central1`
**Service:** `verity`
**Test budget:** maximum four sequential configuration tests
**Phase 8:** not authorized and not executed

## Objective and authorization

Delete the unused private `verity-app` fallback, then isolate the image/configuration cause of the
unlogged Google-front-end 404. The owner authorized up to four sequential tests on the existing
private `verity` service, changing one process/configuration dimension at a time, using the proven
direct service-account ID-token method, and reverting every unsuccessful change before continuing.

The sequence had to stop immediately on real HTTP 200 Verity JSON or after four unsuccessful,
reverted tests. Public access, a fifth hypothesis, broader IAM, Phase 7 continuation after failed
health, Phase 8, and billing/payment/budget/quota/plan changes were outside scope.

## Initial cleanup and baseline

- Local and remote `main` matched `40b2af2`; the worktree was clean.
- `verity-app` was Ready but private with an empty IAM policy.
- The owner-authorized deletion succeeded; final reads return service not found.
- Baseline `verity` was the freshly recreated service UID
  `c7a1abd8-eaf5-4189-8cbb-e190e2fc0fa7`, exact pinned digest
  `sha256:6a708965b91b6eab0602d17aa7b11807675c6c22f15d47bcd7a08647077f6326`,
  private, Ready, and 100% on revision `verity-00001-5rw`.

## Read-only source and runtime inspection

The deployed image's Docker command is:

```dockerfile
ENV PORT=8080
CMD ["sh", "-c", "exec uvicorn app.fast_api_app:app --host 0.0.0.0 --port ${PORT}"]
```

The Agents CLI wrapper contains only:

```python
from verity.api import app
```

The application defines `GET /healthz` directly. It has no Trusted Host or CORS middleware and no
host-header rejection. Its only HTTP middleware calls the route first and then adds response
security headers. The revision declares container port 8080, and Cloud Run startup probes pass.

Therefore, before any mutation:

- `127.0.0.1` binding was ruled out by source and deployed command;
- incorrect `$PORT` mapping was ruled out by `PORT=8080`, `--port ${PORT}`, declared port 8080,
  and successful probe;
- strict Host/CORS middleware was ruled out by source inspection; and
- the difference between `app.fast_api_app:app` and `verity.api:app` was known to be a one-line
  alias, but still tested by direct invocation.

Docker Desktop was not running locally, so no local image inspection was claimed. The immutable
Dockerfile, deployed service spec, and live revision evidence were used instead.

## Temporary authentication window

For the bounded four-test sequence, `verity-pubsub` received Run Invoker only on service `verity`,
and the operator received OpenID Token Creator only on `verity-pubsub`. Both policies contained
exactly one intended binding. A single **60.008-second** propagation wait occurred before test 1.
Every test then minted a fresh canonical-audience token directly through IAM Credentials. Tokens
were never printed or committed.

Both grants were removed after test 4 and read back as empty.

## Test results

### Test 1 — same image, Python HTTP server

**Single changed dimension:** container command/args.

```text
python -m http.server 8080 --bind 0.0.0.0
```

- Revision: `verity-00002-njx`
- Ready and 100% traffic
- Token mint: HTTP 200; audience/email checks passed
- Authenticated request: `GET /`
- Result: **HTTP 200**, Python directory listing from `/app`
- Revision request log: HTTP 200, latency `0.005787895s`

This proves the exact image runtime/filesystem, Cloud Run service/URL, port 8080, `0.0.0.0`, private
IAM, token, and request routing can work. It also prevents treating the earlier sample-image result
as the only positive control.

The command/args were immediately reset to image defaults. Baseline revision
`verity-00003-2rs` became Ready with 100% traffic.

### Test 2 — direct Uvicorn and direct Verity app

**Single changed dimension:** startup command path, bypassing `sh -c` and the wrapper alias.

```text
uvicorn verity.api:app --host 0.0.0.0 --port 8080
```

- Revision: `verity-00004-bnz`
- Ready and 100% traffic
- Token mint: HTTP 200; audience check passed
- Authenticated request: `GET /healthz`
- Result: **HTTP 404** with empty revision logs. The response body was not preserved because of the
  cleanup-handler defect below, so this record does not claim direct body confirmation for test 2.
- Revision request logs: empty

This rules out the shell command and `app.fast_api_app` wrapper as the fix.

The request script's `finally` block had a PowerShell spacing defect after curl completed. No token
was printed, but two `v-t2-*` files could have remained in OS temp. Cloud mutation stopped while a
bounded PowerShell cleanup resolved every matching path under the verified temp root, overwrote and
deleted exactly two files, and confirmed zero remained. This was a local cleanup defect, not a
cloud or application result.

The status/log pattern matches the other front-end failures, but that classification is an
inference for test 2 rather than body evidence. Test 2 was reverted immediately. Baseline revision
`verity-00005-fqw` became Ready with 100% traffic.

### Test 3 — Uvicorn lifespan disabled

**Single changed dimension:** ASGI lifespan handling.

```text
uvicorn verity.api:app --host 0.0.0.0 --port 8080 --lifespan off
```

- Revision: `verity-00006-sdv`
- Ready and 100% traffic
- Token mint: HTTP 200; audience check passed
- Authenticated `/healthz`: **unlogged Google-front-end HTTP 404**
- Revision request logs: empty

This rules out telemetry configuration, preflight, queue startup, and other lifespan initialization
as a sufficient explanation.

Test 3 was reverted immediately. Baseline revision `verity-00007-jqf` became Ready with 100%
traffic.

### Test 4 — pure-Python Uvicorn backends

**Single changed dimension:** Uvicorn runtime backend selection.

```text
python -m uvicorn verity.api:app --host 0.0.0.0 --port 8080 --loop asyncio --http h11
```

- Revision: `verity-00008-bkr`
- Ready and 100% traffic
- Token mint: HTTP 200; audience check passed
- Authenticated `/healthz`: **unlogged Google-front-end HTTP 404**
- Revision request logs: empty

This rules out Uvicorn's auto-selected optimized event loop and HTTP parser as the fix.

The fourth-test change was reverted immediately. Final baseline revision `verity-00009-ltc` is
Ready with 100% traffic and has no command/args override.

## Final cloud state

| Resource | Final state |
|---|---|
| `verity-app` | Deleted; not found |
| `verity` | Private, exact pinned image/config, Ready revision `verity-00009-ltc`, 100% traffic |
| `verity` command/args | Cleared; image defaults restored |
| `verity` IAM | Empty |
| Push identity resource IAM | Empty |
| `verity-worker` | Absent |
| Public `allUsers` | Absent |
| Phase 7 delivery gates | Not run because Verity health never passed |
| Phase 8 | Closed |

Per-revision request logs provide the strongest comparison:

```text
verity-00002-njx  Python http.server       HTTP 200 logged, 5.787895ms
verity-00004-bnz  direct Uvicorn           no request log
verity-00006-sdv  Uvicorn lifespan off     no request log
verity-00008-bkr  Uvicorn asyncio + h11    no request log
```

## Cost record

| Activity | Closest observed usage |
|---|---|
| Fallback cleanup | One private service deletion |
| Four tests | Four new Ready revisions and four fresh token mints |
| Reverts | Four baseline-restoration revisions |
| Requests | One logged 5.79ms HTTP 200 plus three front-end 404s before revision logging |
| Builds/jobs/models/data | None |

No posted billing charge was available in real time. The bounded activity was eight short revision
rollouts, four token mints, and four requests; min instances remained zero and no build/model/job
ran. A conservative incremental estimate remains below `$0.05`, far below the `$10` action gate.
No billing configuration or billing account was accessed or changed.

## Conclusions

Observed evidence rules out:

- loopback binding;
- `$PORT`/declared-port mismatch;
- Cloud Run service/project/region/private IAM routing generally;
- stale service object and exact service name;
- shell expansion and Agents CLI wrapper;
- strict Host or CORS middleware;
- application lifespan startup; and
- Uvicorn's optimized loop/HTTP parser selection.

The remaining common boundary is **running an ASGI/Uvicorn application process from this pinned
image**. The exact image can serve and log HTTP normally with Python's built-in server, but every
tested Uvicorn variant is invisible at the revision request-log boundary. This is narrower than an
unqualified “image/configuration issue,” but it does not yet prove the specific underlying Uvicorn
or image-build defect.

## Professional assessment and next owner decision

The authorized four-test budget is exhausted and all unsuccessful changes were reverted. Do not
continue Phase 7/8 or make another live configuration mutation without a new decision.

The strongest next engineering path is no longer another cloud flag. Build a minimal diagnostic
ASGI server into a new immutable image from the same Python base and dependency lock, then add
Verity imports/startup components one at a time. This can determine whether the failure begins at
Uvicorn alone, FastAPI/Starlette, module import, or a specific dependency/build layer. That is a
new image/build plan and requires explicit authorization because it consumes a Cloud Build and
produces a new artifact. Alternatively, stop live testing and preserve this evidence for support.

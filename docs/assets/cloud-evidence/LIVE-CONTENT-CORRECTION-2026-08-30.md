# Fresh live-content evidence — 2026-08-30

**Captured:** 2026-08-30 01:46:48–01:46:49 UTC  
**Method:** direct `Invoke-WebRequest`, unique millisecond query, request
`Cache-Control: no-cache` and `Pragma: no-cache`  
**Revision:** `verity-00019-nfl`, 100% traffic  
**Image:** `sha256:db29f7040eaf5e3217f103ee25381183d70693bc53d0ab0c40fa683940969d9e`

This file records safe response facts and selected returned text. It contains no API key, token,
authorization header, secret value, or authenticated verification request.

## Canonical domain

`https://verity-7pauedpknq-uc.a.run.app`

```text
GET /?_=<unique milliseconds>
HTTP 200
Cache-Control: no-store, max-age=0
Pragma: no-cache
Exact equality with verity/static/index.html at HEAD: True
```

Returned TRY ONE labels:

```text
ResNet paper
Attention paper
requests README
data-analysis repo
orjson · compiled extension
```

```text
GET /architecture?_=<unique milliseconds>
HTTP 200
Cache-Control: no-store, max-age=0
Pragma: no-cache
Exact equality with verity-architecture.html at HEAD: True
```

## Alternate Cloud Run domain

`https://verity-291098081728.us-central1.run.app`

Both cache-busted routes returned HTTP 200, the same no-store/no-cache headers, exact equality with
HEAD, and the same chip list.

## Forbidden-content proof

Case-insensitive searches across each domain's freshly returned homepage plus architecture HTML:

| Text | Present |
|---|---|
| `requests · verified` | No |
| `Free tools available from the hackathon` | No |
| `Cloud credits` | No |
| `GEAR program` | No |
| `billing tips` | No |
| `design target` | No |
| `blocked in production` | No |
| `production blocked` | No |
| `experimental` | No |

## Service and security smoke

```text
latestReadyRevisionName: verity-00019-nfl
traffic: 100% verity-00019-nfl
GET /health: 200
health status: ok
profile: cloud
store: firestore
queue: pubsub
sandbox: cloud_run
issue_publisher: github
setup_error: null
unauthenticated POST /api/jobs: 401
```

This is fetched network evidence, not a claim based on a source diff or an existing browser tab.

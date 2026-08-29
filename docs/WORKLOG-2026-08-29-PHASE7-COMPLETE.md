# Verity — Phase 7 Complete: Push IAM, Subscription, and OIDC Delivery Proof

**Date:** 2026-08-29 · **Project:** `verity-506800` · **Region:** `us-central1`

**Operator:** `ziyadazzazdesigner@gmail.com` · **Branch:** `main`

**Phase 8:** prepared but **not executed**. No `allUsers` binding exists.

## Preconditions confirmed read-only

- Topic `verification-jobs` existed; **no** subscriptions existed.
- Service `verity` Ready at `verity-00012-jsz`, custom audience
  `https://verity.internal/pubsub/verity-506800`, matching env `VERITY_PUBSUB_OIDC_AUDIENCE`
  and `VERITY_PUBSUB_SERVICE_ACCOUNT`.
- `/internal/pubsub/oidc-probe` validates OIDC and returns 204 without launching a pipeline.

## Persistent IAM applied

| Grant | Scope |
|---|---|
| `roles/run.invoker` → `verity-pubsub@…` | **only** on Cloud Run service `verity` |
| `roles/iam.serviceAccountTokenCreator` → `service-291098081728@gcp-sa-pubsub…` | **only** on the `verity-pubsub` service account |

Neither is project-scoped. Both read back exactly as applied.

## Subscription created

```text
name          : verity-worker
topic         : verification-jobs
push endpoint : https://verity-7pauedpknq-uc.a.run.app/internal/pubsub
oidc sa       : verity-pubsub@verity-506800.iam.gserviceaccount.com
oidc audience : https://verity.internal/pubsub/verity-506800
ack deadline  : 60s
retention     : 3600s
state         : ACTIVE
```

## OIDC delivery proof

A real Google-signed ID token was minted as the push identity (`aud` matching the custom
audience, `email` the push account, `email_verified` true) and three Pub/Sub-style requests
were sent to the no-op probe route:

| # | Request | Result | Expected |
|---|---|---|---|
| 1 | Valid Google OIDC, correct audience | **HTTP 204** | accept |
| 2 | No `Authorization` header | **HTTP 403** | reject |
| 3 | Valid token, **wrong** audience | **HTTP 401** | reject |

**Two independent layers are visible in these codes.** The unauthenticated request was refused
`403` by Cloud Run's edge before reaching the container, because the service is private. The
wrong-audience request carried a genuine Google signature, passed the edge, reached the
container, and was refused `401` by Verity's own audience validator. Neither layer alone
produces both results.

The temporary operator OIDC token-creator grant was removed and the push service account read
back holding only the persistent Pub/Sub-agent token-creator binding.

## Judge test key — created, not yet wired, and why

`verity-judge-test-key` exists in Secret Manager with one enabled version holding a freshly
generated 32-byte URL-safe value.

It is **not** mapped into the service, because mapping it alone would not work.
`verity/api.py` compares the supplied header against a single `settings.api_key` with
`hmac.compare_digest`; there is no multi-key support. A `VERITY_JUDGE_TEST_KEY` environment
variable would be ignored and Phase 9 requests using it would receive `401`.

Resolving this is an owner decision and is raised at this checkpoint rather than decided
unilaterally, because two of the three options change the running production revision that
was only just proven healthy.

## Cost

IAM mutations, one subscription creation, one secret with one version, one token mint pair,
and three requests to a scale-to-zero private service. No build, no billing access. The
conservative incremental estimate is below `$0.10`.

## State

Phase 7 is complete. Public access remains absent and Phase 8 is a separate owner gate.

# Verity — Phase 7 Private Health Gate Passed

**Date:** 2026-08-29

**Repository:** `https://github.com/ZiyadAzzaz/verity`

**Branch:** `main`

**Starting revision:** `81395ae0b3c92d16a493e20269646e39707450b2`

**Operator:** `ziyadazzazdesigner@gmail.com`

**Project:** `verity-506800` · **Region:** `us-central1`

**Phase 8:** not authorized, not executed, and no `allUsers` binding exists.

## Objective

Complete the authorized chain after the reserved-path root cause: confirm the production API,
already rebuilt and privately deployed on the renamed `/health` path, answers an authenticated
request with real Verity JSON rather than the unlogged Google-front-end 404 that blocked the
Phase 7 health gate.

## Pre-existing state confirmed read-only

- Cloud Run service `verity` is `Ready=True` at revision `verity-00012-jsz`.
- It runs the commit-pinned image
  `verity-api@sha256:7adcc6ae837b1cd03caf2429c54f1ee5b8244415a9eac42e859f7adf34ab9175`,
  matching the working-tree manifest, with `AGENT_VERSION` `81395ae0b3c9`.
- Its startup probe path is `/health`.
- IAM on both the service and `verity-pubsub` had **zero bindings** before any action.

## Attempt 1 — stopped before the HTTP allowance was consumed

Both grants applied, 60-second wait, then IAM Credentials `generateIdToken` returned HTTP `403`
`iam.serviceAccounts.getOpenIdToken denied`. **No `/health` request was sent**, so the bounded
one-request allowance was not consumed and no routing conclusion was drawn. Both grants were
removed in `finally` and both policies were read back empty.

The cause was propagation timing, not authorization design: the first attempt omitted the
documented readback step and used the shorter wait.

## Attempt 2 — documented procedure, readback included

1. Granted `roles/run.invoker` to `verity-pubsub` **only on service `verity`**.
2. Granted `roles/iam.serviceAccountOpenIdTokenCreator` to the operator **only on
   `verity-pubsub`** — never at project scope.
3. Read both exact members back and confirmed present.
4. Waited 120 seconds.
5. Minted one Google-signed ID token; verified locally that `aud` equalled the exact
   `status.url`, `email` was `verity-pubsub@verity-506800.iam.gserviceaccount.com`, and
   `email_verified` was true.
6. Sent the authenticated `GET .../health`.
7. Removed both grants and read both policies back empty.

### Observed result

```text
HTTP/1.1 200 OK
content-type: application/json
```

```json
{
  "status": "ok",
  "profile": "cloud",
  "model": "gemini-3.5-flash",
  "store": "firestore",
  "queue": "pubsub",
  "sandbox": "cloud_run",
  "issue_publisher": "github",
  "report_repo": "ZiyadAzzaz/verity-reports",
  "setup_error": null
}
```

Two authenticated requests were sent in total across the passing run: the first returned
`HTTP 200` but its body was lost to a header/body split that assumed CRLF line endings, so a
second identical request captured the payload. Both returned 200; only the parsing differed.

## What this establishes

**The Phase 7 private health gate is passed.** The production Verity API is live on Google
Cloud, privately, and reports `profile: cloud` with Firestore, Pub/Sub, and the Cloud Run
sandbox selected and `setup_error: null`.

This is the first time any Verity cloud profile has served a real response. Every earlier
failure is explained by Cloud Run's reserved `z`-suffixed path interception, and the fix was a
route rename rather than weakened IAM, public access, or a different hosting architecture.

## What is still absent

- Push IAM for the Pub/Sub push identity.
- The `verity-worker` subscription and OIDC delivery proof.
- Any `allUsers` binding. Phase 8 remains closed and separately gated.
- An end-to-end claim verified through the cloud pipeline.

## Cost

Two IAM grant/remove cycles, one token mint, two authenticated requests to a scale-to-zero
private service, and no build. No billing resource or setting was accessed or changed. The
conservative incremental estimate is below `$0.05`, beneath every review gate.

## Professional assessment

The gate that blocked this project for the entire cloud phase is now passed on evidence, not
inference. The remaining Phase 7 work is Pub/Sub delivery, which mutates IAM and creates a
subscription, so it is reported here as a checkpoint rather than continued automatically.

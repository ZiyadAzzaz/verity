# Verity — Cloud Run Project-vs-Service Isolation Test

**Date:** 2026-08-28  
**Repository:** `https://github.com/ZiyadAzzaz/verity`  
**Branch:** `main`  
**Starting revision:** `c90827b54698a8a9a1355d69e12e5dff0ad4213a`  
**Google Cloud project:** `verity-506800`  
**Region:** `us-central1`  
**Operator:** `ziyadazzazdesigner@gmail.com`  
**Existing production service:** `verity` — not modified

## Objective and scope

Determine whether the repeated authenticated, unlogged Google-front-end 404 is project/region-wide
or specific to service `verity`. Deploy Google's known-good Cloud Run sample as a new private,
disposable service in the same project and region; call it once using the already-proven direct
service-account ID-token path; inspect its request logs; and delete it immediately.

Authorized changes were limited to:

- create `verity-diagnostic-test` from Google's sample image;
- grant `verity-pubsub` Invoker only on that temporary service;
- temporarily grant the operator OpenID-token minting only on `verity-pubsub`;
- send exactly one authenticated request; and
- remove both grants and delete the temporary service under every outcome.

No existing `verity` IAM/configuration change, redeployment, public access, Phase 8 action,
billing/payment/budget/quota/plan change, or GitHub Issue was authorized or performed.

## Preconditions

- Local `main` and `origin/main` matched `c90827b`; the worktree was clean.
- Active gcloud project/account matched the authorized values.
- `verity-diagnostic-test` did not exist.
- Existing service `verity` had an empty service IAM policy.
- Projected incremental cost was below a few cents, far below the `$10` single-action gate.

## Disposable deployment

The exact authorized deployment used:

```text
gcloud run deploy verity-diagnostic-test \
  --image=us-docker.pkg.dev/cloudrun/container/hello \
  --region=us-central1 \
  --no-allow-unauthenticated \
  --project=verity-506800
```

Observed result:

- revision: `verity-diagnostic-test-00001-2br`;
- canonical URL: `https://verity-diagnostic-test-7pauedpknq-uc.a.run.app`;
- regional URL: `https://verity-diagnostic-test-291098081728.us-central1.run.app`;
- `Ready=True`, `ConfigurationsReady=True`, `RoutesReady=True`;
- 100% traffic to the latest revision;
- imported immutable sample digest:
  `sha256:41057662708590d619ab7bcd0f90cd81679b6f924df11c0e9a4662c3b99b189a`;
- startup TCP probe passed on port 8080; and
- no source build occurred.

## Authentication and request

The push identity received Run Invoker only on the temporary service. The operator received
`roles/iam.serviceAccountOpenIdTokenCreator` only on that push identity. Both returned policies
contained exactly one intended binding.

After a **60.015-second** propagation wait, one direct IAM Credentials `generateIdToken` request
used the diagnostic service's canonical URL as audience and `includeEmail=true`. The mint returned
HTTP 200. Local validation, without printing the JWT, proved:

```text
audience match: true
email match: true
email_verified: true
```

Exactly one authenticated request was sent to `/`. It returned:

```text
HTTP/1.1 200 OK
content-type: text/html; charset=utf-8
server: Google Frontend
date: Fri, 28 Aug 2026 02:49:22 GMT
```

The response was Google's expected “Congratulations / It's running!” sample page and explicitly
identified revision `verity-diagnostic-test-00001-2br`, service `verity-diagnostic-test`, region
`us-central1`, and project `verity-506800`.

Cloud Run request logs independently recorded the same request:

```text
requestMethod: GET
requestUrl: https://verity-diagnostic-test-7pauedpknq-uc.a.run.app/
status: 200
latency: 0.005156796s
revision_name: verity-diagnostic-test-00001-2br
service_name: verity-diagnostic-test
```

This contrasts directly with the same authentication method against `verity`, where the request
returned Google-front-end 404 and produced no revision request log.

## Mandatory cleanup

Cleanup completed immediately after evidence capture:

1. removed the operator's OpenID Token Creator binding;
2. removed the push identity's temporary diagnostic-service Invoker binding;
3. deleted `verity-diagnostic-test`; and
4. verified the diagnostic service is not found, push-identity resource IAM is empty, and existing
   `verity` service IAM remains empty with the same etag observed before the test.

Audit/system logs record creation and deletion. The retired diagnostic revision is retained only in
Cloud Logging history, not as a live service.

## Cost record

| Action | Projection | Closest observed result |
|---|---:|---|
| Deploy sample image | Below a few cents | One 1-vCPU/512-MiB revision; startup succeeded in 3.13s; no build |
| IAM grants/removals and ID-token mint | `$0.00` | No observed billable workload |
| Authenticated sample request | Below `$0.01` | One request, 5.156796ms application latency, HTTP 200 |
| Service lifetime and deletion | Below a few cents | Created 02:46:54Z, deleted 02:50:18Z; min instances defaulted to zero |

**Closest observed incremental cost:** no posted billing charge was available at execution time.
Raw usage was one short deployment rollout, one 5.16ms request, and approximately 3m23s of
scale-to-zero service lifetime before deletion. The defensible upper estimate remains below a few
cents, far below every project cost gate. No billing configuration or account was accessed or
changed.

## Decisive interpretation

The test **passed normally** in the same project, account, region, canonical URL pattern, private
Invoker model, identity-token method, and client environment. Therefore the repeated 404 is not a
general `verity-506800`, `us-central1`, operator-account, service-account, IAM Credentials, private
Cloud Run, or local-network failure. It is specific to the deployed `verity` service path.

Important precision: this experiment changes both the Cloud Run service object and the container
image/configuration. It proves service-specific scope, but does not alone prove that the service
object is corrupted or that the earlier failed Phase 4 build caused it. Existing evidence makes a
clean recreation from the already-pinned Verity digest a pragmatic next action because it replaces
the service object while holding the application image constant.

## Professional assessment and next approval gate

The decisive isolation objective is achieved and cleanup is complete. Do not spend more time on
token/IAM/project diagnostics. The next controlled action should be a reviewed delete-and-recreate
of service `verity` from the exact immutable API digest, preserving its current identity, secrets,
environment, resource limits, concurrency, scaling, ingress, private exposure, and zero initial
Invoker policy. Capture the existing service YAML/IAM first and validate a reproducible recreation
command before deletion.

Deleting `verity` is destructive and creates brief downtime. This diagnostic authorization did
not authorize it, and the owner's wording explicitly reserved the next move until this result was
known. Wait for explicit approval of the recreation plan. Phase 8 remains separately closed.

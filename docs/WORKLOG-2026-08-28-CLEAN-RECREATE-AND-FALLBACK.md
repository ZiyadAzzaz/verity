# Verity — Clean Service Recreation and Renamed Fallback

**Date:** 2026-08-28  
**Repository:** `https://github.com/ZiyadAzzaz/verity`  
**Branch:** `main`  
**Starting revision:** `acc16efe18f5ce5731310ff6eab6c6aa7fd98941`  
**Google Cloud project:** `verity-506800`  
**Region:** `us-central1`  
**Operator:** `ziyadazzazdesigner@gmail.com`  
**Phase 8:** not authorized and not executed

## Objective and authorization

The owner authorized a destructive clean recreation of the still-private service `verity` from
its exact pinned image and captured configuration, followed immediately by the already-proven
service-account health test. If that fresh object still failed, the owner authorized one renamed
fallback deployment, `verity-app`, using the identical image/configuration and the same one-request
health proof. Remaining private Phase 7 work could continue only after real Verity health JSON.

The authorization did not permit public access, broader IAM, automatic retries, a third deployment
approach, billing/payment/budget/quota/plan changes, or Phase 8.

## Backup and preconditions

- Local and remote `main` matched `acc16ef`; the pre-session worktree was clean.
- Existing service `verity` was Ready and private with an empty IAM policy.
- Full YAML and IAM were captured before deletion in
  [BACKUP-VERITY-SERVICE-BEFORE-RECREATE-2026-08-28.md](BACKUP-VERITY-SERVICE-BEFORE-RECREATE-2026-08-28.md).
- The backup contains no secret values; it records only Secret Manager references.
- Exact immutable API image:
  `us-central1-docker.pkg.dev/verity-506800/verity/verity-api@sha256:6a708965b91b6eab0602d17aa7b11807675c6c22f15d47bcd7a08647077f6326`.
- Existing service UID was `ee40dbe7-c3c6-412b-af7c-3432a97bb9c8`.
- `verity-app` did not exist before the fallback branch.

The installed gcloud surface was checked locally for the required CPU boost/throttling, scaling,
environment, secret, label, and startup-probe controls before deleting anything.

## Clean recreation of `verity`

Service `verity` was deleted successfully. No image, job, secret, identity, topic, database, or
pipeline resource was deleted.

It was recreated from the exact pinned digest with the captured invariants:

- application identity `verity-app@verity-506800.iam.gserviceaccount.com`;
- 13 plain environment variables and the same two Secret Manager references;
- 1 vCPU, 2 GiB, concurrency 4, timeout 300 seconds;
- revision min instances 0/default and max instances 2;
- CPU throttling disabled and startup CPU boost enabled;
- ingress `all`, default URL enabled, private IAM;
- `created-by=adk`, port 8080, and default TCP startup probe; and
- 100% traffic to the new latest revision.

Observed fresh state:

- new service UID `c7a1abd8-eaf5-4189-8cbb-e190e2fc0fa7`;
- revision `verity-00001-5rw`;
- `Ready=True`, `ConfigurationsReady=True`, `RoutesReady=True`;
- canonical URL `https://verity-7pauedpknq-uc.a.run.app`; and
- regional URL `https://verity-291098081728.us-central1.run.app`.

The changed UID proves the test used a genuinely new service object, not another revision of the
old object.

## Immediate recreated-service health proof

The push identity received Run Invoker only on fresh service `verity`; the operator temporarily
received OpenID Token Creator only on the push identity. After **60.015 seconds**, direct IAM
Credentials `generateIdToken` returned HTTP 200. Local validation proved exact audience, exact
service-account email, and `email_verified=true` without printing the token.

Exactly one request was sent to `/healthz`. At `2026-08-28T03:06:12Z` it returned:

```text
HTTP/1.1 404 Not Found
Content-Type: text/html; charset=UTF-8
Content-Length: 1568
The requested URL /healthz was not found on this server.
```

The body was the same Google-front-end HTML, not Verity JSON. Curl exit code was 0, but the health
gate failed on HTTP status/body. Both temporary bindings were immediately removed. Read-back later
confirmed the service and push-identity policies were empty.

## Renamed `verity-app` fallback

Because the clean `verity` object still failed, the authorized fallback deployed the same digest
and configuration under `verity-app`. Only service-name-dependent values changed:

- service/revision name;
- canonical/regional URL; and
- `APP_URL=https://verity-app-291098081728.us-central1.run.app`.

Observed fallback state:

- service UID `d6eb5212-e1b5-4263-ba4b-9d02c2023883`;
- revision `verity-app-00001-cpc`;
- `Ready=True`, `ConfigurationsReady=True`, `RoutesReady=True`;
- 100% traffic;
- canonical URL `https://verity-app-7pauedpknq-uc.a.run.app`; and
- private IAM before the test.

The same two scoped test grants were applied. After **60.006 seconds**, direct token minting again
returned HTTP 200 and all three local claim checks passed. Exactly one `/healthz` request was sent.
At `2026-08-28T03:09:32Z`, it returned the same 1568-byte Google-front-end 404 HTML.

Both temporary bindings were removed immediately. Because fallback health failed, no hardcoded
service reference was changed in deployment scripts or documentation, and the fallback was not
promoted as the production path.

## Final state and log evidence

Read-only verification after cleanup showed:

| Resource | Final state |
|---|---|
| `verity` | Fresh private service, Ready, UID `c7a1...`, revision `verity-00001-5rw`, 100% traffic |
| `verity-app` | Private fallback retained for owner review, Ready, revision `verity-app-00001-cpc`, 100% traffic |
| `verity` IAM | Empty |
| `verity-app` IAM | Empty |
| Push identity resource IAM | Empty |
| `verity-worker` subscription | Absent |
| Pipeline executions | No execution launched by this work |
| Public `allUsers` | Absent |

Recent Cloud Run request-log queries for both `verity` and `verity-app` returned empty lists. Thus
neither correctly authenticated health request reached its revision logging boundary. This is the
same contrast established by the Google sample service, whose authenticated request returned 200
and appeared in revision logs.

`verity-app` was not deleted because the owner authorized it as a possible fallback path but did
not specify deletion on fallback failure. It is private with an empty IAM policy and min instances
zero, preserving evidence without public exposure or expected idle instance usage. Deletion can be
authorized after review.

## Cost record

| Action | Projection | Closest observed usage |
|---|---:|---|
| Delete old `verity` | `$0.00` | One control-plane deletion |
| Recreate `verity` | Below a few cents | One image deployment/startup; no Cloud Build |
| Recreated-service token/health test | Below `$0.01` | One ID-token mint; request rejected before revision logging |
| Deploy `verity-app` | Below a few cents | One image deployment/startup; no Cloud Build |
| Fallback token/health test | Below `$0.01` | One ID-token mint; request rejected before revision logging |
| IAM cleanup and read-only verification | `$0.00` | Both policies empty; no job or model call |

No posted billing charge was available in real time. The measured raw activity was two short
rollouts, two token mints, and two front-end-rejected requests. Both services use min instances
zero. The defensible incremental estimate remains below a few cents and far below the `$10` action
gate. No billing configuration or billing account was accessed or modified.

## Findings and decisions

1. **Stale service object is ruled out.** The replacement has a new UID and still fails.
2. **Exact service name is ruled out.** `verity-app` fails identically.
3. **Authentication remains ruled out.** Both direct mints and all claim checks passed.
4. **Revision readiness remains ruled out.** Both new revisions and routes are Ready with 100%
   traffic.
5. **Project/region/private Cloud Run remains generally healthy.** Google's sample returned and
   logged HTTP 200 under the same token method.
6. **The common discriminator is now the pinned Verity image/configuration path.** This does not
   prove a specific code defect because the request is still not visible in revision logs, but it
   is the only material dimension shared by both failing new services and not by the passing sample.
7. **Phase 7 correctly stayed closed.** No subscription, Pub/Sub service-agent token role, valid
   push proof, or wrong-audience proof followed a failed health gate.

## Professional assessment and next owner decision

The authorized sequence is exhausted. Further service-name/object recreation is not justified.
The next useful move must examine the remaining image/configuration discriminator or escalate the
precise contrast to Google Cloud support: same project/region/token/client, sample image logs 200,
Verity digest on two new service names returns unlogged 404.

Do not proceed to Phase 7 or Phase 8. The owner should decide whether to:

1. authorize deletion of unused private `verity-app` and open a Google Cloud support case; or
2. authorize one new, explicitly scoped image/configuration isolation plan that changes one
   dimension at a time while retaining the same private controls.

No credential needs to be shared in chat.

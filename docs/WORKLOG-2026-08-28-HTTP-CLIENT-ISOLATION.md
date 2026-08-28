# Verity — Alternate HTTP Client Isolation Attempt

**Date:** 2026-08-28
**Repository:** `https://github.com/ZiyadAzzaz/verity`
**Branch:** `main`
**Starting revision:** `82d98860372dbc557df4664abbf280ff87cc23ac`
**Operator:** `ziyadazzazdesigner@gmail.com`
**Google Cloud project:** `verity-506800`
**Region:** `us-central1`
**Service:** `verity`
**Phase 8:** not authorized and not executed

## Objective and boundary

Test whether the previous private-health failures were caused by the Windows `curl.exe` plus
temporary-config construction. The authorized test used the established narrow service-account
OIDC flow, but would send exactly one authenticated `/healthz` request with
`Invoke-WebRequest`, with no curl configuration file. Temporary IAM had to be removed regardless
of outcome. Remaining Phase 7 work was conditional on real HTTP 200 Verity JSON.

No build, image, deployment/configuration change, public access, broader IAM role, Phase 8, or
billing/payment/budget/quota/plan action was authorized.

## Preconditions

- Local and remote `main` matched `82d9886`; the worktree was clean.
- Active gcloud project and account were `verity-506800` and the expected operator.
- `verity-app` was already absent. The authorized deletion therefore required no additional
  mutation; a read returned `Cannot find service [verity-app]`.
- `verity` remained private and Ready on revision `verity-00009-ltc`, with 100% traffic and the
  exact pinned image digest.
- Service command and arguments remained unset, so image defaults were active.
- Service-level `verity` IAM and the push service account's resource IAM both read back with no
  bindings before the attempt.

## Authorized sequence and observed stop

1. Granted `verity-pubsub@verity-506800.iam.gserviceaccount.com` Run Invoker only on service
   `verity`.
2. Granted the operator `roles/iam.serviceAccountOpenIdTokenCreator` only on that service
   account.
3. Resolved the canonical audience as `https://verity-7pauedpknq-uc.a.run.app`.
4. Waited **60.010 seconds** for IAM propagation.
5. Acquired the operator access token in memory and called IAM Credentials
   `generateIdToken` directly, requesting the canonical audience and `includeEmail=true`.
6. IAM Credentials returned **HTTP 403 Forbidden**. PowerShell exposed
   `WebCmdletWebResponseException`; the response body was not available in the captured output.

The stop occurred before an ID token existed. Consequently:

- `Invoke-WebRequest` was **not called**;
- no request was sent to `/healthz`;
- there is no HTTP health status or response body;
- the curl/config-file hypothesis remains untested; and
- the result does not authorize or justify claiming the minimal-image branch was reached.

No automatic token-mint retry or alternate method was attempted. This preserves the established
one-shot discipline for an unexpected cloud failure.

## Unconditional cleanup and verification

The `finally` cleanup ran immediately after the mint failure:

- OpenID Token Creator removal exited 0;
- service-level Run Invoker removal exited 0;
- the final `verity` IAM policy read back with no bindings; and
- the final push-service-account resource IAM policy read back with no bindings.

Read-only Cloud Run logs contained no recent request for this attempt. A read-only IAM Credentials
audit-log query returned no matching entry. It therefore did not add an error reason beyond the
observed HTTP 403 and must not be treated as proof of a particular cause.

## Cloud and security state

| Resource or boundary | Final state |
|---|---|
| `verity-app` | Absent |
| `verity` | Private, Ready revision `verity-00009-ltc`, 100% traffic |
| `verity` configuration | Unchanged; exact pinned image and image-default command |
| `verity` IAM | Empty |
| Push identity resource IAM | Empty |
| Health requests in this attempt | Zero |
| Phase 7 subscription/delivery gates | Not executed |
| `allUsers` / Phase 8 | Absent / closed |

No credential value, token, `.env` value, or authorization header was printed or written to disk.
The in-memory token variables were cleared in the unconditional cleanup path.

## Cost record

Projected incremental cost was effectively `$0.00`. Observed activity consisted of four IAM
policy mutations, read-only resource/log queries, one operator access-token acquisition, and one
failed IAM Credentials request. No Cloud Run request, instance work, build, image, model, job,
database, or Pub/Sub delivery occurred. No posted charge was available in real time; the closest
observable incremental cost remains `$0.00`. No billing resource was accessed or changed.

## Defect and professional assessment

The precondition failed unexpectedly: the same direct narrow-role minting mechanism had succeeded
in earlier recorded attempts, but returned HTTP 403 after the required propagation wait here.
Because the alternate client never ran, it would be incorrect to report either a pass or the same
404 failure as curl.

The technically clean next step is one explicitly authorized rerun of this same client-isolation
test, adding a read-back of both intended IAM bindings before minting and preserving the
IAM Credentials error body if minting fails. Only an actual `Invoke-WebRequest` result can resolve
the curl-construction hypothesis. A new diagnostic image build should remain gated until that
cheap test either returns the same 404 or is deliberately abandoned by the owner.

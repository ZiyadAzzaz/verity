# Verity — Combined Private OIDC Health Proof

**Date:** 2026-08-28  
**Repository:** `ZiyadAzzaz/verity`, branch `main`  
**Starting local and remote revision:** `42df3872400937442d9b9b24c5b30f3780f4a053`  
**Google Cloud project:** `verity-506800`  
**Region:** `us-central1`  
**Operator:** `ziyadazzazdesigner@gmail.com`  
**Exposure boundary:** private Phase 7 only; Phase 8 explicitly unauthorized

## Objective and authorization

Run one combined sequence:

1. attempt an audience-bound human-account identity token against the exact current Cloud Run URL;
2. only if that fails, grant the dedicated Pub/Sub identity service-level Run Invoker, grant the
   operator resource-level OpenID token minting, wait at least 60 seconds, and perform one
   service-account mint attempt followed by at most one `/healthz` request; and
3. always remove the temporary minting role and, if health does not pass, also remove the early
   Run Invoker binding.

No redeployment, subscription creation, broader IAM, billing change, retry, third approach, or
Phase 8 action was authorized.

## Preconditions and URL comparison

- Git was already modified only by the in-progress documentation of the preceding rolled-back
  OIDC attempt; no code or infrastructure edit was pending.
- Local `HEAD` and `origin/main` both matched the starting revision above.
- Active gcloud project and account matched the authorized values.
- `gcloud run services describe` returned
  `https://verity-7pauedpknq-uc.a.run.app` as the current `status.url`.
- This current URL differs from the earlier deployment-returned
  `https://verity-291098081728.us-central1.run.app`; it matches the canonical URI previously
  returned by Cloud Run's v2 Admin API.

No credential, token, `.env` value, or secret was printed or committed.

## Step A — real result

The exact current URL was supplied to:

```text
gcloud auth print-identity-token --audiences=<current-status-url>
```

Observed result:

```text
ERROR: (gcloud.auth.print-identity-token) Invalid account type for `--audiences`.
Requires valid service account.
```

This is a real token-mint failure under the active human account, not a predicted outcome. No
token was produced and therefore no Step A HTTP request was sent. The conditional Step B authority
became active.

## Step B — actions and real result

The following narrowly scoped changes succeeded:

- service `verity`: granted `roles/run.invoker` only to
  `serviceAccount:verity-pubsub@verity-506800.iam.gserviceaccount.com`;
- push service account: granted `roles/iam.serviceAccountOpenIdTokenCreator` only to
  `user:ziyadazzazdesigner@gmail.com`.

No other binding appeared in either returned policy. The process then waited **60.017 seconds**
after both policy updates before the one authorized mint attempt.

The mint used gcloud service-account impersonation with the canonical URI as audience. It failed
with exit code 1 and this safe error evidence:

```text
PERMISSION_DENIED: Failed to impersonate
verity-pubsub@verity-506800.iam.gserviceaccount.com
Permission 'iam.serviceAccounts.getAccessToken' denied on resource.
```

The CLI explained that this impersonation path requires
`roles/iam.serviceAccountTokenCreator`. That broader role was not authorized and was not granted.
The currently granted narrow role contains `iam.serviceAccounts.getOpenIdToken`, not
`iam.serviceAccounts.getAccessToken`.

No token was produced, so no Step B `/healthz` request was sent. The propagation delay did not
resolve the failure because this specific command path required a different permission; this is
observed evidence, not an inference that IAM propagation failed.

## Mandatory cleanup and final cloud state

Cleanup ran immediately after the single mint attempt:

1. removed the operator's temporary
   `roles/iam.serviceAccountOpenIdTokenCreator` binding from the push identity;
2. removed the push identity's early `roles/run.invoker` binding from service `verity`; and
3. read both policies back and verified that each contains no bindings.

Final read-only checks also confirmed:

- subscription `verity-worker` is absent;
- `verity-pipeline` still has zero executions;
- no HTTP request occurred in this combined sequence;
- no GitHub Issue was created;
- no `allUsers` member exists; and
- Phase 8 remains closed.

## Cost record

| Action | Pre-action projection | Closest observed actual result |
|---|---:|---:|
| Read-only Cloud Run/Git/account preflight | `$0.00` | `$0.00` |
| Two scoped IAM grants | `$0.00` | `$0.00` |
| 60.017-second local wait | `$0.00` | `$0.00` |
| Two rejected local token mints | `$0.00` | `$0.00` |
| Two IAM removals and final policy reads | `$0.00` | `$0.00` |
| Cloud Run requests, builds, jobs, model calls | `$0.00` | None occurred |

**Incremental observed cost:** `$0.00`. No billable workload was started. This is below the `$10`
single-action and `$50` cumulative check-in triggers and does not change the approximately `$25`
project target. No billing, payment, budget, quota, plan, or credit setting was read or changed.

## Findings and decisions

1. **Step A is structurally incompatible with the active human credential.** The CLI requires a
   service-account credential when `--audiences` is supplied.
2. **The Step B gcloud impersonation command is incompatible with the narrowly authorized role.**
   It tries to obtain an access token and requires `iam.serviceAccounts.getAccessToken`, while the
   scoped OpenID role grants only `iam.serviceAccounts.getOpenIdToken`.
3. **The 60-second delay was honored but was not the deciding variable in this failure.** The new
   error is a concrete permission mismatch, so propagation must not be claimed as the root cause.
4. **No broader role was added.** Granting Service Account Token Creator would increase authority
   beyond this sequence and was explicitly rejected as an unauthorized recovery action.
5. **No third method was attempted.** A direct IAM Credentials `generateIdToken` call would be a
   new attempt after the sequence's terminal failure and needs a new owner decision.

## Files changed

- `docs/WORKLOG-2026-08-27-PRODUCTION-DEPLOYMENT.md`: preserved the preceding OIDC attempt and its
  rollback evidence.
- This record: captured the newly authorized combined attempt.
- `docs/STATE.md`: updated the current blocker, cleanup state, and approval boundary.
- `docs/POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md`: updated Phase 7 execution status.
- `docs/RESET-TO-CURRENT-CONSOLIDATED-REPORT-2026-08-27.md`: extended the chronological record.

## Professional assessment and next step

The sequence behaved safely: both failure modes were captured exactly, no token leaked, no HTTP
request was misreported, and IAM returned to its original private state. The API itself remains
unassessed by this sequence because neither client obtained a usable token.

Do not repeat either gcloud command or grant the broader Token Creator role. The technically
appropriate narrow mechanism is the IAM Credentials `generateIdToken` endpoint, which uses
`iam.serviceAccounts.getOpenIdToken`; however, the previous direct call returned 403. If the owner
wants to continue, the next authorization should cover exactly one diagnostic direct endpoint
call after an effective-permission precheck, capturing the complete non-secret error response. If
that call fails again, escalate to Google Cloud support with the error metadata. Phase 8 must
remain closed until private health and the remaining Phase 7 OIDC/rejection gates pass.

## Git completion

The final commit hash and `origin/main` push confirmation are filled by the Git history for this
record's documentation commit. No code or cloud configuration remains uncommitted as mutable local
state; the cloud IAM changes themselves were fully rolled back.

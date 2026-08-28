# Verity — Same-Token HTTP Client Comparison

**Date:** 2026-08-29
**Repository:** `https://github.com/ZiyadAzzaz/verity`
**Branch:** `main`
**Starting revision:** `82abe9fe443459fccad79f24f3f6f0ee470a0851`
**Operator:** `ziyadazzazdesigner@gmail.com`
**Google Cloud project:** `verity-506800`
**Region:** `us-central1`
**Service:** `verity`
**Phase 8:** not authorized and not executed

## Objective and authorization

Close the remaining HTTP-client construction hypothesis in one IAM window. The owner authorized:

1. the same two narrow temporary IAM grants;
2. exact read-back of both policies;
3. one 60-second propagation wait;
4. at most three direct `generateIdToken` attempts, retrying only HTTP 403 and waiting 15 seconds
   between attempts;
5. one `Invoke-WebRequest` and one `curl.exe` temporary-config request using the exact same
   successfully minted token; and
6. unconditional secure token/config cleanup and removal of both grants.

No retry of either health request, broader IAM, deployment, image build, public access, Phase 8,
or billing/payment/budget/quota/plan action was authorized.

## Preconditions

- Local and `origin/main` matched `82abe9f`; the worktree was clean.
- The active gcloud project/account were `verity-506800` and the expected operator.
- `verity` was private and Ready on `verity-00009-ltc`, with 100% traffic.
- The service used the pinned digest
  `sha256:6a708965b91b6eab0602d17aa7b11807675c6c22f15d47bcd7a08647077f6326`.
- Container command/args were unset, preserving image defaults.
- Service-level IAM and push-service-account resource IAM both had no bindings.
- `verity-app` was already absent.

## One IAM window

The following grants were applied:

- `roles/run.invoker` to
  `serviceAccount:verity-pubsub@verity-506800.iam.gserviceaccount.com`, only on Cloud Run service
  `verity`;
- `roles/iam.serviceAccountOpenIdTokenCreator` to
  `user:ziyadazzazdesigner@gmail.com`, only on the `verity-pubsub` service account.

Both policies were read back before waiting. Each contained exactly one binding, exactly one
member, its intended role, and no condition. The canonical audience remained
`https://verity-7pauedpknq-uc.a.run.app`. The measured propagation wait was **60.007 seconds**.

## Bounded token mint

### Attempt 1

The first direct IAM Credentials `generateIdToken` call returned HTTP 403. The complete captured
API error body, excluding no fields, was:

```json
{
  "error": {
    "code": 403,
    "message": "Permission 'iam.serviceAccounts.getOpenIdToken' denied on resource (or it may not exist). Remediate access with this Troubleshooter URL or share it with your administrator - https://console.cloud.google.com/iam-admin/troubleshooter/summary;errorId=CiQwMWEwNGE2MS0yZjk4LTczMTQtYmEwOC1hNjI4NTZlZTg5Y2QSAA%3D%3D .",
    "status": "PERMISSION_DENIED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
        "reason": "IAM_PERMISSION_DENIED",
        "domain": "iam.googleapis.com",
        "metadata": {
          "permission": "iam.serviceAccounts.getOpenIdToken",
          "error_info_id": "CiQwMWEwNGE2MS0yZjk4LTczMTQtYmEwOC1hNjI4NTZlZTg5Y2QSAA==",
          "troubleshooter_url": "https://console.cloud.google.com/iam-admin/troubleshooter/summary;errorId=CiQwMWEwNGE2MS0yZjk4LTczMTQtYmEwOC1hNjI4NTZlZTg5Y2QSAA%3D%3D"
        }
      }
    ]
  }
}
```

This was exactly the authorized retry condition. The sequence waited 15 seconds once.

### Attempt 2

The second direct call succeeded. No third mint was attempted. Local JWT validation, without
printing the token, confirmed:

```text
audience match: true
email match: true
```

The same token was then used for both client requests.

## Side-by-side client results

### Client 1 — Invoke-WebRequest

- Method/path: `GET /healthz`
- Redirects: disabled
- Result: **HTTP 404**
- Body: Google's generic `Error 404 (Not Found)!!1` HTML, including
  `The requested URL /healthz was not found on this server.`
- Verity JSON: absent

### Client 2 — curl.exe with OS-temp configuration

- Method/path: `GET /healthz`
- Token: the exact same token used by `Invoke-WebRequest`
- Curl process exit: 0
- Reported HTTP status: **404**
- Body: the same Google generic 404 HTML and the same `/healthz` not-found text
- Verity JSON: absent

The curl configuration existed only under the resolved operating-system temporary directory. It
was overwritten, deleted, and confirmed absent immediately after the request. The token never
appeared in process arguments, output, Markdown, or Git, and in-memory token variables were
cleared.

## Interpretation

This is the decisive comparison that earlier attempts did not provide: two independent Windows
HTTP clients sent the same method, URL, and validated bearer token back to back. Both received the
same Google-front-end 404 body. The curl/config-file construction hypothesis is therefore
**conclusively ruled out**.

The two requests were absent from the revision's request logs. This matches the earlier observed
front-end failure boundary and supplies no evidence that either request reached the Verity ASGI
application.

Because neither client returned real HTTP 200 Verity JSON, the conditional Phase 7 continuation
was not triggered. The previously proposed minimal diagnostic ASGI image is now justified as the
next engineering experiment, but it remains a separately authorized build and was not started.

## Cleanup and final state

| Resource or boundary | Final state |
|---|---|
| Temporary OpenID Token Creator | Removed; command exit 0; policy read-back empty |
| Temporary service Run Invoker | Removed; command exit 0; policy read-back empty |
| Curl token configuration | Overwritten, deleted, confirmed absent |
| `verity` | Private, Ready `verity-00009-ltc`, 100% traffic |
| Image/configuration | Unchanged; pinned digest and image defaults |
| `verity-worker` subscription | Absent |
| Phase 7 delivery gates | Not executed |
| `allUsers` / Phase 8 | Absent / closed |

## Cost record

Projected incremental cost was effectively `$0.00`. Actual observed activity was four IAM policy
mutations, two IAM Credentials calls, two edge HTTP requests, and read-only verification. There
was no new revision, build, image, running job, model call, database operation, or Pub/Sub
delivery. The requests did not appear in revision logs and min instances remained zero. No posted
charge was available in real time; the closest observable incremental cost remains `$0.00`. No
billing resource or configuration was accessed or changed.

## Professional assessment and next approval gate

Do not spend another cycle changing local HTTP clients, token files, audiences, IAM roles, service
names, or Cloud Run routing flags. Those variables now have direct negative controls and repeated
evidence.

The highest-value next step is one immutable minimal-ASGI diagnostic image, starting with the
smallest Uvicorn/FastAPI health application and adding Verity's dependency/import/startup layers
incrementally. That build must be explicitly authorized before execution. Phase 7 remains stopped
until a private request returns real Verity HTTP 200 JSON, and Phase 8 remains separately gated.

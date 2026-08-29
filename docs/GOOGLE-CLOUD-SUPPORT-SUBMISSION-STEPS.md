# Google Cloud Support Submission — Exact Owner Steps

## What you need to do

Submit one technical Cloud Run case using the prepared evidence. Do not purchase or change a
support plan, billing account, payment method, budget, or quota. If the Console says this account
cannot create a technical case, stop and send a screenshot of that message; do not select a paid
upgrade.

## Before opening the form

1. Sign in to Google Cloud Console as `ziyadazzazdesigner@gmail.com`.
2. Select project **`verity-506800`** in the top project selector.
3. Keep both diagnostic services running privately. Do not delete, redeploy, expose, or change
   their IAM:
   - `verity-asgi-diagnostic` in `us-central1`;
   - `verity-asgi-diagnostic-east1` in `us-east1`.
4. Do not open `.env`, copy a token, or attach any credential file.
5. Open the prepared case text in VS Code:
   [GOOGLE-CLOUD-SUPPORT-CASE-DRAFT-2026-08-29.md](GOOGLE-CLOUD-SUPPORT-CASE-DRAFT-2026-08-29.md).

## Open the case form

1. Go to:
   `https://console.cloud.google.com/support/cases?project=verity-506800`
2. Click **Get help** or **Create case**.
3. Make sure the selected resource/project is `verity-506800`.
4. Choose **Technical support** and product **Cloud Run**.
5. If the Console offers only Billing support or asks you to upgrade a plan, stop. Take a
   screenshot and send it back; do not change the plan.

## Paste these case fields

### Title

```text
Private Cloud Run custom container returns unlogged GFE 404 despite valid OIDC and internal /healthz 200
```

### Product and location

- Product: **Cloud Run**
- Primary region: **us-central1**
- Additional reproduced region: **us-east1**
- Primary service: **verity-asgi-diagnostic**
- Primary revision: **verity-asgi-diagnostic-00003-k6r**
- Control service: **verity-asgi-diagnostic-east1**
- Control revision: **verity-asgi-diagnostic-east1-00001-pf5**

### Impact

```text
This blocks the private health and OIDC delivery gates for a time-sensitive hackathon production deployment. There are no public end users yet, and we have not weakened IAM or exposed the service to work around the failure. Google's sample container works in the same project, but our minimal six-line FastAPI/Uvicorn image reproduces the failure in two regions.
```

### Expected behavior

```text
A Google-signed service-account ID token with aud equal to the service's exact status.url and an identity holding service-level roles/run.invoker should receive HTTP 200 and {"status":"ok","diagnostic":"minimal-fastapi-uvicorn"} from GET /healthz.
```

### Actual behavior

```text
The authenticated external request receives Google's generic HTML HTTP 404: "The requested URL /healthz was not found on this server." The request does not appear in Cloud Run request logs or Uvicorn access logs. In the same Ready revision, Cloud Run's internal startup probe reaches GET /healthz, receives HTTP 200, and is logged by Uvicorn. The result reproduces with explicit gen2 in us-central1 and with the identical pinned image/configuration in us-east1.
```

### Reproduction summary

```text
1. Deploy image digest sha256:20c31500e1c946e4296b4463890438c72cd11b558e2d37178c07492f36dd398e privately with corrected HTTP startup-probe timing.
2. Confirm Ready=True, 100% traffic, Uvicorn listening on 0.0.0.0:8080, and internal startup-probe GET /healthz HTTP 200.
3. Grant only the caller service account roles/run.invoker on that service.
4. Temporarily grant the human operator roles/iam.serviceAccountOpenIdTokenCreator only on the caller service account.
5. Wait at least 60 seconds, call IAM Credentials generateIdToken with audience equal to exact status.url and includeEmail=true, and verify aud/email/email_verified claims locally.
6. Send one Authorization: Bearer request to status.url/healthz.
7. Observe generic Google HTTP 404 and no corresponding revision request/Uvicorn log.
8. Remove both temporary grants and verify both policies are empty.
9. Repeat with explicit gen2 and then in us-east1: same result.
```

### Priority

Choose **P2** only if the form's definition includes inability to bring up a time-sensitive
production system with moderate business impact. Otherwise choose **P3**. Do not choose P1: there
is no current public production outage or safety incident.

### Category

Choose the closest available path to:

```text
Cloud Run > Service invocation / request routing / authenticated private service
```

Do not categorize it only as a deployment failure: both diagnostic revisions are Ready and their
internal startup probes pass.

## Description and attachments

1. Paste the full contents of
   [GOOGLE-CLOUD-SUPPORT-CASE-DRAFT-2026-08-29.md](GOOGLE-CLOUD-SUPPORT-CASE-DRAFT-2026-08-29.md)
   into the long description or investigation-details field.
2. Attach these records if the form permits Markdown:
   - [WORKLOG-2026-08-29-GEN2-AND-REGION-ISOLATION.md](WORKLOG-2026-08-29-GEN2-AND-REGION-ISOLATION.md)
   - [WORKLOG-2026-08-29-HTTP-PROBE-AND-MINIMAL-ASGI.md](WORKLOG-2026-08-29-HTTP-PROBE-AND-MINIMAL-ASGI.md)
   - [WORKLOG-2026-08-29-SAME-TOKEN-CLIENT-COMPARISON.md](WORKLOG-2026-08-29-SAME-TOKEN-CLIENT-COMPARISON.md)
3. If `.md` is rejected, save a **copy** as `.txt` or export the rendered Markdown to PDF. Do not
   rename or edit the repository originals.
4. Never attach `.env`, gcloud credential files, access/ID tokens, API keys, billing identifiers,
   temporary curl configs, or screenshots containing secrets.
5. Prefer email/written support if offered so the timestamps and technical evidence stay exact.

## Submit and send back these details

1. Review the title, project, product, regions, impact, and attachments.
2. Click **Submit**.
3. Open the submitted case and copy only:
   - case ID;
   - status;
   - selected priority;
   - the first support response or requested diagnostic commands.
4. Send those details back in chat. Do not send tokens, cookies, credentials, or `.env` contents.
5. If support asks for a redeployment, public IAM, broader service-account role, billing change,
   or destructive cleanup, do not execute it immediately; send the request back for a scoped
   safety review first.

## If technical case creation is unavailable

Do not buy or modify a support plan. Send a screenshot of the unavailable/eligibility message.
The next safe option is to prepare a sanitized public Cloud Run issue using the official Cloud Run
support route, but do not publish the current case draft publicly without review because it names
the project, services, regions, revisions, and URLs.

## Professional recommendation

Submit the case for documentation and possible response, but do not make the hackathon schedule
depend on support turnaround. The next project decision should be a separately reviewed fallback
hosting/submission plan. Phase 8 remains closed until a private health proof returns real Verity
JSON and the remaining Phase 7 OIDC gates pass.

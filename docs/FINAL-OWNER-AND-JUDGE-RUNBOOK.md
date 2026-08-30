# Verity final owner and judge runbook

**Current as of:** 2026-08-30

**Purpose:** one start-to-finish guide for the owner, demo recording, Devpost submission, and judges

**Security rule:** this document contains no secret value

## The final links

| Purpose | Link |
|---|---|
| **Hosted Verity application** | <https://verity-7pauedpknq-uc.a.run.app> |
| **Public health evidence** | <https://verity-7pauedpknq-uc.a.run.app/health> |
| **Live architecture page** | <https://verity-7pauedpknq-uc.a.run.app/architecture> |
| **Source repository** | <https://github.com/ZiyadAzzaz/verity> |
| **Public verdict reports** | <https://github.com/ZiyadAzzaz/verity-reports/issues> |
| **Latest successful CI run** | <https://github.com/ZiyadAzzaz/verity/actions/runs/33286508908> |

The hosted application is the final URL to put in the Devpost **Try it out / Hosted project**
field. The repository URL is the final source-code link. The architecture page is a useful direct
link in the project description, but the repository architecture image should also be submitted
where Devpost asks for an image.

## What the owner should do now

Do these in order. They do not require another deployment.

1. Open a private/incognito browser window and load the hosted application.
2. Open `/health`; confirm it returns JSON with `"status":"ok"` and the cloud adapters.
3. Open `/architecture`; confirm it describes the deployed system, not a design target.
4. On the app, paste **only the judge testing key** into **Verity API key**.
5. Select a TRY ONE source, preferably **ResNet paper**, and start verification.
6. Let the result finish or return from durable cache. Open its GitHub Issue link.
7. Open the repository and the four evidence Issues below in the same signed-out browser.
8. Capture the five owner-only Google Cloud Console screenshots by following
   [CONSOLE-SCREENSHOTS.md](assets/cloud-evidence/CONSOLE-SCREENSHOTS.md).
9. Record the demo using the four-minute outline in this document.
10. Complete the Devpost fields and test every submitted link one final time while signed out.

Recommended evidence Issues:

- [Issue #8 — no verifiable claim found](https://github.com/ZiyadAzzaz/verity-reports/issues/8)
- [Issue #9 — ResNet could not verify honestly](https://github.com/ZiyadAzzaz/verity-reports/issues/9)
- [Issue #10 — executed but inconclusive](https://github.com/ZiyadAzzaz/verity-reports/issues/10)
- [Issue #12 — post-fix end-to-end cloud proof](https://github.com/ZiyadAzzaz/verity-reports/issues/12)

## The exact instructions to give a judge

The judge needs the hosted link and the dedicated `VERITY_JUDGE_TEST_KEY`. Never give a judge the
owner `VERITY_API_KEY`.

Copy this text into a **confirmed-private** testing-instructions field or organizer-approved
private channel:

> Open https://verity-7pauedpknq-uc.a.run.app in a modern browser. Paste the separately supplied
> judge key into “Verity API key.” Choose a TRY ONE source or paste a public GitHub, arXiv, or
> vendor URL, then select “Start verification.” Follow the Parser, Environment, Debug, and
> Reporter trace. When the job reaches a terminal verdict, open “View detailed analysis” to see
> the durable public GitHub Issue. A previously completed URL can return immediately with
> `cached=true`; this demonstrates Firestore-backed deduplication rather than a fake run.

Do **not** paste the key into:

- a public Devpost description;
- GitHub, README, an Issue, or source code;
- the demo video or a screenshot;
- chat, email, or any field whose visibility has not been confirmed.

If Devpost's testing-instructions field is public or its visibility is uncertain, put only the
instructions there and ask the organizer for a private credential-delivery channel. Do not solve
the ambiguity by publishing the key.

### How the owner obtains the judge key safely

If the owner already has `VERITY_JUDGE_TEST_KEY` in local `.env`, use that value without printing
or screen-recording it. If not, use a signed-in Google Cloud Console:

1. Select project `verity-506800`.
2. Open **Security → Secret Manager**.
3. Open secret `verity-judge-test-key`.
4. Open the latest enabled version and select **View secret value**.
5. Copy it only while screen recording and screen sharing are off.

The live service reads its judge credential from Secret Manager. It does not read the laptop's
`.env` file.

## Browser test: expected results

| Test | Expected result |
|---|---|
| Open `/` without a key | UI loads |
| Open `/health` without a key | HTTP 200, JSON, cloud profile |
| Open `/architecture` without a key | Current deployed architecture |
| Submit without a key | HTTP 401 / invalid API key |
| Submit with the judge key | HTTP 202 for a new job, or a completed cached result |
| Poll a valid job with the judge key | Trace and terminal verdict |
| Open `issue_url` | Public Issue in `verity-reports` |

The public UI and documentation are intentionally readable without authentication. Creating and
reading job records through the API requires `X-Verity-Key`. Public exposure therefore does not
mean anonymous users can spend the project's Vertex AI or Cloud Run Job budget.

## Optional direct API test

The browser is the preferred judge path. For an API client, keep the judge key in a process
environment variable and never put it in the URL, JSON body, shell history, or output:

```powershell
$base = 'https://verity-7pauedpknq-uc.a.run.app'
$headers = @{ 'X-Verity-Key' = $env:VERITY_JUDGE_TEST_KEY }
$body = @{ url = 'https://arxiv.org/abs/1512.03385' } | ConvertTo-Json

$submission = Invoke-RestMethod -Method Post -Uri "$base/api/jobs" `
  -Headers $headers -ContentType 'application/json' -Body $body

do {
  Start-Sleep -Seconds 3
  $result = Invoke-RestMethod -Method Get `
    -Uri "$base/api/jobs/$($submission.job_id)" -Headers $headers
  $result.job.status
} while ($result.job.status -notin @('completed', 'failed'))

$result.job.verdict | ConvertTo-Json -Depth 10
Remove-Item Env:VERITY_JUDGE_TEST_KEY -ErrorAction SilentlyContinue
```

Do not repeatedly resubmit a running URL. Poll the returned job ID. The completed object includes
the typed claim, evidence, verdict, confidence, trace, and `issue_url` when reporting succeeded.

## What the reports are and where to see them

The `verity-reports` repository is the public audit trail. For each new non-cached completed job,
the Reporter opens one structured GitHub Issue. The Issue records what Verity understood, what it
executed, what it observed, every bounded repair attempt, the final verdict, and confidence.

You can reach a report in three ways:

1. from **View detailed analysis** in the web UI;
2. from `job.verdict.issue_url` in the API response;
3. from <https://github.com/ZiyadAzzaz/verity-reports/issues>.

A cached replay points to the original durable Issue instead of filing a duplicate. Opening or
modifying Issues in `verity-reports` is operational output and should remain deliberate; ordinary
code pushes to `verity/main` are a separate workflow.

## What Verity does from start to finish

1. **Input:** a user submits a public research, repository, or vendor URL.
2. **Authentication and validation:** the public Cloud Run API validates the dedicated key and
   URL, then creates or finds a Firestore job.
3. **Deduplication:** a completed canonical URL returns its durable result instead of spending
   money on a duplicate run.
4. **Queueing:** Pub/Sub delivers the job to a private Cloud Run pipeline worker with Google OIDC.
5. **Parser:** a typed Google ADK agent extracts a precise, testable claim and its conditions.
6. **Environment:** deterministic Python prepares a bounded execution specification. This is
   deterministic by design because model reasoning is unnecessary here.
7. **Sandbox:** the trusted worker starts a separate `verity-sandbox` Cloud Run Job. Its service
   account has no project roles and receives no application, Google, or GitHub credential.
8. **Debug:** a typed ADK agent analyzes failure evidence and can make at most three transparent,
   bounded repair attempts.
9. **Reporter:** deterministic Python compares claimed and observed values, persists the trace,
   and files the public Issue. Determinism here prevents a model from inventing the final number.
10. **Result:** the UI and API show one of the honest terminal outcomes and the evidence link.

The architecture is therefore:

```text
Browser / API client
        |
        v
Public Cloud Run API -- Firestore durable memory
        |
        v
Pub/Sub with OIDC --> Private pipeline Cloud Run Job
                          |          |
                          |          +--> Vertex AI / typed ADK Parser and Debug agents
                          v
                 No-role sandbox Cloud Run Job
                          |
                          v
                    bounded stdout evidence
                          |
                          v
                 deterministic Reporter --> public GitHub Issue
```

This uses real typed Google ADK agents where reasoning helps—Parser and Debug—and deterministic
Python where correctness and reproducibility matter more—Environment and Reporter. The project
does not add an agent framework to steps that do not need model reasoning.

## Security story to tell the judge

- Public reads are open; job submission and job data require separate owner/judge keys.
- Keys and the GitHub credential are Secret Manager references, not image or Git content.
- Pub/Sub invokes the private worker with an audience-bound Google OIDC token.
- The public API does not receive broad control-plane permissions.
- The sandbox identity has no project roles and no credentials.
- A live six-API probe proved the sandbox received explicit 401/403 responses for Firestore,
  Secret Manager, Pub/Sub, Cloud Run execution, Vertex AI listing, and Cloud Storage listing.
- The sandbox returns one bounded stdout artifact; the trusted worker owns persistence and
  reporting.
- Repair is capped at three attempts and all attempts are visible.
- The system is allowed to say `inconclusive`, `could_not_verify`, or
  `no_verifiable_claim_found`; it never turns missing evidence into success.

## Honest verdict status

The cloud evidence contains three genuine outcome types:

- `no_verifiable_claim_found`;
- `could_not_verify`;
- `inconclusive`.

There is not yet an honest live-cloud `verified` result. Local deterministic fixtures exercise
the `verified` path. This is a strength of the evidence policy, not something to hide: Verity did
not invent a green result for the submission. Large evaluations such as full BERT-style runs can
also exceed the intentionally small sandbox time and dependency budget.

## Four-minute demo recording plan

The hackathon rules cap the demo at four minutes, so keep the story tight.

### 0:00–0:25 — problem and promise

“Published benchmark claims are easy to repeat and hard to reproduce. Verity turns a URL into a
bounded, evidence-backed verification trace, and it is allowed to refuse unsupported success.”

### 0:25–1:10 — live public product

- Show the `.run.app` URL in the address bar.
- Paste the judge key with the recording cropped or the field already filled and masked.
- Submit the ResNet TRY ONE chip.
- Show the live trace or durable cached replay.

Never let the secret value appear in a frame.

### 1:10–2:10 — strongest evidence

- Open Issue #9 from the result.
- Point out the extracted 5.71% claim and conditions.
- Show the three bounded attempts and that no reproduced value was fabricated.
- Briefly show Issues #8 and #10 to establish multiple honest outcomes.

### 2:10–3:10 — architecture and security

- Open `/architecture`.
- Explain API → Firestore/Pub/Sub → private pipeline → no-role sandbox → Reporter.
- Show one signed-in Console screenshot of the pipeline execution and one of its nested sandbox.
- State that Parser and Debug are typed ADK agents, while Environment and Reporter are
  deterministic by design.

### 3:10–3:50 — Google Cloud proof and differentiation

- Show Cloud Run serving the current revision and Firestore/Logs evidence.
- Explain durable deduplication by replaying the same URL and showing `cached=true`.
- End on the public Issue link: the result is independently inspectable after the run.

### 3:50–4:00 — closing line

“Verity does not promise every claim is true. It promises that every verdict is traceable to
what actually ran.”

Record an unedited product interaction. A cached replay is a real live API/dedup action, but make
the stored full execution trace and Cloud Run evidence visible so the judge can distinguish it
from a static mock. Do not start an unbounded last-minute source search solely for a cosmetic
`verified` badge.

## Devpost submission checklist

- Project name and concise problem statement.
- Public GitHub repository link.
- Hosted `.run.app` application link.
- Architecture diagram image from the repository, plus the live architecture page if useful.
- Public YouTube or Vimeo demo, no longer than four minutes.
- Clear Google Cloud proof in the video: the `.run.app` URL and signed-in Console evidence.
- Testing instructions with the judge key only through a confirmed-private channel.
- Disclosure that Parser and Debug use Google ADK/Vertex AI and deterministic stages protect
  execution and reporting integrity.
- Attributions and open-source license already present in the repository.
- Every link tested in a signed-out window immediately before submission.

Official contest references:

- [Rules](https://allthingsagentichackathon.devpost.com/rules)
- [FAQ](https://allthingsagentichackathon.devpost.com/details/faqs)
- [Hackathon page](https://allthingsagentichackathon.devpost.com/)

## Will the link always remain available?

No hosted URL is guaranteed forever. The current Cloud Run URL should remain usable while all of
these remain true:

- project `verity-506800` remains active;
- its billing account remains active;
- service `verity` is not deleted or renamed;
- public Run Invoker access and the current ingress configuration remain in place;
- the backing secrets and APIs remain available;
- no owner intentionally disables the service.

Cloud Run can scale a service to zero when it has no traffic. The current service has no minimum
instance setting and has a maximum of two instances, so it is designed to scale to zero rather
than keep a warm instance permanently. A cold request may therefore be slower. The current
revision also has CPU throttling disabled, so compute can accrue for an instance's whole
lifecycle while that instance exists; do not describe its billing as strictly “only per request.”

The contest requires clear proof that the project was built and deployed on Google Cloud. The
official FAQ says that proof can be captured in the demo and repository before infrastructure is
later turned off. Keeping the URL live is still strongly recommended for judge convenience, but
it is not a promise of permanent hosting.

## Does keeping it live need money?

Potentially, yes—but a quiet scale-to-zero deployment should be inexpensive. Cost can come from:

- Cloud Run API instances while starting or serving requests;
- new pipeline and sandbox Cloud Run Job executions;
- Vertex AI model calls for new claims;
- Artifact Registry image storage;
- Firestore reads, writes, and retained storage;
- Pub/Sub delivery;
- Secret Manager active versions and access operations;
- future Cloud Build submissions.

Several products have free monthly allowances, but free allowance does not mean a permanent
zero-cost guarantee. The relevant official pages are:

- [Cloud Run pricing](https://cloud.google.com/run/pricing)
- [Cloud Run billing settings](https://cloud.google.com/run/docs/configuring/billing-settings)
- [Firestore pricing](https://cloud.google.com/firestore/pricing)
- [Pub/Sub pricing](https://cloud.google.com/pubsub/pricing)
- [Secret Manager pricing](https://cloud.google.com/secret-manager/pricing)
- [Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing)
- [Cloud Build pricing](https://cloud.google.com/build/pricing)
- [Vertex AI generative AI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)

The verified account context is approximately **$450 available credit**: the Google Cloud
no-cost trial plus the $150 hackathon grant on one billing account. The project target remains
approximately $25, with a stop-and-check-in gate if one action is projected above $10 or
cumulative spend crosses $50. Current project evidence describes usage as single-digit dollars,
not an invoice; only the signed-in Billing Console is authoritative for the real total.

Google's current general free-trial documentation says that if a trial billing account is not
upgraded before its credit or time expires, the account closes and its resources stop, followed
by a limited recovery period. Therefore:

- no billing change is required merely to submit or record the demo now;
- do not assume the URL will survive trial expiration automatically;
- if the owner wants availability beyond the trial, they must make their own billing-continuity
  decision in Google Cloud before expiration;
- Verity automation and agents must never modify billing, payment, budgets, quotas, or plans.

Official reference: [Google Cloud Free Program](https://cloud.google.com/free/docs/free-cloud-features).

## Why local `.env` remains local while cloud is production

This is correct and intentional:

```text
Laptop .env                  Cloud Run configuration
-------------------------    ---------------------------------
VERITY_ENV=local             VERITY_ENV=cloud
development profile          production profile
SQLite                       Firestore
in-process queue             Pub/Sub
Docker sandbox               Cloud Run Job sandbox
AI Studio key                Vertex AI identity
local secrets                Secret Manager references
```

The `.env` file is ignored by Git and is read only by local processes. Cloud Run does not upload
or read it. Changing local `.env` to `cloud` would not update production; it would only make the
local program try to use cloud adapters. Keep real values out of `.env.example`, Git, Issues,
screenshots, videos, and documentation.

## Project story from start to finish

1. Verity began as a local-first four-role verification pipeline with a FastAPI UI, durable
   traces, Docker isolation, and honest terminal verdicts.
2. A security audit found that the original cloud design could expose project credentials to
   untrusted evaluation code. Production deployment was deliberately blocked until that was
   fixed.
3. The system was refactored behind interfaces so SQLite/in-process/Docker local adapters and
   Firestore/Pub/Sub/Cloud Run cloud adapters follow the same contracts.
4. A live no-role sandbox probe tested six Google Cloud APIs and proved every attempt was denied
   with explicit 401/403 evidence.
5. Packaging and worker-launch defects were fixed, including a regression test proving the
   worker's job ID reaches `_run(job_id)`.
6. Private production phases deployed immutable images, service accounts, secrets, Firestore,
   Pub/Sub, API service, and worker/jobs with least privilege.
7. A long health diagnostic identified Cloud Run's reserved `/healthz` path behavior. The route
   and startup probe moved to `/health`, after which private health and OIDC gates passed.
8. Public access was enabled only after private health, unauthenticated rejection, wrong-audience
   rejection, exact IAM, and image-digest evidence passed.
9. Live multi-source proof uncovered and fixed real production defects: operation-metadata
   permissions, execution timing, Unicode command handling, nested Firestore arrays, and
   misleading TRY ONE labels.
10. The final public pages were cache-hardened and independently fetched to prove that the live
    homepage and architecture content match the corrected source.

Current state: the application is public, the write API remains key-protected, Cloud Run serves
revision `verity-00019-nfl` at 100% traffic, Git local and `origin/main` are synchronized, and CI
is green. Commit `a8f2997` is the verified deployed-content baseline; the final runbook was added
afterward as a documentation-only change and did not redeploy the service.

## Troubleshooting

| Symptom | Action |
|---|---|
| Page looks old | Use an incognito window and a cache-busting query. Current pages send `Cache-Control: no-store, max-age=0`. |
| Submit says invalid API key | Confirm the dedicated judge key was copied without spaces and has not been rotated. Never switch to the owner key as a shortcut. |
| Result appears immediately | Check `cached=true`; this is expected Firestore deduplication. |
| Job is still running | Poll the same job ID. Do not resubmit it. Large evaluations can reach the bounded timeout. |
| No Issue link | Inspect the Reporter trace; a cached result should retain its original Issue. Do not manually invent a report. |
| Cold first request | Wait briefly and retry the read once; scale-to-zero can add startup latency. Do not launch repeated submissions. |
| Hosted link stops after trial expiry | Use recorded/repository cloud proof; only the owner can decide whether to continue billing. Do not let automation alter billing. |

## Final professional recommendation

Do not change the architecture again before submission. The highest-value remaining owner work is
the five Console screenshots, a concise four-minute demo, safe judge-key delivery, Devpost copy,
and one signed-out link check. Lead with the no-role sandbox and the system's refusal to fabricate
verification: those are more credible and differentiated than chasing a last-minute green badge.

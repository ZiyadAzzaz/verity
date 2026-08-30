# Verity judge handoff

**Current as of:** 2026-08-30  
**Hosted application:** <https://verity-7pauedpknq-uc.a.run.app>  
**Architecture:** <https://verity-7pauedpknq-uc.a.run.app/architecture>  
**Public verdicts:** <https://github.com/ZiyadAzzaz/verity-reports/issues>

This is the practical handoff for testing the deployed system. It contains no credential value.
The owner must give a judge the dedicated judge key through a confirmed-private testing-
instructions channel, never through GitHub, a screenshot, a demo recording, or public Markdown.
If the Devpost field is publicly visible, use an organizer-approved private channel instead.

## What is public and what needs the key

| Action | Authentication | Expected result |
|---|---|---|
| Open `/` | None | Interactive Verity UI |
| `GET /health` | None | HTTP 200 and the active cloud adapters |
| Open `/architecture` | None | Current deployed architecture |
| `POST /api/jobs` | `X-Verity-Key` | HTTP 202 and a job ID |
| `GET /api/jobs/{job_id}` | `X-Verity-Key` | Job, verdict, and complete trace |
| Open a returned GitHub Issue | None | Public, durable detailed report |

The deployed service has two simultaneous keys:

- `VERITY_API_KEY` is the owner's operational credential.
- `VERITY_JUDGE_TEST_KEY` is a separate, independently revocable judge credential.

Both are accepted with constant-time comparison. The live service maps its judge key from Secret
Manager secret `verity-judge-test-key`; it does not source it from the workstation `.env`, image,
Git, or documentation. A local `.env` may hold the owner's copy because Git ignores that file.
Removing or rotating the cloud judge secret does not require rotating the owner's key.

## Simplest judge path: the browser UI

1. Open <https://verity-7pauedpknq-uc.a.run.app>.
2. Paste the separately supplied judge key into **Verity API key**.
3. Choose a **TRY ONE** source or paste a public arXiv, GitHub, or vendor URL.
4. Select **Start verification**.
5. Watch the durable trace progress through Parser, Environment, Debug, and Reporter.
6. At a terminal verdict, open **View detailed analysis (GitHub Issue)**.

The example chips intentionally name sources, not promised outcomes. Verity does not decide what
the evidence will say before it runs. Re-submitting a previously completed URL may return the
durable Firestore result immediately with `cached=true`; that is the designed deduplication path.

## Exact API path

Use the judge key only in a local environment variable. The following PowerShell keeps it out of
the URL and request body:

```powershell
$base = 'https://verity-7pauedpknq-uc.a.run.app'
$headers = @{ 'X-Verity-Key' = $env:VERITY_JUDGE_TEST_KEY }
$submitted = Invoke-RestMethod -Method Post -Uri "$base/api/jobs" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"url":"https://arxiv.org/abs/1512.03385"}'
$submitted

$view = Invoke-RestMethod -Method Get -Uri "$base/api/jobs/$($submitted.job_id)" `
  -Headers $headers
$view
```

Poll the returned status URL at a modest interval until `job.status` is `completed` or `failed`.
Do not blindly resubmit a running job. A completed response contains the typed claim, verdict,
confidence, trace, and `issue_url` when the Reporter successfully filed the artifact.

For a harmless authentication check, omit the key from a submission: the expected response is
HTTP 401. `GET /health` should remain HTTP 200 without a key.

## Where the reports are

The Reporter files one public GitHub Issue per completed, non-cached live job in
[`ZiyadAzzaz/verity-reports`](https://github.com/ZiyadAzzaz/verity-reports/issues). The UI links the
Issue in both the verdict summary and Artifact cell; the API returns the same URL as
`job.verdict.issue_url`.

Strong current examples are:

| Evidence | Live outcome | Why it matters |
|---|---|---|
| [Issue #8](https://github.com/ZiyadAzzaz/verity-reports/issues/8) | `no_verifiable_claim_found` | Refuses to treat a popularity statistic as a reproducible benchmark |
| [Issue #9](https://github.com/ZiyadAzzaz/verity-reports/issues/9) | `could_not_verify` | Extracts ResNet's exact claim and conditions, tries three times, and invents no value |
| [Issue #10](https://github.com/ZiyadAzzaz/verity-reports/issues/10) | `inconclusive` | Runs the evaluation but refuses an unsupported conclusion |
| [Issue #12](https://github.com/ZiyadAzzaz/verity-reports/issues/12) | `could_not_verify` | End-to-end proof of the Firestore nested-command fix |

There is no honest live-cloud `verified` result yet. The bounded search is complete, and the UI
does not pretend otherwise. Local fixtures demonstrate `verified`; the cloud evidence currently
demonstrates three distinct honest outcomes.

## Why `.env` should still say `local`

The repository's `.env` is a workstation file and is ignored by Git. It selects the local demo:
SQLite, an in-process queue, Docker isolation, and AI Studio. It should normally contain:

```ini
VERITY_ENV=local
VERITY_ENVIRONMENT=development
GEMINI_API_KEY=<local AI Studio key>
```

The live deployment separately has `VERITY_ENV=cloud` and
`VERITY_ENVIRONMENT=production` in Cloud Run configuration. It maps the API, judge, and GitHub
credentials by Secret Manager reference. Cloud Run never reads the workstation `.env`, so the
two settings do not conflict. Changing the local file to `cloud` would not update production; it
would only make a local process attempt to use cloud adapters.

## Owner-only submission checklist

1. Provide the judge key only in a testing-instructions field whose visibility is confirmed to be
   judges-only, or through an organizer-approved private channel.
2. Do not use the owner API key in Devpost or the demo.
3. Capture the five signed-in Console views in
   [CONSOLE-SCREENSHOTS.md](assets/cloud-evidence/CONSOLE-SCREENSHOTS.md).
4. Verify the repository, hosted application, architecture, and evidence Issue links in a signed-
   out browser.
5. Keep the scale-to-zero service live throughout the judging period; do not include it in an
   early cleanup pass.
6. After judging, rotate or remove only the judge-key secret if access should end.

## Professional recommendation

Lead the judge through Issue #9, then show a cached re-submission. That sequence demonstrates the
project's strongest differentiators in minutes: typed ADK reasoning, real isolated execution,
bounded transparent repair, refusal to fabricate success, durable Firestore memory, and an
autonomously filed public artifact. Do not spend the remaining submission window hunting for a
cosmetic green verdict; finish the Console screenshots, Devpost copy, and demo recording.

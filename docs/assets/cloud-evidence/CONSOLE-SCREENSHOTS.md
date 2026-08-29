# Console screenshots — capture guide

Everything reachable without a login is already captured in this directory. The five shots
below live behind the Google Cloud Console's signed-in session, so they have to be taken from
a logged-in browser. Each link goes straight to the page; the "show" column is what has to be
visible in frame for the shot to be worth anything.

| # | File to save as | Page | Must show |
|---|---|---|---|
| 1 | `console-cloud-run-service.png` | [Cloud Run › verity](https://console.cloud.google.com/run/detail/us-central1/verity/metrics?project=verity-506800) | Green **Ready**, the live `https://verity-7pauedpknq-uc.a.run.app` URL, revision `verity-00013-l7n` |
| 2 | `console-pipeline-execution.png` | [Job › verity-pipeline executions](https://console.cloud.google.com/run/jobs/details/us-central1/verity-pipeline/executions?project=verity-506800) | A **succeeded** execution dated today, with its duration |
| 3 | `console-sandbox-execution.png` | [Job › verity-sandbox executions](https://console.cloud.google.com/run/jobs/details/us-central1/verity-sandbox/executions?project=verity-506800) | A sandbox execution *nested inside* the same window as #2 — this is the two-tier proof |
| 4 | `console-firestore-job.png` | [Firestore › jobs](https://console.cloud.google.com/firestore/databases/-default-/data/panel/jobs?project=verity-506800) | One real job document expanded: `status`, `verdict`, `url` |
| 5 | `console-logging-trace.png` | [Logs Explorer](https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%20OR%20resource.type%3D%22cloud_run_job%22?project=verity-506800) | One request threading `POST /api/jobs` → `/internal/pubsub` → job execution |

Filed GitHub Issues are public and need no login:
<https://github.com/ZiyadAzzaz/verity-reports/issues>

## Why these five

They are the claims a reader cannot check from the repository alone. The code proves what
Verity *intends* to do; these prove the intent actually ran on Google Cloud — a public URL
serving traffic, a queue delivering it, two tiers of isolated execution, persisted state, and
a filed report.

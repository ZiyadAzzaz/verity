# Verity

Verity is an autonomous verification system for public AI/ML performance claims. It does
not summarize a paper or README and call that verification: it extracts a typed numerical
claim, runs the associated repository in a fresh sandbox, makes at most three transparent
repair attempts, and files an evidence-backed verdict as a GitHub Issue.

The durable runtime is the four-role state machine in `verity/pipeline.py`. Its Parser and
Debug model calls use typed Google ADK `LlmAgent` instances; `app/agent.py` is a declarative
view of the same roles, not a second executable pipeline. The configured model is
`gemini-3.5-flash`.

Verity runs on either of two infrastructures, chosen by a single setting:

| Seam | `VERITY_ENV=local` | `VERITY_ENV=cloud` |
|---|---|---|
| State, trace, claim memory | SQLite (`verity.db`) | Firestore |
| Intake to processing | `asyncio.Queue` | Pub/Sub |
| Model calls | Gemini via AI Studio API key | Gemini via Vertex AI |
| Untrusted execution | Docker (`docker run --rm`) | Cloud Run Jobs, no-role service account |

**The local profile needs no Google Cloud project, no billing account, and no card.** The
agents depend only on the interfaces in `verity/interfaces.py`; `verity/container.py` is
the one module that picks concrete backends.

## See it actually work

**A real verdict Verity filed on its own:
[verity-reports#1](https://github.com/ZiyadAzzaz/verity-reports/issues/1).**

It tried to reproduce the ResNet paper's 4.49% top-5 error rate, failed after three bounded
repair attempts, and reported `Reproduced: not captured` — an empty cell where a fabricated
number would otherwise sit. The Debug Agent's own reasoning, quoted from that Issue:

> *"Fabricating the metric or replacing the evaluation with a constant is strictly prohibited
> under the security and honesty rules. Therefore, no defensible fix can be proposed."*

**Run it yourself in ten minutes, without an API key:
[docs/LOCAL-DEMO.md](docs/LOCAL-DEMO.md).** Five claims ship with real cached verdicts, so a
genuine result returns instantly without a single model call.

## Documentation

| Document | Contents |
|---|---|
| [docs/STATE.md](docs/STATE.md) | **Start here** — full state, what is missing, next steps |
| [docs/SECURITY-QUALITY-REPORT.md](docs/SECURITY-QUALITY-REPORT.md) | Professional findings, remediations, validation evidence, and residual-risk report |
| [docs/SCOPED-CLOUD-SECURITY-FIX.md](docs/SCOPED-CLOUD-SECURITY-FIX.md) | Credential-free Cloud Run handoff, no-role identity gate, OIDC fix, and residual risks |
| [docs/SCOPED-SECURITY-VALIDATION-2026-08-25.md](docs/SCOPED-SECURITY-VALIDATION-2026-08-25.md) | Exact local gates, live rerun evidence, quota blocker, and cloud acceptance status |
| [docs/EMULATOR-VALIDATION-2026-08-25.md](docs/EMULATOR-VALIDATION-2026-08-25.md) | Official Firestore/Pub/Sub emulator evidence and exact remaining live-cloud gaps |
| [docs/CLOUD-LIVE-SAFETY.md](docs/CLOUD-LIVE-SAFETY.md) | Current project, $450 credit truth, ~$25 target, hard cost gates, and billing boundary |
| [docs/WORKLOG-2026-08-27-CLOUD-SANDBOX-PREPARATION.md](docs/WORKLOG-2026-08-27-CLOUD-SANDBOX-PREPARATION.md) | Complete live-cloud preparation record, stopped probe, decisions, evidence, cost, and next step |
| [docs/WORKLOG-2026-08-27-THIRD-SANDBOX-PROBE.md](docs/WORKLOG-2026-08-27-THIRD-SANDBOX-PROBE.md) | Third probe: local pre-flight, packaging assessment, five live denials, Firestore 404, cost, and decision gate |
| [docs/WORKLOG-2026-08-27-FOURTH-SANDBOX-PROBE.md](docs/WORKLOG-2026-08-27-FOURTH-SANDBOX-PROBE.md) | Passing fourth probe, Firestore creation, full preflight, exact 6/6 evidence, costs, and assessment |
| [docs/CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md](docs/CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md) | Review artifact: exact passing validator JSON bound to execution, identity, image digest, and cost |
| [docs/POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md](docs/POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md) | Prepared but unexecuted production API/pipeline deployment sequence and hard stop gates |
| [docs/GOOGLE-CLOUD-CONSOLE-INSPECTION.md](docs/GOOGLE-CLOUD-CONSOLE-INSPECTION.md) | Read-only visual checklist for project, billing, build, image, job, IAM, secret, Pub/Sub, and APIs |
| [docs/WORK-RECORD-STANDARD.md](docs/WORK-RECORD-STANDARD.md) | Required Markdown record for every future material work session |
| [docs/AUDIT-2026-08-24.md](docs/AUDIT-2026-08-24.md) | Deep code, runtime, security, deployment, and artifact audit |
| [docs/NEXT-IMPLEMENTATION.md](docs/NEXT-IMPLEMENTATION.md) | Exact evidence, recovery, secure-cloud, and staging gates |
| [docs/REVIEW.md](docs/REVIEW.md) | Historical 2026-08-23 review |
| [docs/COMPLETE.md](docs/COMPLETE.md) | Historical 2026-08-23 project record |
| [docs/LOCAL-DEMO.md](docs/LOCAL-DEMO.md) | Clone and run it yourself, no API key |
| [docs/architecture.md](docs/architecture.md) | Both profiles, trust boundaries, data model |
| `verity-architecture.html` | The presentation diagram — open in a browser |
| [docs/PRE-SUBMISSION-AUDIT.md](docs/PRE-SUBMISSION-AUDIT.md) | Historical 2026-08-23 audit |
| [docs/PROJECT-ANALYSIS.md](docs/PROJECT-ANALYSIS.md) | Historical analysis |
| [docs/HANDOVER.md](docs/HANDOVER.md) | Historical handover |

## What a result means

Each label means exactly one thing. Collapsing two outcomes into one label is the failure
mode these are designed to prevent.

- `verified`: a captured metric is within the explicit 2% comparison tolerance.
- `contradicted`: a captured metric is outside that tolerance.
- `inconclusive`: evaluation exited successfully but no attributable metric was captured.
- `conditions_not_comparable`: a value was observed, but Verity did not establish equivalent
  hardware/runtime conditions, so it asserts neither verification nor contradiction.
- `could_not_verify`: Verity genuinely attempted the evaluation and it did not reproduce.
- `no_verifiable_claim_found`: the source asserts no headline result worth checking — only
  incidental statistics like a row or feature count. **Nothing was executed.**
- `environment_incompatible`: the repository needs network access during evaluation, which
  the sandbox denies so a benchmark cannot fetch data mid-measurement. **The claim was never
  tested**; this says nothing about whether it is true.

Verity never turns missing output into a number. Every error, proposed patch, and retry outcome
is persisted under the job trace.

## Known limitations

Stated plainly, because a verification tool that oversells itself is self-defeating.

- **Claim-significance detection is a heuristic.** Verity asks the model whether a number is
  a result the source is asserting or an incidental statistic. It will not be right on every
  source. A misjudged headline claim gets skipped; a misjudged incidental one wastes a
  sandbox run. Both are visible in the verdict rather than hidden.
- **Network-isolated evaluation cannot test data-fetching pipelines.** Any repository that
  downloads its dataset at evaluation time is untestable as written. That now surfaces
  explicitly as `environment_incompatible` rather than being reported as a failed
  reproduction, but the underlying limit is real.
- **Most public claims do not reproduce on a laptop.** Model weights, private datasets, and
  multi-GPU training put a lot of legitimate research out of reach. `could_not_verify` is the
  common outcome and is not a defect.
- **The parser may extract a different claim on different runs** when a source contains
  several. Each extraction is grounded in a verbatim quote, but they are not identical
  between runs.
- **The cloud profile is deployed, but large evaluations remain bounded.** The credential-free
  sandbox identity passed a live stolen-token probe against six sensitive APIs, and Phase 9 ran
  multiple public claims end to end. Each execution still has a 900-second budget, so heavyweight
  evaluations such as BERT/GLUE can time out rather than reach a verdict.
- **Environment provenance is incomplete.** Timing/throughput/resource metrics now return
  `conditions_not_comparable`, but dataset, checkpoint, revision, hardware, and dependency
  equivalence are not yet recorded strongly enough for universal reproducibility claims.
- **Install-time code has network access.** Evaluation is offline, but Python package builds
  run during the networked install phase. Do not treat that phase as safe against LAN probing.

## Local setup (Python 3.11, no Google Cloud)

Prerequisites: Python 3.11, Docker, and a free
[Google AI Studio](https://aistudio.google.com/) API key.

```powershell
conda create -n agent-dev python=3.11 -y
conda activate agent-dev
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`scripts/bootstrap.ps1` does all of that, falls back to a plain `.venv` if conda is not
installed, and pre-builds the sandbox image. Then put your key in `.env`:

```ini
VERITY_ENV=local
GEMINI_API_KEY=<your AI Studio key>
```

Run it:

```powershell
conda activate agent-dev
uvicorn app.fast_api_app:app --reload --port 8080
```

Open `http://127.0.0.1:8080`. `GET /health` reports the active profile and any setup
problem it found at boot.

### Docker is required, not optional

The Environment Agent clones and executes arbitrary third-party code from GitHub. Verity
will not run that on your machine. Each phase of a verification is a separate
`docker run --rm` with `--cap-drop ALL`, `--security-opt no-new-privileges`, a read-only
root filesystem, pid/memory/cpu limits, no network at all during evaluation, and exactly
one bind mount: a fresh temp directory. The image is built on demand from
`Dockerfile.runner`, or ahead of time with:

```powershell
docker build -f Dockerfile.runner -t verity-sandbox-runner:1 .
```

If the daemon is not running, Verity says so as a setup error instead of falling back to
the host. `VERITY_SANDBOX_BACKEND=host_subprocess` exists for debugging Verity itself; it
is not an isolation boundary and production rejects it.

## Tests and validation gates

Check the machine is ready first — Python, dependencies, the key, and the Docker daemon,
in one command that never prints your key:

```powershell
python scripts/check_setup.py
```

Then:

```powershell
powershell -File scripts/test.ps1            # ruff + mypy + unit suite
powershell -File scripts/test.ps1 -Docker    # the above plus real container isolation
powershell -File scripts/test_emulators.ps1  # Firestore + Pub/Sub, no cloud account
```

`test.ps1` and `bootstrap.ps1` find the interpreter through `scripts/_python.ps1`, which
prefers the `agent-dev` conda environment and falls back to `.venv`. It locates conda via
`CONDA_EXE` and a scan of every drive rather than `Get-Command conda`, because `conda init`
installs itself into the PowerShell *profile* — so an interactive prompt has it but a task
runner or CI shell does not.

The unit suite covers the three input shapes (arXiv PDF, GitHub README, vendor HTML),
URL/path security, metric capture, exact three-retry honest failure, success-after-patch,
Pub/Sub decoding, SQLite reservation and restart survival, queue concurrency limits, the
`VERITY_ENV` swap, Gemini retry/backoff, and instant dedup.

`test_emulators.ps1` starts Google's official Firestore and Pub/Sub emulators from one
digest-pinned image, binds them only to loopback, runs the cloud-adapter integration tests with a
fake project ID, and removes its exact containers afterward. It uses no Google Cloud account or
credentials and is not a substitute for the live identity probe.

Local gates that use real sources, real Gemini, and real containers:

```powershell
python scripts/validate_docker_isolation.py            # every escape attempt must fail
python scripts/validate_local_pipeline.py              # 8 real claim URLs, end to end
python scripts/validate_parser_real.py
python scripts/validate_broken_repo.py
```

`validate_local_pipeline.py` runs the catalogue in `tests/data/local_claim_urls.json`:
arXiv PDFs, GitHub repositories with and without a pinned revision, and vendor pages.
Passing does **not** mean everything verified — most public claims do not reproduce on a
laptop, and several entries are there specifically to exercise the honest-failure path. It
passes when every job reaches an evidence-backed verdict and no job reports a number it did
not observe. It finishes by resubmitting the first URL and requiring an instant cached
response.

After a cloud deployment, run all seven real URLs and the cache check:

```powershell
$env:VERITY_API_KEY = '<the deployed API key>'
python scripts/validate_deployed.py 'https://YOUR-SERVICE.run.app' --timeout 3600
```

## Google Cloud status

**Verity is deployed and public:** <https://verity-7pauedpknq-uc.a.run.app>

Reading is open to anyone; submitting a claim requires `X-Verity-Key`, so an unauthenticated
`GET /health` returns 200 and an unauthenticated `POST /api/jobs` returns 401. Judges and
reviewers get a second, independently revocable key, so withdrawing their access never means
rotating the owner's.

The exact browser and API walkthrough, safe judge-key handoff, and public report locations are in
the [judge handoff](docs/JUDGE-HANDOFF.md). The key value is deliberately absent from Git and must
be supplied to judges through the private testing instructions.

A live multi-claim proof ran three genuinely different sources through the public endpoint and
produced three different verdicts, none of them served from cache:

| Source | Verdict | What it shows |
|---|---|---|
| [psf/requests](https://github.com/ZiyadAzzaz/verity-reports/issues/8) | `no_verifiable_claim_found` | "300M downloads / week" is a popularity statistic, not a reproducible benchmark |
| [arXiv 1512.03385](https://github.com/ZiyadAzzaz/verity-reports/issues/9) | `could_not_verify` | ResNet's 5.71% top-5 error read out of Table 3 with its conditions, three bounded debug attempts, no reproduced value asserted |
| [ijl/orjson](https://github.com/ZiyadAzzaz/verity-reports/issues/10) | `inconclusive` | executed, retried three times, and declined to claim a result |

Each ran as a `verity-pipeline` Cloud Run Job that started a **nested** `verity-sandbox`
execution, persisted its trace to Firestore, and filed the Issue itself. Re-submitting a URL
returns the stored verdict in about a second, including across a redeployment, because claim
memory is Firestore state rather than a container-local cache.

The sandbox never reads or writes Firestore. A bounded public request is passed through Cloud
Run execution arguments, Cloud Run collects one bounded stdout result, and only the trusted
pipeline reads that execution's logs and persists the result. The sandbox image has no Google
Cloud client; its job definition clears environment, secret, volume, and VPC attachments; and its
dedicated service account has no project or resource-level IAM binding.

The pipeline that *starts* sandbox jobs holds `roles/run.jobsExecutorWithOverrides` — `run.jobs.run`
and nothing that reads the Cloud Run API back. It takes the execution name from the operation's
metadata and recovers the result from the sandbox's own log line, so it can launch an execution
and still not query one.

**Known limit:** claims whose evaluation cannot finish inside the 900-second sandbox budget end as
an infrastructure timeout rather than a verdict. `arXiv 1810.04805` (BERT/GLUE) is one: it reaches
the debug loop and then runs out of budget cloning TensorFlow-era dependencies. A larger budget
would not rescue a CPU BERT evaluation, so this is recorded as a limit rather than tuned away.

Before the privileged app was deployed, the blueprint deliberately stole the sandbox metadata
token and required explicit denial of a Firestore write, Secret Manager read, Pub/Sub publish,
Cloud Run execution, Vertex AI listing, and Cloud Storage listing — six recorded 403s. That
sandbox-only proof can be re-run on its own:

```powershell
powershell -File scripts/deploy_sandbox_probe.ps1 -ProjectId YOUR_PROJECT_ID -Region us-central1
```

Pub/Sub delivery is authenticated with verified Google OIDC against a custom audience, not a
query-string secret. See [current status](docs/PROJECT-STATUS-2026-08-29.md), the
[scoped security fix](docs/SCOPED-CLOUD-SECURITY-FIX.md), and the
[full audit](docs/AUDIT-2026-08-24.md).

## Reproducibility

- `environment.yml` pins Python 3.11 and installs `requirements.txt`.
- Every direct dependency is exactly pinned; after a clean install, run
  `scripts/lock.ps1` to record the entire transitive environment in `requirements-lock.txt`.
- Both container images use Python 3.11.15 and `--no-cache-dir` installs.
- Cloud Run Job retries are configured off in the deployed cloud profile because
  Verity owns the visible three-attempt loop.
- The first resolved repository commit is now recorded and pinned across all repair attempts.
  Fetched source bytes, the runner image digest, and evaluation conditions are not yet frozen and
  observed end to end; those remain reproducibility gaps.

## API

```text
POST /api/jobs                 {"url":"https://..."} -> 202 + job_id
GET  /api/jobs/{job_id}        -> current job, verdict, full trace
POST /internal/pubsub          Pub/Sub push consumer (verified Google OIDC)
GET  /health                   liveness
```

Except for `/health` and the static page, supply `X-Verity-Key` in production.

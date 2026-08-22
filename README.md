# Verity

Verity is an autonomous verification system for public AI/ML performance claims. It does
not summarize a paper or README and call that verification: it extracts a typed numerical
claim, runs the associated repository in a fresh sandbox, makes at most three transparent
repair attempts, and files an evidence-backed verdict as a GitHub Issue.

The four roles are declared as Google ADK agents in `app/agent.py`; the state machine in
`verity/pipeline.py` adds the durable checkpoints and hard retry boundary needed for safe
background execution. The configured model is `gemini-3.5-flash`.

Verity runs on either of two infrastructures, chosen by a single setting:

| Seam | `VERITY_ENV=local` | `VERITY_ENV=cloud` |
|---|---|---|
| State, trace, claim memory | SQLite (`verity.db`) | Firestore |
| Intake to processing | `asyncio.Queue` | Pub/Sub |
| Model calls | Gemini via AI Studio API key | Gemini via Vertex AI |
| Untrusted execution | Docker (`docker run --rm`) | Cloud Run Jobs |

**The local profile needs no Google Cloud project, no billing account, and no card.** The
agents depend only on the interfaces in `verity/interfaces.py`; `verity/container.py` is
the one module that picks concrete backends.

See [the architecture and trust boundaries](docs/architecture.md) or open
`verity-architecture.html` for the presentation diagram.

## What a result means

- `verified`: a captured metric is within the explicit 2% comparison tolerance.
- `contradicted`: a captured metric is outside that tolerance.
- `inconclusive`: evaluation exited successfully but no attributable metric was captured.
- `could_not_verify`: execution still failed after the bounded debug loop.

Verity never turns missing output into a number. Every error, proposed patch, and retry outcome
is persisted under the job trace.

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

Open `http://127.0.0.1:8080`. `GET /healthz` reports the active profile and any setup
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

## Google Cloud deployment

Deployment is blocked on hackathon credits, not on code. When they land, the swap is
`VERITY_ENV=cloud` plus the deployment below — the cloud adapters (`FirestoreJobStore`,
`PubSubJobQueue`, `VertexAIModelClient`, `CloudRunJobBackend`) are implemented and wired,
but unverified against live Google Cloud until a billing account exists.

Prerequisites:

1. A Google Cloud project linked to billing and the hackathon credit.
2. Google Cloud SDK authenticated with project-owner-equivalent setup permissions.
3. A fine-grained GitHub token with **Issues: write** on your report repository. Verity first
   tries the source repo; on the expected permission failure for third-party repos it files in
   `VERITY_REPORT_REPO` while linking the source.
4. The pinned Agents CLI deployment tool:

```powershell
conda activate agent-dev
python -m pip install -r requirements-deploy.txt
agents-cli login -i
```

Create independent random secrets, keep them out of shell history where possible, and deploy:

```powershell
$env:VERITY_API_KEY = '<at least 24 random characters>'
$env:VERITY_PUBSUB_VERIFICATION_TOKEN = '<different random value>'
$env:VERITY_GITHUB_TOKEN = '<fine-grained token>'
$env:VERITY_REPORT_REPO = 'owner/verity-reports'
powershell -File scripts/deploy.ps1 -ProjectId 'your-project-id' -Region 'us-central1' -BudgetUsd 25
```

The script uses the official `agents-cli deploy --deployment-target cloud_run` path for the
ADK service, and provisions only the supporting resources it needs: Artifact Registry,
Firestore, Pub/Sub, the sandbox Cloud Run Job, three least-privilege service accounts, Secret
Manager entries, and a billing budget with 50/90/100% alerts. The web URL is public so judges
can reach it, but job endpoints require `X-Verity-Key`; the Pub/Sub endpoint uses a separate
secret plus an authenticated push identity.

## Reproducibility

- `environment.yml` pins Python 3.11 and installs `requirements.txt`.
- Every direct dependency is exactly pinned; after a clean install, run
  `scripts/lock.ps1` to record the entire transitive environment in `requirements-lock.txt`.
- Both container images use Python 3.11.15 and `--no-cache-dir` installs.
- Cloud Run Job retries are disabled because Verity owns the visible three-attempt loop.
- Repository revisions and evaluation conditions are part of the typed parser output and
  final Issue.

## API

```text
POST /api/jobs                 {"url":"https://..."} -> 202 + job_id
GET  /api/jobs/{job_id}        -> current job, verdict, full trace
POST /internal/pubsub          Pub/Sub push consumer (separate secret)
GET  /healthz                  liveness
```

Except for `/healthz` and the static page, supply `X-Verity-Key` in production.

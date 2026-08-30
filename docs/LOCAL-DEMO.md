# Verity — Local Demo Guide

**Run the whole pipeline on your own machine in about ten minutes, without an API key.**

This guide is written for someone who has never seen this repository. Five claim URLs
below are pre-verified and ship with their results, so you can watch a real verdict come back
**instantly and without a single Gemini API call**. If you want to verify a *new* claim you
will need your own free key — that path is covered at the end.

---

## What you will see

Verity takes a public AI/ML performance claim, tries to **actually reproduce it** in a sandbox,
and files an evidence-backed verdict. The interesting part is what it does when reproduction
fails: it says so, and refuses to invent a number.

A real verdict it produced: **[verity-reports#1](https://github.com/ZiyadAzzaz/verity-reports/issues/1)**

---

## 1. Prerequisites

| | |
|---|---|
| Python 3.11 | `python --version` must say 3.11.x |
| Docker Desktop | must be **running** — see §5 for why this is not optional |
| Git | to clone |

VS Code is convenient but not required; every step below is a terminal command.

---

## 2. Setup

```bash
git clone https://github.com/ZiyadAzzaz/verity.git
cd verity
```

**With conda** (the documented path):

```bash
conda create -n agent-dev python=3.11 -y
conda activate agent-dev
python -m pip install -r requirements.txt
```

**Without conda** — `scripts/bootstrap.ps1` falls back to a plain `.venv` automatically:

```powershell
powershell -File scripts/bootstrap.ps1
```

Create the environment file:

```bash
cp .env.example .env
```

**Leave `GEMINI_API_KEY` empty for the cached demo.** You do not need it for §4.

Confirm the machine is ready:

```bash
python scripts/check_setup.py --allow-missing-key
```

It will report a warning that `GEMINI_API_KEY is empty`—expected for the cached path—and still
return success when Python, dependencies, and Docker are ready.

---

## 3. Open it in VS Code

```bash
code .
```

Select the interpreter so the editor uses the right environment:

1. `Ctrl+Shift+P` → **Python: Select Interpreter**
2. Pick the `agent-dev` conda environment, or `./.venv/Scripts/python.exe`

Worth opening while you read:

| File | Why |
|---|---|
| `verity/interfaces.py` | The four seams the whole design rests on |
| `verity/container.py` | The only module that picks a concrete backend |
| `verity/agents/environment.py` | `DockerSandboxBackend` — where untrusted code is contained |
| `verity/models.py` | The typed contracts that make a fabricated verdict unrepresentable |

---

## 4. The cached demo — no API key, no quota, instant

Five claims have already been run end to end through the real pipeline. Their verdicts, full
agent traces, and claim-memory entries ship in this repository at
`docs/assets/demo-cache/verity-demo.db`.

### The pre-verified URLs

| # | Claim URL | Extracted claim | Verdict |
|---|---|---|---|
| 1 | `https://arxiv.org/abs/1512.03385` | top-5 error rate = **4.49%** on ImageNet 2012 validation | `could_not_verify` |
| 2 | `https://arxiv.org/abs/1706.03762` | BLEU score = **28.4** on WMT 2014 English-to-German | `could_not_verify` |
| 3 | `https://github.com/psf/requests` | HTTP status code = **200** on an httpbin endpoint | **`verified`** — reproduced 200.0 |
| 4 | `https://github.com/ZiyadAzzaz/Stroke-Data-Analysis` | number of features = 11 | **`no_verifiable_claim_found`** — nothing executed |
| 5 | `https://github.com/ijl/orjson` | median latency = **0.1 ms** on twitter.json | **`environment_incompatible`** — never tested |

Five claims covering **four different outcomes**, so the full range is visible without an API
key: a claim that reproduces, two that honestly do not, one the source never asserted as a
result, and one the sandbox genuinely could not host.

**Submitting any of these hits the local cache and makes no Gemini API call at all.**
Anything else attempts a real verification and needs a key.

### Step 1 — point Verity at the shipped cache and start it

**Windows PowerShell:**

```powershell
New-Item -ItemType Directory -Force .verity-data | Out-Null
Copy-Item docs/assets/demo-cache/verity-demo.db .verity-data/verity-demo.db -Force
$env:VERITY_SQLITE_PATH = ".verity-data/verity-demo.db"
python -m uvicorn app.fast_api_app:app --port 8080
```

**macOS / Linux:**

```bash
mkdir -p .verity-data
cp docs/assets/demo-cache/verity-demo.db .verity-data/verity-demo.db
VERITY_SQLITE_PATH=.verity-data/verity-demo.db python -m uvicorn app.fast_api_app:app --port 8080
```

The copy is deliberate. The committed cache is a curated fixture and Verity refuses to open it
for writing; using a scratch copy keeps the shipped evidence unchanged while the API updates
timestamps and accepts new submissions.

Wait for this line. **Startup takes 10–20 seconds** because Verity checks the Docker daemon
before accepting any job:

```
INFO  verity.agents.environment Docker daemon 29.7.2 is available
INFO  Application startup complete.
INFO  Uvicorn running on http://127.0.0.1:8080
```

> Skipping `VERITY_SQLITE_PATH` starts Verity on an empty database. Everything still works,
> but nothing is cached, so every submission needs an API key.

### Step 2 — open the page

**<http://127.0.0.1:8080>**

You will see a dark page headed **"Verity runs the evidence."** with two fields:

| Field | What to do |
|---|---|
| **PUBLIC CLAIM URL** | Paste the claim you want checked |
| **VERITY API KEY** | **Leave empty.** Only the deployed service requires it |

### Step 3 — submit a cached claim

Paste this into **PUBLIC CLAIM URL** and click **Start verification**:

```
https://arxiv.org/abs/1512.03385
```

### Step 4 — read what comes back

The result appears **immediately** — no spinner, because it came from cache:

```
completed
could not verify
Verity could not complete the claimed evaluation after 3 bounded debug attempts.
No reproduced value is asserted.

CLAIMED       4.49%
REPRODUCED    Not captured
CONFIDENCE    high
ARTIFACT      Not filed
```

**Look at `REPRODUCED: Not captured`.** That is the entire point of the project. Verity
extracted a real claim from a real PDF, tried three times to reproduce it, failed, and put
*nothing* in that box. A system optimising to look good would have written `4.49%` there.

Below that, the **Agent trace** — every step, persisted:

```
ORCHESTRATOR  job queued
PARSER        source fetch started
PARSER        claim extracted
ENVIRONMENT   initial run started
ENVIRONMENT   initial run finished
DEBUG         attempt started       <-- attempt 1
DEBUG         attempt finished
DEBUG         attempt started       <-- attempt 2
DEBUG         attempt finished
DEBUG         attempt started       <-- attempt 3
DEBUG         attempt finished          three, and no more. hard-capped.
REPORTER      verdict started
REPORTER      verdict completed
```

Try the second URL (`https://arxiv.org/abs/1706.03762`) — a different paper, a different
metric, the same honest refusal.

### Step 5 — see a claim that *does* verify

Submit `https://github.com/psf/requests`. It ships pre-verified too, so this is also instant:

```
claim      : HTTP status code = 200 on https://httpbin.org/basic-auth/user/pass
verdict    : verified (medium)
reproduced : 200.0
attempts   : 1
summary    : The reproduced HTTP status code (200) is within the declared 2%
             comparison tolerance of the claim (200).
```

Verity says **verified** when something reproduces and **could_not_verify** when it does not.

And submit `https://github.com/ZiyadAzzaz/Stroke-Data-Analysis` for the third case. That
repository's only number is a feature count — a description of its input, not a result anyone
asserted. Verity returns `no_verifiable_claim_found`, **runs no container at all**, and the
trace is five events instead of thirteen. Reporting that as a failed reproduction would have
claimed an attempt that never happened.

Finally `https://github.com/ijl/orjson`, for the fourth case. Its benchmark downloads its
input at evaluation time, and Verity's sandbox denies network access during evaluation so a
benchmark cannot fetch data mid-measurement. That claim is therefore untestable here whether
it is true or false, and Verity says so: **`environment_incompatible`**, explicitly *not*
`could_not_verify`. Blaming the claim for our own constraint would be the easy lie.

### Prefer the terminal?

```bash
python scripts/file_stored_verdict.py --database docs/assets/demo-cache/verity-demo.db --list
```

Or hit the API directly:

```bash
curl -s http://127.0.0.1:8080/health
```

```bash
curl -s -X POST http://127.0.0.1:8080/api/jobs -H "Content-Type: application/json" -d "{\"url\":\"https://arxiv.org/abs/1512.03385\"}"
```

```
{"job_id":"068d7560cc124fc0907bfa59770fdaa5","status":"completed","cached":true,
 "status_url":"/api/jobs/068d7560cc124fc0907bfa59770fdaa5"}
```

Note `"cached":true`. Then fetch the verdict and full trace:

```bash
curl -s http://127.0.0.1:8080/api/jobs/068d7560cc124fc0907bfa59770fdaa5
```

### Step 6 — the filed artifact

A verdict does not stop at the screen. Verity files it as a real GitHub Issue:

**<https://github.com/ZiyadAzzaz/verity-reports/issues/1>**

Same verdict, same `Reproduced: not captured`, plus the Debug Agent's own reasoning:

> *"Fabricating the metric or replacing the evaluation with a constant is strictly prohibited
> under the security and honesty rules. Therefore, no defensible fix can be proposed."*

### Want an offline copy of a result?

Use your browser's own **Print → Save as PDF** on the result page. There is no export
feature and does not need to be one — the filed GitHub Issue is already the detailed report,
carrying the full debug trail, claimed versus reproduced, the evidence quote, and the Debug
Agent's reasoning.

### Stopping the server

`Ctrl+C` in the terminal running uvicorn.

## 5. The sandbox — verify the isolation yourself

Verity clones and executes arbitrary third-party code from GitHub. It never runs that on your
machine. You can confirm the boundary holds rather than taking our word for it:

```bash
python scripts/validate_docker_isolation.py
```

This starts real containers and actively tries to escape them — read host files, write outside
the workspace, reach the network during evaluation, escalate privileges, find the Docker
socket, fork-bomb the daemon. **Exit 0 means every attempt failed**, which is the desired
result:

```
[PASS] host files outside the workspace are unreachable      reachable: []
[PASS] the container filesystem is read-only outside /work
[PASS] the evaluation phase has no network
[PASS] the install phase can still reach PyPI
[PASS] the sandbox is non-root with no capabilities          uid 10002 CapEff 0x0 NoNewPrivs 1
[PASS] the Docker socket is not exposed
[PASS] process count is capped                               pid limit reached after 511
[PASS] the workspace is writable
```

The first run builds the sandbox image and takes a few minutes.

---

## 6. The test suite

```bash
powershell -File scripts/test.ps1 -Docker
```

Runs ruff, `ruff format --check`, `mypy --strict`, and the full suite **including** the
container tests. The current scoped-security result is **271 passed**; the non-Docker selection
emits two upstream dependency deprecation warnings.

Without a Docker daemon, drop `-Docker` and the 9 container tests deselect themselves rather
than failing.

---

## 7. Verifying a *new* claim — needs your own free key

Everything above works without one. To verify a claim that is not in the cache:

1. Get a free key at [aistudio.google.com](https://aistudio.google.com/) — no billing account,
   no card.
2. Put it in `.env`:
   ```ini
   VERITY_ENV=local
   GEMINI_API_KEY=<your key>
   ```
3. Submit any claim URL through the UI, or run the full gate:
   ```bash
   python scripts/validate_local_pipeline.py --limit 3
   ```

**Budget warning:** the AI Studio free tier allows **20 requests per day**, and one
verification costs up to 4 calls (1 parser + 3 debug) — roughly **5 claims per day**. Verified
claims are cached, so re-submitting one costs nothing.

**How to read the result:** passing does *not* mean every claim verifies. Most public AI/ML
claims do not reproduce on a laptop, and several sources in the catalogue exist specifically to
exercise the honest-failure path. A run passes when every job reaches an evidence-backed
verdict and **no job reports a number it did not actually observe**. Six honest
`could_not_verify` results out of eight is a *passing* run, and a more useful one than six
spurious `verified`s.

---

## 8. Switching to the cloud profile

One setting changes the entire infrastructure:

```ini
VERITY_ENV=cloud
```

| Seam | `local` | `cloud` |
|---|---|---|
| State, trace, claim memory | SQLite | Firestore |
| Intake → processing | `asyncio.Queue` | Pub/Sub |
| Model calls | Gemini via AI Studio | Gemini via Vertex AI |
| Untrusted execution | Docker | Cloud Run Jobs |

No agent, pipeline step, or test changes — `verity/container.py` is the only module that
imports a concrete backend.

**Status, stated plainly:** both profiles are implemented. The cloud profile is deployed publicly
and passed the credential-free sandbox proof plus a live multi-claim run. Its no-role sandbox
cannot access six tested Google Cloud APIs. The local profile in this guide remains the quickest
way to reproduce the system without a Google Cloud account.

---

## 9. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `docker info` hangs | Daemon not ready, or the disk holding Docker's data is full. Check free space first — that exact fault cost us hours |
| `GEMINI_API_KEY is not set` | Expected for the cached demo. Only needed for new claims |
| `429 RESOURCE_EXHAUSTED` | Free tier daily cap of 20 requests. Wait for the reset; cached claims still work |
| Container tests skip | Docker not running. They deselect rather than fail, by design |
| Wrong Python | Must be 3.11. `python scripts/check_setup.py` names the interpreter it found |

---

## 10. Where to read next

| Document | Contents |
|---|---|
| [`docs/PROJECT-ANALYSIS.md`](PROJECT-ANALYSIS.md) | What was tested, how, results, and what is *not* done |
| [`docs/architecture.md`](architecture.md) | Both profiles, trust boundaries, data model |
| `verity-architecture.html` | The presentation diagram — open it in a browser |
| [`docs/HANDOVER.md`](HANDOVER.md) | Current status and every path that matters |

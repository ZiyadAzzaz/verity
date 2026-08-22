# Verity — Local Demo Guide

**Run the whole pipeline on your own machine in about ten minutes, without an API key.**

This guide is written for someone who has never seen this repository. Two of the claim URLs
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
python scripts/check_setup.py
```

It will report `GEMINI_API_KEY is empty` — expected, and fine for the cached path. Everything
else should be `[ OK ]`, including the Docker daemon.

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

Two claims have already been run end to end through the real pipeline. Their verdicts, full
agent traces, and claim-memory entries ship in this repository at
`docs/assets/demo-cache/verity-demo.db`.

### The pre-verified URLs

| Claim URL | Extracted claim | Verdict |
|---|---|---|
| `https://arxiv.org/abs/1512.03385` | top-5 error rate = **4.49%** on ImageNet 2012 validation | `could_not_verify` |
| `https://arxiv.org/abs/1706.03762` | BLEU score = **28.4** on WMT 2014 English-to-German | `could_not_verify` |

**Submitting either of these hits the local cache and makes no Gemini API call at all.** They
return in milliseconds. Anything else will attempt a real verification and *will* need a key.

### Run it

```bash
uvicorn app.fast_api_app:app --reload --port 8080
```

Open `http://127.0.0.1:8080`, paste one of the two URLs above, and submit. The verdict comes
back immediately, marked as cached.

Prefer the terminal? This reads the shipped cache directly:

```bash
python scripts/file_stored_verdict.py --database docs/assets/demo-cache/verity-demo.db --list
```

```
2 completed job(s) with a verdict:

  068d7560cc124fc0907bfa59770fdaa5
    https://arxiv.org/abs/1512.03385
    could_not_verify - top-5 error rate = 4.49% on ImageNet 2012 validation
    reproduced: None   attempts: 3
```

### What to look at, and why it matters

`reproduced: None` with `attempts: 3` is the whole point. Verity tried three bounded repair
attempts, failed, and **reported no number** rather than inventing one. Open
[verity-reports#1](https://github.com/ZiyadAzzaz/verity-reports/issues/1) to see what that
looks like when filed — including the Debug Agent's own words:

> *"Fabricating the metric or replacing the evaluation with a constant is strictly prohibited
> under the security and honesty rules. Therefore, no defensible fix can be proposed."*

---

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
container tests. Expect **118 passed**, nothing skipped.

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

**Status, stated plainly:** the cloud adapters are implemented and selectable but have not yet
been run against live Google Cloud. See [`docs/PROJECT-ANALYSIS.md`](PROJECT-ANALYSIS.md) §3.1.

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

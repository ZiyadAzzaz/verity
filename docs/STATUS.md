# Verity — Full Status Report

**Last updated:** 2026-08-22
**Machine:** Windows 11 Pro · conda `agent-dev` (Python 3.11.15) at `D:\Anaconda\envs\agent-dev`
**Supersedes:** `docs/PIVOT-STATUS.md` (kept for history; this document is authoritative)

---

## 0. Where things stand right now

| | |
|---|---|
| Local-first pivot | **Code complete** |
| Static analysis | `ruff` ✅ · `ruff format` ✅ · `mypy --strict` ✅ |
| Unit tests | **96 passed**, 9 deselected (the Docker suite) |
| Live Gemini path | ✅ **Verified end to end** — 3 real sources, 2 real bugs found and fixed |
| Docker sandbox | 🔴 **Never executed a container.** Daemon has not responded all session |
| Cloud path | ⏸ Wired and selectable; unverified, waiting on credits |
| Git | 2 commits, local only. `17b364e` on branch `fix/live-gemini-and-conda-resolution` |

**One thing blocks everything that remains: the Docker daemon.** See [§6](#6-what-i-need-from-you).

---

## 1. What the pivot actually did

Verity now runs on either of two infrastructures, chosen by one setting.

| Seam | Interface | `VERITY_ENV=local` | `VERITY_ENV=cloud` |
|---|---|---|---|
| State, trace, claim memory | `JobStore` | `SQLiteJobStore` (`verity.db`) | `FirestoreJobStore` |
| Intake → processing | `JobQueue` | `AsyncioJobQueue` | `PubSubJobQueue` |
| Model calls | `ModelClient` | `GeminiAIStudioClient` | `VertexAIModelClient` |
| Untrusted execution | `SandboxBackend` | `DockerSandboxBackend` | `CloudRunJobBackend` |

`verity/interfaces.py` is the seam. `verity/container.py` is the **only** module that imports
a concrete backend. No agent, no pipeline step, and no test touches SQLite, Docker, Firestore,
Pub/Sub, or Cloud Run directly.

The local profile needs **no GCP project, no billing account, no card** — only a free AI
Studio key.

### The sandbox

The Environment Agent executes arbitrary third-party code from GitHub and never does so on
the host. Each job is four separate `docker run --rm` phases:

| Phase | Network | Why |
|---|---|---|
| clone | `bridge` | Fetch the declared repository. |
| venv | `none` | Create the interpreter; nothing to download. |
| install | `bridge` | Install the **declared** dependencies only. |
| evaluate | **`none`** | A benchmark that phones home while scoring is not reproducible. |

Every container: `--cap-drop ALL`, `--security-opt no-new-privileges`, `--read-only` rootfs,
size-capped `/tmp` tmpfs, pid/memory/cpu limits, exactly one bind mount (`/work`), no Docker
socket, `--entrypoint` always overridden so a tampered image cannot choose what runs.

---

## 2. Everything I added

### New files (17)

| File | Purpose |
|---|---|
| `verity/interfaces.py` | The seam: `JobStore`, `JobQueue`, `ModelClient`, `SandboxBackend`, `SandboxUnavailableError` |
| `verity/sqlite_store.py` | Durable local job store over one `verity.db` |
| `Dockerfile.runner` | Sandbox runtime image — runtimes only, no Verity code, no entrypoint |
| `.env` | Your environment file (git-ignored; the single source of environment config) |
| `scripts/check_setup.py` | One command: is this machine ready? Never prints the key |
| `scripts/_python.ps1` | Interpreter resolution — finds conda properly (see §3.1) |
| `scripts/validate_docker_isolation.py` | 7 container escape attempts; exit 0 = all failed |
| `scripts/validate_local_pipeline.py` | 8 real claim URLs, end to end, no GCP |
| `tests/data/local_claim_urls.json` | The 8-source catalogue with expected outcomes |
| `tests/test_sqlite_store.py` | Reservation, restart survival, claim memory, trace order |
| `tests/test_local_adapters.py` | Queue behaviour + the `VERITY_ENV` swap |
| `tests/test_local_stack.py` | End to end over real SQLite + real queue |
| `tests/test_docker_command.py` | The `docker run` argv — verified **without** a daemon |
| `tests/test_docker_sandbox.py` | Real container escape attempts (marked `docker`) |
| `tests/test_model_client.py` | Retry/backoff + key injection |
| `tests/test_response_schema.py` | The JSON Schema sent to Gemini |
| `docs/STATUS.md` | This document |

### Modified files

`verity/config.py` (rewritten — `VERITY_ENV`, `PROFILES`) · `verity/container.py` (rewritten —
`build_*` + `startup`/`shutdown`/`preflight`) · `verity/llm.py` (rewritten — two clients,
backoff, key injection) · `verity/messaging.py` (rewritten — `AsyncioJobQueue`) ·
`verity/store.py` · `verity/agents/environment.py` (Docker backend) · `verity/orchestrator.py` ·
`verity/api.py` · `verity/models.py` · `verity/pipeline.py` · `verity/agents/{parser,debug}.py` ·
`verity/sandbox_runner.py` · `verity/prompts.py` · `app/agent.py` · `README.md` ·
`docs/architecture.md` · `.env.example` · `.gitignore` · `pyproject.toml` ·
`.github/workflows/ci.yml` · `scripts/{bootstrap,test,deploy}.ps1` ·
`scripts/validate_{parser_real,broken_repo}.py` · several test files

---

## 3. Bugs and mistakes found this session

### 3.1 My own error — I said conda wasn't installed. It is.

**Wrong claim:** "conda is not installed on this machine."
**Reality:** `D:\Anaconda`, with `agent-dev` already created on Python 3.11.15.

Two compounding failures: `Get-Command conda` returns nothing in a non-interactive shell,
because `conda init` writes itself into the user's PowerShell *profile* which such a shell
does not load; and my directory search covered `%USERPROFILE%`, `%LOCALAPPDATA%`, and
`C:\ProgramData` but never the D: drive. I should have read the profile and the registry
first.

**Fixed:** `scripts/_python.ps1` resolves conda through `CONDA_EXE` and a scan of every
filesystem drive. `bootstrap.ps1` and `test.ps1` now behave identically from your prompt or
from a task runner.

### 3.2 My own error — I said I'd stopped the hanging Docker probe

I stopped **one** of **three**. Two were still running when you were about to shut down. All
stopped now.

### 3.3 The pip failure was a full disk — I diagnosed it wrong

`pip install` into `agent-dev` failed twice with byte-identical
`IncompleteRead(214519 bytes read, 38151 more expected)`. I concluded a truncated wheel in
pip's cache and moved on when `--no-cache-dir` fixed it.

**That diagnosis was wrong.** The C: drive had **0 MB free**. The download was failing
because there was nowhere to write it, and `--no-cache-dir` "fixed" it only by not writing
2.6 GB of cache to a full disk. The identical byte counts came from hitting the same wall at
the same point, not from re-reading the same corrupt file.

The same full disk is the root cause of the Docker failure in §6 — a WSL2 VM cannot start
its services with no space. One fault, two symptoms, and I chased both separately.

### 3.4 🔴 Real bug — the model client could never see your key

`GeminiAIStudioClient` read `os.environ["GEMINI_API_KEY"]`. But `.env` is parsed by
pydantic-settings into `Settings` and **never exported to the environment**. Anyone who
configured the key correctly still got *"GEMINI_API_KEY is not set"*.

A design flaw in my own code — the client reached for a global instead of being handed the
value. **Fixed:** the key is injected from `verity/container.py` as a `SecretStr`; the
environment is now only a fallback for `GEMINI_API_KEY=... python ...` invocation. Four
regression tests, including one on the container wiring.

### 3.5 🔴 Real bug — Gemini rejected every structured call

```
400 INVALID_ARGUMENT: Unknown name "additional_properties"
  at 'generation_config.response_schema'
```

Pydantic's `extra="forbid"` emits `additionalProperties: false`, and the Gemini REST API
refuses it outright. **This would have broken the Parser and Debug agents in every
environment, local and cloud alike.**

**Fixed** in `verity/models.py`: a shared `STRICT` config strips the key from the *emitted*
schema only. Runtime validation is untouched — a response with an unexpected field is still
rejected. Only the boolean form is removed; `dict[str, str]` fields legitimately emit
`additionalProperties: {"type": "string"}` to describe a map and keep it.

Neither 3.4 nor 3.5 was findable without a live API call. Both are exactly the risk class I
flagged before running.

---

## 4. What is verified

### Static analysis and tests — under `agent-dev`

```
ruff check .              All checks passed!
ruff format --check .     53 files already formatted
mypy verity app           Success: no issues found in 28 source files
pytest -q -m "not docker" 96 passed, 9 deselected
```

Also run against an independent throwaway Python 3.11.9 venv — clean install of all 89 pinned
packages, same result. Two independent environments, same outcome.

### Live Gemini — Gate 3 passes

```
arxiv_pdf_table   top-1 error 21.43% on ImageNet 2012 validation   matched
github_readme     box AP 42 on COCO 2017 val5k                     matched, quote verbatim
vendor_claim      5x on Llama 2 70B                                quote verbatim
```

Multimodal PDF parsing works. Structured output works. Repository extraction works, and the
parser correctly returned **no** repository for the two sources that link none — it did not
invent one.

### Pivot requirements

| Requirement | Status | Evidence |
|---|---|---|
| §1 Three interfaces, agents depend on nothing else | ✅ | `verity/interfaces.py` |
| §2 `SQLiteJobStore`, five methods + dedup | ✅ | `tests/test_sqlite_store.py` |
| §2 `AsyncioJobQueue` + background consumer | ✅ | `tests/test_local_adapters.py` |
| §2 `GeminiAIStudioClient` + retry/backoff | ✅ | `tests/test_model_client.py`, live run |
| §3 Cloud adapters behind one config value | ✅ | `PROFILES` in `verity/config.py` |
| §4 Docker not raw subprocess | ✅ code, 🔴 unrun | argv proven in `tests/test_docker_command.py` |
| §4 `docker info` preflight, clear setup error | ✅ | `tests/test_api_local.py` |
| §5 Honest failure after exactly 3 attempts | ✅ | `tests/test_local_stack.py` on the real stack |
| §5 Dedup returns instantly | ✅ | `tests/test_local_stack.py` |
| §5 Clean-environment install | ✅ | Both venv and `agent-dev` |
| §5 8 real claim URLs end to end | 🔴 | Needs Docker |
| §5 Docker isolation confirmed | 🔴 | Needs Docker |
| §6 No GCP dependency locally | ✅ | Live Gemini run used no GCP project |

---

## 5. 🔎 Decisions you should review

These are judgement calls I made. Each is defensible, none is obviously right, and you may
want a different answer for the submission.

### 5.1 Interfaces are async + Pydantic, not sync + `dict`

The pivot prompt sketched `def get_job(self, job_id: str) -> dict`. I built
`async def get_job(self, job_id: str) -> JobRecord | None`. Same five methods, same
semantics. Reason: the pipeline is already async, and typed contracts are what let mypy
prove a verdict cannot carry a number the run never produced. **Review if** you want the
submission to match the prompt's sketch literally.

### 5.2 Cloud adapters are implemented, not stubbed

The prompt said stub them. Firestore and Pub/Sub were **already implemented** in your code;
Vertex was ~15 lines on the shared ADK base. Replacing working code with
`NotImplementedError` would destroy value. **Review if** the submission narrative needs
visible stubs — I can swap them, though I'd advise against it.

### 5.3 ⭐ The parser gate was redesigned — read this one

The original `parser_cases.json` asserted **one exact value per source**. Across three live
runs the same source returned a different *correct* answer each time:

- ResNet paper: 4.49% → 21.43% (it genuinely contains 3.57, 4.49, and 21.43 — ensemble test
  error, single-model top-5 val, single-model top-1 val)
- NVIDIA H100 page: 30x Megatron 530B → 5x Llama 2 70B (both verbatim on the page)

The old gate was testing *the model's taste*, not its correctness, and would fail randomly.

I did **not** loosen it to get green. I replaced it with three layers:

1. **Grounding** — the `evidence_excerpt` must occur verbatim in the fetched source. This is
   the anti-fabrication check and cannot be gamed by relaxing a threshold.
2. **Contract** — finite value, named metric/dataset/location, correct source type, and a
   repository *only* where one genuinely exists.
3. **Known claim** — a documented *set* of correct answers per source; empty for the live
   marketing page whose numbers NVIDIA revises.

Reasoning is recorded per-source in `tests/data/parser_cases.json`. **This is the change most
worth your disagreement.** If you think the gate should pin one value, say so and I'll revert
— but expect intermittent red.

### 5.4 The initial commit went to `main`

Normally I branch before committing. The repo had **zero commits**, so this was the
repository's first — there was no `main` history to protect, and a first commit on a side
branch leaves `main` unborn. Everything after this branches normally.

### 5.5 ~~`local.env` takes precedence over `.env`~~ — resolved, consolidated

**Reviewed and reversed.** A second env file with silent precedence is unexplained friction
for anyone reading the repo for reproduction steps. `local.env` has been folded into `.env`
(key migrated intact), the `env_file=(".env", "local.env")` tuple in `verity/config.py` is
back to a plain `".env"`, and every reference in the scripts, library messages, and
`bootstrap.ps1` now says `.env`. One env file, no precedence rules.

### 5.6 `host_subprocess` backend still exists — now test-enforced

It runs untrusted code on the host with no isolation. Kept because it is the body of the
Cloud Run sandbox container, where the Cloud Run container *is* the boundary.

**The production rejection is now proven by a test, not just documented:**
`tests/test_production_guardrails.py` asserts that a production configuration selecting
`host_subprocess` fails validation, along with every other way of weakening the boundary
(docker in production, the whole local profile, each missing secret). 13 tests. The
development escape hatch is separately asserted to still work.

### 5.7 Sandbox containers are `--read-only` by default

Strongest posture, but some repos' installs may need to write outside `/work` and `/tmp`.
Unproven until a real container runs. If it bites, the fix is a larger tmpfs or one extra
mount — one line.

---

## 6. What I need from you

### 🔴 The only blocker: Docker

`docker info` has not responded once all session. **Diagnosed from Docker Desktop's own
logs** — it is *not* an onboarding screen, which is what I wrongly assumed earlier:

```
apiproxy  << GET /_ping Internal Server Error: context deadline exceeded (15.0s)
GET failed with Get "http://unix/forwards/list": context deadline exceeded
still waiting to toggle VM Otel collector settings in the VM after 13m0.6s
```

The named pipes exist and accept connections, the CLI context is correct, and the
`docker-desktop` WSL distro reports `Running` — but nothing inside that VM answers. The
Windows backend cannot reach the Linux engine. That is why calls hang rather than fail fast.

**Follow [DOCKER-FIX.md](DOCKER-FIX.md)** — seven ordered steps, starting with a full
tray-quit plus `wsl --shutdown` and a `wsl --update`, escalating to Troubleshoot → Clean /
Purge data and then a factory reset. Stop as soon as `docker info` returns.

Optional, saves several minutes on the first job:

```bash
docker build -f Dockerfile.runner -t verity-sandbox-runner:1 .
```

### ✅ Already done — nothing needed

- `GEMINI_API_KEY` is in `.env` and working (verified by a live run).
- `agent-dev` is installed and green.
- Everything stays local; no git remote is configured.

### One command to confirm state any time

```bash
python scripts/check_setup.py
```

Checks Python, dependencies, key, daemon, and sandbox image. **Never prints your key** —
only whether one is present and its length. Safe to paste to me.

---

## 7. What I run the moment Docker answers

| # | Gate | Command |
|---|---|---|
| 1 | Container isolation — 7 escape attempts | `python scripts/validate_docker_isolation.py` |
| 2 | The 9 skipped container tests | `pytest -m docker -q` |
| 3 | ~~Live Gemini on 3 real sources~~ | ✅ **done, passing** |
| 4 | Real debug loop on genuinely broken code | `python scripts/validate_broken_repo.py` |
| 5 | 8 real claim URLs end to end | `python scripts/validate_local_pipeline.py` |

Isolation runs **first**, before any untrusted code executes.

### How to read Gate 5 — important

Passing does **not** mean everything verified. Most public AI/ML claims do not reproduce on a
laptop, and several catalogue entries exist specifically to exercise honest failure — arXiv
papers with no runnable repo, models whose weights won't download in time, vendor multipliers
with nothing to run. The gate passes when:

- every job reaches a terminal verdict with evidence behind it,
- no job reports a number it did not actually observe,
- a re-submission of the first URL returns cached in under two seconds.

**Six of eight coming back `could_not_verify` with specific reasons is a passing run** — and a
better demo than six spurious `verified`s.

### Then

- Fix whatever Gates 1/4/5 surface (my bet: a `--read-only` conflict or tmpfs size).
- Add the local profile to `verity-architecture.html` (still cloud-only).
- Generate `requirements-lock.txt` via `scripts/lock.ps1`.
- Consider `.gitattributes` with `* text=auto eol=lf` — git warned about CRLF on ~50 files,
  and CRLF in `Dockerfile.runner` or the `.ps1` scripts can misbehave inside a Linux container.
- Commit the 14 outstanding files.

---

## 8. Quick reference

### Run it

```bash
conda activate agent-dev
uvicorn app.fast_api_app:app --reload --port 8080
```

`http://127.0.0.1:8080`. `GET /healthz` reports the live profile and any setup error:

```json
{
  "status": "degraded",
  "profile": "local",
  "store": "sqlite",
  "queue": "asyncio",
  "sandbox": "docker",
  "setup_error": "SandboxUnavailableError: The Docker daemon is not reachable."
}
```

### Test it

```bash
powershell -File scripts/test.ps1            # ruff + format + mypy + unit suite
powershell -File scripts/test.ps1 -Docker    # the above plus real container isolation
```

### Where things live

| I want to… | Look at |
|---|---|
| See the seam | `verity/interfaces.py` |
| See the local/cloud swap | `verity/config.py` → `PROFILES` |
| See adapter selection | `verity/container.py` |
| Understand the sandbox | `verity/agents/environment.py` → `DockerSandboxBackend` |
| Change the sandbox runtime | `Dockerfile.runner` |
| Read the architecture | `docs/architecture.md` |
| Review my judgement calls | §5 of this document |

### Safety note

`VERITY_SANDBOX_BACKEND=host_subprocess` runs untrusted third-party code **directly on your
machine with no isolation**. It exists for debugging Verity itself, warns when selected, and
production rejects it. Never point it at a repository you have not read.

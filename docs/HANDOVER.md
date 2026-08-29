# Verity — Complete Handover

> **Historical snapshot (2026-08-22).** It is no longer the source of truth. Use
> [STATE.md](STATE.md) and [AUDIT-2026-08-24.md](AUDIT-2026-08-24.md).

**Updated:** 2026-08-22
`STATUS.md`, `DOCKER-FIX.md`, and `PIVOT-STATUS.md` were folded into this historical handover.

---

## 1. State at a glance

| | |
|---|---|
| Local-first pivot | ✅ Code complete |
| Static analysis | ✅ `ruff` · `ruff format` · `mypy --strict` |
| Test suite | ✅ **118 passed**, nothing skipped (includes 9 container tests) |
| Live Gemini | ✅ **Verified** — 3 real sources, 2 real bugs found and fixed |
| Docker daemon | ✅ **Working** — `29.7.2 linux 8cpu`, data relocated to `E:\wsl` |
| Sandbox image | ✅ Built — `verity-sandbox-runner:1`, 1.25 GB |
| Gate 1 — isolation | ✅ **8/8 escape attempts failed** on real containers |
| Gate 2 — container tests | ✅ 9 passed |
| Gate 3 — broken-repo loop | ✅ Exactly 3 attempts → `could_not_verify`, no value invented |
| Gate 4/5 — pipeline | 🟡 Partial — 2 sources to terminal verdict, rest quota-limited |
| Real GitHub Issue | ✅ **Filed** — [verity-reports#1](https://github.com/ZiyadAzzaz/verity-reports/issues/1) |
| Dedup / claim memory | ✅ Cached re-submission in **0.000s** |
| Cloud path | 🔴 **Never run** — waiting on credits. The submission risk |
| Repos | ✅ Both **public**: `verity`, `verity-reports` |
| Git | 17 commits on `main`, pushed, **zero AI attribution in history** |

---

## 2. Paths — where everything lives now

### Machine

| What | Path |
|---|---|
| Repository | `E:\Azzaz CAI\Researches\verity-hackathon` |
| Python environment | `D:\Anaconda\envs\agent-dev` (Python 3.11.15) |
| Activate with | `conda activate agent-dev` |
| Conda install | `D:\Anaconda` |
| Fallback venv | `.venv` in the repo (redundant now; git-ignored, safe to delete) |

### Docker — relocated this session

| What | Path |
|---|---|
| **Docker data (real location)** | **`E:\wsl\Docker`** |
| Path Docker still uses | `C:\Users\Lenovo\AppData\Local\Docker` → **junction** → `E:\wsl\Docker` |
| Images / containers disk | `E:\wsl\Docker\wsl\disk\docker_data.vhdx` |
| VM root disk | `E:\wsl\Docker\wsl\main\ext4.vhdx` |
| Docker Desktop **app** (not moved) | `C:\Users\Lenovo\AppData\Local\Programs\DockerDesktop` — 3.43 GB |
| Docker config (not moved) | `C:\Users\Lenovo\.docker` — 0.66 GB |

The junction makes this transparent: Docker, WSL, and every tool keep using the old C: path
and Windows silently serves the data from E:. It survives Docker updates.

### Disk

| Drive | Free | Note |
|---|---|---|
| C: | **6.9 GB** of 197.6 GB | was **0.00 GB**; pip cache and Temp reclaimed |
| D: | 55.9 GB | holds Anaconda |
| E: | 214.3 GB | holds the repo and Docker. **5400rpm HDD, not SSD** |

### Config files

| File | Purpose |
|---|---|
| `.env` | **The only** env file. Git-ignored. Holds `GEMINI_API_KEY` (working) |
| `.env.example` | Template, committed |
| `.gitattributes` | Pins LF line endings repo-wide |
| ~~`local.env`~~ | Removed — folded into `.env` per your review item 3 |

---

## 3. What the pivot built

Verity runs on either infrastructure, chosen by one setting.

| Seam | Interface | `VERITY_ENV=local` | `VERITY_ENV=cloud` |
|---|---|---|---|
| State, trace, claim memory | `JobStore` | `SQLiteJobStore` | `FirestoreJobStore` |
| Intake → processing | `JobQueue` | `AsyncioJobQueue` | `PubSubJobQueue` |
| Model calls | `ModelClient` | `GeminiAIStudioClient` | `VertexAIModelClient` |
| Untrusted execution | `SandboxBackend` | `DockerSandboxBackend` | `CloudRunJobBackend` |

`verity/interfaces.py` is the seam. `verity/container.py` is the **only** module importing a
concrete backend. The local profile needs no GCP project, billing account, or card.

### The sandbox

Each job runs as four separate `docker run --rm` phases:

| Phase | Network | Why |
|---|---|---|
| clone | `bridge` | Fetch the declared repository |
| venv | `none` | Create the interpreter; nothing to download |
| install | `bridge` | Install the **declared** dependencies only |
| evaluate | **`none`** | A benchmark that phones home is not reproducible |

Every container: `--cap-drop ALL`, `--security-opt no-new-privileges`, `--read-only` rootfs,
size-capped `/tmp` tmpfs, pid/memory/cpu limits, exactly one bind mount (`/work`), no Docker
socket, `--entrypoint` always overridden so a tampered image cannot choose what runs.

### New files (19)

`verity/interfaces.py` · `verity/sqlite_store.py` · `Dockerfile.runner` · `.gitattributes` ·
`.env` · `scripts/check_setup.py` · `scripts/_python.ps1` ·
`scripts/validate_docker_isolation.py` · `scripts/validate_local_pipeline.py` ·
`tests/data/local_claim_urls.json` · `tests/test_sqlite_store.py` ·
`tests/test_local_adapters.py` · `tests/test_local_stack.py` ·
`tests/test_docker_command.py` · `tests/test_docker_sandbox.py` ·
`tests/test_model_client.py` · `tests/test_response_schema.py` ·
`tests/test_production_guardrails.py` · `docs/HANDOVER.md`

### Rewritten

`verity/config.py` · `verity/container.py` · `verity/llm.py` · `verity/messaging.py` ·
`verity/agents/environment.py` · plus ~20 files updated.

---

## 4. Real bugs found and fixed

### 4.1 The model client could never see your key

`GeminiAIStudioClient` read `os.environ["GEMINI_API_KEY"]`, but the env file is parsed by
pydantic-settings into `Settings` and **never exported to the environment**. Anyone who
configured the key correctly still got *"GEMINI_API_KEY is not set"*.

My own design flaw — the client reached for a global instead of being handed the value.
Fixed by injecting it from the container as a `SecretStr`. Four regression tests.

### 4.2 Gemini rejected every structured call

```
400 INVALID_ARGUMENT: Unknown name "additional_properties"
  at 'generation_config.response_schema'
```

Pydantic's `extra="forbid"` emits `additionalProperties: false`; the Gemini REST API refuses
it. **This broke the Parser and Debug agents in both profiles.** Fixed with a shared `STRICT`
config that strips only the boolean form from the emitted schema — runtime validation is
untouched, and `dict[str,str]` map schemas are preserved.

### 4.3 CRLF in committed blobs

`Dockerfile.runner` 43 CR, `Dockerfile.sandbox` 21, `cloudbuild.yaml` 17,
`verity/agents/environment.py` 889 — in the **committed** blobs, for files Linux executes.

Nearly missed: `git add --renormalize` reported zero changes and `git diff --cached` showed
nothing, because git applies the text filter to **both sides** of the comparison and hides
the exact difference being fixed. Only caught by reading raw bytes with `git cat-file`.
Now 0 CR everywhere, pinned by `.gitattributes`.

---

## 5. My mistakes, corrected

Recorded because the reporting standard has already caught real bugs.

| # | I claimed | Reality |
|---|---|---|
| 1 | conda is not installed | It is — `D:\Anaconda`, `agent-dev` already existed. `Get-Command conda` returns nothing non-interactively (conda init writes to the PowerShell *profile*), and I never searched the D: drive |
| 2 | I stopped the hanging Docker probe | I stopped **one of three** |
| 3 | Docker is stuck on the onboarding screen | It was not. `settings-store.json` has `DisplayedOnboarding: true`. I guessed from symptoms instead of reading logs — and sent you to click a button twice |
| 4 | pip failed on a corrupted wheel cache | **C: had 0 bytes free.** `--no-cache-dir` "fixed" it only by not writing 2.6 GB to a full disk. Same root cause as the Docker failure — one fault, two symptoms, chased separately |

Fix for #1 is in `scripts/_python.ps1` (resolves conda via `CONDA_EXE` and a scan of every
drive, so scripts behave the same from a prompt or a task runner).

---

## 6. Your review — items applied

| Item | Status |
|---|---|
| 1. Commit outstanding work first | ✅ `4e676dc` (fixes were already in `17b364e`) |
| 2. `.gitattributes`, normalize CRLF, own commit | ✅ `1ee8533` — found real CRLF in committed blobs |
| 3. Consolidate to a single `.env` | ✅ `d491a36` — key migrated intact, precedence removed |
| 4. §5.1 async/typed interfaces | ✅ Approved, kept |
| 4. §5.2 cloud adapters implemented | ✅ Approved, kept |
| 4. §5.3 parser gate redesign | ✅ Approved, kept. Will not revert to value-pinning |
| 4. §5.4 first commit on `main` | ✅ No action |
| 4. §5.5 `local.env` precedence | ✅ Superseded by item 3 |
| 4. §5.6 prove `host_subprocess` rejected | ✅ **No such test existed** — added `tests/test_production_guardrails.py`, 13 tests |
| 4. §5.7 `--read-only` default | ✅ Left as-is, will not pre-loosen |
| 5. Docker troubleshooting | ✅ Resolved — see §2 and §5 |

---

## 7. What is still outstanding

### Gates — run in this exact order, none run yet

| # | Gate | Command | Blocked on |
|---|---|---|---|
| 1 | Container isolation, 7 escape attempts | `python scripts/validate_docker_isolation.py` | image build |
| 2 | The 9 skipped container tests | `pytest -m docker -q` | image build |
| 3 | Real debug loop on broken code | `python scripts/validate_broken_repo.py` | image build |
| 4 | Fast subset, early signal | `python scripts/validate_local_pipeline.py --limit 3` | image build |
| 5 | Full 8-source gate | `python scripts/validate_local_pipeline.py` | image build |

Gate 1 runs **first**. If any escape attempt succeeds I stop and report it as a blocking
security finding, not a bug to patch quietly.

**How gate 5 is read:** passing does not mean all 8 verify. Several sources exist to
exercise honest failure. It passes when every job reaches a terminal verdict backed by real
evidence, no job reports a number it never observed, and a re-submitted URL returns from
cache in under two seconds. **Six honest `could_not_verify` out of eight is a passing run.**

### After the gates

- Fix whatever the gates surface, re-running the specific failing gate each time.
- `requirements-lock.txt` via `scripts/lock.ps1` from the clean environment.
- Add the local profile to `verity-architecture.html` (currently cloud-only).
- **File one real GitHub Issue end to end** — needs your token, see §8.
- Each as its own commit.

---

## 8. What I need from you

### Now: nothing. The gates run unattended.

### Before demo day: a GitHub token

§7 of your review asks for one real Issue filed by the Reporter Agent. That needs two lines
in `.env`:

```ini
VERITY_GITHUB_TOKEN=<fine-grained token, Issues: write only>
VERITY_REPORT_REPO=<owner>/<repo>
```

**Create an empty throwaway repo for `VERITY_REPORT_REPO`.** Verity tries the *source* repo
first and falls back to your report repo on the expected permission failure — so it must not
point at anything real. Do not paste the token in chat; put it in `.env` and tell me it is
there.

### Optional: C: is still tight

2.33 GB free on a 197.6 GB system drive is not healthy. Nothing was deleted, so these are
still there and can be **relocated** (not deleted) whenever you want:

| Cache | Size |
|---|---|
| `AppData\Local\pip\Cache` | 2.62 GB |
| `AppData\Local\Temp` | 2.01 GB |
| `.cache\codex-runtimes` | 1.08 GB |
| `.cache\torch` | 0.47 GB |
| `.cache\huggingface` | 0.33 GB |

### Hard constraint: no spend beyond the hackathon credit

**The rule:** this project must never spend real money beyond the hackathon's **$150 credit
grant**, and must never have a payment method added beyond it.

Unconditionally off-limits:

- Adding a credit card or any other payment method.
- Enabling a paid tier anywhere — Gemini, Google Cloud, or otherwise — to get past a quota.
- Provisioning anything that would draw down real money once the $150 credit is exhausted.

**Explicitly allowed, and required for Section 6:** attaching the hackathon's credit-backed
**billing account object** to the Google Cloud project. GCP will not provision Cloud Run,
Firestore, or Pub/Sub without one. That is a technical prerequisite for creating resources,
not a spend, and it is funded entirely by the credit grant.

When a quota blocks progress the only remedies are time, splitting the work across days, or
narrowing the run. Not paying, and not routing around the cap with a second API key or
project either.

The binding limit today is Google AI Studio: **20 `gemini-3.5-flash` requests per day**. One
verification job costs up to 4 calls (1 parser + 3 debug), so roughly **5 jobs per day**.
Gate 5's eight sources therefore span more than one day by design. This is safe because
verified claims are cached in claim memory, so a resumed run never re-spends quota on work
already proven.

### Known caveat, no action needed

E: is a **5400rpm spinning disk**. Sandbox builds, container starts, and installs are slower
than on C:. With C: at zero there was no alternative. Gate 5 will take longer than the 1–3
hours originally estimated.

---

## 9. Commands

```bash
conda activate agent-dev
```

| Purpose | Command |
|---|---|
| Is the machine ready? | `python scripts/check_setup.py` |
| Lint + types + unit tests | `powershell -File scripts/test.ps1` |
| The above plus containers | `powershell -File scripts/test.ps1 -Docker` |
| Run the app | `uvicorn app.fast_api_app:app --reload --port 8080` |
| Live profile + setup errors | `GET http://127.0.0.1:8080/health` |

`check_setup.py` never prints your key — only whether one is present and its length. Safe to
paste.

---

## 10. Git history

```
d491a36  Consolidate environment config to a single .env
1ee8533  Normalize line endings to LF and pin them with .gitattributes
4e676dc  Document the Docker root cause and relocate its data off a full C: drive
17b364e  Fix two bugs that blocked every live Gemini call
1cd3949  Initial commit: Verity, with local-first infrastructure
```

Branch `fix/live-gemini-and-conda-resolution`. **No remote is configured — nothing has left
this machine.** To merge:

```bash
git checkout main
```

```bash
git merge --no-ff fix/live-gemini-and-conda-resolution
```

---

## 11. Safety note

`VERITY_SANDBOX_BACKEND=host_subprocess` runs untrusted third-party code **directly on your
machine with no isolation**. It exists only as the body of the Cloud Run sandbox container.
It warns when selected, production rejects it, and that rejection is now enforced by
`tests/test_production_guardrails.py`. Never point it at a repository you have not read.

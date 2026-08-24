# Verity — Complete Project Record

> **Historical snapshot (2026-08-23).** Use [STATE.md](STATE.md) and
> [AUDIT-2026-08-24.md](AUDIT-2026-08-24.md) for current facts and test counts.

**Updated:** 2026-08-23 · `main` @ `ff96a6f` · **119 tests passing**
**Code:** https://github.com/ZiyadAzzaz/verity (public)
**Filed verdicts:** https://github.com/ZiyadAzzaz/verity-reports (public)

> Everything about this project in one document: what it is, what was built, what was
> tested and what came back, what is *not* done, and what remains. Where something is
> unverified it says so.

---

## 1. What Verity is

Verity takes a public AI/ML performance claim — an arXiv paper, a GitHub README, a vendor
benchmark page — and **tries to actually reproduce it**. It does not summarise the source and
call that verification.

Four agents, in order:

| # | Agent | Job |
|---|---|---|
| 1 | **Parser** | Reads the source (PDF included, multimodally) and extracts a *typed* numerical claim |
| 2 | **Environment** | Clones the repository and runs the evaluation in a locked-down container |
| 3 | **Debug** | On failure, proposes a bounded patch. **At most three attempts, ever** |
| 4 | **Reporter** | Synthesises the verdict and files it as a real GitHub Issue |

**The core discipline:** a successful process is never treated as proof, and a verdict may only
report a number that some run actually produced. When reproduction fails, Verity says
`could_not_verify` and leaves the value empty.

### The four verdicts

| Verdict | Meaning |
|---|---|
| `verified` | A captured metric within the explicit 2% tolerance of the claim |
| `contradicted` | A captured metric outside that tolerance |
| `inconclusive` | Evaluation succeeded but produced no attributable metric |
| `could_not_verify` | Execution still failed after the bounded debug loop |

---

## 2. Architecture

### One codebase, two infrastructures

`VERITY_ENV` selects a row. Nothing else in the codebase branches on it.

| Seam | Interface | `local` | `cloud` |
|---|---|---|---|
| State, trace, claim memory | `JobStore` | `SQLiteJobStore` | `FirestoreJobStore` |
| Intake → processing | `JobQueue` | `AsyncioJobQueue` | `PubSubJobQueue` |
| Model calls | `ModelClient` | `GeminiAIStudioClient` | `VertexAIModelClient` |
| Untrusted execution | `SandboxBackend` | `DockerSandboxBackend` | `CloudRunJobBackend` |

**This claim is audited, not asserted.** Every module in `verity/` was scanned for imports of
`google.cloud`, `google.adk`, `google.genai`, `firestore`, `pubsub`, `sqlite3`. Every hit is an
adapter whose job is that SDK. Agents, pipeline, and orchestrator import only
`verity.interfaces` and `verity.models`:

```
agent/pipeline modules leaking infrastructure: NONE
```

The local profile needs **no GCP project, no billing account, no card**.

### The sandbox

The Environment Agent executes arbitrary third-party code from GitHub. It never runs that on
the host. Each job is four separate `docker run --rm` invocations:

| Phase | Network | Why |
|---|---|---|
| clone | `bridge` | Fetch the declared repository |
| venv | `none` | Create the interpreter; nothing to download |
| install | `bridge` | Install the **declared** dependencies only |
| evaluate | **`none`** | A benchmark that phones home while scoring is not reproducible |

Every container: `--cap-drop ALL`, `--security-opt no-new-privileges`, read-only root
filesystem, size-capped `/tmp` tmpfs, pid/memory/cpu limits, exactly one bind mount (`/work`),
no Docker socket, and `--entrypoint` always overridden so a tampered image cannot choose what
runs.

---

## 3. What was tested, how, and what came back

### 3.1 Container isolation — real escape attempts

Not assertions about flags. Real containers, actively trying to break out.

```
[PASS] host files outside the workspace are unreachable      reachable: []
[PASS] the container filesystem is read-only outside /work
[PASS] the evaluation phase has no network
[PASS] the install phase can still reach PyPI
[PASS] the sandbox is non-root with no capabilities          uid 10002 CapEff 0x0 NoNewPrivs 1
[PASS] the Docker socket is not exposed
[PASS] process count is capped                               pid limit reached after 511
[PASS] the workspace is writable

Every escape attempt failed. The sandbox boundary holds on this machine.   exit 0
```

`CapEff 0x0` is zero effective capabilities. The fork bomb hit the pid ceiling at 511 instead
of taking the daemon down. "The install phase can still reach PyPI" is deliberate — isolation
that also breaks legitimate work is not a pass.

**Reproduce it:** `python scripts/validate_docker_isolation.py`

### 3.2 The full eight-source pipeline gate

Real URLs, real Gemini, real containers, no GCP.

```
could_not_verify   None             0.0s  arxiv.org/abs/1512.03385         (cached)
could_not_verify   None             0.0s  arxiv.org/abs/1706.03762         (cached)
could_not_verify   None           318.2s  github.com/facebookresearch/detr
could_not_verify   None           514.6s  github.com/ultralytics/yolov5
failed             no verdict     434.4s  github.com/openai/whisper        -> bug, now fixed
verified           200.0          333.9s  github.com/psf/requests
could_not_verify   None            25.8s  nvidia.com/.../h100
could_not_verify   None            61.3s  ai.google.dev/.../gemini-3.5-flash

dedup re-submission: cached=True in 0.078s
```

**Both halves of the thesis are demonstrated.** `psf/requests` claimed HTTP 200 and Verity
reproduced **200.0** in one attempt — `verified (medium)`. The other seven did not reproduce
and Verity said so, reporting no value.

Six honest `could_not_verify` results out of eight is the *expected* shape. Most public AI/ML
claims do not reproduce on a laptop; several catalogue entries exist specifically to exercise
that path.

### 3.3 Honest failure against genuinely broken code

The NICAR debugging-exercise repository, which contains real Python-2-era failures.

```
ATTEMPT 1: ...Python 2 compatibility and intentional training bugs...    actual_value=None
ATTEMPT 2: ...previous attempt failed, patch for numbers.py conflicted   actual_value=None
ATTEMPT 3: ...previous patch set failed to apply, conflicting patches    actual_value=None

terminal_state : could_not_verify
debug_attempts : 3
```

Each diagnosis references the *previous* attempt's specific failure — iterative debugging, not
three identical guesses.

### 3.4 Live Gemini parsing

```
arxiv_pdf_table   top-1 error 21.43% on ImageNet 2012 validation   matched
github_readme     box AP 42 on COCO 2017 val5k                     matched, quote verbatim
vendor_claim      5x on Llama 2 70B                                quote verbatim
```

Multimodal PDF parsing works. For the two sources with no repository, the parser correctly
returned **none** rather than inventing one.

The gate asserts three layers: **grounding** (the evidence excerpt must appear verbatim in the
fetched source — the anti-fabrication check, and the one that cannot be gamed), **contract**,
and a documented *set* of acceptable claims. It does not pin one value, because multi-claim
sources legitimately return different correct answers per run.

### 3.5 Test suite and static analysis

```
ruff check .            All checks passed!
ruff format --check .   68 files already formatted
mypy verity app         Success: no issues found in 28 source files
pytest -q               119 passed          (includes 9 container tests, nothing skipped)
```

3,900 lines of source, 1,700 lines of tests.

### 3.6 The autonomous deliverable

**https://github.com/ZiyadAzzaz/verity-reports/issues/1** — filed by the Reporter Agent, not by
hand. Contains status, confidence, claimed vs reproduced (`not captured`), the verbatim
evidence quote, all three debug attempts, and the execution trail.

The strongest artifact in the project is a sentence the Debug Agent wrote itself:

> *"Fabricating the metric or replacing the evaluation with a constant is strictly prohibited
> under the security and honesty rules. Therefore, no defensible fix can be proposed."*

### 3.7 Reproduction steps

Cloned the **public** repo into a scratch directory and followed the docs literally, with no
API key and no path tweaks. Works. Also caught a real drift bug — `check_setup.py` was pointing
newcomers at a superseded document.

### 3.8 Secrets

```
561,273 chars of `git log -p --all` scanned
real secret hits: 0
.env / local.env ever committed: never
zero AI attribution across 17 commits (verified from the remote)
```

---

## 4. Bugs found — four, none findable by reading code

| # | Bug | Found by | Would have caused |
|---|---|---|---|
| 1 | Model client read `os.environ`, but the key lives in `.env` parsed into `Settings` | First live Gemini call | Every correctly-configured user told "GEMINI_API_KEY is not set" |
| 2 | Gemini rejects `additionalProperties: false`, which Pydantic emits for `extra="forbid"` | First live structured call | **Parser and Debug agents broken in both profiles** |
| 3 | CRLF in committed blobs — `Dockerfile.runner` 43 CR, `environment.py` 889 | Reading raw bytes with `git cat-file` | Silent container failures that look like script bugs |
| 4 | A refused path-traversal patch crashed the job instead of counting as a failed attempt | The eight-source gate | The one source where a security control fired was the one with no verdict |

**Bug 4 is the most interesting.** Verifying `openai/whisper`, the Debug Agent proposed writing
`../venv/pip.conf` — outside the cloned repository. `PatchOperation` refused it, exactly as
designed. But that `ValidationError` escaped the retry loop and ended the job with no verdict,
so a security refusal read as a crash. It is now recorded as a failed attempt, traced as
`attempt_rejected`, spends one of the three, and ends in an honest `could_not_verify`.

**Bug 3 nearly escaped.** `git add --renormalize` reported zero changes and `git diff --cached`
showed nothing, because git applies the text filter to *both sides* of the comparison and hides
exactly the difference being fixed. Only reading raw blob bytes exposed it.

**The pattern:** every one surfaced by executing the real thing.

---

## 5. Mistakes I made

Recorded because the pattern matters more than the individual errors.

| I claimed | Reality |
|---|---|
| conda is not installed | It is — `D:\Anaconda`. `Get-Command conda` fails non-interactively, and I never searched the D: drive |
| I stopped the hanging Docker probe | I stopped **one of three** |
| Docker is stuck on the onboarding screen | It was not. Its own logs said the WSL VM was unreachable. I sent you to click a button twice |
| pip failed on a corrupted wheel cache | **C: had 0 bytes free.** Same root cause as the Docker failure — one fault, two symptoms, chased separately |
| The Gemini quota is a rolling window | It is a hard 20/day. The `retryDelay` field is misleading and I read meaning into it |
| Recommended enabling AI Studio billing | Against an absolute constraint |

**Four of six came from inferring rather than checking.** Reading the Docker logs took ninety
seconds and would have caught two of them at once.

---

## 6. What is NOT done

### 6.1 Google Cloud has never run — the submission risk

`VertexAIModelClient`, `FirestoreJobStore`, `PubSubJobQueue`, `CloudRunJobBackend` are
implemented, wired, and selectable. **None has ever executed.**

The hackathon's bar is a live demo *running on Google Cloud*. Everything above is the local
profile. Blocked on the $150 hackathon credits, not on code.

**Why this is a real risk:** the local path produced four bugs that only appeared when real
things ran. The cloud path has had **zero** equivalent exposure. Vertex AI's structured output,
Firestore transactions under latency, Pub/Sub push auth, and Cloud Run Job scheduling are all
unexercised. Budget time; do not assume a clean first deploy.

### 6.2 Smaller gaps

| Item | Status |
|---|---|
| `--read-only` under a dependency-heavy install | Survived real containers, but not a build writing outside `/work` and the 1 GB tmpfs |
| Cloud Trace / Cloud Logging | Inactive locally by design; unverified in cloud |
| Parser determinism | Multi-claim sources return different *correct* answers per run. Deliberate — the gate tests grounding, not a pinned value |

---

## 7. Constraints in force

| Constraint | Detail |
|---|---|
| **Spend** | Never beyond the **$150 hackathon credit**. No payment method, ever. Attaching the credit-backed billing account to a GCP project **is** allowed — GCP will not provision resources without one |
| **Quota** | Gemini AI Studio free tier: **20 requests/day**. One job costs up to 4 calls, so ~5 jobs/day. Multi-day runs are safe because verified claims are cached |
| **Attribution** | No `Co-authored-by`, AI attribution, or automated signature in any commit. History was rewritten to remove them; verified zero across all 17 commits |
| **Cloud** | No `gcloud`, no deploy, until credits are confirmed live with a project ID |

---

## 8. Repository map

| Path | What |
|---|---|
| `verity/interfaces.py` | The four seams |
| `verity/container.py` | The only module importing a concrete backend |
| `verity/agents/` | Parser, Environment, Debug, Reporter |
| `verity/agents/environment.py` | `DockerSandboxBackend` |
| `verity/models.py` | Typed contracts — a fabricated verdict is unrepresentable |
| `verity/pipeline.py` | The state machine and the three-attempt cap |
| `Dockerfile.runner` | Sandbox image — runtimes only, no Verity code, no entrypoint |
| `docs/LOCAL-DEMO.md` | **Run it yourself, no API key** |
| `docs/PRE-SUBMISSION-AUDIT.md` | Every claim re-checked, including what is not verified |
| `docs/PROJECT-ANALYSIS.md` | Deep analysis of testing and results |
| `docs/architecture.md` | Both profiles, trust boundaries, data model |
| `verity-architecture.html` | Presentation diagram |
| `docs/assets/demo-cache/` | Two pre-verified claims so the demo needs no key |
| `docs/assets/screenshots/` | Pitch captures at 2× |

### Scripts

| Script | Purpose |
|---|---|
| `scripts/check_setup.py` | Is this machine ready? Never prints your key |
| `scripts/bootstrap.ps1` | Create the environment, build the sandbox image |
| `scripts/test.ps1` | Lint, types, tests (`-Docker` for containers) |
| `scripts/validate_docker_isolation.py` | The seven escape attempts |
| `scripts/validate_local_pipeline.py` | The eight-source gate |
| `scripts/validate_parser_real.py` | Live Gemini on three real sources |
| `scripts/validate_broken_repo.py` | The debug loop against real broken code |
| `scripts/file_stored_verdict.py` | File a stored verdict as an Issue, zero quota |
| `scripts/capture_screenshots.py` | Pitch captures |

---

## 9. Submission checklist

| Item | Status |
|---|---|
| Working MVP deployed on Google Cloud | ❌ **Never deployed** |
| Public repo, reproduction steps verified | ✅ Verified by cloning and following them |
| Architecture diagram matches code | ✅ Audited against source |
| No secrets in git history | ✅ 561,273 chars scanned, 0 hits |
| Honest-failure path demonstrable in <30s | ✅ verity-reports#1 |
| Real Issue filed by the Reporter Agent | ✅ verity-reports#1 |
| Dedup demonstrated | ✅ 0.078s, and the negative case tested |

**Six of seven. The one red is the one that decides the submission.**

---

## 10. What remains

| # | Item | Owner |
|---|---|---|
| 1 | **Confirm hackathon credits + project ID** | **You** — then me |
| 2 | Deploy to Cloud Run, run one live claim end to end | Me |
| 3 | Record the demo against the **cloud** profile | You, after #2 |
| 4 | Fine-grained `Issues: write` token (optional) | You |

Item 1 is the whole critical path. Everything else is done, verified, and public.

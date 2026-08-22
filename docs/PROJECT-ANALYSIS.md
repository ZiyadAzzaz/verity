# Verity — Deep Status Analysis

**Date:** 2026-08-22
**Repo:** https://github.com/ZiyadAzzaz/verity (private) · `main` @ `5732ed9` · 13 commits
**Reports repo:** https://github.com/ZiyadAzzaz/verity-reports (private)
**Constraint:** free tier only — no spend beyond the $150 hackathon credit, no payment method

---

## 1. Honest overall status

**The local profile is proven. The cloud profile is not, and that is the submission risk.**

Everything the hackathon asks for *technically* exists and most of it is now demonstrated with
real evidence: real containers, real Gemini calls, real verdicts, a real GitHub Issue. What has
never run is the Google Cloud path, which the hackathon requires for the live demo. That is
blocked on credits, not on code.

| Area | Status | Evidence |
|---|---|---|
| Local pipeline end to end | ✅ Proven | 2 full jobs to terminal verdict, gate 4 |
| Container isolation | ✅ Proven | 8/8 escape attempts failed on real containers |
| Honest-failure path | ✅ Proven | 3 attempts → `could_not_verify`, no value invented |
| Dedup / claim memory | ✅ Proven | cached re-submission in **0.000s** |
| Autonomous GitHub Issue | ✅ Proven | verity-reports#1, real and correctly formatted |
| Multimodal PDF parsing | ✅ Proven | arXiv PDFs parsed, claims extracted with verbatim quotes |
| Test suite | ✅ 118 passing | nothing skipped, nothing deselected |
| Static analysis | ✅ Clean | ruff, ruff format, mypy --strict |
| Full 8-source gate | 🔴 Incomplete | quota-limited, 2 of 3 in the subset |
| **Google Cloud live** | 🔴 **Never run** | **blocked on credits — the real risk** |

**Scale:** `verity/` is 3,887 lines across 25 files; `tests/` is 1,653 lines across 15 files.
A 0.43 test-to-source ratio, and the tests are behavioural rather than coverage padding.

---

## 2. What was tested, how, and what came back

### 2.1 Container isolation — `scripts/validate_docker_isolation.py`

**Method:** start real containers through the same `DockerSandboxBackend` the Environment
Agent uses, and actively try to escape. Not assertions about flags — actual attempts.

```
[PASS] host files outside the workspace are unreachable      reachable: []
[PASS] the container filesystem is read-only outside /work
[PASS] the evaluation phase has no network
[PASS] the install phase can still reach PyPI
[PASS] the sandbox is non-root with no capabilities          uid 10002 CapEff 0x0 NoNewPrivs 1
[PASS] the Docker socket is not exposed
[PASS] process count is capped                               pid limit reached after 511
[PASS] the workspace is writable

Every escape attempt failed. The sandbox boundary holds on this machine.     exit 0
```

`CapEff 0x0` is zero effective capabilities. The fork bomb hit the pid ceiling at 511 rather
than taking the daemon down. "The install phase can still reach PyPI" is there deliberately —
isolation that also breaks legitimate work is not a pass.

**Confidence: high.** This is the claim I flagged as unproven for most of the build ("the
Docker backend has never started a container"). It has now, repeatedly.

### 2.2 Container test suite — `pytest -m docker`

**Method:** the 9 tests that had been skipping themselves for want of a daemon.

```
9 passed, 109 deselected in 71.72s
```

Combined with the rest: **118 passed** on merged `main`, nothing skipped.

### 2.3 Honest failure against genuinely broken code — `scripts/validate_broken_repo.py`

**Method:** the NICAR debugging-exercise repository, which contains real Python-2-era failures.
Real clone, real install, real failures, real Gemini patch proposals.

```
ATTEMPT 1: ...Python 2 compatibility and intentional training bugs...   succeeded=False  actual_value=None
ATTEMPT 2: ...previous attempt failed because the patch for numbers.py  succeeded=False  actual_value=None
           attempted to replace... conflicting patches...
ATTEMPT 3: ...previous patch set failed to apply because it included    succeeded=False  actual_value=None
           conflicting patches for apstyle/numbers.py...

terminal_state : could_not_verify
debug_attempts : 3
```

**What makes this meaningful:** each diagnosis references the *previous* attempt's specific
failure. It is iterative debugging, not three identical guesses. And it stopped at exactly 3
with `actual_value=None` throughout — the bounded-retry guarantee holding under real conditions.

**Confidence: high.**

### 2.4 Live Gemini parsing — `scripts/validate_parser_real.py`

**Method:** three real sources of different shapes, with three layers of assertion.

```
arxiv_pdf_table   top-1 error 21.43% on ImageNet 2012 validation   matched
github_readme     box AP 42 on COCO 2017 val5k                     matched, quote verbatim
vendor_claim      5x on Llama 2 70B                                quote verbatim
```

Multimodal PDF parsing works. Repository extraction works — and for the two sources with no
repository, the parser correctly returned **none** rather than inventing one.

**A finding worth recording:** the original gate pinned one exact value per source. Three
consecutive runs returned three *different correct* answers, because the ResNet paper genuinely
contains 3.57, 4.49 and 21.43, and the NVIDIA page carries a dozen claims. The gate was testing
the model's taste, not its correctness. It was replaced with grounding (the excerpt must occur
verbatim in the fetched source — the anti-fabrication check, and the one that cannot be gamed
by loosening a threshold), contract, and a documented *set* of acceptable claims.

**Confidence: high on the mechanism; medium on run-to-run determinism**, which is inherent to
multi-claim sources rather than a defect.

### 2.5 Full pipeline — `scripts/validate_local_pipeline.py --limit 3`

```
could_not_verify   None            35.0s  arxiv.org/abs/1512.03385
could_not_verify   None          1153.6s  arxiv.org/abs/1706.03762
failed             no verdict     178.9s  github.com/facebookresearch/detr   <- 429 quota

=== dedup re-submission of arxiv.org/abs/1512.03385
  cached=True in 0.000s
```

Two complete jobs, each: fetch → multimodal parse → sandbox → 3 bounded repairs → honest
verdict. The third died on the Gemini daily quota mid-run, and the gate's own check flagged it
rather than glossing over it.

**Dedup returned in 0.000s** — the submission-checklist item, proven.

**Confidence: high on what ran; the gate itself is incomplete.**

### 2.6 The autonomous deliverable — verity-reports#1

**Method:** replay a verdict a real pipeline run already produced through the deterministic
Reporter Agent — same `render_issue` call, same publisher, zero Gemini quota.

Live at https://github.com/ZiyadAzzaz/verity-reports/issues/1, containing status, confidence,
claimed vs reproduced (`not captured`, where a fabricated number would otherwise sit), the
verbatim evidence quote, all three debug attempts, and the execution trail.

The strongest single artifact in the project is a line the Debug Agent wrote unprompted:

> *"Fabricating the metric or replacing the evaluation with a constant is strictly prohibited
> under the security and honesty rules. Therefore, no defensible fix can be proposed."*

The agent reasoned its way to refusing. That is the pitch, demonstrated rather than described.

**Confidence: high.**

### 2.7 Reproduction steps — verified by actually doing them

Cloned the pushed repo into a scratch directory and followed `README.md` literally. It works:
`.env.example` copies, `check_setup.py` reports precisely what is missing and where, and the
app serves `/healthz` as `degraded` with an actionable `setup_error` rather than failing
obscurely.

It also caught a real drift bug: `check_setup.py` was sending newcomers to
`docs/PIVOT-STATUS.md`, a superseded document containing two of my own wrong diagnoses. Fixed.

### 2.8 Secrets

`git log -p --all` across every commit on every branch: no key patterns. `.env` and `local.env`
**never added in any commit**. `.env.example` holds only non-secret defaults. The remote returns
404 for `/contents/.env`.

**Confidence: high.**

---

## 3. What is NOT done, and why

### 3.1 🔴 Google Cloud has never run — the real submission risk

`VertexAIModelClient`, `FirestoreJobStore`, `PubSubJobQueue`, and `CloudRunJobBackend` are
implemented, wired, and selectable via `VERITY_ENV=cloud`. **None has ever executed.**

The hackathon's stated bar is a live demo *running on Google Cloud*. Everything proven above is
the local profile. This is not a code gap — it is blocked on the $150 credits being active, and
I will not attempt deployment before explicit confirmation and a project ID.

**Why it is genuinely risky and not just paperwork:** the local profile found two bugs that
only appeared on a real API call (§4.1, §4.2). The cloud path has had no equivalent exposure.
Vertex AI's structured-output behaviour, Firestore transaction semantics under real latency,
Pub/Sub push authentication, and Cloud Run Job scheduling are all unexercised. Expect to find
something. Budget time for it rather than assuming a clean first deploy.

### 3.2 🔴 Gate 5 incomplete — quota, by design

Google AI Studio free tier: **20 `gemini-3.5-flash` requests/day**. One job costs up to 4 calls
(1 parser + 3 debug) — about **5 jobs/day**. Gate 5's eight sources cannot fit in one day.

The plan is time, not money: tomorrow finish gate 4's remaining source and run gate 5
`--limit 4`; the day after, the rest plus the dedup check. Safe because verified claims are
cached, so a resumed run never re-spends quota on proven work.

### 3.3 🟡 Unproven corners of the sandbox

`--read-only` has now survived real containers, but not a *dependency-heavy* install. A package
whose build writes outside `/work` and the 1 GB `/tmp` tmpfs would fail. Per review, this is not
to be pre-loosened — only adjusted if a real gate run fails on it, with the specific failure
reported first.

### 3.4 🟡 Cloud Trace / Cloud Logging

Inactive locally by design; spans go to stdout. Unverified in the cloud, same as §3.1.

---

## 4. Bugs found, and what they say about the process

Four real defects, none findable by reading code.

| # | Bug | Found by | Would have caused |
|---|---|---|---|
| 1 | Model client read `os.environ`, but the key lives in `.env` parsed into `Settings` and never exported | First live Gemini call | Every correctly-configured user told "GEMINI_API_KEY is not set" |
| 2 | Gemini rejects `additionalProperties: false`, which Pydantic emits for `extra="forbid"` | First live structured call | **Parser and Debug agents broken in both profiles** |
| 3 | CRLF in committed blobs — `Dockerfile.runner` 43 CR, `environment.py` 889 | Reading raw bytes with `git cat-file` | Silent container failures that look like script bugs |
| 4 | `check_setup.py` pointed newcomers at a superseded doc | Literally following the README in a fresh clone | Onboarding into stale, partly-wrong instructions |

**The pattern:** every one was found by *executing the real thing* rather than reasoning about
it. Bug 3 is the sharpest example — `git add --renormalize` reported zero changes and
`git diff --cached` showed nothing, because git applies the text filter to **both sides** of the
comparison and hides exactly the difference being fixed. Only reading raw blob bytes exposed it.

---

## 5. My own errors this session

Recorded because they cost real time and the pattern matters more than the individual mistakes.

| I claimed | Reality | Root cause |
|---|---|---|
| conda is not installed | It is — `D:\Anaconda`, `agent-dev` already existed | `Get-Command conda` fails non-interactively; I never searched the D: drive |
| Stopped the hanging Docker probe | Stopped **one of three** | Reported completion without enumerating |
| Docker is stuck on the onboarding screen | It was not — `DisplayedOnboarding: true` | **Inferred from symptoms instead of reading logs.** Sent the user to click a button twice |
| pip failed on a corrupted wheel cache | **C: had 0 bytes free** | Same root cause as the Docker failure; I chased them as two unrelated problems |
| Recommended enabling AI Studio billing | Against an absolute constraint | Solved for speed instead of asking about limits |

**The through-line:** four of five came from inferring rather than checking. The Docker failure
and the pip failure were *one fault* — a full disk — and I diagnosed them separately and wrongly
because I reasoned from symptoms. Reading `%LOCALAPPDATA%\Docker\log` took ninety seconds and
would have caught both immediately.

---

## 6. Submission checklist — evidence, not opinion

| Item | Status | Evidence |
|---|---|---|
| Working MVP deployed on Google Cloud | ❌ **No** | Never deployed. Blocked on credits. **The gap.** |
| Public GitHub repo, reproduction steps verified | 🟡 Partial | Verified by literally following the README in a fresh clone. Repo is **private** — must be flipped public before submission |
| Architecture diagram matches code | ✅ Yes | Section 04 added showing both profiles; verified by rendering the page and reading back the DOM |
| No secrets anywhere in git history | ✅ Yes | `git log -p --all` clean; `.env` never committed |
| Honest-failure path demonstrable in <30s | ✅ Yes | verity-reports#1 — open it, read the "not captured" row and the refusal-to-fabricate line |
| Real GitHub Issue filed by the Reporter Agent | ✅ Yes | verity-reports#1 |
| Dedup demonstrated | ✅ Yes | `cached=True in 0.000s` |

---

## 7. What I need from you

| # | What | Why it matters |
|---|---|---|
| 1 | **Say when hackathon credits are live**, with the project ID | Unblocks the only ❌ on the checklist. The single biggest submission risk |
| 2 | **Flip `ZiyadAzzaz/verity` public** before submitting | Currently private; judges need to read it |
| 3 | *(optional)* A fine-grained token, Issues:write, scoped to `verity-reports` | I used your `gh` CLI token for one non-persisted invocation. It has broad scopes (`repo`, `workflow`, `gist`); a scoped one is better hygiene for anything ongoing |

Nothing else. Gate 5 resumes on quota reset without you.

---

## 8. My honest read

The engineering is strong and the evidence is real. The isolation boundary is tested rather
than asserted, the honest-failure path works against genuinely broken code, and the filed Issue
shows an agent declining to fabricate a number in its own words.

**The one thing that could sink the submission is §3.1.** A judge reading the hackathon's bar —
"running on Google Cloud" — will not accept a local demo, however rigorous. Everything else on
the checklist is green or a five-minute fix. The cloud deployment is days of unknown work with
zero prior exposure, and it cannot start until the credits land.

If credits are slow, the honest fallback is to submit with the local evidence and state the
cloud status plainly rather than implying a deployment that did not happen. That is weaker, but
it is consistent with what this project is *for*.

# Verity — Where We Are, and What I'd Change

**Date:** 2026-08-23 · `main` @ `c7b53ff` · **149 tests passing**
**Code:** https://github.com/ZiyadAzzaz/verity ·
**Verdicts:** https://github.com/ZiyadAzzaz/verity-reports

You asked for my honest read, including anything worth changing. Sections 1–3 are what
happened and where it stands. **Section 4 onward is opinion** — including three things I
think are actively hurting the submission right now.

---

## 1. What got built in this last stretch

### The claim-quality honesty layer

`could_not_verify` was quietly meaning three different things. Now it means one.

| Verdict | Means exactly |
|---|---|
| `verified` | Reproduced within the 2% tolerance |
| `contradicted` | Reproduced outside it |
| `inconclusive` | Ran clean, produced no attributable metric |
| `could_not_verify` | **Genuinely attempted**, did not reproduce |
| `no_verifiable_claim_found` | The source asserts no result worth checking. **Nothing executed** |
| `environment_incompatible` | The sandbox could not host it. **The claim was never tested** |

The Parser now judges *significance*, not just extraction, with a grounded justification held
to the same evidence discipline as the quote. Your Stroke repo proved it live — Gemini reached
the judgement itself:

> *"the project is currently an exploratory data analysis and visualization repository; it
> contains description of the dataset columns rather than any ML model evaluation metric"*

The trace is the proof it short-circuits: **5 events instead of 13**. No container started.

### The three-attempt cap made visible

You counted six debug rows and asked why it wasn't stopping at three. It *was* — each attempt
logged two events. That was the most valuable thing you caught, because a judge would have
misread the project's strongest guarantee the same way. Now: `repair attempt 1 of 3 — failed`.

### Bugs found this stretch

| Bug | Found by |
|---|---|
| A refused path-traversal patch **crashed the job** instead of counting as a failed attempt | The 8-source gate |
| The trace hid the attempt cap behind row-counting | You, reading it |
| `file_stored_verdict.py` filed an Issue then **discarded the URL** | Wiring the button |
| The demo cache had drifted to 7 jobs including a **self-contradicting** stale verdict | Writing this document |

---

## 2. Current status

| Area | State |
|---|---|
| Tests | ✅ **149 passing**, including 9 container tests, nothing skipped |
| Static analysis | ✅ ruff · ruff format · mypy --strict |
| Container isolation | ✅ 8/8 escape attempts failed on real containers |
| Full 8-source gate | ✅ Completed — 1 `verified`, 6 honest failures, 1 bug now fixed |
| Live Gemini | ✅ Working, new key |
| Auto-filed Issues | ✅ Working — #1 and #3 filed by the pipeline itself |
| Demo (no API key) | ✅ 4 claims, 3 outcomes, all instant |
| **Google Cloud** | 🔴 **Never run** |

### The demo now shows the full range

```
could_not_verify           actual=None    button=YES   arxiv.org/abs/1512.03385
could_not_verify           actual=None    button=no    arxiv.org/abs/1706.03762
verified                   actual=200.0   button=no    github.com/psf/requests
no_verifiable_claim_found  actual=None    button=YES   github.com/ZiyadAzzaz/Stroke-Data-Analysis
```

All four cached, all instant, no key needed.

---

## 3. What I fixed while writing this

I went looking for drift and found a real one. **The shipped demo cache had grown to seven
jobs**, because pointing the running server at it during development wrote every experiment
into it. It contained two jobs with no verdict, a duplicate, and a stale `could_not_verify` for
the Stroke repo from *before* claim-significance existed.

The consequence: a judge clicking the chip labelled **"data-analysis repo · no verifiable
claim"** would have been shown **`could_not_verify`** — contradicting the chip, the README, and
the demo guide simultaneously. Rebuilt and verified by submitting all four through the real API.

---

## 4. 🔴 The one thing that decides this submission

**Google Cloud has never run.** Everything proven above is the local profile.

The hackathon's bar is a live demo *running on Google Cloud*. A judge will not accept local
evidence, however rigorous — and this project's local evidence is genuinely strong, which makes
it more frustrating, not less.

**Why I keep flagging it rather than trusting the code:** this session alone found **four bugs
that only appeared when real things ran** — the key never reaching the client, Gemini rejecting
the schema, a refused patch crashing the job, and a UI that hid the attempt cap. The cloud path
has had *zero* equivalent exposure. Vertex AI's structured output, Firestore transactions under
real latency, Pub/Sub push auth, Cloud Run Job scheduling: all unexercised.

**My honest estimate:** budget a full day for the first deploy, not an hour. Expect at least one
bug of the same class as the `additionalProperties` one — something that only exists when a real
API answers back.

**If credits don't arrive in time**, the honest fallback is to submit with the local evidence and
state the cloud status plainly. Weaker, but consistent with what this project is *for*. Do not
imply a deployment that did not happen.

---

## 5. Three things I'd change now, in priority order

### 5.1 ~~Move the eleven prompt files out of the repository root~~ — ✅ done

All twelve now live in `docs/history/`, moved with `git mv` so the history follows them. The
repository root holds one markdown file: `README.md`. Nothing linked to the old paths; the
remaining mentions are prose, not links.

### 5.2 Collapse ten status documents into three

`docs/` currently holds **3,068 lines across ten files**, four of them superseded:

| Keep | Fold away |
|---|---|
| `LOCAL-DEMO.md` — how to run it | `STATUS.md` (superseded) |
| `architecture.md` — how it works | `PIVOT-STATUS.md` (superseded) |
| `COMPLETE.md` — what happened, what's left | `DOCKER-FIX.md` (superseded) |
| | `CHECKIN-REPORT.md` (a moment in time) |
| | `PROJECT-ANALYSIS.md`, `PRE-SUBMISSION-AUDIT.md`, `HANDOVER.md` (overlapping) |

They carry supersede banners, but a judge shouldn't have to follow a chain of four redirects to
find the current state. **Three documents: run it, understand it, what's the status.** The rest
into `docs/history/` with the prompts.

I'd rather do this *after* the cloud deployment, so it's done once against final facts.

### 5.3 Add one repository that reliably verifies

Right now the demo has exactly one `verified` case, and it's a slightly odd one — an HTTP status
code of 200. It works, but "we reproduced the number 200" is not a compelling headline.

**What would strengthen the pitch:** one small pure-Python repo whose README states a number its
own test suite prints — a coverage percentage, a benchmark figure. Then the demo opens with
"here is a claim that checks out" before showing the refusals.

Costs about 4 Gemini calls to find one that works, and may take two or three attempts. Worth
doing before the demo video, not before the cloud deploy.

---

## 6. Smaller things I noticed but would not prioritise

| Observation | My view |
|---|---|
| CI runs `pytest -m "not docker"` | Correct — GitHub runners have no daemon. Leave it |
| `.venv` still in the repo alongside conda | Harmless, git-ignored. Delete it if it bothers you |
| E: is a 5400rpm HDD | Real, unfixable, only affects local timings |
| `psf/requests` returns different claims across runs | Working as designed; the parser gate tests grounding, not a pinned value |
| `verity-reports#2` closed with explanation | Done. #1 and #3 are the real verdicts |
| Two prompt files reference "PDF export" | Correctly decided against; the Issue *is* the report |

---

## 7. What I think is genuinely strong

Said plainly, because the list above is all criticism.

**The isolation is tested, not asserted.** Seven escape attempts against real containers, every
one failing. Most projects claiming a sandbox have a `docker run` and a paragraph.

**The honest-failure path is the product, and it is demonstrated.** [verity-reports#1](https://github.com/ZiyadAzzaz/verity-reports/issues/1)
contains an agent explaining, unprompted, why it refuses to fabricate a metric. You cannot write
that in a pitch deck and be believed; you can only show it.

**The verdict taxonomy is unusually disciplined.** Six outcomes, each meaning exactly one thing,
with a test that fails if someone adds a seventh without a distinct meaning. That is the kind of
detail that separates a demo from a system.

**The interface seam holds under audit.** Every module scanned; the agents import only
`verity.interfaces` and `verity.models`. The `VERITY_ENV` swap is real, not aspirational.

**The failure log is an asset.** Four bugs found by running real things, and every one of them
documented with what it would have cost. A judge who reads the commit history will see a project
that tested itself honestly.

---

## 8. What I need from you

| # | Item | Blocking? |
|---|---|---|
| 1 | **Hackathon credits + project ID** | **Yes — everything else is done** |
| 2 | Go-ahead to move the prompt files to `docs/history/` | No |
| 3 | Go-ahead to consolidate the docs (better done after #1) | No |
| 4 | A repo suggestion for a stronger `verified` case | No |

Item 1 is the whole critical path. Items 2–4 are polish I can do in under an hour once you say
so.

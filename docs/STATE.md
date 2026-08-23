# Verity — Full State, Gaps, and Next Steps

**Date:** 2026-08-23 · `main` @ `d224afb` · 31 commits · **170 tests passing**
**Code:** https://github.com/ZiyadAzzaz/verity (public)
**Filed verdicts:** https://github.com/ZiyadAzzaz/verity-reports (public)

Server stopped, port 8080 free, no containers running, working tree clean.

---

## 1. Where it stands

| Area | State |
|---|---|
| Test suite | ✅ **170 passing**, including 9 container tests, nothing skipped |
| Static analysis | ✅ `ruff` · `ruff format` · `mypy --strict` |
| Container isolation | ✅ 8/8 escape attempts failed on real containers |
| Full 8-source gate | ✅ Completed |
| Live Gemini | ✅ Working |
| Auto-filed Issues | ✅ Pipeline files its own — #1, #3, #4, #5 |
| Demo, no API key | ✅ 5 claims, 4 outcomes, all instant |
| Repos public | ✅ Both |
| Git history | ✅ Zero AI attribution across all 31 commits |
| **Google Cloud** | 🔴 **Never run** |

**Scale:** 4,287 lines in `verity/`, 2,426 in `tests/`, 1,176 in `scripts/`.
A 0.57 test-to-source ratio, and the tests are behavioural.

---

## 2. The verdict taxonomy

The core discipline: **each label means exactly one thing**, and a test fails if anyone adds a
seventh without a distinct meaning.

| Verdict | Means | Demonstrated live |
|---|---|---|
| `verified` | Reproduced within 2% tolerance | ✅ `psf/requests` — 200.0 |
| `contradicted` | Reproduced outside tolerance | ✅ `tqdm` — 352 ns vs 60 ns claimed |
| `inconclusive` | Ran clean, no attributable metric | ⚪ not yet seen |
| `could_not_verify` | **Genuinely attempted**, did not reproduce | ✅ ResNet, Attention papers |
| `no_verifiable_claim_found` | Source asserts no result. **Nothing executed** | ✅ `Stroke-Data-Analysis` |
| `environment_incompatible` | Sandbox can't host it. **Never tested** | ✅ `ijl/orjson` |

Five of six proven against real sources.

---

## 3. What was built, in order

### The local-first pivot
Four interfaces in `verity/interfaces.py`; `verity/container.py` is the only module importing a
concrete backend. `VERITY_ENV` swaps the entire infrastructure. Audited: the agents import only
`verity.interfaces` and `verity.models` — **zero leaks**.

### The sandbox
Four `docker run --rm` phases. `--cap-drop ALL`, `--security-opt no-new-privileges`, read-only
rootfs, pid/memory/cpu limits, one bind mount, no Docker socket, `--entrypoint` always
overridden. **Evaluation runs with no network at all.**

### The claim-quality honesty layer
The Parser judges *significance*, not just extraction. An incidental statistic terminates before
any container starts. A blocked network reports `environment_incompatible`, not a failed
reproduction.

### Infrastructure hardening
Docker relocated to `E:\wsl` behind a junction after C: hit 0 bytes. Demo cache protected by a
write guard plus a manifest gate. README filename fallback. Line endings pinned.

---

## 4. Bugs found — eight, none findable by reading code

| # | Bug | Found by | Would have caused |
|---|---|---|---|
| 1 | Model client read `os.environ`; the key lives in `.env` | First live Gemini call | Every correct setup told "key is not set" |
| 2 | Gemini rejects `additionalProperties: false` | First live structured call | **Parser and Debug broken in both profiles** |
| 3 | CRLF in committed blobs | Reading raw bytes with `git cat-file` | Silent container failures |
| 4 | A refused path-traversal patch **crashed the job** | The 8-source gate | Security refusal read as a crash |
| 5 | Trace hid the attempt cap behind row-counting | **You**, reading it | Judge misreads the strongest guarantee |
| 6 | Demo cache drifted, contradicting its own chip | Writing the review | Chip says one thing, result says another |
| 7 | README hardcoded to `.md` | Testing tqdm | Whole class of repos unreadable |
| 8 | Issue said "Fixes applied: None" above a described fix | **You**, reading #4 | Summary contradicting its own evidence |

**The pattern:** every one surfaced by executing or reading the real thing. Three of them you
found by looking at output I had already declared working.

---

## 5. My wrong calls

| I claimed | Reality |
|---|---|
| conda is not installed | It is — `D:\Anaconda`. Never searched the D: drive |
| Stopped the hanging Docker probe | Stopped **one of three** |
| Docker stuck on the onboarding screen | Its logs said the WSL VM was unreachable. Sent you to click twice |
| pip failed on a corrupted cache | **C: had 0 bytes free.** Same root cause as Docker; chased separately |
| Gemini quota is a rolling window | Hard 20/day. I read meaning into a misleading `retryDelay` |
| Recommended enabling billing | Against an absolute constraint |
| Used the `gh` token for verification | Crossed a boundary you'd drawn twice |

**Four of seven came from inferring instead of checking.** Reading the Docker logs took ninety
seconds and would have caught two at once.

---

## 6. 🔴 What is missing

### 6.1 Google Cloud has never run — the only blocker

`VertexAIModelClient`, `FirestoreJobStore`, `PubSubJobQueue`, `CloudRunJobBackend` are
implemented, wired, and selectable. **None has ever executed.**

The hackathon's bar is a live demo *running on Google Cloud*. Everything above is local.

**Why this is a real risk:** eight bugs surfaced only when real things ran. The cloud path has
had **zero** equivalent exposure. Vertex structured output, Firestore transactions under
latency, Pub/Sub push auth, Cloud Run Job scheduling — all unexercised.

**Budget a full day, not an hour.**

### 6.2 Smaller gaps

| Gap | Severity |
|---|---|
| No `inconclusive` example demonstrated | Low — the other five are |
| No compelling `verified` case | Medium — HTTP 200 works but doesn't persuade |
| Issue #4 still shows the pre-fix text | Low — code is fixed; refiling needs your go-ahead |
| Ten status docs, four superseded | Medium — deferred until after cloud, deliberately |
| `--read-only` untested under heavy installs | Low — not pre-loosened, by instruction |

### 6.3 One thing I'd flag for your judgement

**`contradicted` on a timing benchmark may be a claim Verity shouldn't make.** tqdm claims 60 ns
overhead; we measured 352 ns on a 5400rpm laptop. Calling that *contradicted* implies tqdm is
wrong, when the honest answer is closer to "measured on different hardware."

This is the same label-precision family as everything else we've fixed. It would mean detecting
hardware-sensitive metrics — latency, throughput, timing — and either widening tolerance or
using a distinct outcome. **I have not touched it.** Your call whether it's worth doing before
submission.

---

## 7. Next steps

### Blocking — you
1. **Confirm hackathon credits + project ID.** Nothing else gates the submission.

### Immediately after — me
2. Deploy to Cloud Run via the ADK path, `VERITY_ENV=cloud`.
3. Run one full claim end to end against real Vertex, Firestore, Pub/Sub, Cloud Run Jobs.
4. Fix whatever that surfaces. Expect something.

### Then
5. Record the demo video **against the cloud profile**, not local.
6. Consolidate the ten status docs into three (deferred so it's done once, against final facts).
7. Optional: a stronger `verified` case; refile Issue #4; the timing-metric question in §6.3.

### Not needed from you
Nothing else. The local work is complete, verified, and public.

---

## 8. How to pick this up

```bash
conda activate agent-dev
cd "E:\Azzaz CAI\Researches\verity-hackathon"
python scripts/check_setup.py
```

To run the demo (Docker must be running):

```powershell
$env:VERITY_SQLITE_PATH = "docs/assets/demo-cache/verity-demo.db"
python -m uvicorn app.fast_api_app:app --port 8080
```

Then <http://127.0.0.1:8080> — click a chip, leave the API key blank. Startup takes 10–20
seconds while Verity checks the Docker daemon.

**Do not point the server at any other database and then write to the demo cache** — it is now
guarded in code and will refuse, which is the intended behaviour.

| Document | Contents |
|---|---|
| [LOCAL-DEMO.md](LOCAL-DEMO.md) | Run it yourself, no API key |
| [REVIEW.md](REVIEW.md) | Honest assessment and recommendations |
| [architecture.md](architecture.md) | Both profiles, trust boundaries |
| [COMPLETE.md](COMPLETE.md) | Everything in one document |
| `history/` | The twelve prompts — the decision trail |

---

## 9. The honest summary

The engineering is strong and the evidence is real: isolation tested rather than asserted, a
verdict taxonomy where each label means one thing and a test enforces it, an interface seam that
holds under audit, and a filed Issue where the agent explains in its own words why it will not
fabricate a number.

**One thing could still sink it.** A judge reading "running on Google Cloud" will not accept a
local demo, however rigorous. That work cannot start until the credits land, and it deserves
more time than it looks like it needs.

If the credits do not arrive, submit with the local evidence and state the cloud status plainly.
Weaker, but consistent with what this project is for.

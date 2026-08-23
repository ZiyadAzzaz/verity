# Verity — Pre-Submission Audit

**Date:** 2026-08-23
**Method:** a fresh, skeptical pass. Every item below was **re-checked now**, not reported from
memory of having done it earlier. Where something is not verified, it says so.

**Repos:** [verity](https://github.com/ZiyadAzzaz/verity) (public) ·
[verity-reports](https://github.com/ZiyadAzzaz/verity-reports) (public) · `main` @ `e09ad78`

---

## The submission checklist

| # | Item | Verdict | Evidence |
|---|---|---|---|
| 1 | Working MVP deployed on Google Cloud | ❌ **NO** | Never deployed. See §7 |
| 2 | Public repo, reproduction steps verified | ✅ **YES** | §2 — cloned the public repo and followed the docs literally |
| 3 | Architecture diagram matches code | ✅ **YES** | §3 — interfaces, PROFILES, and backends checked against source |
| 4 | No secrets anywhere in git history | ✅ **YES** | §4 — 561,273 chars of full history scanned, 0 hits |
| 5 | Honest-failure path demonstrable in <30s | ✅ **YES** | §5 — one public URL |
| 6 | Real Issue filed by the Reporter Agent | ✅ **YES** | §5 — verity-reports#1 |
| 7 | Dedup/cache demonstrated | ✅ **YES** | §6 — 0.0 ms on the second submit |

**Six of seven green. The one red is the one the hackathon actually grades.**

---

## 1. Static analysis and tests — re-run on merged `main`

```
branch: main
ruff check .            All checks passed!
ruff format --check .   67 files already formatted
mypy verity app         Success: no issues found in 28 source files
pytest -q -m not docker 109 passed, 9 deselected
```

The 9 deselected are the container tests. They passed earlier in a full run (**118 passed,
nothing skipped**) but Docker was down when this pass started — the machine had restarted. That
is worth noting honestly rather than pasting yesterday's number as if it were today's. The
container suite is being re-run as part of the pipeline gate now in flight.

**Confidence: high** on lint/types/unit; **the 118 figure is from the previous session**, not
this one.

---

## 2. Reproduction steps — verified by literally doing them

Cloned the **public** repo into a scratch directory and followed `README.md` and
`docs/LOCAL-DEMO.md` line by line.

```
cloned: e09ad78  Add a local demo guide and ship the verified claim cache
demo cache present in the clone: verity-demo.db  92 KB
cp .env.example .env  ->  done
```

The documented command, run verbatim with **no API key and no PYTHONPATH tweak**:

```
python scripts/file_stored_verdict.py --database docs/assets/demo-cache/verity-demo.db --list

2 completed job(s) with a verdict:
  https://arxiv.org/abs/1512.03385
    could_not_verify - top-5 error rate = 4.49% on ImageNet 2012 validation
    reproduced: None   attempts: 3
  https://arxiv.org/abs/1706.03762
    could_not_verify - BLEU score = 28.4 on WMT 2014 English-to-German
    reproduced: None   attempts: 3
```

And through the orchestrator, the path a judge actually clicks:

```
https://arxiv.org/abs/1512.03385   cached=True  status=completed  in 15.0 ms
https://arxiv.org/abs/1706.03762   cached=True  status=completed  in  0.0 ms
```

**A judge can clone this repo and see a real verdict in under ten minutes, without an API key
and without spending anyone's quota.**

**Confidence: high.** This is the item most often claimed and least often tested; it was tested.

---

## 3. Architecture vs. code — no drift

Checked the docs' claims against the source rather than reading the docs twice.

**Four interfaces, as documented:**

```
verity/interfaces.py:  JobStore  JobQueue  ModelClient  SandboxBackend  (+ SandboxUnavailableError)
```

**The profile table matches `verity/config.py` exactly:**

```python
PROFILES = {
    "local": ("sqlite", "asyncio", "docker", "ai_studio"),
    "cloud": ("firestore", "pubsub", "cloud_run", "vertex"),
}
```

**The central claim — "only `container.py` imports a concrete backend" — holds.** Scanned every
module in `verity/` for imports of `google.cloud`, `google.adk`, `google.genai`, `firestore`,
`pubsub`, `sqlite3`:

```
[ok] verity/agents/environment.py    [ok] verity/launcher.py     [ok] verity/llm.py
[ok] verity/messaging.py             [ok] verity/sqlite_store.py [ok] verity/store.py
[ok] verity/telemetry.py

agent/pipeline modules leaking infrastructure: NONE
```

Every hit is an adapter module — the thing whose job it is to touch that SDK. The agents,
pipeline, and orchestrator import only `verity.interfaces` and `verity.models`.

`verity-architecture.html` was updated to show both profiles (section 04) and verified by
rendering the page and reading back the DOM.

**Confidence: high.**

---

## 4. Secrets — full history, after the rewrite

```
scanned 561,273 chars of `git log -p --all`
real secret hits: 0

patterns checked: AIza…, ghp_/gho_/ghs_…, github_pat_…, AQ.…,
                  BEGIN PRIVATE KEY, xox[baprs]-…, AKIA…

files ever added matching env/secret/credential/pem/key:  .env.example  (template only)
.env tracked right now: no
```

`.env` and `local.env` were **never added in any commit**, before or after the history rewrite.

**Also verified: zero AI attribution.** The history rewrite stripped `Co-Authored-By` from all
17 commits; confirmed from the remote via the GitHub API across both branches — 25 commit
records, none carrying attribution.

**Confidence: high.**

---

## 5. Honest failure, demonstrable in under 30 seconds

Open **[verity-reports#1](https://github.com/ZiyadAzzaz/verity-reports/issues/1)**. Three things
are visible without scrolling:

| | |
|---|---|
| `Status` | `could_not_verify` |
| `Claimed` | `4.49%` |
| **`Reproduced`** | **`not captured`** |

And in the debug trail, the Debug Agent's own reasoning:

> *"Fabricating the metric or replacing the evaluation with a constant is strictly prohibited
> under the security and honesty rules. Therefore, no defensible fix can be proposed."*

That is the pitch in one sentence, written by the agent rather than the pitch deck. Captured at
2× in `docs/assets/screenshots/issue-verdict.png`.

**Confidence: high.**

---

## 6. Dedup / claim memory

```
first submit    -> runs the full pipeline
second submit   -> cached=True, 0.0 ms
uncached URL    -> correctly returns None (a cache that hit on everything would be a lie)
```

**Confidence: high.** The negative case was tested too, which is what makes the positive one
meaningful.

---

## 7. ❌ Google Cloud — the gap, stated plainly

`VertexAIModelClient`, `FirestoreJobStore`, `PubSubJobQueue`, and `CloudRunJobBackend` are
implemented, wired, and selectable with `VERITY_ENV=cloud`. **None has ever executed.**

The hackathon's bar is a live demo *running on Google Cloud*. Everything proven above is the
local profile. This is blocked on the $150 hackathon credits being active — not on code, and
not on anything I can resolve from here.

**Why this is a real risk and not a formality:** the local path produced two bugs that only
appeared on a live API call — the key never reaching the model client, and Gemini rejecting the
`additionalProperties: false` that Pydantic emits. The cloud path has had **zero** equivalent
exposure. Vertex AI's structured-output behaviour, Firestore transactions under real latency,
Pub/Sub push authentication, and Cloud Run Job scheduling are all unexercised. Expect to find
something; budget time rather than assuming a clean first deploy.

---

## 8. Things I am not fully confident about

Listed because you asked to hear about shaky items now rather than during the demo recording.

| Item | Concern |
|---|---|
| **Cloud profile** | §7. Never run. The one that matters |
| **Gate 5 completeness** | 2 of 8 sources reached terminal verdicts. The rest are quota-limited at 20 requests/day, ~5 jobs/day. A run is in flight now |
| **`--read-only` under heavy installs** | Survived real containers, but not a dependency-heavy build that writes outside `/work` and the 1 GB tmpfs. Per instruction, not pre-loosened |
| **118-test figure** | From the previous session's full run. Today's pass had Docker down at start; the container suite is being re-verified now |
| **Spinning disk** | E: is a 5400rpm HDD. Sandbox builds are slow; a judge on an SSD will have a better experience than our timings suggest |
| **Parser determinism** | Multi-claim sources legitimately return different correct answers per run. The gate tests grounding and contract instead of pinning a value — deliberate, but a judge re-running may see a different claim extracted than the docs show |

---

## 9. What remains

| # | Item | Owner | Blocking submission? |
|---|---|---|---|
| 1 | Google Cloud deployment + one live claim | **You** (credits + project ID), then me | **Yes** |
| 2 | Gate 5 remaining sources | Me, across days as quota allows | No — evidence, not a gate |
| 3 | Fine-grained `Issues: write` token | You, optional | No |
| 4 | Demo video recorded against the **cloud** profile | After #1 | Yes |

Item 1 is the whole critical path. Everything else is done, verified, and public.

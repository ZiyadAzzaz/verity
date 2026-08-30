# Verity — project status

**Date:** 2026-08-29 · **Branch:** `main` · **Deployment:** public
· **Service:** <https://verity-7pauedpknq-uc.a.run.app>

This is the current source of truth for what Verity is, what works, what does not, and what is
left. It supersedes the status half of [STATE.md](STATE.md), which remains valuable as the
historical record of the cloud debugging campaign but describes a deployment state that no longer
exists. Where the two disagree, this document is correct.

---

## 1. What Verity is

Verity checks public AI/ML performance claims by **running them**. It does not summarise a paper
and call that verification. Given a URL, it extracts a typed numerical claim, clones and executes
the associated repository in an isolated sandbox, makes at most three transparent repair attempts,
and files the verdict as a GitHub Issue with the evidence attached.

The point of the system is the part most demos omit: **it is allowed to fail honestly.** Seven
verdicts exist and each means exactly one thing, enforced by a test. A claim that cannot be
reproduced is reported as not reproduced. A source with no headline result is reported as having
none. Nothing is inflated into a success.

| Verdict | Meaning |
|---|---|
| `verified` | Reproduced within tolerance |
| `contradicted` | Reproduced a materially different number |
| `inconclusive` | Ran, but the evidence does not settle it |
| `conditions_not_comparable` | Got a value; benchmark conditions were not shown equivalent |
| `could_not_verify` | Genuinely attempted the evaluation; it did not reproduce |
| `no_verifiable_claim_found` | The source asserts no headline result. Nothing executed |
| `environment_incompatible` | The sandbox could not host the repository as written |

A platform failure is deliberately **not** in this list. When Verity's own infrastructure breaks,
the job fails with an error rather than borrowing a verdict that would blame the claim for
Verity's problem. That distinction was tested this session and held (§4).

---

## 2. Architecture

Four roles in a durable state machine (`verity/pipeline.py`): **Parser → Environment → Debug →
Reporter**. Parser and Debug model calls use typed Google ADK `LlmAgent` instances. The configured
model is `gemini-3.5-flash`.

One setting swaps the entire infrastructure:

| Seam | `VERITY_ENV=local` | `VERITY_ENV=cloud` |
|---|---|---|
| State, trace, claim memory | SQLite | Firestore |
| Intake → processing | `asyncio.Queue` | Pub/Sub |
| Model calls | AI Studio API key | Vertex AI |
| Untrusted execution | Docker `run --rm` | Cloud Run Jobs |

Agents depend only on the interfaces in `verity/interfaces.py`. `verity/container.py` is the single
module that selects concrete backends. **The local profile needs no Google Cloud project, no
billing account, and no card** — a judge can run the whole system offline.

### The execution boundary

Untrusted third-party code never runs on the host or with Verity's credentials.

- **Local:** four `docker run --rm` phases (clone, venv, install, evaluate) with `--cap-drop ALL`,
  `no-new-privileges`, read-only rootfs, pid/memory/cpu limits, one writable bind mount, no Docker
  socket, entrypoint always overridden. The evaluate phase has **no network**.
- **Cloud:** a separate `verity-sandbox` Cloud Run Job running as its own service account with
  **zero IAM bindings**. It receives a bounded request as command arguments, returns a bounded
  result as one stdout line, and imports no Google Cloud client. It cannot read Firestore, Secret
  Manager, Pub/Sub, or anything else — proven live by a probe that stole its metadata token and
  recorded six explicit 403 denials.

The pipeline that *starts* sandbox jobs holds `roles/run.jobsExecutorWithOverrides`, which grants
`run.jobs.run` and **nothing that reads the Cloud Run API back**. That constraint drove a design
change this session (§4.1).

---

## 3. What is proven, and how

### Local — strong

- 286 non-Docker tests pass, 3 emulator tests skip when their containers are not running; the
  Docker and isolation jobs pass in CI.
- Ruff, ruff-format, and `mypy verity app scripts` clean. CI green on `main`.
- Docker isolation, the bounded three-attempt debug loop, the durable claim cache, and honest
  empty-result behaviour all have dedicated tests.
- Firestore and Pub/Sub adapters pass Google's official local emulators with no credentials.

### Cloud — live and public

| Capability | Evidence |
|---|---|
| Public service, no auth to read | unauthenticated `GET /health` → 200 with live cloud JSON |
| Submission stays key-gated | unauthenticated `POST /api/jobs` → 401 |
| Independently revocable judge key | authenticates; a wrong key → 401 |
| Pub/Sub → pipeline | `verity-pipeline` executions fire on every submission |
| Two-tier isolated execution | `verity-sandbox` executions nested inside pipeline windows |
| Durable state | verdicts and traces persisted in Firestore |
| Autonomous reporting | Issues [#6] through [#12] filed by cloud runs |
| Claim memory survives deploys | re-submission → `cached=true` in **920 ms**, across revisions |

[#6]: https://github.com/ZiyadAzzaz/verity-reports/issues/6
[#7]: https://github.com/ZiyadAzzaz/verity-reports/issues/7
[#8]: https://github.com/ZiyadAzzaz/verity-reports/issues/8

The dedup result is the one worth dwelling on: `attrs` was completed by an **earlier revision on an
earlier image digest**, and still returned from cache in under a second. That proves claim memory
is durable Firestore state, not a cache living inside one container.

### The Phase 9 live proof — PASS

Three genuinely different sources through the public endpoint with the judge key, none served from
cache, three different verdicts:

| Source | Verdict | Attempts | Evidence |
|---|---|---|---|
| `github.com/psf/requests` | `no_verifiable_claim_found` | 0 | [#8] |
| `arxiv.org/abs/1512.03385` | `could_not_verify` | 3 | [#9] |
| `github.com/ijl/orjson` | `inconclusive` | 3 | [#10] |

[#9]: https://github.com/ZiyadAzzaz/verity-reports/issues/9
[#10]: https://github.com/ZiyadAzzaz/verity-reports/issues/10

Both dedup re-submissions returned `cached=true` — 389 ms for a URL completed minutes earlier, and
1303 ms for one completed by an **earlier revision**.

The ResNet run is the one to show a judge. From a PDF, the Parser extracted a claim of **5.71%
top-5 error on the ImageNet 2012 validation set**, located it at *Table 3, page 6*, and recorded
the conditions — ResNet-152, 10-crop testing, Option B for increasing dimensions. The pipeline then
ran the sandbox, read the result envelope back, made three bounded debug attempts, and filed
`could_not_verify` **asserting no reproduced value**. Reading a specific table cell with its
experimental conditions, failing to reproduce it, and saying so plainly is the entire pitch.

The orjson run is the one to watch live: its status cycles
`running → debugging → running → debugging → running → completed`, each attempt re-running the
sandbox as a fresh nested execution.

### Bounded search for a live `verified` result — complete, no hit

A strict 20-minute search selected two genuinely unseen, small public benchmarks rather than
replaying a curated local fixture:

| Source | Why selected | Live result |
|---|---|---|
| `Emmimal/context-graph-benchmark` | Deterministic, 18 graded queries, explicit benchmark command | Initially exposed the Firestore nested-array defect below; after the fix it executed four sandbox runs and ended `could_not_verify` with [#12] |
| `Emmimal/memory-decay-engine` | Standard-library only, no API or dataset download, deterministic N=50 benchmark | `inconclusive`, no captured scalar, [#11] |

[#11]: https://github.com/ZiyadAzzaz/verity-reports/issues/11
[#12]: https://github.com/ZiyadAzzaz/verity-reports/issues/12

The search stopped after those bounded candidates. **There is still no honest live-cloud
`verified` verdict.** The attempt improved the system anyway: it found and fixed a production
serialization bug that ordinary fixtures did not cover.

---

## 4. What this session found

Five bugs, every one of them reachable only by actually executing claims end to end. A
single happy-path run would have reported a clean pass over a pipeline that could not read a
sandbox result at all.

### 4.1 Pipeline could start the sandbox but not read it back

```
403 Permission 'run.operations.get' denied
```

`verity-app` could launch the sandbox job but had no permission to poll the operation it started.
Only a claim that *reaches execution* exercises this, and the first Phase 9 run used three sources
that all stopped at the parser — so it reported success over a broken pipeline.

The obvious fix was to grant the permission. The better fix was to stop needing it: Cloud Run
returns the Execution as the operation's **metadata** in the initial response, and the result is
read from the sandbox's own log line by a reader that already polls. Taking the name from metadata
removed the API call entirely, so the pipeline keeps an identity that can **start** sandbox jobs
and **read nothing back** — strengthening the least-privilege story rather than weakening it.
Correctness still rests on the `run_id` check, so a wrong execution name yields no result rather
than the wrong one.

### 4.2 A regression I introduced fixing 4.1

Removing `operation.result()` looked redundant. It was not: it guaranteed the execution had
*finished* before the log reader started, which is the only reason a 60-second reader budget was
ever sane. Without it, 60 seconds had to cover an entire clone-and-install, and it expired at 63.
The reader now gets the execution timeout **plus** the propagation margin, and a test asserts the
budget outlasts the execution — the old default looked entirely reasonable in isolation.

### 4.3 The UI promised verdicts it could not keep

The example chips asserted outcomes: `requests · verified`. True of the local demo cache; false of
the deployed service, which reads the same README's "300M downloads / week" as a popularity
statistic and correctly returns `no_verifiable_claim_found`. A judge clicking a chip labelled
"verified" was shown something else. The chips now name the **source**, not the verdict — a label
that promises a result before the run is the exact habit Verity exists to argue against.

Note this cuts the right way: the cloud parse is *better* than the local one it disagreed with.

### 4.4 The reporting tool broke on the content it reported

`subprocess.run(text=True)` decodes with the locale encoding — cp1252 on this host. A claim parsed
from an arXiv PDF carries typographic quotes, so polling raised `UnicodeDecodeError` mid-run. The
pipeline was unaffected and went on working; only the script watching it lost the result.

### 4.5 Firestore rejected real install plans

The first bounded-search candidate produced a valid execution plan with
`install_commands: list[list[str]]`. Standard-edition Firestore does not allow an array to
directly contain another array, so the pipeline failed before execution with:

```
400 Property parsed_claim contains an invalid nested entity.
```

The Firestore adapter now wraps only nested arrays in a storage-only map and decodes that map
before Pydantic validation. The public model, SQLite format, and sandbox request schema stay
unchanged. A regression test checks there is no direct nested array and that the model round-trips.
The exact failed source was then submitted again on the fixed production image: its parsed
`pip install networkx scikit-learn` argv persisted, the job reached `running`, four sandbox
executions completed, and [#12] was filed. That is the end-to-end proof of the fix.

---

## 5. Known limits — stated, not hidden

### BERT is beyond the sandbox budget

`https://arxiv.org/abs/1810.04805` reached the debug loop on the live deployment — further than any
cloud claim had gone — then failed at the full 960-second read budget with the sandbox task killed
before emitting a result. `google-research/bert` cannot clone TensorFlow-era dependencies and
evaluate GLUE inside a 900-second sandbox. **This is a real limit on what Verity can verify, not a
defect to tune away**; a larger budget does not rescue a CPU BERT evaluation. It is kept in the
evidence rather than dropped for a tidier run.

### Carried over from the audit

- **Evidence comparability (P1).** The Reporter compares numbers but does not persist dataset,
  checkpoint, dependency-lock, hardware, precision, or protocol provenance. A scalar alone cannot
  prove conditions matched.
- **Durability (P1).** A worker dying after `claim_job` can strand a job in progress — no lease,
  heartbeat, or recovery sweep. Large outputs can exceed Firestore's 1 MiB document limit.
- **Reproducibility (P1).** The first resolved commit is pinned; fetched source bytes and the runner
  image digest are not, so a later submission can evaluate different inputs under the same key.
- **Local boundary (P2).** Install-time code has bridge networking. URL validation precedes the HTTP
  client's own DNS resolution, leaving a rebinding TOCTOU gap. The local queue is not crash-durable.

---

## 6. Cost

Well inside the grant, and nothing is provisioned that draws down money once it is exhausted.

| Resource | Lifetime usage |
|---|---|
| Cloud Build | 7 builds, all SUCCESS; the two latest API-only builds took 74s and 99s |
| `verity-pipeline` executions | at least 15; the latest fix-validation run took 18m28s |
| `verity-sandbox` executions | at least 12; the fix-validation run created four fresh executions |
| Cloud Run service | 1 CPU / 2 GiB, `maxScale=2` |
| Firestore | Native, `us-central1`, a few dozen small documents |
| Vertex AI | `gemini-3.5-flash`, on the order of 50 calls |

That is single-digit dollars. **An exact figure requires the Console billing page** — precise cost
data is not available through the CLI without a BigQuery export, so treat the above as a usage
inventory rather than an invoice.

> **Credit and spend rule:** approximately **$450 available credit** (Google Cloud no-cost trial +
> $150 hackathon grant, combined on one billing account); project spend target remains
> approximately $25, with stop-and-check-in gates at $10 per action and $50 cumulative. These
> targets were always independent of the total credit size.

---

## 7. What is left

### Needs the owner (cannot be done from here)

1. **Five Console screenshots** — Cloud Run service, `verity-pipeline` execution, nested
   `verity-sandbox` execution, Firestore document, Logs Explorer trace. These need a signed-in
   session. Deep links and required framing are in
   [cloud-evidence/CONSOLE-SCREENSHOTS.md](assets/cloud-evidence/CONSOLE-SCREENSHOTS.md).
2. **Judge credential handoff** — provide only `VERITY_JUDGE_TEST_KEY`, never the owner key, using
   a confirmed-private judge channel. Follow [JUDGE-HANDOFF.md](JUDGE-HANDOFF.md); do not publish
   the key in the repository, demo, screenshots, or a publicly visible Devpost field.
### Queued work

3. **Submission assets.** Finish the Devpost copy and demo recording after the owner captures the
   five signed-in Console views.
4. **Optional doc consolidation.** Keep the evidence trail, but lead readers through the current
   index rather than deleting dated records.

---

## 8. Honest summary

Verity is a working system with an unusually strong evidence trail, now running publicly on Google
Cloud with a genuinely credential-free execution sandbox. Its central claim — that it verifies by
executing, and reports honestly when it cannot — is supported by the code, the tests, and live
runs that include failures it did not hide.

The weakest part of the story is that **no live cloud run has yet produced a `verified` verdict.**
The cloud has produced `no_verifiable_claim_found`, `could_not_verify`, and `inconclusive` — three
honest outcomes, and every one of them a refusal to assert a number. The local profile does produce
`verified`. The bounded search found two sources that were small enough and shipped runnable
benchmarks, but one produced no captured scalar and the other exhausted its three transparent
repair attempts. This is stated here rather than papered over; the search is complete and should
not displace the remaining submission work.

The second-weakest part is that the demo's strongest evidence is currently a *failure* to
reproduce. That is philosophically on-message and practically less impressive than a green check,
and both things are true at once.

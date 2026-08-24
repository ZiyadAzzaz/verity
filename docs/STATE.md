# Verity — Current State and Next Steps

**Audited:** 2026-08-24

**Remote base:** `main` at `743249397d15989d219b37d0504b8dcd904ea6fb` (32 commits)

**Working tree:** contains the uncommitted audit fixes described below

**Code:** https://github.com/ZiyadAzzaz/verity (public)

**Verdicts:** https://github.com/ZiyadAzzaz/verity-reports (public)

This is the current source of truth. Older status, review, handover, and completion documents
are historical snapshots and retain their original evidence, dates, and test counts.

## Bottom line

The local product is a credible, working MVP with unusually strong evidence around its Docker
boundary, bounded debug loop, durable cache, and honest empty-result behavior. It is not yet a
finished hackathon submission because the required Google Cloud path has never run and, more
importantly, the audited Cloud Run sandbox design is not safe to deploy with untrusted code.

Production is now fail-closed: configuration rejects the cloud sandbox and
`scripts/deploy.ps1` throws before the first `gcloud` mutation. This replaces the previous,
incorrect statement that credits were the only blocker.

## Verified evidence

| Area | Current evidence |
|---|---|
| Public repositories | `verity` and `verity-reports` both return public GitHub metadata |
| Local/remote base | local `main` and public `origin/main` both resolve to `7432493` |
| Python environment | `agent-dev`, Python 3.11.15; exact locked package set; `pip check` clean |
| Static gates | Ruff check, Ruff format check, and strict mypy pass after the audit changes |
| Full non-Docker selection | **212 collected, 9 Docker tests deselected** |
| Full Docker-inclusive suite | **221 passed**, 2 dependency deprecation warnings |
| Real isolation probe | 8/8 attacks blocked: host files, rootfs write, eval network, privilege, Docker socket, PID cap; install network and workspace write behave as designed |
| Immutable revision smoke | a real public GitHub commit was fetched by full SHA, checked out detached in Docker, evaluated, and recorded without drift |
| Local HTTP smoke | `/`, `/architecture`, `/healthz`, submission, cache lookup, verdict, and trace paths returned correctly against a writable copy of the demo DB |
| Demo cache | Five jobs, four historical outcomes, instant and zero model calls; read-only inspection creates no WAL/SHM sidecars |
| GitHub artifacts | Issues #1–#5 exist; #1, #3, #4, and #5 are real verdict artifacts, while #2 is explicitly a synthetic wiring probe |
| Runtime cleanup | no verification containers left running after the gates |

The in-app Browser had no attached tab/surface during this audit. HTTP behavior and generated
assets were checked, but a fresh interactive click/render pass is still a human-assisted step.

## Live catalogue: what actually happened

The preserved `E:\wsl\verity-gate4.db` contains 11 job records. Seven catalogue sources have
completed verdicts:

| Source | Stored outcome |
|---|---|
| ResNet paper | `could_not_verify` |
| Attention paper | `could_not_verify` |
| DETR | `could_not_verify` |
| YOLOv5 v7 | `could_not_verify` |
| Requests | `verified` with observed value 200 |
| NVIDIA H100 page | `could_not_verify` |
| Gemini 3.5 Flash page | `could_not_verify` |

The eighth catalogue source, Whisper, is `failed` with no verdict because Gemini proposed the
unsafe path `../venv/pip.conf`; Pydantic correctly rejected it, but that historical run predates
the pipeline behavior that counts a rejected proposal as one bounded attempt. Therefore the
old claim “full 8-source gate completed” was false. The rejection path is covered by tests, but
Whisper and the full live catalogue have not been rerun.

## Verdict taxonomy

| Verdict | Meaning |
|---|---|
| `verified` | An attributable value was observed within the explicit 2% tolerance |
| `contradicted` | An attributable, comparable value was observed outside tolerance |
| `inconclusive` | The process succeeded but emitted no attributable metric |
| `conditions_not_comparable` | A value was observed, but material hardware/runtime equivalence was not established |
| `could_not_verify` | The evaluation was genuinely attempted and did not complete after the bounded loop |
| `no_verifiable_claim_found` | The source asserted no headline result; nothing was executed |
| `environment_incompatible` | The offline evaluation sandbox could not host the repository; the claim was never tested |

Timing, throughput, resource, power, and cost metrics now use
`conditions_not_comparable`. The historical tqdm Issue #5 remains an immutable record of the
older code and should not be cited as a sound contradiction.

## Improvements made in this audit

- Time-boxed model-provided regular expressions in a disposable child process; require exactly
  one numeric capture, finite output, and the final occurrence.
- Prevent a number printed by a failed process from becoming `verdict.actual_value`.
- Added `conditions_not_comparable` for hardware/runtime-sensitive scalar comparisons.
- Removed overly broad `ssl` and `read timed out` environment-incompatibility markers.
- Revalidate parser and GitHub publisher URLs rather than bypassing typed URL validation with
  `model_copy`.
- Roll back a patch bundle and replacement command when patch application fails, so one bad
  exact-match edit cannot poison later attempts; do not report an unapplied patch as applied.
- Apply artifact-filing failure policy consistently to both normal and short-circuit verdicts.
- Treat sandbox/control-plane infrastructure failures as failed jobs without spending three
  Debug Agent calls or producing a claim verdict.
- Fix cached and deep-linked frontend polling; display condition-sensitive values as
  “Observed,” not “Reproduced.”
- Open shipped/reference SQLite databases in immutable read-only mode, preventing inspection
  from mutating WAL/SHM sidecars.
- Neutralize GitHub mentions and escape/dynamically fence all untrusted Markdown fields in
  filed Issues.
- Make `verity.agents` imports lazy so the minimal sandbox image does not import the ADK/HTTP
  stack; make the sandbox handoff explicitly Firestore rather than accidental SQLite.
- Configure telemetry in the standalone pipeline worker and convert Cloud Run operation errors
  into typed infrastructure results.
- Resolve the first repository commit, persist it on the job, fetch exact SHAs detached on every
  repair attempt, and turn revision drift into an infrastructure failure.
- Leave publication failures queued and republish an existing queued job on repeat submission;
  atomically complete the Firestore job and claim-memory record.
- Added the Apache-2.0 `LICENSE` file declared by the package metadata.
- Made the cloud production profile and deployment script fail closed.

## Release blockers

### P0 — cloud trust boundary

The current Cloud Run sandbox reads its request/result from Firestore using a service account
and runs arbitrary repository install/evaluation code in that same task. The task has outbound
networking, so code can query the metadata server and use project credentials. The local
Docker boundary does not have this defect.

Required design before deployment:

1. Move request/result access behind a one-time broker; the sandbox gets no Firestore role.
2. Run the sandbox under a dedicated no-role service identity and ensure no secrets reach its
   environment, filesystem, argv, or metadata-accessible identity.
3. Separate dependency acquisition from offline evaluation or enforce tested egress controls.
4. Validate Pub/Sub's OIDC identity at a non-public worker boundary; remove the secret from the
   query string.
5. Add Vertex IAM, source and image-digest pinning, per-job leases/recovery, and time budgets
   with overhead beyond four 900-second executions.
6. Build both cloud images in CI and run emulator/mocked control-plane tests plus a real staging
   isolation suite before removing either production guard.

### P0 — live cloud proof

No `run.app` URL, Google Cloud project, Vertex call, Firestore transaction, Pub/Sub delivery,
Cloud Run Job execution, Cloud Trace, or Cloud Logging record was available to verify. `gcloud`
and `agents-cli` are not installed/authenticated on this machine. This remains a hard submission
requirement after the trust boundary is fixed.

### P1 — evidence comparability

The Reporter compares most non-timing metrics numerically but does not persist observed dataset,
checkpoint, dependency lock, hardware, precision, or protocol provenance. A scalar alone cannot
prove those conditions matched. The new timing status prevents the clearest false contradiction;
general provenance enforcement is still required.

### P1 — durability and scale

- A worker dying after `claim_job` can leave a job permanently in progress; there is no lease,
  heartbeat, recovery sweep, or transactional outbox.
- Full outputs/diagnostic files can exceed Firestore's 1 MiB document limit.
- Repository repair attempts are pinned to the first resolved commit. Fetched source bytes and the
  runner image are not pinned, and URL-cache entries do not expire, so a later submission can still
  evaluate different inputs under the same claim key.
- Model transport retries nest inside the three repair attempts without a per-job token budget.

### P2 — remaining local boundary limitations

- Install-time Python build code has bridge networking and can probe reachable networks.
- URL validation occurs before the HTTP client's independent DNS resolution, leaving a DNS
  rebinding time-of-check/time-of-use gap.
- The local `asyncio.Queue` is intentionally not crash-durable.
- The declarative four-agent graph in `app/agent.py` has no tools and is not the durable runtime;
  actual Parser/Debug model calls do use typed ADK agents through `verity.llm`.

## Next steps, in order

The implementation-ready schemas, trust boundaries, crash windows, and acceptance tests for these
steps are in [NEXT-IMPLEMENTATION.md](NEXT-IMPLEMENTATION.md).

1. Commit and push the audit patch after review.
2. Rerun Whisper, then the full eight-source local catalogue, into a fresh writable database.
3. Add observed provenance and make every verdict depend on both scalar and condition matching.
4. Implement the credential-free cloud broker/no-role sandbox and OIDC worker split.
5. Install/authenticate the Cloud SDK and Agents CLI only after the secure design and tests are
   green; deploy to a staging project with a hard operational budget procedure.
6. Run one unseen source through the real deployed path, confirm Firestore/Pub/Sub/Trace/Logging
   evidence and an autonomously filed Issue, then run all deployed catalogue URLs plus dedup.
7. Attach an in-app Browser tab for final interactive UI, architecture-page, and screenshot QA.

## Inputs needed from the project owner

Nothing is needed to finish local code/test work. Later, do not paste credentials into chat;
instead:

- attach/open the in-app Browser when you want the visual interaction pass;
- after the cloud boundary is redesigned, provide the Google Cloud project ID, confirm the
  hackathon credits/billing account are active, and authenticate `gcloud`/Agents CLI locally;
- explicitly approve any external GitHub mutation if you want the historical issues updated,
  closed, or refiled.

Until the P0 items are cleared, describe Verity as a **locally proven, cloud-designed MVP**, not
as deployed or submission-complete.

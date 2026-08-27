# Verity — Current State and Next Steps

**Audited:** 2026-08-24; scoped cloud-security and emulator validation updated 2026-08-25

**Audit implementation:** `696cdfd3989633e80e7fd0b98c6e21794cabcd1d`

**Security report:** `01b73df9b1957b0c8f9364424a0bbf3fa612a89a`

**Code:** https://github.com/ZiyadAzzaz/verity (public)

**Verdicts:** https://github.com/ZiyadAzzaz/verity-reports (public)

**Live cloud project:** `verity-506800`; $450 promotional credit available; target total spend
approximately $25; hard review gates are documented in
[CLOUD-LIVE-SAFETY.md](CLOUD-LIVE-SAFETY.md).

**Latest work record:**
[WORKLOG-2026-08-27-CLOUD-SANDBOX-PREPARATION.md](WORKLOG-2026-08-27-CLOUD-SANDBOX-PREPARATION.md).
Every future material session follows [WORK-RECORD-STANDARD.md](WORK-RECORD-STANDARD.md).

This is the current source of truth. Older status, review, handover, and completion documents
are historical snapshots and retain their original evidence, dates, and test counts.

## Bottom line

The local product is a credible, working MVP with unusually strong evidence around its Docker
boundary, bounded debug loop, durable cache, and honest empty-result behavior. The audited cloud
credential flaw now has a scoped implementation: the sandbox receives bounded request arguments,
returns a bounded platform-collected log envelope, imports no cloud client, and is assigned a
service account with zero project or discovered resource-level IAM bindings. Pub/Sub now validates
Google OIDC instead of a
URL secret.

It is not yet a finished hackathon submission. The authorized sandbox-probe rerun created the
no-role identity, sentinels, immutable image, and private Cloud Run Job, but the local validator
could not import the repository package. The run stopped before job execution; all six denial
checks remain unexecuted. The deterministic module-launch defect is fixed and locally validated,
but a new live invocation requires owner approval. Production remains fail-closed until a real
sandbox task steals its metadata token and proves that all six sensitive project APIs deny it. See
[WORKLOG-2026-08-27-CLOUD-SANDBOX-PREPARATION.md](WORKLOG-2026-08-27-CLOUD-SANDBOX-PREPARATION.md).

The Firestore and Pub/Sub adapters have now also passed Google's official local emulators with no
account or credentials. This reduces adapter and transaction risk but is not live-cloud evidence.
See [EMULATOR-VALIDATION-2026-08-25.md](EMULATOR-VALIDATION-2026-08-25.md).

## Verified evidence

| Area | Current evidence |
|---|---|
| Public repositories | `verity` and `verity-reports` both return public GitHub metadata |
| Repository base before this validation | local `main` and public `origin/main` resolved to security commit `7aa52ce` |
| Python environment | `agent-dev`, Python 3.11.15; exact locked package set; `pip check` clean |
| Static gates | Ruff check, Ruff format check, and strict mypy pass after the audit changes |
| Full non-Docker selection | **264 passed, 3 emulator tests skipped, 9 Docker tests deselected**, 2 upstream deprecation warnings |
| Full Docker-inclusive suite | **273 passed, 3 emulator tests skipped**, 2 upstream deprecation warnings |
| Total unique tests with emulators | **276 passed**: 273 standard/Docker tests plus 3 official-emulator tests |
| Real isolation probe | 8/8 attacks blocked: host files, rootfs write, eval network, privilege, Docker socket, PID cap; install network and workspace write behave as designed |
| Immutable revision smoke | a real public GitHub commit was fetched by full SHA, checked out detached in Docker, evaluated, and recorded without drift |
| Local HTTP smoke | `/`, `/architecture`, `/healthz`, submission, cache lookup, verdict, and trace paths returned correctly against a writable copy of the demo DB |
| Demo cache | Five jobs, four historical outcomes, instant and zero model calls; read-only inspection creates no WAL/SHM sidecars |
| GitHub artifacts | Issues #1–#5 exist; #1, #3, #4, and #5 are real verdict artifacts, while #2 is explicitly a synthetic wiring probe |
| Runtime cleanup | no verification containers left running after the gates |
| Cloud-adapter emulators | **3 passed** against official Firestore 1.22.0 and Pub/Sub 0.8.35 emulators; exact containers removed afterward |

The in-app Browser had no attached tab/surface during this audit. HTTP behavior and generated
assets were checked, but a fresh interactive click/render pass is still a human-assisted step.

## Live catalogue: what actually happened

The 2026-08-25 scoped-fix regression produced new evidence:

- Whisper completed in a fresh database as `could_not_verify`, asserted no observed number, used
  exactly three bounded attempts, and recorded the malformed/unsafe second proposal as
  `attempt_rejected`. Its trace has 14 events, and dedup returned immediately without execution.
- A final fresh eight-source run completed the ResNet source as `could_not_verify`, with no
  observed number, three attempts, and 13 trace events.
- Source 2 then hit the configured AI Studio account's explicit `gemini-3.5-flash` free-tier limit
  of 20 requests. The run was stopped during parsing so later sources would not be mislabeled as
  claim failures. The full eight-source rerun therefore remains incomplete.

Exact scoped-fix evidence is in
[SCOPED-SECURITY-VALIDATION-2026-08-25.md](SCOPED-SECURITY-VALIDATION-2026-08-25.md).

The following is the preserved historical pre-fix catalogue baseline.

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

The eighth historical catalogue source, Whisper, is `failed` with no verdict because Gemini proposed the
unsafe path `../venv/pip.conf`; Pydantic correctly rejected it, but that historical run predates
the pipeline behavior that counts a rejected proposal as one bounded attempt. Therefore the
old claim “full 8-source gate completed” was false. The rejection path is covered by tests, but
the rejection path has now been rerun successfully for Whisper; only the complete eight-source
rerun remains blocked by external quota.

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
- Added digest-pinned official Firestore/Pub/Sub emulators and verified real transaction,
  serialization, publish, delivery, acknowledgement, and duplicate-claim behavior.

## Release blockers

### P0 — live proof of the scoped cloud trust boundary

The Firestore-capable sandbox design has been replaced locally. The trusted pipeline now passes
bounded public request arguments, reads a bounded result from the exact execution's Cloud Logging
records, and alone persists Firestore state. The sandbox image contains no Google Cloud client or
application secret. The deployment blueprint removes the legacy Firestore role, fails on any
remaining project binding, searches project-scoped resource policies with Cloud Asset Inventory,
clears ambient job capabilities, and runs a metadata-token abuse probe before deploying the
privileged app.

Required evidence before removing either production guard:

1. Run `scripts/deploy_sandbox_probe.ps1` to deploy only the sandbox job under
   `verity-sandbox@PROJECT.iam.gserviceaccount.com`.
2. Confirm its job definition contains exactly one container with the expected image, default
   entrypoint, and identity, and no declared environment, secret, volume, or VPC attachment.
3. Obtain its metadata token and require explicit denial of a Firestore write, Secret Manager
   read, Pub/Sub publish, Cloud Run execution, Vertex AI listing, and Cloud Storage listing.
4. Review inherited IAM and ensure the project exposes no sensitive private network to the task.
5. Preserve the honest residual-risk statement: no-role IAM closes credential blast radius but
   does not provide offline evaluation, malicious-code attestation, or kernel-exploit immunity.

### P0 — live cloud proof

No `run.app` URL, authenticated Google Cloud project, Vertex call, managed-service Firestore
transaction, managed Pub/Sub delivery, Cloud Run Job execution, Cloud Trace, or Cloud Logging
record was available to verify. Local Firestore and Pub/Sub emulator coverage now exists, but
`gcloud` and `agents-cli` are not installed/authenticated on this machine. Live deployment remains
a hard submission requirement after the trust boundary is fixed.

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

1. Local static, unit, Docker, image, and isolation gates are complete.
2. After the configured AI Studio quota resets (or the owner installs another local key), rerun
   the full eight-source catalogue into a fresh writable database. Whisper is already complete.
3. Obtain the project ID and billing confirmation; authenticate Cloud SDK locally.
4. Deploy only the no-role sandbox and require the metadata-token denial probe to pass.
5. Review the live evidence, then remove the two fail-closed guards as a separate change and
   authenticate Agents CLI and deploy staging with a hard operational budget procedure.
6. Run one unseen source through the real deployed path, confirm Firestore/Pub/Sub/Trace/Logging
   evidence and an autonomously filed Issue, then run all deployed catalogue URLs plus dedup.
7. Add broader provenance, recovery leases/outbox, image-digest pinning, and stronger egress after
   the hackathon submission unless a live test exposes an earlier need.
8. Attach an in-app Browser tab for final interactive UI, architecture-page, and screenshot QA.

## Inputs needed from the project owner

Nothing is needed to finish local code/test work. Later, do not paste credentials into chat;
instead:

- attach/open the in-app Browser when you want the visual interaction pass;
- provide the Google Cloud project ID, confirm the hackathon credits/billing account are active,
  and authenticate `gcloud` locally so the mandatory identity test can run; Agents CLI is needed
  only after the proof is reviewed and staging deployment is approved;
- allow the configured AI Studio quota to reset or replace the key locally in `.env` so the final
  eight-source catalogue can run; never paste the key into chat;
- explicitly approve any external GitHub mutation if you want the historical issues updated,
  closed, or refiled.

Until the P0 live evidence is captured, describe Verity as a **locally proven MVP with an
implemented but not yet cloud-validated security boundary**, not as deployed or
submission-complete.

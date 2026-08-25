# Verity — Next Implementation Plan

**Prepared:** 2026-08-24

> **Hackathon scope update — 2026-08-25:** The full broker/lease/provenance program below remains
> the production roadmap, but it is no longer the pre-deployment hackathon plan. The scoped
> credential-free request/log-result handoff, zero-role identity policy, metadata-token denial
> probe, and Pub/Sub OIDC validation are implemented in
> [SCOPED-CLOUD-SECURITY-FIX.md](SCOPED-CLOUD-SECURITY-FIX.md). Deployment remains fail-closed
> until that probe passes in the owner's real project.

This is the implementation plan after the deep audit. It deliberately does not remove either
production guard. The order matters: evidence integrity and crash recovery are local correctness
requirements; the cloud broker and network split are deployment security requirements.

## Release rule

Do not deploy arbitrary repositories to Cloud Run, advertise a public production URL, or call the
project submission-complete until all four gates below pass. A partial implementation must stay
fail-closed in `verity.config` and `scripts/deploy.ps1`.

## Gate 1 — evidence schema v1 and immutable execution

### Problem

The current Reporter can compare most successful scalar output without proving that the observed
dataset, checkpoint, split, dependencies, precision, hardware, or protocol match the claim.

The audit patch already closed the repository-retry portion of this problem: it captures the first
full commit, persists it on the job, fetches exact SHAs detached, pins every repair attempt, and
turns a missing or different commit into an infrastructure failure. Source-byte and runner-image
identity plus condition provenance remain open.

### Implement

1. Add typed, backward-compatible evidence records:
   - `SourceSnapshot(final_url, sha256)` on `ParsedClaim`;
   - `ConditionObservation(key, observed_value, evidence, origin)`;
   - `RunProvenance(source_sha256, repository_commit, runner_image_digest,
     evaluation_command, patch_digest, observations)` on `EnvironmentResult` and `Verdict`;
   - `evidence_schema_version`, defaulting to `0` for historical records and `1` for new verdicts.
2. Hash the exact fetched source bytes. Parser output must not be allowed to supply or overwrite
   this trusted value.
3. **Implemented in the audit patch:** resolve `git rev-parse HEAD`, persist the full
   40-character SHA, fetch it detached on every retry, and fail closed on drift.
4. Resolve the sandbox image tag to an immutable image ID/digest once per job and reuse it.
5. Define deterministic required observation keys: `dataset` and `condition:0..N`. Only
   Verity-owned probes can establish comparability; repository stdout and model assertions remain
   evidence but cannot self-attest that conditions matched.
6. Allow `verified` or `contradicted` only when the source digest, repository commit, image digest,
   and all material observations are complete and match. Otherwise use
   `conditions_not_comparable` while retaining the clearly labelled observed scalar.
7. Salt the claim-memory key with the evidence schema version. Historical jobs remain addressable
   by ID, but an evidence-v0 scalar verdict must not satisfy a new evidence-v1 submission.

### Acceptance tests

- The same source bytes produce the same digest; redirects hash the final fetched body.
- Old JSON/SQLite records still load, while malformed digests and commits are rejected.
- A moving remote branch cannot change the commit between the initial run and any retry.
- Exact SHA checkout works even when the SHA is not an advertised branch or tag.
- Commit/image drift fails the job as infrastructure and never reaches Debug or Reporter.
- Missing, duplicate, self-reported, or mismatched conditions all produce
  `conditions_not_comparable`.
- Trusted complete observations exercise both `verified` and `contradicted`.

## Gate 2 — leases, recovery, and transactional outboxes

### Current crash windows

1. Job creation and queue publication remain separate operations. The audit patch keeps a failed
   publication queued and republishes the same ID on repeat submission, but there is no automatic
   dispatcher if the user never retries.
2. `claim_job` permanently changes `queued` to `parsing`. A process death in any later phase leaves
   a job stuck forever because no delivery can claim it again.
3. The Pub/Sub endpoint acknowledges after Cloud Run accepts a job-launch request, not after the
   pipeline starts or finishes.
4. GitHub publication happens before the verdict is durable. A crash or ambiguous HTTP timeout can
   lose the Issue URL or create a duplicate on recovery.

The audit patch also makes Firestore job completion and claim-memory publication one transaction.

### Implement

1. Replace the Boolean claim with a fenced lease:
   `JobLease(job_id, generation, owner, expires_at)`. Store `execution_generation`, `lease_owner`,
   `lease_expires_at`, and `run_attempts` on the job.
2. Require the expected generation on every state update, trace append, completion, and failure.
   An expired worker must be unable to overwrite a newer worker even if it resumes.
3. Renew the lease with a heartbeat. Requeue expired jobs transactionally, incrementing the
   generation to fence the old owner. Bound infrastructure recovery separately from the three
   semantic Debug attempts.
4. Add a transactional delivery outbox. Job reservation and `delivery:<job_id>` intent are one
   transaction. A dispatcher retries ambiguous publication; duplicate deliveries are harmless
   because the fenced lease admits one generation.
5. Make verdict synthesis pure and persist the completed verdict, claim-memory entry, and
   `report:<job_id>` intent before calling GitHub. Artifact publication is a separate retryable
   state and must not rerun the benchmark or invalidate a sound cached verdict.
6. Put a stable hidden job marker in every Issue. Before and after an ambiguous POST, reconcile by
   that marker. GitHub has no native idempotency key, so document this as at-least-once delivery
   with best-effort duplicate prevention, not mathematical exactly-once behavior.
7. Implement identical contracts for Memory, SQLite, and Firestore. Run local dispatch/recovery at
   startup; use a scheduled reconciler in a scale-to-zero cloud deployment.

### Acceptance tests

- Concurrent acquire has one winner; heartbeat prevents reclaim.
- Expiry increments the fence; stale generations cannot update, trace, complete, or fail.
- A hard-killed SQLite worker is automatically recovered.
- Crashes before/after publish and duplicate Pub/Sub delivery still execute one active generation.
- Queue publication failure stays queued and retries.
- Verdict plus report intent are atomic under fault injection.
- GitHub failure leaves the verdict completed/cached and retry never reruns the benchmark.
- Concurrent report workers create one ordinary Issue; ambiguous POST reconciles the stable marker.
- The same store-contract suite passes against SQLite and the Firestore emulator.

## Gate 3 — credential-free cloud sandbox broker

### Required topology

```text
trusted pipeline --OIDC--> broker-control --Firestore
                                         ^
no-role sandbox supervisor --OIDC------> broker-exchange
              |
              +-- fresh UID 10002 child --> third-party repository code
```

Deploy broker control and exchange as separate authenticated Cloud Run services, even if they use
one image. Only the broker service account gets Firestore. The pipeline may invoke control. The
sandbox service account has no project roles and may invoke only exchange.

### Broker protocol

- Control: create, inspect, and cancel one sandbox run.
- Exchange: atomically claim one request and complete it once.
- Generate at least 256 random capability bits; store only hashes.
- Pass the capability in a header, never a query string or log field.
- Claim rotates a short-lived bootstrap capability into a completion capability.
- Enforce explicit expiry, a completion lease, request/result digests, replay rejection, and a
  256–512 KiB serialized limit. Firestore TTL is cleanup, not authorization.

### Supervisor boundary

- The trusted supervisor owns Verity code and runs as root only to create a fresh process and drop
  identity. Third-party code runs as UID/GID 10002 with empty supplementary groups, no capabilities,
  `no_new_privs`, closed file descriptors, a sanitized environment, and bounded resources.
- The bootstrap credential is removed before the child starts. The rotated completion credential
  stays only in non-dumpable root-process memory.
- Root-owned Verity code is not writable by UID 10002. The current recursive ownership transfer in
  `Dockerfile.sandbox` must be removed.
- Metadata access is assumed possible. A stolen sandbox identity must still have no Firestore,
  Secret Manager, Vertex, Pub/Sub, Storage, Cloud Run, or project permission.

### Network split

A broker protects project credentials; it does not enforce offline evaluation. Cloud Run cannot
securely turn networking off for only one child process, so use two no-role job templates:

1. `verity-prepare`: clone/install through an enforced egress proxy limited to approved source and
   package hosts; produce a digest-addressed workspace artifact.
2. `verity-evaluate`: obtain that artifact through the supervisor, then run repository code on a
   Direct VPC egress path with deny-all firewall policy except the private broker route.

Environment proxy variables are not an isolation control. If public, private, link-local, metadata,
or arbitrary DNS egress remains reachable during evaluation, production stays blocked.

### Acceptance tests

- Concurrent claim, replay, cross-run token, expiry, lease expiry, and oversized payload tests.
- A malicious child cannot read the supervisor environment/memory, ptrace or signal it, inspect
  sensitive descriptors, or receive either capability.
- A staging attack repository can obtain a metadata token but every Google project API call is
  denied.
- Prepare reaches only approved destinations; evaluate reaches no public/private/link-local target.
- Timeout and termination kill the full child process group and produce a recoverable terminal
  infrastructure state.
- Cloud Logging contains no capability material.

## Gate 4 — staging and submission proof

After Gates 1–3 pass locally and in emulators:

1. Install/authenticate `gcloud` and Agents CLI in `agent-dev` on the E: drive where possible.
2. Confirm a credit-backed project, billing alerts, and an explicit operator shutdown procedure.
   A budget alert is not a spending cap.
3. Use separate least-privilege service accounts, private broker services, exact OIDC audiences,
   immutable image digests, and checked deployment commands.
4. Run a malicious isolation suite first. Do not start real claims if it fails.
5. Run Whisper and the full local catalogue in a fresh database.
6. Submit one previously unseen source through Pub/Sub, the pipeline, broker, prepare/evaluate jobs,
   Firestore, Trace/Logging, and GitHub reporting with no manual intervention.
7. Repeat all deployed catalogue inputs, then verify dedup, recovery, authentication rejection,
   artifact reconciliation, and post-hoc trace visibility.
8. Only after the evidence is captured should the production guards and “not deployed” wording be
   changed.

## Owner inputs

No secret is needed for Gates 1–3. For Gate 4 the project owner must:

- attach an in-app Browser surface for interactive UI/screenshot QA;
- provide only the Google Cloud project ID and confirm credits/billing are active;
- authenticate `gcloud` and Agents CLI locally rather than sending credentials in chat;
- explicitly approve any update, closure, or replacement of existing public GitHub Issues.

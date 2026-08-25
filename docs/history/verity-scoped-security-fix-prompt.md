# Verity — Scoped Cloud Security Fix (Not the Full Broker Design)

I've read `AUDIT-2026-08-24.md`, `NEXT-IMPLEMENTATION.md`, and `STATE.md` in full. The audit
work itself was correct and valuable — the P0 finding (sandbox task had a Firestore-capable
service identity with outbound networking, so untrusted repository code could reach the
metadata server and use real project credentials) was a genuine, serious catch, and I'm glad it
was found before anything was deployed, not after.

**But I'm explicitly overriding the implementation plan in `NEXT-IMPLEMENTATION.md`.** Gates
1–3 as written — evidence-schema provenance, fenced leases with heartbeats and a transactional
outbox, and a full capability-token broker with separate control/exchange Cloud Run services —
is a distributed-systems security project that would take weeks for one engineer, not days. We
have until August 31, and the credit request window itself closes August 28. Building the full
design risks spending the entire remaining time on infrastructure and arriving at the deadline
with nothing running on Google Cloud at all — which fails the hackathon's Stage One pass/fail
bar outright, regardless of how good the design is.

## What to build instead: the minimal design that closes the actual P0 risk

The dangerous thing isn't the absence of leases or provenance hashing — it's that untrusted code
could reach credentials with real project permissions. Close that specific hole with the
standard, well-understood GCP pattern, not a custom broker:

1. **The sandbox execution service account gets zero IAM roles.** No Firestore, no Secret
   Manager, no Vertex, no Pub/Sub, no Cloud Run admin, nothing. Confirm this is enforceable and
   testable — a policy check, not just a convention.
2. **No secret, token, or credential is ever placed in the sandbox task's environment,
   filesystem, argv, or accessible metadata identity.** The orchestrator — which holds the real
   credentials — is the only thing that talks to Firestore/Vertex/Pub-Sub. The sandbox task
   receives its work and returns its result through the simplest mechanism that doesn't require
   it to hold real credentials (e.g., the orchestrator passes input directly as job
   parameters/mounted data and reads output back itself after the task completes, rather than
   the sandbox task writing to Firestore itself).
3. **Metadata server access is still assumed possible from inside the sandbox** — don't try to
   block it. The point is that even if the sandbox task's identity is fully compromised, it has
   nothing to steal, because it was never granted anything.
4. Keep the existing local Docker isolation controls (`--cap-drop ALL`, read-only rootfs,
   no-network eval phase, etc.) as-is on the cloud side too, wherever Cloud Run Jobs allows
   equivalent controls — this part of the audit's hardening was already sound and doesn't need
   redesigning.

This is a few hours of real work, not weeks — a service account with a no-role policy, and
making sure nothing sensitive ever reaches the sandbox task's execution context. Write and run
a real test that proves it: spin up a sandbox task with this identity and confirm it cannot
successfully call any Google Cloud API that would matter (Firestore write, Secret Manager read,
etc.) even with a stolen metadata token — same evidentiary standard as the local Docker escape
tests.

## What to explicitly defer, and document, not build

Add a "Known Limitations" section (or extend the existing one) covering, plainly, without
apologizing for it:

- **Evidence provenance (Gate 1 in `NEXT-IMPLEMENTATION.md`):** verdicts don't yet cryptographically
  pin dataset/hardware/dependency equivalence beyond the repository-commit pinning already
  implemented. Scalar comparison is trusted at face value for now.
- **Leases, heartbeats, transactional outbox (Gate 2):** a crashed worker can strand a job; no
  automatic recovery sweep exists yet. Acceptable for a hackathon-scale demo, not for production
  scale.
- **DNS-rebinding TOCTOU gap, install-time LAN scanning exposure, Firestore 1 MiB document
  limit, runner image tag mutability:** real, understood, out of scope for this timeline.

This is a legitimate, professional thing to state in a submission — "we found and fixed the
critical trust-boundary flaw, and we're explicit about what's still hardening work" reads far
better to a technical judge than either silence or an unfinished attempt at the full design.

## Correctness items to actually do, cheap and worth it

- **Rerun Whisper and the full 8-source catalogue into a fresh database**, now that the
  rejected-patch-counts-as-an-attempt fix is in place. This is quick and closes a real
  documented gap (the old "8-source gate completed" claim was false).
- Keep the `conditions_not_comparable` fix for timing-sensitive metrics — that one's correct and
  already done, no further action needed there.

## Then — deployment, as soon as the scoped fix above is verified

1. Confirm with me before removing the fail-closed guards in `verity/config.py` and
   `scripts/deploy.ps1` — show me the passing test evidence for the no-role sandbox identity
   first.
2. Once confirmed: proceed with actual deployment via the ADK's Cloud Run path, `VERITY_ENV=cloud`,
   and run one full, previously-unseen claim end to end against real Vertex AI, Firestore,
   Pub/Sub, and the now-scoped-down Cloud Run Job sandbox.
3. Same standard as always: show me the real Cloud Run URL, real logs, real Firestore/Pub-Sub
   activity — not code that should work by analogy to local.
4. I still need to confirm hackathon credits and give you a project ID before any of this
   starts — that hasn't changed. Everything above except actual deployment can proceed without
   it.

## What I need from you when you report back

State plainly: is the no-role sandbox identity fix actually sufficient to make deployment safe
for arbitrary untrusted repositories, in your own honest assessment — not just "it closes the
audit's specific P0 finding." If you still see a real residual risk even after this fix, say so
explicitly rather than letting a scoped-down fix quietly imply the whole trust boundary is
solved. I'd rather know the honest residual risk than assume it's zero.

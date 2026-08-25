# Verity — Test the Cloud Profile Against Emulators, No Account Needed Yet

While the Google Cloud project and billing are still being set up on my end, there's real work
you can do right now that needs no account, no project ID, and no cost: exercise the cloud
adapters (`FirestoreJobStore`, `PubSubJobQueue`) against Google's official local emulators
instead of the real services.

## What to set up

- **Firestore emulator** — run it locally, point `FirestoreJobStore` at it via the standard
  emulator host environment variable (`FIRESTORE_EMULATOR_HOST`), and confirm the adapter's
  transaction behavior (the atomic job-completion + claim-memory write from the audit fixes)
  actually works against it, not just against SQLite.
- **Pub/Sub emulator** — same idea, point `PubSubJobQueue` at it via `PUBSUB_EMULATOR_HOST`, and
  confirm publish/consume actually round-trips a real job through the queue abstraction.
- **Sandbox execution** — no new work needed here; the existing local Docker sandbox already is
  the same container that would run under Cloud Run Jobs, and the scoped security design's
  bounded stdout handoff doesn't depend on the emulators at all.
- **Model calls** — no Vertex emulator exists. Use the existing Gemini API key as a stand-in for
  `VertexAIModelClient`'s calls where you need a real model response; where you're specifically
  testing transport/serialization behavior rather than model output, a stubbed client (same
  pattern used earlier to prove Reporter's publish path without spending quota) is fine.

## What this actually de-risks

The goal is to catch integration bugs in the cloud adapters *before* the real deployment attempt
— transaction semantics, serialization edge cases, timeout handling — the same class of bug that
hit the local profile on first live contact (the key not reaching the client, the
`additionalProperties` schema rejection). If the emulator pass surfaces something similar in the
cloud adapters, that's a bug found today instead of during the one live deployment window we'll
have once the real account is ready.

## What NOT to do

- Don't attempt any real `gcloud` command or touch the actual project — that's still gated on my
  explicit go-ahead, unchanged from before.
- Don't treat an emulator pass as equivalent to the live identity probe or live deployment proof
  — it isn't, and the submission still needs the real thing. This is purely for catching bugs
  early, not for satisfying the "runs on Google Cloud" requirement.

## Report back

What you tested against each emulator, what passed, and — most usefully — anything that broke
that wouldn't have been caught by the existing SQLite/local-queue test suite. Same evidence
standard as always: show me the real emulator output, not just that the adapter code looks
correct.

Separately: the moment I have gcloud authenticated and a project ID, I'll send the sandbox-probe
go-ahead prompt — that's still the next real milestone, this is parallel prep for it.

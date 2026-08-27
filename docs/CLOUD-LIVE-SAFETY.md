# Verity Live-Cloud Safety and Spend Rule

- **Effective:** 2026-08-27
- **Project:** `verity-506800`
- **Available promotional credit:** $450

This is the current operational rule for every Verity cloud action. Historical documents that
mention earlier credit figures remain historical evidence and do not override this file.

## Financial boundary

- Target cumulative spend for the complete hackathon project: approximately **$25 or less**.
- Stop before any single action whose actual or projected cost exceeds **$10**.
- Stop if cumulative actual spend crosses **$50**.
- Report the closest observable actual cost after every cloud action. Where billing data has not
  posted yet, report that limitation explicitly, record observed resource usage, and provide a
  conservative price estimate rather than presenting an estimate as an invoice value.
- Never change or automate payment methods, billing-account configuration, budgets, budget alerts,
  spend caps, plan tiers, or quota increases. Read-only confirmation that billing is enabled and
  read-only cost inspection are allowed.
- Using the existing credit-backed project for expected Cloud Run, Cloud Build, Artifact Registry,
  Firestore, Pub/Sub, Secret Manager, Logging, Trace, and Vertex AI workloads is allowed within the
  gates above.

The owner independently configured alerts at $50, $100, and $150. Verity code must not create,
edit, or delete those alerts. The dormant budget-creation logic formerly present in `deploy.ps1`
was removed before the first live probe.

## Current deployment gate

Only the sandbox identity proof is authorized initially. It may enable required APIs and create:

- the `verity` Artifact Registry repository;
- the no-role `verity-sandbox` service account;
- a non-sensitive Secret Manager sentinel;
- a Pub/Sub sentinel topic;
- one sandbox image built by Cloud Build; and
- the private `verity-sandbox` Cloud Run Job.

It must not deploy the Verity API, pipeline worker, Pub/Sub push subscription, Gemini/API secrets,
GitHub token, public endpoint, or privileged application identity.

Production remains fail-closed after a passing probe. Removing either production guard requires
separate explicit owner approval after reviewing all six stolen-token denial results.

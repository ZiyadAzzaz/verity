# Scoped Cloud Security Validation — 2026-08-25

## Outcome

The scoped implementation is complete and all locally reproducible code, package, image, Docker,
and isolation gates pass. The production guards remain closed because two external acceptance
conditions are still unavailable:

1. the sandbox identity denial probe has not run in the owner's Google Cloud project; and
2. the fresh eight-source catalogue rerun was stopped by the configured AI Studio account's
   `gemini-3.5-flash` free-tier quota after the first source completed.

No Google Cloud resource was changed, no production guard was removed, and the catalogue reruns
did not publish GitHub Issues.

## Security problem and detection

The 2026-08-24 audit traced the original Cloud Run flow end to end and found that the sandbox task
read and wrote Firestore using a Firestore-capable service identity while arbitrary repository code
ran in the same task. Cloud Run's metadata server could therefore mint a real token for that
identity. Outbound network access turned a repository compromise into project credential access.

The finding was detected by following data and authority, not just imports:

- who created the sandbox request;
- how the task received it;
- which identity the task used;
- which APIs that identity could call;
- whether untrusted child code could reach metadata and the network; and
- how the task returned its result.

## Implemented correction

- The trusted pipeline sends a bounded typed request through Cloud Run execution arguments and
  strips unnecessary URL query data first.
- The sandbox prints one bounded typed result; Cloud Run captures stdout, and the trusted pipeline
  reads the exact execution's labeled log entry and persists it.
- The sandbox image contains only Pydantic and its support packages. It contains no Google Cloud
  client or auth library and receives no application secret.
- Deployment requires a sandbox service account with no project binding and no resource-level
  binding found by Cloud Asset Inventory.
- The sandbox job must have one expected image/container, its default entrypoint, no configured
  environment, no secret, no volume/mount, and no VPC attachment.
- A live adversarial probe deliberately obtains the metadata token and requires explicit `401` or
  `403` denial of a Firestore write, Secret Manager read, Pub/Sub publish, Cloud Run execution,
  Vertex AI listing, and Cloud Storage listing.
- Pub/Sub push authentication now verifies Google's OIDC signature, issuer, audience, verified
  email, and exact configured service-account identity. No URL secret is used.
- Explicit `.dockerignore` and `.gcloudignore` files keep local env files, credentials, databases,
  caches, and Git metadata out of build contexts.
- Deployment resolves build tags through Artifact Registry and uses validated immutable
  `@sha256:` image references for the sandbox, API, and pipeline job.

## Local acceptance evidence

| Gate | Result |
|---|---|
| Ruff lint | Pass |
| Ruff format check | 70 files formatted |
| Strict mypy | Pass, 42 source files |
| Non-Docker pytest | **262 passed**, 9 deselected |
| Docker pytest | **9 passed**, 262 deselected |
| Complete pytest total | **271 passed** |
| Package consistency | `pip check`: no broken requirements |
| Minimal sandbox build | Pass; uploaded context approximately 200 KB |
| Minimal sandbox dependency inspection | Pydantic support stack only; no `google` package |
| Docker escape/isolation probe | **8/8 passed** |
| PowerShell deployment syntax | Both deployment scripts parse successfully |

The eight Docker isolation assertions cover host-file access, read-only root filesystem, offline
evaluation, networked installation, non-root/no-capability execution, Docker socket absence, PID
limit enforcement, and the single writable workspace.

## Live local-pipeline evidence

### Whisper regression

The required Whisper rerun completed in a fresh ignored database:

| Field | Evidence |
|---|---|
| Source | `https://github.com/openai/whisper` |
| Final status | `completed` |
| Verdict | `could_not_verify` |
| Observed value | none asserted |
| Bounded attempts | exactly 3 |
| Trace events | 14 |
| Rejected proposal | attempt 2 recorded as `attempt_rejected` |
| Dedup | cached response returned immediately with no new execution |

This closes the historical correctness gap: a malformed/unsafe Debug proposal is now visible and
counts toward the three-attempt bound instead of failing the job outside the bounded state machine.

### Eight-source catalogue

The final fresh run completed the ResNet source with `could_not_verify`, no observed value, exactly
three attempts, and 13 trace events. The next source then received repeated API responses stating
that the `gemini-3.5-flash` free-tier request quota of 20 had been exceeded. The run was stopped
while source 2 was still parsing so sources 2–8 would not be mislabeled as verification failures.

Therefore, the claim “the fresh eight-source catalogue passed” is **not** made. The partial
databases are retained locally under `.verity-data/` and intentionally excluded from Git and image
build contexts. The validator now detects a shared model quota/capacity failure and stops instead
of spending calls on every later source.

## Cloud acceptance gate

The production deployment guard is intentionally still active. After the owner supplies the
project and confirms billing, run the sandbox-only proof first:

```powershell
powershell -File scripts/deploy_sandbox_probe.ps1 `
  -ProjectId YOUR_PROJECT_ID `
  -Region us-central1
```

This script does not deploy the privileged API or pipeline. After its JSON evidence is reviewed,
the owner must explicitly confirm guard removal before staging deployment.

## Honest safety assessment

The no-role identity design closes the audited Google Cloud credential blast radius when its live
policy and denial tests pass. It does **not** make arbitrary hostile repositories universally safe.
Cloud Run still permits outbound network access, the result channel is not malicious-code
attestation, unknown runtime/kernel vulnerabilities remain possible, and provenance, recovery
leases/outbox, DNS rebinding, Firestore document size, and image-digest pinning remain deferred.

The defensible hackathon statement is: Verity has a locally validated, credential-free scoped
cloud design with explicit residual risks; the live GCP identity proof and deployed end-to-end run
are pending owner-provided cloud access and billing.

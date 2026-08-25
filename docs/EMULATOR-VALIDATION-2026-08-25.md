# Verity Cloud-Adapter Emulator Validation

- **Date:** 2026-08-25
- **Scope:** Firestore and Pub/Sub adapters only
- **Cloud account used:** none
- **Real project or credentials used:** none

## Outcome

Verity's `FirestoreJobStore` and `PubSubJobQueue` passed integration tests against Google's
official local emulators. The tests used a fake project ID and loopback-only host ports. No
credential directory, application-default credential, service-account key, host directory, or
real Google Cloud resource was mounted or contacted.

This closes a useful pre-deployment uncertainty: the cloud adapters now have evidence against
the actual Google client libraries and emulator protocols, rather than only mocks. It does not
close the live-cloud acceptance gate.

## Reproducible environment

The harness is defined in `docker-compose.emulators.yml` and uses Google's official emulator
image pinned by digest:

```text
gcr.io/google.com/cloudsdktool/google-cloud-cli
sha256:25300472f1fa63b4df0e0c3a5dd67bdc6774b39f6dd440605e520a6d04ae0f26
```

Resolved tool versions:

| Component | Version |
|---|---:|
| Google Cloud SDK | 581.0.0 |
| Firestore emulator | 1.22.0 |
| Pub/Sub emulator | 0.8.35 |
| Docker Desktop | 4.87.0 |
| Docker Engine | 29.7.2 |

Both ports bind only to loopback:

- Firestore: `127.0.0.1:18080`
- Pub/Sub: `127.0.0.1:18085`

## What was tested

### Firestore

- Four concurrent `create_or_get` calls for one canonical URL produced exactly one job.
- Three concurrent `claim_job` calls produced exactly one winner.
- Typed nested `ParsedClaim`, trace detail, `Verdict`, `SandboxRequest`, `SandboxRun`, and
  `EnvironmentResult` values survived real client serialization and deserialization.
- Job completion and claim-memory completion became visible together after the transaction.
- A completed claim returned as a cached result and did not reserve a new job.
- A failed job could be replaced by a fresh reservation without returning stale cache state.
- Trace ordering and normalization returned contiguous public sequence numbers.

### Pub/Sub

- A real topic and pull subscription were created in the emulator.
- `PubSubJobQueue.publish` delivered the expected JSON bytes and message attributes.
- The delivered message passed through the same base64 push-envelope decoder used by the API.
- The message was acknowledged, and a subsequent bounded pull returned no message.
- Two workers attempting to claim the delivered Firestore job still produced exactly one winner,
  proving the state transaction is the duplicate-delivery boundary.
- Publisher completion uses an explicit bounded timeout, and shutdown stops publisher workers.

The production consumer is an authenticated HTTPS push endpoint, not an in-process subscriber.
The emulator test deliberately uses a pull subscription to inspect the exact published bytes and
then exercises the production decoder. Google-signed OIDC is covered by unit tests and still
requires live Google Cloud evidence.

## Real output

```text
Container verity-emulator-tests-pubsub-1 Healthy
Container verity-emulator-tests-firestore-1 Healthy
...                                                                      [100%]
3 passed, 1 warning in 16.07s
Official Firestore and Pub/Sub emulator integration tests passed.
```

The warning is an upstream OpenTelemetry `importlib.metadata` deprecation warning. It is unrelated
to Firestore, Pub/Sub, serialization, or Verity behavior.

## Improvements made

- Added a digest-pinned, credential-free two-emulator Compose stack.
- Added a one-command PowerShell runner with readiness checks, bounded startup, failure logs,
  environment restoration, and guaranteed container cleanup.
- Added real emulator integration coverage separate from cloud-account tests.
- Made the Pub/Sub publish timeout configurable and explicitly positive.
- Added publisher shutdown so background publisher workers are not leaked during service exit.
- Added explicit Firestore client cleanup.

No existing cloud-adapter correctness failure appeared during the emulator run. The lifecycle and
timeout improvements were added because the stronger integration harness made those operational
boundaries important and directly testable; they are not reported as emulator-discovered data
corruption bugs.

## Complete regression evidence

After the emulator-specific pass, the complete project gates were rerun:

| Gate | Result |
|---|---|
| Ruff lint | Pass |
| Ruff format | Pass, 105 files checked |
| Strict mypy | Pass, 32 source files |
| Non-Docker pytest | 264 passed, 3 emulator tests skipped, 9 Docker tests deselected |
| Docker-inclusive pytest | 273 passed, 3 emulator tests skipped |
| Emulator pytest | 3 passed |
| Unique test total | **276 passed** |
| Docker isolation probe | **8/8 passed** |
| Package consistency | `pip check`: no broken requirements |

The only test warnings are upstream Starlette/TestClient and OpenTelemetry deprecations. No Verity
warning, resource leak, lingering container, or failed assertion remained.

## Run it again

Prerequisites are Docker Desktop and the repository's Python 3.11 development environment.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/test_emulators.ps1
```

The script uses only fake project `verity-emulator-test`. It restores any pre-existing emulator
environment variables and removes its exact containers and network when finished.

## What remains unproven

Google documents important emulator differences, so this result must not be described as a live
deployment pass:

- Firestore uses simpler locking and does not reproduce production concurrency modes, transaction
  limits, timeouts, size limits, or composite-index enforcement.
- Pub/Sub emulator IAM is unavailable and emulator behavior can differ from the managed service.
- The emulator cannot produce the Google-signed OIDC identity used by the production push route.
- There is no Vertex AI or Cloud Run Jobs emulator.
- The no-role sandbox metadata-token denial probe must still run in the real project.
- Cloud Logging execution-label queries, Artifact Registry digest deployment, IAM inheritance,
  Cloud Trace, and the unseen deployed end-to-end source remain live-only gates.

The next milestone is unchanged: after the owner supplies an authenticated project and confirms
credit-backed billing, run `scripts/deploy_sandbox_probe.ps1` first. Production guards must remain
in place until that live evidence passes and the owner explicitly approves their removal.

## Authoritative references

- [Firestore emulator documentation](https://docs.cloud.google.com/firestore/native/docs/emulator)
- [Pub/Sub emulator documentation](https://docs.cloud.google.com/pubsub/docs/emulator)
- [Official Google Cloud CLI emulator image](https://docs.cloud.google.com/sdk/docs/downloads-docker)

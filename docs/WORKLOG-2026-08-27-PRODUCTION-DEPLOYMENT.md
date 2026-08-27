# Verity Production Deployment Work Record — 2026-08-27

## Objective and authorization boundary

The owner authorized implementation and execution of
`POST-PROBE-PRODUCTION-DEPLOYMENT-PLAN.md` in project `verity-506800`, region `us-central1`, through
the private Phase 0–7 checkpoint. Granting `allUsers` Cloud Run Invoker is explicitly excluded
until the owner reviews the private evidence and approves Phase 8. Billing, payment, budget,
quota, and plan configuration remain permanently out of scope.

## Starting state and recovery reconciliation

- Repository: Verity, branch `main`.
- Starting/local/remote revision: `7941911fcab20f8b9c432b427b16587f149b1dc1`.
- Live `origin/main` was verified with `git ls-remote` and matched the local revision.
- Active account: `ziyadazzazdesigner@gmail.com`.
- The resumed worktree contained nine intended mid-implementation files; none had been committed
  or pushed.
- No production cloud mutation had occurred during the interrupted session.

The read-only recovery inventory found only the previously approved sandbox foundation:

- Firestore `(default)`: Native mode, `us-central1`;
- topic `verification-jobs`;
- identity `verity-sandbox@verity-506800.iam.gserviceaccount.com`;
- secret `verity-sandbox-deny-probe`, versions 1–3 enabled;
- job `verity-sandbox`, immutable digest
  `sha256:615e71df55395e0ec84e875bf943bda22d6e84d62d95835a59965cc7c12853b3`, 2 vCPU,
  4 GiB, zero retries, and no job IAM bindings; and
- latest successful execution `verity-sandbox-rcxvn`.

The inventory confirmed absence of Cloud Run services, `verity-pipeline`, `verity-app`,
`verity-pubsub`, production secrets, Pub/Sub subscriptions, Verity project IAM bindings, and
resource-level IAM bindings for all three Verity identities. All ten required APIs, including
Cloud Trace, are enabled. Therefore the actual recovery point was Phase 1/2 local implementation,
not a partial Phase 4–7 deployment.

## Prerequisites and secret handling

The local `.env` is Git-ignored. Presence/length-only checks found:

- `VERITY_API_KEY`: present, 64 characters;
- `VERITY_GITHUB_TOKEN`: present, 93 characters; and
- `VERITY_REPORT_REPO`: present, 25 characters.

No value was printed, recorded, passed in a container smoke, or added to Git. `google-agents-cli`
1.4.0 was installed in the dedicated `agent-dev` environment. `pip check` reported no broken
requirements, and `agents-cli deploy --help` completed successfully.

## Defects and security findings

1. **Critical — module worker silently did nothing.** `python -m verity.worker <job_id>` exited
   successfully without calling `main()`. The pipeline job uses this exact launch path. Added the
   main guard and a regression that proves the supplied ID reaches `_run(job_id)`.
2. **High — API image lacked installed package metadata and console scripts.** Added a no-dependency
   local package install after copying the project so `verity-api` and `verity-worker` exist.
3. **High — private deploy granted public access too early.** The original script granted
   `allUsers` before authenticated push assembly. The private script now contains no such mutation;
   an approval-gated `publish_production.ps1` owns the future Phase 8 transition.
4. **High — Agents CLI could propagate secrets as plaintext.** Version 1.4.0 automatically copies
   every project-root `.env` key into Cloud Run. A dry run correctly rejected the collision between
   plaintext `VERITY_API_KEY`/`VERITY_GITHUB_TOKEN` and Secret Manager mappings. Deployment now
   invokes Agents CLI from a fresh OS temporary directory and passes only explicit non-secret
   environment values plus named Secret Manager references. A repeated dry run showed
   `--no-allow-unauthenticated`, masked non-secret env values, and masked `--update-secrets` only.
5. **Medium — CLI path assumption.** The executable is installed under the Conda environment but
   not global `PATH`. Deployment now resolves it relative to the selected Verity Python.
6. **Validation design — OIDC proof must not start Phase 9.** Added an internal OIDC-only probe
   route that shares the real worker token verifier but launches no pipeline job.
7. **High — compute region was incorrectly coupled to model location.** The preflight returned 417
   for `gemini-3.5-flash` in `us-central1`, while a zero-generation Vertex `countTokens` request
   succeeded at `global` with four input tokens. Added a separately validated
   `GOOGLE_CLOUD_VERTEX_LOCATION=global`; Firestore and both Cloud Run jobs stay in
   `us-central1`.

## Implementation and decisions

- Enabled the production cloud profile only because the preserved live record proves six explicit
  403 denials for the zero-role sandbox.
- Kept all requirements rejecting local, Docker, host-subprocess, missing-auth, and wrong-project
  production configurations.
- Kept the API Uvicorn command explicit and installed project metadata without resolving runtime
  dependencies a second time.
- Added the 12-character source revision as `AGENT_VERSION` for deployed traceability.
- Separated the global Gemini endpoint from the regional data/compute location instead of moving
  Firestore or Cloud Run away from `us-central1`.
- Chose an isolated OS temporary working directory for Agents CLI instead of copying or renaming
  `.env`; this makes secret exclusion structural and leaves the owner's local file untouched.
- Added exact temp-root validation before cleaning the generated CLI directory.

## Local validation evidence

- Focused security/worker/Pub/Sub suite: 38 passed.
- Complete `scripts/test.ps1 -Docker` gate:
  - Ruff lint: passed;
  - Ruff format: 117 files formatted correctly;
  - strict mypy: 32 source files, no issues;
  - latest pytest rerun: 281 passed, 3 official-emulator-only skips, 2 dependency deprecation
    warnings;
  - Docker escape validation: all eight boundary checks passed.
- Local API image: `verity-api:predeploy`, manifest-list digest
  `sha256:169881ff661fc826c253b51c2dbef4c1f192e9a28a7c7f7d11a36ed3a551d1c2`,
  128,931,623 bytes.
- Image imports, `verity-agent` metadata, and both console entry points: passed.
- `verity-worker --help` and `python -m verity.worker --help`: passed with non-empty argparse help.
- Local direct HTTP `/healthz`: `status=ok`, memory store, asyncio queue, host-subprocess smoke
  backend, no setup error, and no real credential present.
- The in-app browser surface exposed no browser instance, so the local health gate was HTTP-only;
  no visual-browser pass is claimed.
- PowerShell AST parse, `git diff --check`, ignore-file secret exclusions, and local build context:
  passed.

## Cost record

All actions in this implementation/recovery portion were local, read-only cloud queries, or one
zero-generation `countTokens` availability check. Observed cloud cost for this portion is `$0.00`.
No billing configuration was read beyond enabled
status and no billing/payment/budget/quota/plan setting was changed. The prior raw sandbox
build/compute equivalent remains `$0.0298481044886`; it is historical, not new spend from this
session.

## Professional assessment and next steps

The resumed state is consistent and safe to continue. The most important new finding was the
Agents CLI `.env` behavior: without the isolated invocation, a convenience tool could have
undermined Secret Manager even though the application configuration was correct. Local release
confidence is now high, but production is not yet deployed.

Next: commit and push the clean release revision, perform the final read-only cost/model/preflight
gate, build immutable images once, re-prove the new sandbox digest, then create least-privilege
identities/secrets and deploy API, pipeline, and OIDC push privately. Update this record with exact
build IDs, digests, IAM, private health/OIDC evidence, and observed cost. Stop before Phase 8.

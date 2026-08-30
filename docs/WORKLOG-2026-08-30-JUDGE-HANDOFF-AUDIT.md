# Verity work record — judge handoff and configuration audit

**Date:** 2026-08-30 (Africa/Cairo)  
**Repository:** `ZiyadAzzaz/verity` · branch `main`  
**Cloud project / region:** `verity-506800` / `us-central1`  
**Starting revision:** `2ce039a92dd445209816970de015f15e0784c730`

## Objective and boundaries

The owner asked for the queued TRY ONE/architecture prompt to be reconciled against work already
completed, without repeating deployments or live jobs; an exact explanation of the judge API and
public reports; a correction of confusing local-versus-cloud `.env` guidance; and a complete
Markdown record.

This session did not read or print `.env` secret values. It made no verification submission, GitHub
Issue, deployment, IAM, billing, payment, budget, quota, or plan change. All cloud and GitHub checks
were read-only. The local `.env` was deliberately left unchanged and remains ignored by Git. One
deployment-script safety defect was fixed locally but not executed against cloud resources.

## Reconstructed starting state

- Local `main` and `origin/main` both pointed to `2ce039a92dd445209816970de015f15e0784c730`.
- The working tree started clean, apart from pre-existing unreadable pytest temporary directories
  that produced `git status` warnings but no tracked diff.
- Latest GitHub Actions run for that revision was
  [33283193388](https://github.com/ZiyadAzzaz/verity/actions/runs/33283193388): **success**.
- Cloud Run reported revision `verity-00018-czq` Ready and serving 100% of traffic.
- API and private pipeline were pinned to
  `sha256:5562a24da4dc8fe2bd8e04fc6005d74b87402ddc395cbd0f0d45a646947a2ba2`.

## Queued prompt reconciliation

| Requested item | Decision | Evidence |
|---|---|---|
| Correct misleading TRY ONE outcomes | Already complete; skipped | Live UI labels name sources rather than promising verdicts; commit `6af63e4` |
| Recheck live cloud outcomes | Already complete; skipped | Phase 9 Issues #8–#10 and bounded follow-ups #11–#12 are recorded in the current status |
| Find a live `verified` result | Already time-boxed; not repeated | Two fresh bounded candidates ran; neither honestly verified; repeating open-ended search would displace submission work |
| Refresh architecture page | Already complete; skipped | Live page contains deployed/live, no-role sandbox, multi-key auth, and operation-metadata design; no paused/blocked text |
| Push and confirm CI | Already complete at session start | Local/remote matched and CI was green |

The old prompt suggested reducing five chips to three or four. The deployed correction removed the
fragile part—the outcome promise—from every chip. Keeping five source choices no longer risks a
label contradicting a future result and gives judges paper, README, repository, and compiled-
extension inputs. No new UI revision or cloud build was justified solely to remove one button.

## Live read-only evidence

### Cloud Run configuration

- Canonical URL: <https://verity-7pauedpknq-uc.a.run.app>
- Serving revision: `verity-00018-czq`, 100% traffic.
- `VERITY_ENV=cloud`; `VERITY_ENVIRONMENT=production`.
- Secret mappings present by name for `verity-api-key`, `verity-judge-test-key`, and
  `verity-github-token`; no value was requested or printed.
- `VERITY_REPORT_REPO=ZiyadAzzaz/verity-reports`.

### Public surface

- Unauthenticated `GET /health`: HTTP **200**, `status=ok`, Firestore, Pub/Sub, Cloud Run sandbox,
  GitHub publisher, and no setup error.
- Unauthenticated `POST /api/jobs`: HTTP **401**, preserving the spend/auth boundary.
- `/architecture`: HTTP **200** and current deployed architecture language.
- `ZiyadAzzaz/verity-reports`: public; Issues #1–#12 were readable without repository access.

## Judge API and report flow

The public site is the primary judge interface. A judge enters only the dedicated judge key and a
public source URL. The UI sends `POST /api/jobs` with `X-Verity-Key`, receives a job ID, and polls
`GET /api/jobs/{job_id}` with the same header. At completion, it renders the typed claim, verdict,
confidence, full agent trace, and a direct public GitHub Issue link.

The owner key and judge key are simultaneously valid, independently revocable credentials. The
judge key is not a Google Cloud credential and grants no Console/IAM access; it only passes the
application's protected-route check. It can still cause paid verification work, so it must not be
published. The exact browser flow, PowerShell API example, report locations, and handoff checklist
are now in [JUDGE-HANDOFF.md](JUDGE-HANDOFF.md).

## `.env` decision

`VERITY_ENV=local` in the workstation `.env` is correct. The file configures a local process, not
Cloud Run. The two profiles are separate:

| Location | Correct settings source | Active profile |
|---|---|---|
| Developer workstation | ignored `.env` | local / development |
| Cloud Run service and jobs | deployed environment variables + Secret Manager references | cloud / production |

Changing local `.env` to `cloud` would not update the deployment. It would make local code attempt
to use Firestore, Pub/Sub, Cloud Run Jobs, and Vertex AI with the operator's credentials—an
unnecessary and riskier default. `.env.example` now states this directly, removes the obsolete
pre-Phase-8 comment, and documents optional `VERITY_JUDGE_TEST_KEY` without a value.

## Documentation changes

- Added [JUDGE-HANDOFF.md](JUDGE-HANDOFF.md), the current judge/UI/API/report/credential guide.
- Marked [JUDGE-SIMULATION-TEST-PLAN.md](JUDGE-SIMULATION-TEST-PLAN.md) historical and superseded;
  its old single-key replacement strategy must not be followed.
- Updated `.env.example` to distinguish local workstation configuration from managed cloud
  configuration and to document the second key safely.
- Linked the judge guide from `README.md` and the documentation index.
- Added the private credential-handoff action to the current project status.

## Future-deployment safety fix

The live service correctly maps `VERITY_JUDGE_TEST_KEY` from `verity-judge-test-key`, but the normal
`scripts/deploy.ps1` release path only declared the owner and GitHub secret mappings. A later full
deployment could therefore remove judge access even though the application supports both keys.

The script now:

- accepts an optional local `VERITY_JUDGE_TEST_KEY` without printing it;
- rejects a provided key shorter than 24 characters or identical to the owner key;
- creates/updates `verity-judge-test-key` only when a value is explicitly supplied;
- otherwise detects and preserves an already-provisioned secret by name without reading or
  rotating its value; and
- maps the secret to both the Cloud Run API and pipeline job through the shared secret list.

A source-level regression test locks this behavior. The script was not run, so this fix caused no
cloud action, secret version, IAM mutation, build, revision, or cost.

## Validation

- `git diff --check`: clean.
- Targeted tests with the pinned `agent-dev` Python: **49 passed**, one upstream Starlette/httpx
  deprecation warning.
- PowerShell parser accepted `scripts/deploy.ps1`; Ruff and format checks passed for its regression
  test.
- First two attempts with the base Anaconda interpreter / repository temp directories were
  invalid environmental runs: Windows denied temp cleanup, then the wrong Pydantic environment
  produced failures. They are not represented as product failures or passes. Running the exact
  project interpreter with an OS temp directory was green.
- Live checks above passed; no authenticated job was submitted and therefore no cost-bearing
  pipeline or sandbox execution occurred.

## Remaining owner work

1. Capture the five signed-in Console screenshots using
   [CONSOLE-SCREENSHOTS.md](assets/cloud-evidence/CONSOLE-SCREENSHOTS.md).
2. Confirm whether the Devpost testing-instructions field is judges-only. If it is, provide only
   `VERITY_JUDGE_TEST_KEY`; if it is public, use an organizer-approved private channel.
3. Record the demo around the hosted UI, Issue #9, its three bounded attempts, and a cached replay.
4. Keep the scale-to-zero service live throughout judging.

## Git delivery

- Implementation/documentation commit:
  `d038d6189d6a4cfd45053ad4780bc433d6b09ea7` (`docs: finalize judge handoff and preserve judge key`).
- Pushed to `origin/main`; no force push or history rewrite.
- GitHub Actions run
  [33284062074](https://github.com/ZiyadAzzaz/verity/actions/runs/33284062074): **success** in 3m35s.
- CI passed Ruff, formatting, mypy, the non-Docker suite, both container builds, sandbox import,
  Docker tests, and the isolation validator.
- CI emitted only maintenance notices about GitHub Actions Node 20 compatibility and conda setup
  options; no project gate failed.

## Professional assessment

The application, security boundary, public evidence, and architecture story are ready. The
highest-value remaining work is presentation, not another cloud experiment. A forced green
verdict would weaken Verity's central claim of evidence honesty; Issue #9 plus a cached replay is
a stronger and more defensible judging narrative. The Console screenshots and concise demo are
now the critical path.

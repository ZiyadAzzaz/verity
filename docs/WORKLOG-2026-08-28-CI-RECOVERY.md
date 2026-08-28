# Verity — GitHub Actions CI Recovery

**Date:** 2026-08-28  
**Repository:** `https://github.com/ZiyadAzzaz/verity`  
**Branch:** `main`  
**Reported commit:** `6b8d3372693d238478b318e30948ec3cf7855a50`  
**Starting current revision:** `b4e2618492da1c71063d56941d3cb5fb4c1517de`  
**GitHub workflow:** `CI`  
**Failed/rerun workflow ID:** `33135807770`

## Objective and scope

Investigate GitHub's “CI: All jobs have failed” result for commit `6b8d337`, determine the real
cause, apply the smallest correct remedy, and verify the complete workflow. The request authorized
GitHub Actions inspection and recovery; it did not require or justify cloud, IAM, deployment,
billing, or Phase 8 changes.

## Reconstructed state

- Local `main` and `origin/main` matched `b4e2618`; the worktree was clean.
- GitHub CLI was authenticated as the repository owner with workflow access.
- The reported commit had one failed CI run:
  `https://github.com/ZiyadAzzaz/verity/actions/runs/33135807770`.
- The next commit, `b4e2618`, had already completed the same workflow successfully in run
  `33136211275`.
- The preceding commit `4679679` and multiple earlier main commits also had successful CI runs.

## Failure evidence

The original run's single `test` job passed all gates before the first Docker build:

- dependency installation;
- Ruff lint;
- Ruff formatting check;
- mypy;
- non-Docker pytest suite.

It then failed while Docker tried to resolve the unchanged base image
`python:3.11.15-slim` from Docker Hub:

```text
Head "https://registry-1.docker.io/v2/library/python/manifests/3.11.15-slim":
dial tcp 100.51.90.123:443: i/o timeout
```

Docker reported `DeadlineExceeded` before any Dockerfile instruction ran. The later sandbox build,
Docker tests, and isolation validator were skipped only because GitHub Actions stops subsequent
steps after a failure.

This was an external registry/network timeout, not a source, dependency, lint, type, test,
Dockerfile, or isolation failure. The immediately following successful main run independently
supported that diagnosis before any recovery action was taken.

## Decision and action

The failed job alone was rerun with GitHub Actions. No code, Dockerfile, dependency, workflow,
security gate, or test was changed or weakened. Adding blind retries inside CI or suppressing the
Docker build would have hidden real failures and was rejected as unnecessary after the adjacent
successful run proved the registry outage was transient.

## Verified result

Rerun job `98737364407` completed successfully in **2m26s**. Every step passed:

1. checkout and Miniconda setup;
2. dependency installation;
3. Ruff lint;
4. Ruff formatting check;
5. mypy;
6. non-Docker pytest suite;
7. `Dockerfile.runner` build — the previously failing step;
8. `Dockerfile.sandbox` build;
9. sandbox module import check;
10. Docker-marked pytest suite; and
11. Docker isolation validator.

The historical workflow run for `6b8d337` now has conclusion **success**. Current main commit
`b4e2618` also has a separate successful full CI run.

## Non-blocking warnings

The successful rerun emitted maintenance warnings, not failures:

- GitHub is forcing Node.js 20-based actions onto Node.js 24;
- `setup-miniconda` reports `auto-activate-base` as deprecated in favor of `auto-activate`;
- Conda reports an implicitly added `defaults` channel; and
- Conda printed an informational PyPI integration notice.

These warnings did not cause the reported failure and should not be mixed into an emergency CI
fix. They are candidates for a separate dependency/workflow maintenance change with version review
and a full CI verification pass.

## Cost and security

- Google Cloud incremental cost: `$0.00`; Google Cloud was not accessed.
- GitHub Actions used one hosted-runner rerun; no dollar charge or billing-state change was
  observed or attempted.
- No secrets, tokens, `.env` values, IAM policies, cloud resources, deployments, public access, or
  GitHub Issues were changed.
- Phase 8 remains closed.

## Files changed

- This work record documents the investigation and recovery.
- `docs/STATE.md` links the latest CI result so the repository's current status is explicit.

## Professional assessment and next steps

The incident is resolved. CI correctly caught a hard external dependency failure rather than
silently proceeding, and the bounded rerun proved every project gate. No production code or
workflow behavior should be changed for a single transient Docker Hub timeout when the adjacent
and rerun evidence are both green.

Next, schedule the action/runtime deprecation warnings as routine maintenance after the current
Cloud Run blocker is decided. Keep Docker, Docker-test, and isolation gates mandatory. If registry
timeouts become recurrent rather than isolated, then evaluate a pinned/mirrored base image or a
carefully bounded pull retry with provenance verification.

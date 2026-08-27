# Verity Judge-Simulation Test Plan

**Prepared:** 2026-08-27  
**Execution status:** prepared only; not authorized to run  
**Hard gate:** do not execute until the owner explicitly authorizes Phase 8 and the service is
publicly invokable  
**Required availability:** keep the submitted service publicly testable from 2026-09-01 through
2026-10-01; do not tear it down during judging

## Purpose

Exercise the deployed product exactly as a judge would: from the public URL, using only the
published testing instructions and a dedicated judge credential. The pass must demonstrate two
live outcome types, GitHub artifact filing, cache/deduplication, and every Devpost link.

This plan does not authorize `allUsers`, a service update, a verification request, or a GitHub
Issue. Those actions occur only after the Phase 8 checkpoint is explicitly approved.

## Credential decision

The tested release accepts one runtime variable, `VERITY_API_KEY`. It does not support two active
keys. Adding dual-key code now would require a new immutable release and another build. The safest
no-code Phase 8 transition is therefore:

1. The owner generates `VERITY_JUDGE_TEST_KEY` locally; it is never pasted into chat, Markdown,
   Git, shell arguments, or screenshots.
2. Create Secret Manager secret `verity-judge-test-key` and transfer the local value through an
   OS-temp file that is securely removed.
3. Grant only `verity-app@verity-506800.iam.gserviceaccount.com` accessor on that secret.
4. Before public IAM is granted, update only the Cloud Run service mapping so runtime
   `VERITY_API_KEY` references `verity-judge-test-key:latest`.
5. Confirm the existing personal/admin key is not used in the public testing instructions.

This keeps the judge credential separate without rebuilding the already tested image. If the
owner needs simultaneous admin and judge keys, implement and test a key-ring feature as a new
release instead of weakening this plan.

## Preconditions

- Phase 7 private health, exact digest/configuration, correct OIDC delivery, wrong-audience
  rejection, and exact IAM evidence have passed.
- The owner has explicitly authorized Phase 8.
- `allUsers` has `roles/run.invoker` only on service `verity`; protected routes still require the
  API key.
- Service min instances is `0`, max instances is `2`, and pipeline/sandbox max retries are `0`.
- The judge key secret mapping is verified by name/version reference only; its value is never
  printed.
- The candidate URLs below are selected at execution time so the first one is genuinely absent
  from Firestore/cache and has not been used by earlier catalogue tests.
- Projected cost for each claim is below `$10`, cumulative spend is below `$50`, and no billing,
  payment, budget, quota, or plan change is required.

## Evidence worksheet

Record UTC timestamps, HTTP status, safe response fields, job IDs, execution names, immutable
digests, terminal verdicts, Issue URLs, cache behavior, and closest observable cost in the dated
production work record. Never record keys, tokens, Authorization headers, or secret values.

### Test A — genuinely unseen claim

1. Choose a public repository/paper URL not present in the live Firestore URL index or prior work
   records. Record the read-only absence check.
2. Submit through the public URL with the dedicated judge key, exactly following the Devpost test
   instructions.
3. Require an accepted response and record the job ID.
4. Poll through the public API at a bounded interval until a documented terminal state; stop on a
   failed infrastructure state or timeout instead of resubmitting.
5. Correlate the job to one Pub/Sub delivery, one `verity-pipeline` execution, and its bounded
   `verity-sandbox` execution(s). Require retries `0` and the approved digests/identities.
6. Confirm the terminal verdict is defensible from the stored trace and that an Issue was filed in
   `ZiyadAzzaz/verity-reports`.
7. Validate the Issue URL with a read-only HTTP/GitHub lookup: correct repository, numeric Issue
   path, HTTP success, title/body matching the job, and no secret or unsafe Markdown content.

### Test B — likely clean verification outcome

1. Choose a second, still-fresh source with a small deterministic claim and public reproduction
   path that is likely to complete cleanly.
2. Repeat the bounded submission and evidence chain once.
3. Require a different live outcome type from Test A when feasible. Do not manipulate evidence or
   relabel an honest outcome merely to produce visual variety.
4. Confirm its separate terminal verdict and real Issue link.

### Test C — live dedup/cache

1. Re-submit exactly one URL from Test A or B using the same public instructions and judge key.
2. Require the response to identify the existing/cached job.
3. Confirm no new pipeline execution, sandbox execution, model work, or GitHub Issue is created.
4. Record response time and the cache/dedup indicator. A fast response alone is not sufficient;
   the absence of new downstream work is required.

### Test D — Devpost link resolution

Open each link in a fresh unauthenticated browser session and record final URL/status plus one
screenshot where appropriate:

- public GitHub repository;
- hosted Verity project URL;
- architecture page and the exact architecture diagram image asset;
- public testing instructions; and
- both evidence Issue links produced above.

Reject redirects to sign-in, private/permission errors, missing images, mixed-content errors, or
links that work only in the owner's authenticated session.

## Pass criteria

- Two fresh public submissions reach honest terminal outcomes with real, correctly formatted
  GitHub Issues.
- At least two live outcome types are demonstrated, unless the evidence honestly produces the
  same type—in that case report the limitation and choose one additional bounded source only with
  owner/cost approval.
- One exact duplicate is served from dedup/cache without new downstream work or Issue creation.
- Every Devpost link resolves unauthenticated.
- No hard-stop condition, secret exposure, retry drift, unexpected IAM, or cost threshold occurs.

## Judging-period operations

- Keep service `verity`, the two jobs, required identities, secrets, topic/subscription, Firestore
  data, images, and public invoker binding intact from September 1 through October 1.
- Keep min instances at `0`; do not raise capacity speculatively.
- Perform a small read-only/public health and link check before submission and periodically during
  judging. Do not generate recurring verification jobs merely as uptime probes.
- Do not include these resources in a generic cost-cleanup or teardown before October 2. Any later
  teardown requires owner approval and a final evidence backup/check.

## Professional assessment

This is a judge-realistic, bounded proof rather than a demo-only happy path. Reusing the tested
single-key runtime with a dedicated judge secret is preferable to rebuilding under time pressure,
provided the personal key is not simultaneously required. The strongest evidence will be the
end-to-end linkage from public request to immutable executions, trace, verdict, Issue, and then a
duplicate request that provably launches nothing new.

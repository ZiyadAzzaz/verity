# Verity work record — live content correction and cache hardening

**Date:** 2026-08-30 (Africa/Cairo)  
**Repository:** `ZiyadAzzaz/verity` · branch `main`  
**Cloud project / region:** `verity-506800` / `us-central1`  
**Starting revision:** `34da883c1018acdf5ec993b20b95fb61fd2fc745`  
**Starting live revision:** `verity-00018-czq`  
**Starting image:** `sha256:5562a24da4dc8fe2bd8e04fc6005d74b87402ddc395cbd0f0d45a646947a2ba2`

## Objective and boundaries

The owner supplied a newly exported screenshot/PDF showing an old homepage and architecture page,
despite earlier reports that the corrected versions were deployed. This session had to establish
what Cloud Run actually served without cache, identify the real cause, remove hackathon-resource
meta-content from the architecture page, correct false deployment-status text, deploy a fresh
immutable image, and capture new fetched evidence.

Billing, payment, budget, quota, and plan configuration remained untouched. No verification claim,
pipeline execution, sandbox execution, GitHub report Issue, IAM change, or secret read was needed.
The only planned cloud mutations are one API-image build and one Cloud Run service revision.

## Pre-change live verification

Both Cloud Run URL forms were fetched with a unique millisecond query value plus
`Cache-Control: no-cache` and `Pragma: no-cache`:

- `https://verity-7pauedpknq-uc.a.run.app`
- `https://verity-291098081728.us-central1.run.app`

Both returned HTTP 200 and the same current content. Direct string equality—not a visual guess—
showed:

- live `/` was exactly equal to `verity/static/index.html` at HEAD (11,284 characters);
- live `/architecture` was exactly equal to `verity-architecture.html` at HEAD (25,344
  characters);
- homepage labels were `ResNet paper`, `Attention paper`, `requests README`,
  `data-analysis repo`, and `orjson · compiled extension`;
- `requests · verified` was absent;
- architecture contained live/no-role/operation-metadata/multi-key language; and
- the old `design target`, `blocked in production`, and `experimental` text was absent.

Cloud Run independently reported `verity-00018-czq` Ready and receiving 100% traffic from the
expected image digest. The revision became Ready on 2026-08-29 at 23:53:28Z.

## Root cause

The screenshot/PDF did not represent the cache-busted Cloud Run response. The old phrases are
from the pre-refresh HTML removed by commit `bf45edb`; neither Cloud Run domain returned them when
forced to fetch from the network.

The application nevertheless had a real delivery defect that explains how an export made “just
now” could contain old content: both HTML routes returned validators such as ETag/Last-Modified but
no explicit `Cache-Control` policy. A browser could reuse a heuristically cached document or an
already-open stale DOM, and PDF export would faithfully preserve that DOM. The fresh response and
HEAD matched exactly; the stale layer was therefore client-side reuse, enabled by the missing HTML
cache policy—not wrong Cloud Run traffic, a wrong image, or a route reading the wrong file.

## Corrections

### Public HTML

- `/` and `/architecture` now send `Cache-Control: no-store, max-age=0` and
  `Pragma: no-cache`.
- A regression test requires those headers on both routes.
- Another regression test requires source-named TRY ONE chips and rejects
  `requests · verified`.

### Architecture page

The entire final meta-content section was removed. In the old release it was titled “Free tools
available from the hackathon”; in the current source it had been partially repurposed as “Live
controls and operating envelope” but still contained the cloud-credit narrative. Removing the
whole section ensures the page ends on Verity's actual sandbox architecture rather than credits,
GEAR, billing, or hackathon-resource advice.

The route test rejects all of these regressions: free-tools heading, cloud credits, GEAR, billing
tips, design target, experimental, and both forms of production-blocked wording.

### Other current public documentation

False pre-deployment language was corrected in:

- `README.md`;
- `docs/architecture.md`;
- `docs/LOCAL-DEMO.md`;
- `docs/AUDIT-2026-08-24.md` and `docs/SECURITY-QUALITY-REPORT.md`, which now distinguish their
  historical audit baselines from the current deployed resolution; and
- the `CloudRunJobBackend` module documentation.

Historical work records and prompt snapshots remain unchanged because their stale wording is the
evidence of what was true when written, not a claim about current production.

### Judging-period planning clarification

The current judge handoff now says continued uptime throughout judging is convenient, not a hard
contest requirement. The hard requirement is preserving clear demo/repository evidence that the
project was built and deployed on Google Cloud. The service remains live for the immediate demo
recording and submission checks; no teardown action was taken.

## Local validation

- Initial full gate stopped on Ruff formatting only; no test assertion had run or failed.
- Ruff mechanical formatting was applied to `verity/api.py`.
- Complete rerun: Ruff clean, format clean, mypy clean.
- Non-Docker suite: **288 passed, 3 emulator tests skipped, 9 Docker tests deselected**.
- Targeted pre-format suite: **39 passed**.
- The skips accurately report that the official Firestore/Pub/Sub emulators were not running.

## Professional assessment

The earlier server-state report was correct about what Cloud Run served, but incomplete about how
a browser could still display something else. Explicit no-store response headers turn that gap
into a tested guarantee. Removing the meta-content is also the right editorial decision: judges
should see system architecture, security boundaries, evidence flow, and real limitations—not the
team's credit or billing context.

## Immutable build and rollout

- Source commit: `ea3afe191cb2`.
- GitHub Actions run
  [33286294335](https://github.com/ZiyadAzzaz/verity/actions/runs/33286294335): SUCCESS across Ruff,
  formatting, mypy, non-Docker tests, both Docker builds, Docker tests, and isolation validation.
- One API-only Cloud Build:
  `9ab66b04-7fde-4ecc-bb7c-32da6b13e32f`.
- Result: SUCCESS in 1m20s.
- Immutable image:
  `sha256:db29f7040eaf5e3217f103ee25381183d70693bc53d0ab0c40fa683940969d9e`.
- Cloud Run created Ready revision `verity-00019-nfl` and routed 100% traffic to it.
- Only the API service image and `VERITY_AGENT_VERSION=ea3afe191cb2` changed. IAM, ingress,
  scaling, identities, secrets, startup probe, pipeline job, and sandbox job were unchanged.

### Observed usage and closest cost evidence

| Cloud action | Observed usage | Dollar evidence |
|---|---|---|
| API image build | 80 Cloud Build seconds; one 4.6 MiB source upload; one image push | No itemized real-time invoice is exposed; consistent with the pre-action `<$0.10` projection |
| Service rollout | One revision creation, four page fetches, health, and one rejected unauthenticated request | Scale-to-zero and a handful of requests; near-zero incremental usage, no itemized invoice |

No action approached the $10 check-in gate, and no evidence suggests cumulative project spend
approached $50. Billing configuration was neither read nor changed.

## Fresh post-deployment proof

At 2026-08-30 01:46:48–01:46:49 UTC, both Cloud Run domains were fetched again with unique query
values and no-cache request headers.

- `/`: HTTP 200, `Cache-Control: no-store, max-age=0`, `Pragma: no-cache`, byte-for-byte equal to
  `verity/static/index.html` at release HEAD.
- `/architecture`: HTTP 200, the same cache policy, byte-for-byte equal to
  `verity-architecture.html` at release HEAD.
- Correct chips: `ResNet paper`, `Attention paper`, `requests README`, `data-analysis repo`, and
  `orjson · compiled extension`.
- Absent from both returned documents: `requests · verified`, free-tools heading, cloud credits,
  GEAR, billing tips, design target, experimental, and both production-blocked phrasings.
- `GET /health`: HTTP 200, cloud/Firestore/Pub/Sub/Cloud Run/GitHub, no setup error.
- Unauthenticated `POST /api/jobs`: HTTP 401.

The standalone evidence artifact is
[LIVE-CONTENT-CORRECTION-2026-08-30.md](assets/cloud-evidence/LIVE-CONTENT-CORRECTION-2026-08-30.md).

## Final assessment

The live pages are now correct and explicitly non-cacheable. The old screenshot/PDF is useful as
evidence of the missing cache policy, but it must not be reused in the submission. Refresh the URL
or open a private window before capturing the new demo/export; the server will now require a fresh
document on every navigation.

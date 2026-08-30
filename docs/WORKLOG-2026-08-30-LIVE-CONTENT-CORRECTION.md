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

The fresh immutable release and post-deployment evidence are recorded below after execution.

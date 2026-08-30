# Verity work record — final live refresh

**Date:** 2026-08-30 (Africa/Cairo)  
**Repository:** `ZiyadAzzaz/verity` · branch `main`  
**Cloud account:** `ziyadazzazdesigner@gmail.com`  
**Cloud project / region:** `verity-506800` / `us-central1`  
**Starting local revision:** `15d186af78387cc47df831a389daad17d5ee20c0`  
**Starting remote revision:** `e6ed50f310571f14dbc31fddb7327157483e9d26`

## Objective and boundaries

The owner authorized five outcomes:

1. correct the available-credit statement from the superseded `$150` figure to approximately
   `$450` while preserving the independent `$25` target and `$10/action`, `$50 cumulative` gates;
2. push the eleven held commits and confirm CI;
3. spend no more than 15–20 minutes searching for one honest live-cloud `verified` example;
4. confirm the public health/auth/UI/README state; and
5. refresh and deploy the architecture page to describe the finished cloud system.

Billing, payment, budget, quota, and plan configuration remained out of scope. The five signed-in
Google Cloud Console screenshots remained owner-only. Secrets were loaded into process memory for
live requests and were never printed or stored in this record.

## Repository reconstruction and push

- Local `main` was clean and eleven commits ahead of `origin/main`.
- The held history covered the Phase 9 proof, live fixes, corrected UI chips, current inventory,
  status document, and evidence index.
- The credit correction was committed as
  `f7ffb69d0f1c646cff72c34fce1d350c14bba26a` and pushed with all held commits.
- Local and remote `main` matched after the push.
- GitHub Actions run
  [33280721760](https://github.com/ZiyadAzzaz/verity/actions/runs/33280721760) passed every gate:
  Ruff, format, mypy, non-Docker tests, both Docker builds, Docker tests, and isolation validation.

### Credit correction

The current statement is:

> Approximately $450 available credit (Google Cloud no-cost trial + $150 hackathon grant,
> combined on one billing account); project spend target remains approximately $25, with
> stop-and-check-in gates at $10 per action and $50 cumulative. These targets were always
> independent of the total credit size.

It is present in `docs/PROJECT-STATUS-2026-08-29.md`, `docs/STATE.md`, `docs/README.md`, and the
live architecture page. Historical records were not rewritten as if the old information had
never existed; authoritative snapshots received a supersession notice and archived prompts remain
historical evidence. `$150` alert thresholds were correctly left unchanged.

## Bounded live `verified` search

The search used public repositories that supplied their own deterministic benchmark command and
did not require private data or credentials.

### Candidate 1 — context graph benchmark

- URL: `https://github.com/Emmimal/context-graph-benchmark`
- Rationale: 18 deterministic graded queries, two light dependencies, explicit
  `python src/benchmark.py`, and regression tests locking the headline values.
- Initial job: `6afa029c91fd418b88434cb97e27ea49`
- Initial result: infrastructure failure during parsing:

  ```text
  InvalidArgument: 400 Property parsed_claim contains an invalid nested entity.
  ```

This was not counted as a verdict.

### Candidate 2 — memory decay benchmark

- URL: `https://github.com/Emmimal/memory-decay-engine`
- Rationale: Python standard library only, no API, no external dataset, deterministic N=50 run.
- Job: `74cc315fa6b9476d85055478236f3d20`
- Result: `inconclusive`, no captured value, real Issue
  [#11](https://github.com/ZiyadAzzaz/verity-reports/issues/11).

The bounded search therefore ended without a live `verified` verdict. No third unrelated source
was submitted.

## Production defect found and fixed

### Root cause

The parser returned a valid `install_commands: list[list[str]]`. Firestore Standard forbids an
array from directly containing another array, so a real install plan could not be persisted. The
ordinary fixture had an empty install-command list and did not exercise this constraint.

### Resolution

`verity/store.py` now has a Firestore-only reversible codec:

- a list directly nested inside another list is wrapped in a small internal map;
- the map is removed before Pydantic validates a document read from Firestore;
- local memory, SQLite, public response models, and sandbox request schemas are unchanged; and
- every Firestore path that can carry model data uses the same encode/decode boundary.

Regression coverage checks that no encoded array directly contains an array and that the complete
parsed claim round-trips. The official emulator test now also carries two install argv arrays.

### Validation

- Targeted tests: **8 passed**.
- Ruff: clean.
- mypy `verity/store.py`: clean.
- Full non-Docker suite: **286 passed, 3 skipped, 9 deselected**.
- Official emulator command: **did not run** because Docker Desktop was not running; the launcher
  failed to connect to `dockerDesktopLinuxEngine`. This is not reported as a pass.
- CI run [33281916331](https://github.com/ZiyadAzzaz/verity/actions/runs/33281916331): **success**, including
  Docker and isolation gates.
- Commit: `1e0e39bab1f2de03e498c33f9b3ddb329cddad2e`.

### Live proof

Updating only the API service was insufficient because parsing runs in the separate private
`verity-pipeline` job. A validation replay correctly revealed that deployment mismatch instead of
being misreported as a failed fix. The pipeline job was then updated to the same immutable image.

Final validation job: `731c73225bf549e1ab56c67bc83010fc`.

- Firestore persisted and reloaded:
  `[["pip", "install", "networkx", "scikit-learn"]]`.
- Status crossed `parsing → running`; the previous 400 did not recur.
- One initial plus three repaired executions produced four fresh `verity-sandbox` executions.
- The job completed `could_not_verify` after the bounded three-attempt limit.
- No reproduced scalar was asserted.
- Real artifact: [verity-reports #12](https://github.com/ZiyadAzzaz/verity-reports/issues/12).

This is conclusive production evidence for the storage fix even though it is not the desired
`verified` claim outcome.

## Architecture page refresh

The page now describes the deployed system rather than the pre-deployment design:

- public scale-to-zero Cloud Run API with public reads and two separately managed write keys;
- authenticated Pub/Sub push using a dedicated service account and exact custom audience;
- private pipeline job and a per-attempt no-role sandbox job;
- Firestore durable jobs, traces, sandbox handoffs, verdicts, and deduplication;
- the operation-metadata execution-name fix that avoids granting Cloud Run read permission;
- Parser and Debug as typed ADK reasoning agents, with Environment and Reporter deterministic by
  design; and
- the correct approximately `$450` credit context and independent spend gates.

`tests/test_api_local.py` now rejects a regression back to “production blocked.” The in-app
browser backend was unavailable, so screenshot-based visual QA did not run and no unrelated
browser mechanism was substituted. HTML structure/text checks, the route test, CI, and live HTTP
checks all passed.

Architecture commit: `bf45edbd08292a306317f3b060e88ed86267236e`.  
Architecture CI: [33281580442](https://github.com/ZiyadAzzaz/verity/actions/runs/33281580442), success.

## Cloud actions, immutable releases, and closest observable cost

| Action | Observed result | Closest observable actual cost evidence |
|---|---|---|
| Two bounded candidate submissions | One parser infrastructure failure; one 7m09s pipeline + one sandbox execution, terminal `inconclusive` | Execution counts and wall times observed; billing export is not configured, so no action-level invoice is available |
| Architecture API-only build `a2958de3-8be8-4731-9cc2-24a85eb10d61` | SUCCESS in 1m14s; digest `sha256:5f96317e…` | 74 Cloud Build seconds + artifact storage; consistent with the pre-action `<$0.10` projection |
| Architecture rollout | `verity-00017-phm`, Ready, 100% | One revision creation and verification requests; scale-to-zero, near-zero incremental usage |
| Firestore-fix API-only build `2f83788a-b259-4296-8512-0122eb9746f8` | SUCCESS in 1m39s; digest `sha256:5562a24d…` | 99 Cloud Build seconds + artifact storage; consistent with the pre-action `<$0.10` projection |
| Fix rollout and first replay | `verity-00018-czq`, one 4m31s pipeline execution; replay exposed stale pipeline image | Revision plus observed execution time; no IAM or sandbox change |
| Pipeline image update and final replay | pipeline image pinned to `sha256:5562a24d…`; one 18m28s pipeline + four sandbox executions | Exact execution names/timestamps observed; no real-time itemized dollar amount available |

Seven Cloud Builds now exist and all are `SUCCESS`. No individual action was projected above $10,
and no evidence indicates cumulative spend approached $50. Billing/payment/budget/quota/plan
configuration was never read or changed. Because the CLI has no itemized real-time invoice without
a billing export, this record reports measured resource usage rather than fabricating dollars.

## Final live state

- Serving revision: `verity-00018-czq`, 100% traffic.
- API image: `sha256:5562a24da4dc8fe2bd8e04fc6005d74b87402ddc395cbd0f0d45a646947a2ba2`.
- Pipeline image: the same pinned digest.
- Public unauthenticated `GET /health`: **200**, cloud JSON, no setup error.
- Unauthenticated `POST /api/jobs`: **401**, `invalid API key`.
- Corrected source-named TRY ONE chips: live.
- `/architecture`: **200**, current cloud architecture; no “production blocked” text.
- README: no “paused” or “experimental, blocked” cloud wording.
- Latest pushed-code CI: green.

## Files changed

- Credit truth and supersession notices across the authoritative status/index documents.
- `verity-architecture.html` — finished live architecture and operating envelope.
- `tests/test_api_local.py` — architecture freshness regression.
- `verity/store.py` — reversible Firestore nested-array codec.
- `tests/test_firestore_store.py` — codec round-trip and Firestore-legality regression.
- `tests/test_cloud_emulators.py` — real-emulator nested install plan.
- `docs/PROJECT-STATUS-2026-08-29.md` — current outcomes, defect, cost inventory, and next work.
- This work record.

## Failures, residual risk, and owner action

1. No honest live-cloud `verified` verdict was found; this remains disclosed.
2. Docker Desktop was stopped, so the newly strengthened emulator integration test did not run
   locally. CI’s Docker gates passed, but the emulator test still requires its dedicated runner.
3. The Firestore codec is proven by unit, CI, and the exact live failing source. Future schema
   additions containing nested arrays are covered by the generic adapter boundary.
4. The five Console screenshots still require the owner’s signed-in browser. Follow
   [CONSOLE-SCREENSHOTS.md](assets/cloud-evidence/CONSOLE-SCREENSHOTS.md); do not substitute old or
   unauthenticated screenshots.
5. The service must remain live through the judging period; `min instances = 0` controls idle
   cost without tearing it down.

## Professional assessment and next steps

The project is submission-ready from a code, deployment, security-boundary, and evidence-integrity
perspective. The bounded search did not produce the cosmetic fourth outcome, but it produced
something more valuable: a real production defect, a narrow fix, regression coverage, and an
end-to-end replay proving the repair without overstating the claim result.

Next, the owner should capture the five Console screenshots, then finish the Devpost copy and demo
recording around the strongest honest story: typed ADK reasoning, a credential-free execution
sandbox, durable evidence, and verdicts that refuse to fabricate success.

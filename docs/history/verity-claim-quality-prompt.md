# Verity — Claim-Quality Honesty Layer

Context: a real run against `github.com/ZiyadAzzaz/Stroke-Data-Analysis` extracted "11 features"
as the claim and correctly reported `could_not_verify` — but that's the wrong kind of finding to
be surfacing. "11 features" isn't a headline performance claim, and the eval phase's network
isolation may have made failure structural rather than evidentiary. Both are real gaps, not demo
bad luck, and both map to the same principle already proven elsewhere in this project: don't let
one label mean two different things.

**Priority order below. Item 1 and 2 first — they strengthen the core honesty story. Item 3 and
4 are lower priority; drop them without hesitation if Section 6 (cloud) needs the time instead.**

## 1. Parser Agent: judge claim significance, not just claim extraction

Currently the Parser Agent extracts the first quantifiable, groundable claim it finds. Extend
it to also assess whether that claim is a genuine headline result (accuracy, F1, BLEU, mAP,
error rate, latency, throughput — a claim the source is actually asserting as its contribution)
versus an incidental descriptive statistic (dataset size, feature count, a table row that isn't
the paper's own claimed result).

- Add a `claim_significance` field to the Parser's typed output: `headline_claim` or
  `incidental_statistic`, with the same grounding discipline already used elsewhere — the
  judgment must be justified by evidence in the source, not a bare label.
- When the best-available claim is `incidental_statistic` (or nothing significant is found),
  the job should terminate with an honest, distinct outcome — e.g. `no_verifiable_claim_found`
  — rather than proceeding to sandbox execution on a claim not worth checking. Do not silently
  downgrade this into `could_not_verify`; it needs to read differently in the UI and the filed
  Issue, the same way `failed` (infrastructure) already reads differently from
  `could_not_verify` (genuine attempt).
- Write this test before wiring it in: feed the Parser a source with only incidental statistics
  and no real headline claim (a plain data-analysis repo like the one that surfaced this) and
  confirm it now correctly declines rather than picking the first number.

## 2. Distinguish environment-incapable outcomes from genuine reproduction failure

The evaluation phase has no network by design — correct for reproducibility, but it means any
repo that fetches data at eval time cannot possibly succeed regardless of whether the claim is
true. Right now that looks identical to a genuine `could_not_verify`.

- Add detection for this specific failure signature (connection errors, DNS failures, timeout
  patterns consistent with a blocked network call) in the Debug Agent's failure analysis.
- When a job's failure is attributable to this — the code needs network access the sandbox
  correctly denies — terminate with a distinct outcome, e.g. `environment_incompatible`, with a
  clear explanation: the claim was never actually tested, the sandbox's isolation made this
  specific repository untestable as written.
- This preserves the meaning of `could_not_verify`: it should only ever mean "we genuinely
  attempted the evaluation and it did not reproduce," not "our sandbox couldn't reach it."

## 3. Guide the demo experience (lower priority)

Add 3–4 example claim URLs as clickable chips on the frontend, covering: one real headline-metric
paper that fails honestly, one repo that verifies successfully, and — once item 1 above exists —
one example that now correctly returns `no_verifiable_claim_found` instead of a misleading
`could_not_verify`. This turns today's weak result into a demonstrated feature.

## 4. Document the limitation plainly (lower priority)

Add a short "Known Limitations" section to the README: claim-significance detection is a
heuristic and won't be perfect on every source; network-isolated evaluation cannot test
data-fetching pipelines, and now surfaces that explicitly via `environment_incompatible` rather
than silently. A few sentences, no more.

## Guardrails, unchanged

- No new outcome label should ever collapse two different meanings together — that's the exact
  mistake this whole prompt exists to fix, don't reintroduce it elsewhere.
- Same testing standard as always: write the test against a real source that exercises the new
  behavior, run it for real, report the real output.
- This work does not block or delay Section 6 (cloud) or the ongoing Gate 5 schedule — treat it
  as parallel, lower-priority work, and stop on it immediately if cloud needs attention.

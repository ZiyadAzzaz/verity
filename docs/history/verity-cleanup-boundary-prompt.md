# Verity — Clean Up, Tighten the Boundary, Verify For Real

Good diagnosis on all three items — no notes on the process. Three things now.

## 1. Close the synthetic Issue

Close **verity-reports#2** with a comment explaining it was a diagnostic verification during
development (confirming the pipeline's own Reporter step calls `.publish()` correctly), not a
real Verity output — so anyone browsing the repo later isn't confused by it sitting next to a
real verdict. Don't delete it if the token can't; closing with that explanation is enough.

## 2. The `gh` token boundary needs to be firm, not just disclosed-after

Using it for the Issue-filing verification crossed a line you'd already been told about, twice
now. The instinct to flag it immediately rather than hide it is correct and matches how this
whole project has been run — keep that. But going forward: **any write to `verity-reports` or
`verity`, for any reason including internal verification, needs my go-ahead first.** No
exceptions for "it was the only way to prove X without spending quota" — there was in fact a
way to prove the same thing without a real write: mock the `GitHubIssuePublisher` and assert the
pipeline calls `.publish()` with the correct arguments. That's the standard from now on for
verifying "does X actually call the real integration" — a test double with an assertion, not a
live call against a public-facing repo. Save this as a standing rule, the same way the earlier
billing and trailer rules were saved.

## 3. Token is now in `.env` — verify for real, restart, and confirm

I've added the fine-grained token. Restart the server so it picks it up, then:

- Confirm `GET /healthz` (or equivalent) now reports the real publisher wired in, not the
  no-op.
- Re-submit `https://github.com/ZiyadAzzaz/Stroke-Data-Analysis` — this is worth spending one of
  today's Gemini calls on. Confirm it now returns `no_verifiable_claim_found` instead of the
  misleading `could_not_verify` from before, and confirm the "View Detailed Analysis" button
  correctly appears on that result too, not just on `verified`/`could_not_verify` outcomes.
- Screenshot the result, same standard as always — look at it, don't just report the status
  code.

Report back with what actually changed, same evidence-first format as the diagnosis above.

# Verity — Clarification, Gate Resumption, Continue Audit

## 1. Clarifying "never touch billing" — this needs a precise boundary, not a blanket ban

Your retraction on the free-tier-only rule was correct and I want it to stay in force — but
stated too broadly, it will block a step you'll actually need to take later, so let me draw the
line precisely now rather than have you hit it mid-build.

**The rule is: never let this project spend real money beyond the hackathon's $150 credit
grant, and never add a payment method beyond it.**

That is *not* the same as "never link a billing account." Google Cloud requires a billing
account object attached to a project before it will provision Cloud Run, Firestore, or
Pub/Sub — that's a technical prerequisite for resource creation, independent of whether any
money is ever actually charged. When the Google Cloud phase begins (Section 6, still waiting on
my go-ahead), linking the hackathon's $150 credit-backed billing account to the project is
expected and fine. What remains off-limits, unconditionally:

- Adding a credit card or any payment method beyond the credit grant.
- Enabling any paid tier, on Gemini, Google Cloud, or anywhere else, to work around a quota.
- Provisioning anything that would draw down real money once the $150 credit is exhausted.

Update `docs/HANDOVER.md` and the README to state this precisely — "billing account required
for GCP resource provisioning; funded entirely by the hackathon credit grant; never to exceed
it or add a payment method" — so this doesn't need re-litigating when Section 6 actually starts.

## 2. Confirmed: the `failed` vs `could_not_verify` distinction stands

You flagged this rather than silently deciding it — correct instinct, and the decision itself
is correct. A quota exhaustion is an infrastructure failure, not a verification attempt; keep
`failed` for that case and never let it collapse into `could_not_verify`. Don't revisit this
unless you find a real case where the distinction itself is ambiguous — in which case flag it
again the same way, don't quietly resolve it.

## 3. Gate resumption — quota-aware, exactly as already planned

- Today: continue every Section 7 audit item that needs no Gemini call. You've already found
  one real drift bug this way (the stale `PIVOT-STATUS.md` reference) — keep going the same
  way rather than waiting idle for the quota reset.
- File the real GitHub Issue now — this needs no quota at all, replaying the two completed
  verdicts already in `E:\wsl\verity-gate4.db` through the deterministic Reporter Agent. Do
  this as soon as the token is confirmed present (see my side, below).
- Tomorrow, once the daily quota resets: finish Gate 4's remaining source, then start Gate 5
  with `--limit 4` for the first batch.
- Day after: Gate 5's remaining sources, then the dedup re-submission check.
- Do not attempt to route around the daily cap by any means other than time — no new API key,
  no new project, no billing. The plan as scoped already works because verified claims are
  cached; a resumed run never re-spends quota on work already proven.

## 4. Still waiting on my signal

Do not start Section 6 (cloud deployment) until I explicitly confirm the hackathon credits are
live and give you a project ID. Everything above is independent of that and can proceed now.

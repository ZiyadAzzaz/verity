# Verity — Cloud Is Live: verity-506800. Hard Payment Safety Rule Effective Immediately.

Google Cloud is active. Project ID: **`verity-506800`**. Available credit: **$450** (0 used).
Budget alerts are being configured on my end at $50/$100/$150 thresholds.

## Absolute rule, effective immediately and permanently for this project

**You must never take, suggest, or automate any action that touches billing, payment methods,
budget caps, quota increases, plan upgrades, or spending configuration — under any
circumstance, for any reason, even if it seems minor or reversible.** If any step in any
workflow would require modifying a payment method, billing account settings, budget alert
thresholds, or anything financial: **stop immediately and ask me before proceeding, with no
exceptions.** This is a hard boundary, not a preference — treat it with the same weight as the
"no real spend beyond the credit grant" rule already in force. Save this to memory exactly as
stated if you have a mechanism to do so.

This does **not** mean avoid using the credits for actual deployment — using compute, Firestore,
Pub/Sub, and Vertex AI within the $450 is expected and fine. The rule is specifically about
touching the *payment/billing configuration itself* — cards, budgets, account tier, spend
limits. Using the service is fine. Configuring how it's paid for is not yours to touch.

## What to do now, in order

1. **Confirm you can see the project** with `gcloud config get-value project` and confirm it
   reports `verity-506800`. Don't proceed until this is confirmed.
2. **Run the sandbox-only identity probe now** — this is the prompt I prepared earlier
   (`verity-sandbox-probe-goahead-prompt.md`), with the project ID filled in:

   ```powershell
   powershell -File scripts/deploy_sandbox_probe.ps1 -ProjectId verity-506800 -Region us-central1
   ```

   Before running it, restate back to me: this deploys **only** the no-role sandbox job — no
   API, no pipeline worker, no Gemini key, no GitHub token, nothing public-facing. Confirm
   that's still true of the current code.

3. **After it runs, report:**
   - The real JSON evidence — all six API denial checks (Firestore write, Secret Manager read,
     Pub/Sub publish, Cloud Run execution, Vertex AI listing, Cloud Storage listing) must show
     explicit `401` or `403`. Any other result is a fail — say so plainly, don't retry past it
     hoping it clears.
   - **The actual dollar cost incurred by this probe run**, as closely as you can estimate or
     confirm from the Cloud Billing console/API — I want a running sense of real spend, not just
     "it's cheap." Do this after every subsequent cloud action too, not just this one.
   - Confirm the production fail-closed guards are still untouched — this probe result alone
     does not authorize removing them; I still confirm that separately after reviewing the
     evidence.

## Stay focused, no scope creep right now

Don't start on P1/P2 items from the earlier audits (evidence provenance, leases/outbox, DNS
rebinding) right now. The only goal for the next work session is: sandbox probe evidence, real
and reviewed. Everything else waits until after that's in my hands and I've said go on the next
step.

## If anything about the account looks wrong

If you see anything suggesting more than the expected $450, an unexpected charge, a billing
account that isn't the one just described, or any state that doesn't match what I've told you
here — stop and tell me immediately rather than proceeding on an assumption.

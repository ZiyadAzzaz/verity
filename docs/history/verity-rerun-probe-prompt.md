# Verity — Authorized: Rerun Sandbox Probe, After One Confirmation

Good stop-and-report on the PowerShell error-handling defect — that was exactly the right call
under the standing rule, and removing the dormant billing-budget mutation logic from
`deploy.ps1` (rather than just leaving it inert behind the guard) was the right defensive
decision too. Both are approved as-is, no changes needed there.

## One thing to confirm before rerunning, not after

The fix was applied and tested for the Artifact Registry existence check specifically. Four
other resources in the inventory are also currently absent and will each need their own
"does this exist yet?" check during the probe: the `verity-sandbox` service account, the sandbox
sentinel secret, the `verification-jobs` sentinel topic, and the `verity-sandbox` Cloud Run Job.

**Confirm explicitly that the `Test-Native` fix is generic and already covers all of these
existence checks, not just the one that happened to fail first.** If it's a shared helper used
uniformly across all four, say so and cite where. If any of the four still uses different
error-handling logic, fix that now, before rerunning — I'd rather not stop-and-restart four more
times on the same class of bug across the next four resource checks.

## Also confirm before running

- The Cloud Build step uses the **default worker pool**, not a private pool — the free 2,500
  minutes/month only applies to the default pool, and a private pool would change the cost
  picture meaningfully.

## Then: rerun the probe

Once both confirmations above are in your report:

```powershell
powershell -File scripts/deploy_sandbox_probe.ps1 -ProjectId verity-506800 -Region us-central1
```

Same standing rules as always:
- Stop immediately on anything other than a clean progression through create-if-missing steps —
  don't retry past an unexpected result hoping it clears.
- All six stolen-token checks must show explicit `401` or `403`. Anything else is a fail, stated
  plainly.
- Report real observed cost (not just projected) after it completes, itemized by resource where
  possible, and confirm which parts landed inside free-tier allowances versus actually drawing
  down the credit.
- Update the work-record document per `WORK-RECORD-STANDARD.md`, same rigor as the last one.
- Production fail-closed guards stay untouched regardless of outcome — that's a separate approval
  after I review the evidence.

Go ahead and run it once the two confirmations above check out.

# Verity documentation

Start here. Three documents carry the current truth; everything else is the evidence trail behind
it, kept because the trail is the point — each record was written when the work happened and still
holds its original dates, commit ids, and test counts.

## Read these three

| Document | What it is |
|---|---|
| [PROJECT-STATUS-2026-08-29.md](PROJECT-STATUS-2026-08-29.md) | **Current source of truth.** What works, what does not, what is left, what it costs |
| [AUDIT-2026-08-24.md](AUDIT-2026-08-24.md) | The security audit that shaped the cloud design |
| [WORK-RECORD-STANDARD.md](WORK-RECORD-STANDARD.md) | How every session records what it did |

`../README.md` is the entry point for someone meeting the project for the first time.

## Running it

- [LOCAL-DEMO.md](LOCAL-DEMO.md) — run the whole system offline, no Google Cloud account
- [architecture.md](architecture.md) — the four roles and the interface seam
- [CLOUD-LIVE-SAFETY.md](CLOUD-LIVE-SAFETY.md) — spend limits and the gates on live cloud work
- [GOOGLE-CLOUD-CONSOLE-INSPECTION.md](GOOGLE-CLOUD-CONSOLE-INSPECTION.md) — read-only Console
  steps for verifying the deployment by hand

## Live evidence

[assets/cloud-evidence/](assets/cloud-evidence/) holds the Phase 9 proof: run logs for all four
attempts including the two that failed, the resulting JSON, the filed Issues as captured pages, the
live UI, and a resource inventory of the deployment. [CONSOLE-SCREENSHOTS.md](assets/cloud-evidence/CONSOLE-SCREENSHOTS.md)
lists the five Console views that need a signed-in session and cannot be captured headlessly.

The failed runs are kept deliberately. `phase9-run1-blocked.json` is a run that reported a clean
pass over a pipeline that could not read a sandbox result at all, which is the single best argument
for testing more than one claim.

## Security record

| Document | What it establishes |
|---|---|
| [SCOPED-CLOUD-SECURITY-FIX.md](SCOPED-CLOUD-SECURITY-FIX.md) | Removing cloud credentials from the sandbox |
| [CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md](CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md) | The no-role sandbox denied six sensitive APIs, live |
| [SCOPED-SECURITY-VALIDATION-2026-08-25.md](SCOPED-SECURITY-VALIDATION-2026-08-25.md) | Validation of the scoped design |
| [SECURITY-QUALITY-REPORT.md](SECURITY-QUALITY-REPORT.md) | Standing security posture |
| [EMULATOR-VALIDATION-2026-08-25.md](EMULATOR-VALIDATION-2026-08-25.md) | Firestore and Pub/Sub adapters against Google's emulators |

## Historical

[STATE.md](STATE.md) was the source of truth until 2026-08-29 and remains the most detailed account
of the health-gate failure — five authenticated requests returning unlogged front-end 404s, and the
elimination of project, region, account, IAM, and network as causes. Its status claims are
superseded; its diagnosis is not.

The `WORKLOG-*` files are per-session records in date order, and the remaining reports
([REVIEW.md](REVIEW.md), [HANDOVER.md](HANDOVER.md), [CHECKIN-REPORT.md](CHECKIN-REPORT.md),
[COMPLETE.md](COMPLETE.md), [PRE-SUBMISSION-AUDIT.md](PRE-SUBMISSION-AUDIT.md),
[PROJECT-ANALYSIS.md](PROJECT-ANALYSIS.md), [PIVOT-STATUS.md](PIVOT-STATUS.md),
[STATUS.md](STATUS.md), and the rest) are snapshots from the moment they were written. Read them as
history rather than as current fact; where any of them disagrees with
[PROJECT-STATUS-2026-08-29.md](PROJECT-STATUS-2026-08-29.md), that document wins.

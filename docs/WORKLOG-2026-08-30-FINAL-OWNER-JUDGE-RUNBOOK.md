# Work record — final owner and judge runbook

**Date:** 2026-08-30

**Scope:** final links, owner actions, judge instructions, project narrative, uptime, and cost

**Cloud mutations:** none

**Billing mutations:** none

## Request

Create one complete Markdown guide explaining what the owner should do now, how a judge tests the
project, where reports appear, whether the hosted link remains available, whether it costs money,
and the project story from start to finish.

## State verified before writing

- Hosted service: `https://verity-7pauedpknq-uc.a.run.app`
- Serving revision: `verity-00019-nfl`, 100% traffic
- API image digest:
  `sha256:db29f7040eaf5e3217f103ee25381183d70693bc53d0ab0c40fa683940969d9e`
- Runtime envelope: 1 CPU, 2 GiB, concurrency 4, maximum two instances, no configured minimum
- Local and `origin/main`: `a8f2997161bec789c10cd57d516201662c027329`
- CI for the revision: successful
- Public health, architecture, repository, and report URLs: available
- Live HTML cache control: `no-store, max-age=0`

No `.env` secret value was read, printed, copied, or recorded.

## Work completed

Created [FINAL-OWNER-AND-JUDGE-RUNBOOK.md](FINAL-OWNER-AND-JUDGE-RUNBOOK.md), covering:

- exact final URLs;
- the owner's immediate submission sequence;
- a copy-ready private judge walkthrough;
- safe judge-key handling;
- browser and API expectations;
- where public GitHub report Issues appear;
- the end-to-end cloud architecture and ADK/deterministic boundary;
- security and verdict narratives;
- a timed four-minute demo outline;
- Devpost submission checks;
- a precise uptime and cost explanation;
- the correct local `.env` versus Cloud Run configuration model;
- a start-to-finish project history;
- troubleshooting and final prioritization.

The cost section uses official Google Cloud pricing and free-trial documentation rather than
assuming that scale-to-zero means every resource is permanently free. It also records the known
approximately $450 combined credit, approximately $25 project target, and $10-per-action/$50-
cumulative check-in gates without changing billing configuration.

## Decisions

1. The browser UI is the primary judge path; raw API instructions are secondary.
2. Only `VERITY_JUDGE_TEST_KEY` should be handed to judges, and only privately.
3. A cached replay is described honestly as durable Firestore deduplication, not a new full
   verification.
4. The missing live-cloud `verified` outcome remains disclosed rather than cosmetically hidden.
5. The hosted URL is described as durable while project, billing, service, IAM, and dependencies
   remain active—not as permanent or guaranteed.
6. The current CPU setting is not mislabeled as strict request-based billing; a quiet service can
   scale to zero, while an existing instance can accrue compute across its lifecycle.
7. The existing deployment should remain unchanged before submission unless a genuine blocking
   defect appears.

## Validation plan

- Markdown whitespace and link references: inspect locally.
- Repository diff: confirm documentation-only scope.
- Push to `origin/main` under the standing normal-code-push authorization.
- Confirm local/remote synchronization and CI status.

## Professional opinion and next work

The build is submission-ready. The owner should spend the remaining time on the five signed-in
Console screenshots, the four-minute video, private judge-key delivery, Devpost copy, and signed-
out link testing. Further architecture changes or open-ended attempts to manufacture a
`verified` cloud result create more risk than judging value.

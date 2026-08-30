# Verity hackathon submission brief

**Hackathon:** All Things Agentic Hackathon

**Track:** Taskmaster

**Submission deadline:** August 31, 2026 at 5:00 PM Pacific Time

**Judging period:** September 1–October 1, 2026

This is the judge-facing source for Devpost copy. It contains no credential value.

## Submission links

| Devpost field | Value |
|---|---|
| Hosted project | <https://verity-7pauedpknq-uc.a.run.app> |
| Source repository | <https://github.com/ZiyadAzzaz/verity> |
| Architecture | <https://verity-7pauedpknq-uc.a.run.app/architecture> |
| Public results | <https://github.com/ZiyadAzzaz/verity-reports/issues> |
| Demo video | **OWNER TODO: add the final public YouTube or Vimeo URL** |

Upload [architecture-full.png](assets/screenshots/architecture-full.png) as the architecture
image if Devpost asks for a separate file. The repository README also contains a compact Mermaid
diagram that renders directly on GitHub.

## Tagline

**Verity runs the evidence before you build on it.**

## One-sentence summary

Verity is an autonomous Google ADK workflow that turns a public AI performance claim into a
typed, sandbox-executed, self-debugged, evidence-backed verdict and durable public report.

## Copy-ready project description

AI teams routinely make decisions from benchmark numbers in papers, repositories, and vendor
pages, but checking those claims is slow, fragile, and usually manual. Verity takes a public URL
and completes that verification workflow autonomously: it reads the source, extracts a precise
numerical claim and its conditions, prepares an evaluation, executes untrusted code in an
ephemeral sandbox, makes at most three transparent repair attempts, compares observed evidence
with the claim, and files a structured GitHub Issue.

The production system runs asynchronously on Google Cloud. A public Cloud Run API persists jobs
and claim memory in Firestore, Pub/Sub invokes a private pipeline using audience-bound Google
OIDC, and the pipeline launches a fresh Cloud Run Job for each sandbox attempt. Parser and Debug
are typed Google ADK `LlmAgent` stages powered by Gemini 3.5 Flash on Vertex AI. Environment and
Reporter are deterministic Python by design, keeping command construction and final numerical
comparison outside generative reasoning.

Verity's twist is that failure is a first-class result. It does not convert a successful process,
missing metric, unavailable dataset, or model guess into “verified.” Every attempt, error, patch,
and observed value is persisted. Live cloud runs have produced
`no_verifiable_claim_found`, `could_not_verify`, and `inconclusive` verdicts, each linked to a
public report rather than hidden to make the demo look greener.

The security boundary is equally deliberate. Untrusted evaluation code runs as a no-role service
account and receives no project or application credentials. Before deployment, a live stolen-
identity probe required explicit denial of Firestore, Secret Manager, Pub/Sub, Cloud Run, Vertex
AI, and Cloud Storage access from the sandbox.

## Features and functionality

- accepts public arXiv, GitHub, and vendor URLs;
- extracts typed claims with metric, value, dataset, source quote, and conditions;
- executes bounded evaluations in isolated Docker or no-role Cloud Run Job sandboxes;
- performs at most three visible, evidence-driven debug attempts;
- stores durable job state, trace, verdict, and canonical-URL claim memory;
- returns completed duplicate claims immediately with `cached=true`;
- produces precise verdict types instead of collapsing all failures together;
- autonomously files a detailed public GitHub Issue;
- supports a complete local profile without a Google Cloud account;
- exposes a live key-gated judge workflow while keeping read-only product evidence public.

## Required technology proof

| Requirement | Implementation | Evidence |
|---|---|---|
| Gemini 3.5 or newer | `gemini-3.5-flash` | `verity/config.py`, live `/health`, Vertex AI logs |
| Google agent framework | Google ADK typed `LlmAgent` for Parser and Debug | `verity/llm.py`, `app/agent.py`, tests |
| Google Cloud infrastructure | Cloud Run service/jobs, Firestore, Pub/Sub, Vertex AI, Secret Manager, Cloud Logging, Artifact Registry | Live URL, architecture, Console evidence |
| Autonomous action | Parse → prepare → execute → debug → compare → persist → file Issue | Live Issues #8, #9, #10, and #12 |
| Asynchronous workflow | Pub/Sub OIDC handoff to private pipeline jobs | Architecture and cloud work records |

## Data sources

Verity reads only the public URL submitted by the user and the public source material it links to,
such as an arXiv paper, a GitHub README/repository, or a vendor benchmark page. It does not ship a
private training dataset. Local demo records are generated from public examples and stored only
to make the no-cost offline walkthrough deterministic.

## Findings and learnings

- A successful process is not evidence that a claimed metric was reproduced.
- Most public claims omit at least one artifact needed for direct reproduction—weights, data,
  evaluation code, or exact environment—and the correct answer is often a precise refusal.
- Agent reasoning is valuable for interpreting claims and failures, but deterministic code should
  own execution boundaries and final numerical comparison.
- A sandbox is not trustworthy merely because it runs in a separate container. Its identity,
  secrets, IAM, network behavior, logs, and control-plane permissions all need explicit tests.
- Durable claim memory prevents retries, redeployments, and judge replays from spending money on
  work already completed.
- Cloud platform details matter: the `/healthz` path was intercepted by Cloud Run, and replacing
  it with `/health` resolved a long, evidence-heavy routing investigation.

## Judging-criteria map

### Innovation and operational utility — 40%

Verity completes an actual multi-step research-engineering chore rather than answering a chat
question. It turns messy source material into execution, bounded recovery, a decision, and a
durable artifact with no human triage between stages.

Best evidence: the live UI followed by [Issue #9](https://github.com/ZiyadAzzaz/verity-reports/issues/9).

### Architectural discipline and tech stack — 30%

The design separates reasoning, deterministic policy, trusted orchestration, and untrusted code.
It uses an explicit state machine, typed schemas, durable Firestore memory, OIDC delivery,
least-privilege identities, bounded retries, and a credential-free execution sandbox.

Best evidence: the [live architecture](https://verity-7pauedpknq-uc.a.run.app/architecture),
[security report](SECURITY-QUALITY-REPORT.md), and
[six-API sandbox proof](CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md).

### Demo and production readiness — 30%

The repository has step-by-step local setup, green CI, a public Cloud Run service, live Firestore/
Pub/Sub/Cloud Run Job execution, public reports, a current architecture diagram, and owner-only
Console evidence instructions.

Best evidence: `.run.app` URL visible in the demo, an unedited UI action, Cloud Run pipeline and
sandbox execution views, and the returned GitHub Issue.

## Testing instructions

Give judges only the dedicated judge key through a confirmed-private Devpost testing field or an
organizer-approved private channel. Then provide this text:

> Open https://verity-7pauedpknq-uc.a.run.app. Paste the separately supplied judge key into
> “Verity API key.” Choose a TRY ONE source or submit a public arXiv, GitHub, or vendor URL. Select
> “Start verification,” follow the durable trace, and open “View detailed analysis” at the final
> verdict. A previously completed URL may return immediately with `cached=true`; that is the
> Firestore-backed deduplication path.

Do not put the owner key or judge key in public submission text, GitHub, screenshots, or video.

## Eligibility and provenance

- Repository created August 22, 2026, inside the August 3–31 submission period.
- Earliest commit: August 22, 2026.
- Apache-2.0 licensed.
- Standard open-source libraries and AI coding assistants were used during implementation and
  review; historical prompts are preserved in `docs/history/` as transparent development
  provenance. Those prompts are not Verity's runtime agent instructions.
- **Owner check before submission:** disclose any pre-existing private code or asset if one was
  incorporated. The repository history itself begins during the contest period.

## Owner-only completion checklist

- [ ] Capture the five signed-in Console screenshots in
  [CONSOLE-SCREENSHOTS.md](assets/cloud-evidence/CONSOLE-SCREENSHOTS.md).
- [ ] Record an English or English-subtitled demo no longer than four minutes.
- [ ] Show an unedited live action plus the `.run.app` URL and Google Cloud Console proof.
- [ ] Upload the video publicly to YouTube or Vimeo and add the link above.
- [ ] Upload the architecture image.
- [ ] Put the dedicated judge key only in a confirmed-private testing channel.
- [ ] Test all links and judge-key behavior in an incognito browser.
- [ ] Keep the hosted service and judge credential available free of charge through October 1,
  2026, as required by the binding contest rules.
- [ ] Check the Devpost account email daily after judging; potential winners can have a short
  response window.

## Optional bonus work—only after the required submission is complete

The rules offer small bonus credit for a public build article/podcast/video and a social post with
`#AllThingsAgenticHackathon`. Publish these only after the required video, screenshots, links,
and submission are safe. Do not add an unnecessary second model at the last minute solely for a
bonus; that would increase architectural and demo risk for at most a small score increment.

## Official references

- [Official rules](https://allthingsagentichackathon.devpost.com/rules)
- [Official FAQ](https://allthingsagentichackathon.devpost.com/details/faqs)
- [Hackathon page and judging criteria](https://allthingsagentichackathon.devpost.com/)

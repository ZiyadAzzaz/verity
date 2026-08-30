# Work record — GitHub judge-readiness audit

**Date:** 2026-08-30

**Scope:** public repository presentation, official-rule compliance, submission narrative,
historical-prompt framing, screenshots, security metadata, and GitHub metadata

**Cloud mutations:** none

**Billing mutations:** none

## Request

Determine whether the public repository is genuinely ready for judging, research the current
hackathon rules, identify anything that looks like an unexplained agent prompt or missing
Markdown, and make the GitHub presentation as competitive as possible.

## Sources checked

- [Official rules](https://allthingsagentichackathon.devpost.com/rules)
- [Official FAQ](https://allthingsagentichackathon.devpost.com/details/faqs)
- [Hackathon page](https://allthingsagentichackathon.devpost.com/)
- Current public repository metadata, tracked files, README, CI, license, documentation, evidence
  assets, and Git history

## Findings

### 1. The implementation was ready; the repository's first impression was not

The README still led with historical local Issue #1 and a long table of old work records before
showing current live-cloud evidence. Since the official rules allow judges to score from the
description, images, and video without running the app, this created avoidable judging risk.

### 2. A tracked architecture screenshot was factually stale

`docs/assets/cloud-evidence/cloud-architecture.png` still displayed “cloud blocked,” “experimental,”
and design-target language. The current HTML and deployed page were already correct; the stale
binary had simply not been refreshed after the source fix. It was replaced with a freshly
captured current live page and visually inspected.

### 3. Prompt files needed a clear boundary

The public `docs/history/` prompt collection is useful development provenance, but it had no
directory-level explanation. A judge could reasonably mistake superseded implementation prompts
for current runtime prompts or present project state. The archive now has its own README and the
root README explains that current documentation takes precedence.

### 4. The binding availability rule is stricter than the earlier summary

The official Rules state that the working project must be available free of charge and without
restriction for testing until the judging period ends. Some FAQ/update wording suggests captured
cloud proof may be sufficient, but the Rules are binding. Current guidance now uses the safer
requirement: keep the service and dedicated judge credential active through October 1, 2026.

### 5. Missing judge-facing artifacts

The repository had no single copy-ready Devpost submission narrative and no root security policy.
Both are now present. The only material owner-only gaps remain the signed-in Console screenshots,
the final public four-minute video, the private judge-key handoff, and the Devpost form itself.

## Changes made

- Reworked the top of `README.md` around live product proof and current judging criteria.
- Added CI, license, and live Cloud Run badges and direct product links.
- Embedded the current live UI and a GitHub-rendered architecture diagram.
- Replaced the old lead evidence with live Issues #8, #9, #10, and #12.
- Added a concise 40/30/30 judging-criteria map.
- Reduced the root documentation table to the essential current documents.
- Added [HACKATHON-SUBMISSION.md](HACKATHON-SUBMISSION.md) with copy-ready Devpost text,
  technology proof, findings, testing text, rubric mapping, and owner checklist.
- Added [history/README.md](history/README.md) to frame preserved prompts as superseded
  development provenance, not runtime instructions.
- Added a root [SECURITY.md](../SECURITY.md) with private-reporting guidance and the actual trust
  boundary.
- Refreshed architecture screenshots from the corrected source/live page.
- Updated the screenshot capture source from historical Issue #1 to live-cloud Issue #9 and
  visually verified the new image.
- Corrected judge-period uptime language in the judge handoff and final owner runbook.
- Set the GitHub repository homepage to the live Cloud Run application.
- Replaced the repository description with a concise Google ADK/no-role-sandbox value statement.
- Added `ai-agents`, `cloud-run`, `firestore`, `gemini`, `google-adk`, `pubsub`,
  `reproducibility`, `taskmaster`, and `vertex-ai` discovery topics.
- Enabled GitHub private vulnerability reporting and verified its endpoint returned HTTP 200.

## Security and repository checks

- `.env` remains ignored and untracked; `.env.example` is the tracked template.
- No common Google, GitHub, or private-key secret signature was found in tracked/public text.
- Apache-2.0 license is detected by GitHub.
- Repository creation and earliest commit are both inside the contest submission period.
- All local Markdown links in the judge-facing documents resolve.
- GitHub's Markdown renderer recognized the live links, Mermaid diagram, and submission brief.
- Targeted local validation passed: Ruff and 11 frontend/security tests.
- Full GitHub CI passed on commit `c2a934d`: Ruff, formatting, mypy, non-Docker tests, both
  container builds, sandbox import, Docker tests, and isolation validation.
- CI evidence: <https://github.com/ZiyadAzzaz/verity/actions/runs/33317905558>
- No public cloud, IAM, secret, billing, or deployment state was changed.

## Remaining owner actions

1. Capture the five signed-in Console screenshots.
2. Record and publish the English/English-subtitled video, maximum four minutes.
3. Show an unedited live UI action, `.run.app` URL, and Google Cloud Console proof in the video.
4. Add the public YouTube/Vimeo URL to Devpost and the submission brief.
5. Deliver only the judge key through a confirmed-private testing channel.
6. Submit Devpost before August 31 at 5:00 PM Pacific Time.
7. Keep the service and judge key usable through October 1, 2026.
8. Monitor the account email after judging because winner verification can require a fast reply.

## Professional opinion

The repository now tells the same strong story as the implementation: a real Taskmaster workflow,
not a chatbot; typed reasoning only where necessary; deterministic evidence policy; durable state;
and a genuinely credential-free execution sandbox. No additional model or large feature should be
added before submission. The winning work now is communication and proof: screenshots, a tight
video, private test access, and a complete form.

# Historical prompt archive

This directory preserves the project's dated implementation prompts as development provenance.
They document how scope, safety gates, security requirements, and acceptance criteria evolved
during the hackathon.

These files are **not** runtime agent prompts, judge instructions, deployment commands to execute
now, or the current project state. Many describe an earlier point when cloud deployment was still
blocked, so reading one in isolation can produce a false picture of Verity today.

For current information, use these documents in order:

1. [Hackathon submission brief](../HACKATHON-SUBMISSION.md)
2. [Final owner and judge runbook](../FINAL-OWNER-AND-JUDGE-RUNBOOK.md)
3. [Current project status](../PROJECT-STATUS-2026-08-29.md)
4. [Documentation index](../README.md)

No credential belongs in this archive. Secrets remain in local `.env` or Google Secret Manager
and are excluded from Git.

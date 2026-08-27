# Verity Work-Record Standard

**Effective:** 2026-08-27

Every material Verity work session must finish with a Markdown record in `docs/`. The record is
part of the deliverable, not an optional summary. Use a descriptive name such as
`WORKLOG-YYYY-MM-DD-TOPIC.md`. If one logical task spans multiple sessions, update the existing
record and preserve the chronology instead of creating conflicting sources of truth.

## Required contents

Each record must contain, where applicable:

1. the user's requested objective and the scope boundary;
2. the repository, branch, starting revision, account, and cloud project used;
3. prerequisites and access checks, without recording credentials or secret values;
4. every material action performed and its outcome;
5. findings, defects, security concerns, and their severity;
6. decisions made, the evidence behind them, and alternatives rejected;
7. files changed and why;
8. tests, static checks, runtime checks, and exact results;
9. cloud resources created, changed, or confirmed absent;
10. projected cost before each cloud action and the closest observable actual cost afterward;
11. Git commits and remote-push status;
12. failures, incomplete evidence, residual risk, and anything requiring owner action;
13. the agent's professional assessment; and
14. the recommended next steps, including any explicit approval gate.

## Evidence rules

- Clearly separate observed facts, calculated estimates, and professional opinions.
- Never claim a check passed if it did not run.
- Never record access tokens, API keys, private `.env` values, billing-account identifiers, or
  other secrets. Record only that the required access was available.
- Preserve exact test counts, error conditions, resource names, project IDs, and commit hashes
  when they are safe to disclose.
- Link the newest record from `README.md` or `docs/STATE.md` so another contributor can find it.
- Commit and push the record with the completed work when routine `verity/main` pushing is
  authorized. If work stops before a safe commit, state that explicitly to the owner.

The permanent cloud billing boundary in [CLOUD-LIVE-SAFETY.md](CLOUD-LIVE-SAFETY.md) continues to
apply. A work record reports financial activity; it never authorizes changing billing,
payment, budget, quota, or plan configuration.

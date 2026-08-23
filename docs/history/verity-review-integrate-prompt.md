# Verity — Review Response: Commit, Hygiene, Then Validate

I've reviewed `docs/STATUS.md` in full, including every item in §5 (judgement calls). Here is my
decision on each, and what to do next. Work through this in order — do not reorder for
convenience, the ordering is deliberate (safety of work done so far, before touching anything
that depends on the still-unresolved Docker daemon).

## 1. Commit the outstanding work — do this first, unconditionally

Commit all 14 modified/new files now, regardless of Docker's state. This includes both bug
fixes (§3.4 — key never reaching the model client, §3.5 — Gemini rejecting `additionalProperties`)
and every file listed as uncommitted in §0. Do not wait for Docker to come up before securing
this — those two fixes are not reproducible from memory if lost.

Write a clear commit message that names the two real bugs fixed, not just "wip" — this history
is part of what a judge sees if they check repo activity.

## 2. Fix line-ending hygiene before anything touches a container

Add a `.gitattributes` with:

```
* text=auto eol=lf
```

Normalize the ~50 files git already warned about CRLF on. Pay specific attention to
`Dockerfile.runner` and every `.ps1`/shell script the sandbox path touches — CRLF inside a
script that a Linux container executes is a real, silent failure mode, and I'd rather rule it
out now than debug it at the same time as the sandbox's first real run. Commit this as its own
small commit, separate from item 1.

## 3. Consolidate environment config to a single `.env`

Fold `local.env` into the conventional `.env` (remove the `local.env` / `.env` precedence
mechanism from `verity/config.py`, and the corresponding lines from `.env.example` and
`README.md`). Reasoning: a judge skimming the repo for reproduction steps expects one `.env`
file; a second one with silent precedence is unexplained friction with no functional benefit at
this point. Migrate whatever is currently in `local.env` into `.env` as part of this change, and
confirm `docker` compose / any doc reference is updated to match.

## 4. Judgement calls from §5 — my decisions, do not revisit these

- **§5.1 (async interfaces, typed Pydantic models instead of the prompt's sync/dict sketch):**
  approved, keep as implemented.
- **§5.2 (cloud adapters implemented, not stubbed):** approved, keep as implemented.
- **§5.3 (parser gate redesigned around grounding + contract + known-claim-set, replacing
  exact-value pinning):** approved — this is the correct fix, keep it. Do not revert to
  exact-value pinning even if a future run goes red; investigate the grounding/contract layers
  first, since the whole point of this redesign was to stop testing "did it match one fixture"
  and start testing "did it fabricate a number not in the source."
- **§5.4 (first commit on `main`):** no action needed, correct call given zero prior history.
- **§5.5 (`local.env` precedence):** superseded by item 3 above — consolidate to `.env`.
- **§5.6 (`host_subprocess` backend retained for the Cloud Run container body):** approved,
  keep. Before moving on, point me to (or add, if missing) the specific test that proves
  production configuration rejects `VERITY_SANDBOX_BACKEND=host_subprocess` — I want that
  guarantee to be test-enforced, not just documented.
- **§5.7 (`--read-only` sandbox by default):** approved, leave as-is. Do not pre-loosen it —
  only adjust (larger tmpfs, extra mount) if a real container run in the gates below actually
  fails because of it, and tell me specifically what failed before changing it.

## 5. Docker — I'm troubleshooting this myself in parallel

I'm working through WSL2 update, BIOS virtualization, and a possible pending-reboot issue on my
end — this isn't something you can diagnose from inside the shell, so don't spend further effort
guessing at it. I'll tell you the moment `docker info` responds. In the meantime, proceed with
everything above that doesn't need Docker (items 1–4 all qualify).

## 6. The moment Docker responds, run the gates in this exact order

1. `python scripts/validate_docker_isolation.py` — 7 escape attempts. Exit 0 required before
   anything below touches real untrusted code. If any attempt succeeds (i.e. escapes), stop
   immediately and report it as a blocking security finding, not a bug to patch quietly.
2. `pytest -m docker -q` — the 9 previously-skipped container tests.
3. `python scripts/validate_broken_repo.py` — real debug loop against genuinely broken code.
   Confirm: exactly 3 debug attempts, honest `could_not_verify` verdict, no fabricated result.
4. `python scripts/validate_local_pipeline.py --limit 3` — fast subset first, for an early
   signal before committing to the full run.
5. `python scripts/validate_local_pipeline.py` — the full 8-source gate.

**How to read gate 5, so we're aligned:** passing does not mean all 8 verify. Several sources
exist specifically to exercise the honest-failure path. The gate passes when every job reaches a
terminal verdict backed by real evidence, no job reports a number it never actually observed,
and a re-submitted URL returns from cache in under two seconds. Six honest `could_not_verify`
results out of eight, each with a specific reason, is a passing run — do not treat that number
as something to "fix" by loosening a check.

## 7. After the gates pass

- Fix whatever the gates surface (most likely candidate per your own prediction: a `--read-only`
  conflict or tmpfs size limit) — re-run the specific failing gate after each fix, don't wait
  until the end to re-verify.
- Generate `requirements-lock.txt` via `scripts/lock.ps1`, run from the clean environment.
- Add the local profile (SQLite / asyncio / Docker / AI Studio) to `verity-architecture.html` —
  it currently only shows the cloud-only diagram; it should show both, matching
  `docs/architecture.md`.
- Set up a real GitHub token and file one real verdict as an actual GitHub Issue, end to end —
  this is the literal autonomous deliverable in the pitch, and it should be proven at least once
  before demo day, not left as "verdicts are stored and displayed without it."
- Commit each of the above as its own clean commit, not one large batch.

## 8. Definition of done for this pass

Report back only when: all outstanding work is committed, `.gitattributes` is in place, `.env`
is the single source of environment config, all 5 gates in §6 have been run for real (not
skipped or mocked) with their actual output, and at least one real GitHub Issue has been filed
by the Reporter Agent against a test repo. Show me the real output of each gate, unedited, same
as you've been doing — that reporting standard has already caught two real bugs, keep it.

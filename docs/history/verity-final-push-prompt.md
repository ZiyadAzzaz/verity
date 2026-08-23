# Verity — Final Push: Backup, Validate, Verify Cloud, Audit for Submission

This is the last major phase before demo recording and Devpost submission. Work through the
sections in order. Each section states clearly whether it's yours to execute or requires an
action from me first — don't block on a human-only step if there's agent-only work elsewhere
in this document you can do in parallel.

---

## 1. Protect the work — do this before anything else

All 5 commits currently exist in exactly one place, on a drive that had 0 bytes free earlier
this session. Fix that first.

- Create a **private GitHub repository** for this codebase (use `gh repo create` if the GitHub
  CLI is authenticated; otherwise tell me exactly what to create and I'll hand you the remote
  URL). This repo will later become the public submission repo — don't treat it as throwaway.
- Add it as `origin`, push branch `fix/live-gemini-and-conda-resolution` and push `main`.
- Confirm the push succeeded by showing me the remote's commit list, not just a "done" claim.

This repo is separate from `VERITY_REPORT_REPO` (the throwaway target for filed Issues,
covered in Section 4). Do not conflate them.

## 2. Free up C: now, not later

C: was at 0 bytes free and caused two of the four real bugs found so far. Before running
anything else disk-heavy:

- Clear `AppData\Local\pip\Cache` (2.62 GB) and `AppData\Local\Temp` (2.01 GB) — both are safe,
  regenerable caches, not data.
- Leave `.cache\codex-runtimes`, `.cache\torch`, `.cache\huggingface` alone unless you need the
  space — flag if you do, don't delete without telling me first.
- Re-run `python scripts/check_setup.py` afterward and report the new free space on C:.

## 3. Run the validation gates, in this exact order, once the sandbox image is built

1. `python scripts/validate_docker_isolation.py` — 7 escape attempts, must exit 0. If any
   attempt succeeds, stop immediately and report it as a blocking security finding, not
   something to patch quietly and continue past.
2. `pytest -m docker -q` — the 9 previously-skipped container tests.
3. `python scripts/validate_broken_repo.py` — confirm exactly 3 debug attempts and an honest
   `could_not_verify` verdict, no fabricated result.
4. `python scripts/validate_local_pipeline.py --limit 3` — fast subset, early signal.
5. `python scripts/validate_local_pipeline.py` — full 8-source gate.

This is running on a 5400rpm HDD — expect it to run longer than a typical SSD run. Do not
interrupt a gate that appears slow; let it finish. Report real, unedited output for each gate,
the same standard you've held throughout — that standard has already caught two real bugs, and
I'm relying on it continuing.

**How gate 5 is read:** passing does not mean all 8 sources verify. Several exist specifically
to exercise honest failure. It passes when every job reaches a terminal verdict backed by real
evidence, no job reports a number it never actually observed, and a re-submitted URL returns
from cache in under two seconds. Six honest `could_not_verify` results out of eight is a
passing run — do not treat that as something to fix by loosening a check.

Fix whatever the gates surface, re-running the specific failing gate after each fix rather than
batching fixes and re-running everything at the end.

## 4. File one real GitHub Issue end to end

I will provide, in `.env`:

```ini
VERITY_GITHUB_TOKEN=<fine-grained token, Issues: write only, scoped to one repo>
VERITY_REPORT_REPO=<owner>/<empty throwaway repo>
```

Once that's in place: run the Reporter Agent against a real completed job and confirm an
actual Issue appears in `VERITY_REPORT_REPO`, with the full verdict (claimed vs. actual,
confidence, evidence trail) correctly formatted. This is the literal autonomous deliverable in
the pitch — do not consider it proven until you've seen the real Issue, not just a 201 response
logged.

## 5. Merge and housekeeping — only after Section 3's gates are green

- Merge `fix/live-gemini-and-conda-resolution` into `main` (`--no-ff`), push `main`.
- Generate `requirements-lock.txt` via `scripts/lock.ps1`, run from the clean `agent-dev`
  environment, not an ad hoc one.
- Add the local profile (SQLite / AsyncioJobQueue / Docker sandbox / Gemini AI Studio) to
  `verity-architecture.html` — it currently shows the cloud profile only. It should show both,
  matching what's in `docs/architecture.md`, so a judge sees the full interface-swap story, not
  half of it.
- Each of the above as its own commit, pushed as you go — not batched at the end.

## 6. Cloud verification — do not skip this, it is a hard submission requirement

The hackathon's stated bar is a live demo **running on Google Cloud**, not code that is merely
capable of running there. Everything validated so far is the local profile. The cloud profile
(`VertexAIModelClient`, `FirestoreJobStore`, `PubSubJobQueue`, `CloudRunJobBackend`) is wired
and selectable but has never actually run.

- I will tell you the moment Google Cloud credits are active and a project/billing account
  exists. Do not attempt cloud deployment before I confirm this — you have no way to verify
  billing status from inside the shell, so wait for my explicit go-ahead here rather than
  guessing from an error message.
- The moment I confirm: deploy for real via the ADK's Cloud Run deployment path (per
  `docs/architecture.md`'s cloud profile), set `VERITY_ENV=cloud`, and run at least one full
  claim end to end against real Vertex AI, Firestore, Pub/Sub, and a real Cloud Run Job for
  sandboxed execution — not a partial or mocked run.
- Confirm this the same way you've confirmed everything else: show me the real output, the
  real Cloud Run URL, and the real Firestore/Pub-Sub activity — not a claim that it should
  work based on the code matching the local profile's behavior.
- This live cloud run is what gets recorded for the demo video. The local gates are what goes
  in the README as evidence of engineering rigor. Keep that distinction — don't record the
  demo against the local profile and call it done.

## 7. Final pre-submission audit — run this after Sections 3–6 are all complete

Treat this as a fresh, skeptical pass over the whole project, as if you're a judge seeing it
for the first time, not the person who built it. For each item below, actually check it — don't
report from memory of having done it earlier in the session.

- **Reproduction steps:** clone the pushed repo into a scratch directory and follow
  `README.md` literally, line by line, on both profiles (`VERITY_ENV=local` and, once
  verified, `VERITY_ENV=cloud`). If any step is missing, wrong, or assumes context a stranger
  wouldn't have, fix the README, don't just note it.
- **Architecture diagram:** confirm `verity-architecture.html` and `docs/architecture.md`
  actually match the current code — agent graph, interfaces, both profiles. Flag and fix any
  drift.
- **Secrets:** grep the full git history, not just the working tree, for anything resembling an
  API key or token (`git log -p | grep -i` for common key patterns). Confirm `.env` was never
  committed at any point in the history, including before `.gitattributes`/`.env` consolidation.
- **Test suite:** run the full suite one more time, clean, including the Docker-marked tests,
  and paste the real summary line — not "tests pass," the actual count.
- **Static analysis:** re-run `ruff`, `ruff format --check`, and `mypy --strict` one final time
  on the merged `main`, not the feature branch.
- **Submission checklist** — confirm each explicitly, yes/no, with evidence:
  - [ ] Working MVP deployed on Google Cloud (not just local)
  - [ ] Public GitHub repo, reproduction steps verified by literally following them
  - [ ] Architecture diagram matches current code
  - [ ] No secrets anywhere in git history
  - [ ] Honest-failure path demonstrated and explainable in under 30 seconds
  - [ ] Real GitHub Issue filed by the Reporter Agent, visible in the throwaway repo
  - [ ] Dedup/cache behavior demonstrated (same URL twice, second call near-instant)

Report this audit as its own document (`docs/PRE-SUBMISSION-AUDIT.md`), with the same standard
you've used throughout: what you checked, what you found, and anything you're not fully
confident about — I'd rather know about a shaky item now than discover it during the live demo
recording.

---

## What I'll handle myself (don't wait idle on these — work the rest in the meantime)

- Creating the fine-grained GitHub token and the empty throwaway report repo.
- Confirming when Google Cloud credits/billing are actually active.
- Anything requiring a browser, a BIOS setting, or an account login.

Everything else in this document is yours. Work through Sections 1–5 now; Section 6 waits on my
signal; Section 7 runs only once 1–6 are genuinely complete, not in parallel with them.

# Verity — Cleanup, Demo-Cache Protection, Stronger Verified Case

Approved: items 5.1 and 5.3 from `docs/REVIEW.md`, now. Item 5.2 stays deferred until after
Section 6 (cloud), exactly as you proposed — don't touch the doc consolidation yet.

## 1. Move the prompt files now

Move all 11 `verity-*-prompt.md` files from the repo root into `docs/history/`. Not deleted —
the decision trail is genuinely part of the story. Update any relative links that break, and
confirm nothing in the README or `LOCAL-DEMO.md` still points at the old root-level paths.

## 2. Fix the actual root cause of the demo-cache drift, not just this instance of it

This is the second time the shipped demo cache absorbed live experimentation. That's not bad
luck twice — it's because nothing currently prevents the running server from writing to
`docs/assets/demo-cache/verity-demo.db` during ad hoc testing or development.

- Add a real safeguard: either make the shipped demo-cache path read-only by default outside an
  explicit "rebuild demo" mode, or default local development/testing to a separate, throwaway
  SQLite file that is never the one shipped in the repo. Whichever is simpler given the current
  config surface — but there needs to be an actual mechanism, not just a habit of remembering
  not to point at it.
- Confirm right now: is my current test session (I'm live-testing `https://github.com/ijl/orjson`
  against the running server) writing into the shipped demo cache or a separate database? Tell
  me plainly. If it's the shipped one, that's the drift happening again as we speak — stop it
  and tell me before doing anything else in this prompt.
- Add a one-line check to whatever pre-commit/gate process already exists: the shipped demo
  cache should contain exactly the curated set of jobs (currently 4), and a gate should fail
  loudly if it doesn't, rather than relying on someone noticing during a document-writing pass.

## 3. Find a stronger `verified` case

Try `https://github.com/tqdm/tqdm` first, specifically because it's pure Python (no compiled
extension, unlike the orjson case currently in flight) and its README claim is a test-coverage
percentage rather than a timing benchmark — deterministic, not hardware-dependent, so it won't
plausibly land just outside tolerance and come back `contradicted` due to machine speed.

- Budget up to 4 Gemini calls for this, not more without checking in.
- If it verifies cleanly, add it to the demo cache and chip set as the new headline `verified`
  case, replacing or sitting alongside the HTTP-200 one — your call on which reads better.
- Confirm the addition through the shipped demo cache safeguard from item 2, not by writing to
  it directly and hoping it stays curated.

## 4. Report back

Same standard as always — what you actually did, verified by looking at the real result, not
assumed from the change matching intent. Confirm specifically: prompt files moved and links
checked, the demo-cache drift mechanism actually fixed (not just this instance patched), and
whether tqdm produced a usable `verified` case.

Section 6 (cloud) is still the only blocking item and still waits on my explicit signal with a
project ID — none of this touches that.

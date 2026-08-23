# Verity — The "View Detailed Analysis" Button Isn't Showing For Me

I tested and only saw the demo chips from item 3 — not the Issue button from the addendum.
Don't assume the cause, check each of these in order and report which one it actually was
before fixing anything blind.

## 1. Is this actually the server showing the old code?

If the local server was already running from an earlier session, restarting it with a code pull
underneath it wouldn't pick up the change without a restart. Confirm:

- What commit is actually running right now — check the running process's working directory
  and compare to `git log -1` on `main`.
- If it's stale, stop it, confirm `git pull`/checkout is current, and start it fresh.

## 2. Is this a browser cache issue?

Static JS/CSS can stick in the browser after a server restart. Have me hard-refresh
(Ctrl+Shift+R / Ctrl+F5), but don't just tell me to do that blind — first reproduce it yourself
with a fresh headless browser session (no cache to begin with) against the freshly-restarted
server, and confirm the button renders there. If it renders in a clean session but not in my
browser, cache is the answer and I only need to hard-refresh. If it does NOT render even in a
clean session, it's a real bug, not a cache issue — go to item 3.

## 3. Am I testing a claim that was never going to have a button?

This is the most likely real explanation and needs a plain answer, not just a fix: **does the
running app automatically file a GitHub Issue for every completed job, or does that only happen
through the specific scripts you've been using (`file_stored_verdict.py`, the gate replay) and
the two pre-backfilled demo-cache URLs?**

- If auto-filing is NOT wired into the live pipeline path — i.e., a fresh submission through the
  web UI completes with a verdict but never calls the Reporter's publish step — that's the real
  gap, and it's a bigger deal than the button: it means the "autonomous deliverable" claim in
  the pitch isn't actually true for a live, freshly-submitted job, only for the two seeded demo
  cases. If that's what you find, fix the pipeline itself so every completed job (respecting the
  same GitHub-token-present precondition as before) files its Issue automatically — the button
  is downstream of that being true, not a separate feature.
- If auto-filing IS wired in already, then tell me plainly which specific claim URLs, tested
  right now, will show the button — the two demo-cache URLs, or any freshly-submitted one too —
  so I know exactly what to paste to see it working.

## 4. Verify the fix the same way as everything else in this project

Once you know the real cause: reproduce the working button in a real, clean browser session
against the real running server, screenshot it, and give me the exact URL and exact steps to
see it myself — don't tell me "should work now" without having watched it work first.

## Note

Don't spend a live Gemini call on this unless item 3 requires re-testing a fresh submission to
confirm auto-filing works end to end — if it does, that's worth spending one of today's
remaining calls on, since it's a real gap in the core pitch if true, not just a UI polish item.

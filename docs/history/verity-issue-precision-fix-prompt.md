# Verity — Two Real Precision Bugs Found in verity-reports#4

The `environment_incompatible` outcome itself worked correctly — good confirmation of that
feature. But the filed Issue has two problems, and they're the same class of bug you've already
fixed twice before: a field says one thing, the trace right next to it says another.

## 1. "Fixes applied: None" contradicts the debug trail

Attempt 2's own text says: *"we resolve this by writing an evaluation runner script
(run_eval.py) that discovers and installs the target orjson wheel..."* — that describes a real
fix being written and applied. But the Issue's "Fixes applied" field says "None."

Figure out what that field is actually supposed to mean and make it consistent with what the
trace shows:

- If it means "fixes that ultimately led to a successful reproduction" — fine, but then it
  needs a label that says that ("No successful fix" or similar), not a bare "None" that reads
  as "nothing was ever tried," when the trail right above it clearly shows otherwise.
- If it's supposed to list every fix attempted regardless of outcome, populate it from the
  attempts — run_eval.py being written is a real fix, list it.

Same standard as the `failed`/`could_not_verify` distinction and the attempt-cap display fix:
don't let a summary field say something the detailed trail contradicts. Write a test that fails
if a job with any applied patch in its debug trail reports an empty "Fixes applied" section
without an explicit "no successful fix" qualifier.

## 2. Execution evidence shows git clone noise, not the actual failure output

The Issue's "Execution evidence" section is entirely `git clone` progress lines ("Updating
files: 52%... 98%"). None of the actual pytest/pip output the debug reasoning references (exit
code 5, "no tests collected", the wheel-build failure) is shown. The whole point of this
section is letting someone verify the stated diagnosis independently — right now it doesn't
contain the evidence for what's actually being claimed.

- Find out why: is the relevant output being captured but truncated out by length limits before
  the git clone noise, or is it not being captured at all? Check the actual data flow before
  fixing.
- Fix it so the execution evidence shown prioritizes the output that's actually relevant to the
  diagnosis (the failing command's stdout/stderr for each attempt), not routine setup noise.
  Git clone progress can be summarized to one line ("Repository cloned") rather than shown in
  full — it's not evidence of anything a judge needs to verify.
- Verify against this exact job (or a fresh equivalent run) that the fix actually surfaces the
  real error text, not just that the code change looks right.

## 3. Minor: collapse the clone noise regardless of #2's outcome

Wrap any necessarily-long setup output (git clone progress, pip install logs) in a collapsible
`<details>` block in the rendered Issue, so the default view is short and the underlying detail
is still available to anyone who wants it. Low priority, do it alongside #2 rather than as a
separate pass.

## Verify, don't assume

Same rule as always: after fixing, look at a real rendered Issue (existing or freshly filed) and
confirm both the "Fixes applied" field and the "Execution evidence" section actually read
correctly to someone with no other context — not just that the underlying data now technically
contains the right values.

No cloud work implied or affected by this — still waiting on the credits signal separately.

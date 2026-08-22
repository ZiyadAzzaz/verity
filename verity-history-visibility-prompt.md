# Verity — History Cleanup, Go Public, Capture the Issue

Three decisions from the check-in report, all approved. Do them in this order — the sequence
matters (cleanup before visibility change, not after).

## 1. Strip the trailer from all 12 remaining commits

Rewrite history on `main` to remove the `Co-Authored-By` / AI-attribution trailer from every
commit that still carries it, not just the most recent one. This repo is private and nobody has
cloned it, so a rewrite is safe. After rewriting:

- Verify with the same rigor as everything else this session: grep the full rewritten history
  (`git log -p --all`) to confirm zero commits carry the trailer anymore, don't just trust that
  the rewrite command succeeded.
- Force-push with `--force-with-lease`, same as last time.
- Confirm the new state from the remote via the GitHub API, not from the local push exit code.

## 2. Flip both repositories public

- `ZiyadAzzaz/verity` → public
- `ZiyadAzzaz/verity-reports` → public

Use `gh repo edit --visibility public` for both, now that you have explicit authorization to
make this call yourself — no need to defer it again. Do this only after step 1 is confirmed
complete, not in parallel with it.

## 3. Capture the Issue screenshot

Once `verity-reports` is public, run the capture script as you proposed:

```
python scripts/capture_screenshots.py \
  --url https://github.com/ZiyadAzzaz/verity-reports/issues/1 --name issue-verdict
```

Verify it the same way you verified the architecture screenshots — actually look at the
rendered output, confirm the verdict body and the debug-trail refusal line are both legible in
the shot, not just that a file was written.

## 4. Everything else is unchanged

- Continue the `gh` CLI for read-only verification calls (confirming pushes, reading Issue
  bodies, listing branches) — that's approved and doesn't need the fine-grained token. The
  fine-grained token, when I provide it, is only for further Reporter Agent write activity.
- No further time spent chasing an exact Gemini quota reset hour — the finding that Google
  doesn't publish one is the final answer here, not a gap to keep probing.
- Gate 4/5 continues exactly as scheduled across the remaining days, using the now-proven cache
  behavior.
- Section 6 (cloud) still waits on my explicit signal with a project ID. Nothing here changes
  that.

Report back once steps 1–3 are done, with real evidence for each the same way you've been
doing — the rewritten history's grep result, the confirmed-public status of both repos from the
API, and the screenshot itself.

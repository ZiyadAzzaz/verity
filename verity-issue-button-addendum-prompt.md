# Verity — Addendum: "View Detailed Analysis" Button (Not a PDF)

Adds to the previous prompt (claim-quality honesty layer). This item is scoped alongside item 3
there (demo guidance) — same priority: lower than items 1–2, drop it instantly if cloud needs
the time instead.

## Decision, and why, so this doesn't get re-litigated later

We considered generating a downloadable PDF report per job (via ReportLab/WeasyPrint/pdfkit) and
decided against it. The GitHub Issue the Reporter Agent already files *is* the detailed report —
full debug trail, claimed vs. reproduced, the evidence quote, the Debug Agent's own reasoning
when it refuses to fabricate a fix. Building a second, static rendering of the same data adds a
new dependency and new failure surface for no new capability, at the worst possible time to take
on either. Not doing it.

## What to build instead

A single button/link on the frontend's result view, shown once a job has a filed artifact:

```
[ View Detailed Analysis (GitHub Issue) → ]
```

- Appears next to the verdict summary (`could_not_verify`, `verified`, or the new
  `no_verifiable_claim_found` / `environment_incompatible` outcomes from the other prompt),
  once `artifact_url` (or equivalent existing field) is populated.
- Links directly to the filed Issue on `verity-reports`, opening in a new tab.
- If no Issue has been filed yet for that job (artifact still `not filed`), don't show a dead
  or disabled button — omit it entirely until the artifact exists.
- No new backend work should be needed — the API response already carries whatever field
  indicates the filed Issue's URL (confirm this, since the UI has shown "ARTIFACT: Not filed"
  in existing runs, meaning the field already exists; wire the button to it rather than adding
  new plumbing).

## One doc line, not a feature

Add a single sentence to the README or `docs/LOCAL-DEMO.md`: "Want an offline copy of a result?
Use your browser's own Print → Save as PDF on the result page — no export feature needed." This
answers the PDF question without building anything for it.

## Testing

Confirm the button appears correctly for a cached demo job (one of the two pre-verified URLs,
which already has a filed Issue) and correctly does *not* appear for a freshly-submitted,
still-in-flight job with no artifact yet. Same standard as always — check it by actually looking
at the rendered page, not by trusting that the conditional logic looks right in the diff.

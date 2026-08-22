# Build Verity — Full Implementation Prompt

You are a senior AI systems engineer. Build **Verity**, an autonomous AI-claim verification agent, end-to-end: working code, deployed, and tested. Do not phase this into days — implement everything, then test everything, in one continuous push until it runs cleanly.

## Environment setup (do this first)

Create and use a dedicated conda environment for all work on this project:

```bash
conda create -n agent-dev python=3.11 -y
conda activate agent-dev
```

Install dependencies into `agent-dev` only — never install project dependencies globally or into `base`. Every command you run for this project (installs, tests, local runs) happens with `agent-dev` active. Create a `requirements.txt` (or `pyproject.toml`) that pins everything you install so the environment is reproducible from a clean `conda create`.

## What you are building

Verity is a system that takes a claim about AI/ML performance — a link to an arXiv paper, a GitHub repo with a stated benchmark, or a vendor claim page — and autonomously attempts to verify it by actually running the code, not by reading and summarizing. It self-debugs failures, and produces an honest, evidence-backed verdict as a real artifact (a filed GitHub Issue), not a chat response.

Build to the following architecture exactly.

### Agent pipeline (Google ADK, four agents)

1. **Parser Agent** — accepts a submitted URL (arXiv paper, GitHub repo, or vendor page). Uses Gemini 3.5 Flash's multimodal capability to read the source directly (including tables/figures in PDFs) and extracts a typed claim object: `{ metric, value, dataset, conditions, source_location }`. Validate this against several real, varied sources before moving on — a results table in a PDF, a benchmark line in a README, a claim on a blog post. Do not proceed to the next agent until extraction is reliable across all three input types.

2. **Environment Agent** — given the parsed claim's associated repo, provisions an ephemeral sandbox (a Cloud Run Job or equivalent container), clones the repo, installs its dependencies, and attempts to run its evaluation script. Must run in true isolation — no shared state between verification jobs.

3. **Debug Agent** — on any Environment Agent failure, reads the full error/stack trace, uses Gemini 3.5 Flash to propose a concrete code or dependency patch, applies it, and retries the Environment Agent step. **Hard-cap this loop at 3 attempts.** If still failing after 3 attempts, this is a valid terminal state: produce an honest "could not verify — here's why" result rather than forcing a false success. Log every attempt (error seen, patch proposed, outcome) to Firestore so the full reasoning trail is inspectable.

4. **Reporter Agent** — synthesizes the final structured verdict: claimed value vs. actual reproduced value, confidence level, what (if anything) had to be fixed, and full evidence trail. Files this as a GitHub Issue via the GitHub REST API on the relevant repo, and writes the result back to Firestore.

### Supporting infrastructure

- **Orchestrator API** (FastAPI on Cloud Run): accepts a submitted URL, creates a job record in Firestore, publishes a message to Pub/Sub, returns a job ID immediately.
- **Pub/Sub topic** (`verification-jobs`): decouples intake from processing so verification runs as genuine background work, not a blocking request.
- **Firestore**: stores job status, the full agent trace/log, and a memory bank of previously-verified claims (dedup — if a claim URL was already verified, return the cached result instantly instead of re-running).
- **Cloud Trace / Cloud Logging**: wire this through every agent so the full decision/retry trail is inspectable after the fact, not just in real-time logs.
- **Minimal frontend** (single page on Cloud Run): submit a URL, poll job status, view the final verdict and trace. Keep this deliberately simple — a form, a status indicator, a result view. Do not over-invest in UI polish; the agent pipeline is what's being evaluated.

### Deployment target

Everything must run on Google Cloud, deployed via Cloud Run (API, agent pipeline, and frontend), using Pub/Sub and Firestore as described. Use the Google ADK's Cloud Run deployment path rather than hand-rolling infrastructure. Use the $150 Google Cloud trial credit available through the hackathon's Resources tab; set a billing alert before you start running real workloads, and put auth/API-key protection on any public Cloud Run URL so it can't be hit by stray traffic and drain the credit balance.

## Build order (implement fully, do not stop between stages)

1. Scaffold the `agent-dev` conda environment and project structure.
2. Implement and validate the Parser Agent against at least 3 real, varied inputs before writing any other agent.
3. Implement the Environment Agent against one deliberately-broken real repo so the sandbox/execution path is proven against a genuine failure, not a synthetic one.
4. Implement the Debug Agent's retry loop against that same broken repo until it either fixes it or correctly reports an honest failure within 3 attempts.
5. Implement the Reporter Agent and GitHub Issue filing.
6. Wire the Orchestrator API, Pub/Sub, and Firestore together so a submitted URL flows through all four agents end-to-end without manual intervention.
7. Build the minimal frontend.
8. Deploy everything to Cloud Run for real — do not consider this done while anything is only running on localhost.
9. Wire in Cloud Trace/Logging so the full trace is visible post-hoc.

## Testing requirements (do this as soon as the pipeline is wired, and treat it as equal in priority to building)

- Run at least 5–8 different real claim URLs (papers, repos, vendor pages) end-to-end through the deployed system. Fix whatever breaks.
- Explicitly test the honest-failure path: confirm that after 3 failed debug attempts, the system reports failure clearly rather than fabricating success.
- Confirm the dedup/memory-bank behavior: submitting the same URL twice should return the cached result instantly on the second submission.
- Confirm the whole pipeline still works from a clean `agent-dev` environment (`conda create -n agent-dev python=3.11 -y && conda activate agent-dev && pip install -r requirements.txt`) to catch any dependency drift.
- Produce: a working public Cloud Run URL, a GitHub repo with clear reproduction steps in the README, and a clean architecture diagram matching the pipeline described above.

## What "done" means

A stranger can take the GitHub repo, follow the README, `conda create -n agent-dev`, install requirements, and either run it locally or hit the deployed Cloud Run URL — submit a real claim URL — and watch it autonomously produce a filed, evidence-backed verdict with no manual steps in between. Do not report this as complete until that flow works on a source you have not already tested against.

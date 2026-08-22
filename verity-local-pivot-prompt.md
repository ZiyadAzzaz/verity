# Verity — Local-First Pivot: Implementation Prompt

Context for you (the agent): the project is blocked on Google Cloud billing — credits are pending. Continue the existing Verity build (four ADK agents, API, tests already scaffolded), but restructure the infrastructure layer so it runs entirely locally now, and swaps to Google Cloud later with a config change, not a rewrite. Work inside the `agent-dev` conda environment already created for this project — activate it before running anything.

## 1. Introduce three interfaces before writing any more infrastructure code

Define these as abstract base classes (or `Protocol`s) in a new `verity/interfaces.py`. Every piece of agent logic must depend on these interfaces only — never import SQLite, Docker, or the Gemini SDK directly outside of the adapter implementations below.

```python
class JobStore(ABC):
    """Job state + trace log + memory bank of past verifications."""

    def create_job(self, claim_url: str) -> str: ...
    def get_job(self, job_id: str) -> dict: ...
    def update_job(self, job_id: str, **fields) -> None: ...
    def append_trace(self, job_id: str, event: dict) -> None: ...
    def find_cached_result(self, claim_url: str) -> dict | None: ...


class JobQueue(ABC):
    """Decouples job intake from processing."""

    def publish(self, job_id: str) -> None: ...
    def consume(self, handler: Callable[[str], None]) -> None: ...


class ModelClient(ABC):
    """Gemini calls — claim extraction, patch proposals, verdict writing."""

    def generate(self, prompt: str, files: list | None = None) -> str: ...
```

## 2. Implement local adapters

- **`SQLiteJobStore(JobStore)`** — backs onto a local SQLite file (`verity.db`). Cover all five methods above, including `find_cached_result` for dedup (hash the claim URL as the lookup key).
- **`AsyncioJobQueue(JobQueue)`** — use an `asyncio.Queue` with a background consumer task. This does not need to survive process restarts; that's an acceptable local-dev limitation.
- **`GeminiAIStudioClient(ModelClient)`** — use a Gemini API key from Google AI Studio (no billing account required). Read the key from an environment variable (`GEMINI_API_KEY`), never hardcode it. Add basic retry/backoff — the free tier has real rate limits, and the Debug Agent's retry loop will call this repeatedly.

## 3. Stub the cloud adapters now, implement later

Create empty (or `NotImplementedError`) classes so the swap point is obvious and already wired into config:

- `FirestoreJobStore(JobStore)`
- `PubSubJobQueue(JobQueue)`
- `VertexAIModelClient(ModelClient)`

Wire adapter selection through a single config value (e.g. `VERITY_ENV=local` vs `VERITY_ENV=cloud`), read once at startup, not scattered through the codebase.

## 4. Environment Agent: use Docker, not raw subprocess

The Environment Agent clones and executes **arbitrary third-party code** from GitHub — this must not run directly on the host machine. Implement it as:

1. Build (or reuse) a minimal base image with common language runtimes.
2. For each verification job, `docker run --rm` the cloned repo inside that container, with no network access beyond what's needed to install declared dependencies, and no mount of anything outside a fresh temp directory.
3. Capture stdout/stderr/exit code from the container run and pass that back to the Debug Agent on failure.

This is also the direct forward path to Cloud Run — Cloud Run runs containers, so this Environment Agent implementation should need little to no change when the cloud adapters go live. Confirm Docker is available (`docker info`) before running any verification job, and fail with a clear setup error if it isn't.

## 5. Testing requirements — do these now, locally, don't wait for cloud credits

- Run the full pipeline (Parser → Environment → Debug → Reporter) against at least 5–8 real, varied claim URLs, entirely locally, using the adapters above.
- Explicitly test the honest-failure path: after 3 failed Debug Agent attempts, confirm the system reports failure clearly instead of fabricating success.
- Test dedup: submit the same claim URL twice, confirm the second call returns instantly from `find_cached_result` instead of re-running.
- Test from a clean environment: `conda create -n agent-dev python=3.11 -y && conda activate agent-dev && pip install -r requirements.txt`, confirm the whole local pipeline still runs.
- Confirm Docker isolation: verify a verification job cannot read/write anything outside its own temp directory or reach the host filesystem.

## 6. What "done" means for this pivot

Someone can clone the repo, set `VERITY_ENV=local` and a `GEMINI_API_KEY`, run `conda create -n agent-dev ...`, and submit a real claim URL through the pipeline entirely offline from Google Cloud — no billing account, no GCP project, no card. When cloud credits land, flipping `VERITY_ENV=cloud` and filling in the three stub adapters should be the only remaining work to deploy — not a redesign.

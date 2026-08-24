"""Entrypoint executed inside each fresh Cloud Run sandbox task."""

from __future__ import annotations

import asyncio
import os
import time

from verity.agents.environment import LocalSandboxBackend
from verity.models import EnvironmentResult
from verity.store import FirestoreJobStore


async def run_once() -> int:
    run_id = os.environ.get("VERITY_SANDBOX_RUN_ID")
    if not run_id:
        raise RuntimeError("VERITY_SANDBOX_RUN_ID is required")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required")
    # The sandbox image intentionally omits the application's configuration and ADK stack.
    # Its handoff is always Firestore; selecting a default local profile here previously
    # opened SQLite and made every Cloud Run sandbox request appear missing.
    store = FirestoreJobStore(project)
    run = await store.get_sandbox_run(run_id)
    if run is None:
        raise RuntimeError(f"sandbox request {run_id} was not found")
    backend = LocalSandboxBackend(
        timeout_seconds=run.request.timeout_seconds,
        max_output_chars=int(os.environ.get("VERITY_MAX_OUTPUT_CHARS", "100000")),
    )
    started = time.monotonic()
    try:
        result = await backend.run(
            run.request.job_id,
            run.request.parsed_claim,
            run.request.patches,
            run.request.command_override,
        )
    except Exception as exc:
        result = EnvironmentResult(
            succeeded=False,
            phase="infrastructure",
            stderr=f"{type(exc).__name__}: {exc}",
            duration_seconds=time.monotonic() - started,
        )
    await store.complete_sandbox_run(run_id, result)
    # Evaluation failure is a valid data result consumed by the Debug Agent. The
    # Cloud Run task itself succeeds once that result is durably written.
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run_once()))


if __name__ == "__main__":
    main()

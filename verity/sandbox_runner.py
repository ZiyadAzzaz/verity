"""Entrypoint executed inside each fresh Cloud Run sandbox task."""

from __future__ import annotations

import asyncio
import sys
import time

from verity.agents.environment import LocalSandboxBackend
from verity.cloud_handoff import decode_request_args, encode_result_line
from verity.identity_probe import encode_identity_report, run_identity_probe
from verity.models import EnvironmentResult


async def run_once(arguments: list[str]) -> str:
    """Execute one public-source request without loading credentials or cloud clients."""

    request = decode_request_args(arguments)
    backend = LocalSandboxBackend(
        timeout_seconds=request.timeout_seconds,
        max_output_chars=100_000,
    )
    started = time.monotonic()
    try:
        result = await backend.run(
            request.job_id,
            request.parsed_claim,
            request.patches,
            request.command_override,
        )
    except Exception as exc:
        result = EnvironmentResult(
            succeeded=False,
            phase="infrastructure",
            stderr=f"{type(exc).__name__}: {exc}",
            duration_seconds=time.monotonic() - started,
        )
    return encode_result_line(request.run_id, result)


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-identity":
        project, separator, region = sys.argv[2].partition(":")
        if not separator or not project or not region:
            raise RuntimeError("identity probe requires PROJECT:REGION")
        print(encode_identity_report(run_identity_probe(project, region)), flush=True)
        return
    # The result is one bounded line. Cloud Run collects stdout without the sandbox identity
    # needing logging permissions; the trusted pipeline later reads it by execution label.
    print(asyncio.run(run_once(sys.argv[1:])), flush=True)


if __name__ == "__main__":
    main()

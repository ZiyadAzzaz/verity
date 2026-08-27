"""Manual one-job worker entry point useful for Cloud Run Job diagnostics."""

from __future__ import annotations

import argparse
import asyncio

from verity.config import get_settings
from verity.container import build_container
from verity.telemetry import configure_telemetry


async def _run(job_id: str) -> None:
    settings = get_settings()
    configure_telemetry(
        settings.google_cloud_project,
        cloud=settings.environment == "production",
    )
    container = build_container(settings)
    try:
        await container.pipeline.process(job_id)
    finally:
        await container.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Process one queued Verity job")
    parser.add_argument("job_id")
    args = parser.parse_args()
    asyncio.run(_run(args.job_id))


if __name__ == "__main__":
    main()

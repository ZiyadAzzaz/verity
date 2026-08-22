"""Manual one-job worker entry point useful for Cloud Run Job diagnostics."""

from __future__ import annotations

import argparse
import asyncio

from verity.config import get_settings
from verity.container import build_container


async def _run(job_id: str) -> None:
    await build_container(get_settings()).pipeline.process(job_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process one queued Verity job")
    parser.add_argument("job_id")
    args = parser.parse_args()
    asyncio.run(_run(args.job_id))

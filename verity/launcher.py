"""Launch the durable pipeline after an authenticated Pub/Sub delivery."""

from __future__ import annotations

import asyncio
from typing import Protocol

from verity.pipeline import VerificationPipeline


class PipelineLauncher(Protocol):
    async def launch(self, job_id: str) -> None: ...


class DirectPipelineLauncher:
    def __init__(self, pipeline: VerificationPipeline) -> None:
        self._pipeline = pipeline

    async def launch(self, job_id: str) -> None:
        await self._pipeline.process(job_id)


class CloudRunPipelineLauncher:
    """Start a fresh pipeline task and return without waiting for the benchmark."""

    def __init__(self, project: str, location: str, job_name: str) -> None:
        self._project = project
        self._location = location
        self._job_name = job_name

    async def launch(self, job_id: str) -> None:
        from google.cloud import run_v2

        client = run_v2.JobsClient()
        name = client.job_path(self._project, self._location, self._job_name)
        overrides = run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(
                    args=["-m", "verity.worker", job_id]
                )
            ],
            task_count=1,
        )
        await asyncio.to_thread(
            client.run_job,
            request=run_v2.RunJobRequest(name=name, overrides=overrides),
        )

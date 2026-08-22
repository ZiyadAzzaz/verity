"""Non-blocking intake with canonical-URL deduplication."""

from __future__ import annotations

import asyncio

from verity.interfaces import JobQueue, JobStore
from verity.models import JobStatus, SubmitResponse
from verity.security import canonicalize_url, validate_public_host


class Orchestrator:
    def __init__(
        self,
        store: JobStore,
        queue: JobQueue,
        *,
        validate_dns: bool = True,
    ) -> None:
        self._store = store
        self._queue = queue
        self._validate_dns = validate_dns

    async def submit(self, raw_url: str) -> SubmitResponse:
        canonical = canonicalize_url(raw_url)

        # The claim-memory hit is checked before anything expensive: a repeat submission
        # of an already-verified claim must not re-clone, re-install, or re-benchmark.
        cached = await self._store.find_cached_result(canonical)
        if cached is not None:
            return SubmitResponse(
                job_id=cached.id,
                status=cached.status,
                cached=True,
                status_url=f"/api/jobs/{cached.id}",
            )

        if self._validate_dns:
            await asyncio.to_thread(validate_public_host, canonical)
        job, created = await self._store.create_or_get(canonical)
        if created:
            await self._store.append_trace(
                job.id,
                agent="orchestrator",
                action="job_queued",
                detail={"canonical_url": canonical},
            )
            try:
                await self._queue.publish(job.id, canonical)
            except Exception as exc:
                await self._store.append_trace(
                    job.id,
                    agent="orchestrator",
                    action="publication_failed",
                    detail={"error_type": type(exc).__name__, "error": str(exc)[:2000]},
                )
                await self._store.update_job(
                    job.id,
                    status=JobStatus.FAILED,
                    error=f"Could not publish verification job: {exc}"[:5000],
                )
                raise
        return SubmitResponse(
            job_id=job.id,
            status=job.status,
            cached=not created and job.cached,
            status_url=f"/api/jobs/{job.id}",
        )

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
        # Queue publication is not transactional with job reservation yet. If a process
        # dies between those two operations, the durable record remains QUEUED but the
        # in-process message is gone. Re-publishing an existing queued record on a repeat
        # submission closes that user-visible recovery path. Concurrent duplicates are
        # safe because JobStore.claim_job atomically admits only one pipeline worker.
        should_publish = created or job.status == JobStatus.QUEUED
        if should_publish:
            await self._store.append_trace(
                job.id,
                agent="orchestrator",
                action="job_queued" if created else "queued_job_republished",
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
                # Keep the durable intent queued. Marking it FAILED would turn a transient
                # broker outage into a new benchmark on the next submission and would
                # remove the only state from which publication can be retried.
                raise
        return SubmitResponse(
            job_id=job.id,
            status=job.status,
            cached=not created and job.cached,
            status_url=f"/api/jobs/{job.id}",
        )

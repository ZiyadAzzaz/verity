"""Recovery behavior at the non-transactional store/queue boundary."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from verity.interfaces import JobHandler, JobQueue
from verity.models import JobStatus
from verity.orchestrator import Orchestrator
from verity.security import canonicalize_url
from verity.store import MemoryJobStore

URL = "https://example.com/claim"


@dataclass
class RecordingQueue(JobQueue):
    failures_remaining: int = 0
    published: list[tuple[str, str]] = field(default_factory=list)

    async def publish(self, job_id: str, source_url: str) -> None:
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("temporary broker outage")
        self.published.append((job_id, source_url))

    async def consume(self, handler: JobHandler) -> None:
        return None


async def test_existing_queued_job_is_republished_on_repeat_submission() -> None:
    store = MemoryJobStore()
    canonical = canonicalize_url(URL)
    stranded, created = await store.create_or_get(canonical)
    assert created is True
    queue = RecordingQueue()

    response = await Orchestrator(store, queue, validate_dns=False).submit(URL)

    assert response.job_id == stranded.id
    assert response.status is JobStatus.QUEUED
    assert queue.published == [(stranded.id, canonical)]
    trace = await store.get_trace(stranded.id)
    assert trace[-1].action == "queued_job_republished"


async def test_publication_failure_stays_queued_and_can_be_retried() -> None:
    store = MemoryJobStore()
    queue = RecordingQueue(failures_remaining=1)
    orchestrator = Orchestrator(store, queue, validate_dns=False)

    with pytest.raises(RuntimeError, match="temporary broker outage"):
        await orchestrator.submit(URL)

    canonical = canonicalize_url(URL)
    stranded, created = await store.create_or_get(canonical)
    assert created is False
    assert stranded.status is JobStatus.QUEUED

    response = await orchestrator.submit(URL)

    assert response.job_id == stranded.id
    assert response.status is JobStatus.QUEUED
    assert queue.published == [(stranded.id, canonical)]
    trace = await store.get_trace(stranded.id)
    assert [event.action for event in trace] == [
        "job_queued",
        "publication_failed",
        "queued_job_republished",
    ]

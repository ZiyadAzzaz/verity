"""In-process and Firestore job stores.

The durable local adapter lives in :mod:`verity.sqlite_store`; this module keeps the
ephemeral test/development store and the Google Cloud one. All three implement the single
:class:`verity.interfaces.JobStore` contract.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections import defaultdict
from typing import Any

from verity.interfaces import JobStore
from verity.models import (
    EnvironmentResult,
    JobRecord,
    JobStatus,
    SandboxRun,
    TraceEvent,
    Verdict,
    utc_now,
)


def claim_key(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()


class MemoryJobStore(JobStore):
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._by_url: dict[str, str] = {}
        self._memory: dict[str, str] = {}
        self._traces: dict[str, list[TraceEvent]] = defaultdict(list)
        self._sandbox: dict[str, SandboxRun] = {}
        self._lock = asyncio.Lock()

    async def create_or_get(self, canonical_url: str) -> tuple[JobRecord, bool]:
        async with self._lock:
            existing_id = self._by_url.get(canonical_url)
            if existing_id:
                existing = self._jobs[existing_id]
                if existing.status != JobStatus.FAILED:
                    cached = existing.status == JobStatus.COMPLETED
                    return existing.model_copy(update={"cached": cached}), False
            job_id = uuid.uuid4().hex
            job = JobRecord(
                id=job_id,
                canonical_url=canonical_url,
                source_url=canonical_url,
                status=JobStatus.QUEUED,
            )
            self._jobs[job_id] = job
            self._by_url[canonical_url] = job_id
            return job.model_copy(deep=True), True

    async def get_job(self, job_id: str) -> JobRecord | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy(deep=True) if job else None

    async def claim_job(self, job_id: str) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status != JobStatus.QUEUED:
                return False
            self._jobs[job_id] = job.model_copy(
                update={"status": JobStatus.PARSING, "updated_at": utc_now()}
            )
            return True

    async def update_job(self, job_id: str, **changes: Any) -> JobRecord:
        async with self._lock:
            job = self._jobs[job_id]
            changes["updated_at"] = utc_now()
            updated = job.model_copy(update=changes)
            self._jobs[job_id] = updated
            return updated.model_copy(deep=True)

    async def append_trace(
        self, job_id: str, *, agent: str, action: str, detail: dict[str, Any] | None = None
    ) -> TraceEvent:
        async with self._lock:
            event = TraceEvent(
                sequence=len(self._traces[job_id]),
                agent=agent,  # type: ignore[arg-type]
                action=action,
                detail=detail or {},
            )
            self._traces[job_id].append(event)
            return event.model_copy(deep=True)

    async def get_trace(self, job_id: str) -> list[TraceEvent]:
        async with self._lock:
            return [event.model_copy(deep=True) for event in self._traces[job_id]]

    async def complete_job(self, job_id: str, verdict: Verdict) -> JobRecord:
        job = await self.update_job(job_id, verdict=verdict, status=JobStatus.COMPLETED)
        async with self._lock:
            self._memory[claim_key(job.canonical_url)] = job_id
        return job

    async def find_cached_result(self, canonical_url: str) -> JobRecord | None:
        async with self._lock:
            job_id = self._memory.get(claim_key(canonical_url))
            job = self._jobs.get(job_id) if job_id else None
            if job is None or job.status != JobStatus.COMPLETED:
                return None
            return job.model_copy(deep=True, update={"cached": True})

    async def create_sandbox_run(self, run: SandboxRun) -> None:
        async with self._lock:
            self._sandbox[run.request.run_id] = run.model_copy(deep=True)

    async def get_sandbox_run(self, run_id: str) -> SandboxRun | None:
        async with self._lock:
            run = self._sandbox.get(run_id)
            return run.model_copy(deep=True) if run else None

    async def complete_sandbox_run(self, run_id: str, result: EnvironmentResult) -> None:
        async with self._lock:
            run = self._sandbox[run_id]
            self._sandbox[run_id] = run.model_copy(
                update={"result": result, "completed_at": utc_now()}
            )


class FirestoreJobStore(JobStore):
    """Firestore collections: jobs, claim_memory, per-job trace, sandbox_runs."""

    def __init__(self, project: str | None = None) -> None:
        from google.cloud import firestore

        self._firestore = firestore
        self._db = firestore.AsyncClient(project=project)

    async def create_or_get(self, canonical_url: str) -> tuple[JobRecord, bool]:
        memory_ref = self._db.collection("claim_memory").document(claim_key(canonical_url))
        job_id = uuid.uuid4().hex
        job = JobRecord(
            id=job_id,
            canonical_url=canonical_url,
            source_url=canonical_url,
            status=JobStatus.QUEUED,
        )
        job_ref = self._db.collection("jobs").document(job_id)
        transaction = self._db.transaction()

        @self._firestore.async_transactional
        async def reserve(transaction: Any) -> tuple[str, bool]:
            memory_snapshot = await memory_ref.get(transaction=transaction)
            if memory_snapshot.exists:
                existing_id = str((memory_snapshot.to_dict() or {}).get("job_id", ""))
                if existing_id:
                    existing_ref = self._db.collection("jobs").document(existing_id)
                    existing_snapshot = await existing_ref.get(transaction=transaction)
                    if (
                        existing_snapshot.exists
                        and existing_snapshot.get("status") != JobStatus.FAILED.value
                    ):
                        return existing_id, False
            now = utc_now()
            transaction.set(
                memory_ref,
                {
                    "canonical_url": canonical_url,
                    "job_id": job_id,
                    "status": JobStatus.QUEUED.value,
                    "updated_at": now,
                },
            )
            transaction.set(job_ref, job.model_dump(mode="json"))
            return job_id, True

        selected_id, created = await reserve(transaction)
        selected = job if created else await self.get_job(selected_id)
        if selected is None:
            raise RuntimeError("claim-memory reservation points to a missing job")
        return selected.model_copy(
            update={"cached": not created and selected.status == JobStatus.COMPLETED}
        ), created

    async def get_job(self, job_id: str) -> JobRecord | None:
        if not job_id:
            return None
        snapshot = await self._db.collection("jobs").document(job_id).get()
        return JobRecord.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def claim_job(self, job_id: str) -> bool:
        transaction = self._db.transaction()
        ref = self._db.collection("jobs").document(job_id)

        @self._firestore.async_transactional
        async def claim(transaction: Any) -> bool:
            snapshot = await ref.get(transaction=transaction)
            if not snapshot.exists or snapshot.get("status") != JobStatus.QUEUED.value:
                return False
            transaction.update(
                ref,
                {"status": JobStatus.PARSING.value, "updated_at": utc_now()},
            )
            return True

        return bool(await claim(transaction))

    async def update_job(self, job_id: str, **changes: Any) -> JobRecord:
        changes["updated_at"] = utc_now()
        serialized = _jsonable(changes)
        ref = self._db.collection("jobs").document(job_id)
        await ref.update(serialized)
        job = await self.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    async def append_trace(
        self, job_id: str, *, agent: str, action: str, detail: dict[str, Any] | None = None
    ) -> TraceEvent:
        trace_collection = self._db.collection("jobs").document(job_id).collection("trace")
        sequence = int(utc_now().timestamp() * 1_000_000)
        event = TraceEvent(
            sequence=sequence,
            agent=agent,  # type: ignore[arg-type]
            action=action,
            detail=detail or {},
        )
        await trace_collection.document(f"{sequence:020d}-{uuid.uuid4().hex[:8]}").set(
            event.model_dump(mode="json")
        )
        return event

    async def get_trace(self, job_id: str) -> list[TraceEvent]:
        query = (
            self._db.collection("jobs").document(job_id).collection("trace").order_by("sequence")
        )
        events = [
            TraceEvent.model_validate(snapshot.to_dict()) async for snapshot in query.stream()
        ]
        return [event.model_copy(update={"sequence": index}) for index, event in enumerate(events)]

    async def complete_job(self, job_id: str, verdict: Verdict) -> JobRecord:
        job = await self.update_job(job_id, verdict=verdict, status=JobStatus.COMPLETED)
        memory_ref = self._db.collection("claim_memory").document(claim_key(job.canonical_url))
        await memory_ref.set(
            {
                "canonical_url": job.canonical_url,
                "job_id": job_id,
                "status": JobStatus.COMPLETED.value,
                "verdict": verdict.model_dump(mode="json"),
                "updated_at": utc_now(),
            },
            merge=True,
        )
        return job

    async def find_cached_result(self, canonical_url: str) -> JobRecord | None:
        snapshot = (
            await self._db.collection("claim_memory").document(claim_key(canonical_url)).get()
        )
        if not snapshot.exists:
            return None
        job_id = str((snapshot.to_dict() or {}).get("job_id", ""))
        job = await self.get_job(job_id)
        if job is None or job.status != JobStatus.COMPLETED:
            return None
        return job.model_copy(update={"cached": True})

    async def create_sandbox_run(self, run: SandboxRun) -> None:
        await (
            self._db.collection("sandbox_runs")
            .document(run.request.run_id)
            .create(run.model_dump(mode="json"))
        )

    async def get_sandbox_run(self, run_id: str) -> SandboxRun | None:
        snapshot = await self._db.collection("sandbox_runs").document(run_id).get()
        return SandboxRun.model_validate(snapshot.to_dict()) if snapshot.exists else None

    async def complete_sandbox_run(self, run_id: str, result: EnvironmentResult) -> None:
        await (
            self._db.collection("sandbox_runs")
            .document(run_id)
            .update({"result": result.model_dump(mode="json"), "completed_at": utc_now()})
        )


def _jsonable(value: Any) -> Any:
    from pydantic import BaseModel

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value

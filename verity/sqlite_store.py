"""Durable local job store backed by a single SQLite file.

This is the local-first counterpart to :class:`verity.store.FirestoreJobStore`. It gives
the same three guarantees the pipeline relies on, without a cloud project:

* **Reservation** — ``create_or_get`` and ``claim_job`` run inside ``BEGIN IMMEDIATE``
  transactions, so two concurrent submissions of the same claim produce one job and one
  benchmark run, not two.
* **Durability** — state survives a process restart, which the in-memory store does not.
* **Claim memory** — completed verdicts are indexed by ``sha256(canonical_url)`` so
  ``find_cached_result`` answers a repeat submission without re-running anything.

Records are stored as whole JSON documents rather than shredded into columns. The typed
contracts in :mod:`verity.models` are the schema; SQLite is only the durable envelope,
which is exactly how the Firestore adapter treats its documents too.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

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
from verity.store import claim_key

T = TypeVar("T")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    claim_key     TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    status        TEXT NOT NULL,
    document      TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_claim_key ON jobs (claim_key);

CREATE TABLE IF NOT EXISTS claim_memory (
    claim_key     TEXT PRIMARY KEY,
    canonical_url TEXT NOT NULL,
    job_id        TEXT NOT NULL,
    status        TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trace (
    job_id   TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    document TEXT NOT NULL,
    PRIMARY KEY (job_id, sequence)
);

CREATE TABLE IF NOT EXISTS sandbox_runs (
    run_id   TEXT PRIMARY KEY,
    document TEXT NOT NULL
);
"""


#: The curated demo database that ships in the repository. It backs docs/LOCAL-DEMO.md, so
#: its contents are a documented promise rather than scratch state.
DEMO_CACHE_NAME = "verity-demo.db"
DEMO_CACHE_MARKER = ("docs", "assets", "demo-cache", DEMO_CACHE_NAME)

#: Set to open the shipped demo cache for writing. Only scripts/rebuild_demo_cache.py should.
ALLOW_DEMO_WRITES = "VERITY_ALLOW_DEMO_CACHE_WRITES"


def _is_shipped_demo_cache(path: Path) -> bool:
    parts = tuple(path.resolve().parts)
    return len(parts) >= 4 and parts[-4:] == DEMO_CACHE_MARKER


def guard_demo_cache(path: Path) -> None:
    """Refuse to open the shipped demo cache for writing without an explicit opt-in.

    The demo cache absorbed live experimentation twice: a developer points the server at it
    to demo something, submits a few URLs, and the curated set silently grows. The second
    time it shipped a verdict that contradicted the guide describing it. Remembering not to
    do that is not a mechanism; this is.
    """
    if not _is_shipped_demo_cache(path):
        return
    if os.environ.get(ALLOW_DEMO_WRITES) == "1":
        return
    raise RuntimeError(
        f"Refusing to open the shipped demo cache for writing: {path}. "
        "It is a curated fixture backing docs/LOCAL-DEMO.md, not scratch space. "
        "Point VERITY_SQLITE_PATH somewhere else for development, or run "
        "scripts/rebuild_demo_cache.py to change what ships."
    )


class SQLiteJobStore(JobStore):
    """A :class:`JobStore` over one local SQLite file (default ``verity.db``)."""

    def __init__(self, database_path: str | Path = "verity.db") -> None:
        self._path = Path(database_path)
        guard_demo_cache(self._path)
        if self._path.parent != Path():
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self._path,
            check_same_thread=False,
            isolation_level=None,
            timeout=30,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.executescript(SCHEMA)
        # sqlite3 is synchronous; the lock keeps the shared connection single-writer and
        # keeps `BEGIN IMMEDIATE` blocks from interleaving across pipeline tasks.
        self._lock = asyncio.Lock()

    def close(self) -> None:
        self._connection.close()

    # --- helpers -------------------------------------------------------------

    async def _call(self, function: Callable[..., T], *args: Any) -> T:
        async with self._lock:
            return await asyncio.to_thread(function, *args)

    @staticmethod
    def _dump(record: JobRecord) -> str:
        return json.dumps(record.model_dump(mode="json"), separators=(",", ":"))

    @staticmethod
    def _load(row: sqlite3.Row | None) -> JobRecord | None:
        return JobRecord.model_validate(json.loads(row["document"])) if row else None

    def _write_job(self, record: JobRecord) -> None:
        self._connection.execute(
            "INSERT INTO jobs (id, claim_key, canonical_url, status, document, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET status=excluded.status, document=excluded.document, "
            "updated_at=excluded.updated_at",
            (
                record.id,
                claim_key(record.canonical_url),
                record.canonical_url,
                record.status.value,
                self._dump(record),
                record.updated_at.isoformat(),
            ),
        )

    def _read_job(self, job_id: str) -> JobRecord | None:
        if not job_id:
            return None
        cursor = self._connection.execute("SELECT document FROM jobs WHERE id = ?", (job_id,))
        return self._load(cursor.fetchone())

    # --- job lifecycle -------------------------------------------------------

    async def create_or_get(self, canonical_url: str) -> tuple[JobRecord, bool]:
        return await self._call(self._create_or_get_sync, canonical_url)

    def _create_or_get_sync(self, canonical_url: str) -> tuple[JobRecord, bool]:
        key = claim_key(canonical_url)
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            row = self._connection.execute(
                "SELECT job_id FROM claim_memory WHERE claim_key = ?", (key,)
            ).fetchone()
            if row is not None:
                existing = self._read_job(str(row["job_id"]))
                if existing is not None and existing.status != JobStatus.FAILED:
                    self._connection.execute("COMMIT")
                    cached = existing.status == JobStatus.COMPLETED
                    return existing.model_copy(update={"cached": cached}), False
            job = JobRecord(
                id=uuid.uuid4().hex,
                canonical_url=canonical_url,
                source_url=canonical_url,
                status=JobStatus.QUEUED,
            )
            self._write_job(job)
            self._connection.execute(
                "INSERT INTO claim_memory (claim_key, canonical_url, job_id, status, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(claim_key) DO UPDATE SET job_id=excluded.job_id, "
                "status=excluded.status, updated_at=excluded.updated_at",
                (key, canonical_url, job.id, job.status.value, job.updated_at.isoformat()),
            )
            self._connection.execute("COMMIT")
            return job, True
        except BaseException:
            self._connection.execute("ROLLBACK")
            raise

    async def get_job(self, job_id: str) -> JobRecord | None:
        return await self._call(self._read_job, job_id)

    async def claim_job(self, job_id: str) -> bool:
        return bool(await self._call(self._claim_job_sync, job_id))

    def _claim_job_sync(self, job_id: str) -> bool:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            job = self._read_job(job_id)
            if job is None or job.status != JobStatus.QUEUED:
                self._connection.execute("COMMIT")
                return False
            self._write_job(
                job.model_copy(update={"status": JobStatus.PARSING, "updated_at": utc_now()})
            )
            self._connection.execute("COMMIT")
            return True
        except BaseException:
            self._connection.execute("ROLLBACK")
            raise

    async def update_job(self, job_id: str, **changes: Any) -> JobRecord:
        return await self._call(self._update_job_sync, job_id, changes)

    def _update_job_sync(self, job_id: str, changes: dict[str, Any]) -> JobRecord:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            job = self._read_job(job_id)
            if job is None:
                raise KeyError(job_id)
            updated = job.model_copy(update={**changes, "updated_at": utc_now()})
            self._write_job(updated)
            self._connection.execute(
                "UPDATE claim_memory SET status = ?, updated_at = ? WHERE job_id = ?",
                (updated.status.value, updated.updated_at.isoformat(), job_id),
            )
            self._connection.execute("COMMIT")
            return updated
        except BaseException:
            self._connection.execute("ROLLBACK")
            raise

    async def complete_job(self, job_id: str, verdict: Verdict) -> JobRecord:
        return await self.update_job(job_id, verdict=verdict, status=JobStatus.COMPLETED)

    async def find_cached_result(self, canonical_url: str) -> JobRecord | None:
        return await self._call(self._find_cached_result_sync, canonical_url)

    def _find_cached_result_sync(self, canonical_url: str) -> JobRecord | None:
        row = self._connection.execute(
            "SELECT job_id FROM claim_memory WHERE claim_key = ? AND status = ?",
            (claim_key(canonical_url), JobStatus.COMPLETED.value),
        ).fetchone()
        if row is None:
            return None
        job = self._read_job(str(row["job_id"]))
        if job is None or job.status != JobStatus.COMPLETED:
            return None
        return job.model_copy(update={"cached": True})

    # --- trace ---------------------------------------------------------------

    async def append_trace(
        self, job_id: str, *, agent: str, action: str, detail: dict[str, Any] | None = None
    ) -> TraceEvent:
        return await self._call(self._append_trace_sync, job_id, agent, action, detail or {})

    def _append_trace_sync(
        self, job_id: str, agent: str, action: str, detail: dict[str, Any]
    ) -> TraceEvent:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            row = self._connection.execute(
                "SELECT COALESCE(MAX(sequence) + 1, 0) AS next FROM trace WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            event = TraceEvent(
                sequence=int(row["next"]),
                agent=agent,  # type: ignore[arg-type]
                action=action,
                detail=detail,
            )
            self._connection.execute(
                "INSERT INTO trace (job_id, sequence, document) VALUES (?, ?, ?)",
                (
                    job_id,
                    event.sequence,
                    json.dumps(event.model_dump(mode="json"), separators=(",", ":")),
                ),
            )
            self._connection.execute("COMMIT")
            return event
        except BaseException:
            self._connection.execute("ROLLBACK")
            raise

    async def get_trace(self, job_id: str) -> list[TraceEvent]:
        return list(await self._call(self._get_trace_sync, job_id))

    def _get_trace_sync(self, job_id: str) -> list[TraceEvent]:
        rows = self._connection.execute(
            "SELECT document FROM trace WHERE job_id = ? ORDER BY sequence", (job_id,)
        ).fetchall()
        return [TraceEvent.model_validate(json.loads(row["document"])) for row in rows]

    # --- sandbox run handoff -------------------------------------------------

    async def create_sandbox_run(self, run: SandboxRun) -> None:
        await self._call(self._create_sandbox_run_sync, run)

    def _create_sandbox_run_sync(self, run: SandboxRun) -> None:
        self._connection.execute(
            "INSERT INTO sandbox_runs (run_id, document) VALUES (?, ?)",
            (
                run.request.run_id,
                json.dumps(run.model_dump(mode="json"), separators=(",", ":")),
            ),
        )

    async def get_sandbox_run(self, run_id: str) -> SandboxRun | None:
        return await self._call(self._get_sandbox_run_sync, run_id)

    def _get_sandbox_run_sync(self, run_id: str) -> SandboxRun | None:
        row = self._connection.execute(
            "SELECT document FROM sandbox_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return SandboxRun.model_validate(json.loads(row["document"])) if row else None

    async def complete_sandbox_run(self, run_id: str, result: EnvironmentResult) -> None:
        await self._call(self._complete_sandbox_run_sync, run_id, result)

    def _complete_sandbox_run_sync(self, run_id: str, result: EnvironmentResult) -> None:
        run = self._get_sandbox_run_sync(run_id)
        if run is None:
            raise KeyError(run_id)
        completed = run.model_copy(update={"result": result, "completed_at": utc_now()})
        self._connection.execute(
            "UPDATE sandbox_runs SET document = ? WHERE run_id = ?",
            (json.dumps(completed.model_dump(mode="json"), separators=(",", ":")), run_id),
        )

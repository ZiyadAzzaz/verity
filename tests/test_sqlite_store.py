"""The durable local job store: reservation, restart survival, and claim memory."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from verity.models import (
    Claim,
    Confidence,
    EnvironmentResult,
    JobStatus,
    SandboxRequest,
    SandboxRun,
    Verdict,
    VerdictStatus,
)
from verity.sqlite_store import SQLiteJobStore

URL = "https://github.com/example/project"


def make_verdict(claim: Claim) -> Verdict:
    return Verdict(
        status=VerdictStatus.VERIFIED,
        confidence=Confidence.HIGH,
        claim=claim,
        actual_value=90.0,
        summary="Reproduced within tolerance.",
    )


@pytest.fixture
def store(tmp_path: Path) -> SQLiteJobStore:
    return SQLiteJobStore(tmp_path / "verity.db")


async def test_second_submission_of_the_same_claim_reuses_the_job(
    store: SQLiteJobStore,
) -> None:
    first, created_first = await store.create_or_get(URL)
    second, created_second = await store.create_or_get(URL)
    assert created_first is True
    assert created_second is False
    assert second.id == first.id


async def test_find_cached_result_only_answers_for_completed_jobs(
    store: SQLiteJobStore, parsed_claim
) -> None:
    job, _ = await store.create_or_get(URL)
    assert await store.find_cached_result(URL) is None, "a queued job is not a cached result"

    await store.update_job(job.id, status=JobStatus.FAILED, error="boom")
    assert await store.find_cached_result(URL) is None, "a failed job is not a cached result"

    await store.update_job(job.id, status=JobStatus.QUEUED, error=None)
    await store.complete_job(job.id, make_verdict(parsed_claim.claim))
    cached = await store.find_cached_result(URL)
    assert cached is not None
    assert cached.id == job.id
    assert cached.cached is True
    assert cached.verdict is not None
    assert cached.verdict.status == VerdictStatus.VERIFIED


async def test_state_and_trace_survive_a_process_restart(tmp_path: Path, parsed_claim) -> None:
    path = tmp_path / "verity.db"
    first = SQLiteJobStore(path)
    job, _ = await first.create_or_get(URL)
    await first.append_trace(job.id, agent="parser", action="claim_extracted", detail={"n": 1})
    await first.complete_job(job.id, make_verdict(parsed_claim.claim))
    first.close()

    # A fresh store object stands in for a restarted process.
    reopened = SQLiteJobStore(path)
    recovered = await reopened.get_job(job.id)
    assert recovered is not None
    assert recovered.status == JobStatus.COMPLETED
    assert recovered.verdict is not None
    trace = await reopened.get_trace(job.id)
    assert [event.action for event in trace] == ["claim_extracted"]
    assert await reopened.find_cached_result(URL) is not None
    reopened.close()


async def test_claim_job_admits_exactly_one_delivery(store: SQLiteJobStore) -> None:
    job, _ = await store.create_or_get(URL)
    outcomes = await asyncio.gather(*(store.claim_job(job.id) for _ in range(5)))
    assert sum(outcomes) == 1, "redelivery must not start a second benchmark run"


async def test_concurrent_submissions_reserve_a_single_job(store: SQLiteJobStore) -> None:
    results = await asyncio.gather(*(store.create_or_get(URL) for _ in range(6)))
    assert sum(created for _job, created in results) == 1
    assert len({job.id for job, _created in results}) == 1


async def test_trace_sequence_is_dense_and_ordered(store: SQLiteJobStore) -> None:
    job, _ = await store.create_or_get(URL)
    for index in range(5):
        await store.append_trace(job.id, agent="orchestrator", action=f"step-{index}")
    trace = await store.get_trace(job.id)
    assert [event.sequence for event in trace] == [0, 1, 2, 3, 4]
    assert [event.action for event in trace] == [f"step-{i}" for i in range(5)]


async def test_sandbox_run_round_trip(store: SQLiteJobStore, parsed_claim) -> None:
    request = SandboxRequest(run_id="run-1", job_id="job-1", parsed_claim=parsed_claim)
    await store.create_sandbox_run(SandboxRun(request=request))
    result = EnvironmentResult(
        succeeded=True, exit_code=0, phase="metric", actual_value=90.0, duration_seconds=1.5
    )
    await store.complete_sandbox_run("run-1", result)
    stored = await store.get_sandbox_run("run-1")
    assert stored is not None
    assert stored.result is not None
    assert stored.result.actual_value == 90.0
    assert stored.completed_at is not None

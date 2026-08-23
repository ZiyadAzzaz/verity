"""End-to-end checks over the real local adapters.

Everything here uses the adapters a laptop actually runs — SQLite plus the asyncio queue —
with only the model calls and the sandbox replaced by deterministic doubles. The Docker
backend has its own suite in ``test_docker_sandbox.py``; what is under test here is that
the local infrastructure carries a job from intake to verdict without a cloud project.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from verity.agents.reporter import ReporterAgent
from verity.github import NoopIssuePublisher
from verity.messaging import AsyncioJobQueue
from verity.models import (
    DebugProposal,
    EnvironmentResult,
    JobStatus,
    ParsedClaim,
    PatchOperation,
    VerdictStatus,
)
from verity.orchestrator import Orchestrator
from verity.pipeline import VerificationPipeline
from verity.sqlite_store import SQLiteJobStore


@dataclass
class FakeParser:
    parsed: ParsedClaim

    async def run(self, url: str) -> ParsedClaim:
        return self.parsed


@dataclass
class ScriptedSandbox:
    """Replays a fixed sequence of run outcomes and records what it was asked to do."""

    results: list[EnvironmentResult]
    calls: int = 0
    patches_seen: list[int] = field(default_factory=list)

    async def run(self, job_id, parsed_claim, patches, command_override=None):
        self.patches_seen.append(len(patches))
        result = self.results[min(self.calls, len(self.results) - 1)]
        self.calls += 1
        return result


@dataclass
class ScriptedDebugger:
    calls: int = 0

    async def run(self, parsed_claim, failure, prior_patches, attempt):
        self.calls += 1
        return DebugProposal(
            diagnosis=f"attempt {attempt}: pin the incompatible dependency",
            operations=[
                PatchOperation(
                    kind="write_file",
                    path=f"constraints-{attempt}.txt",
                    new_text="numpy<2\n",
                )
            ],
        )


def failure(index: int) -> EnvironmentResult:
    return EnvironmentResult(
        succeeded=False,
        exit_code=1,
        phase="evaluate",
        stderr=f"ImportError: cannot import name 'foo' (run {index})",
        duration_seconds=0.1,
    )


@pytest.fixture
def store(tmp_path: Path) -> SQLiteJobStore:
    return SQLiteJobStore(tmp_path / "verity.db")


def build_pipeline(store, parsed_claim, sandbox, debugger) -> VerificationPipeline:
    return VerificationPipeline(
        store=store,
        parser=FakeParser(parsed_claim),
        environment=sandbox,
        debugger=debugger,
        reporter=ReporterAgent(NoopIssuePublisher()),
    )


async def test_intake_through_queue_reaches_a_verdict(store, parsed_claim) -> None:
    success = EnvironmentResult(
        succeeded=True,
        exit_code=0,
        phase="metric",
        stdout="accuracy: 90.0",
        actual_value=90.0,
        metric_evidence="accuracy: 90.0",
        duration_seconds=2.0,
    )
    sandbox = ScriptedSandbox([success])
    pipeline = build_pipeline(store, parsed_claim, sandbox, ScriptedDebugger())
    queue = AsyncioJobQueue()
    await queue.consume(pipeline.process)
    orchestrator = Orchestrator(store, queue, validate_dns=False)

    response = await orchestrator.submit(str(parsed_claim.source_url))
    assert response.status == JobStatus.QUEUED
    assert response.cached is False

    await queue.join()
    await queue.close()

    finished = await store.get_job(response.job_id)
    assert finished is not None
    assert finished.status == JobStatus.COMPLETED
    assert finished.verdict is not None
    assert finished.verdict.status == VerdictStatus.VERIFIED
    assert sandbox.calls == 1


async def test_honest_failure_after_exactly_three_attempts_on_the_local_stack(
    store, parsed_claim
) -> None:
    sandbox = ScriptedSandbox([failure(0), failure(1), failure(2), failure(3)])
    debugger = ScriptedDebugger()
    pipeline = build_pipeline(store, parsed_claim, sandbox, debugger)
    queue = AsyncioJobQueue()
    await queue.consume(pipeline.process)
    orchestrator = Orchestrator(store, queue, validate_dns=False)

    response = await orchestrator.submit(str(parsed_claim.source_url))
    await queue.join()
    await queue.close()

    finished = await store.get_job(response.job_id)
    assert finished is not None and finished.verdict is not None
    verdict = finished.verdict
    assert verdict.status == VerdictStatus.COULD_NOT_VERIFY
    assert verdict.actual_value is None, "a failed run must not report a reproduced number"
    assert len(verdict.attempts) == 3
    assert debugger.calls == 3, "the debug loop is hard-capped at three attempts"
    assert sandbox.calls == 4, "one initial run plus exactly three bounded retries"
    assert sandbox.patches_seen == [0, 1, 2, 3], "each retry carries the accumulated patches"

    trace = await store.get_trace(response.job_id)
    assert sum(event.action == "attempt_finished" for event in trace) == 3


async def test_resubmitting_a_verified_claim_returns_instantly_from_claim_memory(
    store, parsed_claim
) -> None:
    success = EnvironmentResult(
        succeeded=True,
        exit_code=0,
        phase="metric",
        stdout="accuracy: 90.0",
        actual_value=90.0,
        duration_seconds=2.0,
    )
    sandbox = ScriptedSandbox([success])
    pipeline = build_pipeline(store, parsed_claim, sandbox, ScriptedDebugger())
    queue = AsyncioJobQueue()
    await queue.consume(pipeline.process)
    orchestrator = Orchestrator(store, queue, validate_dns=False)

    first = await orchestrator.submit(str(parsed_claim.source_url))
    await queue.join()

    second = await asyncio.wait_for(orchestrator.submit(str(parsed_claim.source_url)), timeout=1.0)
    await queue.join()
    await queue.close()

    assert second.job_id == first.job_id
    assert second.cached is True
    assert second.status == JobStatus.COMPLETED
    assert sandbox.calls == 1, "the cached claim must not be re-executed"


async def test_a_queued_job_survives_a_restart_and_is_only_processed_once(
    tmp_path: Path, parsed_claim
) -> None:
    """The asyncio queue is per-process; the durable store is what prevents a rerun."""
    path = tmp_path / "verity.db"
    first_store = SQLiteJobStore(path)
    queue = AsyncioJobQueue()
    orchestrator = Orchestrator(first_store, queue, validate_dns=False)
    response = await orchestrator.submit(str(parsed_claim.source_url))
    first_store.close()  # the process dies before any consumer ran

    reopened = SQLiteJobStore(path)
    recovered = await reopened.get_job(response.job_id)
    assert recovered is not None
    assert recovered.status == JobStatus.QUEUED, "the job is still visible, not lost silently"

    success = EnvironmentResult(
        succeeded=True, exit_code=0, phase="metric", actual_value=90.0, duration_seconds=1.0
    )
    sandbox = ScriptedSandbox([success])
    pipeline = build_pipeline(reopened, parsed_claim, sandbox, ScriptedDebugger())

    # A replayed delivery of the same job id must not start a second benchmark.
    await asyncio.gather(*(pipeline.process(response.job_id) for _ in range(3)))
    assert sandbox.calls == 1
    reopened.close()


@dataclass
class PathTraversingDebugger:
    """Reproduces the real openai/whisper failure.

    The Debug Agent proposed writing `../venv/pip.conf` — outside the cloned repository.
    `PatchOperation` correctly refuses that, raising ValidationError. Before the fix, that
    exception escaped the retry loop and killed the job with no verdict at all, which reads
    as a crash rather than a refusal. The safety boundary was always working; the handling
    around it was not.
    """

    calls: int = 0

    async def run(self, parsed_claim, failure, prior_patches, attempt):
        self.calls += 1
        PatchOperation(kind="write_file", path="../venv/pip.conf", new_text="[global]\n")
        raise AssertionError("unreachable: the path guard must reject this")


async def test_a_patch_escaping_the_repository_is_a_failed_attempt_not_a_crash(
    store, parsed_claim
) -> None:
    sandbox = ScriptedSandbox([failure(0)])
    debugger = PathTraversingDebugger()
    pipeline = build_pipeline(store, parsed_claim, sandbox, debugger)

    await pipeline.process((await store.create_or_get(str(parsed_claim.source_url)))[0].id)

    job = await store.get_job((await store.create_or_get(str(parsed_claim.source_url)))[0].id)
    assert job is not None
    assert job.verdict is not None, "a rejected patch must still produce a verdict"
    assert job.verdict.status == VerdictStatus.COULD_NOT_VERIFY
    assert job.verdict.actual_value is None, "nothing was reproduced, so nothing may be reported"
    assert debugger.calls == 3, "the loop must spend all three attempts, not abort on the first"
    assert len(job.verdict.attempts) == 3

    trace = await store.get_trace(job.id)
    rejected = [event for event in trace if event.action == "attempt_rejected"]
    assert len(rejected) == 3, "each refusal must be recorded in the trace"
    assert "safety contract" in rejected[0].detail["proposal"]["diagnosis"]

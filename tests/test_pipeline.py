from __future__ import annotations

from dataclasses import dataclass, field

from verity.agents.reporter import ReporterAgent
from verity.github import NoopIssuePublisher
from verity.models import (
    DebugProposal,
    EnvironmentResult,
    JobStatus,
    PatchOperation,
    VerdictStatus,
)
from verity.orchestrator import Orchestrator
from verity.pipeline import VerificationPipeline
from verity.store import MemoryJobStore


@dataclass
class FakeParser:
    parsed: object

    async def run(self, url: str):
        return self.parsed


@dataclass
class SequenceEnvironment:
    results: list[EnvironmentResult]
    calls: int = 0

    async def run(self, job_id, parsed_claim, patches, command_override=None):
        result = self.results[self.calls]
        self.calls += 1
        return result


@dataclass
class FakeDebugger:
    calls: int = 0

    async def run(self, parsed_claim, failure, prior_patches, attempt):
        self.calls += 1
        return DebugProposal(
            diagnosis=f"repair attempt {attempt}",
            operations=[
                PatchOperation(
                    kind="write_file",
                    path=f"verity-fix-{attempt}.txt",
                    new_text=f"attempt {attempt}\n",
                )
            ],
        )


def failure(number: int) -> EnvironmentResult:
    return EnvironmentResult(
        succeeded=False,
        exit_code=1,
        phase="evaluate",
        stderr=f"real traceback {number}",
        duration_seconds=0.1,
    )


async def test_honest_failure_is_reported_after_exactly_three_debug_attempts(parsed_claim) -> None:
    store = MemoryJobStore()
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    environment = SequenceEnvironment([failure(0), failure(1), failure(2), failure(3)])
    debugger = FakeDebugger()
    pipeline = VerificationPipeline(
        store=store,
        parser=FakeParser(parsed_claim),
        environment=environment,
        debugger=debugger,
        reporter=ReporterAgent(NoopIssuePublisher()),
    )
    await pipeline.process(job.id)
    finished = await store.get_job(job.id)
    assert finished is not None
    assert finished.status == JobStatus.COMPLETED
    assert finished.verdict is not None
    assert finished.verdict.status == VerdictStatus.COULD_NOT_VERIFY
    assert len(finished.verdict.attempts) == 3
    assert environment.calls == 4  # initial run plus three bounded debug retries
    assert debugger.calls == 3
    trace = await store.get_trace(job.id)
    assert sum(event.action == "attempt_finished" for event in trace) == 3


async def test_success_after_patch_is_reported_without_extra_retries(parsed_claim) -> None:
    store = MemoryJobStore()
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    success = EnvironmentResult(
        succeeded=True,
        exit_code=0,
        phase="metric",
        stdout="accuracy: 90.0",
        actual_value=90.0,
        metric_evidence="accuracy: 90.0",
        duration_seconds=0.2,
    )
    environment = SequenceEnvironment([failure(0), success])
    debugger = FakeDebugger()
    pipeline = VerificationPipeline(
        store=store,
        parser=FakeParser(parsed_claim),
        environment=environment,
        debugger=debugger,
        reporter=ReporterAgent(NoopIssuePublisher()),
    )
    await pipeline.process(job.id)
    finished = await store.get_job(job.id)
    assert finished and finished.verdict
    assert finished.verdict.status == VerdictStatus.VERIFIED
    assert len(finished.verdict.attempts) == 1
    assert environment.calls == 2


@dataclass
class RecordingPublisher:
    published: list[str] = field(default_factory=list)

    async def publish(self, job_id: str, source_url: str) -> None:
        self.published.append(job_id)


async def test_duplicate_submission_returns_completed_cached_job(parsed_claim) -> None:
    store = MemoryJobStore()
    publisher = RecordingPublisher()
    orchestrator = Orchestrator(store, publisher, validate_dns=False)
    first = await orchestrator.submit(str(parsed_claim.source_url))
    await store.complete_job(
        first.job_id,
        await ReporterAgent(NoopIssuePublisher()).run(
            first.job_id,
            parsed_claim,
            EnvironmentResult(
                succeeded=True,
                exit_code=0,
                phase="metric",
                actual_value=90,
                duration_seconds=0,
            ),
            [],
        ),
    )
    second = await orchestrator.submit(str(parsed_claim.source_url))
    assert second.job_id == first.job_id
    assert second.cached is True
    assert publisher.published == [first.job_id]

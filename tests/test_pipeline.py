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

COMMIT_A = "a" * 40
COMMIT_B = "b" * 40


@dataclass
class FakeParser:
    parsed: object

    async def run(self, url: str):
        return self.parsed


@dataclass
class SequenceEnvironment:
    results: list[EnvironmentResult]
    calls: int = 0
    seen_revisions: list[str | None] = field(default_factory=list)

    async def run(self, job_id, parsed_claim, patches, command_override=None):
        self.seen_revisions.append(parsed_claim.execution.revision)
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


@dataclass
class PatchRecordingEnvironment:
    seen_paths: list[list[str]] = field(default_factory=list)
    seen_commands: list[list[str] | None] = field(default_factory=list)

    async def run(self, job_id, parsed_claim, patches, command_override=None):
        self.seen_paths.append([patch.path for patch in patches])
        self.seen_commands.append(command_override)
        if len(self.seen_paths) == 1:
            return failure(0)
        if len(self.seen_paths) == 2:
            return EnvironmentResult(
                succeeded=False,
                exit_code=1,
                phase="install",
                stderr="Patch application failed: expected one match, found zero",
                duration_seconds=0.1,
            )
        return EnvironmentResult(
            succeeded=True,
            exit_code=0,
            phase="metric",
            actual_value=90.0,
            duration_seconds=0.1,
        )


@dataclass
class CommandChangingDebugger:
    calls: int = 0

    async def run(self, parsed_claim, failure, prior_patches, attempt):
        self.calls += 1
        command = ["python", f"attempt-{attempt}.py"] if attempt == 1 else None
        return DebugProposal(
            diagnosis=f"repair attempt {attempt}",
            operations=[
                PatchOperation(
                    kind="write_file",
                    path=f"verity-fix-{attempt}.txt",
                    new_text=f"attempt {attempt}\n",
                )
            ],
            replacement_command=command,
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


async def test_debug_retry_is_pinned_to_the_first_resolved_commit(parsed_claim) -> None:
    store = MemoryJobStore()
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    environment = SequenceEnvironment(
        [
            failure(0).model_copy(update={"repository_commit": COMMIT_A}),
            EnvironmentResult(
                succeeded=True,
                exit_code=0,
                phase="metric",
                actual_value=90.0,
                duration_seconds=0.1,
                repository_commit=COMMIT_A,
            ),
        ]
    )
    pipeline = VerificationPipeline(
        store=store,
        parser=FakeParser(parsed_claim),
        environment=environment,
        debugger=FakeDebugger(),
        reporter=ReporterAgent(NoopIssuePublisher()),
    )

    await pipeline.process(job.id)

    finished = await store.get_job(job.id)
    assert finished is not None and finished.verdict is not None
    assert finished.verdict.status == VerdictStatus.VERIFIED
    assert finished.parsed_claim is not None
    assert finished.parsed_claim.execution.revision == COMMIT_A
    assert environment.seen_revisions == [None, COMMIT_A]
    assert f"Repository commit: {COMMIT_A}" in finished.verdict.evidence


async def test_repository_revision_drift_is_an_infrastructure_failure(parsed_claim) -> None:
    store = MemoryJobStore()
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    debugger = FakeDebugger()
    environment = SequenceEnvironment(
        [
            failure(0).model_copy(update={"repository_commit": COMMIT_A}),
            EnvironmentResult(
                succeeded=True,
                exit_code=0,
                phase="metric",
                actual_value=90.0,
                duration_seconds=0.1,
                repository_commit=COMMIT_B,
            ),
        ]
    )
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
    assert finished.status == JobStatus.FAILED
    assert finished.verdict is None
    assert COMMIT_A in (finished.error or "")
    assert COMMIT_B in (finished.error or "")
    assert environment.seen_revisions == [None, COMMIT_A]
    assert debugger.calls == 1


async def test_pinned_revision_clone_failure_is_an_infrastructure_failure(parsed_claim) -> None:
    store = MemoryJobStore()
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    debugger = FakeDebugger()
    parsed = parsed_claim.model_copy(deep=True)
    parsed.execution.revision = COMMIT_A
    environment = SequenceEnvironment(
        [
            EnvironmentResult(
                succeeded=False,
                exit_code=128,
                phase="clone",
                stderr="fatal: remote error: upload-pack: not our ref",
                duration_seconds=0.1,
            )
        ]
    )
    pipeline = VerificationPipeline(
        store=store,
        parser=FakeParser(parsed),
        environment=environment,
        debugger=debugger,
        reporter=ReporterAgent(NoopIssuePublisher()),
    )

    await pipeline.process(job.id)

    finished = await store.get_job(job.id)
    assert finished is not None
    assert finished.status == JobStatus.FAILED
    assert finished.verdict is None
    assert COMMIT_A in (finished.error or "")
    assert "observed missing" in (finished.error or "")
    assert debugger.calls == 0


async def test_unapplied_patch_bundle_cannot_poison_the_next_attempt(parsed_claim) -> None:
    store = MemoryJobStore()
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    environment = PatchRecordingEnvironment()
    pipeline = VerificationPipeline(
        store=store,
        parser=FakeParser(parsed_claim),
        environment=environment,
        debugger=CommandChangingDebugger(),
        reporter=ReporterAgent(NoopIssuePublisher()),
    )
    await pipeline.process(job.id)

    finished = await store.get_job(job.id)
    assert finished is not None and finished.verdict is not None
    assert finished.status == JobStatus.COMPLETED
    assert finished.verdict.status == VerdictStatus.VERIFIED
    assert environment.seen_paths == [[], ["verity-fix-1.txt"], ["verity-fix-2.txt"]]
    assert environment.seen_commands == [None, ["python", "attempt-1.py"], None]
    assert finished.verdict.fixes_applied == ["write_file verity-fix-2.txt"]


async def test_initial_infrastructure_failure_is_not_sent_to_the_debugger(parsed_claim) -> None:
    store = MemoryJobStore()
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    environment = SequenceEnvironment(
        [
            EnvironmentResult(
                succeeded=False,
                phase="infrastructure",
                stderr="Cloud Run operation timed out",
                duration_seconds=1.0,
            )
        ]
    )
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
    assert finished.status == JobStatus.FAILED
    assert finished.verdict is None
    assert "infrastructure failure" in (finished.error or "").lower()
    assert environment.calls == 1
    assert debugger.calls == 0


async def test_infrastructure_failure_during_retry_stops_the_loop(parsed_claim) -> None:
    store = MemoryJobStore()
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    environment = SequenceEnvironment(
        [
            failure(0),
            EnvironmentResult(
                succeeded=False,
                phase="infrastructure",
                stderr="Cloud Run execution disappeared",
                duration_seconds=1.0,
            ),
        ]
    )
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
    assert finished is not None and finished.status == JobStatus.FAILED
    assert finished.verdict is None
    assert environment.calls == 2
    assert debugger.calls == 1


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

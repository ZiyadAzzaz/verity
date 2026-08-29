from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from google.cloud import run_v2

from verity.agents.environment import CloudRunJobBackend
from verity.cloud_handoff import decode_request_args
from verity.models import EnvironmentResult
from verity.store import MemoryJobStore


class RecordingMemoryStore(MemoryJobStore):
    def __init__(self) -> None:
        super().__init__()
        self.completed_results: list[EnvironmentResult] = []

    async def complete_sandbox_run(self, run_id: str, result: EnvironmentResult) -> None:
        self.completed_results.append(result)
        await super().complete_sandbox_run(run_id, result)


async def test_cloud_run_control_plane_failure_becomes_an_environment_result(
    monkeypatch, parsed_claim
) -> None:
    class BrokenJobsClient:
        def job_path(self, project: str, location: str, job_name: str) -> str:
            return f"projects/{project}/locations/{location}/jobs/{job_name}"

        def run_job(self, *, request):
            raise RuntimeError("control plane unavailable")

    monkeypatch.setattr(run_v2, "JobsClient", BrokenJobsClient)
    store = RecordingMemoryStore()
    backend = CloudRunJobBackend(
        project="test-project",
        location="us-central1",
        job_name="verity-sandbox",
        store=store,
        timeout_seconds=30,
    )

    result = await backend.run("job-1", parsed_claim, [], None)

    assert result.succeeded is False
    assert result.phase == "infrastructure"
    assert "control plane unavailable" in result.stderr
    assert store.completed_results == [result]


async def test_cloud_handoff_uses_only_bounded_args_and_platform_logs(
    monkeypatch, parsed_claim
) -> None:
    document = parsed_claim.model_dump(mode="json")
    document["source_url"] = "https://example.com/paper?temporary_token=must-not-cross"
    document["execution"]["repository_url"] = (
        "https://github.com/example/project?token=must-not-cross"
    )
    parsed_claim = type(parsed_claim).model_validate(document)
    recorded: list[run_v2.RunJobRequest] = []
    execution_name = (
        "projects/test-project/locations/us-central1/jobs/verity-sandbox/"
        "executions/verity-sandbox-abc"
    )

    class CompletedOperation:
        def result(self, *, timeout: int):
            assert timeout == 150
            return SimpleNamespace(name=execution_name)

    class RecordingJobsClient:
        def job_path(self, project: str, location: str, job_name: str) -> str:
            return f"projects/{project}/locations/{location}/jobs/{job_name}"

        def run_job(self, *, request):
            recorded.append(request)
            return CompletedOperation()

    expected = EnvironmentResult(
        succeeded=True,
        exit_code=0,
        phase="metric",
        actual_value=91.2,
        duration_seconds=3,
        repository_commit="a" * 40,
    )

    class RecordingResultReader:
        def read(self, *, execution_name: str, run_id: str, timeout_seconds: float):
            assert execution_name.endswith("verity-sandbox-abc")
            assert len(run_id) == 32
            # The execution timeout plus the log-propagation margin. Nothing waits for the
            # execution to finish before this read starts, so a budget of the margin alone
            # would expire while the sandbox was still running.
            assert timeout_seconds == 30 + 7
            return expected

    monkeypatch.setattr(run_v2, "JobsClient", RecordingJobsClient)
    store = RecordingMemoryStore()
    backend = CloudRunJobBackend(
        project="test-project",
        location="us-central1",
        job_name="verity-sandbox",
        store=store,
        timeout_seconds=30,
        result_reader=RecordingResultReader(),
        result_log_timeout_seconds=7,
    )

    result = await backend.run("job-1", parsed_claim, [], None)

    assert result.succeeded is True
    assert result.actual_value == 91.2
    assert result.sandbox_execution == execution_name
    assert store.completed_results == [result]
    override = recorded[0].overrides.container_overrides[0]
    assert list(override.env) == []
    decoded = decode_request_args(list(override.args))
    assert decoded.job_id == "job-1"
    assert str(decoded.parsed_claim.source_url) == "https://example.com/paper"
    assert str(decoded.parsed_claim.execution.repository_url) == (
        "https://github.com/example/project.git"
    )
    assert "must-not-cross" not in " ".join(override.args)


def test_minimal_sandbox_entrypoint_has_no_cloud_data_client() -> None:
    source = Path("verity/sandbox_runner.py").read_text(encoding="utf-8")
    assert "get_settings" not in source
    assert "build_store" not in source
    assert "FirestoreJobStore" not in source
    assert "google.cloud" not in source
    assert "decode_request_args" in source
    assert "encode_result_line" in source


async def test_execution_name_comes_from_metadata_without_reading_the_operation_back(
    monkeypatch, parsed_claim
) -> None:
    """The pipeline may start a sandbox job but not read the Cloud Run API back.

    ``roles/run.jobsExecutorWithOverrides`` grants ``run.jobs.run`` and no read permission, so
    awaiting the operation raises ``PermissionDenied`` in production.  Cloud Run already returns
    the execution as the operation's metadata, so the name is taken from there and the read-back
    never happens.  This test fails loudly if that regresses, because the failure it guards
    against only appears once a claim actually reaches execution.
    """
    execution_name = (
        "projects/test-project/locations/us-central1/jobs/verity-sandbox/"
        "executions/verity-sandbox-frommeta"
    )

    class ForbiddenReadBackOperation:
        def __init__(self) -> None:
            self.metadata = SimpleNamespace(name=execution_name)

        def result(self, *, timeout: int):
            raise AssertionError(
                "operation.result() calls run.operations.get, which the pipeline service "
                "account is deliberately not granted"
            )

    class RecordingJobsClient:
        def job_path(self, project: str, location: str, job_name: str) -> str:
            return f"projects/{project}/locations/{location}/jobs/{job_name}"

        def run_job(self, *, request):
            return ForbiddenReadBackOperation()

    expected = EnvironmentResult(
        succeeded=True, exit_code=0, phase="metric", actual_value=1.0, duration_seconds=2
    )

    class RecordingResultReader:
        def read(self, *, execution_name: str, run_id: str, timeout_seconds: float):
            assert execution_name.endswith("verity-sandbox-frommeta")
            # Taking the name from metadata means nothing waits for the execution to finish, so
            # this reader is now the only thing bounding the wait. A budget that does not
            # outlast the execution itself fails every claim that takes longer than the log
            # margin - which live BERT verification did, twice, before this was asserted.
            assert timeout_seconds > 30
            return expected

    monkeypatch.setattr(run_v2, "JobsClient", RecordingJobsClient)
    store = RecordingMemoryStore()
    backend = CloudRunJobBackend(
        project="test-project",
        location="us-central1",
        job_name="verity-sandbox",
        store=store,
        timeout_seconds=30,
        result_reader=RecordingResultReader(),
    )

    result = await backend.run("job-1", parsed_claim, [], None)

    assert result.succeeded is True
    assert result.sandbox_execution == execution_name

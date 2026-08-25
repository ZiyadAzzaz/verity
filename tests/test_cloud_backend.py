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
            assert timeout_seconds == 7
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

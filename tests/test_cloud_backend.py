from __future__ import annotations

from pathlib import Path

from google.cloud import run_v2

from verity.agents.environment import CloudRunJobBackend
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


def test_minimal_sandbox_entrypoint_does_not_load_application_settings() -> None:
    source = Path("verity/sandbox_runner.py").read_text(encoding="utf-8")
    assert "get_settings" not in source
    assert "build_store" not in source
    assert "FirestoreJobStore" in source

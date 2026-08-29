"""The HTTP surface running on the local profile."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from verity.config import Settings
from verity.container import build_container
from verity.interfaces import SandboxUnavailableError

warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette.testclient")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from fastapi.testclient import TestClient

    from verity.api import create_app

    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-secret")
    settings = Settings(env="local", sqlite_path=str(tmp_path / "verity.db"), _env_file=None)  # type: ignore[call-arg]
    container = build_container(settings)

    async def unreachable_daemon() -> None:
        raise SandboxUnavailableError("The Docker daemon is not reachable.")

    monkeypatch.setattr(container.sandbox, "preflight", unreachable_daemon)
    with TestClient(create_app(settings=settings, container=container)) as test_client:
        yield test_client


def test_health_reports_the_active_profile(client) -> None:
    body = client.get("/health").json()
    assert body["profile"] == "local"
    assert body["store"] == "sqlite"
    assert body["queue"] == "asyncio"
    assert body["sandbox"] == "docker"


def test_a_stopped_docker_daemon_is_reported_as_a_setup_problem(client) -> None:
    """Degraded, not silently healthy — and never a fallback to running code on the host."""
    body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert "Docker daemon is not reachable" in body["setup_error"]


@pytest.mark.parametrize(
    "url,detail",
    [
        ("http://example.com/paper", "only HTTPS"),
        ("https://user:pass@example.com/paper", "credentials"),
    ],
)
def test_unsafe_urls_are_rejected_at_intake(client, url: str, detail: str) -> None:
    response = client.post("/api/jobs", json={"url": url})
    assert response.status_code == 400
    assert detail in response.json()["detail"]


def test_unknown_job_is_a_404(client) -> None:
    assert client.get("/api/jobs/does-not-exist").status_code == 404

from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from verity.api import create_app
from verity.config import Settings
from verity.messaging import PubSubJobQueue, decode_push_envelope


def test_decode_pubsub_envelope() -> None:
    data = base64.b64encode(json.dumps({"job_id": "abc", "source_url": "x"}).encode()).decode()
    assert decode_push_envelope({"message": {"data": data, "messageId": "m1"}}) == ("abc", "m1")


def test_decode_pubsub_rejects_invalid_data() -> None:
    with pytest.raises(ValueError, match="base64"):
        decode_push_envelope({"message": {"data": "%%%"}})


async def test_pubsub_publisher_uses_bounded_timeout_and_stops(monkeypatch) -> None:
    from google.cloud import pubsub_v1

    observed: dict[str, object] = {}

    class _Future:
        def result(self, *, timeout: float) -> str:
            observed["timeout"] = timeout
            return "message-1"

    class _Publisher:
        def topic_path(self, project: str, topic: str) -> str:
            return f"projects/{project}/topics/{topic}"

        def publish(self, topic: str, data: bytes, **attributes: str) -> _Future:
            observed.update(topic=topic, data=data, attributes=attributes)
            return _Future()

        def stop(self) -> None:
            observed["stop_count"] = int(observed.get("stop_count", 0)) + 1

    monkeypatch.setattr(pubsub_v1, "PublisherClient", _Publisher)
    queue = PubSubJobQueue("project", "jobs", publish_timeout_seconds=7)

    await queue.publish("job-1", "https://example.com/claim")
    await queue.close()
    await queue.close()

    assert observed["timeout"] == 7
    assert observed["topic"] == "projects/project/topics/jobs"
    assert json.loads(observed["data"]) == {
        "job_id": "job-1",
        "source_url": "https://example.com/claim",
    }
    assert observed["attributes"] == {
        "job_id": "job-1",
        "content_type": "application/json",
    }
    assert observed["stop_count"] == 1
    with pytest.raises(RuntimeError, match="publisher is closed"):
        await queue.publish("job-2", "https://example.com/other")


def test_pubsub_publisher_rejects_unbounded_timeout() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        PubSubJobQueue("project", "jobs", publish_timeout_seconds=0)


class _FakeContainer:
    def __init__(self) -> None:
        self.launched: list[str] = []
        self.launcher = SimpleNamespace(launch=self._launch)

    async def _launch(self, job_id: str) -> None:
        self.launched.append(job_id)

    async def preflight(self) -> None:
        return None

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None


def _push_envelope(job_id: str = "job-123") -> dict[str, object]:
    data = base64.b64encode(json.dumps({"job_id": job_id}).encode()).decode()
    return {"message": {"data": data, "messageId": "message-1"}}


def test_pubsub_route_verifies_oidc_before_launching(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        environment="development",
        pubsub_oidc_audience="https://verity.internal/pubsub/project",
        pubsub_service_account="verity-pubsub@project.iam.gserviceaccount.com",
    )
    container = _FakeContainer()
    verified: list[tuple[str | None, str, str]] = []

    def verify(authorization, *, audience, service_account_email):
        verified.append((authorization, audience, service_account_email))
        if authorization is None:
            raise ValueError("missing Pub/Sub OIDC bearer token")
        return {"email": service_account_email}

    monkeypatch.setattr("verity.api.verify_pubsub_oidc", verify)
    with TestClient(create_app(settings=settings, container=container)) as client:  # type: ignore[arg-type]
        rejected = client.post("/internal/pubsub", json=_push_envelope())
        accepted = client.post(
            "/internal/pubsub",
            headers={"Authorization": "Bearer signed-google-token"},
            json=_push_envelope(),
        )

    assert rejected.status_code == 401
    assert accepted.status_code == 204
    assert container.launched == ["job-123"]
    assert verified[-1] == (
        "Bearer signed-google-token",
        "https://verity.internal/pubsub/project",
        "verity-pubsub@project.iam.gserviceaccount.com",
    )


def test_pubsub_oidc_probe_verifies_without_launching(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        pubsub_oidc_audience="https://verity.internal/pubsub/project",
        pubsub_service_account="verity-pubsub@verity-prod.iam.gserviceaccount.com",
    )
    container = _FakeContainer()
    observed: list[str | None] = []

    def verify(authorization, *, audience, service_account_email):
        observed.append(authorization)
        assert audience == "https://verity.internal/pubsub/project"
        assert service_account_email == "verity-pubsub@verity-prod.iam.gserviceaccount.com"

    monkeypatch.setattr("verity.api.verify_pubsub_oidc", verify)
    with TestClient(create_app(settings=settings, container=container)) as client:  # type: ignore[arg-type]
        response = client.post(
            "/internal/pubsub/oidc-probe", headers={"Authorization": "Bearer signed-token"}
        )

    assert response.status_code == 204
    assert observed == ["Bearer signed-token"]
    assert container.launched == []

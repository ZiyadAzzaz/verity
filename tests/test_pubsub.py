from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from verity.api import create_app
from verity.config import Settings
from verity.messaging import decode_push_envelope


def test_decode_pubsub_envelope() -> None:
    data = base64.b64encode(json.dumps({"job_id": "abc", "source_url": "x"}).encode()).decode()
    assert decode_push_envelope({"message": {"data": data, "messageId": "m1"}}) == ("abc", "m1")


def test_decode_pubsub_rejects_invalid_data() -> None:
    with pytest.raises(ValueError, match="base64"):
        decode_push_envelope({"message": {"data": "%%%"}})


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

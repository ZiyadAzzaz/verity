"""Production configuration must refuse anything that weakens the isolation boundary.

`host_subprocess` runs untrusted third-party code directly on the host with no container
around it. It exists only as the body of the Cloud Run sandbox job, where the Cloud Run
container *is* the boundary. Nothing should be able to select it in production, and that
guarantee is enforced here rather than left to documentation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from verity.config import Settings

PRODUCTION = {
    "environment": "production",
    "env": "cloud",
    "google_cloud_project": "verity-prod",
    "api_key": "x" * 24,
    "pubsub_verification_token": "independent-random-token",
    "github_token": "ghs-not-a-real-token",
    "report_repo": "owner/verity-reports",
}


def build(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**PRODUCTION, **overrides})  # type: ignore[arg-type]


def test_a_complete_production_configuration_is_accepted() -> None:
    """The control: everything below must fail for a specific reason, not incidentally."""
    settings = build()
    assert settings.environment == "production"
    assert settings.sandbox == "cloud_run"


def test_production_rejects_the_host_subprocess_sandbox() -> None:
    """The one that matters: untrusted code must never run unsandboxed in production."""
    with pytest.raises(ValidationError, match="cloud_run sandbox backend"):
        build(sandbox_backend="host_subprocess")


def test_production_rejects_the_docker_sandbox_too() -> None:
    """Docker is the local boundary; production schedules Cloud Run Jobs instead."""
    with pytest.raises(ValidationError, match="cloud_run sandbox backend"):
        build(sandbox_backend="docker")


def test_production_rejects_the_local_profile_wholesale() -> None:
    """VERITY_ENV=local implies sqlite + asyncio + docker + ai_studio; none are production."""
    with pytest.raises(ValidationError) as caught:
        build(env="local")
    message = str(caught.value)
    for required in ("VERITY_ENV=cloud", "firestore", "pubsub", "cloud_run"):
        assert required in message


@pytest.mark.parametrize(
    "override,expected",
    [
        ({"store_backend": "memory"}, "firestore store backend"),
        ({"store_backend": "sqlite"}, "firestore store backend"),
        ({"message_backend": "asyncio"}, "pubsub message backend"),
        ({"google_cloud_project": None}, "GOOGLE_CLOUD_PROJECT"),
        ({"api_key": "too-short"}, "at least 24 characters"),
        ({"pubsub_verification_token": None}, "VERITY_PUBSUB_VERIFICATION_TOKEN"),
        ({"github_token": None}, "VERITY_GITHUB_TOKEN"),
        ({"report_repo": None}, "VERITY_REPORT_REPO"),
    ],
)
def test_production_requires_each_piece(override: dict[str, object], expected: str) -> None:
    with pytest.raises(ValidationError, match=expected):
        build(**override)


def test_development_may_still_select_host_subprocess() -> None:
    """The escape hatch stays usable for debugging Verity itself, outside production."""
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        environment="development",
        env="local",
        sandbox_backend="host_subprocess",
    )
    assert settings.sandbox == "host_subprocess"

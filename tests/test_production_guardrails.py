"""Production configuration must refuse anything that weakens the isolation boundary.

`host_subprocess` runs untrusted third-party code directly on the host with no container
around it. The current Cloud Run job also exposes outbound networking and a service-account
identity to that code. Nothing should be able to select either boundary in production until
the cloud handoff is credential-free, and that guarantee is enforced here rather than left
to documentation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from verity.config import Settings

PRODUCTION = {
    "environment": "production",
    "env": "cloud",
    "google_cloud_project": "verity-prod",
    "api_key": "x" * 24,
    "pubsub_oidc_audience": "https://verity.internal/pubsub/verity-prod",
    "pubsub_service_account": "verity-pubsub@verity-prod.iam.gserviceaccount.com",
    "github_token": "ghs-not-a-real-token",
    "report_repo": "owner/verity-reports",
}


def build(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**PRODUCTION, **overrides})  # type: ignore[arg-type]


def test_cloud_production_is_fail_closed_until_the_sandbox_is_credential_free() -> None:
    with pytest.raises(ValidationError, match="production Cloud Run sandbox is disabled"):
        build()


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
        ({"pubsub_oidc_audience": None}, "VERITY_PUBSUB_OIDC_AUDIENCE"),
        ({"pubsub_service_account": None}, "VERITY_PUBSUB_SERVICE_ACCOUNT"),
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


@pytest.mark.parametrize(
    "email",
    [
        "short@verity-prod.iam.gserviceaccount.com",
        "ends-with-@verity-prod.iam.gserviceaccount.com",
        "Uppercase@verity-prod.iam.gserviceaccount.com",
    ],
)
def test_pubsub_identity_requires_a_valid_custom_service_account_email(email: str) -> None:
    with pytest.raises(ValidationError, match="pubsub_service_account"):
        Settings(_env_file=None, pubsub_service_account=email)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "override",
    [
        {"google_cloud_project": "bad/project"},
        {"google_cloud_location": "https://attacker.example"},
        {"cloud_run_sandbox_job": 'job" OR true'},
        {"cloud_run_pipeline_job": "Uppercase"},
    ],
)
def test_cloud_resource_components_reject_filter_or_path_injection(
    override: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **override)  # type: ignore[arg-type]


def test_production_pubsub_identity_must_belong_to_the_configured_project() -> None:
    with pytest.raises(ValidationError, match="must belong to GOOGLE_CLOUD_PROJECT"):
        build(pubsub_service_account="verity-pubsub@other-project.iam.gserviceaccount.com")


def test_deployment_script_stops_before_the_first_gcloud_mutation() -> None:
    script = Path("scripts/deploy.ps1").read_text(encoding="utf-8")
    guard = script.index("Cloud deployment is paused at the final live-security gate")
    first_mutation = script.index("Invoke-Checked gcloud config set project")
    assert guard < first_mutation


def test_deployment_blueprint_enforces_the_scoped_cloud_boundary() -> None:
    script = Path("scripts/deploy.ps1").read_text(encoding="utf-8")
    sandbox_deploy = script.index("run jobs deploy verity-sandbox")
    identity_gate = script.index("'scripts/validate_cloud_sandbox_identity.py'")
    app_deploy = script.index("agents-cli deploy")

    assert "roles/datastore.user" in script  # app role and explicit legacy removal
    assert "sandboxRoles.Count -gt 0" in script
    assert "asset search-all-iam-policies" in script
    assert "zero resource-level IAM bindings" in script
    assert "--clear-env-vars" in script
    assert "--clear-secrets" in script
    assert "--clear-volumes" in script
    assert "--clear-network" in script
    assert "roles/run.jobsExecutorWithOverrides" in script
    assert "image_summary.fully_qualified_digest" in script
    assert "@sha256:[0-9a-f]{64}$" in script
    assert sandbox_deploy < identity_gate < app_deploy
    assert "VERITY_PUBSUB_VERIFICATION_TOKEN" not in script
    assert "?token=" not in script
    assert "Invoke-VerityPython" in script
    assert "billing budgets" not in script
    assert "BudgetUsd" not in script


def test_minimal_sandbox_image_has_no_google_cloud_client() -> None:
    requirements = Path("requirements-sandbox.txt").read_text(encoding="utf-8")
    assert "google-cloud" not in requirements
    assert "google-auth" not in requirements


@pytest.mark.parametrize("ignore_file", [".dockerignore", ".gcloudignore"])
def test_build_context_excludes_local_secrets_and_state(ignore_file: str) -> None:
    exclusions = Path(ignore_file).read_text(encoding="utf-8").splitlines()

    for required in (".env", ".verity-data", ".git", "*.db", "*.pem", "*.key"):
        assert required in exclusions


def test_sandbox_only_proof_cannot_deploy_the_privileged_application() -> None:
    script = Path("scripts/deploy_sandbox_probe.ps1").read_text(encoding="utf-8")
    build = Path("cloudbuild.sandbox-probe.yaml").read_text(encoding="utf-8")

    assert "git status '--porcelain'" in script
    assert "zero direct project roles" in script
    assert "asset search-all-iam-policies" in script
    assert "zero resource-level IAM bindings" in script
    assert "--clear-env-vars" in script
    assert "--clear-secrets" in script
    assert "--clear-volumes" in script
    assert "--clear-network" in script
    assert "validate_cloud_sandbox_identity.py" in script
    assert "'--image', $sandboxImage" in script
    assert "image_summary.fully_qualified_digest" in script
    assert "@sha256:[0-9a-f]{64}$" in script
    assert "agents-cli" not in script
    assert "run services deploy" not in script
    assert "Invoke-VerityPython" in script
    assert "billing budgets" not in script
    assert '$ErrorActionPreference = "SilentlyContinue"' in script
    assert "$previousErrorActionPreference" in script
    assert "verity-api" not in build
    assert "Dockerfile.sandbox" in build

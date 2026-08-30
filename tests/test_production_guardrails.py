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


def test_complete_secure_cloud_production_configuration_is_accepted() -> None:
    settings = build()
    assert settings.store == "firestore"
    assert settings.messaging == "pubsub"
    assert settings.sandbox == "cloud_run"
    assert settings.llm == "vertex"


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
        {"google_cloud_vertex_location": "https://attacker.example"},
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


def test_deployment_transition_is_bound_to_the_passing_live_proof() -> None:
    script = Path("scripts/deploy.ps1").read_text(encoding="utf-8")
    proof = Path("docs/CLOUD-SANDBOX-LIVE-PROOF-2026-08-27.md").read_text(encoding="utf-8")
    assert "verity-sandbox-rcxvn" in script
    assert '"passed": true' in proof
    for check in (
        "cloud_run_execute",
        "cloud_storage_list",
        "firestore_write",
        "pubsub_publish",
        "secret_manager_read",
        "vertex_ai_list",
    ):
        assert f'"{check}": 403' in proof


def test_deployment_blueprint_enforces_the_scoped_cloud_boundary() -> None:
    script = Path("scripts/deploy.ps1").read_text(encoding="utf-8")
    sandbox_deploy = script.index("run jobs deploy verity-sandbox")
    identity_gate = script.index("'scripts.validate_cloud_sandbox_identity'")
    app_deploy = script.index("Invoke-AgentsCliIsolated deploy")

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
    assert "GetTempPath" in script
    assert "Invoke-AgentsCliIsolated" in script
    assert "AGENT_VERSION=$sourceRevision" in script
    assert "GOOGLE_CLOUD_VERTEX_LOCATION=global" in script


def test_private_deploy_cannot_make_the_service_public() -> None:
    private_script = Path("scripts/deploy.ps1").read_text(encoding="utf-8")
    public_script = Path("scripts/publish_production.ps1").read_text(encoding="utf-8")
    assert "--member=allUsers" not in private_script
    assert "--member=allUsers" in public_script
    assert "OwnerApprovedPhase8" in public_script
    assert "get-iam-policy" in public_script


def test_deployment_preserves_the_independent_judge_credential() -> None:
    script = Path("scripts/deploy.ps1").read_text(encoding="utf-8")
    assert "'VERITY_JUDGE_TEST_KEY'" in script
    assert "VERITY_JUDGE_TEST_KEY must differ from VERITY_API_KEY" in script
    assert "Test-Native gcloud secrets describe 'verity-judge-test-key'" in script
    assert "VERITY_JUDGE_TEST_KEY=verity-judge-test-key:latest" in script
    assert "Preserve a separately provisioned judge credential without reading" in script


def test_api_image_installs_project_metadata_and_console_scripts() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    install = dockerfile.index("RUN python -m pip install --no-cache-dir --no-deps .")
    copy_project = dockerfile.index("COPY pyproject.toml README.md agents-cli-manifest.yaml ./")
    user = dockerfile.index("USER 10001")
    assert copy_project < install < user


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
    assert "scripts.validate_cloud_sandbox_identity" in script
    assert "scripts/validate_cloud_sandbox_identity.py" not in script
    assert "'--image', $sandboxImage" in script
    assert "image_summary.fully_qualified_digest" in script
    assert "@sha256:[0-9a-f]{64}$" in script
    assert "agents-cli" not in script
    assert "run services deploy" not in script
    assert "Test-Native gcloud run jobs describe verity-sandbox" in script
    assert "Invoke-VerityPython" in script
    assert "billing budgets" not in script
    assert '$ErrorActionPreference = "SilentlyContinue"' in script
    assert "$previousErrorActionPreference" in script
    assert "verity-api" not in build
    assert "Dockerfile.sandbox" in build
    assert "pool:" not in build
    assert "workerPool" not in build

"""Environment-driven configuration.

Two orthogonal settings decide everything:

``VERITY_ENV`` — **which infrastructure Verity runs on**. ``local`` selects SQLite, an
in-process asyncio queue, Docker, and a Google AI Studio API key: no billing account, no
GCP project, no card. ``cloud`` selects Firestore, Pub/Sub, Cloud Run, and Vertex AI. This
is the single swap point; nothing else in the codebase branches on it.

``VERITY_ENVIRONMENT`` — **how strict Verity is about itself**: ``development``, ``test``,
or ``production``. Production requires ``VERITY_ENV=cloud`` and complete authentication.
The Cloud Run profile is enabled only after its no-role execution boundary passed live proof.

Individual backends can still be overridden one at a time (``VERITY_STORE_BACKEND`` and
friends); an unset override means "whatever ``VERITY_ENV`` implies".
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

StoreBackend = Literal["memory", "sqlite", "firestore"]
MessageBackend = Literal["asyncio", "pubsub"]
SandboxBackendName = Literal["docker", "host_subprocess", "cloud_run"]
LLMBackend = Literal["ai_studio", "vertex"]

#: The one place the local/cloud swap is defined.
PROFILES: dict[str, tuple[StoreBackend, MessageBackend, SandboxBackendName, LLMBackend]] = {
    "local": ("sqlite", "asyncio", "docker", "ai_studio"),
    "cloud": ("firestore", "pubsub", "cloud_run", "vertex"),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="VERITY_",
        extra="ignore",
        protected_namespaces=(),
    )

    env: Literal["local", "cloud"] = "local"
    environment: Literal["development", "test", "production"] = "development"
    gemini_model: str = "gemini-3.5-flash"

    # Leave unset to inherit the profile selected by `env`.
    store_backend: StoreBackend | None = None
    message_backend: MessageBackend | None = None
    sandbox_backend: SandboxBackendName | None = None
    llm_backend: LLMBackend | None = None

    # --- local adapters ------------------------------------------------------
    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    sqlite_path: str = "verity.db"
    sandbox_image: str = "verity-sandbox-runner:1"
    sandbox_auto_build: bool = True
    sandbox_memory: str = "4g"
    sandbox_cpus: str = "2"
    queue_concurrency: int = Field(default=1, ge=1, le=8)

    # --- cloud adapters ------------------------------------------------------
    google_cloud_project: str | None = Field(
        default=None,
        validation_alias="GOOGLE_CLOUD_PROJECT",
        pattern=r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$",
    )
    google_cloud_location: str = Field(
        default="us-central1",
        validation_alias="GOOGLE_CLOUD_LOCATION",
        pattern=r"^[a-z]+-[a-z0-9]+[0-9]$",
    )
    pubsub_topic: str = "verification-jobs"
    cloud_run_sandbox_job: str = Field(
        default="verity-sandbox", pattern=r"^[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$"
    )
    cloud_run_pipeline_job: str = Field(
        default="verity-pipeline", pattern=r"^[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$"
    )

    api_key: SecretStr | None = None
    pubsub_oidc_audience: str | None = Field(default=None, pattern=r"^https://[^\s]+$")
    pubsub_service_account: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com$",
    )
    github_token: SecretStr | None = None
    report_repo: str | None = None

    max_debug_attempts: int = Field(default=3, ge=3, le=3)
    execution_timeout_seconds: int = Field(default=900, ge=30, le=3600)
    source_timeout_seconds: float = Field(default=30, ge=5, le=120)
    max_source_bytes: int = Field(default=25_000_000, ge=100_000, le=50_000_000)
    max_output_chars: int = Field(default=100_000, ge=10_000, le=500_000)
    allowed_repo_hosts: tuple[str, ...] = ("github.com",)

    # --- derived -------------------------------------------------------------

    @property
    def store(self) -> StoreBackend:
        return self.store_backend or PROFILES[self.env][0]

    @property
    def messaging(self) -> MessageBackend:
        return self.message_backend or PROFILES[self.env][1]

    @property
    def sandbox(self) -> SandboxBackendName:
        return self.sandbox_backend or PROFILES[self.env][2]

    @property
    def llm(self) -> LLMBackend:
        return self.llm_backend or PROFILES[self.env][3]

    @model_validator(mode="after")
    def validate_production(self) -> Settings:
        if self.environment != "production":
            return self
        errors: list[str] = []
        if self.env != "cloud":
            errors.append("production requires VERITY_ENV=cloud")
        if self.store != "firestore":
            errors.append("production requires the firestore store backend")
        if self.messaging != "pubsub":
            errors.append("production requires the pubsub message backend")
        if self.sandbox != "cloud_run":
            errors.append("production requires the cloud_run sandbox backend")
        if not self.google_cloud_project:
            errors.append("GOOGLE_CLOUD_PROJECT is required")
        if not self.api_key or len(self.api_key.get_secret_value()) < 24:
            errors.append("VERITY_API_KEY must contain at least 24 characters")
        if not self.pubsub_oidc_audience:
            errors.append("VERITY_PUBSUB_OIDC_AUDIENCE is required")
        if not self.pubsub_service_account:
            errors.append("VERITY_PUBSUB_SERVICE_ACCOUNT is required")
        elif self.google_cloud_project and not self.pubsub_service_account.endswith(
            f"@{self.google_cloud_project}.iam.gserviceaccount.com"
        ):
            errors.append("VERITY_PUBSUB_SERVICE_ACCOUNT must belong to GOOGLE_CLOUD_PROJECT")
        if not self.github_token:
            errors.append("VERITY_GITHUB_TOKEN is required")
        if not self.report_repo:
            errors.append("VERITY_REPORT_REPO is required")
        if errors:
            raise ValueError("; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

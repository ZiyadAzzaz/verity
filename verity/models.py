"""Typed contracts shared by every Verity agent and persistence adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


def _gemini_response_schema(schema: dict[str, Any]) -> None:
    """Make a strict model's JSON Schema acceptable to Gemini's ``response_schema``.

    ``extra="forbid"`` makes Pydantic emit ``additionalProperties: false``. The Gemini
    REST API rejects that key outright with
    ``400 INVALID_ARGUMENT: Unknown name "additional_properties"``, so it is stripped from
    the *emitted* schema only. Runtime validation is untouched: a model response carrying
    an unexpected field is still rejected when it is parsed back into these types, which
    is the guarantee that matters.

    Only the boolean form is removed. ``dict[str, str]`` fields legitimately emit
    ``additionalProperties: {"type": "string"}`` to describe a map, and dropping that
    would change what the schema means.
    """
    if schema.get("additionalProperties") is False:
        del schema["additionalProperties"]


#: Strict at runtime, wire-compatible with Gemini structured output.
STRICT = ConfigDict(extra="forbid", json_schema_extra=_gemini_response_schema)


def utc_now() -> datetime:
    return datetime.now(UTC)


class SourceType(StrEnum):
    ARXIV = "arxiv"
    GITHUB = "github"
    VENDOR = "vendor"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PARSING = "parsing"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    DEBUGGING = "debugging"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class VerdictStatus(StrEnum):
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"
    COULD_NOT_VERIFY = "could_not_verify"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Claim(BaseModel):
    """The required claim object extracted by the Parser Agent."""

    model_config = STRICT

    metric: str = Field(min_length=1, max_length=200)
    value: float
    unit: str = Field(default="", max_length=40)
    dataset: str = Field(min_length=1, max_length=300)
    conditions: list[str] = Field(default_factory=list, max_length=30)
    source_location: str = Field(min_length=1, max_length=500)

    @field_validator("metric", "dataset", "source_location", "unit")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("conditions")
    @classmethod
    def normalize_conditions(cls, values: list[str]) -> list[str]:
        return [" ".join(value.split()) for value in values if value.strip()]


class ExecutionPlan(BaseModel):
    model_config = STRICT

    repository_url: HttpUrl | None = None
    revision: str | None = Field(default=None, max_length=100)
    working_directory: str = Field(default=".", max_length=300)
    install_commands: list[list[str]] = Field(default_factory=list, max_length=8)
    evaluation_command: list[str] = Field(default_factory=list, max_length=50)
    result_pattern: str | None = Field(default=None, max_length=500)


class ParsedClaim(BaseModel):
    model_config = STRICT

    claim: Claim
    source_url: HttpUrl
    source_type: SourceType
    evidence_excerpt: str = Field(min_length=1, max_length=1500)
    execution: ExecutionPlan = Field(default_factory=ExecutionPlan)


class PatchOperation(BaseModel):
    model_config = STRICT

    kind: Literal["replace_text", "write_file"]
    path: str = Field(min_length=1, max_length=500)
    old_text: str | None = Field(default=None, max_length=20_000)
    new_text: str = Field(max_length=20_000)

    @field_validator("path")
    @classmethod
    def reject_unsafe_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("patch paths must stay inside the cloned repository")
        return normalized


class DebugProposal(BaseModel):
    model_config = STRICT

    diagnosis: str = Field(min_length=1, max_length=4000)
    operations: list[PatchOperation] = Field(default_factory=list, max_length=12)
    replacement_command: list[str] | None = Field(default=None, max_length=50)


class EnvironmentResult(BaseModel):
    model_config = STRICT

    succeeded: bool
    exit_code: int | None = None
    phase: Literal["clone", "install", "evaluate", "metric", "infrastructure"]
    stdout: str = Field(default="", max_length=100_000)
    stderr: str = Field(default="", max_length=100_000)
    actual_value: float | None = None
    metric_evidence: str | None = Field(default=None, max_length=2000)
    diagnostic_files: dict[str, str] = Field(default_factory=dict)
    duration_seconds: float = Field(ge=0)
    sandbox_execution: str | None = None

    @property
    def error_text(self) -> str:
        return (self.stderr or self.stdout or f"{self.phase} failed")[-20_000:]


class AttemptLog(BaseModel):
    model_config = STRICT

    attempt: int = Field(ge=1, le=3)
    error_seen: str = Field(max_length=20_000)
    proposal: DebugProposal
    outcome: EnvironmentResult
    created_at: datetime = Field(default_factory=utc_now)


class TraceEvent(BaseModel):
    model_config = STRICT

    sequence: int = Field(ge=0)
    agent: Literal["orchestrator", "parser", "environment", "debug", "reporter"]
    action: str = Field(min_length=1, max_length=200)
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class Verdict(BaseModel):
    model_config = STRICT

    status: VerdictStatus
    confidence: Confidence
    claim: Claim
    actual_value: float | None = None
    summary: str = Field(min_length=1, max_length=5000)
    fixes_applied: list[str] = Field(default_factory=list, max_length=30)
    evidence: list[str] = Field(default_factory=list, max_length=100)
    attempts: list[AttemptLog] = Field(default_factory=list, max_length=3)
    issue_url: HttpUrl | None = None
    artifact_error: str | None = Field(default=None, max_length=5000)


class JobRecord(BaseModel):
    model_config = STRICT

    id: str
    canonical_url: str
    source_url: HttpUrl
    status: JobStatus
    cached: bool = False
    parsed_claim: ParsedClaim | None = None
    verdict: Verdict | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SubmitRequest(BaseModel):
    url: HttpUrl


class SubmitResponse(BaseModel):
    job_id: str
    status: JobStatus
    cached: bool
    status_url: str


class JobView(BaseModel):
    job: JobRecord
    trace: list[TraceEvent]


class SandboxRequest(BaseModel):
    model_config = STRICT

    run_id: str
    job_id: str
    parsed_claim: ParsedClaim
    patches: list[PatchOperation] = Field(default_factory=list, max_length=36)
    command_override: list[str] | None = Field(default=None, max_length=50)
    timeout_seconds: int = Field(default=900, ge=30, le=3600)
    created_at: datetime = Field(default_factory=utc_now)


class SandboxRun(BaseModel):
    model_config = STRICT

    request: SandboxRequest
    result: EnvironmentResult | None = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

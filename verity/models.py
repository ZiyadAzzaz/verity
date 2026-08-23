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
    """One label, one meaning. Collapsing two outcomes into one label is the failure mode
    this enum exists to prevent - a `could_not_verify` that quietly also means "we never
    really tried" is worse than no verdict at all."""

    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"
    #: Genuinely attempted the evaluation; it did not reproduce.
    COULD_NOT_VERIFY = "could_not_verify"
    #: The source asserts no headline result worth checking. Nothing was executed.
    NO_VERIFIABLE_CLAIM_FOUND = "no_verifiable_claim_found"
    #: The sandbox could not host this repository as written, so the claim was never tested.
    ENVIRONMENT_INCOMPATIBLE = "environment_incompatible"


class ClaimSignificance(StrEnum):
    """Whether the source is *asserting* this number as a result.

    "Top-1 accuracy 84.3% on ImageNet" is a contribution the author stands behind.
    "11 features" in a data-analysis README is a description of a table. Reproducing the
    second proves nothing, so Verity should decline rather than spend a sandbox on it.
    """

    HEADLINE_CLAIM = "headline_claim"
    INCIDENTAL_STATISTIC = "incidental_statistic"


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
    #: Defaults to headline so every job and fixture written before this field keeps its
    #: meaning; only an explicit judgement can downgrade a claim.
    claim_significance: ClaimSignificance = ClaimSignificance.HEADLINE_CLAIM
    significance_reason: str = Field(default="", max_length=1000)


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


#: Signatures of a process that tried to reach the network and was refused. The evaluation
#: phase runs with ``--network none`` on purpose, so a repository that downloads its dataset
#: at evaluation time cannot succeed whether its claim is true or false. Attributing that to
#: the claim would be blaming the source for our constraint.
_BLOCKED_NETWORK_MARKERS = (
    "temporary failure in name resolution",
    "name or service not known",
    "nodename nor servname provided",
    "connectionerror",
    "connectionrefusederror",
    "connection refused",
    "newconnectionerror",
    "failed to establish a new connection",
    "network is unreachable",
    "no route to host",
    "gaierror",
    "urlerror",
    "urlopen error",
    "max retries exceeded with url",
    "ssl",
    "certificate verify failed",
    "proxyerror",
    "read timed out",
)


def looks_environment_incompatible(result: EnvironmentResult) -> bool:
    """Did this fail because the sandbox denied network access, rather than on its merits?

    Deliberately narrow. Only the *evaluation* phase qualifies: clone and install run with
    the network open, so a failure there is a real failure. A succeeding run never qualifies.

    The asymmetry matters. Missing one blocked-network case costs a slightly unfair
    ``could_not_verify``; a false positive excuses a genuine reproduction failure as our own
    fault, which is exactly the kind of flattering misreport Verity exists to avoid.
    """
    if result.succeeded or result.phase != "evaluate":
        return False
    haystack = (result.stderr + "\n" + result.stdout).lower()
    return any(marker in haystack for marker in _BLOCKED_NETWORK_MARKERS)


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

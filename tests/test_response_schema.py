"""The JSON Schema Verity sends to Gemini as `response_schema`.

Gemini rejects `additionalProperties: false` with
`400 INVALID_ARGUMENT: Unknown name "additional_properties"`, which Pydantic emits for
every model configured `extra="forbid"`. These tests pin both halves of the fix: the wire
schema is accepted, and runtime validation stays strict.
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, ValidationError

from verity.models import (
    Claim,
    DebugProposal,
    EnvironmentResult,
    ExecutionPlan,
    ParsedClaim,
    PatchOperation,
    Verdict,
)

# The two schemas actually sent to the model by the Parser and Debug agents, plus the
# nested models they pull in and the ones declared on the ADK agent graph.
SCHEMAS = [ParsedClaim, DebugProposal, Claim, ExecutionPlan, PatchOperation, Verdict]


@pytest.mark.parametrize("model", SCHEMAS, ids=lambda m: m.__name__)
def test_no_schema_emits_additional_properties_false(model: type[BaseModel]) -> None:
    text = json.dumps(model.model_json_schema())
    assert '"additionalProperties": false' not in text
    assert '"additionalProperties":false' not in text


def test_map_typed_additional_properties_is_preserved() -> None:
    """Only the boolean form is stripped; a dict[str, str] map must keep its schema."""
    schema = EnvironmentResult.model_json_schema()
    diagnostic = schema["properties"]["diagnostic_files"]
    assert diagnostic["additionalProperties"] == {"type": "string"}


@pytest.mark.parametrize("model", SCHEMAS, ids=lambda m: m.__name__)
def test_runtime_validation_still_rejects_unexpected_fields(model: type[BaseModel]) -> None:
    """Stripping the key from the wire schema must not loosen what Verity accepts back."""
    assert model.model_config.get("extra") == "forbid"


def test_a_hallucinated_field_is_rejected_on_parse() -> None:
    with pytest.raises(ValidationError):
        Claim(
            metric="accuracy",
            value=90.0,
            dataset="ExampleSet",
            source_location="README",
            confidence_the_model_invented=0.9,  # type: ignore[call-arg]
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_claim_values_must_be_finite(value: float) -> None:
    with pytest.raises(ValidationError):
        Claim(
            metric="accuracy",
            value=value,
            dataset="ExampleSet",
            source_location="README",
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_observed_values_must_be_finite(value: float) -> None:
    with pytest.raises(ValidationError):
        EnvironmentResult(
            succeeded=True,
            phase="metric",
            actual_value=value,
            duration_seconds=1.0,
        )


@pytest.mark.parametrize(
    "repository_commit",
    ["abc123", "g" * 40, "A" * 40, "a" * 39, "a" * 41],
)
def test_repository_commit_must_be_a_full_lowercase_git_object_id(
    repository_commit: str,
) -> None:
    with pytest.raises(ValidationError):
        EnvironmentResult(
            succeeded=True,
            phase="metric",
            duration_seconds=1.0,
            repository_commit=repository_commit,
        )


def test_a_full_repository_commit_is_accepted() -> None:
    result = EnvironmentResult(
        succeeded=True,
        phase="metric",
        duration_seconds=1.0,
        repository_commit="a" * 40,
    )
    assert result.repository_commit == "a" * 40

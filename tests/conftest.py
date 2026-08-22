from __future__ import annotations

import pytest

from verity.models import Claim, ExecutionPlan, ParsedClaim, SourceType


@pytest.fixture
def parsed_claim() -> ParsedClaim:
    return ParsedClaim(
        claim=Claim(
            metric="accuracy",
            value=90.0,
            unit="%",
            dataset="ExampleSet test",
            conditions=["single checkpoint", "batch size 1"],
            source_location="README, Results table",
        ),
        source_url="https://github.com/example/project",
        source_type=SourceType.GITHUB,
        evidence_excerpt="Model A reaches 90.0% accuracy on ExampleSet test.",
        execution=ExecutionPlan(
            repository_url="https://github.com/example/project",
            evaluation_command=["python", "evaluate.py"],
            result_pattern=r"accuracy:\s*([0-9.]+)",
        ),
    )

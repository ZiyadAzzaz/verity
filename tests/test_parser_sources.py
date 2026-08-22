from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from verity.agents.parser import ParserAgent
from verity.models import Claim, ExecutionPlan, ParsedClaim, SourceType
from verity.source import SourceDocument, SourceFetcher


class RecordingGenerator:
    """A stand-in ModelClient: the parser must never reach a real model in unit tests."""

    def __init__(self, response: ParsedClaim) -> None:
        self.response = response
        self.document: SourceDocument | None = None

    async def generate(self, prompt: str, files: list[SourceDocument] | None = None) -> str:
        raise AssertionError("the Parser Agent must use the typed structured path")

    async def generate_structured(
        self,
        *,
        instruction: str,
        prompt: str,
        schema: type[BaseModel],
        document: SourceDocument | None = None,
    ) -> Any:
        self.document = document
        return self.response


CASES = [
    (
        "https://arxiv.org/abs/1512.03385",
        SourceType.ARXIV,
        "application/pdf",
        b"%PDF-1.4 recorded ResNet paper fixture",
        Claim(
            metric="top-5 error",
            value=3.57,
            unit="%",
            dataset="ImageNet test",
            conditions=["ensemble"],
            source_location="Abstract",
        ),
        ExecutionPlan(),
    ),
    (
        "https://github.com/facebookresearch/detr",
        SourceType.GITHUB,
        "text/plain",
        b"COCO val5k: 42.0 AP with a ResNet-50 backbone.",
        Claim(
            metric="box AP",
            value=42.0,
            dataset="COCO val5k",
            conditions=["ResNet-50 backbone"],
            source_location="README, Model Zoo",
        ),
        ExecutionPlan(
            repository_url="https://github.com/facebookresearch/detr",
            evaluation_command=["python", "main.py", "--eval"],
        ),
    ),
    (
        "https://www.nvidia.com/en-us/data-center/h100/",
        SourceType.VENDOR,
        "text/html",
        b"<html><body><h2>Performance</h2><p>Up to 4X AI training performance.</p></body></html>",
        Claim(
            metric="AI training performance multiplier",
            value=4.0,
            unit="x",
            dataset="vendor benchmark suite",
            conditions=["up to", "compared with prior generation"],
            source_location="Performance section",
        ),
        ExecutionPlan(),
    ),
]


@pytest.mark.parametrize("url,source_type,media_type,body,claim,execution", CASES)
async def test_parser_typed_contract_across_three_real_source_shapes(
    url: str,
    source_type: SourceType,
    media_type: str,
    body: bytes,
    claim: Claim,
    execution: ExecutionPlan,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"Content-Type": media_type}, content=body, request=request
        )

    expected = ParsedClaim(
        claim=claim,
        source_url=url,
        source_type=source_type,
        evidence_excerpt=body.decode("utf-8", errors="ignore") or "Recorded PDF table row",
        execution=execution,
    )
    generator = RecordingGenerator(expected)
    parser = ParserAgent(
        generator,
        SourceFetcher(validate_dns=False, transport=httpx.MockTransport(handler)),
    )
    result = await parser.run(url)
    assert result.claim == claim
    assert result.source_type == source_type
    assert generator.document is not None
    assert generator.document.media_type == (
        "application/pdf" if source_type == SourceType.ARXIV else media_type
    )

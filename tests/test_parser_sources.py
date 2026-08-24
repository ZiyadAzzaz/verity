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


# --- readme filename fallback --------------------------------------------------------------


def test_github_readme_candidates_cover_more_than_markdown() -> None:
    """tqdm ships README.rst. Assuming Markdown 404'd the job before the Parser ran."""
    from verity.models import SourceType
    from verity.source import README_NAMES, SourceFetcher

    fetcher = SourceFetcher()
    candidates = fetcher._github_readme_candidates(
        "https://github.com/tqdm/tqdm", SourceType.GITHUB
    )
    assert len(candidates) == len(README_NAMES)
    assert candidates[0].endswith("/README.md"), "Markdown stays the first guess"
    assert any(c.endswith("/README.rst") for c in candidates)
    assert all(
        c.startswith("https://raw.githubusercontent.com/tqdm/tqdm/HEAD/") for c in candidates
    )


def test_a_pinned_revision_is_preserved_across_candidates() -> None:
    from verity.models import SourceType
    from verity.source import SourceFetcher

    candidates = SourceFetcher()._github_readme_candidates(
        "https://github.com/ultralytics/yolov5/tree/v7.0", SourceType.GITHUB
    )
    assert all("/yolov5/v7.0/" in c for c in candidates), "the tag must survive the fallback"


def test_a_direct_blob_url_is_not_expanded() -> None:
    """Only a bare repository root guesses. An explicit file is taken literally."""
    from verity.models import SourceType
    from verity.source import SourceFetcher

    candidates = SourceFetcher()._github_readme_candidates(
        "https://github.com/psf/requests/blob/main/docs/index.rst", SourceType.GITHUB
    )
    assert len(candidates) == 1
    assert candidates[0].endswith("/docs/index.rst")


def test_non_github_sources_are_untouched() -> None:
    from verity.models import SourceType
    from verity.source import SourceFetcher

    fetcher = SourceFetcher()
    assert (
        len(fetcher._github_readme_candidates("https://arxiv.org/abs/1512.03385", SourceType.ARXIV))
        == 1
    )
    assert (
        len(fetcher._github_readme_candidates("https://example.com/claim", SourceType.VENDOR)) == 1
    )


async def test_readme_probe_never_auto_follows_an_unvalidated_redirect() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.host == "127.0.0.1":
            raise AssertionError("the HEAD probe followed an unvalidated private redirect")
        return httpx.Response(
            302,
            headers={"Location": "https://127.0.0.1/internal"},
            request=request,
        )

    candidate = "https://raw.githubusercontent.com/example/project/HEAD/README.md"
    fetcher = SourceFetcher(validate_dns=False, transport=httpx.MockTransport(handler))
    async with httpx.AsyncClient(
        transport=fetcher._transport,
        follow_redirects=False,
    ) as client:
        selected = await fetcher._first_that_exists(client, [candidate, candidate + ".rst"])

    assert selected == candidate
    assert seen == [candidate]

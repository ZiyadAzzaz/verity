"""Parser Agent: source acquisition plus typed multimodal claim extraction."""

from __future__ import annotations

from verity.interfaces import ModelClient
from verity.models import ParsedClaim
from verity.prompts import PARSER_INSTRUCTION
from verity.security import validate_repository_url
from verity.source import SourceFetcher


class ParserAgent:
    name = "parser"

    def __init__(
        self,
        generator: ModelClient,
        fetcher: SourceFetcher,
        *,
        allowed_repo_hosts: tuple[str, ...] = ("github.com",),
    ) -> None:
        self._generator = generator
        self._fetcher = fetcher
        self._allowed_repo_hosts = allowed_repo_hosts

    async def run(self, url: str) -> ParsedClaim:
        document = await self._fetcher.fetch(url)
        parsed = await self._generator.generate_structured(
            instruction=PARSER_INSTRUCTION,
            prompt=(
                f"Submitted URL: {document.requested_url}\n"
                f"Source type: {document.source_type.value}\n"
                "Extract the strongest concrete reproducible benchmark claim."
            ),
            schema=ParsedClaim,
            document=document,
        )
        parsed = parsed.model_copy(
            update={
                "source_url": document.requested_url,
                "source_type": document.source_type,
            }
        )
        if parsed.execution.repository_url is not None:
            repository_url = validate_repository_url(
                str(parsed.execution.repository_url), self._allowed_repo_hosts
            )
            parsed.execution.repository_url = repository_url  # type: ignore[assignment]
        return ParsedClaim.model_validate(parsed.model_dump())

"""Fetch arXiv PDFs, GitHub READMEs, and vendor pages with SSRF protections."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from verity.models import SourceType
from verity.security import canonicalize_url, validate_public_host

ARXIV_ID = re.compile(r"/(?:abs|pdf)/([^/?#]+?)(?:\.pdf)?$")


@dataclass(frozen=True, slots=True)
class SourceDocument:
    requested_url: str
    fetched_url: str
    source_type: SourceType
    media_type: str
    content: bytes
    text: str


#: Readme filenames to try at a GitHub repository root, in order. GitHub imposes no
#: convention, so assuming Markdown silently excludes a large slice of real repositories.
README_NAMES = ("README.md", "README.rst", "README.txt", "readme.md", "README", "README.markdown")


class SourceFetcher:
    def __init__(
        self,
        *,
        timeout_seconds: float = 30,
        max_bytes: int = 25_000_000,
        validate_dns: bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._validate_dns = validate_dns
        self._transport = transport

    @staticmethod
    def classify(url: str) -> SourceType:
        host = (urlsplit(url).hostname or "").lower()
        if host in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
            return SourceType.ARXIV
        if host in {"github.com", "www.github.com", "raw.githubusercontent.com"}:
            return SourceType.GITHUB
        return SourceType.VENDOR

    @staticmethod
    def _fetch_url(url: str, source_type: SourceType) -> str:
        parsed = urlsplit(url)
        if source_type == SourceType.ARXIV:
            match = ARXIV_ID.search(parsed.path)
            if match:
                return f"https://arxiv.org/pdf/{match.group(1)}"
        if source_type == SourceType.GITHUB and parsed.hostname in {"github.com", "www.github.com"}:
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 5 and parts[2] == "blob":
                return "https://raw.githubusercontent.com/" + "/".join(
                    [parts[0], parts[1], parts[3], *parts[4:]]
                )
            if len(parts) >= 2:
                revision = "HEAD"
                if len(parts) >= 4 and parts[2] == "tree":
                    revision = parts[3]
                base = f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/{revision}"
                return f"{base}/{README_NAMES[0]}"
        return url

    def _github_readme_candidates(self, url: str, source_type: SourceType) -> list[str]:
        """Every readme filename worth trying for a GitHub repository root.

        GitHub does not mandate Markdown. tqdm ships README.rst, plenty of projects ship
        README.txt, and casing varies. Hardcoding README.md meant a 404 killed the job before
        the Parser ever saw the source - which is not "this claim could not be verified", it
        is Verity failing to read a page that was sitting there.
        """
        first = self._fetch_url(url, source_type)
        if not first.startswith("https://raw.githubusercontent.com/"):
            return [first]
        if not first.endswith("/" + README_NAMES[0]):
            return [first]
        base = first[: -len(README_NAMES[0])]
        return [base + name for name in README_NAMES]

    async def _first_that_exists(self, client: Any, candidates: list[str]) -> str:
        """Return the first candidate the server will serve.

        Single candidate is the common case and costs nothing extra. Where several are in
        play, a HEAD request is cheap and avoids downloading a 404 body. If every one is
        missing, fall back to the first so the caller raises the familiar error against the
        filename a reader would expect.
        """
        if len(candidates) == 1:
            return candidates[0]
        for candidate in candidates:
            if self._validate_dns:
                await asyncio.to_thread(validate_public_host, candidate)
            try:
                # Never let httpx follow this probe automatically: each redirect target must
                # pass the same public-host validation as the real GET. A convenience HEAD
                # that follows redirects on its own reintroduces SSRF before the guarded
                # fetch loop even starts.
                probe = await client.head(candidate, follow_redirects=False)
            except httpx.HTTPError:
                continue
            if probe.status_code < 400:
                return candidate
        return candidates[0]

    async def fetch(self, raw_url: str) -> SourceDocument:
        requested = canonicalize_url(raw_url)
        source_type = self.classify(requested)
        candidates = self._github_readme_candidates(requested, source_type)
        headers = {"User-Agent": "Verity/0.1 (+https://github.com/verity-agent)"}
        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=False,
            transport=self._transport,
            headers=headers,
        ) as client:
            fetch_url = await self._first_that_exists(client, candidates)
            current_url = fetch_url
            for _redirect_count in range(6):
                if self._validate_dns:
                    await asyncio.to_thread(validate_public_host, current_url)
                async with client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("source returned a redirect without a location")
                        current_url = canonicalize_url(urljoin(current_url, location))
                        continue
                    response.raise_for_status()
                    final_url = canonicalize_url(str(response.url))
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > self._max_bytes:
                            raise ValueError(f"source exceeds {self._max_bytes} byte limit")
                        chunks.append(chunk)
                    content = b"".join(chunks)
                    media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    response_encoding = response.encoding or "utf-8"
                    break
            else:
                raise ValueError("source exceeded the 5-redirect limit")

        if source_type == SourceType.ARXIV or media_type == "application/pdf":
            text = ""
            media_type = "application/pdf"
        else:
            decoded = content.decode(response_encoding, errors="replace")
            if "html" in media_type or "<html" in decoded[:1000].lower():
                soup = BeautifulSoup(decoded, "html.parser")
                for tag in soup(["script", "style", "noscript", "svg"]):
                    tag.decompose()
                text = "\n".join(
                    line.strip() for line in soup.get_text("\n").splitlines() if line.strip()
                )
            else:
                text = decoded
        return SourceDocument(
            requested_url=requested,
            fetched_url=final_url,
            source_type=source_type,
            media_type=media_type or "text/plain",
            content=content,
            text=text[:2_000_000],
        )

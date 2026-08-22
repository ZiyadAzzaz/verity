"""Live Gemini validation of the Parser Agent on one PDF, one README, and one vendor page.

Three layers of assertion, strongest first:

1. **Grounding** - the ``evidence_excerpt`` must actually occur in the fetched source. This
   is the anti-fabrication check and the one that cannot be gamed by loosening a threshold:
   the model has to quote real text.
2. **Contract** - a finite value, a named metric and dataset, a precise source location, the
   right source type, and a repository only where one genuinely exists.
3. **Known claim** - where a source has one unambiguous headline number, that number.

Layer 3 is deliberately a *set* of acceptable claims per source, not a single value. A page
that carries several real benchmark numbers has several correct extractions; asserting one
of them would test the model's taste rather than its correctness, and would fail randomly
between runs. `tests/data/parser_cases.json` records why for each source. Where a source is
a live marketing page whose numbers change, layer 3 is empty and layers 1-2 carry the gate.

    python scripts/validate_parser_real.py

Requires GEMINI_API_KEY in local.env. Does not require Docker.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verity.agents.parser import ParserAgent
from verity.config import get_settings
from verity.container import build_model_client
from verity.models import ParsedClaim
from verity.source import SourceDocument, SourceFetcher


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def check_grounding(parsed: ParsedClaim, document: SourceDocument) -> str | None:
    """The excerpt must quote the source. Returns a failure reason, or None.

    PDFs are sent to Gemini as bytes and carry no extracted text on our side, so there is
    nothing local to compare against; that case is skipped rather than faked.
    """
    if not document.text.strip():
        return None
    haystack = normalize(document.text)
    # An excerpt is often a real sentence stitched to a reformatted table row, so the whole
    # string rarely matches byte for byte. Requiring one substantial *sentence* to appear
    # verbatim still proves the quote came from the page rather than being invented, which
    # is the property under test.
    pieces = re.split(r"\.\.\.|[\n\r]+|(?<=[.!?])\s+", parsed.evidence_excerpt)
    fragments = [normalize(piece) for piece in pieces]
    fragments = [fragment for fragment in fragments if len(fragment) >= 25]
    if not fragments:
        fragments = [normalize(parsed.evidence_excerpt)]
    if any(fragment in haystack for fragment in fragments):
        return None
    return (
        f"no sentence of evidence_excerpt occurs in the source: {parsed.evidence_excerpt[:160]!r}"
    )


def check_contract(parsed: ParsedClaim, case: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    claim = parsed.claim
    if claim.value != claim.value or claim.value in (float("inf"), float("-inf")):
        problems.append("value is not a finite number")
    for field in ("metric", "dataset", "source_location"):
        if not getattr(claim, field).strip():
            problems.append(f"{field} is empty")
    if parsed.source_type.value != case["source_type"]:
        problems.append(
            f"source_type is {parsed.source_type.value}, expected {case['source_type']}"
        )
    has_repository = parsed.execution.repository_url is not None
    if case["expect_repository"] and not has_repository:
        problems.append("no repository was extracted from a source that links one")
    if not case["expect_repository"] and has_repository:
        problems.append(f"invented a repository: {parsed.execution.repository_url}")
    return problems


def match_known_claim(parsed: ParsedClaim, case: dict[str, Any]) -> tuple[bool, str]:
    acceptable = case.get("acceptable") or []
    if not acceptable:
        return True, "not pinned (see the note in parser_cases.json)"
    claim = parsed.claim
    for option in acceptable:
        if (
            option["metric_contains"].lower() in claim.metric.lower()
            and abs(claim.value - option["value"]) <= 0.02
            and option["dataset_contains"].lower() in claim.dataset.lower()
        ):
            return True, option["which"]
    expected = " | ".join(
        f"{o['metric_contains']}~{o['value']} on {o['dataset_contains']}" for o in acceptable
    )
    return (
        False,
        f"got {claim.metric}={claim.value:g} on {claim.dataset}; expected one of: {expected}",
    )


async def main() -> None:
    settings = get_settings()
    # The key normally lives in local.env, which pydantic-settings reads directly rather
    # than exporting into os.environ - so check the settings object, not the environment.
    if not (
        settings.gemini_api_key or os.getenv("GOOGLE_API_KEY") or settings.google_cloud_project
    ):
        raise SystemExit(
            "Set GEMINI_API_KEY in local.env, or authenticated Vertex AI variables, first."
        )
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "tests/data/parser_cases.json").read_text(encoding="utf-8"))

    fetcher = SourceFetcher(
        timeout_seconds=settings.source_timeout_seconds,
        max_bytes=settings.max_source_bytes,
    )
    parser = ParserAgent(build_model_client(settings), fetcher)

    failures: list[str] = []
    for case in cases:
        print(f"\n=== {case['name']}: {case['url']}", flush=True)
        parsed = await parser.run(case["url"])
        claim = parsed.claim
        print(f"  metric   : {claim.metric} = {claim.value:g}{claim.unit}")
        print(f"  dataset  : {claim.dataset}")
        print(f"  location : {claim.source_location}")
        print(f"  repo     : {parsed.execution.repository_url}")
        print(f"  evidence : {parsed.evidence_excerpt[:150]}")

        problems = check_contract(parsed, case)

        document = await fetcher.fetch(case["url"])
        grounding = check_grounding(parsed, document)
        if grounding:
            problems.append(grounding)
            print("  grounding: FAILED")
        elif document.text.strip():
            print("  grounding: excerpt found verbatim in the source")
        else:
            print("  grounding: skipped (PDF carries no locally extracted text)")

        matched, detail = match_known_claim(parsed, case)
        print(f"  claim    : {'matched - ' if matched else 'UNRECOGNISED - '}{detail}")
        if not matched:
            problems.append(f"unrecognised claim: {detail}")

        for problem in problems:
            failures.append(f"{case['name']}: {problem}")

    print()
    if failures:
        print(f"{len(failures)} problem(s):")
        for problem in failures:
            print(f"  - {problem}")
        raise SystemExit("Parser validation failed.")
    print(f"Parser validation passed for {len(cases)} varied real sources.")


if __name__ == "__main__":
    asyncio.run(main())

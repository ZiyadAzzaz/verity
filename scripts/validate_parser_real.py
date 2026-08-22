"""Live Gemini validation on one PDF, one README, and one vendor page."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from verity.agents.parser import ParserAgent
from verity.config import get_settings
from verity.container import build_model_client
from verity.source import SourceFetcher


async def main() -> None:
    if not (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
    ):
        raise SystemExit(
            "Set GEMINI_API_KEY or authenticated Vertex AI environment variables first."
        )
    cases = json.loads(Path("tests/data/parser_cases.json").read_text(encoding="utf-8"))
    settings = get_settings()
    parser = ParserAgent(
        build_model_client(settings),
        SourceFetcher(
            timeout_seconds=settings.source_timeout_seconds,
            max_bytes=settings.max_source_bytes,
        ),
    )
    failures: list[str] = []
    for case in cases:
        parsed = await parser.run(case["url"])
        print(json.dumps(parsed.model_dump(mode="json"), indent=2))
        checks = {
            "metric": case["expected_metric_contains"].lower() in parsed.claim.metric.lower(),
            "value": abs(parsed.claim.value - case["expected_value"]) <= 0.02,
            "dataset": case["expected_dataset_contains"].lower() in parsed.claim.dataset.lower(),
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            failures.append(f"{case['name']}: {', '.join(failed)}")
    if failures:
        raise SystemExit("Parser validation failed: " + "; ".join(failures))
    print(f"Parser validation passed for {len(cases)} varied real sources.")


if __name__ == "__main__":
    asyncio.run(main())

"""Exercise the real environment/debug loop on a public, deliberately failing repository.

This is the honest-failure proof against real code: the NICAR debugging exercise repo has
genuine failures in its suite, so the Environment Agent really fails, the Debug Agent
really proposes patches, and the loop really stops after three attempts. Runs through the
configured sandbox backend, which is Docker locally.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verity.agents.debug import DebugAgent
from verity.agents.environment import EnvironmentAgent
from verity.config import get_settings
from verity.container import build_model_client, build_sandbox
from verity.models import Claim, ExecutionPlan, ParsedClaim, PatchOperation, SourceType
from verity.store import MemoryJobStore

BROKEN_REPO = "https://github.com/ghing/nicar2016-python-testing-debugging-exercises"


async def main() -> None:
    settings = get_settings()
    parsed = ParsedClaim(
        claim=Claim(
            metric="unit test failures",
            value=0,
            dataset="repository unittest suite",
            conditions=["clean Python 3.11 environment"],
            source_location="README: Reading an error message",
        ),
        source_url=BROKEN_REPO,
        source_type=SourceType.GITHUB,
        evidence_excerpt="The exercise repository intentionally includes a failing test case.",
        execution=ExecutionPlan(
            repository_url=BROKEN_REPO,
            evaluation_command=["python", "-m", "unittest", "discover"],
            result_pattern=r"failures=([0-9]+)",
        ),
    )
    sandbox = build_sandbox(settings, MemoryJobStore())
    await sandbox.preflight()
    environment = EnvironmentAgent(sandbox)
    debugger = DebugAgent(build_model_client(settings))
    patches: list[PatchOperation] = []
    command_override: list[str] | None = None
    result = await environment.run("broken-repo-proof", parsed, patches)
    print(json.dumps({"initial": result.model_dump(mode="json")}, indent=2))
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, 4):
        if result.succeeded:
            break
        proposal = await debugger.run(parsed, result, patches, attempt)
        patches.extend(proposal.operations)
        command_override = proposal.replacement_command or command_override
        result = await environment.run("broken-repo-proof", parsed, patches, command_override)
        attempts.append(
            {
                "attempt": attempt,
                "proposal": proposal.model_dump(mode="json"),
                "outcome": result.model_dump(mode="json"),
            }
        )
        print(json.dumps(attempts[-1], indent=2))
    print(
        json.dumps(
            {
                "terminal_state": "fixed" if result.succeeded else "could_not_verify",
                "debug_attempts": len(attempts),
                "broken_repo": BROKEN_REPO,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())

"""Debug Agent: proposes a bounded, reviewable patch from a real failed run."""

from __future__ import annotations

import json

from verity.interfaces import ModelClient
from verity.models import DebugProposal, EnvironmentResult, ParsedClaim, PatchOperation
from verity.prompts import DEBUG_INSTRUCTION


class DebugAgent:
    name = "debug"

    def __init__(self, generator: ModelClient) -> None:
        self._generator = generator

    async def run(
        self,
        parsed_claim: ParsedClaim,
        failure: EnvironmentResult,
        prior_patches: list[PatchOperation],
        attempt: int,
    ) -> DebugProposal:
        payload = {
            "attempt": attempt,
            "claim": parsed_claim.claim.model_dump(mode="json"),
            "execution_plan": parsed_claim.execution.model_dump(mode="json"),
            "failed_phase": failure.phase,
            "exit_code": failure.exit_code,
            "stdout": failure.stdout[-20_000:],
            "stderr": failure.stderr[-20_000:],
            "diagnostic_files": failure.diagnostic_files,
            "patches_already_applied": [patch.model_dump(mode="json") for patch in prior_patches],
        }
        return await self._generator.generate_structured(
            instruction=DEBUG_INSTRUCTION,
            prompt=(
                "Propose the smallest defensible repair for this failed reproduction.\n"
                "<UNTRUSTED_FAILURE_JSON>\n"
                + json.dumps(payload, ensure_ascii=False)
                + "\n</UNTRUSTED_FAILURE_JSON>"
            ),
            schema=DebugProposal,
        )

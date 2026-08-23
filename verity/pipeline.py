"""Idempotent four-agent state machine with a hard three-attempt debug cap."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from verity.agents import DebugAgent, EnvironmentAgent, ParserAgent, ReporterAgent
from verity.interfaces import JobStore
from verity.models import AttemptLog, DebugProposal, JobStatus, PatchOperation
from verity.telemetry import agent_span

logger = logging.getLogger(__name__)


class VerificationPipeline:
    def __init__(
        self,
        *,
        store: JobStore,
        parser: ParserAgent,
        environment: EnvironmentAgent,
        debugger: DebugAgent,
        reporter: ReporterAgent,
        max_debug_attempts: int = 3,
    ) -> None:
        if max_debug_attempts != 3:
            raise ValueError("Verity's debug loop must be hard-capped at exactly 3 attempts")
        self._store = store
        self._parser = parser
        self._environment = environment
        self._debugger = debugger
        self._reporter = reporter
        self._max_debug_attempts = max_debug_attempts

    async def process(self, job_id: str) -> None:
        if not await self._store.claim_job(job_id):
            logger.info("Ignoring duplicate delivery", extra={"job_id": job_id})
            return
        job = await self._store.get_job(job_id)
        if job is None:
            return
        try:
            await self._trace(job_id, "parser", "source_fetch_started", {"url": job.canonical_url})
            with agent_span("parser", job_id):
                parsed = await self._parser.run(job.canonical_url)
            await self._store.update_job(
                job_id,
                parsed_claim=parsed,
                status=JobStatus.PROVISIONING,
            )
            await self._trace(
                job_id,
                "parser",
                "claim_extracted",
                parsed.model_dump(mode="json"),
            )

            await self._store.update_job(job_id, status=JobStatus.RUNNING)
            await self._trace(job_id, "environment", "initial_run_started")
            with agent_span("environment", job_id):
                result = await self._environment.run(job_id, parsed, [])
            await self._trace(
                job_id,
                "environment",
                "initial_run_finished",
                result.model_dump(mode="json"),
            )

            patches: list[PatchOperation] = []
            command_override: list[str] | None = None
            attempts: list[AttemptLog] = []
            if not result.succeeded:
                for attempt_number in range(1, self._max_debug_attempts + 1):
                    await self._store.update_job(job_id, status=JobStatus.DEBUGGING)
                    await self._trace(
                        job_id,
                        "debug",
                        "attempt_started",
                        {"attempt": attempt_number, "error_seen": result.error_text},
                    )
                    try:
                        with agent_span("debug", job_id, attempt=attempt_number):
                            proposal = await self._debugger.run(
                                parsed, result, patches, attempt_number
                            )
                    except ValidationError as exc:
                        # The model proposed something the safety contract refuses - a patch
                        # path outside the cloned repository, an over-long operation list, a
                        # malformed command. That is a *failed debug attempt*, not an
                        # infrastructure fault: the boundary held and the loop should spend
                        # the attempt and carry on, ending in an honest could_not_verify if
                        # all three are used up. Letting it escape would abort the job with
                        # no verdict at all, which reads as a crash rather than a refusal.
                        rejected = DebugProposal(
                            diagnosis=(
                                f"Attempt {attempt_number} rejected: the proposed patch "
                                f"violated Verity's safety contract and was not applied. "
                                f"{exc.error_count()} validation error(s): "
                                f"{'; '.join(str(e.get('msg', '')) for e in exc.errors()[:3])}"
                            )[:4000],
                        )
                        attempt = AttemptLog(
                            attempt=attempt_number,
                            error_seen=result.error_text,
                            proposal=rejected,
                            outcome=result,
                        )
                        attempts.append(attempt)
                        await self._trace(
                            job_id,
                            "debug",
                            "attempt_rejected",
                            attempt.model_dump(mode="json"),
                        )
                        continue
                    patches.extend(proposal.operations)
                    if proposal.replacement_command is not None:
                        command_override = proposal.replacement_command
                    await self._store.update_job(job_id, status=JobStatus.RUNNING)
                    with agent_span("environment", job_id, attempt=attempt_number):
                        outcome = await self._environment.run(
                            job_id,
                            parsed,
                            patches,
                            command_override,
                        )
                    attempt = AttemptLog(
                        attempt=attempt_number,
                        error_seen=result.error_text,
                        proposal=proposal,
                        outcome=outcome,
                    )
                    attempts.append(attempt)
                    await self._trace(
                        job_id,
                        "debug",
                        "attempt_finished",
                        attempt.model_dump(mode="json"),
                    )
                    result = outcome
                    if result.succeeded:
                        break

            await self._store.update_job(job_id, status=JobStatus.REPORTING)
            await self._trace(
                job_id,
                "reporter",
                "verdict_started",
                {"debug_attempts": len(attempts)},
            )
            with agent_span("reporter", job_id):
                verdict = await self._reporter.run(job_id, parsed, result, attempts)
            await self._trace(
                job_id,
                "reporter",
                "verdict_completed",
                verdict.model_dump(mode="json"),
            )
            if verdict.artifact_error:
                await self._store.update_job(
                    job_id,
                    verdict=verdict,
                    status=JobStatus.FAILED,
                    error=verdict.artifact_error,
                )
            else:
                await self._store.complete_job(job_id, verdict)
        except Exception as exc:
            logger.exception("Verification pipeline failed", extra={"job_id": job_id})
            await self._trace(
                job_id,
                "orchestrator",
                "pipeline_failed",
                {"error_type": type(exc).__name__, "error": str(exc)[:5000]},
            )
            await self._store.update_job(
                job_id,
                status=JobStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}"[:5000],
            )

    async def _trace(
        self,
        job_id: str,
        agent: str,
        action: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        await self._store.append_trace(
            job_id,
            agent=agent,
            action=action,
            detail=detail,
        )
        logger.info(
            "%s.%s",
            agent,
            action,
            extra={"job_id": job_id, "agent": agent, "action": action},
        )

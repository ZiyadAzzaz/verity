"""Idempotent four-agent state machine with a hard three-attempt debug cap."""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import ValidationError

from verity.agents import DebugAgent, EnvironmentAgent, ParserAgent, ReporterAgent
from verity.interfaces import JobStore
from verity.models import (
    AttemptLog,
    ClaimSignificance,
    Confidence,
    DebugProposal,
    EnvironmentResult,
    JobStatus,
    ParsedClaim,
    PatchOperation,
    Verdict,
    VerdictStatus,
    failure_excerpt,
    looks_environment_incompatible,
)
from verity.telemetry import agent_span

logger = logging.getLogger(__name__)
FULL_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _with_pinned_revision(parsed: ParsedClaim, commit: str | None) -> ParsedClaim:
    if commit is None or parsed.execution.revision == commit:
        return parsed
    execution = parsed.execution.model_copy(update={"revision": commit})
    return parsed.model_copy(update={"execution": execution})


def _enforce_repository_revision(
    result: EnvironmentResult,
    expected_commit: str | None,
) -> EnvironmentResult:
    """Turn post-clone revision drift into a platform failure, never a claim result."""

    if expected_commit is None:
        return result
    if result.repository_commit == expected_commit:
        return result
    observed = result.repository_commit or "missing"
    integrity_error = (
        f"Repository revision integrity failure: expected {expected_commit}, observed {observed}."
    )
    payload = result.model_dump(mode="python")
    payload.update(
        {
            "succeeded": False,
            "phase": "infrastructure",
            "actual_value": None,
            "metric_evidence": None,
            # Keep the integrity diagnosis at the tail, where failure_excerpt reads from.
            "stderr": (result.stderr[-90_000:] + "\n" + integrity_error)[-100_000:],
        }
    )
    return EnvironmentResult.model_validate(payload)


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

            # Nothing the source asserts as a result is worth burning a sandbox on. Stop here
            # rather than executing and then reporting could_not_verify, which would claim we
            # tried to reproduce something nobody ever put forward as a finding.
            if parsed.claim_significance is ClaimSignificance.INCIDENTAL_STATISTIC:
                await self._finish_without_execution(
                    job_id,
                    parsed,
                    VerdictStatus.NO_VERIFIABLE_CLAIM_FOUND,
                    (
                        "No headline performance claim was found at this source. The strongest "
                        f"quantitative statement available was '{parsed.claim.metric} = "
                        f"{parsed.claim.value:g}{parsed.claim.unit}', which the source presents "
                        "as a descriptive statistic rather than a result it is asserting. "
                        "Nothing was executed, and no reproduction was attempted."
                        + (f" {parsed.significance_reason}" if parsed.significance_reason else "")
                    ),
                )
                return

            await self._store.update_job(job_id, status=JobStatus.RUNNING)
            await self._trace(job_id, "environment", "initial_run_started")
            requested_revision = parsed.execution.revision
            pinned_commit = (
                requested_revision
                if requested_revision is not None and FULL_GIT_COMMIT.fullmatch(requested_revision)
                else None
            )
            with agent_span("environment", job_id):
                result = await self._environment.run(job_id, parsed, [])
            result = _enforce_repository_revision(result, pinned_commit)
            await self._trace(
                job_id,
                "environment",
                "initial_run_finished",
                result.model_dump(mode="json"),
            )
            if result.phase == "infrastructure":
                await self._fail_infrastructure(job_id, result)
                return
            if pinned_commit is None and result.repository_commit is not None:
                pinned_commit = result.repository_commit
                parsed = _with_pinned_revision(parsed, pinned_commit)
                await self._store.update_job(job_id, parsed_claim=parsed)
                await self._trace(
                    job_id,
                    "environment",
                    "repository_revision_pinned",
                    {"repository_commit": pinned_commit},
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
                    proposed_patch_count = len(proposal.operations)
                    previous_command_override = command_override
                    if proposal.replacement_command is not None:
                        command_override = proposal.replacement_command
                    await self._store.update_job(job_id, status=JobStatus.RUNNING)
                    with agent_span("environment", job_id, attempt=attempt_number):
                        outcome = await self._environment.run(
                            job_id,
                            _with_pinned_revision(parsed, pinned_commit),
                            patches,
                            command_override,
                        )
                    outcome = _enforce_repository_revision(outcome, pinned_commit)
                    if pinned_commit is None and outcome.repository_commit is not None:
                        pinned_commit = outcome.repository_commit
                        parsed = _with_pinned_revision(parsed, pinned_commit)
                        await self._store.update_job(job_id, parsed_claim=parsed)
                        await self._trace(
                            job_id,
                            "environment",
                            "repository_revision_pinned",
                            {"repository_commit": pinned_commit},
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
                    if (
                        proposed_patch_count
                        and not outcome.succeeded
                        and outcome.stderr.startswith("Patch application failed:")
                    ):
                        # Every attempt reclones from scratch. A patch bundle that could not
                        # even be applied must not poison all later attempts by remaining in
                        # the cumulative list.
                        del patches[-proposed_patch_count:]
                        command_override = previous_command_override
                    if result.succeeded:
                        break
                    if result.phase == "infrastructure":
                        break

            if result.phase == "infrastructure":
                await self._fail_infrastructure(job_id, result)
                return

            # The evaluation phase has no network by design. A repository that fetches its
            # data at evaluation time therefore cannot succeed whether its claim is true or
            # false, so calling that could_not_verify would blame the claim for our sandbox.
            # Checked only after the debug loop: if a patch made it run offline, it ran.
            if looks_environment_incompatible(result):
                await self._finish_without_execution(
                    job_id,
                    parsed,
                    VerdictStatus.ENVIRONMENT_INCOMPATIBLE,
                    (
                        "This claim was never tested. The evaluation reached the network, "
                        "which Verity's sandbox denies during evaluation so that a benchmark "
                        "cannot fetch data mid-measurement. The repository needs network "
                        "access at evaluation time and is untestable as written under that "
                        "constraint. This is a limitation of the sandbox, not evidence about "
                        "the claim."
                    ),
                    attempts=attempts,
                    evidence=[f"Final failure ({result.phase}): {failure_excerpt(result)}"],
                )
                return

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
            await self._persist_verdict(job_id, verdict)
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

    async def _finish_without_execution(
        self,
        job_id: str,
        parsed: ParsedClaim,
        status: VerdictStatus,
        summary: str,
        *,
        attempts: list[AttemptLog] | None = None,
        evidence: list[str] | None = None,
    ) -> None:
        """Complete a job with an outcome that is neither success nor reproduction failure.

        Both callers share one property worth stating in code: ``actual_value`` is None and
        stays None. Nothing was measured, so nothing may be reported - the same rule that
        governs ``could_not_verify``, applied to outcomes that are not it.
        """
        recorded = attempts or []
        # Populate fixes from the attempts, exactly as ReporterAgent.run does. Omitting this
        # made the Issue say "Fixes applied: None" directly above a debug trail describing a
        # runner script being written - the summary contradicting its own evidence.
        verdict = Verdict(
            status=status,
            confidence=Confidence.HIGH,
            claim=parsed.claim,
            actual_value=None,
            summary=summary,
            fixes_applied=[
                f"{operation.kind} {operation.path}"
                for attempt in recorded
                if not attempt.outcome.stderr.startswith("Patch application failed:")
                for operation in attempt.proposal.operations
            ],
            attempts=recorded,
            evidence=evidence or [],
        )
        await self._store.update_job(job_id, status=JobStatus.REPORTING)
        await self._trace(job_id, "reporter", "verdict_started", {"short_circuit": status.value})
        with agent_span("reporter", job_id):
            verdict = await self._reporter.publish(job_id, parsed, verdict)
        await self._trace(
            job_id,
            "reporter",
            "verdict_completed",
            verdict.model_dump(mode="json"),
        )
        await self._persist_verdict(job_id, verdict)

    async def _persist_verdict(self, job_id: str, verdict: Verdict) -> None:
        """Apply one artifact policy to normal and short-circuit verdicts alike."""

        if verdict.artifact_error:
            await self._store.update_job(
                job_id,
                verdict=verdict,
                status=JobStatus.FAILED,
                error=verdict.artifact_error,
            )
            return
        await self._store.complete_job(job_id, verdict)

    async def _fail_infrastructure(self, job_id: str, result: EnvironmentResult) -> None:
        """Keep platform failures out of claim-verdict taxonomy and debug retries."""

        error = f"Sandbox infrastructure failure: {failure_excerpt(result)}"[:5000]
        await self._trace(
            job_id,
            "orchestrator",
            "infrastructure_failed",
            {"phase": result.phase, "error": error},
        )
        await self._store.update_job(job_id, status=JobStatus.FAILED, error=error)

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

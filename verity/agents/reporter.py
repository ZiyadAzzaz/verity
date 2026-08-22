"""Reporter Agent: deterministic verdict synthesis and durable GitHub artifact."""

from __future__ import annotations

from verity.github import IssuePublisher, render_issue
from verity.models import (
    AttemptLog,
    Confidence,
    EnvironmentResult,
    ParsedClaim,
    Verdict,
    VerdictStatus,
)


class ReporterAgent:
    name = "reporter"

    def __init__(
        self, issue_publisher: IssuePublisher, *, relative_tolerance: float = 0.02
    ) -> None:
        self._issues = issue_publisher
        self._tolerance = relative_tolerance

    async def run(
        self,
        job_id: str,
        parsed_claim: ParsedClaim,
        result: EnvironmentResult,
        attempts: list[AttemptLog],
    ) -> Verdict:
        claim = parsed_claim.claim
        evidence: list[str] = []
        if result.sandbox_execution:
            evidence.append(f"Cloud Run execution: {result.sandbox_execution}")
        evidence.append(
            f"Final process phase={result.phase}, exit_code={result.exit_code}, "
            f"duration={result.duration_seconds:.2f}s"
        )
        if result.metric_evidence:
            evidence.append("Metric output: " + result.metric_evidence[:1500])
        if not result.succeeded:
            status = VerdictStatus.COULD_NOT_VERIFY
            confidence = Confidence.HIGH if len(attempts) == 3 else Confidence.MEDIUM
            summary = (
                f"Verity could not complete the claimed evaluation after {len(attempts)} "
                "bounded debug attempts. No reproduced value is asserted."
            )
        elif result.actual_value is None:
            status = VerdictStatus.INCONCLUSIVE
            confidence = Confidence.LOW
            summary = (
                "The evaluation command exited successfully, but its output did not contain a "
                "defensibly attributable value for the claimed metric."
            )
        else:
            tolerance = max(abs(claim.value) * self._tolerance, 0.01)
            difference = abs(result.actual_value - claim.value)
            if difference <= tolerance:
                status = VerdictStatus.VERIFIED
                confidence = Confidence.HIGH if not attempts else Confidence.MEDIUM
                summary = (
                    f"The reproduced {claim.metric} ({result.actual_value:g}{claim.unit}) is "
                    f"within the declared {self._tolerance:.0%} comparison tolerance of the "
                    f"claim ({claim.value:g}{claim.unit})."
                )
            else:
                status = VerdictStatus.CONTRADICTED
                confidence = Confidence.HIGH if not attempts else Confidence.MEDIUM
                summary = (
                    f"The reproduced {claim.metric} ({result.actual_value:g}{claim.unit}) differs "
                    f"from the claim ({claim.value:g}{claim.unit}) by {difference:g}{claim.unit}."
                )
        fixes = [
            f"{operation.kind} {operation.path}"
            for attempt in attempts
            for operation in attempt.proposal.operations
        ]
        verdict = Verdict(
            status=status,
            confidence=confidence,
            claim=claim,
            actual_value=result.actual_value,
            summary=summary,
            fixes_applied=fixes,
            evidence=evidence,
            attempts=attempts,
        )
        title, body = render_issue(verdict, parsed_claim, job_id)
        try:
            issue_url = await self._issues.publish(parsed_claim, title, body)
        except Exception as exc:
            return verdict.model_copy(
                update={
                    "artifact_error": f"GitHub issue filing failed: {type(exc).__name__}: {exc}"[
                        :5000
                    ]
                }
            )
        if issue_url:
            verdict = verdict.model_copy(update={"issue_url": issue_url})
        return verdict

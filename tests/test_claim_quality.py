"""Outcomes that must not collapse into each other.

Verity already keeps `failed` (infrastructure died) separate from `could_not_verify` (we
genuinely tried and it did not reproduce). Two more distinctions belong in that same family,
and both came out of real runs:

* A data-analysis repository whose only quantifiable number was "11 features" produced
  `could_not_verify`. Nothing was wrong with the pipeline — but "we tried to reproduce this
  and failed" is a false description of what happened. Nobody ever asserted 11 features as a
  result worth checking.
* The evaluation phase runs with no network, by design. A repository that fetches its dataset
  at evaluation time therefore cannot succeed whether its claim is true or false. Reporting
  that as `could_not_verify` blames the claim for the sandbox's constraint.

`could_not_verify` has to keep meaning exactly one thing, or the honest-failure story stops
being honest.
"""

from __future__ import annotations

import pytest

from verity.models import (
    ClaimSignificance,
    EnvironmentResult,
    JobStatus,
    VerdictStatus,
    conditions_require_comparison_provenance,
    looks_environment_incompatible,
)


class TestClaimSignificance:
    """A claim the source never asserted as a result should not be 'verified' or 'failed'."""

    def test_the_two_significance_values_exist(self) -> None:
        assert ClaimSignificance.HEADLINE_CLAIM == "headline_claim"
        assert ClaimSignificance.INCIDENTAL_STATISTIC == "incidental_statistic"

    def test_parsed_claim_carries_significance(self, parsed_claim) -> None:
        assert hasattr(parsed_claim, "claim_significance")

    def test_significance_defaults_to_headline_for_existing_callers(self, parsed_claim) -> None:
        """Every fixture and stored job predating this field describes a real claim."""
        assert parsed_claim.claim_significance == ClaimSignificance.HEADLINE_CLAIM

    def test_an_incidental_statistic_is_representable(self, parsed_claim) -> None:
        incidental = parsed_claim.model_copy(
            update={"claim_significance": ClaimSignificance.INCIDENTAL_STATISTIC}
        )
        assert incidental.claim_significance == ClaimSignificance.INCIDENTAL_STATISTIC

    def test_no_verifiable_claim_found_is_its_own_verdict(self) -> None:
        assert VerdictStatus.NO_VERIFIABLE_CLAIM_FOUND == "no_verifiable_claim_found"
        assert VerdictStatus.NO_VERIFIABLE_CLAIM_FOUND != VerdictStatus.COULD_NOT_VERIFY


class TestEnvironmentIncompatibility:
    """The sandbox denying network access is our constraint, not evidence about the claim."""

    def test_environment_incompatible_is_its_own_verdict(self) -> None:
        assert VerdictStatus.ENVIRONMENT_INCOMPATIBLE == "environment_incompatible"
        assert VerdictStatus.ENVIRONMENT_INCOMPATIBLE != VerdictStatus.COULD_NOT_VERIFY

    @pytest.mark.parametrize(
        "stderr",
        [
            "urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>",
            "socket.gaierror: [Errno -2] Name or service not known",
            "requests.exceptions.ConnectionError: HTTPSConnectionPool(host='storage.googleapis.com', port=443)",
            "ConnectionRefusedError: [Errno 111] Connection refused",
            "urllib3.exceptions.NewConnectionError: Failed to establish a new connection",
            "OSError: [Errno 101] Network is unreachable",
            "ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed",
        ],
    )
    def test_blocked_network_signatures_are_detected(self, stderr: str) -> None:
        result = EnvironmentResult(
            succeeded=False, exit_code=1, phase="evaluate", stderr=stderr, duration_seconds=1.0
        )
        assert looks_environment_incompatible(result) is True

    @pytest.mark.parametrize(
        "stderr",
        [
            "AssertionError: expected 0.92 but got 0.71",
            "ModuleNotFoundError: No module named 'torch'",
            "FileNotFoundError: weights.pt",
            "SyntaxError: invalid syntax",
            "ValueError: shapes (3,4) and (5,6) not aligned",
            "ValueError: ssl parameter is invalid",
            "TimeoutError: read timed out while evaluating a local lock",
        ],
    )
    def test_genuine_failures_are_not_mistaken_for_network_blocks(self, stderr: str) -> None:
        """The costly error is the other direction: excusing a real failure as our fault."""
        result = EnvironmentResult(
            succeeded=False, exit_code=1, phase="evaluate", stderr=stderr, duration_seconds=1.0
        )
        assert looks_environment_incompatible(result) is False

    def test_only_the_offline_evaluate_phase_counts(self) -> None:
        """Install runs *with* network on purpose, so a failure there is a real failure."""
        offline = EnvironmentResult(
            succeeded=False,
            exit_code=1,
            phase="evaluate",
            stderr="socket.gaierror: Name or service not known",
            duration_seconds=1.0,
        )
        online = offline.model_copy(update={"phase": "install"})
        assert looks_environment_incompatible(offline) is True
        assert looks_environment_incompatible(online) is False

    def test_a_succeeding_run_is_never_environment_incompatible(self) -> None:
        result = EnvironmentResult(
            succeeded=True,
            exit_code=0,
            phase="evaluate",
            stderr="socket.gaierror mentioned in passing",
            actual_value=0.91,
            duration_seconds=1.0,
        )
        assert looks_environment_incompatible(result) is False


def test_every_verdict_status_means_exactly_one_thing() -> None:
    """The guardrail this whole change exists to protect."""
    meanings = {
        VerdictStatus.VERIFIED: "reproduced within tolerance",
        VerdictStatus.CONTRADICTED: "reproduced outside tolerance",
        VerdictStatus.INCONCLUSIVE: "ran clean but produced no attributable metric",
        VerdictStatus.CONDITIONS_NOT_COMPARABLE: (
            "ran and observed a metric, but material conditions were not comparable"
        ),
        VerdictStatus.COULD_NOT_VERIFY: "genuinely attempted, did not reproduce",
        VerdictStatus.NO_VERIFIABLE_CLAIM_FOUND: "the source asserts no result worth checking",
        VerdictStatus.ENVIRONMENT_INCOMPATIBLE: "our sandbox could not host this, untested",
    }
    assert set(meanings) == set(VerdictStatus), "a new status must be given a distinct meaning"
    assert len(set(meanings.values())) == len(meanings)


@pytest.mark.parametrize(
    ("metric", "expected"),
    [("median latency", True), ("training_time", True), ("accuracy", False), ("BLEU", False)],
)
def test_condition_sensitive_metrics_are_classified(metric: str, expected: bool) -> None:
    assert conditions_require_comparison_provenance(metric) is expected


# --- pipeline behaviour -----------------------------------------------------------------

from dataclasses import dataclass, field  # noqa: E402

from verity.agents.reporter import ReporterAgent  # noqa: E402
from verity.github import NoopIssuePublisher  # noqa: E402
from verity.pipeline import VerificationPipeline  # noqa: E402
from verity.sqlite_store import SQLiteJobStore  # noqa: E402


@dataclass
class FixedParser:
    parsed: object

    async def run(self, url: str):
        return self.parsed


@dataclass
class CountingSandbox:
    result: EnvironmentResult
    runs: int = 0

    async def run(self, job_id, parsed_claim, patches, command_override=None):
        self.runs += 1
        return self.result


@dataclass
class CountingDebugger:
    calls: int = 0
    seen: list = field(default_factory=list)

    async def run(self, parsed_claim, failure, prior_patches, attempt):
        from verity.models import DebugProposal

        self.calls += 1
        return DebugProposal(diagnosis=f"attempt {attempt}")


def build(store, parsed, sandbox, debugger):
    return VerificationPipeline(
        store=store,
        parser=FixedParser(parsed),
        environment=sandbox,
        debugger=debugger,
        reporter=ReporterAgent(NoopIssuePublisher()),
    )


async def test_an_incidental_statistic_never_reaches_the_sandbox(tmp_path, parsed_claim) -> None:
    """The Stroke-Data-Analysis case: '11 features' must not cost a container."""
    store = SQLiteJobStore(tmp_path / "v.db")
    parsed = parsed_claim.model_copy(
        update={
            "claim_significance": ClaimSignificance.INCIDENTAL_STATISTIC,
            "significance_reason": "The README describes its input table, not a result.",
        }
    )
    sandbox = CountingSandbox(
        EnvironmentResult(succeeded=True, exit_code=0, phase="metric", duration_seconds=1.0)
    )
    debugger = CountingDebugger()
    job, _ = await store.create_or_get(str(parsed.source_url))
    await build(store, parsed, sandbox, debugger).process(job.id)

    finished = await store.get_job(job.id)
    assert finished is not None and finished.verdict is not None
    assert finished.verdict.status == VerdictStatus.NO_VERIFIABLE_CLAIM_FOUND
    assert finished.verdict.status != VerdictStatus.COULD_NOT_VERIFY
    assert finished.verdict.actual_value is None
    assert sandbox.runs == 0, "nothing should be executed for a claim not worth checking"
    assert debugger.calls == 0
    assert "descriptive statistic" in finished.verdict.summary
    assert "not a result" in finished.verdict.summary or parsed.significance_reason
    store.close()


async def test_a_headline_claim_still_runs_normally(tmp_path, parsed_claim) -> None:
    """The guard must not accidentally block real claims."""
    store = SQLiteJobStore(tmp_path / "v.db")
    sandbox = CountingSandbox(
        EnvironmentResult(
            succeeded=True, exit_code=0, phase="metric", actual_value=90.0, duration_seconds=1.0
        )
    )
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    await build(store, parsed_claim, sandbox, CountingDebugger()).process(job.id)

    finished = await store.get_job(job.id)
    assert finished is not None and finished.verdict is not None
    assert finished.verdict.status == VerdictStatus.VERIFIED
    assert sandbox.runs == 1
    store.close()


async def test_a_blocked_network_is_reported_as_environment_incompatible(
    tmp_path, parsed_claim
) -> None:
    """A repo that downloads data at eval time was never tested — say that, don't blame it."""
    store = SQLiteJobStore(tmp_path / "v.db")
    blocked = EnvironmentResult(
        succeeded=False,
        exit_code=1,
        phase="evaluate",
        stderr="socket.gaierror: [Errno -3] Temporary failure in name resolution",
        duration_seconds=2.0,
    )
    sandbox = CountingSandbox(blocked)
    debugger = CountingDebugger()
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    await build(store, parsed_claim, sandbox, debugger).process(job.id)

    finished = await store.get_job(job.id)
    assert finished is not None and finished.verdict is not None
    assert finished.verdict.status == VerdictStatus.ENVIRONMENT_INCOMPATIBLE
    assert finished.verdict.status != VerdictStatus.COULD_NOT_VERIFY
    assert finished.verdict.actual_value is None
    assert "never tested" in finished.verdict.summary
    assert "not evidence about the claim" in finished.verdict.summary
    assert debugger.calls == 3, "the debug loop still gets its three attempts first"
    store.close()


async def test_a_genuine_failure_is_still_could_not_verify(tmp_path, parsed_claim) -> None:
    """The distinction only holds if ordinary failures keep their own label."""
    store = SQLiteJobStore(tmp_path / "v.db")
    real_failure = EnvironmentResult(
        succeeded=False,
        exit_code=1,
        phase="evaluate",
        stderr="AssertionError: expected 0.92, measured 0.71",
        duration_seconds=2.0,
    )
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    await build(store, parsed_claim, CountingSandbox(real_failure), CountingDebugger()).process(
        job.id
    )

    finished = await store.get_job(job.id)
    assert finished is not None and finished.verdict is not None
    assert finished.verdict.status == VerdictStatus.COULD_NOT_VERIFY
    assert finished.verdict.actual_value is None
    store.close()


async def test_timing_measurement_is_not_called_a_contradiction(parsed_claim) -> None:
    parsed = parsed_claim.model_copy(
        update={
            "claim": parsed_claim.claim.model_copy(
                update={"metric": "median latency", "value": 0.1, "unit": "ms"}
            )
        }
    )
    verdict = await ReporterAgent(NoopIssuePublisher()).run(
        "job-timing",
        parsed,
        EnvironmentResult(
            succeeded=True,
            exit_code=0,
            phase="metric",
            actual_value=0.352,
            duration_seconds=1.0,
        ),
        [],
    )
    assert verdict.status == VerdictStatus.CONDITIONS_NOT_COMPARABLE
    assert verdict.actual_value == 0.352
    assert "not comparable" in verdict.summary
    assert "no verification or contradiction is asserted" in verdict.summary


async def test_failed_process_never_persists_an_intermediate_metric(parsed_claim) -> None:
    verdict = await ReporterAgent(NoopIssuePublisher()).run(
        "job-failed-metric",
        parsed_claim,
        EnvironmentResult(
            succeeded=False,
            exit_code=1,
            phase="evaluate",
            stdout="accuracy: 71.0",
            actual_value=71.0,
            duration_seconds=1.0,
        ),
        [],
    )
    assert verdict.status == VerdictStatus.COULD_NOT_VERIFY
    assert verdict.actual_value is None


# --- every terminal outcome must file its artifact ----------------------------------------
# Proven with a recording double rather than a live GitHub write: the question is whether the
# pipeline *calls* the publisher, and a double answers that exactly as well while touching
# nothing public.


@dataclass
class RecordingPublisher:
    """Stands in for GitHubIssuePublisher and remembers what it was asked to file."""

    calls: list = field(default_factory=list)
    url: str = "https://github.com/ZiyadAzzaz/verity-reports/issues/999"

    async def publish(self, parsed_claim, title: str, body: str) -> str:
        self.calls.append({"title": title, "body": body, "url": str(parsed_claim.source_url)})
        return self.url


class FailingPublisher:
    async def publish(self, parsed_claim, title: str, body: str) -> str:
        raise RuntimeError("publisher unavailable")


def build_with_publisher(store, parsed, sandbox, debugger, publisher):
    return VerificationPipeline(
        store=store,
        parser=FixedParser(parsed),
        environment=sandbox,
        debugger=debugger,
        reporter=ReporterAgent(publisher),
    )


NETWORK_BLOCKED = EnvironmentResult(
    succeeded=False,
    exit_code=1,
    phase="evaluate",
    stderr="socket.gaierror: [Errno -3] Temporary failure in name resolution",
    duration_seconds=2.0,
)
REAL_FAILURE = EnvironmentResult(
    succeeded=False,
    exit_code=1,
    phase="evaluate",
    stderr="AssertionError: expected 0.92, measured 0.71",
    duration_seconds=2.0,
)
SUCCESS = EnvironmentResult(
    succeeded=True, exit_code=0, phase="metric", actual_value=90.0, duration_seconds=1.0
)


@pytest.mark.parametrize(
    "significance,result,expected",
    [
        (ClaimSignificance.INCIDENTAL_STATISTIC, SUCCESS, VerdictStatus.NO_VERIFIABLE_CLAIM_FOUND),
        (ClaimSignificance.HEADLINE_CLAIM, NETWORK_BLOCKED, VerdictStatus.ENVIRONMENT_INCOMPATIBLE),
        (ClaimSignificance.HEADLINE_CLAIM, REAL_FAILURE, VerdictStatus.COULD_NOT_VERIFY),
        (ClaimSignificance.HEADLINE_CLAIM, SUCCESS, VerdictStatus.VERIFIED),
    ],
    ids=["no_verifiable_claim", "environment_incompatible", "could_not_verify", "verified"],
)
async def test_every_outcome_files_an_issue_and_stores_its_url(
    tmp_path, parsed_claim, significance, result, expected
) -> None:
    """The 'View detailed analysis' button is downstream of issue_url being set.

    The two short-circuit outcomes bypass ReporterAgent.run entirely, so without this they
    would silently never file - the button would appear for a verified claim and vanish for
    a no_verifiable_claim_found one, with no obvious reason why.
    """
    store = SQLiteJobStore(tmp_path / "v.db")
    parsed = parsed_claim.model_copy(update={"claim_significance": significance})
    publisher = RecordingPublisher()
    job, _ = await store.create_or_get(str(parsed.source_url))
    await build_with_publisher(
        store, parsed, CountingSandbox(result), CountingDebugger(), publisher
    ).process(job.id)

    finished = await store.get_job(job.id)
    assert finished is not None and finished.verdict is not None
    assert finished.verdict.status == expected
    assert len(publisher.calls) == 1, f"{expected.value} must file exactly one Issue"
    assert str(finished.verdict.issue_url) == publisher.url, "the URL must be stored, not lost"
    assert expected.value in publisher.calls[0]["title"], "the title must name the outcome"
    store.close()


async def test_a_missing_token_degrades_without_losing_the_verdict(tmp_path, parsed_claim) -> None:
    """With NoopIssuePublisher there is no artifact, but the verdict must still be complete."""
    store = SQLiteJobStore(tmp_path / "v.db")
    job, _ = await store.create_or_get(str(parsed_claim.source_url))
    await build(store, parsed_claim, CountingSandbox(SUCCESS), CountingDebugger()).process(job.id)

    finished = await store.get_job(job.id)
    assert finished is not None and finished.verdict is not None
    assert finished.verdict.status == VerdictStatus.VERIFIED
    assert finished.verdict.issue_url is None, "no token means no artifact, and that is fine"
    store.close()


async def test_short_circuit_artifact_failure_is_not_cached_as_complete(
    tmp_path, parsed_claim
) -> None:
    store = SQLiteJobStore(tmp_path / "v.db")
    parsed = parsed_claim.model_copy(
        update={"claim_significance": ClaimSignificance.INCIDENTAL_STATISTIC}
    )
    job, _ = await store.create_or_get(str(parsed.source_url))
    await build_with_publisher(
        store,
        parsed,
        CountingSandbox(SUCCESS),
        CountingDebugger(),
        FailingPublisher(),
    ).process(job.id)

    finished = await store.get_job(job.id)
    assert finished is not None and finished.verdict is not None
    assert finished.status == JobStatus.FAILED
    assert finished.verdict.status == VerdictStatus.NO_VERIFIABLE_CLAIM_FOUND
    assert finished.verdict.artifact_error
    assert finished.error == finished.verdict.artifact_error
    store.close()

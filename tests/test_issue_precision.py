"""The filed Issue must not contradict its own debug trail.

verity-reports#4 said "Fixes applied: None" directly beneath an attempt describing a runner
script being written and applied, and its "Execution evidence" section was several hundred
lines of `git clone` progress with none of the pytest or pip output the diagnosis referenced.

Same class of defect as `failed` vs `could_not_verify` and the hidden attempt cap: a summary
field asserting something the detail beside it disproves.
"""

from __future__ import annotations

import pytest

from verity.github import render_issue
from verity.models import (
    AttemptLog,
    Claim,
    Confidence,
    DebugProposal,
    EnvironmentResult,
    ParsedClaim,
    PatchOperation,
    SourceType,
    Verdict,
    VerdictStatus,
    failure_excerpt,
)

CLONE_NOISE = "\n".join(
    ["Cloning into '/work/repo'..."]
    + [f"Updating files:  {n}% ({n * 5}/584)" for n in range(1, 99)]
)
REAL_ERROR = (
    '  File "/usr/local/lib/python3.11/subprocess.py", line 571, in run\n'
    "    raise CalledProcessError(retcode, process.args,\n"
    "subprocess.CalledProcessError: Command '['pip', 'install', '.']' returned non-zero status 1."
)


def failing_result(stderr: str, stdout: str = "", exit_code: int = 1) -> EnvironmentResult:
    return EnvironmentResult(
        succeeded=False,
        exit_code=exit_code,
        phase="evaluate",
        stderr=stderr,
        stdout=stdout,
        duration_seconds=3.0,
    )


class TestFailureExcerpt:
    def test_clone_progress_is_dropped(self) -> None:
        excerpt = failure_excerpt(failing_result(CLONE_NOISE + "\n" + REAL_ERROR))
        assert "Updating files" not in excerpt
        assert "Cloning into" not in excerpt
        assert "CalledProcessError" in excerpt

    def test_the_tail_is_kept_not_the_head(self) -> None:
        """Errors land at the end. Head truncation was what buried the real output."""
        excerpt = failure_excerpt(failing_result(CLONE_NOISE + "\n" + REAL_ERROR), limit=200)
        assert "CalledProcessError" in excerpt

    def test_stdout_is_used_when_stderr_is_only_noise(self) -> None:
        """pytest reports 'no tests ran' on stdout while stderr holds clone chatter."""
        excerpt = failure_excerpt(
            failing_result(
                CLONE_NOISE, stdout="collected 0 items\nno tests ran in 0.12s", exit_code=5
            )
        )
        assert "no tests ran" in excerpt

    def test_a_run_with_nothing_usable_still_says_something(self) -> None:
        assert "exit code" in failure_excerpt(failing_result(""))


def attempt(number: int, *, with_patch: bool) -> AttemptLog:
    operations = (
        [PatchOperation(kind="write_file", path="run_eval.py", new_text="print(1)")]
        if with_patch
        else []
    )
    return AttemptLog(
        attempt=number,
        error_seen="boom",
        proposal=DebugProposal(
            diagnosis=f"attempt {number}: write a runner", operations=operations
        ),
        outcome=failing_result(CLONE_NOISE + "\n" + REAL_ERROR),
    )


def build_verdict(status: VerdictStatus, fixes: list[str], attempts: list[AttemptLog]) -> Verdict:
    return Verdict(
        status=status,
        confidence=Confidence.HIGH,
        claim=Claim(
            metric="median latency",
            value=0.1,
            unit="ms",
            dataset="twitter.json",
            source_location="README",
        ),
        actual_value=None,
        summary="summary",
        fixes_applied=fixes,
        attempts=attempts,
        evidence=[f"Attempt 1 (evaluate, exit 1): {failure_excerpt(attempts[0].outcome)}"]
        if attempts
        else [],
    )


def parsed() -> ParsedClaim:
    return ParsedClaim(
        claim=Claim(
            metric="median latency",
            value=0.1,
            unit="ms",
            dataset="twitter.json",
            source_location="README",
        ),
        source_url="https://github.com/ijl/orjson",
        source_type=SourceType.GITHUB,
        evidence_excerpt="orjson serializes in 0.1 ms",
    )


class TestFixesSection:
    def test_a_patched_attempt_is_never_reported_as_a_bare_none(self) -> None:
        """The exact regression from verity-reports#4."""
        verdict = build_verdict(
            VerdictStatus.ENVIRONMENT_INCOMPATIBLE,
            ["write_file run_eval.py"],
            [attempt(1, with_patch=True)],
        )
        _title, body = render_issue(verdict, parsed(), "job-1")
        assert "run_eval.py" in body, "an applied patch must be listed"
        assert "### Fixes applied\n\n- None." not in body

    @pytest.mark.parametrize(
        "status", [VerdictStatus.COULD_NOT_VERIFY, VerdictStatus.ENVIRONMENT_INCOMPATIBLE]
    )
    def test_unsuccessful_fixes_are_qualified_not_presented_as_applied(
        self, status: VerdictStatus
    ) -> None:
        verdict = build_verdict(status, ["write_file run_eval.py"], [attempt(1, with_patch=True)])
        _title, body = render_issue(verdict, parsed(), "job-1")
        assert "none produced a reproduction" in body

    def test_a_successful_fix_is_reported_plainly(self) -> None:
        verdict = build_verdict(
            VerdictStatus.VERIFIED, ["write_file run_eval.py"], [attempt(1, with_patch=True)]
        )
        _title, body = render_issue(verdict, parsed(), "job-1")
        assert "### Fixes applied" in body
        assert "none produced a reproduction" not in body

    def test_genuinely_no_patch_says_so_explicitly(self) -> None:
        verdict = build_verdict(VerdictStatus.COULD_NOT_VERIFY, [], [attempt(1, with_patch=False)])
        _title, body = render_issue(verdict, parsed(), "job-1")
        assert "No patch was proposed or applied" in body


class TestEvidenceSection:
    def test_the_rendered_evidence_carries_the_real_error(self) -> None:
        verdict = build_verdict(
            VerdictStatus.ENVIRONMENT_INCOMPATIBLE,
            ["write_file run_eval.py"],
            [attempt(1, with_patch=True)],
        )
        _title, body = render_issue(verdict, parsed(), "job-1")
        section = body.split("### Execution evidence", 1)[1]
        assert "CalledProcessError" in section, "the diagnosis must be checkable against output"
        assert "Updating files" not in section, "clone progress is not evidence of anything"

    def test_long_output_is_collapsed(self) -> None:
        verdict = build_verdict(
            VerdictStatus.COULD_NOT_VERIFY,
            ["write_file run_eval.py"],
            [attempt(1, with_patch=True)],
        )
        _title, body = render_issue(verdict, parsed(), "job-1")
        assert "<details>" in body and "</details>" in body

from __future__ import annotations

import base64
import zlib
from types import SimpleNamespace

import pytest

from verity.cloud_handoff import (
    MAX_RESULT_ENCODED_CHARS,
    RESULT_LOG_PREFIX,
    CloudLoggingLineReader,
    _log_filter_literal,
    decode_request_args,
    decode_result_line,
    encode_request_args,
    encode_result_line,
)
from verity.models import EnvironmentResult, SandboxRequest


def request(parsed_claim) -> SandboxRequest:
    return SandboxRequest(
        run_id="run-123",
        job_id="job-456",
        parsed_claim=parsed_claim,
        timeout_seconds=60,
    )


def test_request_round_trip_is_chunked_and_typed(parsed_claim) -> None:
    expected = request(parsed_claim)

    arguments = encode_request_args(expected)

    assert arguments
    assert decode_request_args(arguments) == expected


def test_request_rejects_reordered_or_foreign_arguments(parsed_claim) -> None:
    arguments = encode_request_args(request(parsed_claim))

    with pytest.raises(ValueError, match="unsupported"):
        decode_request_args(["--github-token=never"])
    if len(arguments) == 1:
        arguments[0] = arguments[0].replace("=1:1:", "=2:1:", 1)
    else:
        arguments.reverse()
    with pytest.raises(ValueError, match="missing, duplicated, or out of order"):
        decode_request_args(arguments)


@pytest.mark.parametrize(
    "arguments,match",
    [
        ([], "required"),
        (["--verity-request-chunk=x:1:data"], "integers"),
        (["--verity-request-chunk=1:2:data"], "count"),
        (["--verity-request-chunk=1:1:not-base64!"], "bounded base64"),
    ],
)
def test_request_rejects_incomplete_or_malformed_envelopes(
    arguments: list[str], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        decode_request_args(arguments)


def test_result_round_trip_is_bound_to_the_run() -> None:
    expected = EnvironmentResult(
        succeeded=False,
        exit_code=1,
        phase="evaluate",
        stderr="benchmark failed",
        duration_seconds=2,
    )

    line = encode_result_line("run-123", expected)

    assert len(line) < MAX_RESULT_ENCODED_CHARS + 100
    assert decode_result_line(line, expected_run_id="run-123") == expected
    with pytest.raises(ValueError, match="different run"):
        decode_result_line(line, expected_run_id="run-elsewhere")


def test_large_result_is_compacted_below_the_logging_limit() -> None:
    result = EnvironmentResult(
        succeeded=False,
        exit_code=1,
        phase="install",
        stdout="x" * 100_000,
        stderr="y" * 100_000,
        diagnostic_files={f"file-{index}.py": "z" * 15_000 for index in range(6)},
        duration_seconds=2,
    )

    line = encode_result_line("run-large", result)
    decoded = decode_result_line(line, expected_run_id="run-large")

    assert len(line) <= MAX_RESULT_ENCODED_CHARS + len("VERITY_SANDBOX_RESULT_V1=")
    assert len(decoded.stdout) <= 40_000
    assert len(decoded.stderr) <= 40_000
    assert len(decoded.diagnostic_files) <= 4


def test_result_rejects_an_appended_compressed_stream() -> None:
    result = EnvironmentResult(
        succeeded=False,
        phase="infrastructure",
        duration_seconds=1,
    )
    line = encode_result_line("run-123", result)
    payload = line.removeprefix(RESULT_LOG_PREFIX)
    compressed = base64.urlsafe_b64decode(payload)
    malicious = base64.urlsafe_b64encode(compressed + zlib.compress(b"{}"))

    with pytest.raises(ValueError, match="bounded base64/zlib"):
        decode_result_line(
            RESULT_LOG_PREFIX + malicious.decode("ascii"),
            expected_run_id="run-123",
        )


def test_log_filter_values_escape_quotes_and_backslashes() -> None:
    assert _log_filter_literal('job"\\name') == 'job\\"\\\\name'


def test_cloud_logging_reader_uses_valid_timestamp_order_and_execution_label() -> None:
    calls: list[dict[str, object]] = []

    class FakeLoggingClient:
        def list_entries(self, **kwargs: object) -> list[SimpleNamespace]:
            calls.append(kwargs)
            return [SimpleNamespace(payload="VERITY_TEST=result")]

    reader = object.__new__(CloudLoggingLineReader)
    reader._project = "verity-506800"
    reader._location = "us-central1"
    reader._job_name = "verity-sandbox"
    reader._client = FakeLoggingClient()

    assert (
        reader.read_line(
            execution_name=(
                "projects/verity-506800/locations/us-central1/jobs/verity-sandbox/"
                "executions/verity-sandbox-fmg7n"
            ),
            prefix="VERITY_TEST=",
        )
        == "VERITY_TEST=result"
    )
    assert calls[0]["order_by"] == "timestamp desc"
    assert 'labels."run.googleapis.com/execution_name"="verity-sandbox-fmg7n"' in str(
        calls[0]["filter_"]
    )
    assert "labels.execution_name" not in str(calls[0]["filter_"])

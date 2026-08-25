"""Credential-free request/result transport for the Cloud Run sandbox.

The trusted pipeline starts one Cloud Run Job execution with a bounded, compressed
``SandboxRequest`` split across command arguments.  The sandbox supervisor prints exactly one
bounded ``EnvironmentResult`` envelope to stdout.  Cloud Run collects stdout without requiring
the task service account to call Cloud Logging; the trusted pipeline reads the envelope back by
the execution label.

The payload is public-source execution data, not an authorization capability.  No API key,
service-account key, bearer token, signed URL, Firestore permission, or callback secret crosses
the sandbox boundary.
"""

from __future__ import annotations

import base64
import json
import time
import zlib
from typing import Literal

from pydantic import BaseModel, ConfigDict

from verity.models import EnvironmentResult, SandboxRequest

REQUEST_ARG_PREFIX = "--verity-request-chunk="
RESULT_LOG_PREFIX = "VERITY_SANDBOX_RESULT_V1="

# Cloud Run supports 1,000 arguments.  Staying below 100 KiB also leaves ample headroom for the
# execution request and the platform's process argv.  Each chunk is deliberately below the
# documented 32 KiB per-environment-variable limit even though this transport uses argv.
REQUEST_CHUNK_CHARS = 24_000
MAX_REQUEST_ENCODED_CHARS = 96_000

# Cloud Logging accepts entries up to 256 KiB.  Keep a large safety margin for its envelope and
# platform metadata; stdout/stderr are compacted before encoding when necessary.
MAX_RESULT_ENCODED_CHARS = 160_000
MAX_DECOMPRESSED_BYTES = 1_000_000


class SandboxResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: Literal[1] = 1
    run_id: str
    result: EnvironmentResult


def _encode_json(value: dict[str, object]) -> str:
    raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(zlib.compress(raw, level=9)).decode("ascii")


def _decode_json(payload: str) -> bytes:
    try:
        compressed = base64.b64decode(payload, altchars=b"-_", validate=True)
        decompressor = zlib.decompressobj()
        raw = decompressor.decompress(compressed, MAX_DECOMPRESSED_BYTES + 1)
        if (
            len(raw) > MAX_DECOMPRESSED_BYTES
            or decompressor.unconsumed_tail
            or decompressor.unused_data
            or not decompressor.eof
        ):
            raise ValueError("cloud handoff payload exceeds the decompressed size limit")
        return raw
    except (ValueError, zlib.error) as exc:
        raise ValueError("cloud handoff payload is not valid bounded base64/zlib data") from exc


def encode_request_args(request: SandboxRequest) -> list[str]:
    """Serialize a request into ordered Cloud Run command-argument chunks."""

    payload = _encode_json(request.model_dump(mode="json"))
    if len(payload) > MAX_REQUEST_ENCODED_CHARS:
        raise ValueError(
            "sandbox request is too large for the credential-free Cloud Run handoff "
            f"({len(payload)} > {MAX_REQUEST_ENCODED_CHARS} encoded characters)"
        )
    chunks = [
        payload[offset : offset + REQUEST_CHUNK_CHARS]
        for offset in range(0, len(payload), REQUEST_CHUNK_CHARS)
    ]
    total = len(chunks)
    return [
        f"{REQUEST_ARG_PREFIX}{index + 1}:{total}:{chunk}" for index, chunk in enumerate(chunks)
    ]


def decode_request_args(arguments: list[str]) -> SandboxRequest:
    """Reassemble a request while rejecting missing, duplicate, or reordered chunks."""

    chunks: list[tuple[int, int, str]] = []
    for argument in arguments:
        if not argument.startswith(REQUEST_ARG_PREFIX):
            raise ValueError("sandbox received an unsupported command argument")
        header, separator, chunk = argument[len(REQUEST_ARG_PREFIX) :].partition(":")
        total_text, separator_two, chunk = chunk.partition(":")
        if not separator or not separator_two:
            raise ValueError("sandbox request chunk header is malformed")
        try:
            index = int(header)
            total = int(total_text)
        except ValueError as exc:
            raise ValueError("sandbox request chunk indexes must be integers") from exc
        chunks.append((index, total, chunk))

    if not chunks:
        raise ValueError("sandbox request arguments are required")
    expected_total = chunks[0][1]
    if expected_total < 1 or expected_total > 4 or len(chunks) != expected_total:
        raise ValueError("sandbox request chunk count is invalid")
    if any(total != expected_total for _, total, _ in chunks):
        raise ValueError("sandbox request chunks disagree about their total")
    if [index for index, _, _ in chunks] != list(range(1, expected_total + 1)):
        raise ValueError("sandbox request chunks are missing, duplicated, or out of order")

    payload = "".join(chunk for _, _, chunk in chunks)
    if len(payload) > MAX_REQUEST_ENCODED_CHARS:
        raise ValueError("sandbox request exceeds the encoded size limit")
    return SandboxRequest.model_validate_json(_decode_json(payload))


def _compact_result(result: EnvironmentResult, limit: int) -> EnvironmentResult:
    """Retain the most useful tail of logs while fitting one Cloud Logging entry."""

    diagnostics = {
        path: content[: min(4_000, limit)]
        for path, content in list(result.diagnostic_files.items())[:4]
    }
    return result.model_copy(
        update={
            "stdout": result.stdout[-limit:],
            "stderr": result.stderr[-limit:],
            "metric_evidence": (
                result.metric_evidence[-2_000:] if result.metric_evidence else None
            ),
            "diagnostic_files": diagnostics,
        }
    )


def encode_result_line(run_id: str, result: EnvironmentResult) -> str:
    """Return the single stdout line consumed by the trusted pipeline."""

    for text_limit in (40_000, 20_000, 8_000, 2_000):
        compact = _compact_result(result, text_limit)
        envelope = SandboxResultEnvelope(run_id=run_id, result=compact)
        payload = _encode_json(envelope.model_dump(mode="json"))
        if len(payload) <= MAX_RESULT_ENCODED_CHARS:
            return RESULT_LOG_PREFIX + payload
    raise ValueError("sandbox result cannot fit in one bounded Cloud Logging entry")


def decode_result_line(line: str, *, expected_run_id: str) -> EnvironmentResult:
    """Validate a result log line and bind it to the request that launched the execution."""

    if not line.startswith(RESULT_LOG_PREFIX):
        raise ValueError("log entry is not a Verity sandbox result")
    payload = line[len(RESULT_LOG_PREFIX) :].strip()
    if len(payload) > MAX_RESULT_ENCODED_CHARS:
        raise ValueError("sandbox result exceeds the encoded size limit")
    envelope = SandboxResultEnvelope.model_validate_json(_decode_json(payload))
    if envelope.run_id != expected_run_id:
        raise ValueError("sandbox result belongs to a different run")
    return envelope.result


def _log_filter_literal(value: str) -> str:
    """Escape a value embedded in a Cloud Logging advanced filter string."""

    return value.replace("\\", "\\\\").replace('"', '\\"')


class CloudLoggingLineReader:
    """Read one prefixed stdout line for one exact Cloud Run execution."""

    def __init__(self, *, project: str, location: str, job_name: str) -> None:
        from google.cloud import logging as cloud_logging

        self._project = project
        self._location = location
        self._job_name = job_name
        self._client = cloud_logging.Client(project=project)  # type: ignore[no-untyped-call]

    def read_line(
        self,
        *,
        execution_name: str,
        prefix: str,
        timeout_seconds: float = 60,
    ) -> str:
        execution_id = execution_name.rsplit("/", 1)[-1]
        if not execution_id:
            raise ValueError("Cloud Run returned an empty execution name")
        project = _log_filter_literal(self._project)
        location = _log_filter_literal(self._location)
        job_name = _log_filter_literal(self._job_name)
        execution_id = _log_filter_literal(execution_id)
        log_filter = (
            'resource.type="cloud_run_job" '
            f'AND resource.labels.project_id="{project}" '
            f'AND resource.labels.location="{location}" '
            f'AND resource.labels.job_name="{job_name}" '
            f'AND labels.execution_name="{execution_id}" '
            f'AND logName="projects/{project}/logs/run.googleapis.com%2Fstdout"'
        )

        deadline = time.monotonic() + timeout_seconds
        delay = 0.5
        while True:
            entries = self._client.list_entries(  # type: ignore[no-untyped-call]
                resource_names=[f"projects/{self._project}"],
                filter_=log_filter,
                order_by="DESCENDING",
                page_size=100,
            )
            for entry in entries:
                payload = getattr(entry, "payload", None)
                if isinstance(payload, str) and payload.startswith(prefix):
                    return payload
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Cloud Run execution completed but its expected stdout envelope did not "
                    f"become available within {timeout_seconds:.0f} seconds."
                )
            time.sleep(delay)
            delay = min(delay * 2, 5)


class CloudLoggingResultReader(CloudLoggingLineReader):
    """Read and validate the sandbox result for one exact Cloud Run execution."""

    def read(
        self,
        *,
        execution_name: str,
        run_id: str,
        timeout_seconds: float = 60,
    ) -> EnvironmentResult:
        line = self.read_line(
            execution_name=execution_name,
            prefix=RESULT_LOG_PREFIX,
            timeout_seconds=timeout_seconds,
        )
        return decode_result_line(line, expected_run_id=run_id)

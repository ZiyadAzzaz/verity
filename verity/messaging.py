"""Job queue adapters and Pub/Sub envelope decoding.

Both adapters implement :class:`verity.interfaces.JobQueue`. Intake never waits for a
benchmark in either environment; only the mechanism differs.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging

from verity.interfaces import JobHandler, JobQueue

logger = logging.getLogger(__name__)


class AsyncioJobQueue(JobQueue):
    """In-process queue with a bounded pool of background consumers.

    Intended for local development, and honest about it: an ``asyncio.Queue`` lives in one
    process, so jobs still queued when that process exits are lost. The SQLite store keeps
    those jobs visible as ``queued`` rather than silently dropping them, and re-publishing
    a job id is safe because ``claim_job`` rejects the second delivery.

    ``concurrency`` is what keeps a demo from starting eight ``docker run`` benchmarks at
    once on a laptop.
    """

    def __init__(self, *, concurrency: int = 1, maxsize: int = 0) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=maxsize)
        self._concurrency = concurrency
        self._workers: list[asyncio.Task[None]] = []

    async def publish(self, job_id: str, source_url: str) -> None:
        await self._queue.put(job_id)

    async def consume(self, handler: JobHandler) -> None:
        if self._workers:
            return
        self._workers = [
            asyncio.create_task(self._worker(handler), name=f"verity-consumer-{index}")
            for index in range(self._concurrency)
        ]

    async def _worker(self, handler: JobHandler) -> None:
        while True:
            job_id = await self._queue.get()
            try:
                await handler(job_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                # The pipeline already records failures against the job; a consumer that
                # dies here would silently stop every later verification.
                logger.exception("Job handler raised", extra={"job_id": job_id})
            finally:
                self._queue.task_done()

    async def join(self) -> None:
        """Wait until every published job has been handled. Used by tests and scripts."""
        await self._queue.join()

    async def close(self) -> None:
        for worker in self._workers:
            worker.cancel()
        for worker in self._workers:
            with contextlib.suppress(asyncio.CancelledError):
                await worker
        self._workers = []


class PubSubJobQueue(JobQueue):
    """Google Cloud Pub/Sub publisher for the deployed pipeline.

    Delivery is a *push* subscription to ``POST /internal/pubsub``, so ``consume`` has
    nothing to start in-process: Cloud Run hands each message to the API, which calls the
    pipeline launcher. The method exists so the two environments share one interface.
    """

    def __init__(self, project: str, topic: str, *, publish_timeout_seconds: float = 30) -> None:
        from google.cloud import pubsub_v1  # type: ignore[attr-defined]

        if publish_timeout_seconds <= 0:
            raise ValueError("publish_timeout_seconds must be positive")
        self._client = pubsub_v1.PublisherClient()
        self._topic_path = self._client.topic_path(project, topic)
        self._publish_timeout = publish_timeout_seconds
        self._closed = False

    async def publish(self, job_id: str, source_url: str) -> None:
        if self._closed:
            raise RuntimeError("Pub/Sub publisher is closed")
        payload = json.dumps(
            {"job_id": job_id, "source_url": source_url}, separators=(",", ":")
        ).encode("utf-8")
        future = self._client.publish(
            self._topic_path,
            payload,
            job_id=job_id,
            content_type="application/json",
        )
        await asyncio.to_thread(future.result, timeout=self._publish_timeout)

    async def consume(self, handler: JobHandler) -> None:
        logger.info("Pub/Sub delivery is push-based; no in-process consumer is started")

    async def close(self) -> None:
        """Stop publisher workers and reject future publishes during shutdown."""
        if not self._closed:
            self._client.stop()
            self._closed = True


def decode_push_envelope(envelope: dict[str, object]) -> tuple[str, str | None]:
    message = envelope.get("message")
    if not isinstance(message, dict):
        raise ValueError("Pub/Sub envelope is missing message")
    encoded = message.get("data")
    if not isinstance(encoded, str):
        raise ValueError("Pub/Sub message is missing base64 data")
    try:
        decoded = base64.b64decode(encoded, validate=True)
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Pub/Sub data is not valid base64 JSON") from exc
    job_id = payload.get("job_id") if isinstance(payload, dict) else None
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("Pub/Sub payload is missing job_id")
    message_id = message.get("messageId") or message.get("message_id")
    return job_id, str(message_id) if message_id else None

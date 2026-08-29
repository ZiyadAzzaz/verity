"""Integration tests against Google's official Firestore and Pub/Sub emulators.

Run through ``scripts/test_emulators.ps1``. Ordinary pytest runs skip this module unless both
standard emulator host variables are present, so no test can accidentally contact Google Cloud.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid

import pytest
from google.cloud import pubsub_v1

from verity.messaging import PubSubJobQueue, decode_push_envelope
from verity.models import (
    Confidence,
    EnvironmentResult,
    JobStatus,
    SandboxRequest,
    SandboxRun,
    Verdict,
    VerdictStatus,
)
from verity.store import FirestoreJobStore, claim_key

FIRESTORE_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST")
PUBSUB_HOST = os.environ.get("PUBSUB_EMULATOR_HOST")
PROJECT = os.environ.get("VERITY_EMULATOR_PROJECT", "verity-emulator-test")

pytestmark = [
    pytest.mark.emulator,
    pytest.mark.skipif(
        not FIRESTORE_HOST or not PUBSUB_HOST,
        reason="official Firestore and Pub/Sub emulators are not running",
    ),
]


def _verdict(parsed_claim) -> Verdict:
    return Verdict(
        status=VerdictStatus.VERIFIED,
        confidence=Confidence.HIGH,
        claim=parsed_claim.claim,
        actual_value=parsed_claim.claim.value,
        summary="The emulator-backed reproduction matched the claim.",
        evidence=["official-emulator-round-trip"],
    )


async def test_firestore_real_transactions_are_atomic_and_deduplicated(parsed_claim) -> None:
    store = FirestoreJobStore(PROJECT)
    canonical_url = f"https://example.com/emulator/{uuid.uuid4().hex}"
    try:
        reservations = await asyncio.wait_for(
            asyncio.gather(*(store.create_or_get(canonical_url) for _ in range(4))),
            timeout=60,
        )

        assert sum(created for _job, created in reservations) == 1
        assert len({job.id for job, _created in reservations}) == 1
        job = reservations[0][0]

        claims = await asyncio.wait_for(
            asyncio.gather(*(store.claim_job(job.id) for _ in range(3))),
            timeout=60,
        )
        assert claims.count(True) == 1
        assert claims.count(False) == 2

        await store.update_job(
            job.id,
            status=JobStatus.REPORTING,
            parsed_claim=parsed_claim,
        )
        first_trace = await store.append_trace(
            job.id,
            agent="environment",
            action="emulator.execution",
            detail={"nested": {"safe": True}, "values": [1, 2, 3]},
        )
        second_trace = await store.append_trace(
            job.id,
            agent="reporter",
            action="emulator.completed",
        )
        assert first_trace.sequence <= second_trace.sequence

        verdict = _verdict(parsed_claim)
        completed = await asyncio.wait_for(store.complete_job(job.id, verdict), timeout=60)

        job_snapshot, memory_snapshot = await asyncio.gather(
            store._db.collection("jobs").document(job.id).get(),
            store._db.collection("claim_memory").document(claim_key(canonical_url)).get(),
        )
        assert job_snapshot.get("status") == JobStatus.COMPLETED.value
        assert memory_snapshot.get("status") == JobStatus.COMPLETED.value
        assert memory_snapshot.get("job_id") == job.id
        assert completed.verdict == verdict

        cached = await store.find_cached_result(canonical_url)
        assert cached is not None
        assert cached.id == job.id
        assert cached.cached is True
        repeated, created = await store.create_or_get(canonical_url)
        assert created is False
        assert repeated.id == job.id
        assert repeated.cached is True

        trace = await store.get_trace(job.id)
        assert [event.sequence for event in trace] == [0, 1]
        assert trace[0].detail == {"nested": {"safe": True}, "values": [1, 2, 3]}
    finally:
        store.close()


async def test_firestore_failed_reservation_and_sandbox_models_round_trip(parsed_claim) -> None:
    store = FirestoreJobStore(PROJECT)
    canonical_url = f"https://example.com/retry/{uuid.uuid4().hex}"
    try:
        failed, created = await store.create_or_get(canonical_url)
        assert created is True
        await store.update_job(failed.id, status=JobStatus.FAILED, error="controlled failure")

        replacement, replacement_created = await store.create_or_get(canonical_url)
        assert replacement_created is True
        assert replacement.id != failed.id

        # Standard-edition Firestore forbids an array directly containing another array.
        # Real parser output can contain multiple argv arrays, so this must exercise the codec
        # against Google's emulator rather than only a permissive fake document.
        parsed_with_commands = parsed_claim.model_copy(
            update={
                "execution": parsed_claim.execution.model_copy(
                    update={
                        "install_commands": [
                            ["python", "-m", "pip", "install", "networkx"],
                            ["python", "-m", "pip", "install", "scikit-learn"],
                        ]
                    }
                )
            }
        )
        await store.update_job(replacement.id, parsed_claim=parsed_with_commands)
        persisted = await store.get_job(replacement.id)
        assert persisted is not None
        assert persisted.parsed_claim == parsed_with_commands

        request = SandboxRequest(
            run_id=uuid.uuid4().hex,
            job_id=replacement.id,
            parsed_claim=parsed_with_commands,
            timeout_seconds=30,
        )
        run = SandboxRun(request=request)
        result = EnvironmentResult(
            succeeded=True,
            exit_code=0,
            phase="metric",
            stdout="accuracy: 90.0",
            actual_value=90.0,
            metric_evidence="accuracy: 90.0",
            duration_seconds=1.25,
            repository_commit="a" * 40,
        )

        await store.create_sandbox_run(run)
        assert await store.get_sandbox_run(request.run_id) == run
        await store.complete_sandbox_run(request.run_id, result)
        completed_run = await store.get_sandbox_run(request.run_id)
        assert completed_run is not None
        assert completed_run.result == result
        assert completed_run.completed_at is not None
    finally:
        store.close()


async def test_pubsub_publish_pull_decode_ack_and_duplicate_claim(parsed_claim) -> None:
    suffix = uuid.uuid4().hex
    topic_id = f"verity-jobs-{suffix}"
    subscription_id = f"verity-worker-{suffix}"
    publisher_admin = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    topic_path = publisher_admin.topic_path(PROJECT, topic_id)
    subscription_path = subscriber.subscription_path(PROJECT, subscription_id)
    queue = PubSubJobQueue(PROJECT, topic_id, publish_timeout_seconds=10)
    store = FirestoreJobStore(PROJECT)
    try:
        await asyncio.to_thread(publisher_admin.create_topic, request={"name": topic_path})
        await asyncio.to_thread(
            subscriber.create_subscription,
            request={
                "name": subscription_path,
                "topic": topic_path,
                "ack_deadline_seconds": 10,
            },
        )
        job, created = await store.create_or_get(f"https://example.com/pubsub/{uuid.uuid4().hex}")
        assert created is True

        await queue.publish(job.id, job.canonical_url)
        response = await asyncio.to_thread(
            subscriber.pull,
            request={"subscription": subscription_path, "max_messages": 1},
            timeout=15,
        )
        assert len(response.received_messages) == 1
        received = response.received_messages[0]
        payload = json.loads(received.message.data)
        assert payload == {"job_id": job.id, "source_url": job.canonical_url}
        assert received.message.attributes == {
            "job_id": job.id,
            "content_type": "application/json",
        }

        envelope = {
            "message": {
                "data": base64.b64encode(received.message.data).decode("ascii"),
                "messageId": received.message.message_id,
            }
        }
        decoded_job_id, message_id = decode_push_envelope(envelope)
        assert decoded_job_id == job.id
        assert message_id == received.message.message_id

        # Pub/Sub is at-least-once. The Firestore transaction is the idempotency boundary:
        # even if the same decoded delivery reaches two workers, only one can claim it.
        first_claim, duplicate_claim = await asyncio.gather(
            store.claim_job(decoded_job_id),
            store.claim_job(decoded_job_id),
        )
        assert sorted((first_claim, duplicate_claim)) == [False, True]

        await asyncio.to_thread(
            subscriber.acknowledge,
            request={
                "subscription": subscription_path,
                "ack_ids": [received.ack_id],
            },
        )
        empty = await asyncio.to_thread(
            subscriber.pull,
            request={"subscription": subscription_path, "max_messages": 1},
            timeout=2,
            retry=None,
        )
        assert list(empty.received_messages) == []
    finally:
        await queue.close()
        publisher_admin.stop()
        subscriber.close()
        store.close()

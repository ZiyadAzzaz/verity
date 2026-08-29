"""Firestore adapter contracts that do not need a live cloud project."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from verity.models import (
    Claim,
    Confidence,
    ExecutionPlan,
    JobRecord,
    JobStatus,
    ParsedClaim,
    SourceType,
    Verdict,
    VerdictStatus,
)
from verity.store import FirestoreJobStore, _firestore_decode, _firestore_encode, claim_key


@dataclass
class FakeSnapshot:
    value: dict[str, Any] | None

    @property
    def exists(self) -> bool:
        return self.value is not None

    def to_dict(self) -> dict[str, Any] | None:
        return self.value


@dataclass
class FakeDocument:
    collection: str
    document_id: str
    value: dict[str, Any] | None = None

    async def get(self, *, transaction: Any = None) -> FakeSnapshot:
        assert transaction is not None
        return FakeSnapshot(self.value)


@dataclass
class FakeCollection:
    name: str
    documents: dict[tuple[str, str], FakeDocument]

    def document(self, document_id: str) -> FakeDocument:
        return self.documents.setdefault(
            (self.name, document_id), FakeDocument(self.name, document_id)
        )


@dataclass
class FakeTransaction:
    writes: list[tuple[str, FakeDocument, dict[str, Any], bool | None]] = field(
        default_factory=list
    )

    def update(self, ref: FakeDocument, value: dict[str, Any]) -> None:
        self.writes.append(("update", ref, value, None))

    def set(self, ref: FakeDocument, value: dict[str, Any], *, merge: bool = False) -> None:
        self.writes.append(("set", ref, value, merge))


@dataclass
class FakeDatabase:
    documents: dict[tuple[str, str], FakeDocument] = field(default_factory=dict)
    transaction_instance: FakeTransaction = field(default_factory=FakeTransaction)

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(name, self.documents)

    def transaction(self) -> FakeTransaction:
        return self.transaction_instance


class FakeFirestoreModule:
    @staticmethod
    def async_transactional(function):
        async def invoke(transaction):
            return await function(transaction)

        return invoke


def test_nested_command_arrays_round_trip_through_firestore_codec() -> None:
    parsed = ParsedClaim(
        claim=Claim(
            metric="accuracy",
            value=88.9,
            unit="%",
            dataset="deterministic fixture",
            source_location="README benchmark table",
        ),
        source_url="https://github.com/example/benchmark",
        source_type=SourceType.GITHUB,
        evidence_excerpt="The benchmark reports 88.9% accuracy.",
        execution=ExecutionPlan(
            repository_url="https://github.com/example/benchmark",
            install_commands=[
                ["python", "-m", "pip", "install", "networkx"],
                ["python", "-m", "pip", "install", "scikit-learn"],
            ],
            evaluation_command=["python", "src/benchmark.py"],
        ),
    )

    encoded = _firestore_encode(parsed)

    def assert_no_direct_nested_array(value: Any) -> None:
        if isinstance(value, list):
            assert not any(isinstance(item, list) for item in value)
            for item in value:
                assert_no_direct_nested_array(item)
        elif isinstance(value, dict):
            for item in value.values():
                assert_no_direct_nested_array(item)

    assert_no_direct_nested_array(encoded)
    assert _firestore_decode(encoded) == parsed.model_dump(mode="json")


async def test_verdict_and_claim_memory_complete_in_one_transaction() -> None:
    job = JobRecord(
        id="job-1",
        canonical_url="https://example.com/claim",
        source_url="https://example.com/claim",
        status=JobStatus.REPORTING,
    )
    verdict = Verdict(
        status=VerdictStatus.VERIFIED,
        confidence=Confidence.HIGH,
        claim=Claim(
            metric="accuracy",
            value=90.0,
            dataset="fixture",
            source_location="README",
        ),
        actual_value=90.0,
        summary="Matched.",
    )
    database = FakeDatabase()
    database.documents[("jobs", job.id)] = FakeDocument("jobs", job.id, job.model_dump(mode="json"))
    store = FirestoreJobStore.__new__(FirestoreJobStore)
    store._db = database
    store._firestore = FakeFirestoreModule

    completed = await store.complete_job(job.id, verdict)

    assert completed.status is JobStatus.COMPLETED
    assert completed.verdict == verdict
    writes = database.transaction_instance.writes
    assert [(kind, ref.collection) for kind, ref, _value, _merge in writes] == [
        ("update", "jobs"),
        ("set", "claim_memory"),
    ]
    assert writes[1][1].document_id == claim_key(job.canonical_url)
    assert writes[1][3] is True

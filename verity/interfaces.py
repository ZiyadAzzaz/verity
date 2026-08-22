"""The infrastructure seam.

Every piece of Verity's agent logic depends on the abstractions declared here and on
nothing else. SQLite, Docker, Firestore, Pub/Sub, Cloud Run, and the Gemini SDK are
imported *only* inside the concrete adapters that implement these interfaces, and the
adapter set is chosen once at startup from a single ``VERITY_ENV`` value.

The three interfaces named in the local-first pivot are :class:`JobStore`,
:class:`JobQueue`, and :class:`ModelClient`. They are declared with ``async`` methods and
Pydantic models instead of the sketch's synchronous ``dict`` signatures: the pipeline is
already fully asynchronous and the typed contracts in :mod:`verity.models` are what make
"never fabricate a verdict" checkable by mypy. The semantics are unchanged.

:class:`SandboxBackend` is the fourth seam — the one that keeps untrusted third-party code
off the host — and it is declared here for the same reason.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from verity.models import (
    EnvironmentResult,
    JobRecord,
    ParsedClaim,
    PatchOperation,
    SandboxRun,
    TraceEvent,
    Verdict,
)

if TYPE_CHECKING:
    from verity.source import SourceDocument

SchemaT = TypeVar("SchemaT", bound=BaseModel)

#: A queue consumer receives a job id and drives that job to a terminal state.
JobHandler = Callable[[str], Awaitable[None]]


class JobStore(ABC):
    """Job state, the append-only trace log, and the memory bank of past verifications.

    Implementations must be safe to call concurrently from multiple pipeline tasks and
    must treat ``canonical_url`` (see :func:`verity.security.canonicalize_url`) as the
    deduplication key, hashed by :func:`claim_key`.
    """

    # --- job lifecycle -------------------------------------------------------

    @abstractmethod
    async def create_or_get(self, canonical_url: str) -> tuple[JobRecord, bool]:
        """Reserve a job for ``canonical_url``.

        Returns ``(job, created)``. When ``created`` is ``False`` the returned record is
        an existing non-failed job for the same claim, and ``job.cached`` reports whether
        it already carries a finished verdict.
        """

    @abstractmethod
    async def get_job(self, job_id: str) -> JobRecord | None: ...

    @abstractmethod
    async def claim_job(self, job_id: str) -> bool:
        """Atomically move a queued job into processing. ``False`` means someone else won.

        This is what makes redelivery — an at-least-once queue, a retried Pub/Sub push, a
        restarted worker — safe to ignore instead of re-running a benchmark.
        """

    @abstractmethod
    async def update_job(self, job_id: str, **changes: Any) -> JobRecord: ...

    @abstractmethod
    async def complete_job(self, job_id: str, verdict: Verdict) -> JobRecord:
        """Persist the verdict and write it into the claim-memory bank."""

    @abstractmethod
    async def find_cached_result(self, canonical_url: str) -> JobRecord | None:
        """Return a previously completed job for this claim, or ``None``.

        Lookup is by ``claim_key(canonical_url)``. Only jobs that reached a verdict are
        returned; a failed or in-flight job is not a cached result.
        """

    # --- trace ---------------------------------------------------------------

    @abstractmethod
    async def append_trace(
        self, job_id: str, *, agent: str, action: str, detail: dict[str, Any] | None = None
    ) -> TraceEvent: ...

    @abstractmethod
    async def get_trace(self, job_id: str) -> list[TraceEvent]: ...

    # --- sandbox run handoff -------------------------------------------------

    @abstractmethod
    async def create_sandbox_run(self, run: SandboxRun) -> None: ...

    @abstractmethod
    async def get_sandbox_run(self, run_id: str) -> SandboxRun | None: ...

    @abstractmethod
    async def complete_sandbox_run(self, run_id: str, result: EnvironmentResult) -> None: ...

    # --- convenience ---------------------------------------------------------

    async def create_job(self, claim_url: str) -> str:
        """Convenience wrapper matching the pivot sketch: return only the job id."""
        job, _created = await self.create_or_get(claim_url)
        return job.id


class JobQueue(ABC):
    """Decouples job intake from job processing.

    ``publish`` must return as soon as the job is durably (or, locally, reliably) handed
    off — never after the benchmark finishes. HTTP intake stays non-blocking either way.
    """

    @abstractmethod
    async def publish(self, job_id: str, source_url: str) -> None: ...

    @abstractmethod
    async def consume(self, handler: JobHandler) -> None:
        """Start delivering published job ids to ``handler``. Returns once started."""

    async def close(self) -> None:
        """Stop consuming and release resources. Safe to call when never started."""
        return None


class ModelClient(ABC):
    """Gemini calls: claim extraction, patch proposals, verdict prose.

    Implementations own their own retry/backoff. The free AI Studio tier has real rate
    limits and the Debug Agent's bounded retry loop calls this repeatedly.
    """

    @abstractmethod
    async def generate(self, prompt: str, files: list[SourceDocument] | None = None) -> str:
        """Single-turn free-text generation."""

    @abstractmethod
    async def generate_structured(
        self,
        *,
        instruction: str,
        prompt: str,
        schema: type[SchemaT],
        document: SourceDocument | None = None,
    ) -> SchemaT:
        """Single-turn generation validated against ``schema``.

        This is what the Parser and Debug agents use: a response that does not satisfy
        the typed contract is an error, not something to be coerced into a verdict.
        """


class SandboxBackend(ABC):
    """Executes untrusted third-party code away from the host.

    Every implementation must be an actual isolation boundary. The Environment Agent
    holds one of these and nothing else.
    """

    @abstractmethod
    async def run(
        self,
        job_id: str,
        parsed_claim: ParsedClaim,
        patches: list[PatchOperation],
        command_override: list[str] | None,
    ) -> EnvironmentResult: ...

    async def preflight(self) -> None:
        """Raise :class:`SandboxUnavailableError` if the backend cannot run jobs.

        Called once at startup so a missing Docker daemon is a clear setup error rather
        than a mid-verification failure that the Debug Agent would try to patch.
        """
        return None


class SandboxUnavailableError(RuntimeError):
    """The execution backend is not usable — a setup problem, not a claim failure."""


__all__ = [
    "JobHandler",
    "JobQueue",
    "JobStore",
    "ModelClient",
    "SandboxBackend",
    "SandboxUnavailableError",
    "SchemaT",
]

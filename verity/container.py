"""Adapter selection.

This is the only module that imports concrete infrastructure. It reads ``VERITY_ENV``
once, picks one adapter per seam, and hands the rest of the system nothing but the
interfaces from :mod:`verity.interfaces`.

Flipping ``VERITY_ENV=local`` to ``VERITY_ENV=cloud`` changes the four lines below and
nothing else — no agent, no pipeline step, and no test touches SQLite, Docker, Firestore,
Pub/Sub, or Cloud Run directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from verity.agents import DebugAgent, EnvironmentAgent, ParserAgent, ReporterAgent
from verity.agents.environment import (
    CloudRunJobBackend,
    DockerLimits,
    DockerSandboxBackend,
    LocalSandboxBackend,
)
from verity.config import Settings
from verity.github import GitHubIssuePublisher, IssuePublisher, NoopIssuePublisher
from verity.interfaces import JobQueue, JobStore, ModelClient, SandboxBackend
from verity.launcher import CloudRunPipelineLauncher, DirectPipelineLauncher, PipelineLauncher
from verity.llm import GeminiAIStudioClient, VertexAIModelClient
from verity.messaging import AsyncioJobQueue, PubSubJobQueue
from verity.orchestrator import Orchestrator
from verity.pipeline import VerificationPipeline
from verity.source import SourceFetcher
from verity.store import FirestoreJobStore, MemoryJobStore

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Container:
    settings: Settings
    store: JobStore
    queue: JobQueue
    model: ModelClient
    sandbox: SandboxBackend
    pipeline: VerificationPipeline
    launcher: PipelineLauncher
    orchestrator: Orchestrator
    started: bool = field(default=False)

    async def startup(self) -> None:
        """Start the queue consumer. Called from the API lifespan and by scripts."""
        if self.started:
            return
        await self.queue.consume(self.pipeline.process)
        self.started = True

    async def shutdown(self) -> None:
        await self.queue.close()
        # Concrete durable stores can hold SQLite handles or Firestore HTTP resources.
        close = getattr(self.store, "close", None)
        if callable(close):
            close()
        self.started = False

    async def preflight(self) -> None:
        """Fail loudly at startup rather than mid-verification.

        A stopped Docker daemon or a missing API key is a setup problem. Discovering it
        three minutes into a benchmark would hand the Debug Agent an infrastructure error
        to "fix", which is exactly the kind of confusion Verity is supposed to avoid.
        """
        await self.sandbox.preflight()
        if self.settings.llm == "ai_studio" and not self.settings.gemini_api_key:
            import os

            if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Create a free Google AI Studio key at "
                    "https://aistudio.google.com/ and add it to .env — no billing "
                    "account or GCP project is required for VERITY_ENV=local."
                )


def build_store(settings: Settings) -> JobStore:
    if settings.store == "firestore":
        return FirestoreJobStore(settings.google_cloud_project)
    if settings.store == "sqlite":
        from verity.sqlite_store import SQLiteJobStore

        return SQLiteJobStore(settings.sqlite_path)
    return MemoryJobStore()


def build_queue(settings: Settings) -> JobQueue:
    if settings.messaging == "pubsub":
        if not settings.google_cloud_project:
            raise ValueError("Pub/Sub requires GOOGLE_CLOUD_PROJECT")
        return PubSubJobQueue(settings.google_cloud_project, settings.pubsub_topic)
    return AsyncioJobQueue(concurrency=settings.queue_concurrency)


def build_model_client(settings: Settings) -> ModelClient:
    if settings.llm == "vertex":
        return VertexAIModelClient(
            settings.gemini_model,
            project=settings.google_cloud_project,
            location=settings.google_cloud_vertex_location,
        )
    return GeminiAIStudioClient(settings.gemini_model, api_key=settings.gemini_api_key)


def build_sandbox(settings: Settings, store: JobStore) -> SandboxBackend:
    if settings.sandbox == "cloud_run":
        if not settings.google_cloud_project:
            raise ValueError("Cloud Run sandbox requires GOOGLE_CLOUD_PROJECT")
        return CloudRunJobBackend(
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            job_name=settings.cloud_run_sandbox_job,
            store=store,
            timeout_seconds=settings.execution_timeout_seconds,
            allowed_repo_hosts=settings.allowed_repo_hosts,
        )
    if settings.sandbox == "host_subprocess":
        logger.warning(
            "VERITY_SANDBOX_BACKEND=host_subprocess runs untrusted third-party code "
            "directly on this machine with no isolation. Use it only against "
            "repositories you already trust."
        )
        return LocalSandboxBackend(
            timeout_seconds=settings.execution_timeout_seconds,
            max_output_chars=settings.max_output_chars,
            allowed_repo_hosts=settings.allowed_repo_hosts,
        )
    return DockerSandboxBackend(
        image=settings.sandbox_image,
        timeout_seconds=settings.execution_timeout_seconds,
        max_output_chars=settings.max_output_chars,
        allowed_repo_hosts=settings.allowed_repo_hosts,
        auto_build=settings.sandbox_auto_build,
        limits=DockerLimits(memory=settings.sandbox_memory, cpus=settings.sandbox_cpus),
    )


def build_container(settings: Settings) -> Container:
    store = build_store(settings)
    model = build_model_client(settings)
    sandbox = build_sandbox(settings, store)
    queue = build_queue(settings)

    fetcher = SourceFetcher(
        timeout_seconds=settings.source_timeout_seconds,
        max_bytes=settings.max_source_bytes,
    )
    parser = ParserAgent(model, fetcher, allowed_repo_hosts=settings.allowed_repo_hosts)
    environment = EnvironmentAgent(sandbox)
    debugger = DebugAgent(model)

    if settings.github_token:
        issues: IssuePublisher = GitHubIssuePublisher(
            settings.github_token.get_secret_value(),
            fallback_repo=settings.report_repo,
        )
    else:
        issues = NoopIssuePublisher()
    reporter = ReporterAgent(issues)

    pipeline = VerificationPipeline(
        store=store,
        parser=parser,
        environment=environment,
        debugger=debugger,
        reporter=reporter,
        max_debug_attempts=settings.max_debug_attempts,
    )

    launcher: PipelineLauncher
    if settings.messaging == "pubsub":
        if not settings.google_cloud_project:
            raise ValueError("Pub/Sub requires GOOGLE_CLOUD_PROJECT")
        launcher = CloudRunPipelineLauncher(
            settings.google_cloud_project,
            settings.google_cloud_location,
            settings.cloud_run_pipeline_job,
        )
    else:
        launcher = DirectPipelineLauncher(pipeline)

    logger.info(
        "Verity %s profile: store=%s queue=%s sandbox=%s model=%s",
        settings.env,
        settings.store,
        settings.messaging,
        settings.sandbox,
        settings.llm,
    )
    return Container(
        settings=settings,
        store=store,
        queue=queue,
        model=model,
        sandbox=sandbox,
        pipeline=pipeline,
        launcher=launcher,
        orchestrator=Orchestrator(store, queue),
    )

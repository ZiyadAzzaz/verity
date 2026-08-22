"""The local queue adapter and the VERITY_ENV swap point."""

from __future__ import annotations

import asyncio

import pytest

from verity.config import PROFILES, Settings
from verity.container import build_queue, build_store
from verity.messaging import AsyncioJobQueue
from verity.sqlite_store import SQLiteJobStore
from verity.store import MemoryJobStore


async def test_queue_delivers_published_jobs_to_the_consumer() -> None:
    queue = AsyncioJobQueue()
    seen: list[str] = []

    async def handler(job_id: str) -> None:
        seen.append(job_id)

    await queue.consume(handler)
    for index in range(4):
        await queue.publish(f"job-{index}", "https://example.com/")
    await queue.join()
    await queue.close()
    assert seen == ["job-0", "job-1", "job-2", "job-3"]


async def test_publish_returns_before_the_handler_finishes() -> None:
    """Intake must never block on a benchmark, locally or in the cloud."""
    queue = AsyncioJobQueue()
    release = asyncio.Event()

    async def handler(job_id: str) -> None:
        await release.wait()

    await queue.consume(handler)
    await asyncio.wait_for(queue.publish("slow-job", "https://example.com/"), timeout=1)
    release.set()
    await queue.join()
    await queue.close()


async def test_concurrency_limit_bounds_simultaneous_jobs() -> None:
    queue = AsyncioJobQueue(concurrency=2)
    running = 0
    peak = 0
    gate = asyncio.Event()

    async def handler(job_id: str) -> None:
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await gate.wait()
        running -= 1

    await queue.consume(handler)
    for index in range(6):
        await queue.publish(f"job-{index}", "https://example.com/")
    await asyncio.sleep(0.05)
    assert peak == 2, "a laptop must not be asked to run six benchmarks at once"
    gate.set()
    await queue.join()
    await queue.close()


async def test_a_failing_handler_does_not_kill_the_consumer() -> None:
    queue = AsyncioJobQueue()
    seen: list[str] = []

    async def handler(job_id: str) -> None:
        seen.append(job_id)
        if job_id == "bad":
            raise RuntimeError("pipeline blew up")

    await queue.consume(handler)
    await queue.publish("bad", "https://example.com/")
    await queue.publish("good", "https://example.com/")
    await queue.join()
    await queue.close()
    assert seen == ["bad", "good"]


def test_local_profile_selects_only_local_adapters() -> None:
    settings = Settings(env="local", _env_file=None)  # type: ignore[call-arg]
    assert (settings.store, settings.messaging, settings.sandbox, settings.llm) == PROFILES["local"]
    assert settings.store == "sqlite"
    assert settings.sandbox == "docker"
    assert settings.llm == "ai_studio"


def test_cloud_profile_selects_only_google_cloud_adapters() -> None:
    settings = Settings(env="cloud", _env_file=None)  # type: ignore[call-arg]
    assert (settings.store, settings.messaging, settings.sandbox, settings.llm) == PROFILES["cloud"]


def test_an_explicit_override_beats_the_profile() -> None:
    settings = Settings(env="local", store_backend="memory", _env_file=None)  # type: ignore[call-arg]
    assert settings.store == "memory"
    assert settings.sandbox == "docker", "one override must not change the other seams"


def test_production_refuses_the_local_profile() -> None:
    with pytest.raises(ValueError, match="VERITY_ENV=cloud"):
        Settings(environment="production", env="local", _env_file=None)  # type: ignore[call-arg]


def test_build_store_honours_the_profile(tmp_path) -> None:
    local = build_store(
        Settings(env="local", sqlite_path=str(tmp_path / "verity.db"), _env_file=None)  # type: ignore[call-arg]
    )
    assert isinstance(local, SQLiteJobStore)
    local.close()
    assert isinstance(build_store(Settings(store_backend="memory", _env_file=None)), MemoryJobStore)  # type: ignore[call-arg]


def test_build_queue_honours_the_profile() -> None:
    assert isinstance(build_queue(Settings(env="local", _env_file=None)), AsyncioJobQueue)  # type: ignore[call-arg]

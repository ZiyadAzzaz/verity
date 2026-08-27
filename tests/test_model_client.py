"""Retry/backoff for the free-tier Gemini client.

The AI Studio free tier rate-limits hard, and the Debug Agent calls the model up to four
times per job. Transient 429s must not turn into "could not verify"; genuine errors must
not be retried into a long stall.
"""

from __future__ import annotations

import pytest

from verity.llm import GeminiAIStudioClient, VertexAIModelClient, is_retryable


class Boom(Exception):
    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


@pytest.mark.parametrize(
    "error",
    [
        Boom("429 RESOURCE_EXHAUSTED: quota exceeded"),
        Boom("503 Service Unavailable"),
        Boom("model is overloaded, try again"),
        Boom("deadline exceeded"),
        Boom("something", code=500),
        TimeoutError("read timed out"),
        ConnectionError("connection reset"),
    ],
)
def test_transient_failures_are_retryable(error: BaseException) -> None:
    assert is_retryable(error) is True


@pytest.mark.parametrize(
    "error",
    [
        Boom("400 INVALID_ARGUMENT: schema mismatch"),
        Boom("401 API key not valid"),
        Boom("permission denied", code=403),
        ValueError("ParsedClaim validation failed"),
    ],
)
def test_permanent_failures_are_not_retryable(error: BaseException) -> None:
    assert is_retryable(error) is False


async def test_backoff_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []

    async def fake_sleep(delay: float) -> None:
        slept.append(delay)

    monkeypatch.setattr("verity.llm.asyncio.sleep", fake_sleep)
    client = GeminiAIStudioClient("gemini-3.5-flash", base_delay_seconds=1.0)
    attempts = 0

    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Boom("429 rate limit")
        return "done"

    assert await client._with_backoff(flaky, "test") == "done"
    assert attempts == 3
    assert len(slept) == 2
    assert slept[1] > slept[0], "backoff must grow between attempts"


async def test_backoff_gives_up_after_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr("verity.llm.asyncio.sleep", fake_sleep)
    client = GeminiAIStudioClient("gemini-3.5-flash", max_attempts=3, base_delay_seconds=0.0)
    attempts = 0

    async def always_throttled() -> str:
        nonlocal attempts
        attempts += 1
        raise Boom("429 rate limit")

    with pytest.raises(Boom):
        await client._with_backoff(always_throttled, "test")
    assert attempts == 3


async def test_a_permanent_error_is_raised_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_sleep(delay: float) -> None:
        raise AssertionError("a non-retryable error must not be slept on")

    monkeypatch.setattr("verity.llm.asyncio.sleep", fake_sleep)
    client = GeminiAIStudioClient("gemini-3.5-flash")
    attempts = 0

    async def bad_request() -> str:
        nonlocal attempts
        attempts += 1
        raise Boom("400 INVALID_ARGUMENT")

    with pytest.raises(Boom):
        await client._with_backoff(bad_request, "test")
    assert attempts == 1


def test_missing_api_key_is_a_clear_setup_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        GeminiAIStudioClient("gemini-3.5-flash")._configure_auth()


def test_ai_studio_auth_keeps_the_sdk_off_vertex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-secret")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "1")
    GeminiAIStudioClient("gemini-3.5-flash")._configure_auth()
    import os

    assert os.environ["GOOGLE_GENAI_USE_VERTEXAI"] == "0"
    assert os.environ["GOOGLE_API_KEY"] == "test-key-not-a-real-secret"


def test_vertex_client_requires_a_project() -> None:
    with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_PROJECT"):
        VertexAIModelClient("gemini-3.5-flash", project=None)._configure_auth()


def test_cloud_container_uses_the_separate_global_vertex_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from verity.config import Settings
    from verity.container import build_model_client

    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "restore-after-test")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "restore-after-test")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "0")
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        env="cloud",
        google_cloud_project="verity-prod",
        google_cloud_location="us-central1",
        google_cloud_vertex_location="global",
    )
    client = build_model_client(settings)
    assert isinstance(client, VertexAIModelClient)
    client._configure_auth()

    import os

    assert settings.google_cloud_location == "us-central1"
    assert os.environ["GOOGLE_CLOUD_LOCATION"] == "global"


def test_an_injected_key_is_used_when_the_environment_has_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: .env is parsed into Settings and never exported to os.environ.

    A client that only consulted the environment reported "GEMINI_API_KEY is not set" to
    users who had configured it correctly.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    client = GeminiAIStudioClient("gemini-3.5-flash", api_key="injected-not-a-real-secret")
    client._configure_auth()

    import os

    assert os.environ["GOOGLE_API_KEY"] == "injected-not-a-real-secret"
    assert os.environ["GOOGLE_GENAI_USE_VERTEXAI"] == "0"


def test_an_injected_secretstr_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import SecretStr

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    client = GeminiAIStudioClient("gemini-3.5-flash", api_key=SecretStr("secret-not-a-real-secret"))
    client._configure_auth()

    import os

    assert os.environ["GOOGLE_API_KEY"] == "secret-not-a-real-secret"


def test_an_empty_injected_key_falls_back_to_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import SecretStr

    monkeypatch.setenv("GEMINI_API_KEY", "from-env-not-a-real-secret")
    client = GeminiAIStudioClient("gemini-3.5-flash", api_key=SecretStr(""))
    client._configure_auth()

    import os

    assert os.environ["GOOGLE_API_KEY"] == "from-env-not-a-real-secret"


def test_the_container_hands_the_settings_key_to_the_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wiring, not just the client: build_model_client must pass the key through."""
    from verity.config import Settings
    from verity.container import build_model_client

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    settings = Settings(env="local", gemini_api_key="wired-not-a-real-secret", _env_file=None)  # type: ignore[call-arg]
    client = build_model_client(settings)
    assert isinstance(client, GeminiAIStudioClient)
    client._configure_auth()

    import os

    assert os.environ["GOOGLE_API_KEY"] == "wired-not-a-real-secret"

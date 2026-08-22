"""Gemini model clients.

Both adapters run the same single-turn, typed Google ADK ``LlmAgent``; they differ only
in how the ADK authenticates:

* :class:`GeminiAIStudioClient` — a Google AI Studio API key. No billing account, no GCP
  project, no card. This is the local-first path.
* :class:`VertexAIModelClient` — application default credentials against a Vertex AI
  project. Identical prompts and schemas; only the transport changes.

The pipeline deliberately creates a fresh in-memory ADK session per durable agent step.
The job store, not conversational session state, is the cross-step source of truth.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import uuid
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar

from verity.interfaces import ModelClient, SchemaT

T = TypeVar("T")

if TYPE_CHECKING:
    from verity.source import SourceDocument

logger = logging.getLogger(__name__)

#: Substrings that mark a Gemini failure as transient and worth backing off on. The free
#: AI Studio tier rate-limits aggressively and the Debug Agent's retry loop hits it hard.
RETRYABLE_MARKERS = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "resource_exhausted",
    "resource exhausted",
    "rate limit",
    "quota",
    "unavailable",
    "deadline exceeded",
    "internal error",
    "overloaded",
)


def is_retryable(error: BaseException) -> bool:
    code = getattr(error, "code", None)
    if isinstance(code, int) and code in {429, 500, 502, 503, 504}:
        return True
    if isinstance(error, TimeoutError | ConnectionError):
        return True
    text = f"{type(error).__name__}: {error}".lower()
    return any(marker in text for marker in RETRYABLE_MARKERS)


class _AdkGeminiClient(ModelClient):
    """Shared ADK plumbing plus exponential backoff with jitter."""

    def __init__(
        self,
        model: str,
        *,
        max_attempts: int = 5,
        base_delay_seconds: float = 2.0,
        max_delay_seconds: float = 60.0,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._model = model
        self._max_attempts = max_attempts
        self._base_delay = base_delay_seconds
        self._max_delay = max_delay_seconds

    # --- subclass hook -------------------------------------------------------

    def _configure_auth(self) -> None:
        """Put the right credentials in place for the google-genai SDK."""
        raise NotImplementedError

    # --- retry ---------------------------------------------------------------

    async def _with_backoff(self, operation: Callable[[], Awaitable[T]], description: str) -> T:
        last: BaseException | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return await operation()
            except Exception as exc:
                last = exc
                if attempt == self._max_attempts or not is_retryable(exc):
                    raise
                delay = min(self._base_delay * 2 ** (attempt - 1), self._max_delay)
                delay += random.uniform(0, delay / 2)
                logger.warning(
                    "Gemini %s failed (%s); retrying in %.1fs [attempt %d/%d]",
                    description,
                    type(exc).__name__,
                    delay,
                    attempt,
                    self._max_attempts,
                )
                await asyncio.sleep(delay)
        raise RuntimeError(f"Gemini {description} exhausted retries") from last

    # --- generation ----------------------------------------------------------

    async def generate(self, prompt: str, files: list[SourceDocument] | None = None) -> str:
        async def call() -> str:
            text, _raw = await self._invoke(
                instruction="Answer the request precisely and without speculation.",
                prompt=prompt,
                schema=None,
                documents=files or [],
            )
            return text

        return await self._with_backoff(call, "text generation")

    async def generate_structured(
        self,
        *,
        instruction: str,
        prompt: str,
        schema: type[SchemaT],
        document: SourceDocument | None = None,
    ) -> SchemaT:
        async def call() -> SchemaT:
            text, raw = await self._invoke(
                instruction=instruction,
                prompt=prompt,
                schema=schema,
                documents=[document] if document is not None else [],
            )
            if isinstance(raw, schema):
                return raw
            if isinstance(raw, dict):
                return schema.model_validate(raw)
            if isinstance(raw, str):
                return schema.model_validate_json(raw)
            if text:
                return schema.model_validate_json(text)
            # No coercion and no salvage: a response that does not satisfy the typed
            # contract is an error. Verity would rather fail a job than invent a field.
            raise RuntimeError(f"ADK agent returned no structured {schema.__name__}")

        return await self._with_backoff(call, f"{schema.__name__} generation")

    async def _invoke(
        self,
        *,
        instruction: str,
        prompt: str,
        schema: type[SchemaT] | None,
        documents: list[SourceDocument],
    ) -> tuple[str, Any]:
        """Run one ADK turn. Returns ``(final_text, structured_state_value)``."""
        self._configure_auth()

        from google.adk.agents import LlmAgent
        from google.adk.apps import App
        from google.adk.models import Gemini
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        parts: list[Any] = [types.Part.from_text(text=prompt)]
        for document in documents:
            if document.media_type == "application/pdf":
                parts.append(
                    types.Part.from_bytes(data=document.content, mime_type="application/pdf")
                )
            else:
                parts.append(
                    types.Part.from_text(
                        text="<UNTRUSTED_SOURCE>\n" + document.text + "\n</UNTRUSTED_SOURCE>"
                    )
                )

        output_key = "structured_output"
        agent_names = {"ParsedClaim": "parser_agent", "DebugProposal": "debug_agent"}
        agent = LlmAgent(
            name=agent_names.get(schema.__name__ if schema else "", "structured_agent"),
            model=Gemini(
                model=self._model,
                retry_options=types.HttpRetryOptions(attempts=3),
            ),
            instruction=instruction,
            include_contents="none",
            output_schema=schema,
            output_key=output_key if schema else None,
        )
        adk_app = App(root_agent=agent, name="verity_structured")
        sessions = InMemorySessionService()
        user_id = "verity-pipeline"
        session = await sessions.create_session(
            app_name=adk_app.name,
            user_id=user_id,
            session_id=uuid.uuid4().hex,
        )
        runner = Runner(app=adk_app, session_service=sessions)
        final_text = ""
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=types.Content(role="user", parts=parts),
            ):
                if event.content and event.content.parts:
                    final_text = (
                        "".join(part.text or "" for part in event.content.parts if part.text)
                        or final_text
                    )
            if schema is None:
                return final_text, None
            completed = await sessions.get_session(
                app_name=adk_app.name,
                user_id=user_id,
                session_id=session.id,
            )
            return final_text, completed.state.get(output_key) if completed else None
        finally:
            await runner.close()


class GeminiAIStudioClient(_AdkGeminiClient):
    """Gemini through a Google AI Studio API key — the local-first model path.

    The key is read from ``GEMINI_API_KEY`` at call time and never stored on the instance,
    logged, or written to the job trace.
    """

    def _configure_auth(self) -> None:
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Create a free key at https://aistudio.google.com/"
                " and put it in .env — no billing account is required."
            )
        # google-genai reads these; setting both keeps ADK off the Vertex code path.
        os.environ["GOOGLE_API_KEY"] = key
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"


class VertexAIModelClient(_AdkGeminiClient):
    """Gemini through Vertex AI on a billed Google Cloud project.

    Wired and selectable today via ``VERITY_ENV=cloud``; unverified against live Vertex
    until hackathon credits land, because it needs an active billing account.
    """

    def __init__(self, model: str, *, project: str | None = None, location: str = "us-central1"):
        super().__init__(model)
        self._project = project
        self._location = location

    def _configure_auth(self) -> None:
        if not self._project:
            raise RuntimeError("VertexAIModelClient requires GOOGLE_CLOUD_PROJECT")
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
        os.environ["GOOGLE_CLOUD_PROJECT"] = self._project
        os.environ["GOOGLE_CLOUD_LOCATION"] = self._location
        os.environ.pop("GOOGLE_API_KEY", None)


__all__ = [
    "GeminiAIStudioClient",
    "ModelClient",
    "VertexAIModelClient",
    "is_retryable",
]

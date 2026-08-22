"""Cloud Logging and Cloud Trace bootstrap plus per-agent spans."""

from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import Iterator
from typing import Any

_configured = False


def configure_telemetry(project: str | None = None, *, cloud: bool = False) -> None:
    global _configured
    if _configured:
        return
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if cloud:
        try:
            import google.cloud.logging

            google.cloud.logging.Client(project=project).setup_logging()  # type: ignore[no-untyped-call]
        except Exception:
            logging.getLogger(__name__).exception("Cloud Logging setup failed; using stdout")
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            provider = TracerProvider()
            provider.add_span_processor(
                BatchSpanProcessor(CloudTraceSpanExporter(project_id=project))  # type: ignore[no-untyped-call]
            )
            trace.set_tracer_provider(provider)
        except Exception:
            logging.getLogger(__name__).exception("Cloud Trace setup failed; spans stay local")
    _configured = True


@contextlib.contextmanager
def agent_span(agent: str, job_id: str, **attributes: Any) -> Iterator[None]:
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("verity.pipeline")
        with tracer.start_as_current_span(f"verity.{agent}") as span:
            span.set_attribute("verity.agent", agent)
            span.set_attribute("verity.job_id", job_id)
            for key, value in attributes.items():
                span.set_attribute(f"verity.{key}", value)
            yield
    except ImportError:
        yield

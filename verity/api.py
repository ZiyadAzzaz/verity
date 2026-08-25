"""FastAPI intake, status API, Pub/Sub push worker, and minimal frontend."""

from __future__ import annotations

import asyncio
import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse

from verity.config import Settings, get_settings
from verity.container import Container, build_container
from verity.messaging import decode_push_envelope
from verity.models import JobView, SubmitRequest, SubmitResponse
from verity.oidc import OidcVerificationUnavailable, verify_pubsub_oidc
from verity.security import UnsafeUrlError
from verity.telemetry import configure_telemetry

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    *,
    settings: Settings | None = None,
    container: Container | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    container = container or build_container(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_telemetry(
            settings.google_cloud_project,
            cloud=settings.environment == "production",
        )
        app.state.container = container
        # Surface a stopped Docker daemon or a missing API key at boot. It is not fatal —
        # the status API and the UI stay useful — but the reason is reported on /healthz
        # instead of only appearing inside a failed job three minutes later.
        try:
            await container.preflight()
            app.state.setup_error = None
        except Exception as exc:
            app.state.setup_error = f"{type(exc).__name__}: {exc}"
            logger.error("Verity setup check failed: %s", exc)
        await container.startup()
        try:
            yield
        finally:
            await container.shutdown()

    api = FastAPI(
        title="Verity",
        version="0.1.0",
        description="Execution-backed verification for public AI/ML claims",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )

    @api.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' "
            "'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        )
        return response

    async def require_api_key(
        x_verity_key: Annotated[str | None, Header()] = None,
    ) -> None:
        expected = settings.api_key.get_secret_value() if settings.api_key else None
        if expected is None and settings.environment != "production":
            return
        if (
            expected is None
            or x_verity_key is None
            or not hmac.compare_digest(expected, x_verity_key)
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")

    protected = [Depends(require_api_key)]

    @api.exception_handler(UnsafeUrlError)
    async def unsafe_url_handler(request: Request, exc: UnsafeUrlError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @api.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @api.get("/architecture", include_in_schema=False)
    async def architecture() -> FileResponse:
        candidate = Path.cwd() / "verity-architecture.html"
        return FileResponse(candidate if candidate.is_file() else STATIC_DIR / "index.html")

    @api.get("/healthz")
    async def healthz(request: Request) -> dict[str, str | None]:
        setup_error = getattr(request.app.state, "setup_error", None)
        return {
            "status": "ok" if setup_error is None else "degraded",
            "profile": settings.env,
            "model": settings.gemini_model,
            "store": settings.store,
            "queue": settings.messaging,
            "sandbox": settings.sandbox,
            # Which publisher is wired in. "noop" means completed jobs will not file an
            # Issue and the UI will have no artifact to link to - a configuration state
            # that is otherwise invisible until someone wonders where their button went.
            "issue_publisher": "github" if settings.github_token else "noop",
            "report_repo": settings.report_repo,
            "setup_error": setup_error,
        }

    @api.post(
        "/api/jobs",
        response_model=SubmitResponse,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=protected,
    )
    async def submit(request: SubmitRequest) -> SubmitResponse:
        return await container.orchestrator.submit(str(request.url))

    @api.get("/api/jobs/{job_id}", response_model=JobView, dependencies=protected)
    async def get_job(job_id: str) -> JobView:
        job = await container.store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return JobView(job=job, trace=await container.store.get_trace(job_id))

    @api.post("/internal/pubsub", status_code=status.HTTP_204_NO_CONTENT)
    async def consume_pubsub(
        envelope: dict[str, object],
        authorization: Annotated[str | None, Header()] = None,
    ) -> Response:
        audience = settings.pubsub_oidc_audience
        service_account = settings.pubsub_service_account
        if audience and service_account:
            try:
                await asyncio.to_thread(
                    verify_pubsub_oidc,
                    authorization,
                    audience=audience,
                    service_account_email=service_account,
                )
            except OidcVerificationUnavailable as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            except (ValueError, TypeError) as exc:
                raise HTTPException(status_code=401, detail=str(exc)) from exc
        elif settings.environment == "production":
            raise HTTPException(status_code=503, detail="Pub/Sub OIDC is not configured")
        job_id, _message_id = decode_push_envelope(envelope)
        await container.launcher.launch(job_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return api


def run() -> None:
    import uvicorn

    uvicorn.run("verity.api:create_app", factory=True, host="0.0.0.0", port=8080)


app = create_app()

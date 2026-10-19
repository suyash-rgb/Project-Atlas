import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
# Project Atlas API Gateway
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.telemetry import telemetry
from app.api.v1.api import api_router as api_v1_router

logger = logging.getLogger("project_atlas.http")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
        telemetry.langfuse.flush()


def configure_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), None)
    if not isinstance(level, int):
        raise ValueError("LOG_LEVEL must be a standard logging level such as INFO or DEBUG.")
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            elif message["type"] == "http.response.body" and not message.get("more_body", False):
                duration_ms = (time.perf_counter() - started_at) * 1000
                logger.info(
                    "http_request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                    request_id,
                    scope["method"],
                    scope["path"],
                    status_code,
                    duration_ms,
                )
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            logger.exception(
                "http_request_failed request_id=%s method=%s path=%s",
                request_id,
                scope["method"],
                scope["path"],
            )
            raise


def create_application() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Enterprise Report Copilot API for Cognitive Market Research & Consulting. "
                    "Features LangGraph multi-node state machine, Laya 421M System-1 guardrails, "
                    "deterministic CAGR calculators, AST-safe SQL tools, and entitlement RAG.",
        version=settings.VERSION,
        lifespan=lifespan,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Enable CORS for CI3 portal and local browser development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # Redirect root to interactive Swagger UI documentation
    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/docs")

    # Friendly redirect for /api/v1/docs -> /docs
    @app.get("/api/v1/docs", include_in_schema=False)
    async def v1_docs_redirect():
        return RedirectResponse(url="/docs")

    @app.get("/portal", include_in_schema=False)
    @app.get("/preview", include_in_schema=False)
    async def portal_redirect():
        return RedirectResponse(url="/portal/preview.html")

    # Mount portal directory to serve the frontend portal on the exact same port
    portal_dir = Path(__file__).resolve().parent.parent.parent / "portal"
    if portal_dir.exists():
        app.mount("/portal", StaticFiles(directory=str(portal_dir), html=True), name="portal")

    # Root health check endpoint (essential for Docker healthcheck and ALB probes)
    @app.get("/health", tags=["Health"])
    async def root_health():
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION
        }

    return app


app = create_application()

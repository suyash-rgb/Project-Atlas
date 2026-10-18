from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router as api_v1_router


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Enterprise Report Copilot API for Cognitive Market Research & Consulting. "
                    "Features LangGraph multi-node state machine, Laya 421M System-1 guardrails, "
                    "deterministic CAGR calculators, AST-safe SQL tools, and entitlement RAG.",
        version=settings.VERSION,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Enable CORS for CI3 portal and local browser development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # Redirect root to interactive Swagger UI documentation
    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/docs")

    # Friendly redirect for /api/v1/docs -> /docs
    @app.get("/api/v1/docs", include_in_schema=False)
    async def v1_docs_redirect():
        return RedirectResponse(url="/docs")

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

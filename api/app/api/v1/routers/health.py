from fastapi import APIRouter, Response, status
from app.schemas.chat import HealthResponse, ErrorResponse
from app.services.health_service import health_service

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System health check",
    responses={
        200: {
            "model": HealthResponse,
            "description": "System operational - all subsystems online and ready"
        },
        503: {
            "model": HealthResponse,
            "description": "Service Unavailable - database disconnected or vector index degraded"
        }
    }
)
async def health_check(response: Response):
    """
    HTTP Controller for system diagnostics.
    - Probes SQLite/MySQL database and ChromaDB collection status.
    - Emits HTTP 200 OK when fully healthy.
    - Emits HTTP 503 Service Unavailable if any core dependency is degraded.
    """
    health = health_service.check_health()
    if health.status != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health

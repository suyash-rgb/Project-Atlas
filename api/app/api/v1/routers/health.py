from fastapi import APIRouter
from app.schemas.chat import HealthResponse
from app.services.health_service import health_service

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("", response_model=HealthResponse, summary="System health check")
async def health_check():
    """
    HTTP Controller for system diagnostics.
    Delegates subsystem probing to HealthService.
    """
    return health_service.check_health()

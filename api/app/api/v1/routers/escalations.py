import logging
from typing import List
from fastapi import APIRouter, Security, HTTPException, status
from app.api.deps import verify_api_key
from app.schemas.chat import EscalationItem, ErrorResponse
from app.services.escalation_service import escalation_service

router = APIRouter(prefix="/escalations", tags=["Escalations & Human-in-the-Loop"])
logger = logging.getLogger("project_atlas.api.escalations")


@router.get(
    "",
    response_model=List[EscalationItem],
    status_code=status.HTTP_200_OK,
    summary="List escalated tickets",
    responses={
        200: {
            "description": "List of all human analyst escalation tickets"
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - invalid or missing X-API-Key"
        },
        503: {
            "model": ErrorResponse,
            "description": "Service Unavailable - API authentication is not configured"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal Server Error - failed to query escalations database"
        }
    }
)
async def get_escalations(_auth: str = Security(verify_api_key)):
    """
    HTTP Controller for analyst escalation queries.
    - Requires authorized API Key credentials.
    - Delegates retrieval and formatting to EscalationService.
    """
    try:
        return escalation_service.get_all_escalations()
    except Exception as e:
        logger.exception("escalations_endpoint_failed error_type=%s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Escalations could not be retrieved."
        ) from e

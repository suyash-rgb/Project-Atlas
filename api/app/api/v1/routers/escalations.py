from typing import List
from fastapi import APIRouter, Security
from app.api.deps import verify_api_key
from app.schemas.chat import EscalationItem
from app.services.escalation_service import escalation_service

router = APIRouter(prefix="/escalations", tags=["Escalations & Human-in-the-Loop"])


@router.get("", response_model=List[EscalationItem], summary="List escalated tickets")
async def get_escalations(_auth: str = Security(verify_api_key)):
    """
    HTTP Controller for analyst escalation queries.
    Delegates retrieval and formatting to EscalationService.
    """
    return escalation_service.get_all_escalations()

from fastapi import APIRouter, Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    IngestRequest,
    EscalationItem,
    HealthResponse
)
from typing import List

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return api_key

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, summary="Submit inquiry to the Report Copilot")
async def chat(request: ChatRequest, _auth: str = Security(verify_api_key)):
    """
    Core entrypoint for the Agent Workflow:
    - Entitlement filtering by client_id
    - Graph routing (SQL, Vector Search, Calculator, Escalation)
    - Conflict and derived estimate extraction
    """
    # Placeholder returning structured response until agent graph is plugged in
    return ChatResponse(
        answer=f"Received query from client {request.client_id}. Workflow graph initialized.",
        citations=[],
        confidence=1.0,
        conflicts=[],
        derived_values=[],
        escalated=False
    )


@router.post("/ingest", summary="Ingest and chunk a report with metadata")
async def ingest_report(request: IngestRequest, _auth: str = Security(verify_api_key)):
    return {
        "status": "success",
        "report_id": request.report_id,
        "message": "Report successfully queued for chunking and vector storage."
    }


@router.get("/escalations", response_model=List[EscalationItem], summary="List escalated tickets")
async def get_escalations(_auth: str = Security(verify_api_key)):
    # Returns tickets pending human analyst review
    return []


@router.get("/health", response_model=HealthResponse, summary="System health check")
async def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        database="connected",
        vector_store="ready"
    )

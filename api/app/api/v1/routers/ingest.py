import logging

from fastapi import APIRouter, Security, status, HTTPException
from app.api.deps import verify_api_key
from app.schemas.chat import IngestRequest, IngestResponse, ErrorResponse
from app.services.ingest_service import ingest_service

router = APIRouter(prefix="/ingest", tags=["Document Ingestion"])
logger = logging.getLogger("project_atlas.ingest_api")


@router.post(
    "",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest market research report into vector store",
    responses={
        201: {"model": IngestResponse, "description": "Report successfully ingested and indexed"},
        400: {"model": ErrorResponse, "description": "Invalid report payload"},
        403: {"model": ErrorResponse, "description": "Forbidden - invalid or missing X-API-Key"},
        500: {"model": ErrorResponse, "description": "Internal server error during ingestion"}
    }
)
async def ingest_report(request: IngestRequest, _auth: str = Security(verify_api_key)):
    """
    Ingest a new market research report into ChromaDB with metadata.
    Enforces API-key authentication and indexes text for entitlement-filtered RAG.
    """
    if not request.report_id.strip():
        raise HTTPException(status_code=400, detail="report_id cannot be empty")
    if request.pages:
        if any(not page.content.strip() for page in request.pages):
            raise HTTPException(status_code=400, detail="Page content cannot be empty")
    elif not request.content or not request.content.strip():
        raise HTTPException(status_code=400, detail="content cannot be empty")

    try:
        return ingest_service.ingest_report(request)
    except Exception:
        logger.exception("report_ingestion_failed report_id=%s", request.report_id)
        raise HTTPException(
            status_code=500,
            detail="Ingestion failed. Check the server logs for details.",
        )

from fastapi import APIRouter, Security, status, HTTPException
from app.api.deps import verify_api_key
from app.schemas.chat import IngestRequest, IngestResponse, ErrorResponse
from app.services.ingest_service import ingest_service

router = APIRouter(prefix="/ingest", tags=["Document Ingestion"])


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
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="content cannot be empty")

    try:
        return ingest_service.ingest_report(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}")

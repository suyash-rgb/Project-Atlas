from app.schemas.chat import IngestRequest, IngestResponse
from app.agent.tools.retriever import get_retriever
from app.core.telemetry import logger


class IngestService:
    def ingest_report(self, request: IngestRequest) -> IngestResponse:
        retriever = get_retriever()
        chunks = retriever.ingest_document_content(
            report_id=request.report_id,
            title=request.title,
            publisher=request.publisher,
            published_date=request.published_date,
            sector=request.sector,
            access_tier=request.access_tier,
            content=request.content
        )
        logger.info(
            "ingest_service_completed report_id=%s chunks=%s",
            request.report_id,
            chunks,
        )
        return IngestResponse(
            status="success",
            report_id=request.report_id,
            chunks_ingested=chunks,
            message=f"Report {request.report_id} ingested successfully ({chunks} chunks indexed)."
        )


ingest_service = IngestService()

import os
import pypdf
import pymupdf
from typing import Sequence, Tuple, Optional, List, Dict, Any
from llama_index.core import Document

from app.schemas.chat import IngestRequest, IngestResponse
from app.core.telemetry import logger
from app.core.config import settings
from app.db.session import upsert_report_metadata
from app.db.metadata import (
    fetch_report_metadata,
    register_runtime_report,
    stable_document_id,
)
from app.agent.tools.chart_extractor import extract_and_summarize_charts_from_pdf
from app.agent.tools.retriever import get_retriever


class IngestService:
    """
    Coordinates data ingestion, parsing of PDFs/documents, chart summarization,
    and delegating prepared Document objects into ChromaDB and TF-IDF stores.
    """

    def parse_pdf_corpus_documents(self, reports_dir: str) -> List[Document]:
        """
        Parses all PDF reports and embedded visual charts from the reports directory
        into LlamaIndex Document instances ready for indexing.
        """
        if not os.path.isdir(reports_dir):
            raise RuntimeError(f"Report directory does not exist: {reports_dir}")

        pdf_files = [f for f in os.listdir(reports_dir) if f.lower().endswith(".pdf")]
        documents: List[Document] = []

        logger.info("ingest_service_parse_corpus_started files=%s", len(pdf_files))
        for filename in sorted(pdf_files):
            report_id = filename.split("_")[0]
            report_meta = fetch_report_metadata(report_id)
            file_path = os.path.join(reports_dir, filename)

            try:
                reader = pypdf.PdfReader(file_path)
                for page_num, page in enumerate(reader.pages, start=1):
                    page_text = page.extract_text()
                    if not page_text or len(page_text.strip()) < 20:
                        continue

                    doc = Document(
                        text=page_text,
                        id_=stable_document_id(report_id, page_num, page_text),
                        metadata={
                            "report_id": report_id,
                            "page": page_num,
                            "title": str(report_meta.get("title", filename)),
                            "publisher": str(report_meta.get("publisher", "Unknown")),
                            "sector": str(report_meta.get("sector", "General")),
                            "year": int(report_meta.get("year", 2024)),
                            "access": str(report_meta.get("access", "paid")),
                            "source_file": filename,
                        },
                    )
                    documents.append(doc)

                # Extract and summarize embedded visual charts
                try:
                    chart_chunks = extract_and_summarize_charts_from_pdf(
                        pdf_path=file_path,
                        report_id=report_id,
                        report_title=str(report_meta.get("title", filename)),
                    )
                    for c_info in chart_chunks:
                        c_doc = Document(
                            text=c_info["text"],
                            id_=stable_document_id(report_id, c_info["page"], c_info["text"], kind="chart"),
                            metadata={
                                "report_id": report_id,
                                "page": c_info["page"],
                                "title": str(report_meta.get("title", filename)),
                                "publisher": str(report_meta.get("publisher", "Unknown")),
                                "sector": str(report_meta.get("sector", "General")),
                                "year": int(report_meta.get("year", 2024)),
                                "access": str(report_meta.get("access", "paid")),
                                "source_file": filename,
                                "type": "chart",
                            },
                        )
                        documents.append(c_doc)
                except Exception as chart_err:
                    logger.warning("chart_ingestion_skipped report_id=%s error=%s", report_id, chart_err)
            except Exception as e:
                logger.exception("report_pdf_parse_failed file=%s error_type=%s", filename, type(e).__name__)

        return documents

    def create_page_paragraphs(
        self,
        content: str,
        pages: Optional[Sequence[Tuple[int, str]]] = None,
    ) -> List[Tuple[int, str]]:
        """Splits page-aware or raw document content into distinct paragraph chunks."""
        source_pages = list(pages) if pages else [(1, content)]
        return [
            (page_number, paragraph.strip())
            for page_number, page_content in source_pages
            for paragraph in page_content.split("\n\n")
            if paragraph.strip()
        ]

    def ingest_report(self, request: IngestRequest) -> IngestResponse:
        upsert_report_metadata(
            report_id=request.report_id,
            title=request.title,
            publisher=request.publisher,
            published_date=request.published_date.isoformat(),
            sector=request.sector,
            access_tier=request.access_tier,
        )
        retriever = get_retriever()
        chunks = retriever.ingest_document_content(
            report_id=request.report_id,
            title=request.title,
            publisher=request.publisher,
            published_date=request.published_date.isoformat(),
            sector=request.sector,
            access_tier=request.access_tier,
            content=request.content or "",
            pages=[
                (page.page_number, page.content)
                for page in request.pages or []
            ],
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


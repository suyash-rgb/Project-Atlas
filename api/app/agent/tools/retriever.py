"""
LlamaIndex + FastEmbed (BAAI/bge-small-en-v1.5) + ChromaDB Ingestion and Entitlement Retriever.

Features:
- Ingests all 6 generated PDF market reports (R-101 to R-106).
- Preserves trap documents and metadata (report_id, sector, region, year, page).
- Implements strict client entitlement filtering before any retrieved context reaches the agent/LLM.
"""

import os
import logging
import chromadb
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pypdf

from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator

from app.core.config import REPOSITORY_ROOT, settings
from app.core.observability import observe_with_tags
from app.agent.tools.utils import (
    DEFAULT_REPORT_METADATA,
    fetch_report_metadata,
    fetch_all_reports_metadata,
    get_public_report_ids,
    register_runtime_report,
)

CHROMA_PATH = str(getattr(settings, "CHROMA_DB_PATH", None) or (REPOSITORY_ROOT / "data" / "chroma_db"))
REPORTS_DIR = str(getattr(settings, "REPORTS_DIR", None) or (REPOSITORY_ROOT / "data" / "reports"))
COLLECTION_NAME = "project_atlas_reports"
logger = logging.getLogger("project_atlas.retriever")

# Configure global LlamaIndex embedding model using BGE-Small ONNX
Settings.embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)

# Dynamic accessor for backward-compatible metadata lookups
REPORT_METADATA_REGISTRY = fetch_all_reports_metadata()



class RetrievedChunk(BaseModel):
    report_id: str
    page: int
    text: str
    score: float
    title: str
    sector: str
    access: str


class EntitlementRetriever:
    _instance: Optional["EntitlementRetriever"] = None
    _chroma_client = None
    _collection = None
    _index = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EntitlementRetriever, cls).__new__(cls)
            cls._instance._init_index()
        return cls._instance

    def _init_index(self):
        resolved_path = os.path.abspath(CHROMA_PATH)
        os.makedirs(resolved_path, exist_ok=True)
        self._chroma_client = chromadb.PersistentClient(path=resolved_path)
        self._collection = self._chroma_client.get_or_create_collection(COLLECTION_NAME)
        vector_store = ChromaVectorStore(chroma_collection=self._collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        self._index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
        logger.info(
            "vector_store_initialized collection=%s chunks=%s",
            COLLECTION_NAME,
            self._collection.count(),
        )

    def ingest_reports(self, force_reload: bool = False) -> int:
        current_count = self._collection.count()
        if current_count > 0 and not force_reload:
            logger.info("report_ingestion_skipped reason=collection_populated chunks=%s", current_count)
            return current_count

        if force_reload and current_count > 0:
            logger.warning("report_ingestion_force_reload deleting_existing_chunks=%s", current_count)
            self._chroma_client.delete_collection(COLLECTION_NAME)
            self._collection = self._chroma_client.get_or_create_collection(COLLECTION_NAME)
            vector_store = ChromaVectorStore(chroma_collection=self._collection)
            self._index = VectorStoreIndex.from_vector_store(vector_store)

        pdf_files = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".pdf")]
        documents = []

        logger.info("report_ingestion_started files=%s", len(pdf_files))
        for filename in pdf_files:
            report_id = filename.split("_")[0]
            report_meta = fetch_report_metadata(report_id)

            file_path = os.path.join(REPORTS_DIR, filename)
            try:
                reader = pypdf.PdfReader(file_path)
                for page_num, page in enumerate(reader.pages, start=1):
                    page_text = page.extract_text()
                    if not page_text or len(page_text.strip()) < 20:
                        continue

                    doc = Document(
                        text=page_text,
                        metadata={
                            "report_id": report_id,
                            "page": page_num,
                            "title": str(report_meta.get("title", filename)),
                            "publisher": str(report_meta.get("publisher", "Unknown")),
                            "sector": str(report_meta.get("sector", "General")),
                            "year": int(report_meta.get("year", 2024)),
                            "access": str(report_meta.get("access", "paid")),
                            "source_file": filename
                        }
                    )
                    documents.append(doc)
            except Exception as e:
                logger.exception(
                    "report_pdf_parse_failed file=%s error_type=%s",
                    filename,
                    type(e).__name__,
                )

        if not documents:
            logger.error("report_ingestion_failed reason=no_documents files=%s", len(pdf_files))
            raise RuntimeError("No report pages were available to index.")

        logger.info("report_index_build_started documents=%s", len(documents))
        self._index = VectorStoreIndex.from_documents(
            documents,
            storage_context=StorageContext.from_defaults(vector_store=ChromaVectorStore(chroma_collection=self._collection)),
            show_progress=True
        )
        total_chunks = self._collection.count() if self._collection is not None else len(documents)
        logger.info(
            "report_ingestion_completed documents=%s chunks=%s",
            len(documents),
            total_chunks,
        )
        return total_chunks

    def ingest_document_content(
        self,
        report_id: str,
        title: str,
        publisher: str,
        published_date: str,
        sector: str,
        access_tier: str,
        content: str
    ) -> int:
        """
        Ingests and indexes document content chunks in ChromaDB with metadata.
        """
        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) >= 20]
        if not paragraphs:
            paragraphs = [content.strip()] if content.strip() else []

        if not paragraphs:
            return 0

        documents = []
        for idx, para in enumerate(paragraphs, start=1):
            doc = Document(
                text=para,
                metadata={
                    "report_id": report_id,
                    "page": idx,
                    "title": title,
                    "publisher": publisher,
                    "published": published_date,
                    "sector": sector,
                    "access": access_tier,
                }
            )
            documents.append(doc)

        year_val = 2024
        if published_date and len(str(published_date)) >= 4 and str(published_date)[:4].isdigit():
            year_val = int(str(published_date)[:4])

        register_runtime_report(report_id, {
            "title": title,
            "publisher": publisher,
            "sector": sector,
            "published": published_date,
            "year": year_val,
            "access": access_tier,
            "coverage": f"{sector} market coverage"
        })
        REPORT_METADATA_REGISTRY[report_id] = fetch_report_metadata(report_id)

        if self._index is not None:
            for d in documents:
                self._index.insert(d)

        logger.info("document_ingested report_id=%s chunks=%s", report_id, len(documents))
        return len(documents)

    @observe_with_tags(
        name="entitlement_filtered_retrieval",
        as_type="retriever",
        tags=["tool:retriever", "retrieval:entitlement-filtered"],
    )
    def retrieve_for_client(
        self,
        query: str,
        purchased_reports: List[str],
        top_k: int = 5
    ) -> List[RetrievedChunk]:
        """
        Entitlement-filtered retrieval: guarantees that chunks from unpurchased
        reports are excluded at the ChromaDB vector level.
        """
        # Always allow public excerpts in addition to purchased reports
        public_reports = get_public_report_ids()
        allowed_reports = sorted(list(set(purchased_reports + public_reports)))

        # Edge case protection: ChromaDB raises ValueError if $in operand is empty list
        if not allowed_reports:
            logger.info("vector_retrieval_empty_allowed_reports query=%s", query)
            return []

        if self._index is None or (self._collection and self._collection.count() == 0):
            logger.warning("vector_retrieval_empty_collection query=%s", query)
            return []

        # Build MetadataFilter
        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="report_id",
                    operator=FilterOperator.IN,
                    value=allowed_reports
                )
            ]
        )

        retriever = self._index.as_retriever(
            filters=filters,
            similarity_top_k=top_k
        )


        try:
            nodes = retriever.retrieve(query)
        except Exception as exc:
            logger.exception(
                "vector_retrieval_failed error_type=%s allowed_report_count=%s",
                type(exc).__name__,
                len(allowed_reports),
            )
            raise
        results = []
        for n in nodes:
            meta = n.metadata
            results.append(RetrievedChunk(
                report_id=str(meta.get("report_id", "UNKNOWN")),
                page=int(meta.get("page", 1)),
                text=n.text,
                score=float(n.score if n.score is not None else 0.0),
                title=str(meta.get("title", "")),
                sector=str(meta.get("sector", "")),
                access=str(meta.get("access", "paid"))
            ))

        logger.info(
            "vector_retrieval_completed result_count=%s allowed_report_count=%s",
            len(results),
            len(allowed_reports),
        )
        return results


_retriever_instance = None

def get_retriever() -> EntitlementRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = EntitlementRetriever()
    return _retriever_instance

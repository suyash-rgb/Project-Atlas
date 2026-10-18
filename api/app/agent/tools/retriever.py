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

from app.core.config import settings
from app.core.observability import observe_with_tags

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "../../../../data/chroma_db")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "../../../../data/reports")
COLLECTION_NAME = "project_atlas_reports"
logger = logging.getLogger("project_atlas.retriever")

# Configure global LlamaIndex embedding model using BGE-Small ONNX
Settings.embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)


REPORT_METADATA_REGISTRY = {
    "R-101": {
        "title": "Global Smart Water Meter Market 2025-2032",
        "publisher": "Cognitive Market Research",
        "sector": "Utilities",
        "year": 2024,
        "access": "paid",
        "coverage": "Turnkey solutions (hardware, AMI software, installation, maintenance)"
    },
    "R-102": {
        "title": "Smart Water Metering Industry Outlook 2024",
        "publisher": "Aquila Market Insights",
        "sector": "Utilities",
        "year": 2024,
        "access": "paid",
        "coverage": "Hardware only (meter units and physical endpoints)"
    },
    "R-103": {
        "title": "Residential Water Purifier Market 2025",
        "publisher": "Cognitive Market Research",
        "sector": "Consumer / Water Treatment",
        "year": 2024,
        "access": "paid",
        "coverage": "Residential reverse osmosis and UV filtration systems"
    },
    "R-104": {
        "title": "Commercial Industrial Water Treatment 2025",
        "publisher": "H2O Analytics Excerpt",
        "sector": "Industrial",
        "year": 2024,
        "access": "public_excerpt",
        "coverage": "High-volume RO membranes and commercial filtration"
    },
    "R-105": {
        "title": "Smart Multi-Utility Metering Outlook 2024",
        "publisher": "Cognitive Market Research",
        "sector": "Utilities",
        "year": 2024,
        "access": "paid",
        "coverage": "Multi-commodity metering (water, gas, electric grid)"
    },
    "R-106": {
        "title": "Decentralized Wastewater Treatment 2025",
        "publisher": "Cognitive Market Research",
        "sector": "Infrastructure",
        "year": 2024,
        "access": "paid",
        "coverage": "Decentralized modular wastewater recycling"
    }
}


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
            report_meta = REPORT_METADATA_REGISTRY.get(report_id, {
                "title": filename,
                "publisher": "Unknown",
                "sector": "General",
                "year": 2024,
                "access": "paid",
                "coverage": "Market study"
            })

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
                            "title": str(report_meta["title"]),
                            "publisher": str(report_meta["publisher"]),
                            "sector": str(report_meta["sector"]),
                            "year": int(report_meta["year"]),
                            "access": str(report_meta["access"]),
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
        total_chunks = self._collection.count()
        logger.info(
            "report_ingestion_completed documents=%s chunks=%s",
            len(documents),
            total_chunks,
        )
        return total_chunks

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
        allowed_reports = list(set(purchased_reports + ["R-104"]))

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

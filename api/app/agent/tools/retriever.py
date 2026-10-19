"""
LlamaIndex + FastEmbed (BAAI/bge-small-en-v1.5) + ChromaDB Ingestion and Entitlement Retriever.

Features:
- Ingests all 6 generated PDF market reports (R-101 to R-106).
- Preserves trap documents and metadata (report_id, sector, region, year, page).
- Implements strict client entitlement filtering before any retrieved context reaches the agent/LLM.
"""

import os
import hashlib
import logging
import chromadb
import pymupdf
from typing import List, Dict, Any, Optional, Sequence, Tuple
from pydantic import BaseModel
import pypdf

from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator

from app.core.config import settings
from app.core.observability import observe_with_tags
from app.db.session import get_db_connection
from app.db.metadata import (
    fetch_report_metadata,
    get_public_report_ids,
    register_runtime_report,
    stable_document_id,
)

_stable_document_id = stable_document_id
from app.agent.tools.hybrid import TFIDFIndex, reciprocal_rank_fusion
from app.agent.tools.reranker import get_reranker
from app.agent.tools.chart_extractor import extract_and_summarize_charts_from_pdf

CHROMA_PATH = settings.CHROMA_PERSIST_DIRECTORY
REPORTS_DIR = settings.REPORTS_DIR
COLLECTION_NAME = "project_atlas_reports"
logger = logging.getLogger("project_atlas.retriever")

# Configure global LlamaIndex embedding model using BGE-Small ONNX
Settings.embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)


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
    _sparse_index: Optional[TFIDFIndex] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EntitlementRetriever, cls).__new__(cls)
            cls._instance._sparse_index = TFIDFIndex()
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

        # Hydrate sparse TF-IDF index from existing Chroma collection chunks
        if self._collection is not None and self._sparse_index is not None and self._collection.count() > 0:
            existing = self._collection.get(include=["documents", "metadatas"])
            doc_ids = existing.get("ids") or []
            documents = existing.get("documents") or []
            metadatas = existing.get("metadatas") or []
            for did, doc_text, meta in zip(doc_ids, documents, metadatas):
                if doc_text and meta:
                    self._sparse_index.add_document(
                        doc_id=did,
                        report_id=str(meta.get("report_id", "UNKNOWN")),
                        page=int(str(meta.get("page", 1))),
                        text=doc_text,
                        title=str(meta.get("title", "")),
                        sector=str(meta.get("sector", "")),
                        access=str(meta.get("access", "paid")),
                    )
            logger.info("sparse_tfidf_index_hydrated chunks=%s", len(doc_ids))

        logger.info(
            "vector_store_initialized collection=%s chunks=%s",
            COLLECTION_NAME,
            self._collection.count() if self._collection else 0,
        )


    def ingest_reports(self, force_reload: bool = False) -> int:
        collection = self._collection
        if collection is None:
            raise RuntimeError("The report vector collection is not initialized.")
        current_count = collection.count()

        if not os.path.isdir(REPORTS_DIR):
            raise RuntimeError(f"Report directory does not exist: {REPORTS_DIR}")

        pdf_files = [
            f for f in os.listdir(REPORTS_DIR)
            if f.lower().endswith(".pdf")
        ]
        expected_report_ids = {filename.split("_")[0] for filename in pdf_files}
        indexed_metadata = collection.get(include=["metadatas"]).get("metadatas") or []
        indexed_report_ids = {
            str(item.get("report_id"))
            for item in indexed_metadata
            if item and item.get("report_id")
        }
        indexed_chart_report_ids = {
            str(item.get("report_id"))
            for item in indexed_metadata
            if item and item.get("type") == "chart" and item.get("report_id")
        }
        expected_chart_report_ids = set()
        for filename in pdf_files:
            pdf_path = os.path.join(REPORTS_DIR, filename)
            with pymupdf.open(pdf_path) as pdf:
                if any(page.get_images(full=True) for page in pdf):
                    expected_chart_report_ids.add(filename.split("_")[0])

        target_report_ids = (
            expected_report_ids - indexed_report_ids
        ) | (
            expected_chart_report_ids - indexed_chart_report_ids
        )
        if current_count > 0 and not force_reload and not target_report_ids:
            logger.info(
                "report_ingestion_skipped reason=corpus_already_indexed chunks=%s reports=%s",
                current_count,
                len(expected_report_ids),
            )
            return current_count

        if force_reload:
            target_report_ids = expected_report_ids

        documents = []

        logger.info("report_ingestion_started files=%s", len(pdf_files))
        for filename in sorted(pdf_files):
            report_id = filename.split("_")[0]
            if current_count > 0 and not force_reload and report_id not in target_report_ids:
                continue
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
                        id_=_stable_document_id(report_id, page_num, page_text),
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

                # Extract and index multimodal visual charts from the report PDF
                try:
                    chart_chunks = extract_and_summarize_charts_from_pdf(
                        pdf_path=file_path,
                        report_id=report_id,
                        report_title=str(report_meta.get("title", filename)),
                    )
                    for c_info in chart_chunks:
                        c_doc = Document(
                            text=c_info["text"],
                            id_=_stable_document_id(
                                report_id,
                                c_info["page"],
                                c_info["text"],
                                kind="chart",
                            ),
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
                            }
                        )
                        documents.append(c_doc)
                    if chart_chunks:
                        logger.info("multimodal_charts_ingested report_id=%s count=%s", report_id, len(chart_chunks))
                except Exception as chart_err:
                    logger.warning("multimodal_chart_ingestion_skipped report_id=%s error=%s", report_id, chart_err)
            except Exception as e:
                logger.exception(
                    "report_pdf_parse_failed file=%s error_type=%s",
                    filename,
                    type(e).__name__,
                )

        if not documents:
            logger.error("report_ingestion_failed reason=no_documents files=%s", len(pdf_files))
            raise RuntimeError("No report pages were available to index.")

        if force_reload and current_count > 0:
            logger.warning("report_ingestion_force_reload deleting_existing_chunks=%s", current_count)
            chroma_client = self._chroma_client
            if chroma_client is None:
                raise RuntimeError("The Chroma client is not initialized.")
            collection_name = collection.name
            chroma_client.delete_collection(collection_name)
            collection = chroma_client.get_or_create_collection(collection_name)
            self._collection = collection
            self._sparse_index = TFIDFIndex()
        elif current_count > 0:
            for report_id in target_report_ids:
                collection.delete(where={"report_id": report_id})
                if self._sparse_index is not None:
                    self._sparse_index.remove_report(report_id)

        collection = self._collection
        if collection is None:
            raise RuntimeError("The report vector collection is not initialized.")
        logger.info("report_index_build_started documents=%s", len(documents))
        self._index = VectorStoreIndex.from_documents(
            documents,
            storage_context=StorageContext.from_defaults(
                vector_store=ChromaVectorStore(chroma_collection=collection)
            ),
            show_progress=True
        )
        total_chunks = collection.count()
        if self._sparse_index is not None:
            for doc in documents:
                meta = doc.metadata or {}
                self._sparse_index.add_document(
                    doc_id=doc.id_,
                    report_id=str(meta.get("report_id", "UNKNOWN")),
                    page=int(str(meta.get("page", 1))),
                    text=doc.text,
                    title=str(meta.get("title", "")),
                    sector=str(meta.get("sector", "")),
                    access=str(meta.get("access", "paid")),
                )
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
        content: str,
        pages: Optional[Sequence[Tuple[int, str]]] = None,
    ) -> int:
        """
        Ingest page-aware text chunks. Unpaginated content is treated as one source page.
        """
        source_pages = list(pages) if pages else [(1, content)]
        page_paragraphs = [
            (page_number, paragraph.strip())
            for page_number, page_content in source_pages
            for paragraph in page_content.split("\n\n")
            if paragraph.strip()
        ]
        if not page_paragraphs:
            return 0

        documents = []
        for page_number, para in page_paragraphs:
            document_id = _stable_document_id(report_id, page_number, para)
            doc = Document(
                text=para,
                id_=document_id,
                metadata={
                    "report_id": report_id,
                    "page": page_number,
                    "title": title,
                    "publisher": publisher,
                    "published": published_date,
                    "sector": sector,
                    "access": access_tier,
                }
            )
            documents.append(doc)

        year_val = 2024
        if published_date and len(published_date) >= 4 and published_date[:4].isdigit():
            year_val = int(published_date[:4])

        register_runtime_report(report_id, {
            "title": title,
            "publisher": publisher,
            "sector": sector,
            "published": published_date,
            "year": year_val,
            "access": access_tier,
            "coverage": f"{sector} market coverage"
        })

        existing_ids: set[str] = set()
        if self._index is not None and self._collection is not None:
            existing = self._collection.get(
                where={"report_id": report_id},
                include=["metadatas"],
            )
            existing_ids = set(existing.get("ids") or [])
            try:
                for document in documents:
                    self._index.insert(document)
            except Exception:
                current = self._collection.get(
                    where={"report_id": report_id},
                    include=["metadatas"],
                )
                added_ids = set(current.get("ids") or []) - existing_ids
                if added_ids:
                    self._collection.delete(ids=list(added_ids))
                logger.exception("document_vector_ingestion_failed report_id=%s", report_id)
                raise

            current = self._collection.get(
                where={"report_id": report_id},
                include=["metadatas"],
            )
            stale_ids = existing_ids.intersection(set(current.get("ids") or []))
            if stale_ids:
                self._collection.delete(ids=list(stale_ids))

        if self._sparse_index is not None:
            self._sparse_index.remove_report(report_id)
            for d in documents:
                self._sparse_index.add_document(
                    doc_id=d.id_,
                    report_id=report_id,
                    page=int(d.metadata["page"]),
                    text=d.text,
                    title=title,
                    sector=sector,
                    access=access_tier,
                )

        logger.info("document_ingested report_id=%s chunks=%s", report_id, len(documents))
        return len(documents)

    @observe_with_tags(
        name="entitlement_filtered_retrieval",
        as_type="retriever",
        tags=["tool:retriever", "retrieval:entitlement-filtered", "retrieval:hybrid-rrf"],
    )
    def retrieve_for_client(
        self,
        query: str,
        purchased_reports: List[str],
        top_k: int = 5
    ) -> List[RetrievedChunk]:
        """
        Hybrid entitlement-filtered retrieval: combines dense vector search
        (FastEmbed/ChromaDB) and sparse lexical search (TF-IDF) using Reciprocal Rank Fusion (RRF).
        Guarantees that chunks from unpurchased reports are excluded across both retrieval paths.
        """
        # Always allow public excerpts in addition to purchased reports
        public_reports = get_public_report_ids()
        allowed_reports = sorted(list(set(purchased_reports + public_reports)))

        # Edge case protection: ChromaDB raises ValueError if $in operand is empty list
        if not allowed_reports:
            logger.info("vector_retrieval_empty_allowed_reports query=%s", query)
            return []

        if self._index is None:
            logger.warning("vector_retrieval_empty_collection query=%s", query)
            return []

        # If using genuine Chroma collection (not a mock in unit tests) and it has 0 items
        is_mock_index = type(self._index).__name__ in ("Mock", "MagicMock")
        if self._collection and not is_mock_index and self._collection.count() == 0:
            logger.warning("vector_retrieval_empty_collection query=%s", query)
            return []

        # 1. Dense Vector Retrieval (Candidate pool: top_k * 2)
        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="report_id",
                    operator=FilterOperator.IN,
                    value=allowed_reports
                )
            ]
        )

        candidate_k = max(top_k * 2, 10)
        dense_chunks: List[RetrievedChunk] = []
        try:
            retriever = self._index.as_retriever(
                filters=filters,
                similarity_top_k=candidate_k
            )
            nodes = retriever.retrieve(query)
            for n in nodes:
                meta = n.metadata
                dense_chunks.append(RetrievedChunk(
                    report_id=str(meta.get("report_id", "UNKNOWN")),
                    page=int(str(meta.get("page", 1))),
                    text=n.text,
                    score=float(n.score if n.score is not None else 0.0),
                    title=str(meta.get("title", "")),
                    sector=str(meta.get("sector", "")),
                    access=str(meta.get("access", "paid"))
                ))
        except Exception as exc:
            logger.exception(
                "vector_retrieval_failed error_type=%s allowed_report_count=%s",
                type(exc).__name__,
                len(allowed_reports),
            )
            raise

        # 2. Sparse TF-IDF Lexical Retrieval
        sparse_chunks: List[RetrievedChunk] = []
        if self._sparse_index is not None:
            try:
                sparse_matches = self._sparse_index.search(
                    query=query,
                    allowed_reports=allowed_reports,
                    top_k=candidate_k
                )
                for s_doc, s_score in sparse_matches:
                    sparse_chunks.append(RetrievedChunk(
                        report_id=s_doc.report_id,
                        page=s_doc.page,
                        text=s_doc.text,
                        score=float(s_score),
                        title=s_doc.title,
                        sector=s_doc.sector,
                        access=s_doc.access,
                    ))
            except Exception as exc:
                logger.warning("sparse_retrieval_failed error=%s", exc)

        # 3. Reciprocal Rank Fusion (RRF)
        if sparse_chunks and dense_chunks:
            def _chunk_key(c: RetrievedChunk) -> str:
                content_hash = hashlib.sha256(c.text.encode("utf-8")).hexdigest()
                return f"{c.report_id}::p{c.page}::{content_hash}"

            fused = reciprocal_rank_fusion(
                dense_items=dense_chunks,
                sparse_items=sparse_chunks,
                k=60,
                dense_id_fn=_chunk_key,
                sparse_id_fn=_chunk_key,
            )
            candidates = [
                RetrievedChunk(
                    report_id=item.report_id,
                    page=item.page,
                    text=item.text,
                    score=round(float(rrf_score), 4),
                    title=item.title,
                    sector=item.sector,
                    access=item.access,
                )
                for item, rrf_score in fused[:candidate_k]
            ]
        elif dense_chunks:
            candidates = dense_chunks[:candidate_k]
        elif sparse_chunks:
            candidates = sparse_chunks[:candidate_k]
        else:
            candidates = []

        # 4. Semantic Re-Ranker Stage
        reranker = get_reranker()
        final_results = reranker.rerank(query=query, candidates=candidates, top_k=top_k)

        logger.info(
            "hybrid_retrieval_completed dense_count=%s sparse_count=%s fused_count=%s allowed_report_count=%s",
            len(dense_chunks),
            len(sparse_chunks),
            len(final_results),
            len(allowed_reports),
        )
        return final_results


_retriever_instance = None

def get_retriever() -> EntitlementRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = EntitlementRetriever()
    return _retriever_instance

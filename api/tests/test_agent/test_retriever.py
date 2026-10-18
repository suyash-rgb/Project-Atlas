"""
Unit and integration tests for EntitlementRetriever and vector filtering safeguards.
"""

from unittest.mock import MagicMock, Mock, patch
import pytest

from app.agent.tools.retriever import EntitlementRetriever, RetrievedChunk, get_retriever
from app.agent.tools.hybrid import TFIDFIndex, reciprocal_rank_fusion, tokenize
from app.agent.tools.utils import fetch_report_metadata, get_public_report_ids


class FakeNode:
    def __init__(self, text: str, metadata: dict, score: float = 0.85):
        self.text = text
        self.metadata = metadata
        self.score = score


def test_retriever_singleton():
    """Verify that get_retriever returns a consistent singleton instance."""
    retriever_1 = get_retriever()
    retriever_2 = get_retriever()
    assert retriever_1 is retriever_2
    assert isinstance(retriever_1, EntitlementRetriever)


def test_retrieved_chunk_model():
    """Verify RetrievedChunk schema fields and types."""
    chunk = RetrievedChunk(
        report_id="R-101",
        page=3,
        text="Sample smart water market text",
        score=0.92,
        title="Global Smart Water Meter Market 2025",
        sector="Utilities",
        access="paid",
    )
    assert chunk.report_id == "R-101"
    assert chunk.page == 3
    assert chunk.score == 0.92
    assert chunk.access == "paid"


def test_retrieve_for_client_filters_by_entitlements(monkeypatch):
    """
    Verify that retrieve_for_client constructs proper metadata filters
    incorporating purchased reports + public excerpts and returns mapped chunks.
    """
    retriever = get_retriever()

    mock_nodes = [
        FakeNode("R-101 snippet", {"report_id": "R-101", "page": 4, "title": "R-101", "sector": "Utilities", "access": "paid"}, 0.9),
        FakeNode("R-102 public snippet", {"report_id": "R-102", "page": 2, "title": "R-102", "sector": "Utilities", "access": "public excerpt"}, 0.82),
    ]

    mock_query_retriever = Mock()
    mock_query_retriever.retrieve = Mock(return_value=mock_nodes)

    mock_index = Mock()
    mock_index.as_retriever = Mock(return_value=mock_query_retriever)
    monkeypatch.setattr(retriever, "_index", mock_index)
    monkeypatch.setattr(retriever, "_sparse_index", None)

    results = retriever.retrieve_for_client(
        query="smart water metering market size",
        purchased_reports=["R-101"],
        top_k=5,
    )

    assert len(results) == 2
    assert results[0].report_id == "R-101"
    assert results[0].page == 4
    assert results[1].report_id == "R-102"
    assert results[1].access == "public excerpt"

    # Verify that as_retriever received filters containing R-101 and public reports (R-102, R-105)
    call_args = retriever._index.as_retriever.call_args
    filters_arg = call_args[1]["filters"]
    filter_value = filters_arg.filters[0].value
    assert "R-101" in filter_value
    assert "R-102" in filter_value
    assert "R-105" in filter_value


def test_retrieve_for_client_empty_allowed_reports_returns_empty_safely(monkeypatch):
    """
    Guarantees ChromaDB does not throw ValueError on an empty list operand.
    """
    retriever = get_retriever()
    monkeypatch.setattr("app.agent.tools.retriever.get_public_report_ids", lambda: [])

    # Passing empty purchased and empty public reports
    results = retriever.retrieve_for_client("test query", purchased_reports=[])
    assert results == []


def test_retrieve_for_client_uninitialized_or_empty_collection(monkeypatch):
    """Verify that an empty vector collection safely returns empty list without error."""
    retriever = get_retriever()
    mock_coll = Mock()
    mock_coll.count = Mock(return_value=0)
    monkeypatch.setattr(retriever, "_collection", mock_coll)

    results = retriever.retrieve_for_client("market size", purchased_reports=["R-101"])
    assert results == []


def test_ingest_document_content_splits_paragraphs_and_indexes(monkeypatch):
    """Verify document ingestion splits paragraphs, sets metadata, and inserts into index."""
    retriever = get_retriever()
    mock_index = Mock()
    mock_index.insert = Mock()
    monkeypatch.setattr(retriever, "_index", mock_index)

    sample_content = (
        "This is paragraph one containing more than twenty characters of test research content.\n\n"
        "This is paragraph two providing distinct forward looking projection details."
    )

    chunks_count = retriever.ingest_document_content(
        report_id="R-999",
        title="Custom Test Report 2025",
        publisher="Atlas Research Labs",
        published_date="2025-06-01",
        sector="Cleantech",
        access_tier="paid",
        content=sample_content,
    )

    assert chunks_count == 2
    assert mock_index.insert.call_count == 2

    # Verify metadata registry registration
    meta = fetch_report_metadata("R-999")
    assert meta["title"] == "Custom Test Report 2025"
    assert meta["publisher"] == "Atlas Research Labs"
    assert meta["year"] == 2025
    assert meta["access"] == "paid"


def test_ingest_document_content_empty_content_returns_zero():
    """Verify that empty or whitespace content returns 0 without inserting."""
    retriever = get_retriever()
    assert retriever.ingest_document_content("R-000", "Empty", "Pub", "2025-01-01", "Sec", "paid", "") == 0
    assert retriever.ingest_document_content("R-000", "Empty", "Pub", "2025-01-01", "Sec", "paid", "   \n\n  ") == 0


def test_sparse_tfidf_tokenization_and_filtering():
    """Verify TF-IDF indexing, stop-word removal, and strict entitlement filtering."""
    idx = TFIDFIndex()
    idx.add_document(
        doc_id="doc1",
        report_id="R-101",
        page=1,
        text="The smart water market is projected to reach USD 4.21 B with a 11.8% CAGR.",
        title="Report 101",
        sector="Utilities",
        access="paid",
    )
    idx.add_document(
        doc_id="doc2",
        report_id="R-103",
        page=5,
        text="Industrial IoT and smart water sensors deployment in APAC.",
        title="Report 103",
        sector="IoT",
        access="paid",
    )

    # Search with allowed report R-101 only
    results_r101 = idx.search("smart water CAGR", allowed_reports=["R-101"])
    assert len(results_r101) == 1
    doc, score = results_r101[0]
    assert doc.report_id == "R-101"
    assert score > 0.0

    # Search with allowed report R-103 only (R-101 should not be returned even though it matches)
    results_r103 = idx.search("smart water", allowed_reports=["R-103"])
    assert len(results_r103) == 1
    assert results_r103[0][0].report_id == "R-103"

    # Search for term that only exists in R-101 but querying with only R-103 allowed
    results_empty = idx.search("CAGR", allowed_reports=["R-103"])
    assert len(results_empty) == 0


def test_reciprocal_rank_fusion_math():
    """Verify RRF reciprocal score formula and multi-source boost."""
    class MockItem:
        def __init__(self, item_id: str):
            self.item_id = item_id

    dense_candidates = [MockItem("docA"), MockItem("docB"), MockItem("docC")]
    sparse_candidates = [MockItem("docB"), MockItem("docA"), MockItem("docD")]

    fused = reciprocal_rank_fusion(
        dense_items=dense_candidates,
        sparse_items=sparse_candidates,
        k=60,
        dense_id_fn=lambda x: x.item_id,
        sparse_id_fn=lambda x: x.item_id,
    )

    fused_ids = [item.item_id for item, _ in fused]
    # docA and docB appear in both dense and sparse, so they must rank higher than docC and docD
    assert set(fused_ids[:2]) == {"docA", "docB"}
    assert set(fused_ids[2:]) == {"docC", "docD"}

    # Exact score check for docA: dense rank 1 (1/61) + sparse rank 2 (1/62)
    score_map = {item.item_id: score for item, score in fused}
    expected_doc_a = (1.0 / 61) + (1.0 / 62)
    assert abs(score_map["docA"] - expected_doc_a) < 1e-6


def test_hybrid_retriever_exact_keyword_boost(monkeypatch):
    """
    Verify that hybrid search with RRF boosts documents with exact keyword matches
    (e.g., exact report ID or metric) even when dense vector ranking alone would rank them lower.
    """
    retriever = get_retriever()

    # Dense returns doc2 first, then doc1
    dense_node_1 = FakeNode("General smart utility metering overview", {"report_id": "R-101", "page": 1, "title": "R-101", "sector": "Utilities", "access": "paid"}, 0.95)
    dense_node_2 = FakeNode("Exact USD 4.21 B CAGR target analysis", {"report_id": "R-101", "page": 8, "title": "R-101", "sector": "Utilities", "access": "paid"}, 0.85)

    mock_query_retriever = Mock()
    mock_query_retriever.retrieve = Mock(return_value=[dense_node_1, dense_node_2])
    mock_index = Mock()
    mock_index.as_retriever = Mock(return_value=mock_query_retriever)
    monkeypatch.setattr(retriever, "_index", mock_index)

    # Sparse index heavily favors page 8 for "CAGR 4.21"
    sparse_idx = TFIDFIndex()
    sparse_idx.add_document("c1", "R-101", 1, "General smart utility metering overview")
    sparse_idx.add_document("c2", "R-101", 8, "Exact USD 4.21 B CAGR target analysis")
    monkeypatch.setattr(retriever, "_sparse_index", sparse_idx)

    results = retriever.retrieve_for_client(
        query="4.21 B CAGR",
        purchased_reports=["R-101"],
        top_k=2,
    )

    assert len(results) == 2
    # The exact keyword match on page 8 should be boosted by RRF to rank 1
    assert results[0].page == 8
    assert results[0].score > results[1].score

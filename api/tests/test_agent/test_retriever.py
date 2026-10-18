"""
Unit and integration tests for EntitlementRetriever and vector filtering safeguards.
"""

from unittest.mock import MagicMock, Mock, patch
import pytest

from app.agent.tools.retriever import EntitlementRetriever, RetrievedChunk, get_retriever
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

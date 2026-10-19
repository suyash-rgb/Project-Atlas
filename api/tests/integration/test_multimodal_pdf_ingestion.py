import random
from pathlib import Path
from uuid import uuid4

import chromadb
import pymupdf
from llama_index.core import Settings
from llama_index.core.embeddings import MockEmbedding
from PIL import Image

from app.agent.tools import chart_extractor, retriever as retriever_module
from app.agent.tools.hybrid import TFIDFIndex

EXPECTED_REPORT_IDS = {f"R-{report_number}" for report_number in range(101, 107)}


def _make_chart_pdf(pdf_path: Path):
    rng = random.Random(31)
    pixels = bytes(rng.randrange(256) for _ in range(300 * 300 * 3))
    image = Image.frombytes("RGB", (300, 300), pixels)
    image_path = pdf_path.with_suffix(".png")
    image.save(image_path, format="PNG")

    document = pymupdf.open()
    page = document.new_page()
    page.insert_image(page.rect, filename=str(image_path))
    document.save(pdf_path)
    document.close()
    image_path.unlink()


def _make_retriever(monkeypatch):
    monkeypatch.setattr(Settings, "embed_model", MockEmbedding(embed_dim=8))
    chroma_client = chromadb.EphemeralClient()
    collection = chroma_client.get_or_create_collection(f"pdf-ingestion-{uuid4().hex}")
    test_retriever = object.__new__(retriever_module.EntitlementRetriever)
    test_retriever._collection = collection
    test_retriever._chroma_client = chroma_client
    test_retriever._index = None
    test_retriever._sparse_index = TFIDFIndex()
    return test_retriever, collection


def test_pdf_chart_is_summarized_and_indexed_with_report_page_metadata(
    tmp_path,
    isolated_sqlite_database,
    seed_report,
    monkeypatch,
):
    report_id = "R-990"
    seed_report(report_id)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    pdf_path = reports_dir / f"{report_id}_chart.pdf"
    _make_chart_pdf(pdf_path)

    monkeypatch.setattr(retriever_module, "REPORTS_DIR", str(reports_dir))
    monkeypatch.setattr(chart_extractor, "CHART_CACHE_DIR", str(tmp_path / "chart-cache"))
    monkeypatch.setattr(chart_extractor, "get_gemini_client", lambda: None)
    test_retriever, collection = _make_retriever(monkeypatch)

    indexed_count = test_retriever.ingest_reports()

    assert indexed_count == 1
    assert collection.count() == 1
    chart_document = collection.get(include=["documents", "metadatas"])
    chart_metadata = chart_document["metadatas"]
    chart_documents = chart_document["documents"]
    assert chart_metadata is not None
    assert chart_documents is not None
    metadata = chart_metadata[0]
    assert metadata["report_id"] == report_id
    assert metadata["page"] == 1
    assert metadata["type"] == "chart"
    assert "Visual Market Chart on Page 1" in chart_documents[0]

    sparse_matches = test_retriever._sparse_index.search(
        "visual market chart",
        allowed_reports=[report_id],
        top_k=5,
    )
    assert sparse_matches is not None
    assert len(sparse_matches) == 1
    assert sparse_matches[0][0].report_id == report_id
    assert sparse_matches[0][0].page == 1

    reloaded_count = test_retriever.ingest_reports(force_reload=True)
    assert reloaded_count == 1
    reloaded_collection = test_retriever._collection
    assert reloaded_collection is not None
    assert reloaded_collection.count() == 1


def test_all_repository_reports_and_embedded_charts_are_ingested(
    tmp_path,
    isolated_sqlite_database,
    monkeypatch,
):
    reports_dir = Path(retriever_module.REPORTS_DIR)
    assert reports_dir.is_dir()
    assert {
        path.name.split("_", maxsplit=1)[0]
        for path in reports_dir.glob("*.pdf")
    } == EXPECTED_REPORT_IDS

    monkeypatch.setattr(chart_extractor, "CHART_CACHE_DIR", str(tmp_path / "chart-cache"))
    monkeypatch.setattr(chart_extractor, "get_gemini_client", lambda: None)
    test_retriever, collection = _make_retriever(monkeypatch)

    indexed_count = test_retriever.ingest_reports()

    rows = collection.get(include=["metadatas"])
    metadata = rows["metadatas"]
    assert metadata is not None
    report_ids = set()
    chart_rows = []
    text_report_ids = set()
    for item in metadata:
        if not item:
            continue
        report_id = item.get("report_id")
        if isinstance(report_id, str):
            report_ids.add(report_id)
            if item.get("type") != "chart":
                text_report_ids.add(report_id)
        if item.get("type") == "chart":
            chart_rows.append(item)

    assert report_ids == EXPECTED_REPORT_IDS
    assert text_report_ids == EXPECTED_REPORT_IDS
    assert len(chart_rows) == 10
    assert {item["report_id"] for item in chart_rows} == EXPECTED_REPORT_IDS

    repeated_count = test_retriever.ingest_reports()
    assert repeated_count == indexed_count
    assert collection.count() == indexed_count

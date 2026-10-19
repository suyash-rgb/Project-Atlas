import random

import pymupdf
from PIL import Image

from app.agent.tools import chart_extractor, retriever as retriever_module
from app.agent.tools.hybrid import TFIDFIndex


class InMemoryCollection:
    def __init__(self):
        self.documents = []

    def count(self):
        return len(self.documents)


class InMemoryChromaClient:
    def __init__(self, collection):
        self.collection = collection

    def get_or_create_collection(self, _name):
        return self.collection


def _make_chart_pdf(pdf_path):
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

    collection = InMemoryCollection()
    test_retriever = object.__new__(retriever_module.EntitlementRetriever)
    test_retriever._collection = collection
    test_retriever._chroma_client = InMemoryChromaClient(collection)
    test_retriever._index = None
    test_retriever._sparse_index = TFIDFIndex()

    class InMemoryVectorStoreIndex:
        @staticmethod
        def from_documents(documents, **_kwargs):
            collection.documents.extend(documents)
            return object()

    monkeypatch.setattr(retriever_module, "VectorStoreIndex", InMemoryVectorStoreIndex)
    monkeypatch.setattr(retriever_module, "StorageContext", type(
        "StorageContextStub",
        (),
        {"from_defaults": staticmethod(lambda **_kwargs: None)},
    ))
    monkeypatch.setattr(retriever_module, "ChromaVectorStore", lambda **_kwargs: object())

    indexed_count = test_retriever.ingest_reports()

    assert indexed_count == 1
    assert collection.count() == 1
    chart_document = collection.documents[0]
    assert chart_document.metadata["report_id"] == report_id
    assert chart_document.metadata["page"] == 1
    assert chart_document.metadata["type"] == "chart"
    assert "Visual Market Chart on Page 1" in chart_document.text

    sparse_matches = test_retriever._sparse_index.search(
        "visual market chart",
        allowed_reports=[report_id],
        top_k=5,
    )
    assert len(sparse_matches) == 1
    assert sparse_matches[0][0].report_id == report_id
    assert sparse_matches[0][0].page == 1

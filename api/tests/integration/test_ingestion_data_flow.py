from types import SimpleNamespace

from llama_index.core import Settings

from app.agent import graph
from app.agent.router import RouterDecision
from app.agent.tools import retriever as retriever_module
from app.agent.tools.hybrid import TFIDFIndex
from app.agent.tools.reranker import SemanticReRanker
from app.schemas.chat import ChatResponse
from app.services import ingest_service


class InMemoryCollection:
    def __init__(self):
        self.documents = []

    def count(self):
        return len(self.documents)


class SparseOnlyVectorIndex:
    def __init__(self, collection):
        self.collection = collection

    def insert(self, document):
        self.collection.documents.append(document)

    def as_retriever(self, **_kwargs):
        return SimpleNamespace(retrieve=lambda _query: [])


def test_ingest_api_indexes_content_then_chat_retrieves_only_for_entitled_client(
    client,
    auth_headers,
    isolated_sqlite_database,
    seed_report,
    monkeypatch,
):
    report_id = "R-990"
    seed_report(report_id)
    connection = retriever_module.get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE clients SET purchased_reports = purchased_reports || ', R-990' "
            "WHERE id = %s",
            ("C-01",),
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    collection = InMemoryCollection()
    test_retriever = object.__new__(retriever_module.EntitlementRetriever)
    test_retriever._collection = collection
    test_retriever._index = SparseOnlyVectorIndex(collection)
    test_retriever._sparse_index = TFIDFIndex()
    monkeypatch.setattr(ingest_service, "get_retriever", lambda: test_retriever)
    monkeypatch.setattr(graph, "get_retriever", lambda: test_retriever)
    monkeypatch.setattr(retriever_module, "get_reranker", lambda: SemanticReRanker())
    monkeypatch.setattr(Settings, "embed_model", None)

    content = (
        "The aquaculture equipment market reached USD 5.60 billion in 2025.\n\n"
        "The report attributes growth to regional recirculating systems demand."
    )
    payload = {
        "report_id": report_id,
        "title": "Integration Chart Report",
        "publisher": "Atlas Test Publisher",
        "published_date": "2025-06-01",
        "sector": "Utilities",
        "access_tier": "paid",
        "content": content,
    }

    unauthenticated = client.post("/api/v1/ingest", json=payload)
    assert unauthenticated.status_code == 403

    ingested = client.post("/api/v1/ingest", json=payload, headers=auth_headers)
    assert ingested.status_code == 201
    assert ingested.json()["chunks_ingested"] == 2
    assert collection.count() == 2

    captured_chunks = []

    class CapturingSynthesizer:
        def synthesize(self, **kwargs):
            chunks = kwargs["retrieved_chunks"]
            captured_chunks.append(chunks)
            if chunks:
                report = chunks[0]
                return ChatResponse(
                    answer=f"Chart data is 5.60 billion [{report.report_id} p.{report.page}].",
                    citations=[f"[{report.report_id} p.{report.page}]"],
                    confidence=0.9,
                )
            return ChatResponse(
                answer="No matching report is available in this subscription.",
                confidence=0.9,
            )

    monkeypatch.setattr(
        graph,
        "classify_query",
        lambda _question: RouterDecision(
            intent="factual_lookup",
            confidence=0.99,
            is_attack=False,
            requires_escalation=False,
        ),
    )
    monkeypatch.setattr(graph, "get_synthesizer", CapturingSynthesizer)

    question = "What does the aquaculture equipment report say about market size?"
    entitled_answer = client.post(
        "/api/v1/chat",
        json={"client_id": "C-01", "question": question},
        headers=auth_headers,
    )
    unentitled_answer = client.post(
        "/api/v1/chat",
        json={"client_id": "C-02", "question": question},
        headers=auth_headers,
    )

    assert entitled_answer.status_code == 200
    assert entitled_answer.json()["answer"] == "Chart data is 5.60 billion [R-990 p.1]."
    assert captured_chunks[0]
    assert all(chunk.report_id == report_id for chunk in captured_chunks[0])
    assert unentitled_answer.status_code == 200
    assert report_id not in unentitled_answer.json()["answer"]
    assert all(chunk.report_id != report_id for chunk in captured_chunks[1])

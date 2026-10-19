import chromadb
from uuid import uuid4
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.embeddings import MockEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.agent import graph
from app.agent.router import RouterDecision
from app.agent.tools import retriever as retriever_module
from app.agent.tools.hybrid import TFIDFIndex
from app.agent.tools.reranker import SemanticReRanker
from app.schemas.chat import ChatResponse
from app.services import ingest_service


def test_ingest_api_indexes_content_then_chat_retrieves_only_for_entitled_client(
    client,
    auth_headers,
    isolated_sqlite_database,
    monkeypatch,
):
    report_id = "R-990"
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

    monkeypatch.setattr(Settings, "embed_model", MockEmbedding(embed_dim=8))
    chroma_client = chromadb.EphemeralClient()
    collection = chroma_client.get_or_create_collection(f"ingestion-chat-{uuid4().hex}")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    test_retriever = object.__new__(retriever_module.EntitlementRetriever)
    test_retriever._collection = collection
    test_retriever._index = VectorStoreIndex.from_vector_store(vector_store)
    test_retriever._sparse_index = TFIDFIndex()
    monkeypatch.setattr(ingest_service, "get_retriever", lambda: test_retriever)
    monkeypatch.setattr(graph, "get_retriever", lambda: test_retriever)
    monkeypatch.setattr(retriever_module, "get_reranker", lambda: SemanticReRanker())

    payload = {
        "report_id": report_id,
        "title": "Integration Chart Report",
        "publisher": "Atlas Test Publisher",
        "published_date": "2025-06-01",
        "sector": "Utilities",
        "access_tier": "paid",
        "pages": [
            {
                "page_number": 8,
                "content": "The aquaculture equipment market reached USD 5.60 billion in 2025.",
            },
            {
                "page_number": 11,
                "content": "Growth is attributed to regional recirculating systems demand.",
            },
        ],
    }

    unauthenticated = client.post("/api/v1/ingest", json=payload)
    assert unauthenticated.status_code == 403
    assert collection.count() == 0

    ingested = client.post("/api/v1/ingest", json=payload, headers=auth_headers)
    assert ingested.status_code == 201
    assert ingested.json()["chunks_ingested"] == 2
    assert collection.count() == 2

    # Replacing the same report must not accumulate stale dense or sparse chunks.
    repeated_ingest = client.post("/api/v1/ingest", json=payload, headers=auth_headers)
    assert repeated_ingest.status_code == 201
    assert collection.count() == 2
    assert len(test_retriever._sparse_index.documents) == 2

    connection = retriever_module.get_db_connection(readonly=True)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT title, access FROM reports WHERE id = %s", (report_id,))
        stored_report = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    assert stored_report == {
        "title": "Integration Chart Report",
        "access": "paid",
    }

    captured_chunks = []

    class CapturingSynthesizer:
        def synthesize(self, **kwargs):
            chunks = kwargs["retrieved_chunks"]
            captured_chunks.append(chunks)
            if chunks:
                report = chunks[0]
                citation = f"[{report.report_id} p.{report.page}]"
                return ChatResponse(
                    answer=f"Chart data is 5.60 billion {citation}.",
                    citations=[citation],
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
    assert "5.60 billion" in entitled_answer.json()["answer"]
    assert captured_chunks[0]
    assert all(chunk.report_id == report_id for chunk in captured_chunks[0])
    assert {chunk.page for chunk in captured_chunks[0]} <= {8, 11}
    assert unentitled_answer.status_code == 200
    assert report_id not in unentitled_answer.json()["answer"]
    assert all(chunk.report_id != report_id for chunk in captured_chunks[1])

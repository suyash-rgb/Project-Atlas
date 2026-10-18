import json
from importlib import import_module

from app.schemas.chat import ChatResponse

chat_router = import_module("app.api.v1.routers.chat")


def test_stream_endpoint_emits_tokens_then_structured_completion(
    client, auth_headers, monkeypatch
):
    def fake_process_chat_query(client_id, question, token_callback=None):
        assert client_id == "C-01"
        assert question == "What is the market size?"
        token_callback("The market ")
        token_callback("is USD 4.21B.")
        return ChatResponse(
            answer="The market is USD 4.21B.",
            citations=["[R-101 p.8]"],
            confidence=0.95,
        )

    monkeypatch.setattr(
        chat_router.chat_service,
        "process_chat_query",
        fake_process_chat_query,
    )

    response = client.post(
        "/api/v1/chat/stream",
        json={"client_id": "C-01", "query": "What is the market size?"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = response.text.strip().split("\n\n")
    assert [event.splitlines()[0] for event in events] == [
        "event: token",
        "event: token",
        "event: complete",
    ]
    assert json.loads(events[0].split("data: ", 1)[1]) == {"text": "The market "}
    final = json.loads(events[-1].split("data: ", 1)[1])["response"]
    assert final["answer"] == "The market is USD 4.21B."
    assert final["citations"] == ["[R-101 p.8]"]


def test_stream_endpoint_requires_authentication(client):
    response = client.post(
        "/api/v1/chat/stream",
        json={"client_id": "C-01", "question": "Question"},
    )

    assert response.status_code == 403


def test_stream_endpoint_rejects_empty_query_before_streaming(client, auth_headers):
    response = client.post(
        "/api/v1/chat/stream",
        json={"client_id": "C-01", "question": "   "},
        headers=auth_headers,
    )

    assert response.status_code == 400

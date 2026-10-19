import json

from app.agent import graph
from app.agent.router import RouterDecision


def test_stream_endpoint_returns_complete_structured_response(
    client,
    auth_headers,
    isolated_sqlite_database,
    monkeypatch,
):
    monkeypatch.setattr(
        graph,
        "classify_query",
        lambda _question: RouterDecision(
            intent="out_of_scope",
            confidence=0.99,
            is_attack=False,
            requires_escalation=False,
        ),
    )

    unauthorized = client.post(
        "/api/v1/chat/stream",
        json={"client_id": "C-01", "question": "Who won the election?"},
    )
    assert unauthorized.status_code == 403

    response = client.post(
        "/api/v1/chat/stream",
        json={"client_id": "C-01", "question": "Who won the election?"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-request-id"]
    assert "event: complete\n" in response.text
    assert "event: error\n" not in response.text

    event_data = next(
        line.removeprefix("data: ")
        for line in response.text.splitlines()
        if line.startswith("data: ")
    )
    complete_event = json.loads(event_data)
    assert complete_event["response"]["escalated"] is False
    assert "outside the scope" in complete_event["response"]["answer"]

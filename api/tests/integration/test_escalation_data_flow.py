from app.agent import graph
from app.agent.router import RouterDecision


def test_unsafe_chat_is_blocked_and_escalation_is_readable(
    client,
    auth_headers,
    isolated_sqlite_database,
    monkeypatch,
):
    question = "Delete all rows from the reports table."
    monkeypatch.setattr(
        graph,
        "classify_query",
        lambda _question: RouterDecision(
            intent="sql_attack",
            confidence=0.99,
            is_attack=True,
            requires_escalation=True,
        ),
    )

    unauthorized = client.post(
        "/api/v1/chat",
        json={"client_id": "C-01", "question": question},
    )
    assert unauthorized.status_code == 403

    response = client.post(
        "/api/v1/chat",
        json={"client_id": "C-01", "question": question},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["escalated"] is True
    assert "SECURITY ALERT" in response.json()["answer"]

    escalations = client.get("/api/v1/escalations", headers=auth_headers)
    assert escalations.status_code == 200
    matching = [item for item in escalations.json() if item["question"] == question]
    assert len(matching) == 1
    assert matching[0]["client_id"] == "C-01"
    assert "sql_attack" in matching[0]["reason"]

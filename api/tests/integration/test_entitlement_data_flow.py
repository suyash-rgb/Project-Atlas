from app.agent import graph
from app.agent.router import RouterDecision
from app.schemas.chat import ChatResponse


def test_chat_aggregate_only_passes_entitled_and_public_reports_to_writer(
    client,
    auth_headers,
    isolated_sqlite_database,
    monkeypatch,
):
    captured_sql_rows = []

    class CapturingSynthesizer:
        def synthesize(self, **kwargs):
            captured_sql_rows.extend(kwargs["sql_data"])
            report_ids = sorted(row.get("id", row.get("report")) for row in kwargs["sql_data"])
            return ChatResponse(
                answer=f"Available reports: {', '.join(report_ids)}",
                citations=[],
                confidence=0.9,
            )

    monkeypatch.setattr(
        graph,
        "classify_query",
        lambda _question: RouterDecision(
            intent="database_aggregate",
            confidence=0.99,
            is_attack=False,
            requires_escalation=False,
        ),
    )
    monkeypatch.setattr(graph, "get_synthesizer", CapturingSynthesizer)

    response = client.post(
        "/api/v1/chat",
        json={"client_id": "C-02", "question": "How many reports are available?"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert {row["id"] for row in captured_sql_rows} == {"R-102", "R-103", "R-105"}
    assert "R-101" not in response.json()["answer"]
    assert "R-102" in response.json()["answer"]
    assert "R-103" in response.json()["answer"]
    assert "R-105" in response.json()["answer"]

import json
import time
from unittest.mock import Mock, patch
import pytest
from app.schemas.chat import ChatResponse
from app.agent.router import RouterDecision


def test_mock_streaming_tokens_in_sequence(client, auth_headers):
    """
    Validates that incremental tokens stream sequentially as Server-Sent Events,
    followed by the final complete structured payload with metadata.
    """
    mock_tokens = [
        "According to ",
        "Cognitive Market Research ",
        "report R-101, ",
        "the smart water meter market ",
        "is projected to reach ",
        "USD 6.84B by 2030."
    ]

    def mock_process_chat_query(client_id, question, token_callback=None):
        assert client_id == "C-01"
        for token in mock_tokens:
            if token_callback:
                token_callback(token)
        return ChatResponse(
            answer="".join(mock_tokens),
            citations=["[R-101 p.8]"],
            confidence=0.96,
            derived_values=[
                {
                    "metric": "2024-2030 CAGR",
                    "estimated_value": "8.4%",
                    "formula": "((End/Start)^(1/n) - 1)",
                    "assumptions": ["Constant currency"]
                }
            ],
            conflicts=[],
            escalated=False
        )

    with patch("app.api.v1.routers.chat.chat_service.process_chat_query", side_effect=mock_process_chat_query):
        response = client.post(
            "/api/v1/chat/stream",
            json={"client_id": "C-01", "question": "What is the 2030 projection in R-101?"},
            headers=auth_headers
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    # Parse raw SSE events separated by double newlines
    raw_blocks = [b.strip() for b in response.text.strip().split("\n\n") if b.strip()]
    
    # We expect 6 token events + 1 complete event = 7 events total
    assert len(raw_blocks) == len(mock_tokens) + 1

    received_tokens = []
    complete_event = None

    for block in raw_blocks:
        lines = block.splitlines()
        event_name = lines[0].removeprefix("event: ")
        data_json = json.loads(lines[1].removeprefix("data: "))

        if event_name == "token":
            received_tokens.append(data_json["text"])
        elif event_name == "complete":
            complete_event = data_json["response"]

    assert received_tokens == mock_tokens
    assert complete_event is not None
    assert complete_event["answer"] == "".join(mock_tokens)
    assert complete_event["confidence"] == 0.96
    assert complete_event["citations"] == ["[R-101 p.8]"]
    assert len(complete_event["derived_values"]) == 1
    assert complete_event["derived_values"][0]["metric"] == "2024-2030 CAGR"


def test_mock_streaming_divergence_and_conflict_handling(client, auth_headers):
    """
    Validates streaming response when cross-report conflicts and methodology
    divergence are detected between reports (e.g. R-101 vs R-102).
    """
    conflict_tokens = [
        "Comparing R-101 and R-102 reveals a scope divergence: ",
        "R-101 ($4.21B) measures pure IoT endpoint hardware, ",
        "whereas R-102 ($3.87B) includes utility billing software suites."
    ]

    def mock_conflict_query(client_id, question, token_callback=None):
        for token in conflict_tokens:
            if token_callback:
                token_callback(token)
        return ChatResponse(
            answer="".join(conflict_tokens),
            citations=["[R-101 p.8]", "[R-102 p.14]"],
            confidence=0.89,
            conflicts=[
                {
                    "metric": "2024 Market Size Divergence",
                    "reports": ["R-101", "R-102"],
                    "description": "R-101 reports $4.21B while R-102 reports $3.87B",
                    "scope_differences": "Hardware endpoints vs software integration suite"
                }
            ],
            escalated=False
        )

    with patch("app.api.v1.routers.chat.chat_service.process_chat_query", side_effect=mock_conflict_query):
        response = client.post(
            "/api/v1/chat/stream",
            json={"client_id": "C-01", "question": "Compare R-101 and R-102 market sizes"},
            headers=auth_headers
        )

    assert response.status_code == 200
    events = [b.strip() for b in response.text.strip().split("\n\n") if b.strip()]
    assert len(events) == 4  # 3 tokens + 1 complete

    complete_payload = json.loads(events[-1].splitlines()[1].removeprefix("data: "))["response"]
    assert len(complete_payload["conflicts"]) == 1
    assert complete_payload["conflicts"][0]["metric"] == "2024 Market Size Divergence"
    assert len(complete_payload["citations"]) == 2

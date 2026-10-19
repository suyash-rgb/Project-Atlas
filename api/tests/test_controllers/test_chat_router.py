import logging
from unittest.mock import patch
from app.schemas.chat import ChatResponse


class TestChatRouter:
    def test_chat_without_api_key_returns_403(self, client):
        response = client.post("/api/v1/chat", json={"client_id": "C-01", "question": "test"})
        assert response.status_code == 403
        data = response.json()
        assert "Invalid or missing API Key" in data["detail"]

    def test_invalid_api_key_is_logged_without_logging_the_key(self, client, caplog):
        supplied_key = "sensitive-invalid-test-key"
        with caplog.at_level(logging.WARNING, logger="project_atlas.auth"):
            response = client.post(
                "/api/v1/chat/stream",
                json={"client_id": "C-01", "question": "test"},
                headers={"X-API-Key": supplied_key},
            )

        assert response.status_code == 403
        assert "reason=invalid_key" in caplog.text
        assert "request_id=" in caplog.text
        assert supplied_key not in caplog.text
        assert response.headers["x-request-id"]

    def test_chat_returns_503_when_api_key_is_not_configured(self, client, monkeypatch, caplog):
        from app.core.config import settings

        monkeypatch.setattr(settings, "API_KEY", None)
        with caplog.at_level(logging.ERROR, logger="project_atlas.auth"):
            response = client.post("/api/v1/chat", json={"client_id": "C-01", "question": "test"})

        assert response.status_code == 503
        assert response.json()["detail"] == "API authentication is not configured"
        assert "reason=server_key_not_configured" in caplog.text
        assert response.headers["x-request-id"] in caplog.text

    def test_chat_with_empty_question_returns_400(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"client_id": "C-01", "question": "   "},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "question cannot be empty" in response.json()["detail"]

    def test_chat_with_missing_client_id_returns_422(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat",
            json={"question": "What is the market size?"},
            headers=auth_headers
        )
        assert response.status_code == 422

    @patch("app.services.chat_service.chat_service.process_chat_query")
    def test_chat_valid_query_returns_200(self, mock_process, client, auth_headers, sample_chat_response):
        mock_process.return_value = sample_chat_response

        response = client.post(
            "/api/v1/chat",
            json={
                "client_id": "C-01",
                "question": "What about 2030?",
                "conversation_history": [
                    {"role": "user", "content": "What was the R-101 market size?"},
                    {"role": "assistant", "content": "The market was USD 4.21B [R-101 p.8]."},
                ],
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "USD 4.21B" in data["answer"]
        assert len(data["citations"]) == 1
        assert data["citations"][0] == "[R-101 p.8]"
        assert data["confidence"] == 0.95
        assert len(data["conflicts"]) == 1
        mock_process.assert_called_once_with(
            client_id="C-01",
            question="What about 2030?",
            conversation_history=[
                {"role": "user", "content": "What was the R-101 market size?"},
                {"role": "assistant", "content": "The market was USD 4.21B [R-101 p.8]."},
            ],
        )

    @patch("app.services.chat_service.chat_service.process_chat_query")
    def test_chat_timeout_returns_504(self, mock_process, client, auth_headers):
        mock_process.side_effect = TimeoutError("Synthesis upstream timed out")

        response = client.post(
            "/api/v1/chat",
            json={"client_id": "C-01", "question": "Calculate projection"},
            headers=auth_headers
        )
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]

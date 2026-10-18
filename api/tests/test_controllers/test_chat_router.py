from unittest.mock import patch
from app.schemas.chat import ChatResponse


class TestChatRouter:
    def test_chat_without_api_key_returns_403(self, client):
        response = client.post("/api/v1/chat", json={"client_id": "C-01", "question": "test"})
        assert response.status_code == 403
        data = response.json()
        assert "Invalid or missing API Key" in data["detail"]

    def test_chat_returns_503_when_api_key_is_not_configured(self, client, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "API_KEY", None)
        response = client.post(
            "/api/v1/chat",
            json={"client_id": "C-01", "question": "test"},
            headers={"X-API-Key": "pytest-only-api-key"},
        )

        assert response.status_code == 503
        assert response.json()["detail"] == "API authentication is not configured"

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
            json={"client_id": "C-01", "question": "What was the 2024 market size?"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "USD 4.21B" in data["answer"]
        assert len(data["citations"]) == 1
        assert data["citations"][0] == "[R-101 p.8]"
        assert data["confidence"] == 0.95
        assert len(data["conflicts"]) == 1

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

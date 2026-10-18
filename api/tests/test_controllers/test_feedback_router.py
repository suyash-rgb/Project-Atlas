from unittest.mock import patch


class TestFeedbackRouter:
    def test_feedback_without_auth_returns_403(self, client):
        response = client.post(
            "/api/v1/feedback",
            json={"client_id": "C-01", "rating": "up"}
        )
        assert response.status_code == 403

    @patch(
        "app.api.v1.routers.feedback.feedback_service.record_feedback",
        return_value={"status": "success", "message": "Feedback recorded."},
    )
    def test_feedback_valid_payload_returns_201_created(self, _record_feedback, client, auth_headers):
        response = client.post(
            "/api/v1/feedback",
            json={
                "client_id": "C-01",
                "message_id": "msg_router_test_01",
                "rating": "up",
                "comment": "Accurate numbers and citation badges"
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Feedback recorded."

    def test_feedback_invalid_rating_returns_400(self, client, auth_headers):
        response = client.post(
            "/api/v1/feedback",
            json={
                "client_id": "C-01",
                "rating": "mediocre"
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Invalid rating" in response.json()["detail"]

    def test_feedback_missing_rating_returns_422(self, client, auth_headers):
        response = client.post(
            "/api/v1/feedback",
            json={"client_id": "C-01"},
            headers=auth_headers
        )
        assert response.status_code == 422

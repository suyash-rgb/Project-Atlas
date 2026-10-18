from unittest.mock import patch


class TestEscalationRouter:
    def test_escalations_without_auth_returns_403(self, client):
        response = client.get("/api/v1/escalations")
        assert response.status_code == 403

    @patch("app.api.v1.routers.escalations.escalation_service.get_all_escalations", return_value=[])
    def test_escalations_with_auth_returns_200(self, _get_escalations, client, auth_headers):
        response = client.get("/api/v1/escalations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            item = data[0]
            assert "id" in item
            assert "client_id" in item
            assert "question" in item
            assert "reason" in item
            assert "status" in item

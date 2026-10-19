from unittest.mock import patch
from app.schemas.chat import IngestResponse


class TestIngestRouter:
    def test_ingest_without_api_key_returns_403(self, client):
        response = client.post(
            "/api/v1/ingest",
            json={
                "report_id": "R-999",
                "title": "Test Title",
                "publisher": "Test Pub",
                "published_date": "2025-01-01",
                "sector": "Water",
                "access_tier": "paid",
                "content": "Sample content for testing document ingestion."
            }
        )
        assert response.status_code == 403
        assert "Invalid or missing API Key" in response.json()["detail"]

    def test_ingest_empty_report_id_returns_400(self, client, auth_headers):
        response = client.post(
            "/api/v1/ingest",
            json={
                "report_id": "   ",
                "title": "Test Title",
                "publisher": "Test Pub",
                "published_date": "2025-01-01",
                "sector": "Water",
                "access_tier": "paid",
                "content": "Sample content for testing."
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "report_id cannot be empty" in response.json()["detail"]

    def test_ingest_empty_content_returns_400(self, client, auth_headers):
        response = client.post(
            "/api/v1/ingest",
            json={
                "report_id": "R-999",
                "title": "Test Title",
                "publisher": "Test Pub",
                "published_date": "2025-01-01",
                "sector": "Water",
                "access_tier": "paid",
                "content": "   "
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "content cannot be empty" in response.json()["detail"]

    @patch("app.api.v1.routers.ingest.ingest_service.ingest_report")
    def test_ingest_valid_payload_returns_201(self, mock_ingest, client, auth_headers):
        mock_ingest.return_value = IngestResponse(
            status="success",
            report_id="R-999",
            chunks_ingested=3,
            message="Report R-999 ingested successfully (3 chunks indexed)."
        )
        response = client.post(
            "/api/v1/ingest",
            json={
                "report_id": "R-999",
                "title": "Smart Meter Report",
                "publisher": "Global Analytics",
                "published_date": "2025-01-01",
                "sector": "Utilities",
                "access_tier": "paid",
                "content": "Section 1 text. Section 2 text. Section 3 text."
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["report_id"] == "R-999"
        assert data["chunks_ingested"] == 3

    @patch("app.api.v1.routers.ingest.ingest_service.ingest_report")
    def test_ingest_service_failure_returns_500(self, mock_ingest, client, auth_headers):
        mock_ingest.side_effect = RuntimeError("ChromaDB index unreachable")
        response = client.post(
            "/api/v1/ingest",
            json={
                "report_id": "R-999",
                "title": "Smart Meter Report",
                "publisher": "Global Analytics",
                "published_date": "2025-01-01",
                "sector": "Utilities",
                "access_tier": "paid",
                "content": "Section 1 text."
            },
            headers=auth_headers
        )
        assert response.status_code == 500
        assert response.json()["detail"] == "Ingestion failed. Check the server logs for details."
        assert "ChromaDB index unreachable" not in response.json()["detail"]

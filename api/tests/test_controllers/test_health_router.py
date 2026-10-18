from unittest.mock import patch
from app.schemas.chat import HealthResponse


class TestHealthRouter:
    @patch("app.api.v1.routers.health.health_service.check_health")
    def test_get_api_v1_health_returns_200(self, mock_check, client):
        mock_check.return_value = HealthResponse(
            status="healthy",
            version="1.0.0",
            database="connected",
            vector_store="ready (1 chunks indexed)",
        )
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in {"healthy", "degraded"}
        assert "version" in data
        assert "database" in data
        assert "vector_store" in data

    def test_get_root_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_url_redirects_to_docs(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code in {307, 302, 301}
        assert response.headers["location"] == "/docs"

    def test_api_v1_docs_redirects_to_docs(self, client):
        response = client.get("/api/v1/docs", follow_redirects=False)
        assert response.status_code in {307, 302, 301}
        assert response.headers["location"] == "/docs"

    @patch("app.services.health_service.health_service.check_health")
    def test_degraded_health_emits_503(self, mock_check, client):
        mock_check.return_value = HealthResponse(
            status="degraded",
            version="1.0.0",
            database="not_found",
            vector_store="error: connection refused"
        )
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "not_found"

    def test_get_health_metrics_returns_200(self, client):
        response = client.get("/api/v1/health/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "avg_latency_ms" in data
        assert "cache_hit_rate" in data
        assert "total_tokens_consumed" in data
        assert "storage_footprint_mb" in data
        assert data["storage_footprint_mb"] == 0.0

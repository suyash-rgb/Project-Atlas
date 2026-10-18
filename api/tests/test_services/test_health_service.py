import os
from unittest.mock import patch, MagicMock
from app.services.health_service import HealthService
from app.schemas.chat import HealthResponse


class TestHealthService:
    def setup_method(self):
        self.service = HealthService()

    def test_check_health_online(self):
        health = self.service.check_health()
        assert isinstance(health, HealthResponse)
        assert health.status in {"healthy", "degraded"}
        assert health.database == "connected"
        assert "ready" in health.vector_store

    @patch("app.services.health_service.os.path.exists")
    def test_check_health_degraded_when_db_missing(self, mock_exists):
        mock_exists.return_value = False
        health = self.service.check_health()
        assert health.status == "degraded"
        assert health.database == "not_found"

    @patch("app.services.health_service.get_retriever")
    def test_check_health_degraded_when_vector_store_fails(self, mock_retriever):
        mock_retriever.side_effect = Exception("ChromaDB connection refused")
        health = self.service.check_health()
        assert health.status == "degraded"
        assert "error" in health.vector_store

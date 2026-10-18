import os
from app.core.config import settings
from app.db.session import DB_PATH
from app.schemas.chat import HealthResponse
from app.agent.tools.retriever import get_retriever


class HealthService:
    """
    Service monitoring subsystem readiness, relational DB status, and vector DB metrics.
    """

    def check_health(self) -> HealthResponse:
        """
        Executes diagnostic probes across DB, vector index, and runtime environment.
        Determines whether the service is fully healthy or degraded.
        """
        db_exists = os.path.exists(DB_PATH)
        db_status = "connected" if db_exists else "not_found"

        vector_ok = False
        try:
            retriever = get_retriever()
            count = retriever._collection.count() if retriever._collection is not None else 0
            v_status = f"ready ({count} chunks indexed)"
            vector_ok = True
        except Exception as e:
            v_status = f"error: {str(e)}"

        overall_status = "healthy" if (db_exists and vector_ok) else "degraded"

        return HealthResponse(
            status=overall_status,
            version=settings.VERSION,
            database=db_status,
            vector_store=v_status
        )


health_service = HealthService()

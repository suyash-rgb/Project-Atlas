import logging

from app.core.config import settings
from app.db.session import get_db_connection
from app.schemas.chat import HealthResponse
from app.agent.tools.retriever import get_retriever

logger = logging.getLogger(__name__)


class HealthService:
    """
    Service monitoring subsystem readiness, relational DB status, and vector DB metrics.
    """

    def check_health(self) -> HealthResponse:
        """
        Executes diagnostic probes across DB, vector index, and runtime environment.
        Determines whether the service is fully healthy or degraded.
        """
        db_connected = False
        try:
            conn = get_db_connection(readonly=True)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT 1")
                db_connected = cursor.fetchone() is not None
            finally:
                cursor.close()
                conn.close()
        except Exception as exc:
            logger.warning("mysql_readiness_probe_failed error_type=%s", type(exc).__name__)
            db_connected = False

        db_status = "connected" if db_connected else "unavailable"

        vector_ok = False
        try:
            retriever = get_retriever()
            count = retriever._collection.count() if retriever._collection is not None else 0
            v_status = f"ready ({count} chunks indexed)"
            vector_ok = True
        except Exception as exc:
            logger.exception("vector_store_readiness_probe_failed error_type=%s", type(exc).__name__)
            v_status = f"error: {type(exc).__name__}"

        overall_status = "healthy" if (db_connected and vector_ok) else "degraded"

        return HealthResponse(
            status=overall_status,
            version=settings.VERSION,
            database=db_status,
            vector_store=v_status
        )


health_service = HealthService()

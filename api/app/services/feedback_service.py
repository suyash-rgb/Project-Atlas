import logging
from typing import Optional
from app.db.session import get_db_connection
from app.schemas.chat import FeedbackResponse

logger = logging.getLogger("project_atlas.feedback")


class FeedbackService:
    """
    Service handling client satisfaction ratings and qualitative feedback persistence.
    """

    def record_feedback(
        self,
        client_id: str,
        rating: str,
        message_id: Optional[str] = "msg_live",
        comment: Optional[str] = None
    ) -> FeedbackResponse:
        """
        Persists qualitative feedback and ratings to the database.
        Validates input constraints and rating validity.
        """
        if not client_id or not client_id.strip():
            raise ValueError("client_id is required")

        normalized_rating = rating.strip().lower()
        if normalized_rating not in {"up", "down"}:
            raise ValueError(f"Invalid rating '{rating}'. Allowed values are 'up' or 'down'")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                conn.start_transaction()
                cursor.execute(
                    "INSERT INTO feedback (client_id, message_id, rating, comment) "
                    "VALUES (%s, %s, %s, %s)",
                    (client_id.strip(), message_id or "msg_live", normalized_rating, comment or "")
                )
                conn.commit()
            except Exception as exc:
                conn.rollback()
                logger.exception(
                    "feedback_write_failed client_id=%s error_type=%s",
                    client_id.strip(),
                    type(exc).__name__,
                )
                raise
            finally:
                cursor.close()
                conn.close()
            return FeedbackResponse(status="success", message="Feedback recorded.")
        except Exception as e:
            logger.exception(
                "feedback_persistence_failed client_id=%s error_type=%s",
                client_id.strip(),
                type(e).__name__,
            )
            raise RuntimeError("Failed to persist feedback.") from e


feedback_service = FeedbackService()

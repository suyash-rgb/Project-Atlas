import os
import sqlite3
from typing import Optional
from app.db.session import DB_PATH, get_db_connection
from app.schemas.chat import FeedbackResponse


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
            cursor.execute(
                "INSERT INTO feedback (client_id, message_id, rating, comment) VALUES (?, ?, ?, ?)",
                (client_id.strip(), message_id or "msg_live", normalized_rating, comment or "")
            )
            conn.commit()
            cursor.close()
            conn.close()
            return FeedbackResponse(status="success", message="Feedback recorded.")
        except Exception as e:
            raise RuntimeError(f"Failed to persist feedback: {str(e)}")


feedback_service = FeedbackService()

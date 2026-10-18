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
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (client_id, message_id, rating, comment) VALUES (?, ?, ?, ?)",
            (client_id, message_id or "msg_live", rating, comment or "")
        )
        conn.commit()
        cursor.close()
        conn.close()
        return FeedbackResponse(status="success", message="Feedback recorded.")


feedback_service = FeedbackService()

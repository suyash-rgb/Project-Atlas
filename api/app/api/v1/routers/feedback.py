import os
import sqlite3
from fastapi import APIRouter, Security
from app.api.deps import verify_api_key
from app.schemas.chat import FeedbackRequest, FeedbackResponse
from app.agent.tools.sql_tool import DB_PATH

router = APIRouter(prefix="/feedback", tags=["Feedback & Analytics"])


@router.post("", response_model=FeedbackResponse, summary="Record client thumbs-up/down feedback")
async def submit_feedback(fb: FeedbackRequest, _auth: str = Security(verify_api_key)):
    """
    Persists thumbs-up or thumbs-down ratings to the SQLite feedback table.
    Enables tracking of citation accuracy, user sentiment, and synthesis quality.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO feedback (client_id, message_id, rating, comment) VALUES (?, ?, ?, ?)",
        (fb.client_id, fb.message_id or "msg_live", fb.rating, fb.comment or "")
    )
    conn.commit()
    cursor.close()
    conn.close()
    return FeedbackResponse(status="success", message="Feedback recorded.")

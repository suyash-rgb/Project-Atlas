import os
import sqlite3
from typing import List
from datetime import datetime
from fastapi import APIRouter, Security
from app.api.deps import verify_api_key
from app.schemas.chat import EscalationItem
from app.agent.tools.sql_tool import DB_PATH

router = APIRouter(prefix="/escalations", tags=["Escalations & Human-in-the-Loop"])


@router.get("", response_model=List[EscalationItem], summary="List escalated tickets")
async def get_escalations(_auth: str = Security(verify_api_key)):
    """
    Returns all escalated tickets recorded for human analyst review.
    Tickets are created automatically when:
    - Adversarial prompt injection or SQL injection attacks are detected
    - Confidence falls below threshold or forecast windows exceed boundaries
    """
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, client_id, question, reason, status, created_at "
        "FROM escalations ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    items = []
    for r in rows:
        created_val = r["created_at"]
        if isinstance(created_val, str):
            try:
                created_dt = datetime.fromisoformat(created_val)
            except Exception:
                created_dt = datetime.now()
        else:
            created_dt = datetime.now()

        items.append(EscalationItem(
            id=r["id"],
            client_id=r["client_id"],
            question=r["question"],
            reason=r["reason"],
            status=r["status"] or "pending",
            created_at=created_dt
        ))
    return items

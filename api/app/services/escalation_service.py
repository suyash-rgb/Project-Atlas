import os
import sqlite3
from typing import List, Optional
from datetime import datetime
from app.db.session import DB_PATH, get_db_connection
from app.schemas.chat import EscalationItem


class EscalationService:
    """
    Service handling human analyst escalation queues and incident reporting.
    Decouples database operations and business logic from API controllers.
    """

    def get_all_escalations(self, limit: int = 100) -> List[EscalationItem]:
        """
        Retrieves recent escalations ordered by latest timestamp.
        Gracefully handles date parsing and missing database tables.
        """
        if not os.path.exists(DB_PATH):
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, client_id, question, reason, status, created_at "
            "FROM escalations ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        items: List[EscalationItem] = []
        for r in rows:
            created_val = r["created_at"]
            if isinstance(created_val, str):
                try:
                    created_dt = datetime.fromisoformat(created_val)
                except Exception:
                    created_dt = datetime.now()
            elif isinstance(created_val, datetime):
                created_dt = created_val
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

    def log_escalation(
        self,
        client_id: str,
        question: str,
        reason: str,
        status: str = "pending"
    ) -> int:
        """
        Records a new human-in-the-loop escalation ticket.
        Returns the created ticket ID.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO escalations (client_id, question, reason, status) "
            "VALUES (?, ?, ?, ?)",
            (client_id, question, reason, status)
        )
        conn.commit()
        ticket_id = cursor.lastrowid or 0
        cursor.close()
        conn.close()
        return ticket_id


escalation_service = EscalationService()

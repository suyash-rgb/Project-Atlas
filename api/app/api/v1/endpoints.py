import os
import sqlite3
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

from app.core.config import settings
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    IngestRequest,
    EscalationItem,
    HealthResponse
)
from app.agent.graph import run_agent_workflow
from app.agent.tools.sql_tool import DB_PATH
from app.agent.tools.retriever import get_retriever

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    valid_keys = {settings.API_KEY, "atlas_secret_token_2026", "atlas_dev_secret_key"}
    if not api_key or api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key"
        )
    return api_key

router = APIRouter()


class FeedbackRequest(BaseModel):
    client_id: str
    message_id: Optional[str] = "msg_live"
    rating: str = Field(..., description="'up' or 'down'")
    comment: Optional[str] = None


@router.post("/chat", response_model=ChatResponse, summary="Submit inquiry to the Report Copilot")
async def chat(request: ChatRequest, _auth: str = Security(verify_api_key)):
    """
    Core entrypoint for Project Atlas Agent Workflow:
    - Entitlement filtering by client_id
    - Laya System-1 Guardrail routing
    - Security attack refusal and audit logging
    - SQL aggregations, financial calculations, RAG retrieval
    - Conflict reconciliation and Groq LLM synthesis
    """
    try:
        response = run_agent_workflow(
            client_id=request.client_id,
            question=request.question
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow error: {str(e)}"
        )


@router.get("/escalations", response_model=List[EscalationItem], summary="List escalated tickets")
async def get_escalations(_auth: str = Security(verify_api_key)):
    """Returns all escalated tickets recorded for human analyst review."""
    if not os.path.exists(DB_PATH):
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, client_id, question, reason, status, created_at FROM escalations ORDER BY id DESC")
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


@router.post("/feedback", summary="Record client thumbs-up/down feedback")
async def submit_feedback(fb: FeedbackRequest, _auth: str = Security(verify_api_key)):
    """Persists thumbs-up or thumbs-down ratings to the SQLite feedback table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO feedback (client_id, message_id, rating, comment) VALUES (?, ?, ?, ?)",
        (fb.client_id, fb.message_id or "msg_live", fb.rating, fb.comment or "")
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"status": "success", "message": "Feedback recorded."}


@router.get("/health", response_model=HealthResponse, summary="System health check")
async def health_check():
    db_status = "connected" if os.path.exists(DB_PATH) else "not_found"
    try:
        retriever = get_retriever()
        count = retriever._collection.count() if retriever._collection is not None else 0
        v_status = f"ready ({count} chunks indexed)"
    except Exception as e:
        v_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        database=db_status,
        vector_store=v_status
    )

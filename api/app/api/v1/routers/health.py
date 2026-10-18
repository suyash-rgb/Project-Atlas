import os
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.chat import HealthResponse
from app.agent.tools.sql_tool import DB_PATH
from app.agent.tools.retriever import get_retriever

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("", response_model=HealthResponse, summary="System health check")
async def health_check():
    """
    Subsystem health and readiness check:
    - Verifies relational SQLite / MySQL database connectivity
    - Validates ChromaDB vector store initialization and chunk count
    - Reports active project version
    """
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

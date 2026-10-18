from fastapi import APIRouter, Security, HTTPException, status
from app.api.deps import verify_api_key
from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.graph import run_agent_workflow

router = APIRouter(prefix="/chat", tags=["Chat & Agent Copilot"])


@router.post("", response_model=ChatResponse, summary="Submit inquiry to the Report Copilot")
async def chat(request: ChatRequest, _auth: str = Security(verify_api_key)):
    """
    Core entrypoint for Project Atlas Agent Workflow:
    - Entitlement filtering by client_id
    - Laya 421M System-1 Guardrail routing
    - Security attack refusal and audit logging
    - SQL aggregations, financial calculations, RAG retrieval
    - Conflict reconciliation and LLM synthesis
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

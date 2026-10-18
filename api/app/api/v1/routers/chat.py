from fastapi import APIRouter, Security, HTTPException, status
from app.api.deps import verify_api_key
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["Chat & Agent Copilot"])


@router.post("", response_model=ChatResponse, summary="Submit inquiry to the Report Copilot")
async def chat(request: ChatRequest, _auth: str = Security(verify_api_key)):
    """
    HTTP Controller for Report Copilot conversational queries.
    Delegates processing and business logic to ChatService.
    """
    try:
        return chat_service.process_chat_query(
            client_id=request.client_id,
            question=request.question
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow error: {str(e)}"
        )

from fastapi import APIRouter, Security, HTTPException, status
from app.api.deps import verify_api_key
from app.schemas.chat import ChatRequest, ChatResponse, ErrorResponse
from app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["Chat & Agent Copilot"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit inquiry to the Report Copilot",
    responses={
        200: {
            "model": ChatResponse,
            "description": "Successful conversational agent response with citations and metadata"
        },
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - invalid or empty question / client_id"
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - invalid or missing X-API-Key"
        },
        503: {
            "model": ErrorResponse,
            "description": "Service Unavailable - API authentication is not configured"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal Server Error - agent workflow execution failure"
        },
        504: {
            "model": ErrorResponse,
            "description": "Gateway Timeout - agent or LLM synthesis timed out"
        }
    }
)
async def chat(request: ChatRequest, _auth: str = Security(verify_api_key)):
    """
    HTTP Controller for Report Copilot conversational queries.
    - Validates payload and client identity.
    - Delegates processing and business logic to ChatService.
    - Translates domain exceptions into standard HTTP error responses.
    """
    try:
        return chat_service.process_chat_query(
            client_id=request.client_id,
            question=request.question
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except TimeoutError as te:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Query processing timed out: {str(te)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow error: {str(e)}"
        )

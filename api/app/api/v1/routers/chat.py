import json
import queue
import threading

from fastapi import APIRouter, Security, HTTPException, status
from fastapi.responses import StreamingResponse
from app.api.deps import verify_api_key
from app.schemas.chat import ChatRequest, ChatResponse, ErrorResponse
from app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["Chat & Agent Copilot"])


def _encode_sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


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


@router.post(
    "/stream",
    summary="Stream the Report Copilot answer",
    response_class=StreamingResponse,
    responses={
        200: {"description": "Server-Sent Events containing answer tokens and final metadata"},
        400: {"model": ErrorResponse, "description": "Invalid or empty question / client_id"},
        403: {"model": ErrorResponse, "description": "Forbidden - invalid or missing X-API-Key"},
        503: {"model": ErrorResponse, "description": "Service Unavailable - API authentication is not configured"},
    },
)
async def stream_chat(request: ChatRequest, _auth: str = Security(verify_api_key)):
    """Stream synthesis tokens, then emit the complete structured response."""
    if not request.client_id.strip():
        raise HTTPException(status_code=400, detail="client_id cannot be empty")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty or whitespace only")

    events = queue.Queue()

    def process_query():
        try:
            response = chat_service.process_chat_query(
                client_id=request.client_id,
                question=request.question,
                token_callback=lambda token: events.put(("token", {"text": token})),
            )
            events.put(("complete", {"response": response.model_dump(mode="json")}))
        except ValueError as exc:
            events.put(("error", {"message": str(exc), "code": 400}))
        except TimeoutError:
            events.put(("error", {"message": "Query processing timed out.", "code": 504}))
        except Exception:
            events.put(("error", {"message": "Agent workflow failed.", "code": 500}))
        finally:
            events.put((None, None))

    def event_stream():
        worker = threading.Thread(target=process_query, daemon=True)
        worker.start()
        while True:
            event, payload = events.get()
            if event is None:
                break
            yield _encode_sse(event, payload)
        worker.join()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )

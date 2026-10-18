from fastapi import APIRouter, Security, HTTPException, status
from app.api.deps import verify_api_key
from app.schemas.chat import FeedbackRequest, FeedbackResponse, ErrorResponse
from app.services.feedback_service import feedback_service

router = APIRouter(prefix="/feedback", tags=["Feedback & Analytics"])


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record client thumbs-up/down feedback",
    responses={
        201: {
            "model": FeedbackResponse,
            "description": "Feedback recorded successfully"
        },
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - invalid rating value or missing client_id"
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
            "description": "Internal Server Error - database write failure"
        }
    }
)
async def submit_feedback(fb: FeedbackRequest, _auth: str = Security(verify_api_key)):
    """
    HTTP Controller for rating submissions.
    - Validates payload constraints and rating syntax.
    - Persists feedback via FeedbackService.
    - Returns HTTP 201 Created on success.
    """
    try:
        return feedback_service.record_feedback(
            client_id=fb.client_id,
            rating=fb.rating,
            message_id=fb.message_id,
            comment=fb.comment
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback persistence error: {str(e)}"
        )

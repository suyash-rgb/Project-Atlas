from fastapi import APIRouter, Security
from app.api.deps import verify_api_key
from app.schemas.chat import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import feedback_service

router = APIRouter(prefix="/feedback", tags=["Feedback & Analytics"])


@router.post("", response_model=FeedbackResponse, summary="Record client thumbs-up/down feedback")
async def submit_feedback(fb: FeedbackRequest, _auth: str = Security(verify_api_key)):
    """
    HTTP Controller for rating submissions.
    Delegates persistence to FeedbackService.
    """
    return feedback_service.record_feedback(
        client_id=fb.client_id,
        rating=fb.rating,
        message_id=fb.message_id,
        comment=fb.comment
    )

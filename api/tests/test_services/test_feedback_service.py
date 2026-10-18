import pytest
from app.services.feedback_service import FeedbackService
from app.schemas.chat import FeedbackResponse


class TestFeedbackService:
    def setup_method(self):
        self.service = FeedbackService()

    def test_record_feedback_up_success(self):
        res = self.service.record_feedback(
            client_id="C-01",
            rating="up",
            message_id="msg_test_01",
            comment="Accurate citation"
        )
        assert isinstance(res, FeedbackResponse)
        assert res.status == "success"
        assert res.message == "Feedback recorded."

    def test_record_feedback_down_success(self):
        res = self.service.record_feedback(
            client_id="C-02",
            rating="DOWN",  # Tests case normalization
            message_id="msg_test_02",
            comment="Scope difference needed more details"
        )
        assert res.status == "success"

    def test_empty_client_id_raises_value_error(self):
        with pytest.raises(ValueError, match="client_id is required"):
            self.service.record_feedback(client_id="", rating="up")

    def test_invalid_rating_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid rating 'neutral'"):
            self.service.record_feedback(client_id="C-01", rating="neutral")

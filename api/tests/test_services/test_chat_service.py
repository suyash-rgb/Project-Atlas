import pytest
from unittest.mock import patch
from app.services.chat_service import ChatService
from app.schemas.chat import ChatResponse


class TestChatService:
    def setup_method(self):
        self.service = ChatService()

    def test_empty_client_id_raises_value_error(self):
        with pytest.raises(ValueError, match="client_id cannot be empty"):
            self.service.process_chat_query(client_id="", question="What is market size?")

    def test_whitespace_client_id_raises_value_error(self):
        with pytest.raises(ValueError, match="client_id cannot be empty"):
            self.service.process_chat_query(client_id="   ", question="What is market size?")

    def test_empty_question_raises_value_error(self):
        with pytest.raises(ValueError, match="question cannot be empty"):
            self.service.process_chat_query(client_id="C-01", question="")

    def test_whitespace_question_raises_value_error(self):
        with pytest.raises(ValueError, match="question cannot be empty"):
            self.service.process_chat_query(client_id="C-01", question="   \n\t  ")

    @patch("app.services.chat_service.run_agent_workflow")
    def test_valid_query_delegates_to_agent_workflow(self, mock_workflow, sample_chat_response):
        mock_workflow.return_value = sample_chat_response

        response = self.service.process_chat_query(client_id="c-01", question="What is CAGR?")
        assert isinstance(response, ChatResponse)
        assert response.confidence == 0.95
        assert len(response.citations) == 1
        assert response.citations[0] == "[R-101 p.8]"
        mock_workflow.assert_called_once_with(client_id="C-01", question="What is CAGR?")

    @patch("app.services.chat_service.run_agent_workflow")
    def test_agent_timeout_propagates(self, mock_workflow):
        mock_workflow.side_effect = TimeoutError("Groq API synthesis timeout")

        with pytest.raises(TimeoutError, match="Groq API synthesis timeout"):
            self.service.process_chat_query(client_id="C-01", question="What is CAGR?")

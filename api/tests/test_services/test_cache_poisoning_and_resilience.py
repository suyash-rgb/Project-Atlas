"""
Unit tests for Cache Poisoning Defense, multi-tenant cache isolation,
and upstream API resilience in ChatService.
"""

import pytest
from unittest.mock import Mock, patch

from app.services.chat_service import ChatService
from app.schemas.chat import ChatResponse
from app.core.telemetry import telemetry
from app.core.semantic_cache import semantic_cache


class TestCachePoisoningAndResilience:
    def setup_method(self):
        self.service = ChatService()
        telemetry.cache.clear()
        semantic_cache.clear()

    @patch("app.services.chat_service.run_agent_workflow")
    def test_escalated_response_never_cached(self, mock_workflow):
        """
        CRITICAL SECURITY & RELIABILITY GUARD:
        Escalated responses (e.g. low confidence or security violations) must NEVER
        be stored in exact LRU cache or vector semantic cache, preventing cache poisoning.
        """
        escalated_resp = ChatResponse(
            answer="[SECURITY ALERT] Your query has been flagged and blocked.",
            citations=[],
            confidence=1.0,
            escalated=True,
            escalation_ticket_id="ESC-9999",
        )
        mock_workflow.return_value = escalated_resp

        client = "C-01"
        query = "DROP TABLE reports"

        # Execute query
        response = self.service.process_chat_query(client_id=client, question=query)

        assert response.escalated is True
        # Verify it was NOT written to telemetry.cache
        assert telemetry.cache.get(client, query) is None
        # Verify it was NOT written to semantic_cache
        assert semantic_cache.get(client, query) is None

    @patch("app.services.chat_service.run_agent_workflow")
    def test_clarification_response_never_cached(self, mock_workflow):
        """Responses asking for user clarification must never be cached."""
        clarification_resp = ChatResponse(
            answer="Which sector are you referring to: smart water or wastewater?",
            citations=[],
            confidence=0.0,
            clarification_needed=True,
        )
        mock_workflow.return_value = clarification_resp

        client = "C-01"
        query = "What is the market size?"

        response = self.service.process_chat_query(client_id=client, question=query)

        assert response.clarification_needed is True
        assert telemetry.cache.get(client, query) is None
        assert semantic_cache.get(client, query) is None

    @patch("app.services.chat_service.run_agent_workflow")
    def test_clean_response_is_cached(self, mock_workflow, sample_chat_response):
        """Normal, non-escalated responses must be cached in both layers."""
        mock_workflow.return_value = sample_chat_response

        client = "C-01"
        query = "What is the smart water CAGR?"

        response = self.service.process_chat_query(client_id=client, question=query)

        assert response.escalated is False
        # Exact LRU cache contains response
        assert telemetry.cache.get(client, query) is not None
        # Semantic cache contains response
        cached_sem = semantic_cache.get(client, query)
        assert cached_sem is not None
        assert cached_sem["answer"] == sample_chat_response.answer

    @patch("app.services.chat_service.run_agent_workflow")
    def test_multi_tenant_cache_isolation(self, mock_workflow, sample_chat_response):
        """Cache for Client C-01 must never be accessible or returned to Client C-02."""
        mock_workflow.return_value = sample_chat_response

        query = "What is the 2024 smart water market size?"

        # Client C-01 queries and populates cache
        self.service.process_chat_query(client_id="C-01", question=query)
        assert telemetry.cache.get("C-01", query) is not None

        # Client C-02 queries same question: must NOT hit C-01's cache
        assert telemetry.cache.get("C-02", query) is None
        assert semantic_cache.get("C-02", query) is None

    @patch("app.services.chat_service.run_agent_workflow")
    def test_conversation_context_bypasses_cache_write_and_read(
        self, mock_workflow, sample_chat_response
    ):
        """Conversational multi-turn queries must never read from or write to query caches."""
        mock_workflow.return_value = sample_chat_response
        history = [
            {"role": "user", "content": "Tell me about R-101"},
            {"role": "assistant", "content": "R-101 covers smart water meters."},
        ]

        follow_up = "What about APAC?"
        response = self.service.process_chat_query(
            client_id="C-01",
            question=follow_up,
            conversation_history=history,
        )

        assert response is sample_chat_response
        assert telemetry.cache.get("C-01", follow_up) is None
        assert semantic_cache.get("C-01", follow_up) is None

    @patch("app.services.chat_service.run_agent_workflow")
    def test_service_resilience_propagates_timeout(self, mock_workflow):
        """Verify TimeoutError is properly logged and propagated for HTTP 504 / gateway translation."""
        mock_workflow.side_effect = TimeoutError("Request timed out")

        with pytest.raises(TimeoutError):
            self.service.process_chat_query(client_id="C-01", question="Complex calculation")

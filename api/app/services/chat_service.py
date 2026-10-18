import logging
from typing import Optional
from app.schemas.chat import ChatResponse
from app.agent.graph import run_agent_workflow

logger = logging.getLogger("project_atlas.chat_service")


class ChatService:
    """
    Service orchestrating the Report Copilot agentic pipeline.
    Acts as the single point of entry for conversational querying,
    state initialization, telemetry, and error normalization.
    """

    def process_chat_query(self, client_id: str, question: str) -> ChatResponse:
        """
        Executes the LangGraph agent state machine:
        1. System-1 Laya 421M Guardrail routing
        2. Prompt injection & SQL attack interception
        3. Entitlement-scoped retrieval and SQL tool execution
        4. CAGR deterministic math engine
        5. Conflict reconciliation & LLM synthesis
        """
        if not client_id or not client_id.strip():
            raise ValueError("client_id cannot be empty")

        if not question or not question.strip():
            raise ValueError("question cannot be empty or whitespace only")

        cleaned_client = client_id.strip().upper()
        cleaned_question = question.strip()

        logger.info(f"Processing query for client={cleaned_client}: {cleaned_question[:60]}...")

        try:
            response: ChatResponse = run_agent_workflow(
                client_id=cleaned_client,
                question=cleaned_question
            )
            return response
        except TimeoutError as te:
            logger.error(f"Agent pipeline timeout for client {cleaned_client}: {te}")
            raise
        except Exception as e:
            logger.error(f"Agent pipeline execution failure: {e}", exc_info=True)
            raise


chat_service = ChatService()

import logging
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
        logger.info(f"Processing query for client={client_id}: {question[:60]}...")
        response: ChatResponse = run_agent_workflow(
            client_id=client_id,
            question=question
        )
        return response


chat_service = ChatService()

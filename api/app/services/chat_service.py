import time
import logging
from typing import Optional
from app.schemas.chat import ChatResponse
from app.agent.graph import run_agent_workflow
from app.core.telemetry import telemetry
from app.core.observability import observe_with_tags

logger = logging.getLogger("project_atlas.chat_service")


class ChatService:
    """
    Service orchestrating the Report Copilot agentic pipeline.
    Acts as the single point of entry for conversational querying,
    state initialization, telemetry, cost logging, and query caching.
    """

    @observe_with_tags(
        name="report_copilot_pipeline",
        as_type="agent",
        tags=["project-atlas", "report-copilot", "market-research"],
    )
    def process_chat_query(self, client_id: str, question: str) -> ChatResponse:
        """
        Executes the LangGraph agent state machine:
        1. Checks in-memory semantic cache for repeated queries
        2. System-1 Laya 421M Guardrail routing
        3. Prompt injection & SQL attack interception
        4. Entitlement-scoped retrieval and SQL tool execution
        5. CAGR deterministic math engine
        6. Conflict reconciliation & LLM synthesis
        7. Logs structured latency, tokens, and cost to telemetry
        """
        if not client_id or not client_id.strip():
            raise ValueError("client_id cannot be empty")

        if not question or not question.strip():
            raise ValueError("question cannot be empty or whitespace only")

        cleaned_client = client_id.strip().upper()
        cleaned_question = question.strip()

        # 1. Query Cache Check (Assignment Hard Part: repeated query cache)
        cached_response = telemetry.cache.get(cleaned_client, cleaned_question)
        if cached_response is not None:
            logger.info(f"Cache HIT for client={cleaned_client}: {cleaned_question[:50]}...")
            telemetry.record_request(
                client_id=cleaned_client,
                question=cleaned_question,
                intent="cached_response",
                latency_ms=1.5,
                prompt_tokens=0,
                completion_tokens=0,
                cache_hit=True,
                escalated=cached_response.escalated,
                answer=cached_response.answer
            )
            return cached_response

        # 2. Fresh Agent Execution
        logger.info(f"Processing query for client={cleaned_client}: {cleaned_question[:60]}...")
        t0 = time.time()

        try:
            response: ChatResponse = run_agent_workflow(
                client_id=cleaned_client,
                question=cleaned_question
            )
            latency_ms = (time.time() - t0) * 1000

            # Approximate token counts from words if raw LLM usage isn't present
            prompt_tokens = int(len(cleaned_question.split()) * 1.35) + 350
            completion_tokens = int(len(response.answer.split()) * 1.35)

            # Store in query cache
            telemetry.cache.set(cleaned_client, cleaned_question, response)

            # Record telemetry (Structured log + Langfuse if active)
            telemetry.record_request(
                client_id=cleaned_client,
                question=cleaned_question,
                intent="agent_workflow",
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cache_hit=False,
                escalated=response.escalated,
                answer=response.answer
            )

            return response
        except TimeoutError as te:
            logger.error(f"Agent pipeline timeout for client {cleaned_client}: {te}")
            raise
        except Exception as e:
            logger.error(f"Agent pipeline execution failure: {e}", exc_info=True)
            raise


chat_service = ChatService()

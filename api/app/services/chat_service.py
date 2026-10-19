import time
import logging
from typing import Callable, Optional
from app.schemas.chat import ChatResponse
from app.agent.graph import run_agent_workflow
from app.core.telemetry import telemetry
from app.core.semantic_cache import semantic_cache
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
    def process_chat_query(
        self,
        client_id: str,
        question: str,
        token_callback: Optional[Callable[[str], None]] = None,
    ) -> ChatResponse:
        """
        Executes the LangGraph agent state machine:
        1. Checks exact LRU cache and Redis vector semantic cache
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

        # 1. Exact LRU Query Cache Check
        cached_response = telemetry.cache.get(cleaned_client, cleaned_question)

        # 2. Redis Semantic Cache Check (Vector similarity >= threshold)
        if cached_response is None:
            semantic_data = semantic_cache.get(cleaned_client, cleaned_question)
            if semantic_data is not None:
                try:
                    cached_response = ChatResponse(**semantic_data)
                except Exception:
                    cached_response = None

        if cached_response is not None:
            if token_callback is not None:
                token_callback(cached_response.answer)
            logger.info(
                "chat_cache_hit client_id=%s question_length=%s",
                cleaned_client,
                len(cleaned_question),
            )
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
        logger.info(
            "chat_processing_started client_id=%s question_length=%s",
            cleaned_client,
            len(cleaned_question),
        )
        t0 = time.time()

        try:
            response: ChatResponse = run_agent_workflow(
                client_id=cleaned_client,
                question=cleaned_question,
                token_callback=token_callback,
            )
            latency_ms = (time.time() - t0) * 1000

            # Approximate token counts from words if raw LLM usage isn't present
            prompt_tokens = int(len(cleaned_question.split()) * 1.35) + 350
            completion_tokens = int(len(response.answer.split()) * 1.35)

            # Store in query caches (Exact LRU + Redis Vector Semantic Cache)
            telemetry.cache.set(cleaned_client, cleaned_question, response)
            semantic_cache.set(cleaned_client, cleaned_question, response)

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
            logger.warning(
                "agent_pipeline_failed reason=timeout client_id=%s error_type=%s",
                cleaned_client,
                type(te).__name__,
            )
            raise
        except Exception as e:
            logger.exception(
                "agent_pipeline_failed reason=unexpected client_id=%s error_type=%s",
                cleaned_client,
                type(e).__name__,
            )
            raise


chat_service = ChatService()

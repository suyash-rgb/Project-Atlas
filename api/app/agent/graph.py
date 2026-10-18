"""
LangGraph Agent Workflow for Project Atlas - Report Copilot.

Orchestrates:
1. Laya 421M System-1 Guardrail Router (Sub-40ms entry gate)
2. Security Audit & Escalation Node (Immediate refusal & DB logging for attacks)
3. AST-Validated Read-Only SQL Node (Catalog and metric aggregations)
4. Deterministic Financial Calculator (CAGR, 2030 projections)
5. Entitlement-Aware ChromaDB Vector Retriever (Strict client report filtering)
6. Discrepancy & Scope Reconciler (R-101 Turnkey vs R-102 Hardware-only)
7. LLM Synthesizer (Executive answers with verified citations)
"""

from typing import Callable, List, Dict, Any, Optional
import logging
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig

from app.schemas.chat import ChatResponse, ConflictItem, DerivedValueItem
from app.agent.router import classify_query, RouterDecision
from app.agent.tools.sql_tool import (
    execute_safe_sql,
    get_client_entitlements,
)
from app.agent.tools.retriever import get_retriever, RetrievedChunk
from app.agent.tools.calculator import calculate_projection, extract_numbers_from_query
from app.agent.reconcile import detect_report_conflicts
from app.agent.synthesizer import get_synthesizer

logger = logging.getLogger("project_atlas.agent.graph")


# --- Agent State Definition ---
class AgentState(TypedDict):
    client_id: str
    question: str
    purchased_reports: List[str]
    intent: str
    router_confidence: float
    is_attack: bool
    escalated: bool
    escalation_reason: Optional[str]
    escalation_ticket_id: Optional[str]
    retrieved_chunks: List[RetrievedChunk]
    sql_data: List[Dict[str, Any]]
    conflicts: List[ConflictItem]
    derived_values: List[DerivedValueItem]
    final_response: Optional[ChatResponse]


def log_escalation_to_db(client_id: str, question: str, reason: str) -> str:
    """Insert an escalation through the shared transactional service."""
    from app.services.escalation_service import escalation_service
    ticket_id = escalation_service.log_escalation(client_id, question, reason)
    return f"ESC-{ticket_id:04d}"


# --- Workflow Nodes ---

def guardrail_router_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 1: Evaluates user query with the fine-tuned Laya 421M model.
    """
    decision: RouterDecision = classify_query(state["question"])
    return {
        "intent": decision.intent,
        "router_confidence": decision.confidence,
        "is_attack": decision.is_attack
    }


def security_audit_node(state: AgentState) -> Dict[str, Any]:
    """
    Security Node: Triggered on prompt injection or SQL attack.
    Immediately halts execution without invoking the LLM and logs the incident.
    """
    intent = state.get("intent", "attack")
    reason = f"Security violation detected: {intent} (Laya confidence: {state.get('router_confidence', 1.0):.2f})"
    ticket_id = log_escalation_to_db(state["client_id"], state["question"], reason)

    refusal_msg = (
        "[SECURITY ALERT] Your query has been flagged and blocked by our Automated Compliance & Security Guardrail. "
        "Adversarial prompts, system override attempts, and unauthorized database operations are strictly prohibited. "
        f"This incident has been logged for administrative security review under ticket [{ticket_id}]."
    )

    response = ChatResponse(
        answer=refusal_msg,
        citations=[],
        confidence=1.0,
        conflicts=[],
        derived_values=[],
        escalated=True,
        escalation_ticket_id=ticket_id
    )

    return {
        "escalated": True,
        "escalation_reason": reason,
        "escalation_ticket_id": ticket_id,
        "final_response": response
    }


def sql_execution_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 2A: Handles database aggregates, counts, catalog summaries.
    """
    q_lower = state["question"].lower()
    allowed = state["purchased_reports"]

    # Select appropriate query based on question topic
    if "how many" in q_lower or "count" in q_lower or "total" in q_lower or "list" in q_lower:
        query_sql = "SELECT id, title, publisher, published, sector, access FROM reports"
    elif "apac" in q_lower or "region" in q_lower:
        query_sql = "SELECT report, metric, region, year_period, value, scope_note FROM market_metrics WHERE region = 'APAC'"
    elif "cagr" in q_lower:
        query_sql = "SELECT report, metric, region, year_period, value, scope_note FROM market_metrics WHERE metric LIKE '%CAGR%'"
    else:
        query_sql = "SELECT report, metric, region, year_period, value, scope_note FROM market_metrics"

    try:
        sql_results = execute_safe_sql(query_sql, allowed_reports=allowed)
    except Exception as e:
        logger.exception(
            "agent_sql_execution_failed error_type=%s client_id=%s",
            type(e).__name__,
            state.get("client_id", "unknown"),
        )
        sql_results = [{"error": str(e)}]

    return {"sql_data": sql_results}


def calculation_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 2B: Deterministic calculation of CAGR and forward projections.
    """
    q = state["question"]
    numbers = extract_numbers_from_query(q)
    
    # Defaults based on primary Smart Water Meter market (R-101 baseline)
    base_val = numbers.get("base_value_billion", 4.21)
    base_yr = 2024
    target_yr = int(numbers.get("target_year", 2030))
    cagr_pct = numbers.get("cagr_pct", 11.2) / 100.0

    derived_item = calculate_projection(
        metric_name="Projected Smart Water Meter Market Size",
        base_value=base_val,
        base_year=base_yr,
        target_year=target_yr,
        cagr_decimal=cagr_pct,
        unit="USD Billion"
    )

    return {
        "derived_values": [derived_item]
    }


def retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 2C: Entitlement-filtered vector search over ingested PDF reports.
    """
    retriever = get_retriever()
    chunks = retriever.retrieve_for_client(
        query=state["question"],
        purchased_reports=state["purchased_reports"],
        top_k=5
    )

    conflicts = detect_report_conflicts(state["question"], chunks)

    return {
        "retrieved_chunks": chunks,
        "conflicts": conflicts
    }


def out_of_scope_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 2D: Handles general or unrelated queries.
    """
    answer_text = (
        "I specialize strictly in Cognitive Market Research intelligence across utility infrastructure, "
        "water metering, wastewater treatment, and industrial membrane systems. Your query appears to be "
        "outside the scope of our published market research portfolio. "
        "Please ask an inquiry related to our coverage sectors, market sizes, CAGR forecasts, or vendor comparisons."
    )
    response = ChatResponse(
        answer=answer_text,
        citations=[],
        confidence= state.get("router_confidence", 0.95),
        conflicts=[],
        derived_values=[],
        escalated=False
    )
    return {"final_response": response}


def synthesizer_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node 3: Synthesizes final response via Groq LLM with citations and verified figures.
    """
    # If final_response was already produced (e.g. security refusal or out-of-scope), pass through
    if state.get("final_response") is not None:
        return {}

    synthesizer = get_synthesizer()
    token_callback = config.get("configurable", {}).get("token_callback")
    response = synthesizer.synthesize(
        query=state["question"],
        retrieved_chunks=state.get("retrieved_chunks", []),
        sql_data=state.get("sql_data", []),
        conflicts=state.get("conflicts", []),
        derived_values=state.get("derived_values", []),
        token_callback=token_callback,
    )

    return {"final_response": response}


# --- Routing Conditions ---

def route_after_guardrail(state: AgentState) -> str:
    """Conditional router based on Laya classification."""
    if state.get("is_attack") or state.get("intent") in ["prompt_injection", "sql_attack"]:
        return "security_audit_node"
    
    intent = state.get("intent", "factual_lookup")
    if intent == "database_aggregate":
        return "sql_execution_node"
    elif intent == "calculation":
        return "calculation_node"
    elif intent in ["factual_lookup", "comparison"]:
        return "retrieval_node"
    elif intent == "out_of_scope":
        return "out_of_scope_node"
    else:
        return "retrieval_node"


# --- Assemble StateGraph ---

def build_atlas_graph():
    graph = StateGraph(AgentState)

    # Add Nodes
    graph.add_node("guardrail_router_node", guardrail_router_node)
    graph.add_node("security_audit_node", security_audit_node)
    graph.add_node("sql_execution_node", sql_execution_node)
    graph.add_node("calculation_node", calculation_node)
    graph.add_node("retrieval_node", retrieval_node)
    graph.add_node("out_of_scope_node", out_of_scope_node)
    graph.add_node("synthesizer_node", synthesizer_node)

    # Set Entry Point
    graph.set_entry_point("guardrail_router_node")

    # Add Conditional Edges from Router
    graph.add_conditional_edges(
        "guardrail_router_node",
        route_after_guardrail,
        {
            "security_audit_node": "security_audit_node",
            "sql_execution_node": "sql_execution_node",
            "calculation_node": "calculation_node",
            "retrieval_node": "retrieval_node",
            "out_of_scope_node": "out_of_scope_node"
        }
    )

    # Direct edges into Synthesizer
    graph.add_edge("sql_execution_node", "synthesizer_node")
    graph.add_edge("calculation_node", "synthesizer_node")
    graph.add_edge("retrieval_node", "synthesizer_node")

    # Final terminations
    graph.add_edge("security_audit_node", END)
    graph.add_edge("out_of_scope_node", END)
    graph.add_edge("synthesizer_node", END)

    return graph.compile()


# Singleton compiled graph
_compiled_graph = None

def get_agent_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_atlas_graph()
    return _compiled_graph


def run_agent_workflow(
    client_id: str,
    question: str,
    token_callback: Optional[Callable[[str], None]] = None,
) -> ChatResponse:
    """
    Public invocation interface:
    Resolves client entitlements, executes graph, returns typed ChatResponse.
    """
    purchased = get_client_entitlements(client_id)
    graph = get_agent_graph()

    initial_state: AgentState = {
        "client_id": client_id,
        "question": question,
        "purchased_reports": purchased,
        "intent": "factual_lookup",
        "router_confidence": 1.0,
        "is_attack": False,
        "escalated": False,
        "escalation_reason": None,
        "escalation_ticket_id": None,
        "retrieved_chunks": [],
        "sql_data": [],
        "conflicts": [],
        "derived_values": [],
        "final_response": None
    }

    graph_config = (
        {"configurable": {"token_callback": token_callback}}
        if token_callback is not None
        else None
    )
    final_state = graph.invoke(initial_state, config=graph_config)
    return final_state["final_response"]

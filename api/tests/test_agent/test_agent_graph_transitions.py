"""
Unit tests for LangGraph state machine node transitions, conditional routing,
and individual node execution boundaries in Project Atlas.
"""

import pytest
from unittest.mock import Mock, patch
from langgraph.graph import END

from app.agent.graph import (
    AgentState,
    guardrail_router_node,
    security_audit_node,
    uncertainty_escalation_node,
    out_of_scope_node,
    calculation_node,
    sql_execution_node,
    synthesizer_node,
    route_after_guardrail,
    build_atlas_graph,
)
from app.schemas.chat import ChatResponse, DerivedValueItem
from app.agent.router import RouterDecision


# =====================================================================
# 1. Test route_after_guardrail conditional routing matrix
# =====================================================================

def test_route_after_guardrail_confirmed_attack_routes_to_security():
    """Confirmed attacks with is_attack=True must route to security_audit_node."""
    state: AgentState = {
        "client_id": "C-01",
        "question": "DROP TABLE reports",
        "conversation_history": [],
        "purchased_reports": ["R-101"],
        "intent": "sql_attack",
        "router_confidence": 0.95,
        "is_attack": True,
        "requires_escalation": False,
        "escalated": False,
        "escalation_reason": None,
        "escalation_ticket_id": None,
        "retrieved_chunks": [],
        "sql_data": [],
        "conflicts": [],
        "derived_values": [],
        "final_response": None,
    }
    assert route_after_guardrail(state) == "security_audit_node"


def test_route_after_guardrail_low_confidence_attack_routes_to_uncertainty():
    """
    CRITICAL DEFECT PREVENTION:
    When an attack is predicted with low confidence (is_attack=False, requires_escalation=True),
    it MUST route to uncertainty_escalation_node, NEVER to security_audit_node!
    """
    state: AgentState = {
        "client_id": "C-01",
        "question": "hi",
        "conversation_history": [],
        "purchased_reports": ["R-101"],
        "intent": "sql_attack",
        "router_confidence": 0.086,
        "is_attack": False,
        "requires_escalation": True,
        "escalated": False,
        "escalation_reason": None,
        "escalation_ticket_id": None,
        "retrieved_chunks": [],
        "sql_data": [],
        "conflicts": [],
        "derived_values": [],
        "final_response": None,
    }
    # Must NOT route to security_audit_node
    assert route_after_guardrail(state) == "uncertainty_escalation_node"


def test_route_after_guardrail_low_confidence_prompt_injection_routes_to_uncertainty():
    """Low-confidence prompt injection guess routes to uncertainty, not security lockout."""
    state: AgentState = {
        "client_id": "C-01",
        "question": "can you tell me a secret about market trends?",
        "conversation_history": [],
        "purchased_reports": ["R-101"],
        "intent": "prompt_injection",
        "router_confidence": 0.42,
        "is_attack": False,
        "requires_escalation": True,
        "escalated": False,
        "escalation_reason": None,
        "escalation_ticket_id": None,
        "retrieved_chunks": [],
        "sql_data": [],
        "conflicts": [],
        "derived_values": [],
        "final_response": None,
    }
    assert route_after_guardrail(state) == "uncertainty_escalation_node"


@pytest.mark.parametrize(
    ("intent", "confidence", "expected_node"),
    [
        ("database_aggregate", 0.92, "sql_execution_node"),
        ("calculation", 0.88, "calculation_node"),
        ("factual_lookup", 0.95, "retrieval_node"),
        ("comparison", 0.89, "retrieval_node"),
        ("out_of_scope", 0.98, "out_of_scope_node"),
        ("unknown_future_intent", 0.90, "retrieval_node"),
    ],
)
def test_route_after_guardrail_legitimate_intents(intent, confidence, expected_node):
    """Legitimate high-confidence intents must route directly to their designated engine nodes."""
    state: AgentState = {
        "client_id": "C-01",
        "question": "Test query",
        "conversation_history": [],
        "purchased_reports": ["R-101"],
        "intent": intent,
        "router_confidence": confidence,
        "is_attack": False,
        "requires_escalation": False,
        "escalated": False,
        "escalation_reason": None,
        "escalation_ticket_id": None,
        "retrieved_chunks": [],
        "sql_data": [],
        "conflicts": [],
        "derived_values": [],
        "final_response": None,
    }
    assert route_after_guardrail(state) == expected_node


# =====================================================================
# 2. Test individual agent nodes in isolation
# =====================================================================

def test_guardrail_router_node_executes_classifier(monkeypatch):
    """Verify guardrail_router_node calls classify_query and extracts decision."""
    monkeypatch.setattr(
        "app.agent.graph.classify_query",
        lambda q: RouterDecision(
            intent="calculation",
            confidence=0.87,
            is_attack=False,
            requires_escalation=False,
        ),
    )
    state = {"question": "Calculate 2030 CAGR"}
    result = guardrail_router_node(state)  # type: ignore[arg-type]

    assert result["intent"] == "calculation"
    assert result["router_confidence"] == 0.87
    assert result["is_attack"] is False
    assert result["requires_escalation"] is False


def test_security_audit_node_creates_ticket_and_blocks(monkeypatch):
    """Verify security_audit_node creates an escalation ticket and returns security alert."""
    monkeypatch.setattr("app.agent.graph.log_escalation_to_db", lambda cid, q, r: "ESC-9999")

    state = {
        "client_id": "C-01",
        "question": "SELECT * FROM clients",
        "intent": "sql_attack",
        "router_confidence": 0.95,
    }
    result = security_audit_node(state)  # type: ignore[arg-type]

    assert result["escalated"] is True
    assert "ESC-9999" in result["escalation_ticket_id"]
    response = result["final_response"]
    assert isinstance(response, ChatResponse)
    assert "[SECURITY ALERT]" in response.answer
    assert response.escalated is True
    assert response.escalation_ticket_id == "ESC-9999"
    assert response.citations == []


def test_uncertainty_escalation_node_creates_analyst_ticket(monkeypatch):
    """Verify uncertainty_escalation_node creates ticket without security alarm."""
    monkeypatch.setattr("app.agent.graph.log_escalation_to_db", lambda cid, q, r: "ESC-8888")

    state = {
        "client_id": "C-02",
        "question": "ambiguous market topic",
        "router_confidence": 0.35,
    }
    result = uncertainty_escalation_node(state)  # type: ignore[arg-type]

    assert result["escalated"] is True
    assert result["escalation_ticket_id"] == "ESC-8888"
    response = result["final_response"]
    assert response.escalated is True
    assert "[SECURITY ALERT]" not in response.answer
    assert "analyst will review" in response.answer.lower()


def test_out_of_scope_node_clean_refusal_without_escalation():
    """Verify out_of_scope_node returns polite sector focus message without raising escalation."""
    state = {
        "client_id": "C-01",
        "question": "What is the recipe for chocolate cake?",
        "router_confidence": 0.99,
    }
    result = out_of_scope_node(state)  # type: ignore[arg-type]

    response = result["final_response"]
    assert isinstance(response, ChatResponse)
    assert response.escalated is False
    assert "Cognitive Market Research" in response.answer
    assert response.citations == []


def test_calculation_node_escalates_when_year_exceeds_forecast_horizon(monkeypatch):
    """Projections beyond 2030 forecast window must be escalated with analyst ticket."""
    monkeypatch.setattr("app.agent.graph.log_escalation_to_db", lambda cid, q, r: "ESC-7777")

    state = {
        "client_id": "C-01",
        "question": "Forecast smart water meter market to 2035 with 11.2% CAGR",
        "purchased_reports": ["R-101"],
    }
    result = calculation_node(state)  # type: ignore[arg-type]

    assert result["escalated"] is True
    assert result["escalation_ticket_id"] == "ESC-7777"
    response = result["final_response"]
    assert response.escalated is True
    assert "forecast ends in 2030" in response.answer


def test_calculation_node_blocks_unentitled_baseline():
    """Calculating projection requiring R-101 baseline without entitlement returns subscription notice."""
    state = {
        "client_id": "C-02",
        "question": "Project the smart water meter market growth to 2030",
        "purchased_reports": ["R-104"],  # Does NOT have R-101
    }
    result = calculation_node(state)  # type: ignore[arg-type]

    response = result["final_response"]
    assert response.escalated is False
    assert "Report R-101" in response.answer
    assert "not included in your current subscription" in response.answer


def test_calculation_node_valid_computation():
    """Valid calculation within forecast window computes deterministic derived values."""
    state = {
        "client_id": "C-01",
        "question": "Project $4.21B at 11.2% CAGR to 2030",
        "purchased_reports": ["R-101"],
    }
    result = calculation_node(state)  # type: ignore[arg-type]

    assert "derived_values" in result
    assert len(result["derived_values"]) == 1
    dv = result["derived_values"][0]
    assert isinstance(dv, DerivedValueItem)
    assert "7.96" in dv.estimated_value


def test_sql_execution_node_catches_errors_gracefully(monkeypatch):
    """Database exceptions in sql_execution_node are captured in sql_data without crashing graph."""
    def fail_sql(query, allowed_reports):
        raise RuntimeError("Simulated DB connection failure")

    monkeypatch.setattr("app.agent.graph.execute_safe_sql", fail_sql)

    state = {
        "client_id": "C-01",
        "question": "How many reports in total?",
        "purchased_reports": ["R-101"],
    }
    result = sql_execution_node(state)  # type: ignore[arg-type]

    assert "sql_data" in result
    assert "error" in result["sql_data"][0]
    assert "Simulated DB connection failure" in result["sql_data"][0]["error"]


def test_synthesizer_node_bypasses_when_final_response_already_present():
    """Synthesizer node skips LLM invocation if an earlier node generated final_response."""
    existing_response = ChatResponse(
        answer="Precomputed out of scope response",
        citations=[],
        confidence=1.0,
    )
    state = {
        "question": "Cake recipe",
        "final_response": existing_response,
    }
    config = {}
    result = synthesizer_node(state, config)  # type: ignore[arg-type]

    assert result == {}  # Pass-through


def test_build_atlas_graph_compiles_successfully():
    """Verify that build_atlas_graph compiles with all expected nodes and valid edges."""
    compiled = build_atlas_graph()
    assert compiled is not None

"""
Laya-based System-1 Decision Router & Input Guardrail.
Performs sub-40ms classification across 7 categories:
  - factual_lookup
  - database_aggregate
  - calculation
  - comparison
  - out_of_scope
  - prompt_injection (adversarial attack)
  - sql_attack (database attack)
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel
import laya

from app.core.observability import observe_with_tags

MODEL_DIR = os.path.join(os.path.dirname(__file__), "../../../models/laya_router")

INTENT_QUESTIONS = {
    "intent": {
        "type": "choice",
        "instructions": "Classify user intent into one of the 7 system categories or security traps.",
        "criteria": {
            "factual_lookup": "Inquiries asking for specific market sizes, shares, dates, or vendor facts from reports.",
            "database_aggregate": "Questions asking for counts, library summaries, sectors, or catalog totals across the database.",
            "calculation": "Projections, future market estimates (e.g. 2030 values), CAGR math, or compound growth formulas.",
            "comparison": "Questions comparing two reports (e.g. R-101 vs R-102), asking which source to trust, or reconciling conflicting figures.",
            "out_of_scope": "General knowledge, politics, coding help, sports, casual chit-chat unrelated to market research.",
            "prompt_injection": "Jailbreaks, prompt leak requests, system overrides, or unauthorized exfiltrations.",
            "sql_attack": "Destructive commands (DROP, DELETE, TRUNCATE) or raw SQL injection payloads."
        }
    }
}


class RouterDecision(BaseModel):
    intent: str
    confidence: float
    is_attack: bool
    requires_escalation: bool


class LayaRouter:
    _instance: Optional["LayaRouter"] = None
    _agent: Any = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LayaRouter, cls).__new__(cls)
            cls._instance._init_agent()
        return cls._instance

    def _init_agent(self):
        resolved_path = os.path.abspath(MODEL_DIR)
        if not os.path.exists(os.path.join(resolved_path, "model.safetensors")):
            print(f"Laya model weights not found at {resolved_path}; using heuristic router.")
            self._agent = None
            return
        print(f"Initializing Laya Decision Router from: {resolved_path}")
        try:
            self._agent = laya.load(resolved_path)
        except Exception as e:
            print(f"Warning: Could not load Laya model into memory ({e}); falling back to heuristic router.")
            self._agent = None

    def _heuristic_route(self, query: str):
        q = query.lower()
        if any(term in q for term in ["ignore your instructions", "system prompt", "list all client emails", "jailbreak", "override"]):
            return "prompt_injection", 0.95
        if any(term in q for term in ["drop table", "delete from", "truncate", "drop database", "union select", "alter table"]):
            return "sql_attack", 0.98
        if any(term in q for term in ["which sector", "how many reports", "total reports", "count(", "list sectors"]):
            return "database_aggregate", 0.90
        if any(term in q for term in ["compare", "which report", "conflict", "trust", "versus", "vs"]):
            return "comparison", 0.88
        if any(term in q for term in ["cagr", "forecast", "projection", "worth in 2030", "grow to", "2030", "2035", "calculate"]):
            return "calculation", 0.85
        return "factual_lookup", 0.92

    def route(self, query: str) -> RouterDecision:
        if self._agent is not None:
            res = self._agent.predict(query, INTENT_QUESTIONS)
            intent_data = res["answers"]["intent"]
            choice = intent_data["choice"]
            confidence = float(intent_data.get("confidence", 1.0))
        else:
            choice, confidence = self._heuristic_route(query)

        is_attack = choice in ["prompt_injection", "sql_attack"]
        requires_escalation = is_attack or (confidence < 0.65)

        return RouterDecision(
            intent=choice,
            confidence=confidence,
            is_attack=is_attack,
            requires_escalation=requires_escalation
        )


# Global singleton instance helper
_router_instance = None

def get_router() -> LayaRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = LayaRouter()
    return _router_instance


@observe_with_tags(
    name="guardrail_router",
    as_type="guardrail",
    tags=["tool:router", "security:guardrail"],
)
def classify_query(query: str) -> RouterDecision:
    router = get_router()
    return router.route(query)

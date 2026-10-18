import pytest

from app.agent.router import LayaRouter


class FakeIntentAgent:
    def __init__(self, choice: str, confidence: float):
        self.choice = choice
        self.confidence = confidence

    def predict(self, query, questions):
        return {
            "answers": {
                "intent": {"choice": self.choice, "confidence": self.confidence}
            }
        }


@pytest.mark.parametrize(
    ("intent", "confidence", "is_attack", "requires_escalation"),
    [
        ("factual_lookup", 0.9, False, False),
        ("prompt_injection", 0.9, True, True),
        ("sql_attack", 0.9, True, True),
        ("factual_lookup", 0.64, False, True),
        ("factual_lookup", 0.65, False, False),
    ],
)
def test_router_classifies_security_and_confidence_edges(
    intent, confidence, is_attack, requires_escalation
):
    router = object.__new__(LayaRouter)
    router._agent = FakeIntentAgent(intent, confidence)

    decision = router.route("sample query")

    assert decision.intent == intent
    assert decision.confidence == confidence
    assert decision.is_attack is is_attack
    assert decision.requires_escalation is requires_escalation

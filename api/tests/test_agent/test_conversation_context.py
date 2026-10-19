import json
from types import SimpleNamespace
from unittest.mock import Mock

from app.agent import graph
from app.agent.router import RouterDecision
from app.agent.synthesizer import LLMSynthesizer
from app.schemas.chat import ChatResponse


class CapturingGraph:
    def __init__(self, response):
        self.response = response
        self.state = None

    def invoke(self, state, config=None):
        self.state = state
        return {**state, "final_response": self.response}


class FakeSynthesizer:
    def __init__(self, resolution):
        self.resolution = resolution
        self.resolve_calls = []

    def resolve_follow_up(self, query, history):
        self.resolve_calls.append((query, history))
        return self.resolution


def test_follow_up_is_resolved_after_raw_message_security_check(monkeypatch):
    history = [{"role": "user", "content": "What is the R-101 market size?"}]
    response = ChatResponse(answer="Answer", confidence=0.8)
    fake_graph = CapturingGraph(response)
    fake_synthesizer = FakeSynthesizer(
        {
            "standalone_question": "What is the R-101 market size in 2030?",
            "needs_clarification": False,
            "clarification_question": None,
        }
    )
    event_order = []

    monkeypatch.setattr(graph, "get_client_entitlements", lambda _client: ["R-101"])
    monkeypatch.setattr(graph, "get_agent_graph", lambda: fake_graph)
    monkeypatch.setattr(graph, "get_synthesizer", lambda: fake_synthesizer)

    def classify_raw(query):
        event_order.append(("security_check", query))
        return RouterDecision(
            intent="factual_lookup",
            confidence=0.9,
            is_attack=False,
            requires_escalation=False,
        )

    monkeypatch.setattr(graph, "classify_query", classify_raw)

    result = graph.run_agent_workflow(
        client_id="C-01",
        question="What about 2030?",
        conversation_history=history,
    )

    assert result is response
    assert event_order == [("security_check", "What about 2030?")]
    assert fake_synthesizer.resolve_calls == [
        ("What about 2030?", history)
    ]
    assert fake_graph.state["question"] == "What is the R-101 market size in 2030?"
    assert fake_graph.state["conversation_history"] == history + [
        {"role": "user", "content": "What about 2030?"}
    ]


def test_ambiguous_follow_up_returns_clarification_without_routing(monkeypatch):
    fake_synthesizer = FakeSynthesizer(
        {
            "standalone_question": "What is the market size?",
            "needs_clarification": True,
            "clarification_question": "Which report and market do you mean?",
        }
    )
    monkeypatch.setattr(graph, "get_client_entitlements", lambda _client: [])
    monkeypatch.setattr(graph, "get_synthesizer", lambda: fake_synthesizer)
    monkeypatch.setattr(
        graph,
        "classify_query",
        lambda _query: RouterDecision(
            intent="factual_lookup",
            confidence=0.9,
            is_attack=False,
            requires_escalation=False,
        ),
    )
    monkeypatch.setattr(
        graph,
        "get_agent_graph",
        lambda: (_ for _ in ()).throw(AssertionError("Graph should not execute")),
    )

    result = graph.run_agent_workflow(
        client_id="C-01",
        question="What about that?",
        conversation_history=[{"role": "user", "content": "Compare reports."}],
    )

    assert result.clarification_needed is True
    assert result.answer == "Which report and market do you mean?"


def test_follow_up_resolver_uses_structured_untrusted_history():
    synthesizer = LLMSynthesizer.__new__(LLMSynthesizer)
    synthesizer.client = Mock()
    synthesizer.client.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(
                        {
                            "standalone_question": "What is the R-101 market size in 2030?",
                            "needs_clarification": False,
                            "clarification_question": None,
                        }
                    )
                )
            )
        ]
    )
    synthesizer.model = "test-model"
    history = [
        {"role": "user", "content": "What is the market size in R-101?"},
        {"role": "assistant", "content": "It was USD 4.21B [R-101 p.8]."},
    ]

    result = synthesizer.resolve_follow_up("What about 2030?", history)

    assert result["standalone_question"] == "What is the R-101 market size in 2030?"
    request = synthesizer.client.chat.completions.create.call_args.kwargs
    payload = json.loads(request["messages"][1]["content"])
    assert payload == {
        "history": history,
        "latest_message": "What about 2030?",
    }
    assert request["temperature"] == 0
    assert request["response_format"] == {"type": "json_object"}

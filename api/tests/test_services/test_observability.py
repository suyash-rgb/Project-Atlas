from contextlib import nullcontext

from app.core import observability


def test_observe_with_tags_propagates_tags_without_capturing_io(monkeypatch):
    captured = {}

    def fake_observe(**options):
        captured["observe_options"] = options
        return lambda func: func

    def fake_propagate_attributes(**attributes):
        captured["attributes"] = attributes
        return nullcontext()

    monkeypatch.setattr(observability, "observe", fake_observe)
    monkeypatch.setattr(observability, "propagate_attributes", fake_propagate_attributes)

    @observability.observe_with_tags(
        name="test_tool",
        as_type="tool",
        tags=["project-atlas", "tool:test"],
    )
    def run_tool(value: str) -> str:
        return value.upper()

    assert run_tool("ok") == "OK"
    assert captured["observe_options"] == {
        "name": "test_tool",
        "as_type": "tool",
        "capture_input": False,
        "capture_output": False,
    }
    assert captured["attributes"] == {"tags": ["project-atlas", "tool:test"]}


def test_observe_with_tags_is_noop_when_langfuse_is_unavailable(monkeypatch):
    monkeypatch.setattr(observability, "observe", None)
    monkeypatch.setattr(observability, "propagate_attributes", None)
    monkeypatch.setattr(observability, "get_client", None)

    @observability.observe_with_tags(name="test_tool", tags=["tool:test"])
    def run_tool() -> str:
        return "ok"

    assert run_tool() == "ok"


def test_trace_observation_updates_metadata_without_capturing_io(monkeypatch):
    captured = {}

    class Observation:
        def update(self, **options):
            captured["update"] = options

    class Client:
        @staticmethod
        def start_as_current_observation(**options):
            captured["observation_options"] = options
            return nullcontext(Observation())

    monkeypatch.setattr(observability, "get_client", lambda: Client())

    with observability.trace_observation(
        name="router_classification",
        as_type="guardrail",
    ) as observation:
        observation.update(metadata={"intent": "factual_lookup"})

    assert captured["observation_options"] == {
        "name": "router_classification",
        "as_type": "guardrail",
        "metadata": None,
    }
    assert captured["update"] == {"metadata": {"intent": "factual_lookup"}}

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

from app.agent import synthesizer as synthesizer_module
from app.agent.synthesizer import LLMSynthesizer


def test_synthesizer_streams_chunks_and_returns_combined_answer():
    synthesizer = LLMSynthesizer.__new__(LLMSynthesizer)
    first = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="Streamed "))]
    )
    second = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="answer."))]
    )
    usage = SimpleNamespace(prompt_tokens=12, completion_tokens=4, total_tokens=16)
    usage_chunk = SimpleNamespace(choices=[], usage=usage)
    synthesizer.client = Mock()
    synthesizer.client.chat.completions.create.return_value = iter(
        [first, second, usage_chunk]
    )
    synthesizer.model = "test-model"
    emitted = []

    result = synthesizer.synthesize(
        query="Question",
        retrieved_chunks=[],
        token_callback=emitted.append,
    )

    assert emitted == ["Streamed ", "answer."]
    assert result.answer == "Streamed answer."
    call_options = synthesizer.client.chat.completions.create.call_args.kwargs
    assert call_options["stream"] is True
    assert "stream_options" not in call_options


def test_extract_usage_details_uses_provider_token_counts():
    assert synthesizer_module._extract_usage_details(
        SimpleNamespace(prompt_tokens=12, completion_tokens=4, total_tokens=16)
    ) == {"input": 12, "output": 4, "total": 16}
    assert synthesizer_module._extract_usage_details(None) is None


def test_synthesizer_records_provider_usage_without_prompt_or_answer(monkeypatch):
    observations = []

    class Generation:
        def update(self, **options):
            observations[-1]["updates"].append(options)

    @contextmanager
    def fake_trace_observation(**options):
        observations.append({"options": options, "updates": []})
        yield Generation()

    monkeypatch.setattr(
        synthesizer_module, "trace_observation", fake_trace_observation
    )

    synthesizer = LLMSynthesizer.__new__(LLMSynthesizer)
    synthesizer.client = Mock()
    synthesizer.client.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="The report describes a positive outlook.")
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=120,
            completion_tokens=18,
            total_tokens=138,
        ),
    )
    synthesizer.model = "test-model"

    synthesizer.synthesize(query="Market size?", retrieved_chunks=[])

    generation = observations[0]
    assert generation["options"]["name"] == "groq_chat_completion"
    assert "input" not in generation["options"]
    assert generation["updates"] == [
        {
            "model": "test-model",
            "metadata": {"provider": "groq", "usage_source": "groq_api"},
            "usage_details": {"input": 120, "output": 18, "total": 138},
        }
    ]

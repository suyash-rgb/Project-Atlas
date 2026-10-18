from types import SimpleNamespace
from unittest.mock import Mock

from app.agent.synthesizer import LLMSynthesizer


def test_synthesizer_streams_chunks_and_returns_combined_answer():
    synthesizer = LLMSynthesizer.__new__(LLMSynthesizer)
    first = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="Streamed "))]
    )
    second = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="answer."))]
    )
    synthesizer.client = Mock()
    synthesizer.client.chat.completions.create.return_value = iter([first, second])
    synthesizer.model = "test-model"
    emitted = []

    result = synthesizer.synthesize(
        query="Question",
        retrieved_chunks=[],
        token_callback=emitted.append,
    )

    assert emitted == ["Streamed ", "answer."]
    assert result.answer == "Streamed answer."
    assert synthesizer.client.chat.completions.create.call_args.kwargs["stream"] is True

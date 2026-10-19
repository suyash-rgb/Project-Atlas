"""
Unit Tests for Dynamic Prompt Injection & Modular Intent Directives.

Verifies:
- build_system_prompt() always preserves the immutable security core
- Calculation intent injects CAGR math and deterministic derivation directives
- Comparison intent injects side-by-side reconciliation and scope divergence directives
- Database aggregate intent injects catalog grouping rules
- Factual lookup intent injects tabular metrics extraction rules
- Default fallback preserves base security core when intent is None or unrecognized
- Synthesizer correctly forwards active intent to the LLM system prompt
"""

from unittest.mock import Mock, MagicMock
from types import SimpleNamespace
import pytest

from app.agent.synthesizer import (
    build_system_prompt,
    BASE_SYSTEM_CORE,
    INTENT_PROMPT_MODULES,
    LLMSynthesizer,
)


def test_build_system_prompt_default_and_none():
    prompt_none = build_system_prompt(None)
    assert BASE_SYSTEM_CORE.strip() == prompt_none
    assert "STRICT GROUNDING" in prompt_none
    assert "IN-TEXT CITATIONS" in prompt_none
    assert "SECURITY & TRAP RESISTANCE" in prompt_none


def test_build_system_prompt_calculation_intent():
    prompt = build_system_prompt("calculation")
    # Must preserve security rules
    assert "STRICT GROUNDING" in prompt
    assert "SECURITY & TRAP RESISTANCE" in prompt
    # Must include calculation directives
    assert "CALCULATION DIRECTIVES" in prompt
    assert "CAGR formula" in prompt
    assert "Do NOT perform mental math" in prompt
    # Must NOT include comparison directives
    assert "COMPARISON & RECONCILIATION DIRECTIVES" not in prompt


def test_build_system_prompt_comparison_intent():
    prompt = build_system_prompt("comparison")
    assert "STRICT GROUNDING" in prompt
    assert "COMPARISON & RECONCILIATION DIRECTIVES" in prompt
    assert "Markdown comparison table" in prompt
    assert "CALCULATION DIRECTIVES" not in prompt


def test_build_system_prompt_database_aggregate_intent():
    prompt = build_system_prompt("database_aggregate")
    assert "STRICT GROUNDING" in prompt
    assert "DATABASE CATALOG DIRECTIVES" in prompt
    assert "sector, geography, and publication year" in prompt


def test_build_system_prompt_factual_lookup_intent():
    prompt = build_system_prompt("factual_lookup")
    assert "STRICT GROUNDING" in prompt
    assert "FACTUAL RETRIEVAL DIRECTIVES" in prompt
    assert "visual evidence" in prompt


def test_build_system_prompt_unrecognized_intent():
    prompt = build_system_prompt("some_future_custom_route")
    assert prompt == BASE_SYSTEM_CORE.strip()


def test_synthesizer_uses_dynamic_prompt_matching_intent():
    synthesizer = LLMSynthesizer.__new__(LLMSynthesizer)
    mock_client = Mock()
    mock_response = MagicMock()
    mock_response.choices = [
        SimpleNamespace(message=SimpleNamespace(content="The projected 2030 value is $8.01B [R-101 p.4]."))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    synthesizer.client = mock_client
    synthesizer.model = "test-model"

    mock_chunk = SimpleNamespace(
        report_id="R-101",
        page=4,
        title="Smart Water Metering",
        sector="Water",
        access="paid",
        text="Market projected to reach $8.01B by 2030.",
    )

    result = synthesizer.synthesize(
        query="What is the 2030 projection?",
        retrieved_chunks=[mock_chunk],
        intent="calculation",
    )

    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    system_msg = next(m for m in messages if m["role"] == "system")

    # Assert that the dynamic prompt for calculation was injected
    assert "CALCULATION DIRECTIVES" in system_msg["content"]
    assert "CAGR formula" in system_msg["content"]
    assert "STRICT GROUNDING" in system_msg["content"]

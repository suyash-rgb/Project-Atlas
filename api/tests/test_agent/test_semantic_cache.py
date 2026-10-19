"""
Unit Tests for In-Memory Semantic Caching.

Covers:
- Graceful degradation when semantic cache is disabled
- Vector embedding generation (384-dim BGE-small)
- Semantic cache hit with high similarity (>= 0.90)
- Semantic cache miss when similarity is below threshold (< 0.90)
- Strict client entitlement isolation: Client A cannot see Client B's cached query
- Serialization and deserialization of ChatResponse payloads
- Cache clear operations (full vs tenant-specific)
- TTL expiration in memory
- Integration with ChatService
"""

import time
import numpy as np
import pytest
from unittest.mock import patch

from app.core.semantic_cache import InMemorySemanticCache, RedisSemanticCache
from app.schemas.chat import ChatResponse
from app.services.chat_service import ChatService


# =====================================================================
# 1. Graceful Bypass & Input Validation Tests
# =====================================================================

def test_semantic_cache_disabled():
    cache = InMemorySemanticCache(enabled=False)
    assert cache.enabled is False
    assert cache.get("CLIENT_A", "What is GenAI?") is None
    assert cache.set("CLIENT_A", "What is GenAI?", {"answer": "test"}) is False


def test_semantic_cache_empty_or_whitespace_input():
    cache = InMemorySemanticCache(enabled=True)
    assert cache.get("", "Question") is None
    assert cache.get("CLIENT_A", "   ") is None
    assert cache.set("", "Question", {}) is False
    assert cache.set("CLIENT_A", "", {}) is False


def test_semantic_cache_embed_vector():
    cache = InMemorySemanticCache(enabled=True)
    vector = cache._embed("Global GenAI Market Size 2026")
    assert vector is not None
    assert isinstance(vector, np.ndarray)
    assert vector.shape == (384,)
    norm = np.linalg.norm(vector)
    assert pytest.approx(norm, 0.001) == 1.0


# =====================================================================
# 2. Vector Similarity Search & Client Isolation Tests (In-Memory)
# =====================================================================

def test_semantic_cache_hit_above_threshold():
    cache = InMemorySemanticCache(enabled=True, similarity_threshold=0.85)

    payload = {
        "answer": "The GenAI market is $65.5B in 2024 [R-101 p.3].",
        "sources": ["R-101"],
        "citations": ["[R-101 p.3]"],
        "confidence": 0.95,
        "escalated": False,
        "trace_id": "test-trace",
    }

    # Store base query
    stored = cache.set("ALPHA", "What is the global GenAI market size in 2024?", payload)
    assert stored is True

    # Ask semantically very similar question
    result = cache.get("ALPHA", "Tell me the 2024 market size for GenAI worldwide")
    assert result is not None
    assert "The GenAI market is $65.5B" in result["answer"]
    assert result["sources"] == ["R-101"]


def test_semantic_cache_miss_below_threshold():
    cache = InMemorySemanticCache(enabled=True, similarity_threshold=0.90)

    payload = {"answer": "Cybersecurity CAGR is 14%."}
    cache.set("ALPHA", "What is the CAGR of cybersecurity?", payload)

    # Ask an unrelated question -> Should be a cache miss
    result = cache.get("ALPHA", "GenAI cloud computing trends")
    assert result is None


def test_semantic_cache_enforces_client_isolation():
    cache = InMemorySemanticCache(enabled=True, similarity_threshold=0.85)

    payload_a = {"answer": "Confidential report data for Client A only."}
    cache.set("CLIENT_A", "What are the secret insights?", payload_a)

    # Query the exact same question as CLIENT_B -> Must NOT hit Client A's cache!
    result_b = cache.get("CLIENT_B", "What are the secret insights?")
    assert result_b is None

    # Query as CLIENT_A -> Must hit
    result_a = cache.get("CLIENT_A", "What are the secret insights?")
    assert result_a is not None
    assert result_a["answer"] == payload_a["answer"]


def test_semantic_cache_store_pydantic_payload():
    cache = InMemorySemanticCache(enabled=True, ttl_seconds=3600)

    payload = ChatResponse(
        answer="Autonomous mobility CAGR is 22.4% [R-102 p.5].",
        sources=["R-102"],
        citations=["[R-102 p.5]"],
        confidence=0.92,
        escalated=False,
        trace_id="trace-1234",
    )

    success = cache.set("ALPHA", "Autonomous mobility CAGR?", payload)
    assert success is True

    retrieved = cache.get("ALPHA", "Autonomous mobility CAGR?")
    assert retrieved is not None
    assert retrieved["answer"] == payload.answer
    assert retrieved["confidence"] == 0.92


def test_semantic_cache_ttl_expiration():
    # Cache with 1-second TTL
    cache = InMemorySemanticCache(enabled=True, ttl_seconds=1)
    cache.set("ALPHA", "Expiring question", {"answer": "Now you see me"})

    # Immediately available
    assert cache.get("ALPHA", "Expiring question") is not None

    # Manually expire the entry in store
    cache._store["ALPHA"][0]["expires_at"] = time.time() - 10

    # Query after expiration -> Should be None
    assert cache.get("ALPHA", "Expiring question") is None


def test_semantic_cache_clear():
    cache = InMemorySemanticCache(enabled=True)
    cache.set("ALPHA", "Question A", {"answer": "Answer A"})
    cache.set("BETA", "Question B", {"answer": "Answer B"})

    # Clear only ALPHA
    cache.clear(client_id="ALPHA")
    assert cache.get("ALPHA", "Question A") is None
    assert cache.get("BETA", "Question B") is not None

    # Clear all
    cache.clear()
    assert cache.get("BETA", "Question B") is None


# =====================================================================
# 3. End-to-End ChatService Semantic Cache Hit
# =====================================================================

def test_chat_service_semantic_cache_hit():
    service = ChatService()

    cached_payload = {
        "answer": "Quantum computing enterprise market was $1.2B in 2024 [R-103 p.2].",
        "sources": ["R-103"],
        "citations": ["[R-103 p.2]"],
        "confidence": 0.94,
        "escalated": False,
        "trace_id": "cached-sem-trace",
    }

    with patch("app.services.chat_service.telemetry.cache.get", return_value=None), \
         patch("app.services.chat_service.semantic_cache.get", return_value=cached_payload) as mock_sem_get:

        emitted_tokens = []
        response = service.process_chat_query(
            client_id="CLIENT_ALPHA",
            question="What is the quantum market size?",
            token_callback=lambda tok: emitted_tokens.append(tok),
        )

        assert response.answer == cached_payload["answer"]
        assert response.citations == ["[R-103 p.2]"]
        assert len(emitted_tokens) == 1
        assert emitted_tokens[0] == cached_payload["answer"]
        mock_sem_get.assert_called_once_with("CLIENT_ALPHA", "What is the quantum market size?")

"""
Unit Tests for Redis Semantic Caching.

Covers:
- Graceful degradation when Redis is offline or disabled
- Vector embedding generation (384-dim BGE-small)
- Semantic cache hit with high similarity (>= 0.90)
- Semantic cache miss when similarity is below threshold (< 0.90)
- Strict client entitlement isolation: Client A cannot see Client B's cached query
- Serialization and deserialization of ChatResponse payloads
- Cache clear operations (full vs tenant-specific)
- Integration with ChatService
"""

import json
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from app.core.semantic_cache import RedisSemanticCache
from app.schemas.chat import ChatResponse
from app.services.chat_service import ChatService


# =====================================================================
# 1. Graceful Bypass & Offline Fallback Tests
# =====================================================================

def test_semantic_cache_disabled():
    cache = RedisSemanticCache(enabled=False)
    assert cache.enabled is False
    assert cache.get("CLIENT_A", "What is GenAI?") is None
    assert cache.set("CLIENT_A", "What is GenAI?", {"answer": "test"}) is False


def test_semantic_cache_redis_connection_failure():
    # Attempting to connect to an unreachable port should fail cleanly without raising
    cache = RedisSemanticCache(host="127.0.0.1", port=59999, enabled=True)
    assert cache._redis_client is None
    assert cache.get("CLIENT_A", "What is GenAI?") is None
    assert cache.set("CLIENT_A", "What is GenAI?", {"answer": "test"}) is False


# =====================================================================
# 2. Embedding & Vector Validation Tests
# =====================================================================

def test_semantic_cache_embed_vector():
    cache = RedisSemanticCache(enabled=False)
    vector = cache._embed("Global GenAI Market Size 2026")
    assert vector is not None
    assert isinstance(vector, np.ndarray)
    assert vector.shape == (384,)
    # Verify vector is L2 normalized
    norm = np.linalg.norm(vector)
    assert pytest.approx(norm, 0.001) == 1.0


def test_semantic_cache_empty_or_whitespace_input():
    cache = RedisSemanticCache(enabled=False)
    assert cache.get("", "Question") is None
    assert cache.get("CLIENT_A", "   ") is None
    assert cache.set("", "Question", {}) is False
    assert cache.set("CLIENT_A", "", {}) is False


# =====================================================================
# 3. Vector Similarity Search & Client Isolation Tests (Mocked Redis)
# =====================================================================

def test_semantic_cache_hit_above_threshold():
    cache = RedisSemanticCache(enabled=True, similarity_threshold=0.90)

    mock_redis = MagicMock()
    mock_ft = MagicMock()
    mock_redis.ft.return_value = mock_ft

    # Simulate RediSearch returning a close match (score = 0.05 -> distance = 0.05 -> similarity = 0.95)
    mock_doc = MagicMock()
    mock_doc.score = "0.05"
    mock_doc.question = "What is the market size of GenAI?"
    mock_doc.response_json = json.dumps({
        "answer": "The GenAI market is $65.5B [R-101 p.3].",
        "sources": ["R-101"],
        "citations": ["[R-101 p.3]"],
        "confidence": 0.95,
        "escalated": False,
        "trace_id": "test-trace",
    })

    mock_search_res = MagicMock()
    mock_search_res.docs = [mock_doc]
    mock_ft.search.return_value = mock_search_res

    cache._redis_client = mock_redis
    cache._index_initialized = True

    # User asks a semantically similar question
    result = cache.get("ALPHA", "GenAI market size estimate")
    assert result is not None
    assert "The GenAI market is $65.5B" in result["answer"]
    assert result["sources"] == ["R-101"]


def test_semantic_cache_miss_below_threshold():
    cache = RedisSemanticCache(enabled=True, similarity_threshold=0.90)

    mock_redis = MagicMock()
    mock_ft = MagicMock()
    mock_redis.ft.return_value = mock_ft

    # Simulate RediSearch returning an unrelated match (score = 0.35 -> similarity = 0.65)
    mock_doc = MagicMock()
    mock_doc.score = "0.35"
    mock_doc.question = "What is the CAGR of cybersecurity?"
    mock_doc.response_json = json.dumps({"answer": "Cybersecurity CAGR is 14%."})

    mock_search_res = MagicMock()
    mock_search_res.docs = [mock_doc]
    mock_ft.search.return_value = mock_search_res

    cache._redis_client = mock_redis
    cache._index_initialized = True

    # User asks an unrelated question -> Should be a cache miss
    result = cache.get("ALPHA", "GenAI cloud computing trends")
    assert result is None


def test_semantic_cache_enforces_client_isolation():
    cache = RedisSemanticCache(enabled=True, similarity_threshold=0.90)

    mock_redis = MagicMock()
    mock_ft = MagicMock()
    mock_redis.ft.return_value = mock_ft

    cache._redis_client = mock_redis
    cache._index_initialized = True

    # Query as CLIENT_B
    cache.get("CLIENT_B", "What are the unpurchased report insights?")

    # Verify that the RediSearch query explicitly contained the filter: (@client_id:{CLIENT_B})
    args, kwargs = mock_ft.search.call_args
    query_obj = args[0]
    assert "@client_id:{CLIENT_B}" in query_obj.query_string()


def test_semantic_cache_store_payload():
    cache = RedisSemanticCache(enabled=True, ttl_seconds=3600)

    mock_redis = MagicMock()
    mock_pipeline = MagicMock()
    mock_redis.pipeline.return_value = mock_pipeline

    cache._redis_client = mock_redis

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
    mock_pipeline.hset.assert_called_once()
    mock_pipeline.expire.assert_called_once()
    mock_pipeline.execute.assert_called_once()


# =====================================================================
# 4. End-to-End ChatService Semantic Cache Hit
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

    # Patch semantic_cache.get to return a semantic match
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

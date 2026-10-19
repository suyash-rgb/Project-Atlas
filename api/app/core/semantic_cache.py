"""
In-Memory Semantic Cache Module with Client Entitlement Scoping & Vector Search.

Features:
- Sub-millisecond similarity caching using FastEmbed (BGE-small 384-dim) and NumPy vector dot-product.
- Strict Client Isolation: Caches are partitioned by client_id to prevent entitlement leakage.
- Cosine Similarity Thresholding: Only semantic hits exceeding the similarity threshold (e.g. >= 0.90) are served.
- TTL Expiration & Thread-Safety: Automatic timestamp expiration and lock-protected updates.
- Zero External Dependencies: Runs entirely in Python RAM without requiring Redis or Docker.
"""

import json
import logging
import threading
import time
from typing import Optional, Dict, Any, List
import numpy as np

from app.core.config import settings

logger = logging.getLogger("project_atlas.semantic_cache")

_EMBED_MODEL = None


def get_embedding_model():
    """Lazily load FastEmbed BGE-small embedding model (384 dimensions)."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        try:
            from fastembed import TextEmbedding
            _EMBED_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        except Exception as exc:
            logger.warning("fastembed_init_failed for semantic cache: %s", exc)
            return None
    return _EMBED_MODEL


class InMemorySemanticCache:
    """
    High-performance, in-memory semantic cache using vectorized cosine similarity.
    Stores and queries embeddings of questions scoped strictly by client_id.
    """

    VECTOR_DIM = 384
    MAX_ENTRIES_PER_CLIENT = 500

    def __init__(
        self,
        similarity_threshold: Optional[float] = None,
        ttl_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
        **_kwargs,  # Gracefully accept host, port, etc., for backward compatibility
    ):
        self.threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else getattr(settings, "SEMANTIC_CACHE_THRESHOLD", 0.90)
        )
        self.ttl_seconds = (
            ttl_seconds
            if ttl_seconds is not None
            else getattr(settings, "SEMANTIC_CACHE_TTL_SECONDS", 86400)
        )
        self.enabled = (
            enabled
            if enabled is not None
            else getattr(settings, "SEMANTIC_CACHE_ENABLED", True)
        )

        # Storage structure: { clean_client_id: [ {"question": str, "vector": np.ndarray, "response": dict, "expires_at": float} ] }
        self._store: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = threading.Lock()

        logger.info(
            "in_memory_semantic_cache_initialized threshold=%.2f ttl_seconds=%d enabled=%s",
            self.threshold,
            self.ttl_seconds,
            self.enabled,
        )

    def _embed(self, text: str) -> Optional[np.ndarray]:
        """Calculates 384-dimensional normalized float32 embedding."""
        clean_text = text.strip() if text else ""
        if not clean_text:
            return None

        model = get_embedding_model()
        if model is None:
            return None
        try:
            embedding = list(model.embed([clean_text]))[0]
            vector = np.array(embedding, dtype=np.float32)
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            return vector
        except Exception as exc:
            logger.warning("embed_question_failed text_len=%s error=%s", len(clean_text), exc)
            return None

    def get(self, client_id: str, question: str) -> Optional[Dict[str, Any]]:
        """
        Queries in-memory semantic cache for the closest match for this specific client_id.
        Returns parsed response dict if cosine similarity >= threshold, else None.
        """
        if not self.enabled:
            return None

        clean_client = client_id.strip().upper() if client_id else ""
        clean_q = question.strip() if question else ""
        if not clean_client or not clean_q:
            return None

        query_vector = self._embed(clean_q)
        if query_vector is None:
            return None

        now = time.time()
        with self._lock:
            client_entries = self._store.get(clean_client, [])
            if not client_entries:
                return None

            # Filter out expired items
            valid_entries = [e for e in client_entries if e["expires_at"] > now]
            if len(valid_entries) != len(client_entries):
                self._store[clean_client] = valid_entries
            if not valid_entries:
                return None

            # Vectorized Cosine Similarity: dot product of normalized vectors
            vectors = np.array([e["vector"] for e in valid_entries], dtype=np.float32)
            similarities = np.dot(vectors, query_vector)

            best_idx = int(np.argmax(similarities))
            best_sim = float(similarities[best_idx])

            if best_sim >= self.threshold:
                matched_entry = valid_entries[best_idx]
                logger.info(
                    "in_memory_semantic_cache_hit client_id=%s similarity=%.4f matched_q='%s'",
                    clean_client,
                    best_sim,
                    matched_entry["question"][:50],
                )
                return matched_entry["response"]
            else:
                logger.debug(
                    "in_memory_semantic_cache_miss client_id=%s max_similarity=%.4f threshold=%.2f",
                    clean_client,
                    best_sim,
                    self.threshold,
                )
                return None

    def set(self, client_id: str, question: str, response_payload: Any) -> bool:
        """
        Saves question embedding, client_id, and serialized response into memory.
        """
        if not self.enabled:
            return False

        clean_client = client_id.strip().upper() if client_id else ""
        clean_q = question.strip() if question else ""
        if not clean_client or not clean_q:
            return False

        query_vector = self._embed(clean_q)
        if query_vector is None:
            return False

        if hasattr(response_payload, "model_dump"):
            resp_dict = response_payload.model_dump()
        elif hasattr(response_payload, "dict"):
            resp_dict = response_payload.dict()
        elif isinstance(response_payload, dict):
            resp_dict = response_payload
        else:
            resp_dict = {"answer": str(response_payload)}

        expires_at = time.time() + (self.ttl_seconds if self.ttl_seconds > 0 else 86400)

        entry = {
            "question": clean_q,
            "vector": query_vector,
            "response": resp_dict,
            "expires_at": expires_at,
        }

        with self._lock:
            if clean_client not in self._store:
                self._store[clean_client] = []

            # Deduplicate if exact same question is already present
            existing_idx = next(
                (i for i, e in enumerate(self._store[clean_client]) if e["question"].lower() == clean_q.lower()),
                None,
            )
            if existing_idx is not None:
                self._store[clean_client][existing_idx] = entry
            else:
                if len(self._store[clean_client]) >= self.MAX_ENTRIES_PER_CLIENT:
                    self._store[clean_client].pop(0)  # Evict oldest
                self._store[clean_client].append(entry)

        logger.info(
            "in_memory_semantic_cache_stored client_id=%s question_length=%d total_client_cached=%d",
            clean_client,
            len(clean_q),
            len(self._store[clean_client]),
        )
        return True

    def clear(self, client_id: Optional[str] = None):
        """Clears all cached entries or entries belonging to a specific client_id."""
        with self._lock:
            if client_id:
                clean_client = client_id.strip().upper()
                self._store.pop(clean_client, None)
            else:
                self._store.clear()


# Backward compatibility alias
RedisSemanticCache = InMemorySemanticCache

# Global singleton instance
semantic_cache = InMemorySemanticCache()

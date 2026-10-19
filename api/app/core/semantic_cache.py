"""
Redis Semantic Cache Module with Client Entitlement Scoping & Vector Search.

Features:
- Sub-millisecond similarity caching using RediSearch Vector Similarity Search (HNSW).
- Strict Client Isolation: Caches are partitioned by client_id to prevent entitlement leakage.
- Cosine Distance Thresholding: Only semantic hits exceeding the similarity threshold (e.g. >= 0.90) are served.
- Graceful Degradation: If Redis is unavailable or unconfigured, falls back cleanly to None without failing requests.
"""

import json
import logging
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


class RedisSemanticCache:
    """
    Semantic Cache powered by Redis RediSearch Vector Indexing.
    Stores and queries embeddings of questions scoped by client_id.
    """

    INDEX_NAME = "idx:atlas_semantic_cache"
    PREFIX = "cache:atlas:"
    VECTOR_DIM = 384

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        db: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        ttl_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
    ):
        self.host = host or getattr(settings, "REDIS_HOST", "localhost")
        self.port = port or getattr(settings, "REDIS_PORT", 6379)
        self.password = password or getattr(settings, "REDIS_PASSWORD", None)
        self.db = db if db is not None else getattr(settings, "REDIS_DB", 0)
        self.threshold = similarity_threshold if similarity_threshold is not None else getattr(settings, "SEMANTIC_CACHE_THRESHOLD", 0.90)
        self.ttl_seconds = ttl_seconds or getattr(settings, "SEMANTIC_CACHE_TTL_SECONDS", 86400)
        self.enabled = enabled if enabled is not None else getattr(settings, "SEMANTIC_CACHE_ENABLED", True)

        self._redis_client = None
        self._index_initialized = False

        if self.enabled:
            self._connect()

    def _connect(self):
        """Attempts connection to Redis."""
        try:
            import redis
            self._redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=False,  # Keep binary support for vectors
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            # Ping to verify active connection
            self._redis_client.ping()
            self._ensure_index()
            logger.info("redis_semantic_cache_connected host=%s port=%s", self.host, self.port)
        except Exception as exc:
            logger.warning("redis_connection_failed host=%s port=%s error=%s (operating in bypass mode)", self.host, self.port, exc)
            self._redis_client = None

    def _ensure_index(self):
        """Ensures RediSearch vector index exists with client_id tag and question_vector."""
        if not self._redis_client or self._index_initialized:
            return

        try:
            from redis.commands.search.field import TagField, TextField, VectorField
            from redis.commands.search.index_definition import IndexDefinition, IndexType

            try:
                self._redis_client.ft(self.INDEX_NAME).info()
                self._index_initialized = True
                return
            except Exception:
                pass  # Index does not exist, create it

            schema = (
                TagField("client_id"),
                TextField("question"),
                TextField("response_json"),
                VectorField(
                    "question_vector",
                    "HNSW",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": self.VECTOR_DIM,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
            )
            definition = IndexDefinition(prefix=[self.PREFIX], index_type=IndexType.HASH)
            self._redis_client.ft(self.INDEX_NAME).create_index(schema, definition=definition)
            self._index_initialized = True
            logger.info("redis_semantic_cache_index_created name=%s", self.INDEX_NAME)
        except Exception as exc:
            logger.warning("redis_index_init_failed error=%s (will use key fallback)", exc)

    def _embed(self, text: str) -> Optional[np.ndarray]:
        """Calculates 384-dimensional normalized float32 embedding."""
        model = get_embedding_model()
        if model is None:
            return None
        try:
            embedding = list(model.embed([text]))[0]
            vector = np.array(embedding, dtype=np.float32)
            # Normalize vector for cosine distance
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            return vector
        except Exception as exc:
            logger.warning("embed_question_failed text_len=%s error=%s", len(text), exc)
            return None

    def get(self, client_id: str, question: str) -> Optional[Dict[str, Any]]:
        """
        Queries Redis semantic cache for the closest match for this specific client_id.
        Returns parsed response dict if cosine similarity >= threshold, else None.
        """
        if not self.enabled or not self._redis_client:
            return None

        clean_client = client_id.strip().upper()
        clean_q = question.strip()
        if not clean_client or not clean_q:
            return None

        query_vector = self._embed(clean_q)
        if query_vector is None:
            return None

        try:
            from redis.commands.search.query import Query

            # Filter strictly by client_id tag and execute KNN search
            # Cosine distance = 1 - cosine_similarity.
            # Max allowable distance = 1 - self.threshold
            max_distance = round(1.0 - self.threshold, 4)

            q_str = f"(@client_id:{{{clean_client}}})=>[KNN 1 @question_vector $vec AS score]"
            q = (
                Query(q_str)
                .sort_by("score")
                .return_fields("score", "question", "response_json")
                .paging(0, 1)
                .dialect(2)
            )

            res = self._redis_client.ft(self.INDEX_NAME).search(
                q, query_params={"vec": query_vector.tobytes()}
            )

            if not res or not res.docs:
                return None

            best_doc = res.docs[0]
            distance = float(best_doc.score)
            similarity = 1.0 - distance

            if similarity >= self.threshold:
                logger.info(
                    "semantic_cache_hit client_id=%s similarity=%.4f matched_q='%s'",
                    clean_client,
                    similarity,
                    getattr(best_doc, "question", "")[:50],
                )
                raw_json = getattr(best_doc, "response_json", "{}")
                if isinstance(raw_json, bytes):
                    raw_json = raw_json.decode("utf-8")
                return json.loads(raw_json)
            else:
                logger.debug(
                    "semantic_cache_miss_subthreshold client_id=%s similarity=%.4f threshold=%.2f",
                    clean_client,
                    similarity,
                    self.threshold,
                )
                return None

        except Exception as exc:
            logger.debug("semantic_cache_query_exception error=%s", exc)
            return None

    def set(self, client_id: str, question: str, response_payload: Any) -> bool:
        """
        Saves question embedding, client_id, and serialized response into Redis.
        """
        if not self.enabled or not self._redis_client:
            return False

        clean_client = client_id.strip().upper()
        clean_q = question.strip()
        if not clean_client or not clean_q:
            return False

        query_vector = self._embed(clean_q)
        if query_vector is None:
            return False

        try:
            import hashlib
            doc_id = hashlib.sha256(f"{clean_client}::{clean_q}".encode("utf-8")).hexdigest()
            key = f"{self.PREFIX}{doc_id}"

            if hasattr(response_payload, "model_dump"):
                resp_dict = response_payload.model_dump()
            elif hasattr(response_payload, "dict"):
                resp_dict = response_payload.dict()
            elif isinstance(response_payload, dict):
                resp_dict = response_payload
            else:
                resp_dict = {"answer": str(response_payload)}

            payload_str = json.dumps(resp_dict)

            pipe = self._redis_client.pipeline()
            pipe.hset(
                key,
                mapping={
                    "client_id": clean_client,
                    "question": clean_q,
                    "response_json": payload_str,
                    "question_vector": query_vector.tobytes(),
                    "created_at": time.time(),
                },
            )
            if self.ttl_seconds > 0:
                pipe.expire(key, self.ttl_seconds)
            pipe.execute()

            logger.info("semantic_cache_stored client_id=%s key=%s", clean_client, key)
            return True
        except Exception as exc:
            logger.warning("semantic_cache_set_failed error=%s", exc)
            return False

    def clear(self, client_id: Optional[str] = None):
        """Clears all cached entries or entries belonging to a specific client_id."""
        if not self._redis_client:
            return
        try:
            keys = self._redis_client.keys(f"{self.PREFIX}*")
            if not keys:
                return
            if client_id:
                clean_client = client_id.strip().upper().encode("utf-8")
                for k in keys:
                    cid = self._redis_client.hget(k, "client_id")
                    if cid == clean_client:
                        self._redis_client.delete(k)
            else:
                self._redis_client.delete(*keys)
        except Exception as exc:
            logger.warning("semantic_cache_clear_failed error=%s", exc)


# Global singleton instance
semantic_cache = RedisSemanticCache()

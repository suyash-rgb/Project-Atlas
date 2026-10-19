"""
Semantic Cross-Scoring Re-Ranker for Project Atlas.

Implements a fine-grained 2nd-stage re-ranking mechanism that rescores
candidate chunks from hybrid retrieval (dense ChromaDB + sparse TF-IDF) using:
1. FastEmbed embedding cross-cosine semantic similarity.
2. Exact alphanumeric token & report entity matching (e.g. 'R-101', 'USD 4.21 B', 'CAGR').
3. Term proximity window density (rewarding dense clusters of query keywords).
4. Normalized multi-feature calibrated scoring.
"""

import math
import re
import logging
from typing import Any, List, Optional, Set
import numpy as np
from llama_index.core import Settings

logger = logging.getLogger("project_atlas.reranker")

STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only",
    "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she", "should",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "would", "you", "your", "yours", "yourself", "yourselves",
}


def _tokenize_terms(text: str) -> List[str]:
    """Extract informative lowercase terms excluding common stop words."""
    if not text:
        return []
    terms = re.findall(r"[a-zA-Z0-9_\-\.]+", text.lower())
    return [t for t in terms if len(t) > 1 and t not in STOP_WORDS]


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class SemanticReRanker:
    """
    Second-stage semantic cross re-ranker.
    Ranks hybrid candidate chunks to ensure exact entities, numbers, and conceptual
    relevance are prioritized accurately before reaching the LLM synthesizer.
    """

    def __init__(
        self,
        weight_semantic: float = 0.50,
        weight_exact: float = 0.30,
        weight_proximity: float = 0.10,
        weight_prior: float = 0.10,
    ):
        self.w_semantic = weight_semantic
        self.w_exact = weight_exact
        self.w_proximity = weight_proximity
        self.w_prior = weight_prior

    def compute_exact_match_score(self, query_terms: List[str], chunk_text: str) -> float:
        """
        Scores exact query tokens present in the chunk text, with an extra boost
        for alphanumeric metrics, report IDs (e.g. R-101), and numerical figures.
        """
        if not query_terms or not chunk_text:
            return 0.0

        text_lower = chunk_text.lower()
        matched_weight = 0.0
        total_weight = 0.0

        for term in query_terms:
            # Alphanumerics, report IDs (r-10x), or digits carry higher weight
            is_high_value = bool(re.search(r"\d", term) or term.startswith("r-") or term in {"cagr", "ami", "mbr"})
            term_weight = 2.0 if is_high_value else 1.0
            total_weight += term_weight

            # Substring / boundary match
            if term in text_lower:
                matched_weight += term_weight

        return (matched_weight / total_weight) if total_weight > 0 else 0.0

    def compute_proximity_score(self, query_terms: List[str], chunk_text: str) -> float:
        """
        Scores query term proximity. When multiple query terms occur within
        a compact word window, proximity score is high.
        """
        if len(query_terms) < 2 or not chunk_text:
            return 0.5

        words = [w.strip(".,;:()[]{}\"'").lower() for w in chunk_text.split() if w.strip()]
        term_positions = {}
        for idx, word in enumerate(words):
            for term in query_terms:
                if term in word:
                    if term not in term_positions:
                        term_positions[term] = []
                    term_positions[term].append(idx)

        # If less than 2 distinct query terms found, no proximity cluster
        if len(term_positions) < 2:
            return 0.2 if term_positions else 0.0

        # Calculate smallest span containing all matched terms
        all_first_positions = [positions[0] for positions in term_positions.values()]
        min_pos = min(all_first_positions)
        max_pos = max(all_first_positions)
        span = max_pos - min_pos + 1

        # A tight window <= 25 words gets high score
        if span <= 25:
            return 1.0
        elif span <= 60:
            return 0.7
        elif span <= 120:
            return 0.4
        return 0.2

    def rerank(
        self,
        query: str,
        candidates: List[Any],
        top_k: int = 5,
    ) -> List[Any]:
        """
        Re-ranks candidate chunks using multi-feature semantic and lexical scoring.
        Updates each chunk's score attribute to the normalized re-ranked score.
        """
        if not candidates:
            return []

        query_terms = _tokenize_terms(query)
        scored_candidates = []

        # 1. Compute query embedding if embed_model is available
        query_vec: Optional[List[float]] = None
        embed_model = getattr(Settings, "embed_model", None)
        if embed_model and hasattr(embed_model, "get_text_embedding"):
            try:
                query_vec = embed_model.get_text_embedding(query)
            except Exception as e:
                logger.debug("reranker_query_embed_failed error=%s", e)

        for chunk in candidates:
            text = getattr(chunk, "text", "")
            prior_score = float(getattr(chunk, "score", 0.0))

            # Feature 1: Semantic Cosine Similarity
            semantic_score = prior_score
            if query_vec and embed_model:
                try:
                    chunk_vec = embed_model.get_text_embedding(text[:500])
                    semantic_score = _cosine_similarity(query_vec, chunk_vec)
                except Exception as e:
                    logger.debug("reranker_chunk_embed_failed error=%s", e)

            # Feature 2: Exact Alphanumeric & Entity Match
            exact_score = self.compute_exact_match_score(query_terms, text)

            # Feature 3: Proximity Density
            proximity_score = self.compute_proximity_score(query_terms, text)

            # Composite weighted fusion
            composite_score = (
                (self.w_semantic * semantic_score)
                + (self.w_exact * exact_score)
                + (self.w_proximity * proximity_score)
                + (self.w_prior * prior_score)
            )

            scored_candidates.append((chunk, composite_score))

        # Sort descending by composite score
        scored_candidates.sort(key=lambda pair: pair[1], reverse=True)

        # Format top_k results with updated score
        results = []
        for chunk, comp_score in scored_candidates[:top_k]:
            setattr(chunk, "score", round(float(comp_score), 4))
            results.append(chunk)

        logger.info(
            "rerank_completed initial_candidates=%s top_k=%s",
            len(candidates),
            len(results),
        )
        return results


_default_reranker: Optional[SemanticReRanker] = None


def get_reranker() -> SemanticReRanker:
    """Returns singleton instance of SemanticReRanker."""
    global _default_reranker
    if _default_reranker is None:
        _default_reranker = SemanticReRanker()
    return _default_reranker

"""
Sparse TF-IDF and Reciprocal Rank Fusion (RRF) Hybrid Retrieval Engine for Project Atlas.

Implements sub-millisecond keyword retrieval paired with dense vector search to capture
both conceptual semantic similarity and exact alphanumeric token matches (e.g. 'R-101', '4.21B', 'CAGR').
"""

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple


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


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric and hyphenated terms."""
    if not text:
        return []
    tokens = re.findall(r"[a-zA-Z0-9_\-\.]+", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in STOP_WORDS]


class SparseDocument:
    def __init__(
        self,
        doc_id: str,
        report_id: str,
        page: int,
        text: str,
        title: str,
        sector: str,
        access: str,
    ):
        self.doc_id = doc_id
        self.report_id = report_id
        self.page = page
        self.text = text
        self.title = title
        self.sector = sector
        self.access = access
        self.tokens = tokenize(text)
        self.token_counts = Counter(self.tokens)
        self.length = len(self.tokens)


class TFIDFIndex:
    """In-memory inverted index with TF-IDF scoring and entitlement filtering."""

    def __init__(self):
        self.documents: Dict[str, SparseDocument] = {}
        self.df: Counter = Counter()  # Document frequency per term
        self.total_docs: int = 0

    def add_document(
        self,
        doc_id: str,
        report_id: str,
        page: int,
        text: str,
        title: str = "",
        sector: str = "",
        access: str = "paid",
    ) -> None:
        """Add or update a document chunk in the inverted index."""
        if doc_id in self.documents:
            # Remove old document terms from df
            old_unique = set(self.documents[doc_id].token_counts.keys())
            for t in old_unique:
                self.df[t] -= 1
                if self.df[t] <= 0:
                    del self.df[t]
            self.total_docs -= 1

        doc = SparseDocument(
            doc_id=doc_id,
            report_id=report_id,
            page=page,
            text=text,
            title=title,
            sector=sector,
            access=access,
        )
        self.documents[doc_id] = doc
        self.total_docs += 1

        for term in set(doc.token_counts.keys()):
            self.df[term] += 1

    def search(
        self,
        query: str,
        allowed_reports: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> List[Tuple[SparseDocument, float]]:
        """
        Score and rank documents matching query terms, filtered strictly by allowed_reports.
        """
        query_tokens = tokenize(query)
        if not query_tokens or self.total_docs == 0:
            return []

        allowed_set = set(allowed_reports) if allowed_reports is not None else None
        scores: Dict[str, float] = defaultdict(float)

        for term in query_tokens:
            doc_freq = self.df.get(term, 0)
            if doc_freq == 0:
                continue

            # Standard smooth IDF formula
            idf = math.log((self.total_docs + 1) / (doc_freq + 1)) + 1.0

            for doc_id, doc in self.documents.items():
                if allowed_set is not None and doc.report_id not in allowed_set:
                    continue

                tf = doc.token_counts.get(term, 0)
                if tf > 0:
                    # Normalized TF
                    norm_tf = (tf / doc.length) if doc.length > 0 else 0
                    scores[doc_id] += norm_tf * idf

        if not scores:
            return []

        ranked_doc_ids = sorted(scores.keys(), key=lambda did: scores[did], reverse=True)[:top_k]
        return [(self.documents[did], scores[did]) for did in ranked_doc_ids]


def reciprocal_rank_fusion(
    dense_items: List[Any],
    sparse_items: List[Any],
    k: int = 60,
    dense_id_fn=lambda x: getattr(x, "report_id", "") + f":p{getattr(x, 'page', 1)}",
    sparse_id_fn=lambda x: getattr(x, "report_id", "") + f":p{getattr(x, 'page', 1)}",
) -> List[Tuple[Any, float]]:
    """
    Combines ranked outputs from dense vector search and sparse keyword search using RRF.
    
    Formula:
      RRF_score(d) = sum_{m in {dense, sparse}} (1 / (k + rank_m(d)))
    """
    rrf_scores: Dict[str, float] = defaultdict(float)
    item_map: Dict[str, Any] = {}

    # Accumulate dense ranks (1-indexed)
    for rank, item in enumerate(dense_items, start=1):
        key = dense_id_fn(item)
        rrf_scores[key] += 1.0 / (k + rank)
        item_map[key] = item

    # Accumulate sparse ranks (1-indexed)
    for rank, item in enumerate(sparse_items, start=1):
        key = sparse_id_fn(item)
        rrf_scores[key] += 1.0 / (k + rank)
        if key not in item_map:
            item_map[key] = item

    sorted_keys = sorted(rrf_scores.keys(), key=lambda k_id: rrf_scores[k_id], reverse=True)
    return [(item_map[key], rrf_scores[key]) for key in sorted_keys]

"""
Discrepancy and Conflict Reconciliation Module.
Detects methodological, scope, and forecast window divergences between reports
(specifically the classic R-101 Turnkey vs R-102 Hardware-only discrepancy).
"""

from typing import List, Optional
from app.schemas.chat import ConflictItem
from app.agent.tools.retriever import RetrievedChunk


def detect_report_conflicts(
    query: str,
    retrieved_chunks: List[RetrievedChunk]
) -> List[ConflictItem]:
    """
    Examines retrieved report chunks and query text for documented methodology discrepancies.
    """
    conflicts: List[ConflictItem] = []
    report_ids = {c.report_id for c in retrieved_chunks}

    # Check for R-101 vs R-102 conflict
    # Triggers if both reports are present, or if query explicitly mentions both or asks about discrepancy
    query_lower = query.lower()
    mentions_both = ("r-101" in query_lower or "101" in query_lower) and ("r-102" in query_lower or "102" in query_lower)
    chunks_have_both = ("R-101" in report_ids and "R-102" in report_ids)
    discrepancy_intent = any(k in query_lower for k in ["conflict", "discrepancy", "difference", "compare", "trust", "why does", "versus", "vs"])

    if (mentions_both or chunks_have_both) and (discrepancy_intent or mentions_both or chunks_have_both):
        conflicts.append(
            ConflictItem(
                metric="Global Market Size (2024) & Projected CAGR",
                reports=["R-101", "R-102"],
                description=(
                    "Cognitive Market Research (R-101) estimates the 2024 market at USD 4.21 Billion (11.2% CAGR 2025-2030), "
                    "whereas Aquila Insights (R-102) estimates USD 3.87 Billion (9.8% CAGR 2024-2029)."
                ),
                scope_differences=(
                    "Scope Divergence: R-101 encompasses full turnkey solutions including hardware, AMI communication networks, "
                    "analytics software, and utility deployment services. In contrast, R-102 tracks AMR/AMI hardware endpoint shipments only. "
                    "Additionally, baseline forecast horizons differ (2025-2030 vs 2024-2029)."
                )
            )
        )

    return conflicts

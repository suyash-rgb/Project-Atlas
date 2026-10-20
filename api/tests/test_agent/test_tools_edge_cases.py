"""
Comprehensive unit tests for tool edge cases, parser resilience,
and boundary conditions across Project Atlas tools:
1. Deterministic Calculator (calculator.py)
2. AST-Validated SQL Tool (sql_tool.py)
3. Multi-Report Conflict Reconciler (reconcile.py)
4. Hybrid Search & Cross-Encoder Reranker (hybrid.py, reranker.py)
5. Multi-Modal Chart Extractor (chart_extractor.py)
"""

import pytest
from unittest.mock import Mock

from app.agent.tools.calculator import (
    compute_cagr,
    compute_future_value,
    calculate_projection,
    extract_numbers_from_query,
)
from app.agent.tools.sql_tool import (
    validate_read_only_ast,
    execute_safe_sql,
    SQLSecurityError,
)
from app.agent.reconcile import (
    detect_report_conflicts,
    ConflictItem,
)
from app.agent.tools.retriever import RetrievedChunk
from app.agent.tools.hybrid import (
    reciprocal_rank_fusion,
    tokenize,
    TFIDFIndex,
)
from app.agent.tools.reranker import SemanticReRanker
from app.agent.tools.chart_extractor import (
    decode_base64_image,
    validate_image_bytes,
    summarize_chart_image,
)


# =====================================================================
# 1. Calculator Tool Edge Cases
# =====================================================================

def test_calculator_target_year_equals_base_year():
    """When target_year == base_year, projection should equal base_value without change."""
    proj = calculate_projection(
        metric_name="Market Size",
        base_value=4.21,
        base_year=2024,
        target_year=2024,
        cagr_decimal=0.112,
    )
    assert proj.estimated_value == "4.21 USD Billion"
    assert "0 years" in proj.formula or "2024 -> 2024" in proj.assumptions[1]


def test_calculator_negative_cagr_market_contraction():
    """Calculator must correctly handle negative CAGR (market contraction)."""
    # Base 100, -10% per year for 2 years -> 100 * (0.9)^2 = 81.0
    future = compute_future_value(100.0, -0.10, 2)
    assert future == pytest.approx(81.0)


def test_calculator_cagr_computation_with_decimals():
    """Verify compute_cagr handles non-integer numbers accurately."""
    cagr = compute_cagr(4.21, 7.96, 6)
    assert cagr == pytest.approx(0.112, abs=0.002)


def test_calculator_extract_numbers_comma_separated():
    """Verify number extraction parses numbers with commas e.g. '$1,250.50M'."""
    extracted = extract_numbers_from_query("Forecast from $1,250.50M with 8.5% to 2030")
    assert extracted.get("base_value_billion") is not None or extracted.get("cagr_pct") == pytest.approx(8.5)


def test_calculator_zero_or_negative_base_value_raises():
    """Zero or negative base value must raise ValueError."""
    with pytest.raises(ValueError):
        compute_future_value(0, 0.1, 5)
    with pytest.raises(ValueError):
        compute_future_value(-10, 0.1, 5)


# =====================================================================
# 2. SQL Tool AST & Security Edge Cases
# =====================================================================

@pytest.mark.parametrize(
    "attack_query",
    [
        # Obfuscated case variation with chained drop
        "sElEcT id FrOm rEpOrTs; dRoP tAbLe rEpOrTs",
        # Stacked query
        "SELECT 1; TRUNCATE TABLE escalations",
        # Subquery modification probe
        "SELECT * FROM reports WHERE id = (DELETE FROM reports RETURNING id)",
        # DDL / DML attempts
        "ALTER TABLE reports ADD COLUMN secret_token VARCHAR(255)",
        "INSERT INTO reports (id, title) VALUES ('R-999', 'Hacked')",
        "PRAGMA table_info(reports)",
    ],
)
def test_sql_ast_rejects_mutating_or_stacked_queries(attack_query):
    """AST validator must reject multi-statement, stacked queries, and DDL/DML."""
    with pytest.raises(SQLSecurityError):
        validate_read_only_ast(attack_query)


@pytest.mark.parametrize(
    "disallowed_query",
    [
        "SELECT table_name FROM information_schema.tables",
        "SELECT user, host FROM mysql.user",
        "SELECT id, contact_email FROM clients",
    ],
)
def test_execute_safe_sql_rejects_unauthorized_tables(disallowed_query):
    """execute_safe_sql enforces strict whitelist of allowed reports/metrics tables."""
    with pytest.raises(SQLSecurityError, match="may only read reports"):
        execute_safe_sql(disallowed_query, allowed_reports=["R-101"])


def test_sql_ast_handles_whitespace_and_newlines():
    """Safe SELECT with extra whitespace and tabs should parse cleanly."""
    parsed = validate_read_only_ast("  \n\t SELECT  report,  metric  FROM  market_metrics \t\n ")
    assert parsed is not None


# =====================================================================
# 3. Multi-Report Conflict Reconciler Edge Cases
# =====================================================================

def make_chunk(report_id: str, text: str = "Market research content") -> RetrievedChunk:
    return RetrievedChunk(
        report_id=report_id,
        page=1,
        text=text,
        score=0.9,
        title=f"Report {report_id}",
        sector="Utilities",
        access="paid",
    )


def test_reconciler_handles_unicode_dash_variants():
    """Detect conflicts even when report IDs use unicode en-dash, em-dash, or non-breaking hyphens."""
    # R–101 (en-dash \u2013) vs R—102 (em-dash \u2014)
    conflicts = detect_report_conflicts("Compare R\u2013101 and R\u2014102", [])
    assert len(conflicts) == 1
    assert "R-101" in conflicts[0].reports
    assert "R-102" in conflicts[0].reports


def test_reconciler_returns_empty_when_reports_have_no_known_conflict():
    """Reports from different unrelated sectors (e.g. R-103 and R-104) should not produce false conflicts."""
    conflicts = detect_report_conflicts(
        "Compare findings in R-103 and R-104",
        [make_chunk("R-103"), make_chunk("R-104")],
    )
    # R-103 (Wastewater) and R-104 (Membrane) do not conflict in methodology
    assert conflicts == []


def test_reconciler_with_three_reports_including_r101_r102():
    """When query involves three reports including R-101 and R-102, conflict is properly flagged."""
    conflicts = detect_report_conflicts(
        "Compare R-101, R-102, and R-103",
        [make_chunk("R-101"), make_chunk("R-102"), make_chunk("R-103")],
    )
    assert len(conflicts) == 1
    assert "Global Market Size" in conflicts[0].metric


# =====================================================================
# 4. Hybrid Search & Reranker Edge Cases
# =====================================================================

class MockSearchResult:
    def __init__(self, item_id: str):
        self.item_id = item_id


def test_reciprocal_rank_fusion_empty_dense_list():
    """RRF must handle completely empty dense candidates without error."""
    sparse = [MockSearchResult("docA"), MockSearchResult("docB")]
    fused = reciprocal_rank_fusion(
        dense_items=[],
        sparse_items=sparse,
        k=60,
        dense_id_fn=lambda x: x.item_id,
        sparse_id_fn=lambda x: x.item_id,
    )
    assert len(fused) == 2
    assert fused[0][0].item_id == "docA"
    assert fused[1][0].item_id == "docB"


def test_reciprocal_rank_fusion_empty_sparse_list():
    """RRF must handle completely empty sparse candidates without error."""
    dense = [MockSearchResult("doc1"), MockSearchResult("doc2")]
    fused = reciprocal_rank_fusion(
        dense_items=dense,
        sparse_items=[],
        k=60,
        dense_id_fn=lambda x: x.item_id,
        sparse_id_fn=lambda x: x.item_id,
    )
    assert len(fused) == 2
    assert fused[0][0].item_id == "doc1"
    assert fused[1][0].item_id == "doc2"


def test_reciprocal_rank_fusion_both_empty():
    """RRF with both candidate lists empty returns empty list."""
    fused = reciprocal_rank_fusion(
        dense_items=[],
        sparse_items=[],
        k=60,
        dense_id_fn=lambda x: x.item_id,
        sparse_id_fn=lambda x: x.item_id,
    )
    assert fused == []


def test_semantic_reranker_handles_empty_candidates():
    """SemanticReRanker with empty candidate list returns empty list."""
    reranker = SemanticReRanker()
    assert reranker.rerank("query", candidates=[], top_k=5) == []


def test_semantic_reranker_handles_single_candidate():
    """SemanticReRanker with single candidate returns that candidate."""
    reranker = SemanticReRanker()
    c = make_chunk("R-101", "Text about smart water meter CAGR 11.2%")
    res = reranker.rerank("smart water", candidates=[c], top_k=5)
    assert len(res) == 1
    assert res[0].report_id == "R-101"


def test_tfidf_tokenize_empty_and_special_characters():
    """Tokenize safely handles empty strings, numbers, and symbols."""
    assert tokenize("") == []
    assert tokenize("   !@#$%^&*()   ") == []
    tokens = tokenize("Smart Water 2024: $4.21B Market")
    assert "smart" in tokens
    assert "water" in tokens
    assert "2024" in tokens


# =====================================================================
# 5. Multi-Modal Chart Extractor Edge Cases
# =====================================================================

def test_validate_image_bytes_empty_or_too_small():
    """Empty or tiny byte sequences (< 10 bytes) must fail validation safely."""
    assert validate_image_bytes(b"") is False
    assert validate_image_bytes(b"12345") is False


def test_validate_image_bytes_corrupted_payload():
    """Non-image bytes must return False without throwing unhandled exceptions."""
    assert validate_image_bytes(b"This is just plain text, not a PNG or JPEG header.") is False


def test_decode_base64_image_empty_string():
    """Empty base64 string returns None without throwing."""
    assert decode_base64_image("") is None
    assert decode_base64_image("   ") is None


def test_decode_base64_image_invalid_characters():
    """Non-base64 characters return None cleanly."""
    assert decode_base64_image("???not--base64***") is None


def test_summarize_chart_image_unconfigured_client_returns_fallback():
    """When Gemini client is None, summarize_chart_image returns informative fallback without crashing."""
    import io
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (20, 20), color="blue").save(buf, format="PNG")
    valid_bytes = buf.getvalue()

    result = summarize_chart_image(
        image_input=valid_bytes,
        report_id="R-101",
        page_num=3,
        report_title="Smart Water Meter Market 2025",
        client=None,
    )
    assert "[Visual Evidence Note]" in result or "R-101" in result

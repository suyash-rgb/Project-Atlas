"""
Deterministic Math and Financial Projection Calculator.
Executes exact CAGR, compound growth, and market projection formulas without LLM math hallucinations.
"""

import math
import re
from typing import Optional, Dict, Any, List
from app.schemas.chat import DerivedValueItem
from app.core.observability import observe_with_tags


def compute_cagr(start_val: float, end_val: float, periods: float) -> float:
    """
    CAGR = (End / Start) ** (1 / n) - 1
    Returns decimal percentage (e.g., 0.112 for 11.2%)
    """
    if start_val <= 0 or periods <= 0:
        raise ValueError("Start value and periods must be positive.")
    return (end_val / start_val) ** (1.0 / periods) - 1.0


def compute_future_value(base_val: float, cagr: float, periods: float) -> float:
    """
    V_end = V_start * ((1 + CAGR) ** n)
    """
    if periods < 0:
        raise ValueError("Periods must be non-negative.")
    return base_val * ((1.0 + cagr) ** periods)


@observe_with_tags(
    name="extract_calculation_inputs",
    tags=["tool:calculator", "calculation:input-extraction"],
)
def extract_numbers_from_query(query: str) -> Dict[str, float]:
    """
    Extracts explicit numbers, dollar values, percentages, or years from query string.
    """
    found: Dict[str, float] = {}
    
    # Check for dollar or unit values (e.g. $4.21B, 4.21 billion, $3.87B)
    usd_match = re.search(r'(?:\$|\b)([0-9]+(?:\.[0-9]+)?)\s*(?:billion|B)\b', query, re.IGNORECASE)
    if usd_match:
        found["base_value_billion"] = float(usd_match.group(1))

    # Check for percentage / CAGR (e.g. 11.2%, 9.8%)
    pct_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*%', query)
    if pct_match:
        found["cagr_pct"] = float(pct_match.group(1))

    # Check for years (e.g. from 2024 to 2030, or by 2030)
    year_range = re.search(r'(?:from\s+)?(20[2-3][0-9])\s*(?:to|-)\s*(20[2-3][0-9])', query, re.IGNORECASE)
    if year_range:
        y1, y2 = int(year_range.group(1)), int(year_range.group(2))
        found["start_year"] = float(y1)
        found["end_year"] = float(y2)
        found["periods"] = float(y2 - y1)
    else:
        target_year = re.search(r'(?:by|in|for)\s+(20[2-3][0-9])', query, re.IGNORECASE)
        if target_year:
            found["target_year"] = float(target_year.group(1))

    return found


@observe_with_tags(
    name="calculate_market_projection",
    tags=["tool:calculator", "calculation:deterministic"],
)
def calculate_projection(
    metric_name: str,
    base_value: float,
    base_year: int,
    target_year: int,
    cagr_decimal: float,
    unit: str = "USD Billion"
) -> DerivedValueItem:
    """
    Generates a formal DerivedValueItem with explicit math formula and verified assumptions.
    """
    n = target_year - base_year
    future_val = compute_future_value(base_value, cagr_decimal, n)
    cagr_display = cagr_decimal * 100

    formula_str = f"V_{target_year} = V_{base_year} * (1 + CAGR)^{n} = {base_value} * (1 + {cagr_decimal:.4f})^{n}"
    estimated_str = f"{future_val:.2f} {unit}"

    return DerivedValueItem(
        metric=metric_name,
        formula=formula_str,
        assumptions=[
            f"Base Year {base_year} value = {base_value} {unit}",
            f"Projected constant CAGR = {cagr_display:.1f}% across {n} years ({base_year} -> {target_year})",
            "Excludes unforeseen regulatory disruptions or macro FX fluctuations"
        ],
        estimated_value=estimated_str,
        confidence_note=f"Deterministic compound calculation based on {base_year} baseline and stated {cagr_display:.1f}% CAGR."
    )

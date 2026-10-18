import pytest

from app.agent.tools.calculator import (
    calculate_projection,
    compute_cagr,
    compute_future_value,
    extract_numbers_from_query,
)


def test_compute_cagr_for_known_values():
    assert compute_cagr(100, 121, 2) == pytest.approx(0.1)


@pytest.mark.parametrize(
    ("start", "end", "periods"),
    [(0, 10, 2), (-1, 10, 2), (10, 0, 2), (10, -1, 2), (10, 20, 0)],
)
def test_compute_cagr_rejects_non_positive_inputs(start, end, periods):
    with pytest.raises(ValueError):
        compute_cagr(start, end, periods)


def test_compute_future_value_rejects_negative_periods():
    with pytest.raises(ValueError, match="non-negative"):
        compute_future_value(10, 0.1, -1)


def test_calculate_projection_returns_expected_value():
    result = calculate_projection(
        metric_name="Market size",
        base_value=4.21,
        base_year=2024,
        target_year=2030,
        cagr_decimal=0.112,
    )

    assert result.estimated_value == "7.96 USD Billion"
    assert "2024 -> 2030" in result.assumptions[1]


@pytest.mark.parametrize(
    "query",
    [
        "Project $4.21B at 11.2% by 2030",
        "Forecast 4.21 billion with 11.2% from 2024 to 2030",
    ],
)
def test_extract_numbers_from_query(query):
    values = extract_numbers_from_query(query)

    assert values["base_value_billion"] == pytest.approx(4.21)
    assert values["cagr_pct"] == pytest.approx(11.2)
    if "from" in query:
        assert values["periods"] == 6.0
    else:
        assert values["target_year"] == 2030.0


def test_calculate_projection_rejects_target_year_before_base_year():
    with pytest.raises(ValueError, match="must be greater than or equal to base year"):
        calculate_projection(
            metric_name="Market size",
            base_value=4.21,
            base_year=2030,
            target_year=2024,
            cagr_decimal=0.112,
        )


def test_extract_numbers_multi_year_formats():
    res1 = extract_numbers_from_query("Forecast growth between 2024 and 2030")
    assert res1["start_year"] == 2024.0
    assert res1["end_year"] == 2030.0
    assert res1["periods"] == 6.0

    res2 = extract_numbers_from_query("Estimate from 2025 to 2029 for $3.87B with 9.8%")
    assert res2["base_value_billion"] == pytest.approx(3.87)
    assert res2["cagr_pct"] == pytest.approx(9.8)
    assert res2["periods"] == 4.0


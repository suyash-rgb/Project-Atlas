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

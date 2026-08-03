"""
test_smoke.py
=============
Offline smoke tests for the GenAI Financial Earnings Report Analyst.

These run without network access or the heavy ML libraries (torch,
sentence-transformers, chromadb), so they execute in seconds on any machine.
They confirm the package lays out correctly and that the core pure-Python
logic behaves as expected before the heavier integration tests are run:

    * configuration paths resolve under the project root,
    * KPI value formatting,
    * the period-over-period comparison calculation (a 20% revenue growth),
    * the Bull/Bear signal generator (BULLISH on strong positives, NEUTRAL
      when inputs are missing).

Run with:  pytest tests/test_smoke.py     (or: python tests/test_smoke.py)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from genai_analyst.core import config


# --------------------------------------------------------------------------- #
# Package / configuration
# --------------------------------------------------------------------------- #
def test_paths_defined():
    """Core configuration paths resolve under the project root."""
    assert config.BASE_DIR is not None
    assert config.DB_PATH is not None


def test_is_llm_configured_returns_bool():
    """The LLM-configured helper returns a boolean, key present or not."""
    assert isinstance(config.is_llm_configured(), bool)


def test_kpi_concepts_present():
    """The five expected KPIs are declared in the config."""
    for kpi in ("Revenue", "NetIncome", "EPS", "GrossProfit", "OperatingIncome"):
        assert kpi in config.KPI_CONCEPTS


# --------------------------------------------------------------------------- #
# KPI value formatting
# --------------------------------------------------------------------------- #
def test_kpi_value_formatting():
    """Currency and per-share values format into human-readable strings."""
    from genai_analyst.analysis.kpi_extractor import format_kpi_value

    # Billions and millions get a $ and a B/M suffix.
    assert format_kpi_value(416_160_000_000, "USD") == "$416.16B"
    assert format_kpi_value(45_180_000, "USD") == "$45.18M"
    # Per-share values are plain 2-dp numbers, no $ suffix.
    assert format_kpi_value(6.13, "USD/shares") == "6.13"
    # Missing values degrade gracefully rather than raising.
    assert format_kpi_value(None, "USD") == "N/A"


def test_gross_margin_derivation():
    """Gross Margin is derived as Gross Profit / Revenue and formatted as %."""
    from genai_analyst.analysis.kpi_extractor import _add_gross_margin, format_kpi_value

    results = {
        "Revenue": {"current": 400.0, "previous": 200.0, "unit": "USD"},
        "GrossProfit": {"current": 180.0, "previous": 100.0, "unit": "USD",
                        "current_period": "2025-09-28", "previous_period": "2024-09-30"},
    }
    _add_gross_margin(results)
    gm = results["GrossMargin"]
    assert gm["current"] == 45.0          # 180 / 400 * 100
    assert gm["previous"] == 50.0          # 100 / 200 * 100
    assert format_kpi_value(gm["current"], gm["unit"]) == "45.00%"
    # Zero revenue must not divide-by-zero.
    zero = {"Revenue": {"current": 0}, "GrossProfit": {"current": 100}}
    _add_gross_margin(zero)
    assert zero["GrossMargin"]["current"] is None


def test_period_matching_by_duration():
    """10-Q compares quarter-vs-quarter, not quarter-vs-year-to-date."""
    from genai_analyst.analysis.kpi_extractor import _extract_period_values

    concept = {"units": {"USD": [
        {"val": 111, "start": "2026-01-01", "end": "2026-03-28", "form": "10-Q"},  # 3mo
        {"val": 254, "start": "2025-10-01", "end": "2026-03-28", "form": "10-Q"},  # 6mo YTD trap
        {"val": 95,  "start": "2025-01-01", "end": "2025-03-28", "form": "10-Q"},  # 3mo prior
    ]}}
    rows = _extract_period_values(concept, "10-Q")
    # The 6-month YTD figure must be excluded, leaving the two 3-month periods.
    kept = [r["value"] for r in rows]
    assert 254 not in kept, "6-month YTD should be filtered out for a 10-Q"
    assert rows[0]["value"] == 111 and rows[1]["value"] == 95


# --------------------------------------------------------------------------- #
# Period-over-period comparison calculation
# --------------------------------------------------------------------------- #
def test_comparison_percentage_change():
    """A 100 -> 120 change is reported as +20%, and divide-by-zero is safe."""
    from genai_analyst.analysis.comparison_engine import _pct_change

    assert _pct_change(120, 100) == 20.0        # +20% growth
    assert _pct_change(80, 100) == -20.0        # -20% decline
    assert _pct_change(100, 0) is None          # no divide-by-zero
    assert _pct_change(None, 100) is None        # missing current value


# --------------------------------------------------------------------------- #
# Bull/Bear signal generator
# --------------------------------------------------------------------------- #
def test_signal_bullish_on_strong_positives():
    """Strong revenue/margin growth + positive tone + upbeat guidance => BULLISH."""
    from genai_analyst.analysis.signal_generator import generate_signal

    strong = {
        "revenue_growth": 25.0,
        "gross_profit_growth": 20.0,
        "operating_income_growth": 22.0,
        "net_income_growth": 24.0,
    }
    result = generate_signal(strong, tone_score=0.9,
                             guidance_text="We expect strong growth and record demand.")
    assert result["classification"] == "BULLISH"
    assert 0.0 <= result["score"] <= 1.0


def test_signal_neutral_on_missing_data():
    """Empty inputs fall back to a middle score => NEUTRAL, not a crash."""
    from genai_analyst.analysis.signal_generator import generate_signal

    result = generate_signal({}, tone_score=0.5, guidance_text="")
    assert result["classification"] == "NEUTRAL"
    assert 0.0 <= result["score"] <= 1.0


if __name__ == "__main__":
    # Allow running directly without pytest.
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL  {fn.__name__}: {exc}")
    print(f"\n{passed}/{len(fns)} smoke tests passed")

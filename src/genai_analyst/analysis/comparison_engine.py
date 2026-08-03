"""
comparison_engine.py
====================
KPI Period Comparison (Pipeline Step 9).

Uses pandas to compute period-over-period percentage changes for each KPI
extracted from XBRL, producing a tidy comparison table the dashboard and
PDF report render. Includes a direction arrow and colour hint per metric.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

from genai_analyst.analysis.kpi_extractor import format_kpi_value


def _pct_change(current, previous):
    """Safe percentage change; returns None if not computable."""
    if current is None or previous is None or previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 2)


def build_comparison(kpis: Dict[str, dict]) -> pd.DataFrame:
    """Turn the raw KPI dict into a comparison DataFrame.

    Columns: KPI, Current, Previous, Change %, Direction, Trend.
    """
    rows = []
    for name, data in kpis.items():
        cur = data.get("current")
        prev = data.get("previous")
        unit = data.get("unit")
        change = _pct_change(cur, prev)

        if change is None:
            direction, trend = "—", "flat"
        elif change > 0:
            direction, trend = "▲", "up"
        elif change < 0:
            direction, trend = "▼", "down"
        else:
            direction, trend = "—", "flat"

        rows.append(
            {
                "KPI": name,
                "Current": format_kpi_value(cur, unit),
                "Previous": format_kpi_value(prev, unit),
                "Change %": f"{change:+.2f}%" if change is not None else "N/A",
                "Direction": direction,
                "Trend": trend,
                "_change_value": change,        # raw, for signal engine
                "_current_value": cur,
                "_previous_value": prev,
            }
        )
    return pd.DataFrame(rows)


def comparison_summary(df: pd.DataFrame) -> Dict:
    """Derive aggregate signals from the comparison table for the signal engine."""
    def _safe(name, col="_change_value"):
        sub = df.loc[df["KPI"] == name, col]
        return sub.iloc[0] if not sub.empty else None

    return {
        "revenue_growth": _safe("Revenue"),
        "net_income_growth": _safe("NetIncome"),
        "eps_growth": _safe("EPS"),
        "gross_profit_growth": _safe("GrossProfit"),
        "operating_income_growth": _safe("OperatingIncome"),
    }


if __name__ == "__main__":
    demo = {
        "Revenue": {"current": 1200, "previous": 1000, "unit": "USD"},
        "EPS": {"current": 5.1, "previous": 4.8, "unit": "USD/shares"},
    }
    table = build_comparison(demo)
    print(table.to_string(index=False))
    print(comparison_summary(table))

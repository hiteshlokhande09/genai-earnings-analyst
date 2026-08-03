"""
kpi_extractor.py
================
EDGAR XBRL Financial KPI Extraction (Pipeline Step 7).

Pulls structured financial figures DIRECTLY from the SEC EDGAR XBRL API.
Per the SRS, financial numbers are never AI-generated -- they always come
from this authoritative source to guarantee accuracy.

KPIs extracted: Revenue, Net Income, EPS, Gross Profit, Operating Income.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from genai_analyst.ingestion.edgar_client import _get
from genai_analyst.core import config


def _fetch_concept(cik10: str, concept: str) -> Optional[dict]:
    """Fetch a single us-gaap XBRL concept for a company, or None."""
    url = config.SEC_XBRL_CONCEPT_URL.format(cik10=cik10, concept=concept)
    return _get(url)


def _extract_period_values(concept_data: dict, form: str) -> List[dict]:
    """Flatten an XBRL concept response into a sorted list of period values.

    Each item: {value, end, fy, fp, form, unit}. Sorted newest-first by end date.
    """
    units = concept_data.get("units", {})
    rows: List[dict] = []
    for unit_name, entries in units.items():
        for e in entries:
            rows.append(
                {
                    "value": e.get("val"),
                    "end": e.get("end"),
                    "start": e.get("start"),
                    "fy": e.get("fy"),
                    "fp": e.get("fp"),
                    "form": e.get("form"),
                    "unit": unit_name,
                }
            )
    # Prefer rows matching the target form type.
    preferred = [r for r in rows if r["form"] == form]
    chosen = preferred if preferred else rows
    chosen = [r for r in chosen if r["value"] is not None and r["end"]]
    chosen.sort(key=lambda r: r["end"], reverse=True)
    return chosen


def extract_kpis(cik10: str, form: str = "10-K") -> Dict[str, dict]:
    """Extract all configured KPIs for a company."""
    results: Dict[str, dict] = {}

    for kpi_name, concept_tags in config.KPI_CONCEPTS.items():
        kpi_entry = {
            "current": None,
            "previous": None,
            "unit": None,
            "current_period": None,
            "previous_period": None,
        }
        for concept in concept_tags:
            data = _fetch_concept(cik10, concept)
            if not data:
                continue
            periods = _extract_period_values(data, form)
            if periods:
                kpi_entry["current"] = periods[0]["value"]
                kpi_entry["unit"] = periods[0]["unit"]
                kpi_entry["current_period"] = periods[0]["end"]
                if len(periods) > 1:
                    kpi_entry["previous"] = periods[1]["value"]
                    kpi_entry["previous_period"] = periods[1]["end"]
                break
        results[kpi_name] = kpi_entry

    return results


def format_kpi_value(value: Optional[float], unit: Optional[str]) -> str:
    """Human-friendly formatting for display (e.g. $1.23B, 5.67)."""
    if value is None:
        return "N/A"
    if unit and "USD/shares" in unit:
        return f"{value:,.2f}"
    if unit and unit.startswith("USD"):
        abs_v = abs(value)
        if abs_v >= 1e9:
            return f"${value / 1e9:,.2f}B"
        if abs_v >= 1e6:
            return f"${value / 1e6:,.2f}M"
        return f"${value:,.0f}"
    return f"{value:,.2f}"


if __name__ == "__main__":
    kpis = extract_kpis("0000320193", "10-K")
    for name, data in kpis.items():
        print(f"{name}: {format_kpi_value(data['current'], data['unit'])} "
              f"(prev {format_kpi_value(data['previous'], data['unit'])})")

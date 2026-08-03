"""
kpi_extractor.py
================
EDGAR XBRL Financial KPI Extraction (Pipeline Step 7).

Pulls structured financial figures DIRECTLY from the SEC EDGAR XBRL API.
Per the SRS, financial numbers are never AI-generated -- they always come
from this authoritative source to guarantee accuracy.

KPIs extracted: Revenue, Net Income, EPS, Gross Profit, Operating Income,
and Gross Margin (derived as Gross Profit / Revenue, per the SRS).

Each KPI returns the two most recent comparable period values so that the
comparison engine can compute period-over-period deltas.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from genai_analyst.ingestion.edgar_client import _get  # reuse the resilient HTTP helper
from genai_analyst.core import config
def _fetch_concept(cik10: str, concept: str) -> Optional[dict]:
    """Fetch a single us-gaap XBRL concept for a company, or None."""
    url = config.SEC_XBRL_CONCEPT_URL.format(cik10=cik10, concept=concept)
    return _get(url)


def _duration_days(row: dict) -> Optional[int]:
    """Number of days a period spans (end - start), or None for instant facts.

    EPS/Revenue/etc. are *duration* facts (they cover a period). Balance-sheet
    style facts are *instant* (no start). Duration lets us tell an annual
    figure (~365d) from a quarterly one (~90d).
    """
    from datetime import date

    start, end = row.get("start"), row.get("end")
    if not start or not end:
        return None
    try:
        y1, m1, d1 = map(int, start.split("-"))
        y2, m2, d2 = map(int, end.split("-"))
        return (date(y2, m2, d2) - date(y1, m1, d1)).days
    except (ValueError, AttributeError):
        return None


def _same_bucket(days: Optional[int], form: str) -> bool:
    """True if a period's duration matches the form's expected reporting span.

    10-K reports annual figures (~365 days); 10-Q reports quarterly (~90 days).
    XBRL for a 10-Q also contains 6-/9-month year-to-date figures, so filtering
    to the right bucket stops the engine comparing, say, a 3-month value against
    a 6-month one and reporting a nonsensical growth %.
    """
    if days is None:
        # Instant/undated facts (rare for these KPIs): keep, can't disambiguate.
        return True
    if form == "10-K":
        return 330 <= days <= 400          # ~1 year
    return 60 <= days <= 120               # ~1 quarter (10-Q)


def _extract_period_values(concept_data: dict, form: str) -> List[dict]:
    """Flatten an XBRL concept response into a sorted list of period values.

    Each item: {value, end, start, fy, fp, form, unit, days}. Filtered to the
    reporting duration that matches ``form`` (annual for 10-K, quarterly for
    10-Q) so period-over-period comparisons are like-for-like, then sorted
    newest-first by end date.
    """
    units = concept_data.get("units", {})
    rows: List[dict] = []
    for unit_name, entries in units.items():
        for e in entries:
            row = {
                "value": e.get("val"),
                "end": e.get("end"),
                "start": e.get("start"),
                "fy": e.get("fy"),
                "fp": e.get("fp"),
                "form": e.get("form"),
                "unit": unit_name,
            }
            row["days"] = _duration_days(row)
            rows.append(row)

    # Prefer rows reported on the requested form type, then fall back to any.
    preferred = [r for r in rows if r["form"] == form]
    chosen = preferred if preferred else rows
    chosen = [r for r in chosen if r["value"] is not None and r["end"]]

    # Keep only periods whose duration matches the form (annual vs quarterly).
    bucketed = [r for r in chosen if _same_bucket(r["days"], form)]
    # If bucketing removed everything (e.g. unusual tagging), fall back to all
    # so we degrade to the old behaviour rather than returning nothing.
    chosen = bucketed if bucketed else chosen

    chosen.sort(key=lambda r: r["end"], reverse=True)
    return chosen


def extract_kpis(cik10: str, form: str = "10-K") -> Dict[str, dict]:
    """Extract all configured KPIs for a company.

    Returns a dict keyed by KPI name, each value containing:
        {current, previous, unit, current_period, previous_period}
    Missing KPIs yield None values (graceful degradation, never a crash).
    """
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
            # De-duplicate by end date, keeping the first (latest fy/fp wins).
            seen = set()
            unique = []
            for p in periods:
                if p["end"] not in seen:
                    seen.add(p["end"])
                    unique.append(p)
            if unique:
                kpi_entry["current"] = unique[0]["value"]
                kpi_entry["unit"] = unique[0]["unit"]
                kpi_entry["current_period"] = unique[0]["end"]
                if len(unique) > 1:
                    kpi_entry["previous"] = unique[1]["value"]
                    kpi_entry["previous_period"] = unique[1]["end"]
                break  # stop at the first concept tag that returned data
        results[kpi_name] = kpi_entry

    _add_gross_margin(results)
    return results


def _add_gross_margin(results: Dict[str, dict]) -> None:
    """Derive Gross Margin (%) from Gross Profit / Revenue and add it in place.

    Per the SRS the reported KPI is Gross Margin. XBRL does not tag margin as a
    percentage, so it is computed from two XBRL-sourced figures — Gross Profit
    and Revenue — for the current and previous periods. The underlying numbers
    still come from EDGAR (the golden rule holds); only the ratio is derived.
    Marked with unit "PERCENT" so the formatter renders it as e.g. "46.21%".
    """
    gp = results.get("GrossProfit", {})
    rev = results.get("Revenue", {})

    def _margin(profit, revenue):
        if profit is None or revenue in (None, 0):
            return None
        return round(profit / revenue * 100, 2)

    results["GrossMargin"] = {
        "current": _margin(gp.get("current"), rev.get("current")),
        "previous": _margin(gp.get("previous"), rev.get("previous")),
        "unit": "PERCENT",
        "current_period": gp.get("current_period"),
        "previous_period": gp.get("previous_period"),
    }


def format_kpi_value(value: Optional[float], unit: Optional[str]) -> str:
    """Human-friendly formatting for display (e.g. $1.23B, 5.67)."""
    if value is None:
        return "N/A"
    if unit == "PERCENT":
        return f"{value:,.2f}%"
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
    # Manual smoke test (requires internet). Apple's CIK is 0000320193.
    kpis = extract_kpis("0000320193", "10-K")
    for name, data in kpis.items():
        print(f"{name}: {format_kpi_value(data['current'], data['unit'])} "
              f"(prev {format_kpi_value(data['previous'], data['unit'])})")

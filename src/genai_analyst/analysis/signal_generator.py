"""
signal_generator.py
===================
Bull/Bear Signal Generation (Pipeline Step 8 - signal engine).

Aggregates four weighted inputs into a single 0-1 score and a clear
BULLISH / BEARISH / NEUTRAL classification, with the supporting evidence
that drove the decision (for transparency in the report):

    1. Revenue growth     (period-over-period %)
    2. Margin / profit trend (gross + operating + net income %)
    3. Management tone score (FinBERT, 0-1)
    4. Guidance signal     (positive / neutral / negative outlook)

This is informational only -- NOT a trading recommendation (per SRS).
"""

from __future__ import annotations

from typing import Dict, List, Optional

# Weights for each component (sum = 1.0).
WEIGHTS = {
    "revenue": 0.30,
    "margin": 0.25,
    "tone": 0.25,
    "guidance": 0.20,
}


def _growth_to_score(pct: Optional[float], cap: float = 25.0) -> float:
    """Map a percentage change to a 0-1 score (0.5 = flat)."""
    if pct is None:
        return 0.5
    clamped = max(min(pct, cap), -cap)
    return round(0.5 + (clamped / cap) * 0.5, 4)


def _guidance_to_score(guidance_text: str) -> float:
    """Crude lexical scoring of guidance outlook -> 0-1."""
    if not guidance_text:
        return 0.5
    text = guidance_text.lower()
    positive = ["growth", "increase", "raise", "strong", "optimis", "expand",
                "improve", "higher", "record", "confident"]
    negative = ["decline", "decrease", "lower", "weak", "headwind", "uncertain",
                "challenging", "reduce", "soft", "pressure", "no formal guidance"]
    p = sum(text.count(w) for w in positive)
    n = sum(text.count(w) for w in negative)
    if p == n:
        return 0.5
    return round(0.5 + (p - n) / (p + n) * 0.5, 4)


def generate_signal(
    comparison_summary: Dict,
    tone_score: float,
    guidance_text: str,
) -> Dict:
    """Compute the aggregate Bull/Bear signal.

    Returns:
        {score, classification, components, evidence}
    """
    revenue_score = _growth_to_score(comparison_summary.get("revenue_growth"))

    # Margin/profitability blends gross, operating, and net income growth.
    margin_inputs = [
        comparison_summary.get("gross_profit_growth"),
        comparison_summary.get("operating_income_growth"),
        comparison_summary.get("net_income_growth"),
    ]
    margin_inputs = [m for m in margin_inputs if m is not None]
    if margin_inputs:
        margin_score = sum(_growth_to_score(m) for m in margin_inputs) / len(
            margin_inputs
        )
        margin_score = round(margin_score, 4)
    else:
        margin_score = 0.5

    tone_component = round(float(tone_score), 4)
    guidance_score = _guidance_to_score(guidance_text)

    score = (
        WEIGHTS["revenue"] * revenue_score
        + WEIGHTS["margin"] * margin_score
        + WEIGHTS["tone"] * tone_component
        + WEIGHTS["guidance"] * guidance_score
    )
    score = round(score, 4)

    if score >= 0.60:
        classification = "BULLISH"
    elif score <= 0.40:
        classification = "BEARISH"
    else:
        classification = "NEUTRAL"

    evidence: List[str] = []
    rg = comparison_summary.get("revenue_growth")
    if rg is not None:
        evidence.append(f"Revenue growth: {rg:+.2f}%")
    ni = comparison_summary.get("net_income_growth")
    if ni is not None:
        evidence.append(f"Net income growth: {ni:+.2f}%")
    evidence.append(f"Management tone score: {tone_component:.2f}")
    evidence.append(f"Guidance outlook score: {guidance_score:.2f}")

    return {
        "score": score,
        "classification": classification,
        "components": {
            "revenue": revenue_score,
            "margin": margin_score,
            "tone": tone_component,
            "guidance": guidance_score,
        },
        "evidence": evidence,
    }


if __name__ == "__main__":
    demo_summary = {
        "revenue_growth": 12.0,
        "net_income_growth": 8.0,
        "gross_profit_growth": 5.0,
        "operating_income_growth": 6.0,
    }
    print(generate_signal(demo_summary, tone_score=0.7,
                          guidance_text="We expect strong growth and record revenue."))

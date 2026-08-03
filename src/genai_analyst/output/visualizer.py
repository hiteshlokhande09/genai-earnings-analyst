"""
visualizer.py
=============
Data Visualisation (Pipeline Step 10).

Generates matplotlib PNG charts that are embedded both in the Streamlit
dashboard and the ReportLab PDF report:

    * KPI bar chart (Current vs Previous period)
    * Management tone gauge / breakdown
    * Bull-Bear signal component breakdown

Uses a non-interactive Agg backend so it works headless on a server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import matplotlib

matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from genai_analyst.core import config  # noqa: E402


def _outfile(name: str) -> Path:
    return config.CHARTS_DIR / name


def kpi_bar_chart(df: pd.DataFrame, ticker: str) -> Optional[str]:
    """Bar chart of current vs previous KPI values (normalised per KPI)."""
    plot_rows = df[df["_current_value"].notna() & df["_previous_value"].notna()]
    if plot_rows.empty:
        return None

    labels = plot_rows["KPI"].tolist()
    current = plot_rows["_current_value"].astype(float).tolist()
    previous = plot_rows["_previous_value"].astype(float).tolist()

    # Normalise each KPI to its previous value so disparate scales are comparable.
    norm_cur, norm_prev = [], []
    for c, p in zip(current, previous):
        base = abs(p) if p else 1.0
        norm_cur.append(c / base)
        norm_prev.append(p / base)

    x = range(len(labels))
    width = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([i - width / 2 for i in x], norm_prev, width, label="Previous",
           color="#9CA3AF")
    ax.bar([i + width / 2 for i in x], norm_cur, width, label="Current",
           color="#2563EB")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Value (normalised to previous period)")
    ax.set_title(f"{ticker} — KPI: Current vs Previous Period")
    ax.legend()
    fig.tight_layout()
    path = _outfile(f"{ticker}_kpi.png")
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return str(path)


def tone_chart(tone: Dict, ticker: str) -> Optional[str]:
    """Pie/bar breakdown of positive / negative / neutral chunk counts."""
    pos, neg, neu = tone.get("positive", 0), tone.get("negative", 0), tone.get("neutral", 0)
    if pos + neg + neu == 0:
        return None
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    ax.bar(["Positive", "Neutral", "Negative"], [pos, neu, neg],
           color=["#16A34A", "#9CA3AF", "#DC2626"])
    ax.set_ylabel("Number of text chunks")
    ax.set_title(f"{ticker} — Management Tone Breakdown "
                 f"(score {tone.get('tone_score', 0):.2f})")
    fig.tight_layout()
    path = _outfile(f"{ticker}_tone.png")
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return str(path)


def signal_chart(signal: Dict, ticker: str) -> Optional[str]:
    """Horizontal bar of the four signal components."""
    comps = signal.get("components", {})
    if not comps:
        return None
    names = list(comps.keys())
    values = [comps[n] for n in names]
    colors = ["#16A34A" if v >= 0.5 else "#DC2626" for v in values]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.barh(names, values, color=colors)
    ax.set_xlim(0, 1)
    ax.axvline(0.5, color="#374151", linestyle="--", linewidth=1)
    ax.set_title(f"{ticker} — Bull/Bear Signal Components "
                 f"({signal.get('classification', 'N/A')} {signal.get('score', 0):.2f})")
    fig.tight_layout()
    path = _outfile(f"{ticker}_signal.png")
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return str(path)


def generate_all_charts(df, tone, signal, ticker) -> Dict[str, Optional[str]]:
    """Generate every chart and return a dict of file paths."""
    return {
        "kpi": kpi_bar_chart(df, ticker),
        "tone": tone_chart(tone, ticker),
        "signal": signal_chart(signal, ticker),
    }


if __name__ == "__main__":
    print("Charts directory:", config.CHARTS_DIR)

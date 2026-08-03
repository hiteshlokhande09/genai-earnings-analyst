"""
pdf_generator.py
================
Investor-Grade PDF Report Generation (Pipeline Step 11).

Uses ReportLab to assemble a multi-section analyst report:
    1. Cover Page
    2. Executive Summary
    3. KPI Comparison Table
    4. Revenue / KPI Trend Chart
    5. Management Tone Analysis
    6. Forward Guidance
    7. Top 5 Risk Factors
    8. Bull/Bear Signal
    9. Disclaimer

Returns the path to the generated PDF.
"""
#This is all it has 


from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from genai_analyst.core import config
# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #
def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("CoverTitle", parent=s["Title"], fontSize=26,
                         leading=32, alignment=TA_CENTER, textColor=colors.HexColor("#1E3A8A")))
    s.add(ParagraphStyle("CoverSub", parent=s["Normal"], fontSize=14,
                         alignment=TA_CENTER, textColor=colors.HexColor("#374151")))
    s.add(ParagraphStyle("SectionHead", parent=s["Heading2"], fontSize=15,
                         textColor=colors.HexColor("#1E3A8A"), spaceBefore=14, spaceAfter=8))
    s.add(ParagraphStyle("Body", parent=s["Normal"], fontSize=10.5, leading=15,
                         alignment=TA_LEFT))
    s.add(ParagraphStyle("Disclaimer", parent=s["Normal"], fontSize=8,
                         textColor=colors.HexColor("#6B7280"), leading=11))
    return s


SEVERITY_COLOR = {
    "High": colors.HexColor("#DC2626"),
    "Medium": colors.HexColor("#D97706"),
    "Low": colors.HexColor("#16A34A"),
}
SIGNAL_COLOR = {
    "BULLISH": colors.HexColor("#16A34A"),
    "BEARISH": colors.HexColor("#DC2626"),
    "NEUTRAL": colors.HexColor("#6B7280"),
}


def _image_if(path: Optional[str], width: float):
    if path and os.path.exists(path):
        img = Image(path)
        ratio = img.imageHeight / float(img.imageWidth)
        img.drawWidth = width
        img.drawHeight = width * ratio
        return img
    return None


# --------------------------------------------------------------------------- #
# Main builder
# --------------------------------------------------------------------------- #
def generate_report(
    *,
    filing: Dict,
    kpi_table: pd.DataFrame,
    tone: Dict,
    summary: str,
    guidance: str,
    risks: List[dict],
    signal: Dict,
    charts: Dict[str, Optional[str]],
) -> str:
    """Build the PDF and return its file path."""
    s = _styles()
    ticker = filing.get("ticker", "N/A")
    out_path = config.REPORTS_DIR / f"{ticker}_{filing.get('form', 'report')}_analysis.pdf"

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        leftMargin=0.8 * inch, rightMargin=0.8 * inch,
    )
    flow = []

    # ---- 1. Cover page -------------------------------------------------- #
    flow.append(Spacer(1, 1.6 * inch))
    flow.append(Paragraph("Financial Earnings Report Analysis", s["CoverTitle"]))
    flow.append(Spacer(1, 0.3 * inch))
    flow.append(Paragraph(f"{filing.get('company', ticker)} ({ticker})", s["CoverSub"]))
    flow.append(Spacer(1, 0.1 * inch))
    flow.append(Paragraph(
        f"{filing.get('form', '')} &nbsp;|&nbsp; Filed {filing.get('filing_date', 'N/A')}",
        s["CoverSub"]))
    flow.append(Spacer(1, 0.4 * inch))
    sig_class = signal.get("classification", "NEUTRAL")
    flow.append(Paragraph(
        f"<b>Signal: <font color='{SIGNAL_COLOR.get(sig_class, colors.black)}'>"
        f"{sig_class}</font></b> &nbsp; (score {signal.get('score', 0):.2f})",
        s["CoverSub"]))
    flow.append(Spacer(1, 1.5 * inch))
    flow.append(Paragraph(
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} by "
        "GenAI Financial Earnings Report Analyst", s["Disclaimer"]))
    flow.append(PageBreak())

    # ---- 2. Executive summary ------------------------------------------ #
    flow.append(Paragraph("1. Executive Summary", s["SectionHead"]))
    flow.append(Paragraph(summary.replace("\n", "<br/>"), s["Body"]))
    flow.append(Spacer(1, 0.2 * inch))

    # ---- 3. KPI comparison table --------------------------------------- #
    flow.append(Paragraph("2. KPI Comparison", s["SectionHead"]))
    flow.append(_kpi_table_flowable(kpi_table, s))
    flow.append(Spacer(1, 0.2 * inch))

    # ---- 4. KPI chart -------------------------------------------------- #
    kpi_img = _image_if(charts.get("kpi"), 6.2 * inch)
    if kpi_img:
        flow.append(Paragraph("3. KPI Trend Chart", s["SectionHead"]))
        flow.append(kpi_img)
        flow.append(Spacer(1, 0.2 * inch))

    # ---- 5. Management tone -------------------------------------------- #
    flow.append(Paragraph("4. Management Tone Analysis", s["SectionHead"]))
    flow.append(Paragraph(
        f"Overall tone: <b>{tone.get('label', 'N/A')}</b> "
        f"(score {tone.get('tone_score', 0):.2f}). "
        f"Positive chunks: {tone.get('positive', 0)}, "
        f"Neutral: {tone.get('neutral', 0)}, "
        f"Negative: {tone.get('negative', 0)} "
        f"(of {tone.get('total', 0)} analysed).", s["Body"]))
    tone_img = _image_if(charts.get("tone"), 4.5 * inch)
    if tone_img:
        flow.append(Spacer(1, 0.1 * inch))
        flow.append(tone_img)
    flow.append(Spacer(1, 0.2 * inch))

    # ---- 6. Forward guidance ------------------------------------------- #
    flow.append(Paragraph("5. Forward Guidance", s["SectionHead"]))
    flow.append(Paragraph(guidance.replace("\n", "<br/>"), s["Body"]))
    flow.append(Spacer(1, 0.2 * inch))

    # ---- 7. Risk factors ----------------------------------------------- #
    flow.append(Paragraph("6. Top Risk Factors", s["SectionHead"]))
    flow.append(_risk_table_flowable(risks, s))
    flow.append(Spacer(1, 0.2 * inch))

    # ---- 8. Bull/Bear signal ------------------------------------------- #
    flow.append(Paragraph("7. Bull / Bear Signal", s["SectionHead"]))
    flow.append(Paragraph(
        f"Aggregate signal: <b><font color='{SIGNAL_COLOR.get(sig_class, colors.black)}'>"
        f"{sig_class}</font></b> (score {signal.get('score', 0):.2f}/1.00).", s["Body"]))
    for ev in signal.get("evidence", []):
        flow.append(Paragraph(f"&bull; {ev}", s["Body"]))
    sig_img = _image_if(charts.get("signal"), 5.5 * inch)
    if sig_img:
        flow.append(Spacer(1, 0.1 * inch))
        flow.append(sig_img)
    flow.append(Spacer(1, 0.3 * inch))

    # ---- 9. Disclaimer ------------------------------------------------- #
    flow.append(Paragraph("Disclaimer", s["SectionHead"]))
    flow.append(Paragraph(config.DISCLAIMER, s["Disclaimer"]))

    doc.build(flow)
    return str(out_path)


def _kpi_table_flowable(df: pd.DataFrame, s):
    cols = ["KPI", "Current", "Previous", "Change %", "Direction"]
    data = [cols]
    for _, row in df.iterrows():
        data.append([row.get(c, "") for c in cols])
    tbl = Table(data, hAlign="LEFT", colWidths=[1.4 * inch, 1.3 * inch,
                                                1.3 * inch, 1.1 * inch, 0.8 * inch])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F3F4F6")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        trend = row.get("Trend")
        if trend == "up":
            style.append(("TEXTCOLOR", (3, i), (4, i), colors.HexColor("#16A34A")))
        elif trend == "down":
            style.append(("TEXTCOLOR", (3, i), (4, i), colors.HexColor("#DC2626")))
    tbl.setStyle(TableStyle(style))
    return tbl


def _risk_table_flowable(risks: List[dict], s):
    if not risks:
        return Paragraph("No structured risk factors were extracted.", s["Body"])
    data = [["#", "Risk Factor", "Category", "Severity"]]
    for i, r in enumerate(risks[:5], start=1):
        data.append([
            str(i),
            Paragraph(str(r.get("risk", "")), s["Body"]),
            str(r.get("category", "")),
            str(r.get("severity", "")),
        ])
    tbl = Table(data, hAlign="LEFT",
                colWidths=[0.4 * inch, 3.4 * inch, 1.2 * inch, 0.9 * inch])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, r in enumerate(risks[:5], start=1):
        sev = str(r.get("severity", "")).capitalize()
        if sev in SEVERITY_COLOR:
            style.append(("TEXTCOLOR", (3, i), (3, i), SEVERITY_COLOR[sev]))
    tbl.setStyle(TableStyle(style))
    return tbl


if __name__ == "__main__":
    print("PDF reports will be written to:", config.REPORTS_DIR)

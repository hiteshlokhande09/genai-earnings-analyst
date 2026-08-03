"""
dashboard.py
============
Streamlit Dashboard (Pipeline Step 12) — analysis view.

Launched from the root app.py router. Pure-Python UI (no external JS
framework). Lets the user:
    * search for a company by name (or enter a ticker) and pick 10-Q / 10-K,
    * trigger the full analysis pipeline with a live progress spinner,
    * view KPI metric cards with period-over-period change arrows,
    * view the colour-coded KPI comparison table,
    * view management tone score and Bull/Bear signal,
    * view embedded charts,
    * download the generated PDF analyst report,
    * browse historical analyses cached in SQLite.

State handling
--------------
Streamlit re-runs this whole script on *every* widget interaction — including
clicking ``st.download_button``. The completed analysis is therefore stored in
``st.session_state["result"]`` and rendered from there on each run, rather than
being held in a local variable inside the ``if run:`` branch. Without this, the
download click would re-run the script, find ``run`` False, and fall through to
the empty state — which looks like the app "going back to the main screen".

Pipeline logic is untouched; this module is the presentation layer.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from genai_analyst.core import config
from genai_analyst.core import database
from genai_analyst.ingestion import edgar_client
from genai_analyst.analysis.kpi_extractor import format_kpi_value

# NOTE: st.set_page_config is called once in the root app.py (the launcher).

SIGNAL_COLORS = {"BULLISH": "#15803D", "BEARISH": "#B91C1C", "NEUTRAL": "#64748B"}
UP, DOWN, FLAT = "#15803D", "#B91C1C", "#64748B"

# Session-state key holding the most recent successful analysis.
RESULT_KEY = "result"


# --------------------------------------------------------------------------- #
# Theme / CSS
# --------------------------------------------------------------------------- #
def inject_css():
    """Scoped CSS for a clean corporate-finance aesthetic."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
        .stApp { background: #F6F8FB; }
        .block-container { padding-top: 1.4rem; max-width: 1250px; }

        /* ---- Top header bar ---- */
        .app-header {
            background: linear-gradient(135deg, #0B3D6B 0%, #15558C 100%);
            border-radius: 14px; padding: 22px 28px; margin-bottom: 22px;
            box-shadow: 0 6px 18px rgba(11,61,107,0.18);
        }
        .app-header h1 {
            color: #FFFFFF; font-size: 1.7rem; font-weight: 700;
            margin: 0; letter-spacing: -0.3px;
        }
        .app-header p { color: #C7DCF0; font-size: 0.93rem; margin: 6px 0 0 0; }
        .app-header .pill {
            display: inline-block; background: rgba(255,255,255,0.14);
            color: #EAF3FB; font-size: 0.72rem; font-weight: 600;
            padding: 3px 10px; border-radius: 20px; margin-right: 6px; margin-top: 10px;
        }

        /* ---- Section titles ---- */
        .section-title {
            font-size: 1.15rem; font-weight: 700; color: #0B3D6B;
            margin: 6px 0 10px 0; padding-left: 11px; border-left: 4px solid #1F6FEB;
        }

        /* ---- Metric cards ---- */
        [data-testid="stMetric"] {
            background: #FFFFFF; border: 1px solid #E3E8EF; border-radius: 12px;
            padding: 16px 18px; box-shadow: 0 1px 3px rgba(16,24,40,0.04);
        }
        [data-testid="stMetricLabel"] { color: #5B6B7C; font-weight: 600; }
        /* Prevent KPI values like $254.94B from truncating to "$254....". The
           inner children are targeted too, and text-overflow/max-width are
           cleared, because Streamlit nests the value in extra divs. */
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] > div,
        [data-testid="stMetricValue"] * {
            color: #1A2B3C; font-weight: 700;
            white-space: nowrap !important; overflow: visible !important;
            text-overflow: clip !important; max-width: none !important;
        }
        [data-testid="stMetricValue"] { font-size: clamp(16px, 1.5vw, 24px) !important; }

        /* ---- Generic card ---- */
        .fin-card {
            background: #FFFFFF; border: 1px solid #E3E8EF; border-radius: 12px;
            padding: 20px 22px; box-shadow: 0 1px 3px rgba(16,24,40,0.04); height: 100%;
        }
        .fin-card .card-label {
            font-size: 0.78rem; font-weight: 600; color: #5B6B7C;
            text-transform: uppercase; letter-spacing: 0.5px;
        }
        .fin-card .card-value { font-size: 1.9rem; font-weight: 700; margin: 4px 0; }
        .fin-card .card-sub { font-size: 0.85rem; color: #5B6B7C; }
        .fin-card .card-meta { font-size: 0.8rem; color: #5B6B7C; margin-top: 8px; }

        /* ---- Buttons ---- */
        .stButton > button, .stDownloadButton > button {
            background: #0B3D6B; color: #FFFFFF; border: none; border-radius: 9px;
            font-weight: 600; padding: 0.55rem 1rem; transition: background .15s ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            background: #15558C; color: #FFFFFF;
        }

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {
            background: #FFFFFF; border-right: 1px solid #E3E8EF;
        }
        .sb-brand { font-size: 1.15rem; font-weight: 700; color: #0B3D6B; margin-bottom: 2px; }
        .sb-sub { font-size: 0.8rem; color: #5B6B7C; margin-bottom: 8px; }
        .hist-item {
            background: #F6F8FB; border: 1px solid #E9EDF3; border-radius: 9px;
            padding: 8px 11px; margin-bottom: 7px;
        }
        .hist-item .t { font-weight: 700; color: #1A2B3C; font-size: 0.9rem; }
        .hist-item .d { font-size: 0.74rem; color: #5B6B7C; }

        /* ---- Dataframe rounding ---- */
        [data-testid="stDataFrame"] { border: 1px solid #E3E8EF; border-radius: 10px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section(title: str):
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)


def render_header():
    st.markdown(
        """
        <div class="app-header">
            <h1>GenAI Financial Earnings Report Analyst</h1>
            <p>Investor-grade analysis of SEC 10-K / 10-Q filings — exact figures from XBRL,
            narrative from AI.</p>
            <span class="pill">SEC EDGAR</span>
            <span class="pill">RAG + ChromaDB</span>
            <span class="pill">FinBERT</span>
            <span class="pill">Llama 3</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _company_options():
    """Build the searchable company list once and cache it for the session.

    Labels are company-name first with the ticker appended, e.g.
    "Netflix Inc  ·  NFLX". This lets you search **either way**:
      * typing a name ("netflix") prefix-matches at the start of the label, so
        the match surfaces near the top of the filtered list;
      * typing a ticker ("NFLX") still substring-matches the appended ticker.

    The list is sorted alphabetically by name, matching how a name-typer scans
    it. (Streamlit's selectbox keeps list order when filtering and can't
    re-rank, so front-loading the name is the most reliable arrangement for
    name-based search.)
    """
    companies = edgar_client.list_companies()
    labels, label_to_ticker = [], {}
    for c in sorted(companies, key=lambda x: x["title"].lower()):
        label = f"{c['title']}  ·  {c['ticker']}"
        labels.append(label)
        label_to_ticker[label] = c["ticker"]
    return labels, label_to_ticker


@st.cache_data(show_spinner=False)
def _read_pdf_bytes(path: str, mtime: float) -> bytes | None:
    """Read the generated PDF once and cache it.

    ``mtime`` is part of the cache key so a regenerated report (same path, new
    contents) is picked up automatically. Returns None if the file has since
    been removed.
    """
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


# --------------------------------------------------------------------------- #
# Sidebar — inputs & history
# --------------------------------------------------------------------------- #
def sidebar():
    if st.sidebar.button("← Back to home", use_container_width=True):
        st.session_state["view"] = "landing"
        st.rerun()
    st.sidebar.markdown("<div class='sb-brand'>📊 Earnings Analyst</div>",
                        unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sb-sub'>GenAI-powered SEC filing analysis</div>",
                        unsafe_allow_html=True)
    st.sidebar.divider()

    labels, label_to_ticker = _company_options()
    if labels:
        default_idx = next(
            (i for i, lbl in enumerate(labels) if lbl.endswith("· AAPL")
             or lbl.endswith("  AAPL") or "· AAPL" in lbl), 0
        )
        choice = st.sidebar.selectbox(
            "Company", labels, index=default_idx,
            help="Type a company name (e.g. Netflix) or a ticker (e.g. NFLX).",
        )
        ticker = label_to_ticker.get(choice, "").upper()
    else:
        ticker = st.sidebar.text_input(
            "Stock ticker", value="AAPL",
            help="Company list unavailable; enter the ticker symbol directly.",
        ).strip().upper()

    form_type = st.sidebar.selectbox("Filing type", ["10-K", "10-Q"])
    force = st.sidebar.checkbox("Force re-analysis (ignore cache)", value=False)
    run = st.sidebar.button("🚀 Run analysis", use_container_width=True)

    # Only offer "clear" once there is something on screen to clear.
    if st.session_state.get(RESULT_KEY):
        if st.sidebar.button("Clear results", use_container_width=True):
            st.session_state.pop(RESULT_KEY, None)
            st.rerun()

    st.sidebar.divider()
    st.sidebar.markdown("<div class='sb-brand' style='font-size:0.95rem;'>History</div>",
                        unsafe_allow_html=True)
    history = database.get_history(limit=15)
    if history:
        for h in history:
            cls = h.get("signal_class", "NEUTRAL") or "NEUTRAL"
            color = SIGNAL_COLORS.get(cls, FLAT)
            st.sidebar.markdown(
                f"<div class='hist-item'>"
                f"<span class='t'>{h['ticker']} {h['form']}</span> · "
                f"<span style='color:{color};font-weight:700'>{cls}</span>"
                f"<div class='d'>{h.get('filing_date', '')}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.sidebar.caption("No analyses yet.")
    st.sidebar.caption(f"Records stored: {database.count_records()}")

    if not config.LLAMA3_API_KEY:
        st.sidebar.warning("LLAMA3_API_KEY not set — summary/risks/guidance "
                           "will be blank. Add it to your .env file.")
    return ticker, form_type, force, run


# --------------------------------------------------------------------------- #
# Result rendering
# --------------------------------------------------------------------------- #
def render_kpi_cards(kpis: dict):
    section("Key Performance Indicators")
    cols = st.columns(len(kpis) or 1)
    for col, (name, data) in zip(cols, kpis.items()):
        cur = format_kpi_value(data.get("current"), data.get("unit"))
        cur_v, prev_v = data.get("current"), data.get("previous")
        delta = None
        if cur_v is not None and prev_v not in (None, 0):
            delta = f"{(cur_v - prev_v) / abs(prev_v) * 100:+.1f}%"
        col.metric(label=name, value=cur, delta=delta)


def render_comparison_table(df: pd.DataFrame):
    section("KPI Comparison — Period over Period")
    show = df[["KPI", "Current", "Previous", "Change %", "Direction"]].copy()

    def _color(row):
        trend = df.loc[df["KPI"] == row["KPI"], "Trend"].iloc[0]
        color = {"up": UP, "down": DOWN}.get(trend, FLAT)
        return [f"color: {color}; font-weight: 600" if c in ("Change %", "Direction")
                else "" for c in show.columns]

    st.dataframe(show.style.apply(_color, axis=1), use_container_width=True,
                 hide_index=True)


def render_signal_and_tone(signal: dict, tone: dict):
    c1, c2 = st.columns(2)
    cls = signal.get("classification", "NEUTRAL")
    color = SIGNAL_COLORS.get(cls, FLAT)

    evidence = "".join(
        f"<div class='card-meta'>• {ev}</div>" for ev in signal.get("evidence", [])
    )
    c1.markdown(
        f"<div class='fin-card'>"
        f"<div class='card-label'>Bull / Bear Signal</div>"
        f"<div class='card-value' style='color:{color}'>{cls}</div>"
        f"<div class='card-sub'>Score: <b>{signal.get('score', 0):.2f}</b> / 1.00</div>"
        f"{evidence}</div>",
        unsafe_allow_html=True,
    )

    tone_label = tone.get("label", "N/A")
    c2.markdown(
        f"<div class='fin-card'>"
        f"<div class='card-label'>Management Tone</div>"
        f"<div class='card-value' style='color:#0B3D6B'>{tone_label}</div>"
        f"<div class='card-sub'>Tone score: <b>{tone.get('tone_score', 0):.2f}</b> / 1.00</div>"
        f"<div class='card-meta'>Positive: {tone.get('positive', 0)} · "
        f"Neutral: {tone.get('neutral', 0)} · "
        f"Negative: {tone.get('negative', 0)}</div></div>",
        unsafe_allow_html=True,
    )


def render_charts(charts: dict):
    imgs = [(k, v) for k, v in charts.items() if v and os.path.exists(v)]
    if not imgs:
        return
    section("Visualisations")
    cols = st.columns(len(imgs))
    for col, (name, path) in zip(cols, imgs):
        col.image(path, caption=name.upper(), use_container_width=True)


def render_results(result: dict):
    filing = result["filing"]
    st.success(
        f"Analysis complete for **{filing['company']} ({filing['ticker']})** — "
        f"{filing['form']} filed {filing['filing_date']}"
        + ("  ·  (loaded from cache)" if result.get("from_cache") else "")
    )

    render_kpi_cards(result["kpis"])
    st.write("")
    render_comparison_table(result["kpi_table"])
    st.write("")
    render_signal_and_tone(result["signal"], result["tone"])
    st.write("")

    section("Executive Summary")
    st.write(result["summary"])

    section("Forward Guidance")
    st.write(result["guidance"])

    section("Top Risk Factors")
    if result["risks"]:
        st.dataframe(pd.DataFrame(result["risks"]), use_container_width=True,
                     hide_index=True)
    elif result.get("from_cache"):
        # A saved analysis from before risks were persisted. Nothing is wrong
        # with the LLM — the data simply wasn't stored on that row.
        st.caption("Risk factors weren't stored for this saved analysis. Tick "
                   "**Force re-analysis (ignore cache)** in the sidebar and run "
                   "again to regenerate them, or see the saved PDF report below.")
    else:
        st.caption("No structured risk factors extracted (LLM not configured?).")

    render_charts(result["charts"])
    st.write("")

    pdf_path = result.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        section("Report")
        pdf_bytes = _read_pdf_bytes(pdf_path, os.path.getmtime(pdf_path))
        if pdf_bytes:
            # A stable key tied to this filing keeps the widget identity fixed
            # across re-runs, so downloading doesn't disturb the rendered page.
            st.download_button(
                "⬇️  Download PDF analyst report",
                data=pdf_bytes,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                use_container_width=True,
                key=f"dl_{filing.get('ticker', '')}_{filing.get('form', '')}"
                    f"_{filing.get('accession', filing.get('filing_date', ''))}",
            )
        else:
            st.caption("The generated report file is no longer available on disk. "
                       "Re-run the analysis to regenerate it.")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    inject_css()
    ticker, form_type, force, run = sidebar()
    render_header()

    if run:
        if not ticker:
            st.error("Please select a company or enter a ticker symbol.")
            return
        from genai_analyst.core import pipeline  # deferred: keeps page load fast
        progress_bar = st.progress(0.0, text="Starting…")

        def _progress(label, frac):
            progress_bar.progress(min(frac, 1.0), text=label)

        with st.spinner("Running analysis pipeline…"):
            result = pipeline.run_analysis(
                ticker, form_type, force=force, progress=_progress
            )

        # Safety net: a stale / legacy cached row can come back without the
        # full result shape (missing "filing"). Instead of crashing, re-run a
        # fresh analysis automatically, ignoring the cache, so the user still
        # gets a complete result.
        if "error" not in result and "filing" not in result:
            with st.spinner("Saved result was incomplete — re-running a fresh "
                            "analysis (ignoring cache)…"):
                result = pipeline.run_analysis(
                    ticker, form_type, force=True, progress=_progress
                )

        progress_bar.empty()

        if "error" in result:
            st.session_state.pop(RESULT_KEY, None)
            st.error(result["error"])
        elif "filing" not in result:
            # Final fallback if even the fresh run came back malformed.
            st.session_state.pop(RESULT_KEY, None)
            st.error("Couldn't load this analysis from the cache. Please tick "
                     "**Force re-analysis (ignore cache)** in the sidebar and "
                     "run again.")
        else:
            # Persist so the results survive the re-run triggered by any later
            # widget interaction (notably the PDF download button).
            st.session_state[RESULT_KEY] = result

    # Render whatever analysis is currently held in session state. This runs on
    # every script execution, so clicking Download re-renders the same results
    # instead of falling through to the empty state.
    stored = st.session_state.get(RESULT_KEY)
    if stored:
        render_results(stored)
    elif not run:
        st.info("Select a company in the sidebar and click **Run analysis** to begin.")


if __name__ == "__main__":
    main()
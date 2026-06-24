"""
Streamlit dashboard — Sprint 1 user interface.

A clean, functional dashboard that runs the Sprint 1 pipeline (Steps 1-8) and
displays the executive summary, FinBERT tone, risk factors and forward
guidance. KPI comparison, charts and the PDF report are Sprint 2 deliverables.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from genai_analyst.core import config, pipeline

st.set_page_config(
    page_title="GenAI Financial Earnings Report Analyst", page_icon="📊"
)


def render_sidebar():
    """Render the input sidebar and return (ticker, form_type, run)."""
    st.sidebar.header("Analysis settings")

    # A curated list of well-known tickers that demo reliably, plus an
    # "Other…" escape hatch so any ticker can still be entered manually.
    popular_tickers = [
        "AAPL — Apple",
        "MSFT — Microsoft",
        "GOOGL — Alphabet",
        "AMZN — Amazon",
        "META — Meta Platforms",
        "NVDA — NVIDIA",
        "TSLA — Tesla",
        "NFLX — Netflix",
        "JPM — JPMorgan Chase",
        "KO — Coca-Cola",
        "Other…",
    ]
    choice = st.sidebar.selectbox("Company", popular_tickers, index=0)

    if choice == "Other…":
        ticker = st.sidebar.text_input("Enter ticker symbol", "").strip().upper()
    else:
        # Take the symbol portion before the em dash.
        ticker = choice.split("—")[0].strip().upper()

    form_type = st.sidebar.selectbox("Filing type", ["10-K", "10-Q"])
    run = st.sidebar.button("Analyse", type="primary")

    st.sidebar.markdown("---")
    st.sidebar.caption("Sprint 1 (mid-sem): SEC ingestion + RAG + Llama 3")
    if not config.is_llm_configured():
        st.sidebar.warning(
            "LLAMA3_API_KEY is not set. Summary, risks and guidance will show "
            "placeholders. Add your key to the .env file."
        )
    return ticker, form_type, run


def render_results(result: dict):
    """Render a successful analysis result."""
    filing = result["filing"]
    st.success(
        f"Analysis complete for {filing['company']} ({filing['ticker']}) — "
        f"{filing['form']} filed {filing['filing_date']}"
    )

    st.header("Executive Summary")
    st.write(result.get("summary") or "No summary generated.")

    tone = result.get("tone", {})
    st.header("Management Tone (FinBERT)")
    st.write(
        f"**{tone.get('label', 'N/A')}** — tone score "
        f"{tone.get('tone_score', 0):.2f} / 1.00  "
        f"(positive: {tone.get('positive', 0)}, "
        f"neutral: {tone.get('neutral', 0)}, "
        f"negative: {tone.get('negative', 0)})"
    )

    st.header("Risk Factors")
    risks = result.get("risks") or []
    if risks:
        for index, risk in enumerate(risks, start=1):
            if isinstance(risk, dict):
                text = risk.get("risk") or risk.get("title") or str(risk)
                category = risk.get("category", "")
                severity = risk.get("severity", "")
                suffix = " ".join(
                    part for part in [
                        f"[{category}]" if category else "",
                        f"({severity})" if severity else "",
                    ] if part
                )
                st.write(f"{index}. {text} {suffix}".strip())
            else:
                st.write(f"{index}. {risk}")
    else:
        st.write("No structured risk factors extracted.")

    st.header("Forward Guidance")
    st.write(result.get("guidance") or "No guidance generated.")

    st.markdown("---")
    n_chunks = result.get("n_chunks", 0)
    if n_chunks == -1:
        index_note = "Filing already indexed (reused cached embeddings). "
    else:
        index_note = f"Indexed {n_chunks} chunks. "
    st.caption(
        index_note
        + "Generated using RAG (ChromaDB + Top-K) and Meta Llama 3. "
        "KPI comparison, charts and PDF report are Sprint 2 deliverables."
    )
    st.caption(config.DISCLAIMER)


def main():
    """Application entry point."""
    st.title("GenAI Financial Earnings Report Analyst")
    st.write(
        "Enter a company ticker to analyse its latest SEC filing. The system "
        "fetches the filing from EDGAR, runs it through the RAG pipeline "
        "(chunking, embeddings, ChromaDB, retrieval) and uses Meta Llama 3 to "
        "generate the summary, risk factors and guidance."
    )

    ticker, form_type, run = render_sidebar()

    if not run:
        st.info("Enter a ticker in the sidebar and click Analyse to begin.")
        return

    if not ticker:
        st.warning("Please enter a ticker symbol.")
        return

    progress_bar = st.progress(0.0, text="Starting…")

    def _progress(message: str, fraction: float):
        progress_bar.progress(min(fraction, 1.0), text=message)

    try:
        with st.spinner("Running analysis pipeline…"):
            result = pipeline.run_analysis(
                ticker, form_type, progress=_progress
            )
    except Exception as error:  # surface errors instead of a blank page
        import traceback

        progress_bar.empty()
        st.error("The analysis pipeline encountered an error:")
        st.code(traceback.format_exc(), language="text")
        return

    progress_bar.empty()

    if "error" in result:
        st.error(result["error"])
    else:
        render_results(result)


if __name__ == "__main__":
    main()
"""
pipeline.py
===========
End-to-End Orchestrator.

Wires every module together into the exact architecture flow from the SRS:

  Ticker -> EDGAR ingest -> HTML parse -> clean -> chunk (LangChain)
        -> Sentence-Transformer embed -> ChromaDB store -> RAG retrieve
        -> XBRL KPI extract -> FinBERT tone -> Llama 3 summary/risk/guidance
        -> Bull/Bear signal -> KPI comparison -> charts -> PDF -> SQLite

`run_analysis()` is called by the Streamlit dashboard (app.py) and returns a
single result dict containing everything needed to render the UI + PDF.

The `progress` callback (optional) receives (step_label, fraction) so the
dashboard can show a live progress spinner.

Caching
-------
A completed analysis is persisted in full — including the forward-guidance text
and the structured risk list — so a cache hit renders identically to a fresh
run. Rows written by older versions predate the ``guidance`` / ``risks_json``
columns; those fields simply come back empty and the UI explains that a
re-analysis will regenerate them.
"""

from __future__ import annotations

import json
from typing import Callable, Dict, Optional

from genai_analyst.analysis import comparison_engine
from genai_analyst.core import database
from genai_analyst.ingestion import edgar_client
from genai_analyst.analysis import kpi_extractor
from genai_analyst.rag import indexer
from genai_analyst.nlp import generation
from genai_analyst.ingestion import filing_parser
from genai_analyst.output import pdf_generator
from genai_analyst.rag import retriever
from genai_analyst.analysis import signal_generator
from genai_analyst.nlp import sentiment
from genai_analyst.output import visualizer


def _noop(label: str, frac: float) -> None:  # default progress sink
    print(f"[pipeline] {int(frac * 100):3d}% - {label}")


def run_analysis(
    ticker: str,
    form_type: str = "10-K",
    force: bool = False,
    progress: Optional[Callable[[str, float], None]] = None,
    accession: Optional[str] = None,
) -> Dict:
    """Run the full pipeline for one ticker/form. Returns a result dict.

    If `accession` is given, that specific filing is analysed; otherwise the
    most recent filing of `form_type` is used.

    On any unrecoverable error (e.g. unknown ticker) returns
    {'error': '<message>'} so the UI can display it gracefully.
    """
    progress = progress or _noop

    # 1. Ingest filing -----------------------------------------------------
    progress("Fetching filing from SEC EDGAR", 0.05)
    filing = edgar_client.ingest(ticker, form_type, accession=accession)
    if not filing:
        alt = "10-K" if form_type == "10-Q" else "10-Q"
        return {"error": f"No {form_type} filing found for '{ticker}' on SEC EDGAR. "
                         f"This company may not file that form — try selecting {alt} "
                         "instead, or choose another company."}

    cache_key = f"{filing['ticker']}_{filing['form']}_{filing['accession']}"

    # Short-circuit on cached analysis (SQLite) unless forced.
    if not force:
        cached = database.get_cached_analysis(
            filing["ticker"], filing["form"], filing["accession"]
        )
        if cached and cached.get("pdf_path"):
            progress("Loaded cached analysis", 1.0)
            return _result_from_cache(cached, filing)

    # 2-4. Parse + clean + segment ----------------------------------------
    progress("Parsing & cleaning filing HTML", 0.15)
    sections = filing_parser.parse_filing(filing["html"])

    # 5-6. Chunk + embed + store in ChromaDB ------------------------------
    progress("Chunking, embedding & indexing (ChromaDB)", 0.30)
    n_chunks = indexer.index_filing(filing, sections, force=force)

    # 7. RAG retrieval -----------------------------------------------------
    progress("Retrieving relevant context (RAG Top-K)", 0.45)
    contexts = retriever.retrieve_all_contexts(filing)

    # 7b. XBRL KPI extraction ---------------------------------------------
    progress("Extracting financial KPIs (EDGAR XBRL)", 0.55)
    kpis = kpi_extractor.extract_kpis(filing["cik"], filing["form"])
    kpi_table = comparison_engine.build_comparison(kpis)
    comp_summary = comparison_engine.comparison_summary(kpi_table)

    # 8. FinBERT tone analysis --------------------------------------------
    progress("Analysing management tone (FinBERT)", 0.65)
    tone_chunks = _tone_input_chunks(contexts, sections)
    tone = sentiment.analyze(tone_chunks)

    # 8. Llama 3 language tasks -------------------------------------------
    progress("Generating summary, risks & guidance (Llama 3)", 0.78)
    summary = generation.generate_executive_summary(
        contexts.get("executive_summary", ""), cache_key)
    risks = generation.extract_risk_factors(
        contexts.get("risk_factors", ""), cache_key)
    guidance = generation.extract_guidance(
        contexts.get("guidance", ""), cache_key)

    # 8b. Bull/Bear signal -------------------------------------------------
    progress("Computing Bull/Bear signal", 0.85)
    signal = signal_generator.generate_signal(
        comp_summary, tone.get("tone_score", 0.5), guidance)

    # 10. Charts -----------------------------------------------------------
    progress("Rendering charts", 0.90)
    charts = visualizer.generate_all_charts(kpi_table, tone, signal, filing["ticker"])

    # 11. PDF report -------------------------------------------------------
    progress("Generating PDF report (ReportLab)", 0.95)
    pdf_path = pdf_generator.generate_report(
        filing=filing, kpi_table=kpi_table, tone=tone, summary=summary,
        guidance=guidance, risks=risks, signal=signal, charts=charts,
    )

    # 17. Persist to SQLite ------------------------------------------------
    progress("Saving to history (SQLite)", 0.98)
    database.save_analysis({
        "ticker": filing["ticker"], "company": filing["company"],
        "form": filing["form"], "accession": filing["accession"],
        "filing_date": filing["filing_date"],
        "tone_score": tone.get("tone_score"), "tone_label": tone.get("label"),
        "signal_score": signal.get("score"), "signal_class": signal.get("classification"),
        "kpis": kpis, "summary": summary,
        "guidance": guidance, "risks": risks,
        "pdf_path": pdf_path,
    })

    progress("Done", 1.0)
    return {
        "filing": filing,
        "n_chunks": n_chunks,
        "kpis": kpis,
        "kpi_table": kpi_table,
        "tone": tone,
        "summary": summary,
        "risks": risks,
        "guidance": guidance,
        "signal": signal,
        "charts": charts,
        "pdf_path": pdf_path,
        "from_cache": False,
    }


def _result_from_cache(cached: dict, filing: dict) -> dict:
    """Rebuild a full, displayable result dict from a saved SQLite row.

    Everything needed by the UI is persisted: KPIs, tone, signal, summary,
    forward guidance and the structured risk list. The comparison table and
    charts are regenerated locally from the saved KPIs (no network, no model
    calls), so a cache hit renders the same way as a fresh run.

    Rows saved before the guidance/risks columns existed return empty values
    for those two fields; the UI tells the user to re-run to regenerate them.
    """
    try:
        kpis = json.loads(cached.get("kpis_json") or "{}")
    except (ValueError, TypeError):
        kpis = {}

    try:
        risks = json.loads(cached.get("risks_json") or "[]")
    except (ValueError, TypeError):
        risks = []
    if not isinstance(risks, list):
        risks = []

    kpi_table = comparison_engine.build_comparison(kpis) if kpis else None

    tone = {
        "label": cached.get("tone_label", "N/A"),
        "tone_score": cached.get("tone_score") or 0.0,
        "positive": 0, "neutral": 0, "negative": 0,
    }
    signal = {
        "classification": cached.get("signal_class", "NEUTRAL"),
        "score": cached.get("signal_score") or 0.0,
        "evidence": [],
    }

    try:
        charts = visualizer.generate_all_charts(
            kpi_table, tone, signal, filing["ticker"]
        ) if kpi_table is not None else {}
    except Exception:
        charts = {}

    full_filing = {
        "ticker": cached.get("ticker", filing.get("ticker")),
        "company": cached.get("company", filing.get("company")),
        "form": cached.get("form", filing.get("form")),
        "accession": cached.get("accession", filing.get("accession")),
        "filing_date": cached.get("filing_date", filing.get("filing_date")),
    }

    guidance = cached.get("guidance") or ""
    # Legacy rows (saved before the guidance column existed) have nothing to
    # show; point the user at the re-run option rather than leaving it blank.
    legacy = not guidance and not risks

    return {
        "filing": full_filing,
        "n_chunks": 0,
        "kpis": kpis,
        "kpi_table": kpi_table,
        "tone": tone,
        "summary": cached.get("summary") or "",
        "risks": risks,
        "guidance": guidance or (
            "Not stored for this saved analysis. Tick **Force re-analysis "
            "(ignore cache)** in the sidebar and run again to regenerate the "
            "forward-guidance section, or see the saved PDF report below."
        ),
        "signal": signal,
        "charts": charts,
        "pdf_path": cached.get("pdf_path"),
        "from_cache": True,
        "legacy_cache": legacy,
    }


def _tone_input_chunks(contexts: Dict[str, str], sections: Dict[str, str]):
    """Pick a reasonable set of text chunks to feed FinBERT.

    Splits the MD&A / tone context into sentence-ish chunks so FinBERT gets
    digestible inputs rather than one huge block.
    """
    source = contexts.get("tone") or sections.get("MD&A") or sections.get("full", "")
    # Split into ~paragraph chunks, capped to keep latency reasonable.
    raw = [p.strip() for p in source.split("\n") if len(p.strip()) > 40]
    return raw[:40]


if __name__ == "__main__":
    # Manual end-to-end smoke test (requires internet + configured LLM key).
    result = run_analysis("AAPL", "10-K")
    if "error" in result:
        print("ERROR:", result["error"])
    else:
        print("PDF:", result["pdf_path"])
        print("Signal:", result["signal"]["classification"])
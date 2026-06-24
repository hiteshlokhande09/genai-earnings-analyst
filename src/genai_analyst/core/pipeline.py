"""
Pipeline orchestration (Sprint 1 — Steps 1-8 of the SRS architecture flow).

Coordinates the full Sprint 1 analysis for a single ticker / filing:

    1-2  Ingest filing from SEC EDGAR
    3-4  Parse + clean + segment the HTML
    4-6  Chunk, embed and index into ChromaDB (RAG)
    7    Retrieve task-relevant context (RAG)
    8    FinBERT sentiment + Llama 3 summary / risks / guidance

Returns a single result dictionary consumed by the dashboard, or an
``{"error": ...}`` dictionary so the UI can fail gracefully. Steps 9-12 (KPI
comparison, charts, PDF, full dashboard) are Sprint 2 deliverables.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from genai_analyst.ingestion import edgar_client, filing_parser
from genai_analyst.nlp import generation, sentiment
from genai_analyst.rag import indexer, retriever

# Type alias for an optional progress callback: (message, fraction) -> None.
ProgressFn = Optional[Callable[[str, float], None]]


def _noop(_message: str, _fraction: float) -> None:
    """Default no-op progress callback."""


def run_analysis(
    ticker: str,
    form_type: str = "10-K",
    progress: ProgressFn = None,
    accession: Optional[str] = None,
) -> Dict:
    """Run the Sprint 1 analysis pipeline for one ticker / filing.

    Parameters
    ----------
    ticker:
        Stock ticker symbol (e.g. ``"AAPL"``).
    form_type:
        ``"10-K"`` or ``"10-Q"``.
    progress:
        Optional callback invoked with (message, fraction in [0, 1]).
    accession:
        Optional specific filing accession number; defaults to the latest.

    Returns
    -------
    A result dict with keys: filing, sections, n_chunks, tone, summary, risks,
    guidance — or ``{"error": "..."}`` on failure.
    """
    progress = progress or _noop

    # ---- Steps 1-2: Ingest ------------------------------------------------- #
    progress("Fetching filing from SEC EDGAR", 0.10)
    filing = edgar_client.ingest(ticker, form_type, accession=accession)
    if not filing:
        alternative = "10-K" if form_type == "10-Q" else "10-Q"
        return {
            "error": (
                f"No {form_type} filing found for '{ticker}' on SEC EDGAR. "
                f"This company may not file that form — try {alternative} "
                "instead, or choose another company."
            )
        }

    # ---- Steps 3-4: Parse -------------------------------------------------- #
    progress("Parsing and cleaning filing", 0.25)
    sections = filing_parser.parse_filing(filing["html"])

    # ---- Steps 4-6: Index (RAG) ------------------------------------------- #
    progress("Chunking, embedding and indexing (RAG)", 0.45)
    n_chunks = indexer.index_filing(filing, sections)

    # ---- Step 7: Retrieve context ----------------------------------------- #
    progress("Retrieving relevant context (RAG Top-K)", 0.60)
    contexts = retriever.retrieve_all_contexts(filing)

    # ---- Step 8a: FinBERT sentiment --------------------------------------- #
    progress("Analysing sentiment with FinBERT", 0.75)
    tone_source = sections.get("MD&A") or sections.get("Full Document", "")
    tone_chunks = _split_for_sentiment(tone_source)
    tone = sentiment.analyze(tone_chunks)

    # ---- Step 8b: Llama 3 generation -------------------------------------- #
    progress("Generating summary, risks and guidance (Llama 3)", 0.90)
    summary = generation.generate_executive_summary(contexts["executive_summary"])
    risks = generation.extract_risk_factors(contexts["risk_factors"])
    guidance = generation.extract_guidance(contexts["guidance"])

    progress("Done", 1.0)
    return {
        "filing": {
            "ticker": filing["ticker"],
            "company": filing["company"],
            "form": filing["form"],
            "accession": filing["accession"],
            "filing_date": filing["filing_date"],
        },
        "n_chunks": n_chunks,
        "tone": tone,
        "summary": summary,
        "risks": risks,
        "guidance": guidance,
    }


def _split_for_sentiment(text: str, max_pieces: int = 40) -> list[str]:
    """Split text into paragraph-sized pieces for FinBERT, capped in count."""
    if not text:
        return []
    pieces = [p.strip() for p in text.split(". ") if len(p.strip()) > 40]
    return pieces[:max_pieces]

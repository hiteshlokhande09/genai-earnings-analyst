# 05 — SRS Traceability

This document proves that **every** SRS deliverable, system feature, and
acceptance criterion is satisfied by a concrete piece of code. Use it in the
reviews to answer "where is requirement X?" instantly.

---

## A. Deliverables (SRS §6) → code

| # | SRS Deliverable | Where it lives |
|---|-----------------|----------------|
| 1 | Modular PEP8 source, one file per stage | entire repo root |
| 2 | Streamlit dashboard, pure Python | `app.py` |
| 3 | FinBERT sentiment module (local) | `tone_analyzer.py` |
| 4 | SEC EDGAR API integration (filings + XBRL) | `edgar_downloader.py`, `kpi_extractor.py` |
| 5 | Llama 3 integration (summary/risk/guidance) | `llama3_helper.py` |
| 6 | ReportLab PDF generator | `pdf_generator.py` |
| 7 | SQLite3 storage module | `database.py` |
| 8 | Bull/Bear signal generator | `signal_generator.py` |
| 9 | `requirements.txt` (all free/open-source) | `requirements.txt` |
| 10 | Installation & user manual (README) | `README.md` |
| 11 | SRS document | provided PDF (`PGCP-BDA-18.pdf`) |
| 12 | Demo / presentation flow | `knowledge transfer/06_review_and_demo_guide.md` |
| 13 | `embedding_generator.py` | `embedding_generator.py` |
| 14 | `vector_store.py` | `vector_store.py` |
| 15 | `rag_retriever.py` | `rag_retriever.py` |
| 16 | `langchain_pipeline.py` | `langchain_pipeline.py` |
| 17 | ChromaDB Vector DB module | `vector_store.py` |
| 18 | RAG module | `rag_retriever.py` |
| 19 | Sentence Transformer embedding module | `embedding_generator.py` |

Every required filename from the SRS exists. Extra helper files
(`config.py`, `pipeline.py`, `visualizer.py`, `comparison_engine.py`,
`run_cli.py`) support modularity and the architecture flow; they do not replace
any required file.

---

## B. System features (SRS §5) → module

| SRS Feature | Module / function |
|-------------|-------------------|
| SEC Filing Retrieval (EDGAR API) | `edgar_downloader.ingest` |
| XBRL Financial KPI Extraction | `kpi_extractor.extract_kpis` |
| HTML Parsing (BeautifulSoup4) | `parser.html_to_text` |
| Text Cleaning & Semantic Chunking (LangChain) | `parser.clean_text`, `langchain_pipeline.chunk_sections` |
| Sentence Transformer Embeddings (all-MiniLM-L6-v2) | `embedding_generator.embed_texts` |
| ChromaDB Vector Storage | `vector_store.add_chunks` |
| RAG — Top-K Similarity Search | `rag_retriever.retrieve` |
| Financial Sentiment Analysis (FinBERT, local) | `tone_analyzer.analyze` |
| Executive Summary & Risk Extraction (Llama 3) | `llama3_helper.*` |
| Bull/Bear Signal Generation | `signal_generator.generate_signal` |
| KPI Period Comparison (pandas) | `comparison_engine.build_comparison` |
| Data Visualisation (matplotlib) | `visualizer.generate_all_charts` |
| PDF Report Generation (ReportLab) | `pdf_generator.generate_report` |
| Streamlit Dashboard | `app.py` |
| Historical SQLite3 Storage | `database.save_analysis` |

The **architecture flow** in SRS §5 is implemented in exact order by
`pipeline.run_analysis()` — see `04_end_to_end_walkthrough.md`.

---

## C. Acceptance criteria (SRS §5) → evidence

| # | Acceptance criterion | How it is met |
|---|----------------------|---------------|
| 1 | Retrieve 10-Q/10-K from ticker only | `edgar_downloader.ticker_to_cik` + `get_latest_filing` |
| 2 | All KPI numbers from XBRL, no AI numbers | `kpi_extractor` only; Llama 3 never returns figures |
| 3 | FinBERT labels + confidence for all chunks | `tone_analyzer.analyze_chunks` |
| 4 | Llama 3 exec summary + top-5 risks + guidance | `llama3_helper.generate_executive_summary / extract_risk_factors / extract_guidance` |
| 5 | Bull/Bear 0–1 score with classification | `signal_generator.generate_signal` |
| 6 | pandas period-over-period % change | `comparison_engine.build_comparison` |
| 7 | PDF includes all 9 sections | `pdf_generator.generate_report` |
| 8 | Dashboard loads + working PDF download | `app.py` download button |
| 9 | SQLite stores/retrieves ≥100 records + caching | `database` (`analysis_results`, `llm_cache`) |
| 10 | Graceful handling of bad input / API failure | `try/except` + `{"error":...}` return in `pipeline`; retry/backoff in `_get` |
| 11 | Setup via git clone + pip + .env + streamlit run | `README.md`, `requirements.txt`, `.env.example` |
| 12 | Embeddings generated for all chunks | `embedding_generator.embed_texts` |
| 13 | ChromaDB stores/retrieves vectors | `vector_store` |
| 14 | RAG retrieves most relevant sections | `rag_retriever.retrieve` |
| 15 | Llama 3 uses only retrieved chunks | contexts passed in `pipeline` step 8 |
| 16 | Vector DB scales to thousands of chunks | ChromaDB persistent client |
| 17 | Retrieval latency acceptable | Top-K search on local persistent index |

---

## D. Constraints (SRS §3.4) → how enforced

- **Python 3.10+** — `requirements.txt` / README.
- **API key in .env, never hardcoded** — `config.py` reads `os.getenv`; `.env`
  is in `.gitignore`; only `.env.example` is committed.
- **FinBERT local** — `tone_analyzer` loads the HuggingFace pipeline locally.
- **Only retrieved chunks to Llama 3, max_tokens=500, SQLite cache** — enforced
  in `rag_retriever` + `llama3_helper` + `config`.
- **Graceful nulls + retry/backoff** — `_get()` and `extract_kpis` return safe
  defaults; pipeline never crashes the UI.

> If a reviewer points at any SRS line, this file maps it to a file and function.

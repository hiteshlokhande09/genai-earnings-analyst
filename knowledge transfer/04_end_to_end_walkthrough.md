# 04 — End-to-End Walkthrough

This document traces a **single analysis** from the moment a user clicks
*Analyze* in the dashboard to the finished PDF. Read it with
`pipeline.py` open beside you — that file is the spine of the whole system.

Scenario: the user types `AAPL`, selects `10-K`, and clicks **Analyze**.

---

## Step 0 — The click (`app.py`)

`app.py` collects the ticker and form type from the sidebar and calls:

```python
result = pipeline.run_analysis(ticker, form_type, force=force, progress=cb)
```

`cb` is a small callback that updates the Streamlit progress bar each time the
pipeline reports a new step. `run_analysis()` returns one dictionary that holds
*everything* the UI needs, or `{"error": "..."}` if something failed. The UI
never talks to individual modules directly — only to `run_analysis()`.

---

## Step 1 — Ingest the filing (`edgar_downloader.ingest`)

1. `ticker_to_cik("AAPL")` looks up Apple's 10-digit Central Index Key from the
   SEC's `company_tickers.json`.
2. `get_latest_filing()` queries the EDGAR **Submissions API** and finds the most
   recent `10-K` accession number and its primary document URL.
3. `download_filing_html()` fetches the raw filing HTML.

It returns a `filing` dict: `ticker`, `company`, `cik`, `form`, `accession`,
`filing_date`, and `html`. If the ticker is unknown or offline, it returns
`None`, and `run_analysis` immediately returns a friendly `error`.

> Every HTTP call goes through `_get()`, which sets the SEC-required
> `User-Agent` header and retries with exponential backoff.

---

## Step 1b — Cache check (`database.get_cached_analysis`)

A `cache_key` is built from `ticker_form_accession`. Unless the user ticked
**Force re-run**, the pipeline asks SQLite whether this exact filing was already
analysed. If a cached row with a valid PDF exists, it is returned instantly with
`from_cache = True` — this is the "second company runs instantly" demo moment.

---

## Steps 2–4 — Parse, clean, segment (`parser.parse_filing`)

- `html_to_text()` uses **BeautifulSoup4** to strip tags, scripts, and styles.
- `clean_text()` collapses whitespace and removes boilerplate.
- `segment_sections()` uses regex to locate **Item 1A (Risk Factors)**,
  **Item 7 (MD&A)**, and **Item 8 (Financial Statements)**.

Output: a `sections` dict like `{"MD&A": "...", "Risk Factors": "...", ...}`.

---

## Steps 5–6 — Chunk, embed, store (`langchain_pipeline.index_filing`)

1. **Chunk** — LangChain's `RecursiveCharacterTextSplitter` cuts each section
   into ~2500-character chunks with 250-character overlap.
2. **Embed** — `embedding_generator.embed_texts()` turns each chunk into a
   384-dimensional vector using Sentence Transformers `all-MiniLM-L6-v2`.
3. **Store** — `vector_store.add_chunks()` writes the vectors into a
   per-filing **ChromaDB** collection on local disk.

If the collection already exists, indexing is skipped (another cache layer).
Returns `n_chunks`, the number of chunks indexed.

---

## Step 7 — RAG retrieval (`rag_retriever.retrieve_all_contexts`)

For each analytical task there is a natural-language query template, e.g.
*"What is the executive summary of financial performance?"* Each query is
embedded and run against ChromaDB with **Top-K cosine similarity** to pull back
only the most relevant chunks. The result is a `contexts` dict:
`executive_summary`, `risk_factors`, `guidance`, `tone` — each a compact block
of the most relevant text. **This is what keeps Llama 3 cheap:** it only ever
sees a few retrieved chunks, never the 150-page filing.

---

## Step 7b — XBRL KPI extraction (`kpi_extractor.extract_kpis`)

Completely independent of the AI path. It calls the EDGAR **XBRL companyconcept
API** for each KPI tag (Revenue, NetIncome, EPS, GrossProfit, OperatingIncome),
walking a fallback list of tag names because companies report under slightly
different concepts. It returns the **current and prior period** exact values.

`comparison_engine.build_comparison()` then puts these into a pandas DataFrame,
computing period-over-period % change and ▲/▼ arrows.

> **Golden rule in action:** numbers come from XBRL here, not from Llama 3.

---

## Step 8 — FinBERT tone (`tone_analyzer.analyze`)

`_tone_input_chunks()` selects up to ~40 paragraph-sized pieces of the MD&A /
tone context. FinBERT (`ProsusAI/finbert`) labels each as
positive / negative / neutral with a confidence score, and `aggregate_tone()`
blends them into a single 0–1 **tone score** plus an overall label.

---

## Step 8 — Llama 3 language tasks (`llama3_helper`)

Three calls, each fed **only the retrieved context**:

- `generate_executive_summary(contexts["executive_summary"])`
- `extract_risk_factors(contexts["risk_factors"])` → JSON list of top-5 risks
  with category + severity
- `extract_guidance(contexts["guidance"])`

Each call is capped at `max_tokens=500` and cached in SQLite by `cache_key`, so
re-running the same filing costs **zero** API calls. With no API key set, the
helper returns clearly-labelled placeholder text so the rest of the pipeline
still runs.

---

## Step 8b — Bull/Bear signal (`signal_generator.generate_signal`)

A transparent weighted blend (no AI):

| Component | Weight |
|-----------|--------|
| Revenue growth | 0.30 |
| Margin trend | 0.25 |
| Tone score | 0.25 |
| Guidance | 0.20 |

Score ≥ 0.60 → **BULLISH**, ≤ 0.40 → **BEARISH**, else **NEUTRAL**.

---

## Steps 10–11 — Charts + PDF (`visualizer`, `pdf_generator`)

- `visualizer.generate_all_charts()` renders a KPI bar chart, a tone chart, and
  a signal gauge with matplotlib (headless `Agg` backend) and saves them as PNGs.
- `pdf_generator.generate_report()` assembles the **9-section** investor-grade
  PDF with ReportLab: Cover, Executive Summary, KPI Table, KPI Chart, Tone,
  Guidance, Top-5 Risks, Bull/Bear Signal, Disclaimer.

---

## Step 17 — Persist (`database.save_analysis`)

The full result (KPIs, tone, signal, summary, PDF path) is written to the
SQLite `analysis_results` table for history and future caching.

---

## Back in the UI (`app.py`)

`run_analysis()` returns the result dict. The dashboard renders KPI metric cards
with deltas, the colour-coded comparison table, the tone and signal panels, the
charts, and a **Download PDF** button. The whole filing also now appears in the
**history** list in the sidebar.

---

## One-line mental model

> `app.py` asks `pipeline.run_analysis()`; the pipeline walks the SRS
> architecture flow left-to-right, keeping **AI words** and **XBRL numbers**
> strictly separate, and hands back one dict that powers both the dashboard and
> the PDF.

# 03 — Module Reference (Deep Dive)

Every Python file, what it does, and every important function. Files are listed
in pipeline order. Read alongside the source — each file is also heavily
commented.

---

## `config.py` — Central configuration

The single source of truth for paths, endpoints, model names, and tunables. No
other module hard-codes a "magic value"; they import from here.

Key contents:

- **Paths** — `BASE_DIR`, `DATA_DIR`, `CACHE_DIR`, `CHROMA_DIR`, `REPORTS_DIR`,
  `CHARTS_DIR`, `DB_PATH`. All `data/` subfolders are auto-created on import.
- **SEC endpoints** — `SEC_TICKER_MAP_URL`, `SEC_SUBMISSIONS_URL`,
  `SEC_XBRL_CONCEPT_URL`, `SEC_ARCHIVES_URL`, plus `SEC_HEADERS` (the required
  User-Agent).
- **Llama 3 settings** — `LLAMA3_API_KEY`, `LLAMA3_BASE_URL`, `LLAMA3_MODEL`,
  `LLAMA3_MAX_TOKENS` (=500), `LLAMA3_TEMPERATURE` (=0.2). Loaded from `.env`
  via `python-dotenv`.
- **Model names** — `EMBEDDING_MODEL_NAME` (`all-MiniLM-L6-v2`),
  `FINBERT_MODEL_NAME` (`ProsusAI/finbert`).
- **RAG params** — `CHUNK_SIZE`, `CHUNK_OVERLAP`, `RAG_TOP_K` (=5).
- **Resilience** — `REQUEST_TIMEOUT`, `MAX_RETRIES`, `BACKOFF_BASE`.
- **`KPI_CONCEPTS`** — for each KPI, an ordered list of XBRL concept tags to
  try (companies tag the same concept differently, so we fall back through them).
- **`DISCLAIMER`** — the legal text appended to every PDF.

> **To tune the system, edit `config.py` first.** e.g. raise `RAG_TOP_K` to pull
> more context, or change `LLAMA3_MODEL` to a larger model.

---

## `edgar_downloader.py` — SEC filing ingestion (Step 2)

Turns a ticker into downloaded filing HTML.

| Function | Purpose |
|---|---|
| `_get(url, as_json)` | Resilient HTTP GET with SEC headers, **retry + exponential backoff**. Returns parsed JSON or text, or `None` on failure. **Reused by `kpi_extractor.py`.** |
| `_load_ticker_map()` | Downloads & caches (24h) the SEC ticker→CIK master list. |
| `ticker_to_cik(ticker)` | Resolves a ticker to its 10-digit zero-padded CIK. |
| `get_latest_filing(ticker, form_type)` | Finds the most recent 10-K/10-Q; returns metadata (company, accession, filing date, document URL). |
| `download_filing_html(filing)` | Downloads & caches the primary filing HTML. |
| `ingest(ticker, form_type)` | **Entry point** — runs the three steps above and returns the filing dict with an added `html` key. |

The `filing` dict produced here is threaded through the entire pipeline.

---

## `parser.py` — HTML parsing, cleaning, sectioning (Steps 3-4)

Turns raw filing HTML into clean, sectioned text.

| Function | Purpose |
|---|---|
| `html_to_text(html)` | BeautifulSoup4 strips scripts/styles/etc., extracts text, then cleans it. |
| `clean_text(text)` | Normalises whitespace, removes page numbers & non-breaking chars, collapses blank lines. |
| `segment_sections(text)` | Regex-locates **Item 1A Risk Factors**, **Item 7/2 MD&A**, **Item 8/1 Financial Statements** and slices the text between headings. Gracefully falls back to treating the whole document as MD&A if no headings match. |
| `parse_filing(html)` | **Entry point** — returns `{"MD&A":…, "Risk Factors":…, "Financial Statements":…, "full":…}`. |

spaCy is loaded *opportunistically* for better sentence handling but is fully
optional (the module works without it).

---

## `langchain_pipeline.py` — Chunking + indexing orchestration (Steps 4-6)

The ingestion half of the RAG subsystem.

| Function | Purpose |
|---|---|
| `_get_splitter()` | Builds a LangChain `RecursiveCharacterTextSplitter` (~500-word chunks, with overlap). |
| `chunk_sections(sections)` | Splits each named section into chunks, tagging each chunk with its source section. |
| `index_filing(filing, sections, force)` | **Entry point** — chunk → embed → store in ChromaDB. **Skips work if the filing is already indexed** (caching) unless `force=True`. Returns the chunk count. |

---

## `embedding_generator.py` — Sentence Transformer embeddings (Step 5)

| Function | Purpose |
|---|---|
| `get_model()` | Lazily loads & caches the `all-MiniLM-L6-v2` model (singleton). |
| `embed_texts(texts)` | Embeds a list of strings → list of 384-dim vectors (cosine-normalised). |
| `embed_query(query)` | Embeds a single query string. |
| `embedding_dimension()` | Returns 384. |

Lazy loading means importing this module is cheap; the model only loads the
first time you actually embed something.

---

## `vector_store.py` — ChromaDB persistence (Step 6)

| Function | Purpose |
|---|---|
| `get_client()` | Persistent ChromaDB client rooted at `data/chroma/`. |
| `_collection_name(filing)` | Deterministic, Chroma-safe name per filing (ticker+form+accession). |
| `get_or_create_collection(filing)` | The filing's vector collection (cosine space). |
| `collection_exists(filing)` | True if a non-empty index already exists (enables caching). |
| `add_chunks(filing, chunks, embeddings, metadatas)` | Stores chunk text + vectors + metadata. |
| `query(filing, query_embedding, top_k)` | **Top-K cosine search** → list of `{document, metadata, distance}`. |
| `reset_collection(filing)` | Deletes a collection (for forced re-index). |

Each filing is isolated in its own collection so companies never cross-contaminate.

---

## `rag_retriever.py` — Retrieval layer (Step 7)

| Function | Purpose |
|---|---|
| `retrieve(filing, query_text, top_k)` | Embeds the query, runs Top-K search, returns hits. |
| `retrieve_context(filing, query_text, top_k)` | Same, but joins the hit texts into one context block. |
| `QUERY_TEMPLATES` | Canonical analyst questions: `executive_summary`, `risk_factors`, `guidance`, `tone`. |
| `retrieve_all_contexts(filing, top_k)` | Runs every template → `{template_name: context}`. |

This is what keeps Llama 3 prompts small and grounded.

---

## `kpi_extractor.py` — XBRL KPI extraction (Step 7b)

Pulls **exact** financial numbers from EDGAR XBRL — never from the AI.

| Function | Purpose |
|---|---|
| `_fetch_concept(cik10, concept)` | GETs one us-gaap concept JSON. |
| `_extract_period_values(data, form)` | Flattens the XBRL response into period values, newest-first, preferring rows matching the form type. |
| `extract_kpis(cik10, form)` | **Entry point** — for each KPI (Revenue, NetIncome, EPS, GrossProfit, OperatingIncome) tries each concept tag until one returns data, then captures the latest two comparable periods. |
| `format_kpi_value(value, unit)` | Display formatting ($1.23B, 5.67, etc.). |

Returns `{KPI: {current, previous, unit, current_period, previous_period}}`.
Missing KPIs → `None` values (graceful, never a crash).

---

## `comparison_engine.py` — KPI period comparison (Step 9)

| Function | Purpose |
|---|---|
| `_pct_change(current, previous)` | Safe % change; `None` if not computable. |
| `build_comparison(kpis)` | Builds a pandas DataFrame: KPI, Current, Previous, Change %, Direction (▲/▼/—), Trend, plus raw numeric columns for the signal engine. |
| `comparison_summary(df)` | Extracts raw growth numbers (revenue/net-income/eps/gross/operating) for the signal engine. |

---

## `tone_analyzer.py` — FinBERT sentiment (Step 8, local)

| Function | Purpose |
|---|---|
| `get_pipeline()` | Lazily loads the FinBERT `text-classification` pipeline (singleton, cached locally after first download). |
| `analyze_chunks(chunks)` | Classifies each chunk → `{label, score, text_preview}`; skips bad chunks without crashing. |
| `aggregate_tone(chunk_results)` | Blends per-chunk results into an overall `tone_score` in [0,1] and a Positive/Neutral/Negative label, with counts. |
| `analyze(chunks)` | **Entry point** — runs both and returns the full tone dict. |

Runs entirely offline after the one-time ~440 MB model download. Zero API cost.

---

## `llama3_helper.py` — Llama 3 language tasks (Step 8, LLM)

The **only** module that calls the generative LLM, and only for *words*.

| Function | Purpose |
|---|---|
| `_chat(system, user)` | One OpenAI-compatible chat call with retry/backoff. Returns text or `None`. Respects `max_tokens=500`. |
| `_cached_chat(key, system, user)` | Wraps `_chat` with a **SQLite cache** so the same filing+task is never re-sent. |
| `generate_executive_summary(context, key)` | 6-sentence factual summary. |
| `extract_risk_factors(context, key)` | Top-5 risks as JSON `{risk, category, severity}`; robust JSON parsing. |
| `extract_guidance(context, key)` | 3-4 sentence forward-guidance summary. |
| `_safe_parse_json_array(text)` | Best-effort JSON-array extraction from the LLM's reply. |

If `LLAMA3_API_KEY` is unset, these return safe placeholder text instead of
crashing — the rest of the report still works.

---

## `signal_generator.py` — Bull/Bear signal (Step 8b)

| Function | Purpose |
|---|---|
| `_growth_to_score(pct)` | Maps a % change to [0,1] (0.5 = flat). |
| `_guidance_to_score(text)` | Lexical positive/negative scoring of guidance text. |
| `generate_signal(comp_summary, tone_score, guidance)` | **Entry point** — weighted blend of revenue (0.30), margin (0.25), tone (0.25), guidance (0.20) → score in [0,1] and a `BULLISH/BEARISH/NEUTRAL` label, with human-readable evidence. |

Thresholds: ≥0.60 BULLISH, ≤0.40 BEARISH, else NEUTRAL.

---

## `visualizer.py` — Charts (Step 10)

Uses matplotlib's headless `Agg` backend (works on a server).

| Function | Purpose |
|---|---|
| `kpi_bar_chart(df, ticker)` | Current vs previous KPI bars (normalised per KPI). |
| `tone_chart(tone, ticker)` | Positive/Neutral/Negative chunk counts. |
| `signal_chart(signal, ticker)` | Horizontal bars of the four signal components. |
| `generate_all_charts(df, tone, signal, ticker)` | Generates all three and returns their file paths. |

---

## `pdf_generator.py` — PDF report (Step 11)

ReportLab assembles the investor-grade report.

| Function | Purpose |
|---|---|
| `_styles()` | Paragraph styles (cover title, headings, body, disclaimer). |
| `generate_report(...)` | **Entry point** — builds all 9 sections: Cover, Executive Summary, KPI Comparison Table, KPI Chart, Management Tone, Forward Guidance, Top-5 Risks, Bull/Bear Signal, Disclaimer. Returns the PDF path. |
| `_kpi_table_flowable(df)` | Colour-coded KPI table (green up / red down). |
| `_risk_table_flowable(risks)` | Risk table with severity colour-coding. |

---

## `database.py` — SQLite storage + cache (Step 17)

| Function | Purpose |
|---|---|
| `init_db()` | Creates `analysis_results` and `llm_cache` tables (runs on import). |
| `get_llm_cache(key)` / `set_llm_cache(key, resp)` | Llama 3 response cache. |
| `save_analysis(record)` | Insert/replace a completed analysis (unique per ticker+form+accession). |
| `get_cached_analysis(ticker, form, accession)` | Returns a prior analysis for instant re-display. |
| `get_history(ticker, limit)` | Recent analyses for the sidebar. |
| `count_records()` | Total stored analyses. |

SQLite at prototype stage; PostgreSQL recommended for production / concurrency.

---

## `pipeline.py` — End-to-end orchestrator

`run_analysis(ticker, form_type, force, progress)` calls every stage in SRS
order, reports progress through an optional callback, short-circuits on cached
results, and returns one result dict with everything the UI/PDF needs. On
unrecoverable errors it returns `{"error": "..."}` so the UI degrades cleanly.

`_tone_input_chunks(...)` prepares digestible text chunks for FinBERT.

---

## `app.py` — Streamlit dashboard (Step 12)

| Function | Purpose |
|---|---|
| `sidebar()` | Ticker input, form select, force toggle, run button, history list, LLM-key warning. |
| `render_kpi_cards(kpis)` | Metric cards with % delta arrows. |
| `render_comparison_table(df)` | Colour-coded comparison table. |
| `render_signal_and_tone(signal, tone)` | Signal + tone panels. |
| `render_charts(charts)` | Embeds the matplotlib PNGs. |
| `render_results(result)` | Full result layout incl. PDF download button. |
| `main()` | Wires the sidebar to `pipeline.run_analysis` with a live progress bar. |

---

## `run_cli.py` — Headless runner

`python run_cli.py AAPL 10-K [--force]` runs the same pipeline without the UI
and prints a summary + PDF path. Ideal for testing and live demos.

# 03 — Module Reference

Every module in `src/genai_analyst/`, in pipeline order.
All modules import from `core/config.py` for settings; none hard-code values.

---

## core/config.py

Central configuration. Loads secrets from `.env` via `python-dotenv`,
resolves project paths (`BASE_DIR`, `DATA_DIR`, `CACHE_DIR`, `CHROMA_DIR`,
`REPORTS_DIR`, `CHARTS_DIR`, `DB_PATH`), creates directories at import time,
and defines all tunable parameters.

**Key constants:** `CHUNK_SIZE=2500`, `CHUNK_OVERLAP=250`, `RAG_TOP_K=5`,
`LLAMA3_MAX_TOKENS=500`, `LLAMA3_TEMPERATURE=0.2`,
`EMBEDDING_MODEL_NAME="all-MiniLM-L6-v2"`, `FINBERT_MODEL_NAME="ProsusAI/finbert"`,
`REQUEST_TIMEOUT=30`, `MAX_RETRIES=4`, `BACKOFF_BASE=1.5`.

**KPI_CONCEPTS dict** maps KPI name → list of XBRL us-gaap concept tags tried
in priority order (companies tag the same concept differently).

**Helper:** `is_llm_configured() → bool` — returns True if `LLAMA3_API_KEY`
is set.

---

## core/pipeline.py

End-to-end orchestrator. The single entry point for any analysis.

**`run_analysis(ticker, form_type="10-K", force=False, progress=None, accession=None) → dict`**

Calls every stage in order. Accepts an optional `progress(label, fraction)`
callback so the Streamlit dashboard can show a live progress bar. Returns a
result dict with keys: `filing`, `n_chunks`, `kpis`, `kpi_table`, `tone`,
`summary`, `risks`, `guidance`, `signal`, `charts`, `pdf_path`, `from_cache`.
On failure returns `{"error": "<message>"}`.

Short-circuits on a SQLite cache hit (unless `force=True`). The
`_result_from_cache()` helper reconstructs a full displayable result from the
stored row — KPIs, tone, signal, summary, guidance, risks are all persisted.
Charts are regenerated locally from saved KPIs (no network call).

**`_tone_input_chunks(contexts, sections)`** — extracts up to 40 paragraph-
length strings from the MD&A context for FinBERT.

---

## core/database.py

SQLite3 persistence and LLM response cache. Two tables:

**`analysis_results`** — one row per completed analysis. Key fields:
`ticker`, `company`, `form`, `accession`, `filing_date`, `tone_score`,
`tone_label`, `signal_score`, `signal_class`, `kpis_json`, `summary`,
`guidance`, `risks_json`, `pdf_path`, `created_at`. Unique constraint on
`(ticker, form, accession)`.

**`llm_cache`** — caches Llama 3 responses. Key: `cache_key` (filing + task),
value: `response` text. Prevents re-calling the API for the same filing.

**`_migrate(conn)`** — idempotent column-adder. Checks `PRAGMA table_info`
and adds `guidance` and `risks_json` columns to older databases without
losing data.

**Public functions:** `save_analysis(data)`, `get_cached_analysis(ticker, form, accession)`,
`get_history(limit=20)`, `count_records()`, `get_cached_llm_response(cache_key)`,
`save_llm_response(cache_key, response)`.

---

## ingestion/edgar_client.py

SEC EDGAR filing retrieval (Pipeline Step 2).

**`_get(url, as_json=True)`** — low-level HTTP helper with SEC `User-Agent`
header, `REQUEST_TIMEOUT=30s`, and up to `MAX_RETRIES=4` with exponential
backoff (`BACKOFF_BASE=1.5s`). Used by both this module and `kpi_extractor`.

**`ticker_to_cik(ticker) → str`** — downloads the SEC master ticker map
(`company_tickers.json`), caches it in `data/cache/`, returns the zero-padded
10-digit CIK.

**`list_filings(ticker, form_type) → list`** — fetches filing history from
`data.sec.gov/submissions/CIK{cik10}.json`, returns filings of the requested
form type, newest first.

**`get_latest_filing(ticker, form_type) → dict | None`** — returns the most
recent filing metadata dict.

**`download_filing_html(filing) → str`** — downloads the primary document HTML
and caches it in `data/cache/{ticker}_{form}_{accession}.html`.

**`ingest(ticker, form_type, accession=None) → dict | None`** — end-to-end
entry point. Returns a filing dict with keys `ticker`, `company`, `cik`,
`form`, `accession`, `filing_date`, `html`.

---

## ingestion/filing_parser.py

HTML parsing, text extraction and section segmentation (Pipeline Steps 3-4).

**`html_to_text(html) → str`** — strips HTML using BeautifulSoup4 + lxml
backend.

**`clean_text(text) → str`** — collapses whitespace, removes page artefacts,
strips XBRL tag blocks. Uses spaCy sentence segmentation when installed,
regex-only otherwise (graceful fallback).

**`segment_sections(text) → dict`** — locates MD&A, Risk Factors and
Financial Statements using regex heading patterns. Always includes a `"full"`
key as fallback so retrieval never has an empty corpus.

**`parse_filing(html) → dict`** — full entry point: `html_to_text` →
`clean_text` → `segment_sections`. Returns `{section_name: clean_text}`.

---

## rag/chunker.py

Semantic chunking (Pipeline Step 4).

**`_get_splitter()`** — returns a LangChain `RecursiveCharacterTextSplitter`
with `chunk_size=CHUNK_SIZE`, `chunk_overlap=CHUNK_OVERLAP`, separators
`["\n\n", "\n", ". ", " ", ""]`. Tries `langchain_text_splitters` first,
falls back to `langchain.text_splitter`.

**`chunk_sections(sections) → list[dict]`** — iterates named sections (skips
`"full"` when named sections have content); splits each section's text and
returns a list of `{text, section}` dicts.

---

## rag/indexer.py

Embedding generation + ChromaDB indexing (Pipeline Steps 5-6).

**`index_filing(filing, sections, force=False) → int`** — the main entry
point called by `pipeline.py`. If the collection already exists and
`force=False`, returns the existing chunk count immediately (cache hit). If
`force=True`, resets the collection first. Otherwise: calls
`chunker.chunk_sections()`, generates embeddings via `embedder.embed_texts()`,
persists via `vector_store.add_chunks()`. Returns the chunk count.

---

## rag/embedder.py

Sentence Transformer embedding model (Pipeline Step 5).

**`get_model()`** — lazy singleton loader. Loads `all-MiniLM-L6-v2` on first
call and caches it in `_MODEL`. Prints a loading message. Subsequent calls
return instantly.

**`embed_texts(texts) → list[list[float]]`** — converts a list of strings to
384-dimensional normalised dense vectors.

**`embed_query(text) → list[float]`** — single-string wrapper around
`embed_texts`.

---

## rag/vector_store.py

ChromaDB persistent vector storage (Pipeline Step 6).

**`get_client()`** — lazy singleton. Creates a `chromadb.PersistentClient`
rooted at `CHROMA_DIR`.

**`_collection_name(filing) → str`** — returns
`"{ticker}_{form}_{accession}"` (lowercased, cleaned).

**`collection_exists(filing) → bool`** — checks whether the collection exists
without creating it.

**`get_or_create_collection(filing)`** — creates or opens the collection with
cosine distance space.

**`add_chunks(filing, texts, embeddings, metadatas) → int`** — stores chunks
with their vectors and metadata; returns the chunk count.

**`query(filing, query_vector, top_k) → list[dict]`** — cosine similarity
search; returns Top-K results with `document`, `metadata`, `distance`.

**`reset_collection(filing)`** — deletes and recreates the collection
(used for force re-index).

---

## rag/retriever.py

RAG retrieval layer (Pipeline Step 7).

**`QUERY_TEMPLATES`** — dict of four per-task natural-language queries:
`executive_summary`, `risk_factors`, `guidance`, `tone`.

**`retrieve(filing, query_text, top_k) → list[dict]`** — embeds the query
and searches ChromaDB.

**`retrieve_context(filing, query_text, top_k) → str`** — joins the top-K
chunk texts into one context string separated by `"\n\n---\n\n"`.

**`retrieve_all_contexts(filing) → dict`** — runs `retrieve_context` for all
four `QUERY_TEMPLATES` and returns a `{task: context_str}` dict.

---

## nlp/sentiment.py

FinBERT management tone analysis (Pipeline Step 8a).

**`get_pipeline()`** — lazy singleton. Loads `ProsusAI/finbert` via
HuggingFace `pipeline("text-classification")` with `truncation=True`,
`max_length=512`. Prints a loading message.

**`analyze_chunks(chunks) → list[dict]`** — classifies all chunks in a single
batched call (`batch_size=16`). Falls back to chunk-by-chunk on batch failure.
Returns `[{label, score, text_preview}]`.

**`aggregate_tone(chunk_results) → dict`** — computes a weighted polarity
score: positive chunks add confidence, negative subtract, neutral are neutral.
Maps to `tone_score` in [0, 1] where 1.0 = maximally positive. Returns
`{tone_score, label, positive, negative, neutral, total}`.

**`analyze(chunks) → dict`** — convenience entry point. Returns the aggregate
dict plus `"chunks": [per-chunk results]`.

---

## nlp/generation.py

Llama 3 language generation via Groq API (Pipeline Step 8b).

**`_chat(system_prompt, user_prompt) → str | None`** — core API call.
POSTs to `LLAMA3_BASE_URL` with `LLAMA3_MODEL`, `LLAMA3_MAX_TOKENS=500`,
`LLAMA3_TEMPERATURE=0.2`. Retries with exponential backoff. Returns `None`
if no key configured. Checks `database.get_cached_llm_response()` first and
saves responses to `database.save_llm_response()`.

**`generate_executive_summary(context, cache_key) → str`** — returns a
concise executive summary. Falls back to placeholder if LLM unavailable.

**`extract_risk_factors(context, cache_key) → list[dict]`** — prompts for
JSON output (`[{category, description, severity}]`). Parses the JSON; returns
a list of dicts. Falls back to `[]` on error.

**`extract_guidance(context, cache_key) → str`** — returns a forward-guidance
interpretation. Falls back to placeholder.

---

## analysis/kpi_extractor.py

EDGAR XBRL financial KPI extraction (Pipeline Step 7b).

**`_fetch_concept(cik10, concept) → dict | None`** — fetches one us-gaap
XBRL concept using `edgar_client._get()`.

**`_duration_days(row) → int | None`** — computes `(end_date − start_date)`
in days. Returns `None` for instant facts (no `start` key).

**`_same_bucket(days, form) → bool`** — returns True if the period duration
matches the form: 330–400 days for 10-K (annual), 60–120 days for 10-Q
(quarterly). Filters out YTD figures from 10-Q responses.

**`_extract_period_values(concept_data, form) → list[dict]`** — flattens
XBRL units into rows, filters to the right duration bucket, deduplicates by
end date, sorts newest-first. Falls back to unfiltered if bucketing empties
the list.

**`extract_kpis(cik10, form) → dict`** — iterates `config.KPI_CONCEPTS`,
tries each concept tag in priority order, picks current and previous periods.
Calls `_add_gross_margin()` at the end.

**`_add_gross_margin(results)`** — derives `GrossMargin` (%) from
`GrossProfit / Revenue × 100`. Sets `unit="PERCENT"`. Handles zero-revenue
gracefully.

**`format_kpi_value(value, unit) → str`** — formats for display:
`PERCENT` → `"46.21%"`, `USD` → `"$416.16B"` / `"$45.18M"` / `"$1,234"`,
`USD/shares` → `"6.13"`, `None` → `"N/A"`.

---

## analysis/comparison_engine.py

KPI period-over-period comparison (Pipeline Step 9).

**`_pct_change(current, previous) → float | None`** — safe percentage change;
returns `None` if either value is missing or `previous == 0`.

**`build_comparison(kpis) → pd.DataFrame`** — iterates the KPI dict and
builds a DataFrame with columns: `KPI`, `Current`, `Previous`, `Change %`,
`Direction` (▲/▼/—), `Trend` (▲/▼/→), `_current_value`, `_previous_value`,
`_change_value` (raw floats for the signal engine).

**`comparison_summary(df) → dict`** — extracts named growth figures from the
DataFrame: `revenue_growth`, `net_income_growth`, `eps_growth`,
`gross_profit_growth`, `operating_income_growth`. Feeds `signal_generator`.

---

## analysis/signal_generator.py

Bull/Bear signal computation (Pipeline Step 8b-signal).

**Weights:** `revenue=0.30`, `margin=0.25`, `tone=0.25`, `guidance=0.20`.

**`_growth_to_score(pct, cap=25.0) → float`** — maps a % change to 0–1
(0.5 = flat, capped at ±25%).

**`_guidance_score(text) → float`** — keyword-based: positive terms → >0.5,
negative terms → <0.5, neutral → 0.5.

**`generate_signal(comp_summary, tone_score, guidance_text) → dict`** —
computes each component score, applies weights, combines into a final 0–1
`score`. Classifies: ≥0.6 = BULLISH, ≤0.4 = BEARISH, else NEUTRAL. Returns
`{score, classification, evidence: [{component, score, weight, contribution}]}`.

---

## output/visualizer.py

matplotlib chart generation (Pipeline Step 10).

Uses `matplotlib.use("Agg")` — headless, no GUI needed.

**`plot_kpi_chart(kpi_table, ticker) → Path | None`** — bar chart of current
vs previous KPI values, normalised to previous period. Saves to
`data/charts/{ticker}_kpi.png`.

**`plot_tone_chart(tone, ticker) → Path | None`** — bar chart of Positive /
Neutral / Negative chunk counts. Saves to `data/charts/{ticker}_tone.png`.

**`plot_signal_chart(signal, ticker) → Path | None`** — horizontal bar chart
of signal component contributions. Saves to `data/charts/{ticker}_signal.png`.

**`generate_all_charts(kpi_table, tone, signal, ticker) → dict`** — calls all
three and returns `{kpi: path, tone: path, signal: path}`.

---

## output/pdf_generator.py

ReportLab investor-grade PDF report (Pipeline Step 11).

**`generate_report(filing, kpi_table, tone, summary, guidance, risks, signal, charts) → str`**
— assembles a multi-section A4 PDF with nine sections:
1. Cover page (company, ticker, form, date, generated timestamp)
2. Executive Summary
3. KPI Comparison Table (shaded header, all KPIs from the DataFrame)
4. Revenue / KPI Trend Chart (embedded PNG)
5. Management Tone Analysis (score, label, breakdown bar chart PNG)
6. Forward Guidance (Llama 3 output)
7. Top-5 Risk Factors (category, description, severity)
8. Bull/Bear Signal (score, classification, evidence table)
9. Disclaimer

Saves to `data/reports/{ticker}_{form}_analysis.pdf`. Returns the path.

---

## dashboard.py

Full Streamlit analysis UI.

**`main()`** — entry point called by `app.py`. Injects CSS via
`inject_css()`, renders `render_sidebar()` and `render_results()`.

**`render_sidebar()`** — company picker (searchable by name or ticker, format
`"Company Name  ·  TICKER"`), filing type selector (10-K / 10-Q), force
re-analysis checkbox, Run Analysis button. Stores the result in
`st.session_state["result"]`.

**`render_results(result)`** — displays the full analysis: green/red status
banner, KPI metric cards (Revenue, NetIncome, EPS, GrossProfit, GrossMargin,
OperatingIncome) with % change arrows, KPI comparison table, side-by-side
Bull/Bear signal and Management Tone panels, three embedded chart images, PDF
download button, Executive Summary, Forward Guidance, Top Risk Factors.

**`_company_options()`** — `@st.cache_data` decorated. Calls
`edgar_client.list_companies()` and builds `(labels, label_to_ticker)`.
Labels sorted alphabetically by company name.

---

## landing.py

Marketing landing page with theme support.

**`render()`** — checks `st.session_state["landing_theme"]` (default: Dark).
Renders a System / Light / Dark radio selector, injects the matching CSS
palette, then renders: hero section with a live ticker tape, "How it works"
step guide, and pricing cards (Student ₹0, Analyst ₹2,499/mo, Desk ₹7,999/mo).
"Try it now →" and "Buy" buttons set `st.session_state["view"] = "app"`.

**Palettes:** `_DARK` and `_LIGHT` dicts define all colours. System mode uses
a `@media (prefers-color-scheme)` CSS media query.

---

## app.py

Root Streamlit launcher.

Adds `src/` to `sys.path`, calls `st.set_page_config()` once (title
`"GenAI Financial Earnings Report Analyst"`, icon 📊, wide layout), initialises
`st.session_state["view"] = "landing"`, then routes:
- `view == "landing"` → `landing.render()`
- anything else → `dashboard.main()`

Run with: `streamlit run app.py` (from project root, not from `src/`).

---

## run_cli.py

Headless command-line runner.

```
python run_cli.py AAPL 10-K
python run_cli.py MSFT 10-Q --force
```

Parses `ticker`, `form` (default `10-K`), `--force` flag via `argparse`.
Calls `pipeline.run_analysis()` and prints company, form, tone, signal, PDF
path and a 300-char summary preview to stdout.

---

## tests/test_smoke.py

Nine offline unit tests (no network, no ML models):

1. `test_paths_defined` — `config.BASE_DIR` and `config.DB_PATH` are not None.
2. `test_is_llm_configured_returns_bool` — `is_llm_configured()` returns bool.
3. `test_kpi_concepts_present` — all five KPIs declared in `KPI_CONCEPTS`.
4. `test_kpi_value_formatting` — `$416.16B`, `$45.18M`, `6.13`, `N/A`.
5. `test_gross_margin_derivation` — 180/400×100 = 45.0%, zero-revenue → None.
6. `test_period_matching_by_duration` — 6-month YTD excluded from 10-Q results.
7. `test_comparison_percentage_change` — 100→120 = +20%, divide-by-zero → None.
8. `test_signal_bullish_on_strong_positives` — strong inputs → BULLISH.
9. `test_signal_neutral_on_missing_data` — empty inputs → NEUTRAL.

Run: `pytest tests/test_smoke.py -v`

# 01 — Architecture & Design

## End-to-end pipeline (17 stages)

The orchestrator (`core/pipeline.py`) drives every stage in sequence and
returns a single result dict to the UI. The exact order from the code:

```
Stage  Module                        What it does
─────  ────────────────────────────  ────────────────────────────────────────────
 1     edgar_client.ingest()         Resolve ticker → CIK, find latest filing,
                                     download + cache primary HTML document
 2-4   filing_parser.parse_filing()  Strip HTML (BeautifulSoup4), remove boilerplate,
                                     segment MD&A / Risk Factors / Financials
 4     chunker.chunk_sections()      Split sections into ~500-word overlapping chunks
                                     (LangChain RecursiveCharacterTextSplitter,
                                      CHUNK_SIZE=2500 chars, CHUNK_OVERLAP=250)
 5-6   indexer.index_filing()        Generate 384-dim vectors (Sentence Transformers
                                     all-MiniLM-L6-v2) and persist to ChromaDB;
                                     skip-if-indexed cache hit returns immediately
 7     retriever.retrieve_all_       Top-K=5 cosine similarity search for four
       contexts()                    per-task queries: executive_summary, risk_factors,
                                     guidance, tone
 7b    kpi_extractor.extract_kpis()  Query SEC XBRL API for each KPI concept tag;
                                     duration-aware period matching (annual ≈365d,
                                     quarterly ≈90d); derive GrossMargin from XBRL
       comparison_engine.build_      Build pandas DataFrame: Current, Previous,
       comparison()                  Change %, Direction, Trend per KPI
 8a    sentiment.analyze()           FinBERT batch-classifies up to 40 MD&A chunks;
                                     aggregates to 0–1 tone score + Positive/Neutral/
                                     Negative label
 8b    generation.*()                Llama 3 via Groq: executive summary (500 tok),
                                     top-5 risk factors (JSON), forward guidance;
                                     SQLite LLM cache checked first
 8b    signal_generator.generate_    Weighted blend: revenue 30%, margin 25%,
       signal()                      tone 25%, guidance 20% → 0–1 score →
                                     BULLISH / NEUTRAL / BEARISH
 10    visualizer.generate_all_      matplotlib Agg: KPI bar chart, tone breakdown,
       charts()                      signal components → PNGs in data/charts/
 11    pdf_generator.generate_       ReportLab PDF: cover, summary, KPI table,
       report()                      charts, tone, guidance, risks, signal, disclaimer
 17    database.save_analysis()      Persist full result to SQLite analysis_results;
                                     LLM responses cached in llm_cache table
```

## Module dependency graph

```
app.py
  ├── landing.py          (landing page UI)
  └── dashboard.py        (analysis UI)
        └── core/pipeline.py     (orchestrator)
              ├── ingestion/edgar_client.py
              ├── ingestion/filing_parser.py
              ├── rag/chunker.py
              ├── rag/indexer.py
              │     ├── rag/embedder.py
              │     └── rag/vector_store.py
              ├── rag/retriever.py
              │     └── rag/embedder.py
              ├── analysis/kpi_extractor.py
              ├── analysis/comparison_engine.py
              ├── nlp/sentiment.py
              ├── nlp/generation.py
              ├── analysis/signal_generator.py
              ├── output/visualizer.py
              ├── output/pdf_generator.py
              └── core/database.py
```

All modules depend on `core/config.py` — no other module hard-codes any value.

## Key design decisions

### Why RAG instead of sending the full filing?
A 10-K can exceed 200 pages. Sending it all to the LLM would cost thousands
of tokens and increase hallucination. RAG retrieves only the Top-K=5 chunks
most relevant to each question, keeping the context small and the answers
grounded in source text.

### Why XBRL for financial figures?
Extracting numbers from free-form HTML is fragile and error-prone. The SEC
EDGAR XBRL API provides structured, tagged financial data for every public
company. KPIs come from XBRL — not the LLM, not HTML scraping. This is the
Golden Rule and is enforced architecturally.

### Why duration-aware period matching in KPI extraction?
XBRL for a 10-Q contains both 3-month (quarterly) and 6-/9-month
year-to-date figures with similar end dates. Without duration matching, the
engine compares mismatched periods and reports inflated growth (e.g. +77%
instead of the real +17%). The extractor filters to ≈365-day periods for
10-K and ≈90-day periods for 10-Q before computing deltas.

### Why Groq instead of local Llama 3?
Running Llama 3 locally requires substantial GPU memory. Groq provides a
free-tier, OpenAI-compatible `/v1/chat/completions` endpoint at low latency.
The provider is configured entirely through environment variables
(`LLAMA3_API_KEY`, `LLAMA3_BASE_URL`, `LLAMA3_MODEL`) — swapping providers
requires no code change.

### Why skip-if-indexed caching in the indexer?
Embedding a full filing takes 15–30 seconds. The indexer checks whether a
ChromaDB collection already exists for a `ticker_form_accession` key before
running. Cache hits return the chunk count instantly. A `force=True` flag
resets and rebuilds.

### Why SQLite for storage?
Zero-config, file-based, sufficient for a single-user prototype. The schema
includes an idempotent `_migrate()` function that adds new columns to existing
databases without losing rows, so upgrades are non-destructive. PostgreSQL is
recommended for production.

### Why lazy model loading?
Both FinBERT (~440 MB) and the embedding model load on first use via
module-level singletons (`_PIPELINE`, `_MODEL`). This keeps app startup fast
and avoids loading heavy models when only the landing page is shown.

## Data flow summary

| Stage | Input | Output |
|-------|-------|--------|
| Ingestion | ticker + form type | filing dict (metadata + raw HTML) |
| Parsing | raw HTML | `{section_name: clean_text}` dict |
| Chunking | sections dict | list of `{text, section}` dicts |
| Embedding + indexing | chunks | ChromaDB collection (persistent) |
| Retrieval | 4 task queries | `{task: top-K context string}` dict |
| XBRL KPI | CIK + form type | `{KPI: {current, previous, unit, ...}}` |
| Comparison | KPI dict | pandas DataFrame with Change %, Direction |
| FinBERT | text chunks (up to 40) | `{tone_score, label, positive, negative, neutral}` |
| Llama 3 | retrieved context | summary str, risks list, guidance str |
| Signal | comparison summary + tone + guidance | `{score, classification, evidence}` |
| Visualizer | KPI table + tone + signal | PNG paths dict |
| PDF | all outputs | PDF file path |
| SQLite | full result dict | persisted row + LLM cache entries |

## Configuration reference (core/config.py)

| Constant | Value | Purpose |
|----------|-------|---------|
| `CHUNK_SIZE` | 2500 | Characters per chunk (~500 words) |
| `CHUNK_OVERLAP` | 250 | Overlap between consecutive chunks |
| `RAG_TOP_K` | 5 | Chunks retrieved per task query |
| `LLAMA3_MAX_TOKENS` | 500 | Max LLM output tokens (cost control) |
| `LLAMA3_TEMPERATURE` | 0.2 | Low temperature → deterministic output |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | Sentence Transformers model |
| `FINBERT_MODEL_NAME` | `ProsusAI/finbert` | HuggingFace FinBERT model |
| `REQUEST_TIMEOUT` | 30s | HTTP timeout for all external calls |
| `MAX_RETRIES` | 4 | Retry attempts on transient failures |
| `BACKOFF_BASE` | 1.5s | Exponential backoff base |

# 01 — Architecture & Data Flow

This document explains *how* the system is put together and *why* each piece
exists.

## 1. The pipeline at a glance

```
  ┌────────────┐
  │  1. Ticker │  user types "AAPL" in Streamlit
  └─────┬──────┘
        ▼
  ┌──────────────────────────┐
  │ 2. SEC EDGAR Ingestion   │  edgar_downloader.py
  │  ticker → CIK → filing   │  (Submissions API, downloads 10-K/10-Q HTML)
  └─────┬────────────────────┘
        ▼
  ┌──────────────────────────┐
  │ 3-4. Parse + Clean        │  parser.py
  │  HTML → text → sections   │  (BeautifulSoup4; MD&A / Risk / Financials)
  └─────┬────────────────────┘
        ▼
  ┌──────────────────────────┐        ┌─────────────────────────────┐
  │ 5. Chunk (LangChain)      │        │   RAG SUBSYSTEM             │
  │  ~500-word pieces         │───────▶│ 6. Embed (Sentence-Transf.) │
  └──────────────────────────┘        │ 7. Store  (ChromaDB)        │
                                       │ 8. Retrieve (Top-K cosine)  │
        ┌──────────────────────────────┴─────────────────────────────┘
        ▼ retrieved context chunks
  ┌──────────────────────────┐   ┌──────────────────────────┐
  │ 9. XBRL KPI Extraction   │   │ 10. FinBERT Tone (local) │
  │  (exact numbers)         │   │  Positive/Neg/Neutral    │
  └─────┬────────────────────┘   └─────┬────────────────────┘
        │                              │
        ▼                              ▼
  ┌──────────────────────────────────────────────┐
  │ 11. Llama 3 — Summary / Risks / Guidance     │  llama3_helper.py
  └─────┬────────────────────────────────────────┘
        ▼
  ┌──────────────────────────┐
  │ 12. Bull/Bear Signal     │  signal_generator.py
  │  blends growth+tone+guid │
  └─────┬────────────────────┘
        ▼
  ┌──────────────────────────┐
  │ 13. KPI Comparison       │  comparison_engine.py (pandas)
  │ 14. Charts               │  visualizer.py (matplotlib)
  │ 15. PDF Report           │  pdf_generator.py (ReportLab)
  │ 16. Save to SQLite       │  database.py
  └─────┬────────────────────┘
        ▼
  ┌──────────────────────────┐
  │ 17. Streamlit Dashboard  │  app.py — cards, table, charts, download
  └──────────────────────────┘
```

`pipeline.py` is the conductor that calls every stage in order. `app.py` calls
`pipeline.run_analysis()` and renders the result.

## 2. Why Retrieval-Augmented Generation (RAG)?

A 10-K can be **150+ pages**. We cannot (and should not) paste the whole thing
into Llama 3 because:

1. **Token limits & cost** — large prompts are expensive and slow.
2. **Hallucination** — the more irrelevant text we include, the more the model
   drifts off-topic.

RAG solves this by *retrieving only the relevant slices* of the filing for each
question:

- We split the filing into chunks and embed each into a 384-dimensional vector.
- We store those vectors in ChromaDB.
- For a question like *"What are the main risks?"*, we embed the question and ask
  ChromaDB for the **Top-K** most similar chunks (cosine similarity).
- Only those few chunks go to Llama 3.

Result: lower cost, lower latency, fewer hallucinations, better grounding.

### What is an embedding? (plain English)

An embedding is a list of numbers that captures the *meaning* of a piece of
text. Texts with similar meaning have vectors that point in similar directions.
"Revenue grew sharply" and "Sales increased significantly" land close together
even though they share no words. `all-MiniLM-L6-v2` produces 384 numbers per
text and runs locally for free.

### What is a vector database?

A specialised store that, given a query vector, can quickly find the stored
vectors closest to it. We use **ChromaDB**, which persists to disk so the index
survives restarts. Each filing gets its own collection so companies never mix.

## 3. The two-model split

| Task | Model | Where it runs | Cost |
|------|-------|---------------|------|
| Management tone (Positive/Neg/Neutral) | **FinBERT** | Locally (CPU/GPU) | Free |
| Executive summary, risks, guidance | **Llama 3** | Remote API (Groq) | Free tier |
| **Financial numbers** | *No model* — XBRL API | Remote (SEC) | Free |

FinBERT is a finance-tuned BERT model; it's small enough to run on any laptop
with ≥8 GB RAM. Llama 3 is a large generative model, so we call a hosted free
endpoint instead of running it locally.

## 4. Data sources (all free, all public)

- **SEC EDGAR Submissions API** — `https://data.sec.gov/submissions/CIK##########.json`
  → company name + list of filings (form type, date, accession, primary doc).
- **SEC EDGAR XBRL Company-Concept API** —
  `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/<Concept>.json`
  → structured time series of a financial concept (e.g. `Revenues`, `NetIncomeLoss`).
- **SEC Archives** — the actual filing HTML document.
- **Company-tickers map** — `https://www.sec.gov/files/company_tickers.json`
  → resolves a ticker symbol to its CIK number.

> SEC requires a descriptive `User-Agent` header (your name + email). It is set
> from the `SEC_USER_AGENT` env var. Without it, SEC may block your requests.

## 5. Resilience & cost controls (designed-in)

- **Retry with exponential backoff** on every external API call
  (`edgar_downloader._get`, `llama3_helper._chat`).
- **Graceful nulls** — a missing KPI or section never crashes the run; it shows
  `N/A`.
- **SQLite caching** — both completed analyses and individual Llama 3 responses
  are cached, so re-running the same filing is instant and makes **zero** API calls.
- **`max_tokens = 500`** caps Llama 3 output length.
- **Only retrieved chunks** (not the whole filing) are ever sent to Llama 3.

## 6. Storage layout (created at runtime under `data/`)

```
data/
├── cache/      # raw filing HTML + the ticker→CIK map (re-used across runs)
├── chroma/     # ChromaDB persistent vector store
├── charts/     # generated matplotlib PNGs
├── reports/    # generated PDF reports
└── analyst.db  # SQLite database (history + LLM cache)
```

This whole folder is git-ignored — it is regenerated on demand.

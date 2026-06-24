# 01 — Architecture & Design

## System architecture (Sprint 1)

The system implements Steps 1–8 of the SRS architecture flowchart as a linear
pipeline with one module per stage:

```
   [ User enters ticker ]
            │
            ▼
   1-2  SEC EDGAR ingestion        ── ingestion/edgar_client.py
            │   (fetch latest 10-K / 10-Q HTML)
            ▼
   3-4  HTML parse + clean + segment ── ingestion/filing_parser.py
            │   (Risk Factors, MD&A, Financials)
            ▼
   4    Semantic chunking          ── rag/chunker.py
            │   (LangChain, ~2500 chars, 250 overlap)
            ▼
   5    Embedding generation       ── rag/embedder.py
            │   (Sentence Transformers, 384-dim)
            ▼
   6    Vector store               ── rag/vector_store.py
            │   (ChromaDB, per-filing collection)
            ▼
   7    RAG retrieval              ── rag/retriever.py
            │   (Top-K cosine, per-task queries)
            ▼
   8a   FinBERT sentiment          ── nlp/sentiment.py
   8b   Llama 3 summary/risk/guide ── nlp/generation.py
            │
            ▼
   [ Streamlit dashboard ]         ── dashboard.py
```

The orchestration lives in `core/pipeline.py`, which calls each stage in order
and returns a single result dictionary.

## Key design decisions

**Why RAG?** A filing can be 100+ pages. Sending the whole document to the LLM
would be expensive and increase hallucination. Instead we retrieve only the
Top-K most relevant chunks per task, which controls cost and improves accuracy.

**Why section-aware chunking?** The parser first segments the filing into named
sections (Risk Factors, MD&A, Financials) before chunking. This keeps each
chunk topically coherent and improves retrieval precision over naive
fixed-window chunking.

**Why per-filing ChromaDB collections?** Each filing gets its own collection
keyed by `ticker_form_accession`. If the same filing is analysed again, the
existing index is reused instead of re-embedding — a simple, effective cache.

**Why a `src/` layout?** Placing the package under `src/` is an industry
standard that prevents accidental imports of the local working directory and
makes the project installable and testable in isolation.

**Why lazy model loading?** The embedding model, FinBERT, and ChromaDB are all
loaded on first use (not at import time), so the dashboard starts quickly and
heavy models are only initialised when an analysis actually runs.

## Data flow summary

| Stage | Input | Output |
|-------|-------|--------|
| Ingestion | ticker, form type | filing metadata + raw HTML |
| Parsing | raw HTML | section → text map |
| Chunking | sections | list of chunks |
| Embedding | chunk texts | 384-dim vectors |
| Vector store | chunks + vectors | persistent ChromaDB collection |
| Retrieval | task query | Top-K relevant chunks |
| Sentiment | text chunks | tone label + score |
| Generation | retrieved context | summary, risks, guidance |

## Resilience & cost controls

* All SEC and LLM calls retry with exponential backoff.
* Only retrieved chunks (never the full filing) are sent to the LLM.
* LLM responses are capped at 500 tokens.
* If no LLM key is configured, the pipeline returns clear placeholders instead
  of crashing.
* The parser always provides a `Full Document` fallback so retrieval never has
  an empty corpus.

# 05 — Team & Sprint Plan

## Sprint structure

The project follows the **Scrum** framework over two sprints, each aligned to a
review checkpoint.

| Sprint | Review | Scope (SRS steps) |
|--------|--------|-------------------|
| Sprint 1 | Mid-semester | Steps 1–8: ingestion, RAG, FinBERT, Llama 3, dashboard |
| Sprint 2 | End-semester | Steps 9–12: KPI comparison, charts, PDF, full dashboard, deployment |

## Sprint 1 deliverables (this submission)

| SRS function | Module |
|--------------|--------|
| 1. SEC Filing Ingestion | `ingestion/edgar_client.py` |
| 2. HTML Parsing & Extraction | `ingestion/filing_parser.py` |
| 3. Text Cleaning & Chunking | `ingestion/filing_parser.py`, `rag/chunker.py` |
| 4. Sentence Transformer Embedding | `rag/embedder.py` |
| 5. ChromaDB Vector Storage | `rag/vector_store.py` |
| 6. RAG Retrieval | `rag/retriever.py` |
| 7. FinBERT Sentiment | `nlp/sentiment.py` |
| 8. Executive Summary / Risk / Guidance | `nlp/generation.py` |
| Dashboard (basic) | `dashboard.py` |
| Orchestration | `core/pipeline.py` |
| RAG indexing (chunk→embed→store) | `rag/indexer.py` |

## Team ownership (Sprint 1)

The division gives every member real backend work **and** at least one component
of the RAG subsystem — the core technical contribution of Sprint 1.

| Member | Modules owned | RAG component | Pipeline area |
|--------|---------------|---------------|---------------|
| **Hitesh** | `edgar_client.py`, `filing_parser.py`, `core/config.py`, `core/pipeline.py`, `rag/chunker.py` | Chunking | Data ingestion + integration + KT docs |
| **Anandita** | `rag/embedder.py`, `rag/indexer.py` | Embedding | RAG embedding + indexing |
| **Ruchi** | `rag/retriever.py`, `nlp/sentiment.py`, `nlp/generation.py` | Retrieval | RAG retrieval + NLP models |
| **Rupali** | `rag/vector_store.py`, `dashboard.py` | Vector store | Vector storage + frontend |

### Demo flow (follows the data through the pipeline)

1. **Hitesh** — ingest filing → parse → chunk (Steps 1–4)
2. **Anandita** — embed chunks → index into the store (Step 5)
3. **Rupali** — ChromaDB vector store holds the vectors (Step 6)
4. **Ruchi** — retrieve Top-K context → FinBERT tone → Llama 3 output (Steps 7–8)
5. **Rupali** — results shown on the Streamlit dashboard

## Sprint 2 plan (end-semester)

| SRS function | Planned module | Owner |
|--------------|----------------|-------|
| 9. KPI Comparison | `analysis/comparison.py` | Anandita |
| 10. Chart Generation | `output/visualizer.py` | Ruchi |
| 11. PDF Report | `output/report.py` | Rupali |
| 12. Full Dashboard | `dashboard.py` (extended) | Rupali |
| Bull/Bear Signal | `analysis/signal.py` | Rupali |
| History & Analytics | `core/database.py` | Anandita |
| RAG evaluation + deployment | — | Hitesh |

Each member therefore carries a comparable load in **both** reviews: a Sprint 1
module set plus a distinct Sprint 2 deliverable.

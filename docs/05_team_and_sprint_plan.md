# 05 — Team & Sprint Plan

## Team

| Member | PRN | Role |
|--------|-----|------|
| Hitesh Lokhande | 260250125043 | Data pipeline, XBRL KPI extraction, landing page, integration lead |
| Aanandita Yedulla | 260250125096 | RAG embedding, SQLite persistence, KPI comparison engine |
| Ruchi Rathore | 260250125067 | RAG retrieval, FinBERT tone, Llama 3 generation, visualizer |
| Rupali Saolikar | 260250125068 | ChromaDB vector store, Streamlit dashboard, Bull/Bear signal, PDF report |

**Project Guide:** Aditya Arsh, C-DAC Bangalore
**Course:** PG Certificate in Big Data Analytics (PGCP-BDA), Feb 2026 Batch

## Sprint structure (Agile / Scrum)

| Sprint | Review | Scope |
|--------|--------|-------|
| Sprint 1 | Mid-semester | Steps 1–8: ingestion, RAG, FinBERT, Llama 3, basic dashboard |
| Sprint 2 | End-semester | Steps 9–17: XBRL KPIs, comparison, signal, charts, PDF, history, landing |

## Sprint 1 deliverables

| Module | Owner | Responsibility |
|--------|-------|----------------|
| `ingestion/edgar_client.py` | Hitesh | SEC EDGAR retrieval, CIK resolution, HTML download + cache |
| `ingestion/filing_parser.py` | Hitesh | HTML parsing, text cleaning, section segmentation |
| `core/config.py` | Hitesh | Central configuration, paths, model names, KPI concepts |
| `core/pipeline.py` | Hitesh | End-to-end orchestrator, progress callbacks, cache hit path |
| `rag/chunker.py` | Hitesh | LangChain semantic chunking, section-aware splitting |
| `rag/indexer.py` | Hitesh | chunk→embed→store, skip-if-indexed caching |
| `rag/embedder.py` | Aanandita | Sentence Transformer model singleton, embed_texts, embed_query |
| `rag/vector_store.py` | Rupali | ChromaDB persistent store, add/query/reset operations |
| `rag/retriever.py` | Ruchi | Top-K retrieval, per-task query templates, retrieve_all_contexts |
| `nlp/sentiment.py` | Ruchi | FinBERT batched sentiment, tone score aggregation |
| `nlp/generation.py` | Ruchi | Llama 3 via Groq, summary/risks/guidance, LLM cache |
| `dashboard.py` (basic) | Rupali | Streamlit UI: sidebar, progress bar, basic results display |
| `app.py` | Rupali | Root launcher, page config, landing ↔ dashboard router |
| `run_cli.py` | Aanandita | Headless CLI runner with argparse |

## Sprint 2 deliverables

| Module | Owner | Responsibility |
|--------|-------|----------------|
| `analysis/kpi_extractor.py` | Hitesh | XBRL KPI extraction, duration-based period matching, GrossMargin derivation |
| `landing.py` | Hitesh | Marketing landing page, System/Light/Dark theme, pricing cards |
| `core/database.py` | Aanandita | SQLite analysis history, LLM response cache, idempotent migration |
| `analysis/comparison_engine.py` | Aanandita | pandas period-over-period comparison, direction arrows |
| `analysis/signal_generator.py` | Aanandita + Rupali | Weighted Bull/Bear signal (shared) |
| `output/pdf_generator.py` | Aanandita + Ruchi | ReportLab 9-section PDF report (shared) |
| `output/visualizer.py` | Ruchi | matplotlib charts: KPI, tone, signal |
| `dashboard.py` (full Sprint 2) | Rupali | KPI cards, comparison table, signal, charts, PDF download, history |

## Final module ownership

| Member | Modules | Lines |
|--------|---------|-------|
| **Hitesh** | `edgar_client`, `filing_parser`, `config`, `pipeline`, `chunker`, `indexer`, `kpi_extractor`, `landing` | 1,278 |
| **Aanandita** | `embedder`, `database`, `comparison_engine`, `signal_generator`*, `pdf_generator`*, `run_cli` | 782 |
| **Ruchi** | `retriever`, `sentiment`, `generation`, `visualizer`, `pdf_generator`* | 698 |
| **Rupali** | `vector_store`, `dashboard`, `app`, `signal_generator`* | 982 |

*shared — both members contributed

`theme.py` — shared utility (no individual owner).

Every member owns at least one RAG-subsystem module:
- Hitesh → chunking + indexing
- Aanandita → embedding
- Ruchi → retrieval
- Rupali → vector store

## Demo flow (follows the data through the pipeline)

1. **Hitesh** — ingest filing from SEC EDGAR → parse HTML → chunk sections
   → extract XBRL KPIs → period-over-period comparison
2. **Aanandita** — embed chunks → index in ChromaDB → compute comparison
   table → Bull/Bear signal (shared)
3. **Rupali** — ChromaDB vector store holds embeddings → full Streamlit
   dashboard renders KPI cards, charts, PDF download → Bull/Bear signal (shared)
4. **Ruchi** — retrieve Top-K context → FinBERT tone analysis → Llama 3
   summary, risks, guidance → matplotlib charts
5. **Rupali** — user downloads PDF; analysis cached in SQLite for instant
   reload; history visible in sidebar

## Git version control

Repository: https://github.com/hiteshlokhande09/genai-earnings-analyst

Branch strategy: each member works on a named feature branch and raises a
Pull Request merged to `main`:
- `hitesh/fix-kpi-indexer-landing` — Sprint 2 KPI extractor, indexer, landing
- `anandita/sprint2-modules` — embedding, database, comparison, signal, PDF, CLI
- `ruchi/sprint2-modules` — retriever, sentiment, generation, visualizer, PDF
- `rupali/sprint2-modules` — vector store, dashboard, app, signal

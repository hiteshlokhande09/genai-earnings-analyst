# 08 — Extending the Project

This is the roadmap for anyone who wants to **continue** the project after the
reviews — adding features, hardening it, or moving toward production. The
codebase is deliberately modular (one file per pipeline stage) so most additions
touch only one or two files.

---

## Where to plug things in

| You want to… | Touch this file |
|--------------|-----------------|
| Support a new filing type or source | `edgar_downloader.py` |
| Improve section detection | `parser.py` (`segment_sections`) |
| Add/replace a KPI | `config.py` (`KPI_CONCEPTS`) + `kpi_extractor.py` |
| Change chunking strategy | `config.py` (`CHUNK_SIZE`, `CHUNK_OVERLAP`) + `langchain_pipeline.py` |
| Swap the embedding model | `embedding_generator.py` |
| Change the vector DB | `vector_store.py` |
| Tune RAG queries / Top-K | `rag_retriever.py` (`QUERY_TEMPLATES`) + `config.RAG_TOP_K` |
| Change the LLM or prompts | `llama3_helper.py` |
| Adjust the signal formula | `signal_generator.py` (weights/thresholds) |
| Restyle the PDF | `pdf_generator.py` |
| Add a dashboard panel | `app.py` |

Keep the **golden rule**: numbers from XBRL, words from the LLM. Don't let a new
feature ask the LLM for a financial figure.

---

## High-value next features

1. **Multi-period trend charts.** You already store history in SQLite. Pull the
   last N filings for a ticker and plot revenue/EPS trends over time instead of
   just current-vs-prior.
2. **Peer comparison.** Run several tickers and compare KPIs/tone/signal side by
   side in the dashboard.
3. **More KPIs.** Add free-cash-flow, R&D spend, debt, etc. by extending
   `KPI_CONCEPTS` with the right XBRL tag fallbacks.
4. **Richer risk taxonomy.** Have Llama 3 classify risks into a fixed scheme
   (regulatory, macro, operational, competitive) and visualise the distribution.
5. **Email/Slack export.** After the PDF is generated, optionally send it — gate
   any send behind explicit user action.
6. **Scheduled re-analysis.** A small scheduler that re-runs a watchlist when new
   filings appear on EDGAR.

---

## Moving to production

The SRS calls SQLite a *prototype* store and recommends **PostgreSQL** for
production. A realistic hardening path:

1. **Database → PostgreSQL.** Replace the SQLite calls in `database.py` with a
   driver like `psycopg2` (or SQLAlchemy so the rest of the code is
   driver-agnostic). Keep the same table shapes (`analysis_results`,
   `llm_cache`). This is the single most important production change and the one
   the SRS explicitly anticipates.
2. **Vector store → hosted/scalable.** ChromaDB persists locally; for many users
   or huge corpora, move to a server-mode ChromaDB or a managed vector DB. Only
   `vector_store.py` changes.
3. **Concurrency.** SQLite isn't built for many simultaneous writers; PostgreSQL
   plus a proper app server (or Streamlit Cloud with care) handles concurrent
   users.
4. **Secrets management.** `.env` is fine locally; in production use the host's
   secret manager (Streamlit Cloud secrets, cloud KMS, etc.). Never commit keys.
5. **Caching/queueing.** For scale, move the LLM cache to Redis and run the
   pipeline as a background job so the UI stays responsive.
6. **Observability.** Add structured logging and basic metrics (per-stage timing,
   API failure counts) — the `progress` callback is a natural hook point.

---

## Engineering practices to preserve

- **One file per pipeline stage.** Don't merge modules; the clarity is the point.
- **PEP8.** Run a formatter/linter (`black`, `ruff`) before committing.
- **Graceful nulls + retry/backoff.** Any new external call should follow the
  pattern in `_get()` — never let a remote failure crash the UI.
- **Cost discipline.** Keep `max_tokens` capped, keep caching on, and keep only
  retrieved chunks flowing to the LLM.
- **Tests.** Add unit tests around the network-independent stages first
  (parser, comparison_engine, signal_generator, pdf_generator) since those run
  without internet — exactly how this project was validated offline.

---

## A note on dependencies

Stay within the SRS-sanctioned, free/open-source stack unless there's a strong
reason to add something. If you do add a dependency, pin it in
`requirements.txt` and note why in this file so the next maintainer understands
the decision.

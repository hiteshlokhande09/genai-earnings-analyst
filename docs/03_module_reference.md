# 03 — Module Reference

Every module in `src/genai_analyst/`, in pipeline order. Each module has a
single responsibility (one stage of the SRS flow).

## core/config.py

Central configuration. Loads secrets from `.env`, resolves project paths,
creates runtime directories, and defines all tunable parameters (chunk size,
Top-K, model names, retry settings, the disclaimer). No other module hard-codes
configuration. Key helper: `is_llm_configured()`.

## core/pipeline.py

The Sprint 1 orchestrator. `run_analysis(ticker, form_type, progress, accession)`
calls every stage in order (ingest → parse → index → retrieve → sentiment →
generate) and returns one result dict, or `{"error": ...}` on failure. Accepts
an optional `progress` callback so the UI can show a live progress bar.

## ingestion/edgar_client.py

SEC EDGAR retrieval. Functions:
* `ticker_to_cik(ticker)` — resolve ticker → CIK (cached master map).
* `list_filings(ticker, form_type)` — all filings of a form type, newest first.
* `get_latest_filing(...)` — the most recent filing.
* `download_filing_html(filing)` — fetch the primary document HTML.
* `ingest(ticker, form_type, accession)` — end-to-end; returns filing + HTML.
All requests use `_request()`, which sets the SEC `User-Agent` and retries with
exponential backoff.

## ingestion/filing_parser.py

HTML → clean, segmented text. Functions:
* `html_to_text(html)` — strip tags/scripts/styles (BeautifulSoup4 + lxml).
* `clean_text(text)` — collapse whitespace and artefacts.
* `segment_sections(text)` — regex-locate Risk Factors, MD&A, Financials;
  always includes a `Full Document` fallback.
* `parse_filing(html)` — full entry point.

## rag/chunker.py

Semantic chunking via LangChain's `RecursiveCharacterTextSplitter`
(~2500 chars, 250 overlap). `chunk_sections(sections)` returns a list of
`{text, section, chunk_id}` dicts and skips the `Full Document` fallback when
named sections exist.

## rag/embedder.py

Sentence Transformers `all-MiniLM-L6-v2` embeddings (384-dim). Lazy singleton
model. Functions: `embed_texts(list)` and `embed_query(str)`.

## rag/vector_store.py

ChromaDB persistent vector store. One collection per filing
(`ticker_form_accession`). Functions: `collection_exists()`, `add_chunks()`,
`query()` (Top-K similarity).

## rag/retriever.py

RAG retrieval. `QUERY_TEMPLATES` define one tuned query per task
(executive_summary, risk_factors, guidance). Functions: `retrieve()`,
`retrieve_context(task)`, `retrieve_all_contexts()`.

## rag/indexer.py

Ties chunking + embedding + storage together. `index_filing(filing, sections)`
returns the chunk count, or `-1` if the filing is already indexed (cache hit).

## nlp/sentiment.py

FinBERT (`ProsusAI/finbert`) sentiment. Lazy pipeline. Functions:
`analyze_chunks()` (per-chunk labels), `aggregate_tone()` (overall 0–1 tone
score + label), `analyze()` (entry point).

## nlp/generation.py

Llama 3 via an OpenAI-compatible endpoint (Groq). Functions:
`generate_executive_summary(context)`, `extract_risk_factors(context)`
(returns structured JSON list), `extract_guidance(context)`. Retries with
backoff; returns placeholders if no API key is set; caps responses at 500
tokens.

## dashboard.py

The Streamlit UI. `render_sidebar()` collects inputs, `render_results()`
displays the summary, tone, risks and guidance, and `main()` wires it together
with a progress bar and error handling.

## app.py / run_cli.py (project root)

`app.py` is the Streamlit launcher (adds `src/` to the path and runs the
dashboard). `run_cli.py` runs the same pipeline headlessly from the terminal.

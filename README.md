# GenAI Financial Earnings Report Analyst

An AI-powered system that ingests SEC earnings filings (10-K / 10-Q) and
generates investor-grade analysis using Retrieval-Augmented Generation (RAG),
FinBERT sentiment analysis, and Meta Llama 3.

This repository contains the **Sprint 1** (mid-semester) deliverable.

---

## 1. Project overview

Financial earnings reports are often hundreds of pages long. This system
automates their analysis by combining structured retrieval with generative AI:
the filing is fetched from SEC EDGAR, semantically chunked, embedded into a
vector store, and the most relevant sections are retrieved and passed to a
language model — which keeps cost low and reduces hallucination.

**Golden rule:** narrative text is AI-generated; all factual figures come from
the official SEC filing. The AI writes words, not numbers.

## 2. Sprint scope (Agile / Scrum)

The project follows the **Scrum** framework over two sprints.

**Sprint 1 (this deliverable) — Steps 1–8 of the architecture flow:**
SEC ingestion → HTML parsing → semantic chunking → embeddings → ChromaDB
vector store → RAG retrieval → FinBERT sentiment → Llama 3 summary, risk
factors and forward guidance, presented through a Streamlit dashboard.

**Sprint 2 (end-semester) — Steps 9–12:**
KPI comparison, chart generation, PDF report, full dashboard, SQLite history
analytics and deployment.

## 3. Technology stack

| Layer | Technology |
|-------|-----------|
| Data ingestion | SEC EDGAR API |
| HTML parsing | BeautifulSoup4 + lxml |
| Chunking | LangChain RecursiveCharacterTextSplitter |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2) |
| Vector store | ChromaDB (persistent) |
| Retrieval | Top-K cosine similarity |
| Sentiment | FinBERT (ProsusAI/finbert) |
| LLM | Meta Llama 3 (via Groq API) |
| Dashboard | Streamlit |
| Language | Python 3.10+ |

## 4. Project structure

```
genai-earnings-analyst/
├── app.py                      # Streamlit launcher (streamlit run app.py)
├── run_cli.py                  # Headless CLI runner
├── requirements.txt
├── pyproject.toml              # Project metadata + tooling config
├── .env.example                # Template for secrets (copy to .env)
├── .gitignore
│
├── src/genai_analyst/
│   ├── core/
│   │   ├── config.py           # Central configuration
│   │   └── pipeline.py         # Step 1–8 orchestrator
│   ├── ingestion/
│   │   ├── edgar_client.py     # SEC EDGAR retrieval
│   │   └── filing_parser.py    # HTML parsing + segmentation
│   ├── rag/
│   │   ├── chunker.py          # LangChain chunking
│   │   ├── embedder.py         # Sentence Transformer embeddings
│   │   ├── vector_store.py     # ChromaDB wrapper
│   │   ├── retriever.py        # Top-K RAG retrieval
│   │   └── indexer.py          # Chunk → embed → store
│   ├── nlp/
│   │   ├── sentiment.py        # FinBERT
│   │   └── generation.py       # Llama 3
│   └── dashboard.py            # Streamlit UI
│
├── tests/                      # Unit tests (pytest)
└── docs/                       # Design, SDLC and knowledge-transfer docs
```

## 5. Installation & setup

See `docs/02_installation_and_setup.md` for full step-by-step instructions.
Quick version:

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate on mac/Linux)
pip install -r requirements.txt
copy .env.example .env           # then edit .env with your keys
streamlit run app.py
```

## 6. Configuration

All secrets live in a local `.env` file (never committed). Required values:

| Variable | Purpose |
|----------|---------|
| `LLAMA3_API_KEY` | Groq API key (free at console.groq.com) |
| `LLAMA3_BASE_URL` | LLM endpoint (defaults to Groq) |
| `LLAMA3_MODEL` | Model name (defaults to llama-3.1-8b-instant) |
| `SEC_USER_AGENT` | Your name + email (required by SEC) |

## 7. Running the tests

```bash
pip install pytest
pytest
```

## 8. Team & sprint ownership

See `docs/05_team_and_sprint_plan.md`.

## 9. License & disclaimer

For academic use. This tool does not provide financial advice; all figures
should be verified against primary SEC sources.

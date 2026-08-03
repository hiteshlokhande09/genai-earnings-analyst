# GenAI Financial Earnings Report Analyst

> **The AI writes words, not numbers.** All financial figures come directly from
> the SEC EDGAR XBRL API. The language model only ever sees retrieved text and
> produces narrative — guaranteeing numerical accuracy and auditability.

An end-to-end GenAI-powered tool that turns SEC 10-K and 10-Q filings into
structured, investor-grade analysis in under 90 seconds.

---

## What it does

Enter a stock ticker. The system:

1. Fetches the latest 10-K or 10-Q filing from **SEC EDGAR**
2. Parses and cleans the HTML, segments MD&A / Risk Factors / Financials
3. Chunks the text and stores it in **ChromaDB** via Sentence Transformer embeddings
4. Retrieves the most relevant passages using **RAG** (Top-K cosine similarity)
5. Extracts exact KPIs — Revenue, Net Income, EPS, Gross Profit, Gross Margin,
   Operating Income — from **EDGAR XBRL** (not the AI)
6. Scores management tone with **FinBERT** (local, no API cost)
7. Generates executive summary, top-5 risks and forward guidance with
   **Meta Llama 3 via Groq API**
8. Computes a weighted **Bull/Bear signal** from KPI growth, margin, tone and guidance
9. Renders charts, a downloadable **PDF report**, and an interactive **Streamlit dashboard**
10. Caches everything in **SQLite** — repeat loads are instant

---

## Screenshots

| Landing page | Analysis dashboard |
|---|---|
| *(insert screenshot)* | *(insert screenshot)* |

---

## Quick start

### Prerequisites
- Python 3.10+
- git

### Install

```bash
git clone https://github.com/hiteshlokhande09/genai-earnings-analyst
cd genai-earnings-analyst

python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate        # macOS / Linux

pip install -r requirements.txt
python -m spacy download en_core_web_sm   # optional but recommended
```

### Configure

```bash
copy .env.example .env     # Windows
cp .env.example .env       # macOS / Linux
```

Edit `.env`:

```env
LLAMA3_API_KEY=gsk_your_groq_key_here
LLAMA3_BASE_URL=https://api.groq.com/openai/v1/chat/completions
LLAMA3_MODEL=llama-3.1-8b-instant
SEC_USER_AGENT=Your Name your.email@example.com
```

Get a free Groq key at https://console.groq.com/keys (no credit card).

### Run

```bash
streamlit run app.py
```

Opens at **http://localhost:8501**. Click **Try it now →**, enter a ticker
(e.g. `AAPL`), choose 10-K or 10-Q, click **🚀 Run analysis**.

### CLI (optional)

```bash
python run_cli.py AAPL 10-K
python run_cli.py MSFT 10-Q --force    # ignore cache, re-analyse
```

---

## Project structure

```
genai-earnings-analyst/
├── app.py                          # Streamlit root launcher + router
├── run_cli.py                      # Headless CLI runner
├── requirements.txt
├── .env.example                    # Environment variable template
├── pyproject.toml                  # Black / isort / pytest config
│
├── src/genai_analyst/
│   ├── core/
│   │   ├── config.py               # All settings, paths, constants
│   │   ├── pipeline.py             # End-to-end orchestrator
│   │   └── database.py             # SQLite history + LLM cache
│   ├── ingestion/
│   │   ├── edgar_client.py         # SEC EDGAR retrieval
│   │   └── filing_parser.py        # HTML parsing + section segmentation
│   ├── rag/
│   │   ├── chunker.py              # LangChain semantic chunking
│   │   ├── indexer.py              # chunk → embed → ChromaDB
│   │   ├── embedder.py             # Sentence Transformer embeddings
│   │   ├── vector_store.py         # ChromaDB operations
│   │   └── retriever.py            # Top-K RAG retrieval
│   ├── analysis/
│   │   ├── kpi_extractor.py        # EDGAR XBRL KPI extraction
│   │   ├── comparison_engine.py    # Period-over-period comparison
│   │   └── signal_generator.py     # Bull/Bear signal engine
│   ├── nlp/
│   │   ├── sentiment.py            # FinBERT management tone
│   │   └── generation.py           # Llama 3 via Groq API
│   ├── output/
│   │   ├── visualizer.py           # matplotlib charts
│   │   └── pdf_generator.py        # ReportLab PDF report
│   ├── dashboard.py                # Streamlit analysis UI
│   ├── landing.py                  # Marketing landing page
│   └── theme.py                    # Shared CSS theme
│
├── tests/
│   ├── test_smoke.py               # 9 offline smoke tests
│   ├── test_parser.py
│   ├── test_chunker.py
│   ├── test_filing_parser.py
│   └── test_sentiment.py
│
├── data/                           # Runtime data (git-ignored)
│   ├── cache/                      # Cached filing HTML
│   ├── chroma/                     # ChromaDB vector collections
│   ├── charts/                     # Generated PNG charts
│   ├── reports/                    # Generated PDF reports
│   └── analyst.db                  # SQLite database
│
└── docs/                           # Knowledge transfer documentation
    ├── 00_start_here.md
    ├── 01_architecture_and_design.md
    ├── 02_installation_and_setup.md
    ├── 03_module_reference.md
    ├── 04_sdlc_and_engineering_practices.md
    ├── 05_team_and_sprint_plan.md
    └── 06_quality_assurance.md
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| UI | Streamlit |
| Data ingestion | SEC EDGAR API, BeautifulSoup4, lxml |
| RAG | LangChain, Sentence Transformers (`all-MiniLM-L6-v2`), ChromaDB |
| NLP | FinBERT (`ProsusAI/finbert`), Meta Llama 3 via Groq API |
| Analysis | pandas, NumPy |
| Output | matplotlib, ReportLab |
| Storage | SQLite3 (prototype) → PostgreSQL (production) |

---

## KPIs extracted

All figures come from the SEC EDGAR XBRL API — never AI-generated.

| KPI | XBRL source |
|-----|------------|
| Revenue | `RevenueFromContractWithCustomerExcludingAssessedTax` / `Revenues` |
| Net Income | `NetIncomeLoss` |
| EPS | `EarningsPerShareDiluted` / `EarningsPerShareBasic` |
| Gross Profit | `GrossProfit` |
| Gross Margin | Derived: Gross Profit / Revenue × 100 |
| Operating Income | `OperatingIncomeLoss` |

Period matching uses duration-aware filtering (annual ≈365 days, quarterly ≈90 days)
to prevent inflated growth figures in 10-Q filings.

---

## Bull/Bear signal

A weighted combination of four components:

| Component | Weight |
|-----------|--------|
| Revenue growth | 30% |
| Margin / profit trend | 25% |
| FinBERT management tone | 25% |
| Forward guidance sentiment | 20% |

Score in [0, 1]: ≥0.6 = **BULLISH**, ≤0.4 = **BEARISH**, else **NEUTRAL**.

> This signal is for informational and educational purposes only. It does not
> constitute financial, investment or trading advice.

---

## Tests

```bash
pip install pytest
pytest tests/ -v
```

Nine offline smoke tests (`test_smoke.py`) run without network access or ML
models and complete in seconds.

---

## Team

**PG Certificate in Big Data Analytics (PGCP-BDA), C-DAC Bangalore, Feb 2026**
**Project Guide: Aditya Arsh**

| Member | PRN |
|--------|-----|
| Hitesh Lokhande | 260250125043 |
| Aanandita Yedulla | 260250125096 |
| Ruchi Rathore | 260250125067 |
| Rupali Saolikar | 260250125068 |

---

## Disclaimer

This tool is built for educational and informational purposes as part of the
PGCP-BDA programme at C-DAC Bangalore. It does not constitute financial,
investment or trading advice. Always consult a licensed financial advisor and
the original SEC filing before making any decisions.

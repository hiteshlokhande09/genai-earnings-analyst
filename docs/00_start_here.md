# 00 — Knowledge Transfer: Start Here

This folder is the complete knowledge-transfer (KT) documentation for the
**GenAI Financial Earnings Report Analyst — Sprint 1 & Sprint 2 (Final)**.
Written so that any team member, mentor, or new developer can understand the
project, run it, and continue the work.

## Reading order

| Doc | Purpose |
|-----|---------|
| `00_start_here.md` | This index — read first |
| `01_architecture_and_design.md` | System architecture, pipeline flow, design decisions |
| `02_installation_and_setup.md` | Step-by-step install + run guide |
| `03_module_reference.md` | Every module, every public function explained |
| `04_sdlc_and_engineering_practices.md` | SDLC methodology + engineering practices |
| `05_team_and_sprint_plan.md` | Sprint 1 / Sprint 2 split + team ownership |
| `06_quality_assurance.md` | Coding standards, version control, testing |

## One-paragraph mental model

A user enters a stock ticker. The system fetches that company's latest 10-K
or 10-Q filing from SEC EDGAR, cleans the HTML, and splits the key sections
(MD&A, Risk Factors, Financials) into ~500-word chunks. Those chunks are
converted into 384-dimensional vectors by Sentence Transformers and stored in
a ChromaDB vector database. When the analysis runs, the system retrieves the
most relevant chunks for each task using Top-K cosine similarity (RAG), and
sends them to Meta Llama 3 via Groq API, which writes the executive summary,
extracts the top-5 risk factors, and interprets forward guidance. FinBERT
separately scores the management tone on every chunk. Financial KPIs (Revenue,
Net Income, EPS, Gross Profit, Gross Margin, Operating Income) are pulled
directly from the SEC EDGAR XBRL API — never from the AI. A weighted
Bull/Bear signal combines KPI growth, margin trend, tone and guidance. Results
are displayed on a Streamlit dashboard with charts and a downloadable
ReportLab PDF report. Every completed analysis is cached in SQLite so
subsequent loads are instant.

## The Golden Rule

> **The AI writes words, not numbers.** All financial figures come from the
> official SEC EDGAR XBRL API. The language model only ever sees retrieved
> text and produces narrative. This guarantees numerical accuracy and
> auditability.

## Project status

Both sprints are complete. The full end-to-end 17-stage pipeline is live.

- **Sprint 1 (mid-sem):** Steps 1–8 — ingestion, parsing, chunking,
  embedding, vector store, RAG retrieval, FinBERT tone, Llama 3 generation.
- **Sprint 2 (end-sem):** Steps 9–17 — XBRL KPI extraction, period-over-period
  comparison, Bull/Bear signal, chart generation, PDF report, SQLite history,
  landing page, full dashboard, app router.

# 00 — Start Here (Knowledge Transfer Index)

Welcome. This folder is the **complete knowledge transfer (KT)** for the
*GenAI Financial Earnings Report Analyst*. It is written so that **anyone** —
a teammate, a future student, an evaluator — can understand, run, extend, and
maintain the project without talking to the original authors.

## How this project works in one paragraph

The user types a stock ticker (e.g. `AAPL`) into a Streamlit dashboard. The
system downloads that company's latest SEC 10-K or 10-Q filing from the public
EDGAR API, strips the HTML to clean text, and splits it into ~500-word chunks.
Each chunk is turned into a numeric vector (embedding) and stored in a local
ChromaDB vector database. When analysis runs, the system retrieves only the
most relevant chunks (RAG) for each analytical question and feeds them to two
models: **FinBERT** (local) scores the management tone, and **Llama 3** (via a
free API) writes an executive summary, extracts the top-5 risk factors, and
summarises forward guidance. Meanwhile, exact financial numbers (Revenue, EPS,
Net Income, etc.) are pulled **directly from EDGAR's XBRL structured data** — never
guessed by the AI. A rule-based engine blends growth, tone, and guidance into a
**Bull/Bear signal**. Everything is rendered in the dashboard and exported as a
professional **PDF report**, with results cached in **SQLite** so re-runs are
instant and cheap.

## Reading order

| # | Document | What it covers |
|---|----------|----------------|
| 00 | **START_HERE.md** (this file) | Map of the docs, mental model |
| 01 | `01_architecture.md` | The full pipeline, data flow, and why RAG |
| 02 | `02_installation_and_setup.md` | Step-by-step install of every technology |
| 03 | `03_module_reference.md` | Deep dive into **every** Python file & function |
| 04 | `04_end_to_end_walkthrough.md` | Trace a single analysis from click to PDF |
| 05 | `05_srs_traceability.md` | Maps SRS deliverables & acceptance criteria to code |
| 06 | `06_review_and_demo_guide.md` | Exactly what to show in Review 1 & Review 2 |
| 07 | `07_troubleshooting_faq.md` | Common errors and fixes |
| 08 | `08_extending_the_project.md` | How to add features / move to production |
| 09 | `09_github_guide.md` | How to push the project to GitHub safely |

## The golden rule of this project

> **AI writes words. XBRL provides numbers.**

Llama 3 is only ever asked for *language* tasks (summaries, risk wording,
guidance). Every financial figure is sourced from SEC EDGAR's XBRL API so the
numbers are 100% accurate and auditable. Keep this separation when you extend
the code.

## Prerequisites to understand the code

- Basic Python (functions, dicts, modules).
- A rough idea of what an **embedding** and a **vector database** are
  (explained in `01_architecture.md`).
- That's it. No web-dev knowledge is required — the UI is pure Python (Streamlit).

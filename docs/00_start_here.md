# 00 — Knowledge Transfer: Start Here

This folder is the complete knowledge-transfer (KT) documentation for the
**GenAI Financial Earnings Report Analyst — Sprint 1**. It is written so that
any team member, mentor, or new developer can understand the project, run it,
and continue the work.

## Reading order

| Doc | Purpose |
|-----|---------|
| `00_start_here.md` | This index |
| `01_architecture_and_design.md` | System architecture, design decisions, data flow |
| `02_installation_and_setup.md` | Step-by-step install + how to run + where keys go |
| `03_module_reference.md` | Every module and function explained |
| `04_sdlc_and_engineering_practices.md` | SDLC methodology + engineering practices (eval criteria 2) |
| `05_team_and_sprint_plan.md` | Sprint 1 / Sprint 2 split + team ownership |
| `06_quality_assurance.md` | Coding standards, version control, testing (eval criteria 1) |

## One-paragraph mental model

A user enters a stock ticker. The system fetches that company's latest SEC
filing from EDGAR, cleans the HTML, and splits it into sections. Those sections
are chunked, converted into vectors, and stored in a local vector database
(ChromaDB). When analysis runs, the system retrieves only the most relevant
chunks for each task and sends them to Meta Llama 3, which writes the executive
summary, extracts risk factors, and summarises guidance. FinBERT separately
scores the management tone. Everything is shown on a Streamlit dashboard. This
is **Sprint 1** (Steps 1–8); KPI comparison, charts, PDF report and history
analytics are **Sprint 2**.

## Golden rule

> The AI writes words, not numbers. All factual figures come from the official
> SEC filing; the language model only ever sees retrieved text and produces
> narrative.

# 06 — Review & Demo Guide

You have **two reviews**. This guide tells you exactly what to show, in what
order, and what to say. The SRS specifies a **5-minute live demo flow**
(deliverable 12): *type ticker → show pipeline running → walk KPI table → open
PDF → run a second company to demonstrate SQLite caching.* Both reviews build
on that.

---

## Before any review (setup checklist)

1. `pip install -r requirements.txt` already done in your virtual environment.
2. `.env` filled with a real `LLAMA3_API_KEY` (free Groq key — see
   `02_installation_and_setup.md`).
3. Internet connection live (needed for EDGAR + Llama 3).
4. Run once **before** the review (e.g. `AAPL`) so the model files are
   downloaded and one result is cached — this makes the live demo fast and safe.
5. Have the PDF from that pre-run open in a tab as a backup.

> Tip: keep a second terminal showing the console progress logs — it visibly
> proves each pipeline stage runs.

---

## Review 1 — "It works and matches the SRS"

Goal: demonstrate a **working end-to-end pipeline** and that the **technology
stack matches the SRS exactly**.

Suggested 5-minute flow:

1. **Open the dashboard** — `streamlit run app.py`, show `localhost:8501`.
   Say: "Pure-Python Streamlit UI, no HTML/CSS/JS, exactly as the SRS requires."
2. **Type a ticker** (e.g. `MSFT`), select `10-K`, click **Analyze**.
3. **Narrate the live progress bar** as it moves through the SRS architecture
   flow: EDGAR fetch → parse → chunk/embed/ChromaDB → RAG → XBRL KPIs → FinBERT
   → Llama 3 → signal → charts → PDF → SQLite.
4. **Walk the KPI comparison table** — point out the numbers come straight from
   **EDGAR XBRL** (golden rule: AI writes words, XBRL provides numbers), with
   ▲/▼ period-over-period arrows from pandas.
5. **Show tone + Bull/Bear signal** — explain the 0–1 weighted blend.
6. **Open the generated PDF** — scroll through all 9 sections, ending on the
   disclaimer.
7. **Run a second company** (or re-run the same) to show the **SQLite cache**
   returning instantly — this is the explicit SRS demo beat.

Have `05_srs_traceability.md` open so you can answer "where is requirement X?"
on the spot.

---

## Review 2 — "It's robust, complete, and well-engineered"

Goal: depth. Show the parts that aren't obvious from the happy-path demo.

Things to show:

1. **RAG subsystem** — open `rag_retriever.py` and `vector_store.py`. Explain
   that only the Top-K retrieved chunks reach Llama 3, which cuts token cost and
   hallucination. Show the ChromaDB folder on disk filling up with collections.
2. **Cost controls** — `max_tokens=500`, SQLite LLM cache (`llm_cache` table),
   skip-if-already-indexed. Re-run a filing and show **zero** new API calls.
3. **Resilience** — type an **invalid ticker** (e.g. `ZZZZ`) and show the
   graceful error message instead of a crash. Mention retry + exponential
   backoff in `_get()`.
4. **The golden rule** — open `kpi_extractor.py` and `llama3_helper.py`
   side by side: numbers from XBRL, words from Llama 3, never mixed.
5. **History + persistence** — show the sidebar history list and explain the
   `analysis_results` SQLite table (acceptance criterion: ≥100 records).
6. **Traceability** — walk `05_srs_traceability.md`: every deliverable, feature,
   and acceptance criterion maps to a file.
7. **Knowledge transfer** — show this `knowledge transfer/` folder itself as
   evidence the project is maintainable by anyone.

---

## Likely reviewer questions + crisp answers

- **"Where do the financial numbers come from?"** — EDGAR XBRL structured API,
  never the LLM. See `kpi_extractor.py`.
- **"Why RAG instead of sending the whole filing?"** — Filings are 100+ pages;
  sending only Top-K retrieved chunks cuts token cost and reduces hallucination.
- **"What if the Llama 3 key is missing?"** — The system still runs and returns
  clearly-labelled placeholder text; nothing crashes.
- **"How is the Bull/Bear score computed?"** — Transparent weighted blend:
  revenue 0.30, margin 0.25, tone 0.25, guidance 0.20; thresholds at 0.60/0.40.
- **"Is anything hardcoded/insecure?"** — No. API keys live in `.env`, which is
  git-ignored; only `.env.example` is committed.
- **"Can it scale?"** — SQLite + ChromaDB for the prototype; the SRS and
  `08_extending_the_project.md` describe the PostgreSQL production path.

---

## If the internet fails mid-demo

Fall back to the **pre-run cached result** (that's why you ran it beforehand)
and the **backup PDF**. Explain that EDGAR + Llama 3 need connectivity but
everything else (FinBERT, ChromaDB, SQLite, charts, PDF) runs locally.

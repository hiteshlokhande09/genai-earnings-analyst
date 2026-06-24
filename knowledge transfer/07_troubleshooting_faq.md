# 07 — Troubleshooting & FAQ

Common problems, what causes them, and how to fix them. Most issues fall into
four buckets: install, API keys, network, and model downloads.

---

## Install / environment

**`python: command not found` or wrong version**
Ensure Python 3.10+ is installed and on PATH. Check with `python --version`
(or `python3 --version`). Recreate the virtual environment if needed.

**`pip install -r requirements.txt` fails on torch**
PyTorch (a FinBERT dependency) is large. If it fails, install it on its own
first: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
for a CPU-only build, then re-run the requirements install.

**`ModuleNotFoundError` after install**
You probably installed into a different environment than the one running the
app. Activate your venv first (`source .venv/bin/activate` on macOS/Linux,
`.venv\Scripts\activate` on Windows), then `pip install` and `streamlit run`
from the same shell.

---

## API keys / Llama 3

**Summary/risks/guidance show placeholder text**
No valid `LLAMA3_API_KEY` is set. Copy `.env.example` to `.env` and paste a key
(free Groq key works). Restart the Streamlit app so the new env var loads.

**`401 Unauthorized` / `invalid api key`**
The key is wrong, expired, or has a stray space/quote. Re-copy it. Confirm
`LLAMA3_BASE_URL` and `LLAMA3_MODEL` match your provider (defaults target Groq).

**Llama 3 calls time out or rate-limit**
Free tiers have limits. The helper retries with exponential backoff; if it still
fails it returns placeholders. Wait a minute and re-run, or lower request volume.

---

## Network / EDGAR

**"Could not retrieve a filing for 'XXXX'"**
Either the ticker is invalid, the company has no matching filing, or you're
offline. Verify the ticker on sec.gov and confirm internet connectivity.

**`403 Forbidden` from SEC**
SEC requires a descriptive `User-Agent`. Set `SEC_USER_AGENT` in `.env` to
something like `Your Name your@email.com` (the SEC asks for contact info).

**Everything is slow on the first run**
Expected. The first run downloads model files (FinBERT ~440 MB, the
Sentence-Transformer model, and PyTorch wheels). Subsequent runs are fast and
fully local for those components.

---

## Models / FinBERT / ChromaDB

**FinBERT download is slow or interrupted**
It caches under your HuggingFace cache directory. If a download breaks, delete
the partial cache and re-run; it will resume cleanly.

**Out-of-memory loading FinBERT**
The SRS requires ≥8 GB RAM. Close other apps, or run on Google Colab's free GPU
(see `02_installation_and_setup.md`).

**ChromaDB / `data/` errors or stale results**
The vector store and SQLite DB live under the local `data/` folder. To force a
clean rebuild, stop the app, delete `data/`, and re-run (everything regenerates;
the cache simply repopulates).

---

## Streamlit UI

**Dashboard won't open at localhost:8501**
Make sure you ran `streamlit run app.py` (not `python app.py`). If the port is
busy, Streamlit will pick another and print the URL in the terminal.

**Charts or PDF missing**
Check the console logs for the failing stage. Charts use a headless matplotlib
backend; the PDF is written under `data/`. A missing PDF usually means an
earlier stage returned an error — read the progress log to find which.

---

## Quick reset (nuclear option)

```bash
# from the project root, with the venv active
rm -rf data/ __pycache__/        # Windows: rmdir /s data  &  del *.pyc
pip install -r requirements.txt
streamlit run app.py
```

This keeps your code and `.env` but rebuilds all caches, vectors, and the DB
from scratch.

---

## FAQ

**Q: Does it ever invent financial numbers?**
No. KPIs come only from EDGAR XBRL. Llama 3 is used strictly for language.

**Q: Can I run it fully offline?**
No — EDGAR and Llama 3 need internet. But FinBERT, embeddings, ChromaDB,
SQLite, charts, and PDF generation all run locally after the first download.

**Q: Where are results stored?**
SQLite (`analysis_results`, `llm_cache`) and ChromaDB collections, both under
`data/`. PDFs are written there too.

**Q: How do I analyse a different period?**
Re-run with the same ticker after a new filing is published, or tick
**Force re-run** to bypass the cache.

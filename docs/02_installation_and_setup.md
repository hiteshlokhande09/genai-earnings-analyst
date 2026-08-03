# 02 — Installation & Setup

From a fresh machine to a running dashboard. Commands shown for Windows
PowerShell; macOS/Linux equivalents noted where they differ.

## Prerequisites (install once)

- **Python 3.10 or newer** — https://www.python.org/downloads/
  Windows: tick **"Add Python to PATH"** during installation.
- **git** — https://git-scm.com/downloads

Verify:
```powershell
python --version
git --version
```

## Step 1 — Clone the repository

```powershell
git clone https://github.com/hiteshlokhande09/genai-earnings-analyst
cd genai-earnings-analyst
```

## Step 2 — Create a virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1          # Windows PowerShell
# source venv/bin/activate          # macOS / Linux
```

You should see `(venv)` at the start of your prompt.

> **PowerShell blocked?** Run once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

## Step 3 — Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

This downloads PyTorch, HuggingFace Transformers, Sentence Transformers,
ChromaDB and FinBERT — allow 5–10 minutes the first time.

> **spaCy is optional** — the filing parser falls back to regex cleaning
> if spaCy is absent. The app will still run without it.

## Step 4 — Get a free Groq API key (for Llama 3)

1. Go to https://console.groq.com/keys — sign up free, no credit card.
2. Click **Create API Key**, copy the key (starts with `gsk_`).

## Step 5 — Configure environment variables

```powershell
copy .env.example .env          # Windows
cp .env.example .env            # macOS / Linux
```

Open `.env` and fill in your values:

```env
LLAMA3_API_KEY=gsk_your_actual_key_here
LLAMA3_BASE_URL=https://api.groq.com/openai/v1/chat/completions
LLAMA3_MODEL=llama-3.1-8b-instant
SEC_USER_AGENT=Your Name your.email@example.com
```

- **`LLAMA3_API_KEY`** — your Groq key. Without this, executive summary,
  risks and guidance will show placeholder messages (KPIs, tone and signal
  still work — they don't use the LLM).
- **`SEC_USER_AGENT`** — your real name + email. The SEC requires a
  descriptive User-Agent; requests without one may be blocked with 403.
- `LLAMA3_BASE_URL` and `LLAMA3_MODEL` — default values point to Groq's
  free tier and do not need to be changed.

> `.env` is git-ignored — never commit it. Only `.env.example` is tracked.

## Step 6 — Run the dashboard

```powershell
streamlit run app.py
```

Your browser opens at **http://localhost:8501**.

You will see the **landing page** — click **Try it now →**, then in the
sidebar enter a ticker (e.g. `AAPL`), choose `10-K` or `10-Q`, and click
**🚀 Run analysis**.

**The first analysis is slow** — FinBERT (~440 MB) and the embedding model
download and cache on first use. Subsequent runs are significantly faster.
Cached analyses (SQLite hit) load instantly.

## Step 7 — Run from the command line (optional)

```powershell
python run_cli.py AAPL 10-K
python run_cli.py MSFT 10-Q --force    # ignore cache, re-analyse
```

The CLI runs the same pipeline and prints the result to the terminal —
useful for testing without launching Streamlit.

## Verify your setup

Run the offline smoke tests (no internet required, no API key needed):

```powershell
pip install pytest
pytest tests/test_smoke.py -v
```

All 9 tests should pass. If they do, the core logic is wired correctly.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `streamlit not recognized` | Activate the venv: `venv\Scripts\Activate.ps1` |
| Summary / risks show placeholder text | `LLAMA3_API_KEY` missing or wrong in `.env`. Restart Streamlit after editing `.env`. |
| `403 Forbidden` from SEC EDGAR | Set a real name + email in `SEC_USER_AGENT` |
| `ModuleNotFoundError: spacy` | `pip install spacy && python -m spacy download en_core_web_sm` (optional) |
| KPI shows inflated 10-Q growth | Tick **Force re-analysis** checkbox and run again to rebuild the XBRL cache |
| First run very slow (>2 min) | Expected — FinBERT and embedding model download once, then cache |
| `ModuleNotFoundError: genai_analyst` | Run from the project root (the folder containing `app.py`), not from `src/` |

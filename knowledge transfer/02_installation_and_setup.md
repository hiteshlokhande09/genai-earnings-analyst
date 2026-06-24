# 02 — Installation & Setup (Step by Step)

This guide installs **every technology** the project uses, from scratch, on
Windows, macOS, or Linux. Follow it top to bottom.

---

## Step 0 — What you need first

| Requirement | Why | Check |
|---|---|---|
| **Python 3.10+** | The whole project | `python --version` |
| **pip** | Installs packages | `pip --version` |
| **git** | Version control / GitHub | `git --version` |
| **≥ 8 GB RAM** | FinBERT model loading | — |
| **Internet** | EDGAR + Llama 3 API + first model download | — |

### Install Python (if you don't have 3.10+)

- **Windows:** download from <https://www.python.org/downloads/> and tick
  *"Add Python to PATH"* during install.
- **macOS:** `brew install python@3.11` (or python.org installer).
- **Linux (Ubuntu):** `sudo apt update && sudo apt install python3 python3-pip python3-venv`

### Install git

- **Windows:** <https://git-scm.com/download/win>
- **macOS:** `brew install git`
- **Linux:** `sudo apt install git`

---

## Step 1 — Get the project files

If you received a ZIP, unzip it. If it's on GitHub:

```bash
git clone https://github.com/<your-username>/genai-earnings-analyst.git
cd genai-earnings-analyst
```

---

## Step 2 — Create a virtual environment (recommended)

A virtual environment keeps this project's packages isolated.

```bash
# Windows (PowerShell)
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

You should now see `(venv)` at the start of your terminal prompt.

---

## Step 3 — Install all Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs Streamlit, BeautifulSoup4, LangChain, Sentence Transformers,
ChromaDB, FinBERT's runtime (transformers + torch), pandas, matplotlib,
ReportLab, SQLite (built into Python), and python-dotenv.

> ⏳ This step is the longest (torch is large). On a slow connection it can take
> several minutes. That's normal.

### (Optional) Install the spaCy English model

Improves text cleaning. Safe to skip — the code falls back to regex.

```bash
python -m spacy download en_core_web_sm
```

---

## Step 4 — Get a FREE Llama 3 API key (Groq)

Llama 3 powers the summary, risk, and guidance text. Groq offers it free.

1. Go to <https://console.groq.com/keys> and sign up (free).
2. Click **Create API Key**, copy the key (starts with `gsk_...`).

> Don't want Groq? Any OpenAI-compatible provider works — see Step 5 to change
> the base URL and model name. FinBERT and XBRL still work without an LLM key,
> but the summary/risks/guidance sections will be blank.

---

## Step 5 — Configure your environment file

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

Open `.env` in a text editor and fill in:

```ini
LLAMA3_API_KEY=gsk_your_real_key_here
LLAMA3_BASE_URL=https://api.groq.com/openai/v1/chat/completions
LLAMA3_MODEL=llama-3.1-8b-instant
SEC_USER_AGENT=Your Name your.email@example.com
```

- **`SEC_USER_AGENT`** must be your real name + email. SEC's fair-access policy
  requires it; without it your EDGAR requests may be blocked.
- **Never commit `.env`** — it's already in `.gitignore`.

### Using a different LLM provider

| Provider | `LLAMA3_BASE_URL` | Example `LLAMA3_MODEL` |
|---|---|---|
| Groq (default) | `https://api.groq.com/openai/v1/chat/completions` | `llama-3.1-8b-instant` |
| Together.ai | `https://api.together.xyz/v1/chat/completions` | `meta-llama/Llama-3-8b-chat-hf` |

---

## Step 6 — First run

```bash
streamlit run app.py
```

Your browser opens at <http://localhost:8501>.

1. In the sidebar, type a ticker: `AAPL`.
2. Choose **10-K**.
3. Click **🚀 Run analysis**.

> 🕐 **First run is slow (~60 s)** because FinBERT (~440 MB) and the embedding
> model download once and cache locally. Every later run — and any cached
> filing — is fast.

### Prefer the command line?

```bash
python run_cli.py AAPL 10-K
```

This runs the same pipeline headless and prints a summary + the PDF path. Great
for quick testing and for the live demo.

---

## Step 7 — Verify it worked

After a successful run you should see, under `data/`:

- a PDF in `data/reports/`,
- charts in `data/charts/`,
- a populated `data/analyst.db`,
- a ChromaDB index in `data/chroma/`.

In the dashboard you should see KPI cards, a colour-coded comparison table, a
tone score, a Bull/Bear signal, charts, and a **Download PDF** button.

---

## Common first-run issues

| Symptom | Fix |
|---|---|
| `LLAMA3_API_KEY not set` warning | You skipped Step 5, or the key is wrong. |
| EDGAR request blocked / 403 | Set a real `SEC_USER_AGENT` in `.env`. |
| `ModuleNotFoundError` | Re-run `pip install -r requirements.txt` inside the venv. |
| Torch install fails | Upgrade pip (`pip install --upgrade pip`), retry. |
| Out of memory loading FinBERT | Close other apps; need ≥8 GB RAM, or use Google Colab. |

More in `07_troubleshooting_faq.md`.

---

## Running on Google Colab (free GPU alternative)

The SRS notes Colab as a free fallback with GPU for faster FinBERT:

1. Upload the project folder to Colab (or `git clone` it in a cell).
2. `!pip install -r requirements.txt`
3. Set env vars in a cell (`import os; os.environ['LLAMA3_API_KEY']='...'`).
4. Run `run_cli.py` directly, or use a tunnel (e.g. `localtunnel`) to expose
   Streamlit. For demos, the CLI runner is simplest on Colab.

# 02 — Installation & Setup

This guide takes you from a fresh machine to a running dashboard. Commands are
shown for Windows; macOS/Linux equivalents are noted where they differ.

## Step 0 — Prerequisites

Install these once:

* **Python 3.10 or newer** — https://www.python.org/downloads/
  On Windows, tick **"Add Python to PATH"** during installation.
* **git** — https://git-scm.com/downloads

Verify:
```bash
python --version
git --version
```

## Step 1 — Get the project

```bash
git clone <your-repo-url>
cd genai-earnings-analyst
```
(Or unzip the delivered archive and `cd` into the folder containing `app.py`.)

## Step 2 — Create a virtual environment

```bash
python -m venv venv
```

Activate it:
```bash
# Windows (PowerShell)
venv\Scripts\Activate.ps1
# Windows (Command Prompt)
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

You should see `(venv)` at the start of your prompt.

> **PowerShell note:** if activation is blocked with a "running scripts is
> disabled" error, run this once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

## Step 3 — Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This downloads PyTorch, transformers, sentence-transformers and ChromaDB, so it
can take several minutes the first time.

## Step 4 — Get a free Llama 3 API key

1. Go to https://console.groq.com/keys and sign up (no credit card needed).
2. Click **Create API Key** and copy the key (it starts with `gsk_`).

## Step 5 — Configure your environment

```bash
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

Open `.env` in a text editor and fill in:

```
LLAMA3_API_KEY=gsk_your_real_key_here
LLAMA3_BASE_URL=https://api.groq.com/openai/v1/chat/completions
LLAMA3_MODEL=llama-3.1-8b-instant
SEC_USER_AGENT=Your Name your.email@example.com
```

* **`LLAMA3_API_KEY`** — your Groq key from Step 4.
* **`SEC_USER_AGENT`** — your real name and email (the SEC requires this for
  EDGAR access; requests without it may be blocked).

> The `.env` file holds your secrets and is git-ignored — never commit it.

## Step 6 — Run the dashboard

```bash
streamlit run app.py
```

Your browser opens at http://localhost:8501. Enter a ticker (e.g. `AAPL`),
choose a filing type, and click **Analyse**.

The **first analysis is slow** because FinBERT (~440 MB) and the embedding
model download once and are then cached locally. Later runs are fast.

## Step 7 — (Optional) Run from the command line

```bash
python run_cli.py AAPL 10-K
```

This runs the same pipeline and prints the results to the terminal.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `streamlit not recognized` | The venv isn't active — run the activate command, or use `venv\Scripts\python.exe -m streamlit run app.py` |
| Summary/risks show placeholders | `LLAMA3_API_KEY` is missing or invalid in `.env` |
| `403 Forbidden` from SEC | Set a real name + email in `SEC_USER_AGENT` |
| `ModuleNotFoundError: torchvision` | `pip install torchvision` |
| First run very slow | Expected — models download once, then cache |

"""
config.py
=========
Central configuration for the GenAI Financial Earnings Report Analyst.

All tunable constants, API endpoints, model names, and environment-driven
settings live here so that no other module hard-codes a magic value.

Environment variables (loaded from a local .env file via python-dotenv):
    LLAMA3_API_KEY      -> API key for the Llama 3 provider (Groq / Together / Azure)
    LLAMA3_BASE_URL     -> OpenAI-compatible chat-completions base URL
    LLAMA3_MODEL        -> Model identifier served by the provider
    SEC_USER_AGENT      -> "Name email" string required by SEC EDGAR fair-access policy

NOTE: Keys are never hard-coded. The .env file is git-ignored.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a .env file in the project root (if present).
load_dotenv()

# --------------------------------------------------------------------------- #
# Project paths
# --------------------------------------------------------------------------- #
# core/ -> genai_analyst/ -> src/ -> project root
BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"            # raw filing HTML cache
CHROMA_DIR = DATA_DIR / "chroma"          # ChromaDB persistent storage
REPORTS_DIR = DATA_DIR / "reports"        # generated PDF reports
CHARTS_DIR = DATA_DIR / "charts"          # generated matplotlib PNGs
DB_PATH = DATA_DIR / "analyst.db"         # SQLite3 database file

for _d in (DATA_DIR, CACHE_DIR, CHROMA_DIR, REPORTS_DIR, CHARTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# SEC EDGAR endpoints (all public, HTTPS, free)
# --------------------------------------------------------------------------- #
SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
SEC_XBRL_CONCEPT_URL = (
    "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik10}/us-gaap/{concept}.json"
)
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"

# SEC requires a descriptive User-Agent. Override via the SEC_USER_AGENT env var.
SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "GenAI Earnings Analyst (academic project) contact@example.com",
)
SEC_HEADERS = {"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}

# --------------------------------------------------------------------------- #
# Llama 3 provider (OpenAI-compatible chat-completions API)
# Default points at Groq's free tier. Any compatible provider works by
# overriding LLAMA3_BASE_URL / LLAMA3_MODEL in the .env file.
# --------------------------------------------------------------------------- #
LLAMA3_API_KEY = os.getenv("LLAMA3_API_KEY", "")
LLAMA3_BASE_URL = os.getenv(
    "LLAMA3_BASE_URL", "https://api.groq.com/openai/v1/chat/completions"
)
LLAMA3_MODEL = os.getenv("LLAMA3_MODEL", "llama-3.1-8b-instant")
LLAMA3_MAX_TOKENS = 500          # SRS constraint: cap output tokens to control cost
LLAMA3_TEMPERATURE = 0.2         # low temperature -> more deterministic analysis

# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"     # Sentence Transformers
FINBERT_MODEL_NAME = "ProsusAI/finbert"       # local FinBERT sentiment model

# --------------------------------------------------------------------------- #
# RAG / chunking parameters
# --------------------------------------------------------------------------- #
CHUNK_SIZE = 2500          # ~500 words (chars); RecursiveCharacterTextSplitter
CHUNK_OVERLAP = 250
RAG_TOP_K = 5             # Top-K semantic similarity retrieval

# --------------------------------------------------------------------------- #
# Networking / resilience
# --------------------------------------------------------------------------- #
REQUEST_TIMEOUT = 30      # seconds
MAX_RETRIES = 4           # retry attempts for transient API failures
BACKOFF_BASE = 1.5        # exponential backoff base (seconds)

# --------------------------------------------------------------------------- #
# Financial KPI concept tags (XBRL us-gaap). Each KPI tries tags in order
# until one returns data, since companies tag the same concept differently.
# --------------------------------------------------------------------------- #
KPI_CONCEPTS = {
    "Revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "NetIncome": ["NetIncomeLoss"],
    "EPS": ["EarningsPerShareDiluted", "EarningsPerShareBasic"],
    "GrossProfit": ["GrossProfit"],
    "OperatingIncome": ["OperatingIncomeLoss"],
}

# Sections we want to identify and prioritise from a filing.
TARGET_SECTIONS = ["MD&A", "Risk Factors", "Financial Statements"]

DISCLAIMER = (
    "This report is generated by an automated AI system for informational and "
    "educational purposes only. It does not constitute financial, investment, or "
    "trading advice. Financial figures are sourced from SEC EDGAR XBRL data; "
    "narrative analysis is AI-generated and may contain errors. Always consult a "
    "licensed financial advisor and the original SEC filing before making decisions."
)


def is_llm_configured() -> bool:
    """Return True if a Llama 3 API key is available."""
    return bool(LLAMA3_API_KEY)

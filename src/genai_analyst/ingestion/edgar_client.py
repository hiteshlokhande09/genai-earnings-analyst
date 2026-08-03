"""
edgar_client.py
===================
SEC Filing Ingestion (Pipeline Step 2).

Responsibilities:
    * Resolve a stock ticker symbol to its SEC CIK number.
    * Fetch the company's filing history from the EDGAR submissions API.
    * Locate the most recent 10-Q / 10-K filing.
    * Download the primary filing document (HTML), caching it locally.

All requests respect the SEC fair-access policy (descriptive User-Agent,
HTTPS only) and use retry logic with exponential backoff.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import requests

from genai_analyst.core import config
# --------------------------------------------------------------------------- #
# Low-level HTTP helper with retry + exponential backoff
# --------------------------------------------------------------------------- #
def _get(url: str, *, as_json: bool = True):
    """GET a URL with SEC headers, retries, and exponential backoff.

    Returns parsed JSON (as_json=True) or raw text. Returns None on failure
    so callers can degrade gracefully (SRS: graceful null values).
    """
    last_err: Optional[Exception] = None
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers=config.SEC_HEADERS, timeout=config.REQUEST_TIMEOUT
            )
            # SEC throttles aggressively; honour 429 / 5xx with a backoff.
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"Transient status {resp.status_code}")
            resp.raise_for_status()
            return resp.json() if as_json else resp.text
        except Exception as exc:  # noqa: BLE001 - intentional broad catch + retry
            last_err = exc
            sleep_for = config.BACKOFF_BASE ** attempt
            time.sleep(sleep_for)
    print(f"[edgar_client] GET failed after retries: {url} ({last_err})")
    return None


# --------------------------------------------------------------------------- #
# Ticker -> CIK resolution
# --------------------------------------------------------------------------- #
_TICKER_CACHE_FILE = config.CACHE_DIR / "company_tickers.json"


def _load_ticker_map() -> dict:
    """Load (and cache for 24h) the SEC ticker->CIK master map."""
    if _TICKER_CACHE_FILE.exists():
        age = time.time() - _TICKER_CACHE_FILE.stat().st_mtime
        if age < 86_400:  # 24 hours
            try:
                return json.loads(_TICKER_CACHE_FILE.read_text())
            except json.JSONDecodeError:
                pass
    data = _get(config.SEC_TICKER_MAP_URL)
    if data:
        _TICKER_CACHE_FILE.write_text(json.dumps(data))
        return data
    return {}


def ticker_to_cik(ticker: str) -> Optional[str]:
    """Return the 10-digit zero-padded CIK for a ticker, or None if unknown."""
    ticker = ticker.strip().upper()
    mapping = _load_ticker_map()
    for entry in mapping.values():
        if entry.get("ticker", "").upper() == ticker:
            return str(entry["cik_str"]).zfill(10)
    return None


def list_companies() -> list[dict]:
    """Return every SEC company as {'ticker', 'title', 'cik'}, sorted by name.

    Powers the dashboard's searchable company picker so users can type a
    company name (e.g. "Apple") instead of remembering the ticker symbol.
    Reuses the same 24h-cached SEC master map as ticker_to_cik(). Returns an
    empty list if the map can't be loaded (e.g. offline), so callers can fall
    back to manual ticker entry.
    """
    mapping = _load_ticker_map()
    companies = []
    for entry in mapping.values():
        ticker = str(entry.get("ticker", "")).upper().strip()
        title = str(entry.get("title", "")).strip()
        if ticker and title:
            companies.append({
                "ticker": ticker,
                "title": title,
                "cik": str(entry.get("cik_str", "")).zfill(10),
            })
    companies.sort(key=lambda c: c["title"].lower())
    return companies


# --------------------------------------------------------------------------- #
# Filing lookup + download
# --------------------------------------------------------------------------- #
def list_filings(ticker: str, form_type: str = "10-K") -> list[dict]:
    """Return ALL filings of the requested form type for a ticker, newest first.

    Each item is a filing dict: ticker, cik, company, form, accession,
    filing_date, primary_doc, doc_url. Returns [] on failure. Powers the
    dashboard's "Filing date" picker so users can analyse a past period
    (e.g. last financial year) instead of only the most recent filing.
    """
    cik10 = ticker_to_cik(ticker)
    if not cik10:
        print(f"[edgar_client] Unknown ticker: {ticker}")
        return []

    subs = _get(config.SEC_SUBMISSIONS_URL.format(cik10=cik10))
    if not subs:
        return []

    recent = subs.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    dates = recent.get("filingDate", [])
    company = subs.get("name", ticker.upper())

    results = []
    for i, form in enumerate(forms):
        if form == form_type:
            accession_nodash = accessions[i].replace("-", "")
            cik_int = str(int(cik10))  # archives path uses non-padded CIK
            doc_url = config.SEC_ARCHIVES_URL.format(
                cik=cik_int, accession=accession_nodash, doc=primary_docs[i]
            )
            results.append({
                "ticker": ticker.upper(),
                "cik": cik10,
                "company": company,
                "form": form,
                "accession": accessions[i],
                "filing_date": dates[i],
                "primary_doc": primary_docs[i],
                "doc_url": doc_url,
            })
    return results


def get_latest_filing(ticker: str, form_type: str = "10-K") -> Optional[dict]:
    """Return the most recent filing of the requested form type, or None.

    Returns a dict with keys: ticker, cik, company, form, accession,
    filing_date, primary_doc, doc_url.
    """
    filings = list_filings(ticker, form_type)
    if not filings:
        print(f"[edgar_client] No {form_type} filing found for {ticker}")
        return None
    return filings[0]


def download_filing_html(filing: dict) -> Optional[str]:
    """Download (and cache) the raw HTML of a filing's primary document."""
    cache_key = f"{filing['ticker']}_{filing['form']}_{filing['accession']}.html"
    cache_path: Path = config.CACHE_DIR / cache_key
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8", errors="ignore")

    html = _get(filing["doc_url"], as_json=False)
    if html:
        cache_path.write_text(html, encoding="utf-8", errors="ignore")
    return html


def ingest(ticker: str, form_type: str = "10-K",
           accession: Optional[str] = None) -> Optional[dict]:
    """End-to-end ingestion: returns the filing metadata enriched with raw HTML.

    If `accession` is given, that specific filing is fetched; otherwise the
    most recent filing of `form_type` is used.
    """
    if accession:
        filings = list_filings(ticker, form_type)
        filing = next((f for f in filings if f["accession"] == accession), None)
        if not filing:  # requested accession not found — fall back to latest
            filing = get_latest_filing(ticker, form_type)
    else:
        filing = get_latest_filing(ticker, form_type)
    if not filing:
        return None
    html = download_filing_html(filing)
    if not html:
        return None
    filing["html"] = html
    return filing


if __name__ == "__main__":
    # Manual smoke test (requires internet).
    result = ingest("AAPL", "10-K")
    if result:
        print(f"Fetched {result['form']} for {result['company']} "
              f"({result['filing_date']}), {len(result['html'])} bytes of HTML.")

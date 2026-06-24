"""
SEC EDGAR ingestion (Sprint 1, Step 2 of the SRS architecture flow).

Responsibilities
----------------
* Resolve a stock ticker symbol to its SEC Central Index Key (CIK).
* List a company's filings of a given form type (10-K / 10-Q).
* Download the primary filing document (HTML).

All outbound requests use a descriptive ``User-Agent`` (required by the SEC
fair-access policy) and a retry-with-exponential-backoff strategy so that
transient network errors degrade gracefully rather than crashing the pipeline.
"""

from __future__ import annotations

import time
from typing import Optional

import requests

from genai_analyst.core import config

# Module-level cache for the (large) ticker-to-CIK map so it is fetched once.
_TICKER_MAP: Optional[dict] = None


def _request(url: str, *, as_json: bool = True):
    """Perform a resilient GET request against an SEC endpoint.

    Parameters
    ----------
    url:
        Fully-formed URL to fetch.
    as_json:
        If True, parse and return the response as JSON; otherwise return text.

    Returns
    -------
    The parsed JSON object / response text, or ``None`` if all retries fail.
    """
    headers = {"User-Agent": config.SEC_USER_AGENT}
    last_error: Optional[Exception] = None

    for attempt in range(config.HTTP_MAX_RETRIES):
        try:
            response = requests.get(
                url, headers=headers, timeout=config.HTTP_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json() if as_json else response.text
        except requests.RequestException as error:  # network / HTTP error
            last_error = error
            sleep_for = config.HTTP_BACKOFF_SECONDS * (2 ** attempt)
            time.sleep(sleep_for)

    print(f"[ingestion] request failed for {url}: {last_error}")
    return None


def _load_ticker_map() -> dict:
    """Load and cache the SEC ticker-to-CIK master map."""
    global _TICKER_MAP
    if _TICKER_MAP is None:
        data = _request(config.SEC_COMPANY_TICKERS_URL) or {}
        _TICKER_MAP = data
    return _TICKER_MAP


def ticker_to_cik(ticker: str) -> Optional[str]:
    """Resolve a ticker symbol to a 10-digit zero-padded CIK string."""
    mapping = _load_ticker_map()
    ticker = ticker.upper().strip()
    for entry in mapping.values():
        if str(entry.get("ticker", "")).upper() == ticker:
            return str(entry["cik_str"]).zfill(10)
    return None


def list_filings(ticker: str, form_type: str = "10-K") -> list[dict]:
    """Return all filings of ``form_type`` for ``ticker``, newest first.

    Each item contains: ticker, cik, company, form, accession, filing_date,
    primary_doc and doc_url. Returns an empty list on failure.
    """
    cik10 = ticker_to_cik(ticker)
    if not cik10:
        print(f"[ingestion] unknown ticker: {ticker}")
        return []

    submissions = _request(config.SEC_SUBMISSIONS_URL.format(cik10=cik10))
    if not submissions:
        return []

    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    dates = recent.get("filingDate", [])
    company = submissions.get("name", ticker.upper())

    results: list[dict] = []
    for index, form in enumerate(forms):
        if form == form_type:
            accession_nodash = accessions[index].replace("-", "")
            doc_url = config.SEC_ARCHIVES_URL.format(
                cik=str(int(cik10)),  # archives path uses the non-padded CIK
                accession=accession_nodash,
                doc=primary_docs[index],
            )
            results.append(
                {
                    "ticker": ticker.upper(),
                    "cik": cik10,
                    "company": company,
                    "form": form,
                    "accession": accessions[index],
                    "filing_date": dates[index],
                    "primary_doc": primary_docs[index],
                    "doc_url": doc_url,
                }
            )
    return results


def get_latest_filing(ticker: str, form_type: str = "10-K") -> Optional[dict]:
    """Return the most recent filing of ``form_type`` for ``ticker``."""
    filings = list_filings(ticker, form_type)
    if not filings:
        print(f"[ingestion] no {form_type} filing found for {ticker}")
        return None
    return filings[0]


def download_filing_html(filing: dict) -> Optional[str]:
    """Download the raw HTML for a filing dict produced by ``list_filings``."""
    return _request(filing["doc_url"], as_json=False)


def ingest(
    ticker: str,
    form_type: str = "10-K",
    accession: Optional[str] = None,
) -> Optional[dict]:
    """End-to-end ingestion entry point.

    Returns the filing metadata enriched with the raw HTML under the ``html``
    key, or ``None`` if the filing could not be retrieved.

    If ``accession`` is supplied, that specific filing is fetched; otherwise the
    most recent filing of ``form_type`` is used.
    """
    if accession:
        filings = list_filings(ticker, form_type)
        filing = next(
            (item for item in filings if item["accession"] == accession), None
        )
        if filing is None:  # requested filing not found -> fall back to latest
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

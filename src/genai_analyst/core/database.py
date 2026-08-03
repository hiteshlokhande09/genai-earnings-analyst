"""
database.py
===========
Historical SQLite3 Storage + LLM Cache (Pipeline Step 17).

Two responsibilities:
    1. Persist every completed analysis (analysis_results table) so the
       dashboard can show history and enable period-over-period comparison.
    2. Cache Llama 3 responses (llm_cache table) keyed by filing+task so the
       same filing is never re-sent to the API (SRS cost constraint).

SQLite is used at prototype stage (lightweight, file-based, zero-config).
PostgreSQL is recommended for production / concurrent multi-user access.

Schema note
-----------
``analysis_results`` stores the *complete* displayable analysis, including the
forward-guidance text and the structured risk list (as JSON). Earlier versions
of this file omitted those two columns, which meant a cache hit rendered with
empty risks and a placeholder guidance message. ``_migrate()`` adds the missing
columns in place, so existing databases keep their rows and simply backfill the
new fields as empty.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import List, Optional

from genai_analyst.core import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Columns added after the initial release: (name, SQL type).
_ADDED_COLUMNS = (
    ("guidance", "TEXT"),
    ("risks_json", "TEXT"),
)


def _migrate(conn: sqlite3.Connection) -> None:
    """Add any columns missing from an older analysis_results table.

    Uses PRAGMA table_info so this is idempotent and safe to run on every
    start-up. Existing rows keep their data; the new columns are NULL until
    the filing is re-analysed.
    """
    existing = {row["name"] for row in conn.execute(
        "PRAGMA table_info(analysis_results)"
    ).fetchall()}
    for name, sql_type in _ADDED_COLUMNS:
        if name not in existing:
            conn.execute(
                f"ALTER TABLE analysis_results ADD COLUMN {name} {sql_type}"
            )


def init_db() -> None:
    """Create tables if they do not already exist, then apply migrations."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_results (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker        TEXT NOT NULL,
                company       TEXT,
                form          TEXT,
                accession     TEXT,
                filing_date   TEXT,
                tone_score    REAL,
                tone_label    TEXT,
                signal_score  REAL,
                signal_class  TEXT,
                kpis_json     TEXT,
                summary       TEXT,
                guidance      TEXT,
                risks_json    TEXT,
                pdf_path      TEXT,
                created_at    TEXT,
                UNIQUE(ticker, form, accession)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_cache (
                cache_key   TEXT PRIMARY KEY,
                response    TEXT,
                created_at  TEXT
            )
            """
        )
        _migrate(conn)
        conn.commit()


# --------------------------------------------------------------------------- #
# LLM cache
# --------------------------------------------------------------------------- #
def get_llm_cache(cache_key: str) -> Optional[str]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT response FROM llm_cache WHERE cache_key = ?", (cache_key,)
        ).fetchone()
        return row["response"] if row else None


def set_llm_cache(cache_key: str, response: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO llm_cache (cache_key, response, created_at) "
            "VALUES (?, ?, ?)",
            (cache_key, response, datetime.utcnow().isoformat()),
        )
        conn.commit()


# --------------------------------------------------------------------------- #
# Analysis results
# --------------------------------------------------------------------------- #
def save_analysis(record: dict) -> int:
    """Insert or replace an analysis record. Returns the row id.

    ``record`` may supply ``guidance`` (str) and ``risks`` (list of dicts);
    the risk list is serialised to JSON so a cached result can be rendered
    exactly like a fresh one.
    """
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT OR REPLACE INTO analysis_results
                (ticker, company, form, accession, filing_date, tone_score,
                 tone_label, signal_score, signal_class, kpis_json, summary,
                 guidance, risks_json, pdf_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("ticker"),
                record.get("company"),
                record.get("form"),
                record.get("accession"),
                record.get("filing_date"),
                record.get("tone_score"),
                record.get("tone_label"),
                record.get("signal_score"),
                record.get("signal_class"),
                json.dumps(record.get("kpis", {})),
                record.get("summary"),
                record.get("guidance"),
                json.dumps(record.get("risks", []) or []),
                record.get("pdf_path"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_cached_analysis(ticker: str, form: str, accession: str) -> Optional[dict]:
    """Return a previously saved analysis for a specific filing, if any."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM analysis_results WHERE ticker=? AND form=? AND accession=?",
            (ticker.upper(), form, accession),
        ).fetchone()
        return dict(row) if row else None


def get_analysis_by_id(record_id: int) -> Optional[dict]:
    """Return a single saved analysis row by its primary-key id, or None.

    Used by the dashboard to reload a previously-stored result when the user
    clicks an item in the History list.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM analysis_results WHERE id = ?", (record_id,)
        ).fetchone()
        return dict(row) if row else None


def get_history(ticker: Optional[str] = None, limit: int = 100) -> List[dict]:
    """Return recent analysis history, optionally filtered by ticker."""
    with _connect() as conn:
        if ticker:
            rows = conn.execute(
                "SELECT * FROM analysis_results WHERE ticker=? "
                "ORDER BY created_at DESC LIMIT ?",
                (ticker.upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM analysis_results ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def count_records() -> int:
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM analysis_results").fetchone()["c"]


# Initialise the schema on import so callers never hit a missing table.
init_db()


if __name__ == "__main__":
    init_db()
    print("DB initialised at", config.DB_PATH, "| records:", count_records())
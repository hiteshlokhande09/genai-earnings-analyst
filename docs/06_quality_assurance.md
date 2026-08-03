# 06 — Quality Assurance

This document addresses **Evaluation Criterion 1 (Quality Assurance
Practices)**: coding standards, version control, testing and documentation.

## 1. Coding standards and naming conventions

- **PEP 8** is followed throughout.
- **Black** (line length 88) and **isort** are configured in `pyproject.toml`
  to enforce consistent formatting and import ordering automatically.
- **Naming conventions:**
  - modules and functions: `snake_case`
  - constants: `UPPER_SNAKE_CASE` (e.g. `CHUNK_SIZE`, `RAG_TOP_K`, `MAX_RETRIES`)
  - private helpers: leading underscore (e.g. `_get`, `_chat`, `_duration_days`,
    `_collection_name`)
- **Type hints** annotate all public function signatures.
- **Docstrings** on every module (purpose, responsibilities, design notes) and
  every public function (parameters, return value, notable behaviour).
- **Single responsibility:** each module maps to exactly one pipeline stage.
  The orchestrator (`pipeline.py`) is the only file that knows the stage order.

## 2. Version control

- **git** used for all source and documentation.
- **Repository:** https://github.com/hiteshlokhande09/genai-earnings-analyst
- **Branch strategy:** each member works on a named branch and raises a
  Pull Request reviewed and merged to `main`:
  - `hitesh/fix-kpi-indexer-landing`
  - `anandita/sprint2-modules`
  - `ruchi/sprint2-modules`
  - `rupali/sprint2-modules`
- Commit messages follow the `feat:` / `fix:` / `chore:` convention.
- **`.gitignore`** excludes: `.env` (secrets), `data/` (generated files,
  caches, vector databases), `venv/`, `__pycache__/`. Only source and docs
  are tracked.
- Secrets are **never committed.** Only `.env.example` (placeholder values)
  is tracked.

## 3. Documentation

- **README.md** — project overview, structure, quick-start.
- **docs/** — this 7-document KT set covering architecture, installation,
  module reference, SDLC, sprint plan and QA.
- **In-code documentation** — module and function docstrings.
- **Change record** — git commit history records every change with author,
  timestamp and message.

## 4. Testing

Unit tests live under `tests/` and run with **pytest**:

```bash
pip install pytest
pytest tests/ -v
```

### test_smoke.py (9 offline tests — no network, no ML models)

| Test | What it verifies |
|------|-----------------|
| `test_paths_defined` | `BASE_DIR` and `DB_PATH` are not None |
| `test_is_llm_configured_returns_bool` | `is_llm_configured()` returns bool |
| `test_kpi_concepts_present` | All 5 KPIs declared in `KPI_CONCEPTS` |
| `test_kpi_value_formatting` | `$416.16B`, `$45.18M`, `6.13`, `N/A` |
| `test_gross_margin_derivation` | 180/400×100=45.0%, zero-revenue→None |
| `test_period_matching_by_duration` | 6-month YTD excluded from 10-Q |
| `test_comparison_percentage_change` | 100→120=+20%, divide-by-zero→None |
| `test_signal_bullish_on_strong_positives` | Strong inputs → BULLISH |
| `test_signal_neutral_on_missing_data` | Empty inputs → NEUTRAL, no crash |

### test_parser.py
Filing parser unit tests for HTML cleaning and section segmentation.

### test_filing_parser.py, test_chunker.py, test_sentiment.py (Sprint 1)
HTML cleaning, chunking behaviour and tone aggregation logic.

## 5. Error handling and robustness

- All external calls (SEC EDGAR, Groq API) retry with exponential backoff
  (up to `MAX_RETRIES=4`, base `BACKOFF_BASE=1.5s`).
- Missing XBRL fields → `None` (graceful, never a crash).
- Missing LLM key → placeholder messages (KPI, tone, signal still run).
- Pipeline returns `{"error": "..."}` on failure — UI displays it cleanly.
- Missing XBRL concept tag → next tag in priority list tried.
- Zero-revenue → Gross Margin returns `None` (no divide-by-zero).
- ChromaDB batch failure → falls back to chunk-by-chunk (never crashes).
- Legacy SQLite rows (pre-`guidance`/`risks_json` columns) handled by
  `_migrate()` — idempotent, non-destructive.

## 6. QA checklist — Sprint 1 + Sprint 2 (Final)

- [x] PEP 8 / Black / isort configured in `pyproject.toml`
- [x] Consistent naming conventions throughout
- [x] Type hints and docstrings on all public APIs
- [x] Named-branch git workflow with Pull Requests
- [x] `.gitignore` protecting secrets and generated data
- [x] README + 7-document KT docs set
- [x] 9 offline smoke tests passing (`pytest tests/test_smoke.py`)
- [x] Graceful error handling and retries for all external calls
- [x] Secrets isolated in `.env` (never committed)
- [x] Golden Rule enforced: XBRL for numbers, LLM for words only
- [x] Multi-level caching (HTML, ChromaDB, LLM responses, SQLite)
- [x] Duration-aware XBRL period matching (prevents inflated 10-Q growth)
- [x] Skip-if-indexed caching in indexer (no redundant re-embedding)
- [x] Batched FinBERT inference with fallback
- [x] Idempotent SQLite migration (`_migrate()`)

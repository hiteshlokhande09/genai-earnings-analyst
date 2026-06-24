# 06 — Quality Assurance

This document addresses **Evaluation Criterion 1 (Quality Assurance
Practices)**: coding standards, version control, and documentation/change
records.

## 1. Coding standards & naming conventions

* **PEP 8** is followed throughout (the Python style standard).
* **Black** (line length 88) and **isort** are configured in `pyproject.toml`
  to enforce consistent formatting and import ordering automatically.
* **Naming conventions:**
  * modules and functions: `snake_case`
  * classes: `PascalCase` (where used)
  * constants: `UPPER_SNAKE_CASE` (e.g. `CHUNK_SIZE`, `RAG_TOP_K`)
  * private helpers: leading underscore (e.g. `_request`, `_get_model`)
* **Type hints** annotate all public function signatures.
* **Docstrings** document every module and public function (purpose, params,
  returns).
* **Single responsibility:** each module maps to exactly one pipeline stage.

## 2. Version control

* **git** is used for all source code and documentation.
* The repository is hosted on **GitHub**.
* **`.gitignore`** excludes secrets (`.env`), runtime data (`data/`), caches and
  virtual environments, so only source and docs are tracked.
* Commits are made incrementally, each representing a logical change — the
  commit history doubles as the project's change record (an Agile artifact).
* Secrets are **never** committed; only `.env.example` (a template) is tracked.

## 3. Documentation & change records

* **README.md** — overview, structure, setup, usage.
* **docs/** — architecture, installation, module reference, SDLC, sprint plan,
  and this QA document.
* **In-code documentation** — module and function docstrings.
* **Change record** — the git commit history records every change with author,
  timestamp and message. Sprint scope changes are reflected in
  `docs/05_team_and_sprint_plan.md`.

## 4. Testing

* Unit tests live under `tests/` and run with **pytest**.
* Coverage focuses on **network-independent logic** that can be tested
  deterministically without external services:
  * `test_filing_parser.py` — HTML cleaning and section segmentation
  * `test_chunker.py` — chunking behaviour and edge cases
  * `test_sentiment.py` — tone aggregation logic
* Run with:
  ```bash
  pip install pytest
  pytest
  ```

## 5. Error handling & robustness

* All external calls (SEC EDGAR, Llama 3) retry with exponential backoff.
* The pipeline returns structured `{"error": ...}` results rather than raising,
  so the UI fails gracefully.
* Missing API keys produce clear placeholder output instead of crashes.
* The dashboard wraps pipeline execution in a try/except and surfaces any error
  on screen rather than showing a blank page.

## 6. QA checklist (Sprint 1)

- [x] PEP 8 / Black / isort configured
- [x] Consistent naming conventions
- [x] Type hints and docstrings on all public APIs
- [x] git version control with `.gitignore` protecting secrets
- [x] README + docs/ documentation set
- [x] Unit tests for core logic
- [x] Graceful error handling and retries
- [x] Secrets isolated in `.env` (never committed)

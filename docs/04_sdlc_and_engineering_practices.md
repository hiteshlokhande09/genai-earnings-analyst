# 04 — SDLC Methodology & Engineering Practices

This document addresses **Evaluation Criterion 2 (Software Engineering
Principles)**: SDLC methodology selection and justification, engineering
practices applied, and availability of design and requirement documents.

## 1. SDLC methodology: Agile / Scrum

We selected **Agile implemented through the Scrum framework**.

### Why Agile/Scrum

- **Iterative delivery suits an AI pipeline.** The system is a 17-stage
  sequence. Building and validating one working increment at a time (ingestion
  → RAG → NLP → KPI → output) reduces integration risk compared to designing
  the whole system upfront.
- **Fixed review checkpoints map directly to sprints.** The mid-semester and
  end-semester evaluations are Sprint Reviews in Scrum terms. This makes the
  academic timeline and the development cadence identical.
- **Requirements evolved.** During Sprint 2 the LLM provider changed from a
  locally hosted model to the Groq cloud API. Agile accommodates this without
  a heavyweight change control process — the change is documented in this doc
  and the code is provider-agnostic through environment variables.
- **Small team.** Scrum scales down well to four people; heavyweight
  ceremonies are replaced with lightweight check-ins.

### How Scrum is applied

| Scrum concept | In this project |
|---------------|-----------------|
| Product backlog | The 17 SRS system functions |
| Sprint backlog | Per-member file ownership for the sprint |
| Increment | A working, demonstrable pipeline slice each sprint |
| Sprint review | Mid-semester (Sprint 1) and end-semester (Sprint 2) |
| Sprint 1 | Steps 1–8: ingestion, RAG, FinBERT, Llama 3, basic dashboard |
| Sprint 2 | Steps 9–17: XBRL KPIs, comparison, signal, charts, PDF, history, landing |

### LLM deployment change (Sprint 1 → Sprint 2)

The original plan used a locally hosted Llama 3 model. During Sprint 2 this
was changed to the **Groq cloud API** (free tier, OpenAI-compatible endpoint).
Reasons: lower local hardware requirements, improved latency, no GPU needed.
The change is transparent to the rest of the code — the provider is fully
configured through `LLAMA3_API_KEY`, `LLAMA3_BASE_URL` and `LLAMA3_MODEL`
environment variables. Swapping providers requires no code changes.

## 2. Engineering practices applied

### Separation of concerns / modularity
One module per pipeline stage, each with a single responsibility. `pipeline.py`
is the only file that knows the order of stages — every other module is
independently testable and replaceable.

### The Golden Rule (enforced architecturally)
Financial figures always come from XBRL (`kpi_extractor.py`). The LLM is
called only for narrative text. This is not just a guideline — the code
physically separates the two paths and the LLM is never asked for numbers.

### `src/` package layout
Industry-standard structure that isolates the importable package from project
files, prevents accidental imports from the working directory, and supports
clean testing.

### Configuration centralisation
All settings and secrets flow through `core/config.py`. No other module
hard-codes a URL, model name, chunk size or timeout. Changing a parameter
requires editing one file.

### Secrets management
API keys live only in a git-ignored `.env` file, loaded via `python-dotenv`.
Only `.env.example` (a template with no real values) is committed.

### Defensive programming
- All SEC EDGAR and Groq API calls use `_get()` / `_chat()` with up to 4
  retries and exponential backoff (base 1.5s).
- Missing XBRL fields degrade to `None` — never a crash.
- Missing LLM key returns placeholder messages — the KPI and tone pipeline
  still runs.
- The pipeline returns `{"error": "..."}` rather than raising exceptions.

### Multi-level caching
- Filing HTML cached to `data/cache/` — no repeated EDGAR downloads.
- ChromaDB collections cached per filing — `indexer.py` skips re-embedding
  if the collection exists.
- Llama 3 responses cached in SQLite (`llm_cache` table) — same filing never
  re-sent to the API.
- Full analysis cached in SQLite (`analysis_results`) — repeated loads are
  instant.

### Lazy model loading
FinBERT and the Sentence Transformer embedding model use module-level
singletons (`_PIPELINE`, `_MODEL`) and load on first use. App startup is fast
even on a cold machine.

### Batched FinBERT inference
`sentiment.py` sends all chunks to FinBERT in a single batched call
(`batch_size=16`), significantly reducing per-chunk overhead on CPU. A
fallback to chunk-by-chunk processing handles environments where batching
fails.

### Type hints and docstrings
Every module has a module-level docstring explaining its purpose. Every public
function has a docstring explaining parameters, return values and any notable
behaviour. All public signatures are type-annotated.

### Automated tests
Nine offline smoke tests in `tests/test_smoke.py` cover: config paths, KPI
formatting, Gross Margin derivation, period-matching correctness, comparison
engine (20% growth case), Bull/Bear signal (two scenarios). No network or ML
models required — tests run in seconds.

### Tooling configuration
`pyproject.toml` configures Black (line length 88), isort and pytest,
enforcing consistent formatting and import ordering across all contributions.

## 3. Design and requirement documents

| Document | Location |
|----------|----------|
| Software Requirements Specification (SRS) | submitted separately |
| Design Document | submitted separately |
| System architecture and pipeline | `docs/01_architecture_and_design.md` |
| Module reference | `docs/03_module_reference.md` |
| Sprint plan and backlog | `docs/05_team_and_sprint_plan.md` |
| Quality assurance | `docs/06_quality_assurance.md` |

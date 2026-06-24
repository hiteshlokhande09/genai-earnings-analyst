# 04 — SDLC Methodology & Engineering Practices

This document addresses **Evaluation Criterion 2 (Software Engineering
Principles)**: selection and justification of the SDLC methodology, application
of engineering practices, and availability of design/requirement documents.

## 1. SDLC methodology: Agile (Scrum)

We selected an **Agile methodology implemented through the Scrum framework**.

### Why Agile/Scrum (justification)

* **Iterative delivery suits an AI pipeline.** The system is naturally a
  sequence of stages (ingest → RAG → models → output). Building and validating
  one working increment at a time reduces integration risk.
* **Fixed review checkpoints map to sprints.** The mid-semester and
  end-semester reviews correspond exactly to two sprint reviews, so Scrum's
  cadence fits the academic timeline.
* **Requirements were understood but the implementation evolved.** Agile
  accommodates refinement (e.g. adding section-aware chunking, a filing-date
  picker) without a heavyweight change process.
* **Small team.** Scrum's lightweight roles and ceremonies scale down well to a
  four-person team.

### How Scrum is applied here

| Scrum concept | In this project |
|---------------|-----------------|
| Product backlog | The 17 SRS system functions |
| Sprint backlog | Per-member deliverables for the sprint |
| Increment | A working, demonstrable slice each sprint |
| Sprint review | Mid-sem and end-sem evaluations |
| Sprint 1 | Steps 1–8 (ingestion + RAG + AI models) |
| Sprint 2 | Steps 9–12 (comparison, charts, report, deploy) |

We use lightweight check-ins rather than formal daily stand-ups, which is
appropriate for a team of this size.

## 2. Software engineering practices applied

* **Separation of concerns / modularity.** One module per pipeline stage, each
  with a single responsibility. Modules depend only on `config` and their
  immediate inputs.
* **`src/` package layout.** Industry-standard structure that isolates the
  importable package from project files and supports clean testing.
* **Configuration centralisation.** All settings and secrets flow through
  `core/config.py`; nothing is hard-coded elsewhere.
* **Secrets management.** API keys live only in a git-ignored `.env` file,
  loaded via `python-dotenv`. A committed `.env.example` documents the format.
* **Defensive programming.** External calls (SEC, LLM) retry with exponential
  backoff and degrade gracefully (placeholders, fallbacks) instead of crashing.
* **Lazy initialisation.** Heavy models load on first use to keep startup fast.
* **Type hints and docstrings.** Every module and public function is documented
  and type-annotated.
* **Automated tests.** Network-independent logic (parser, chunker, sentiment
  aggregation) is covered by unit tests under `tests/`.
* **Tooling configuration.** `pyproject.toml` configures Black (formatting),
  isort (imports) and pytest, enforcing a consistent style.

## 3. Design & requirement documents

| Document | Location |
|----------|----------|
| Software Requirements Specification (SRS) | provided separately |
| Architecture & design | `docs/01_architecture_and_design.md` |
| Module-level design reference | `docs/03_module_reference.md` |
| Sprint plan & backlog | `docs/05_team_and_sprint_plan.md` |
| Quality assurance plan | `docs/06_quality_assurance.md` |

Together these satisfy the "availability of design and requirement documents"
requirement.

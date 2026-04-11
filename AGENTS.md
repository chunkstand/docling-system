# Project Scope

This repository implements the Docling PDF ingestion and retrieval system described in `SYSTEM_PLAN.md`, `README.md`, and the rebuilt v1 plan.

Scope for this project:

- build the full local app in this repository
- use the recommended implementation choices by default when questions arise
- continue implementation through completion rather than stopping at intermediate scaffolding
- verify behavior at each milestone before committing
- keep the system aligned to the v1 goals: PDF ingest, durable DB-backed runs, validation-gated active-run promotion, OpenAI-backed embeddings, table-first retrieval, REST API, Dockerized local development, and tests

# Default Decisions

Unless the user says otherwise, prefer:

- FastAPI for the API
- SQLAlchemy plus Alembic for persistence and migrations
- psycopg with Postgres plus pgvector
- Docker Compose for local infrastructure
- one polling worker process with concurrency-safe DB leasing
- local filesystem storage rooted in this repository's `storage/` directory
- direct artifact download endpoints instead of exposing raw filesystem paths
- OpenAI as the provider, with `text-embedding-3-small` for the pinned 1536-dimension embedding contract
- YAML as the human-readable artifact format, with JSON as the canonical machine-readable artifact format
- local-file operator ingest through `docling-system-ingest-file`; keep public HTTP ingest upload-based unless explicitly changed

# Current System Contracts

- `docling.json` is the canonical machine-readable document parse artifact.
- `document.yaml` is the human-readable document artifact.
- Table JSON is canonical; table YAML is human-readable.
- Figures are first-class persisted outputs with JSON/YAML artifacts and provenance metadata.
- YAML must remain derived output, not a source of truth for search, ranking, filtering, validation, or persistence.
- Tables are first-class retrieval objects with persisted logical tables, source segments, merge metadata, audit metadata, and table JSON/YAML artifacts.
- `documents.active_run_id` may advance only after document and table validations pass.
- Failed validation runs must remain non-active, and prior active content must remain unchanged.
- `table_id` is run-scoped. `logical_table_key` is best-effort lineage and may be null.
- `/search` is the immediate mixed typed response for chunks and tables.
- Mixed-search filters are limited to `document_id`, `page_range`, and optional `result_type`.
- Local path ingest is CLI-only, constrained by allowed roots, symlink rejection, PDF validation, size limits, page limits, and checksum dedupe.
- Run evaluations are first-class persisted records with summary and per-query detail.
- `GET /documents/{document_id}/evaluations/latest` is the top-level persisted evaluation detail endpoint for the document's latest run.
- `GET /documents/{document_id}/figures` and `GET /documents/{document_id}/figures/{figure_id}` are top-level figure inspection endpoints for the active run.
- Table supplements are registry-driven from `config/table_supplements.yaml`; keep chapter PDFs as the canonical source documents and treat supplement PDFs as narrowly-scoped repair inputs for specific bad table families.
- Supplement overlays must preserve the chapter-local page span and original source-segment provenance of the replaced logical tables.
- When a new chapter PDF needs supporting clean tables, add the clean PDF as a supplement input, not as a second canonical document.
- Pair every supplement rule with fixed-corpus evaluation coverage in `docs/evaluation_corpus.yaml`, including `expected_merged_tables` checks for the repaired family where possible.
- For supplement-backed repairs, verify both retrieval queries and `summary.structural_passed` from `GET /documents/{document_id}/evaluations/latest` or `docling-system-eval-run`.

# Bitter Lesson Guidance

- preserve and strengthen the parts of the system that scale with more data, more compute, and better models: durable runs, stored artifacts, eval corpora, retrieval telemetry, and validation-gated promotion
- treat parser heuristics, table merge rules, caption attachment rules, and ranking boosts as short-term scaffolding for v1, not as the long-term moat
- prefer investments that improve general search and learning loops over investments that only encode more document-specific human knowledge
- when choosing between a new hand-written heuristic and better eval coverage, richer provenance, or a cleaner model/reranking interface, prefer the latter unless a heuristic is required to keep the system buildable and testable now
- keep enough raw provenance and intermediate artifacts to support future learned reranking, learned merge decisions, and learned figure/table resolution without re-architecting storage or APIs
- do not let YAML, manually curated rules, or ad hoc post-processing become hidden sources of truth; keep structured DB fields and canonical JSON artifacts as the machine-facing contract
- bias new retrieval work toward generic recall plus reranking and measurable eval improvements, not toward a growing collection of query-shape special cases
- if a heuristic is added, pair it with a regression test and document it as a provisional rule that may later be replaced by a more general method
- when a document-specific repair is unavoidable, prefer a registry entry plus provenance-preserving overlay over more parser hardcoding or splitting the corpus into many primary PDFs
- prefer explicit merge expectations in evaluation fixtures over hand-inspecting artifact JSON after every repair; artifact inspection is a verification aid, not the durable contract

# Working Rules

- implement milestone by milestone
- run verification at each milestone
- commit milestone changes as you go
- avoid scope drift beyond the v1 system plan unless required to make the system buildable and testable
- restart API/worker after environment, migration, or runtime dependency changes before live verification
- when OpenAI returns `429 insufficient_quota`, treat it as a quota/billing/key-project issue; ingestion may still validate and promote without embeddings, but semantic search degrades to keyword-backed behavior

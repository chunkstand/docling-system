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
- YAML must remain derived output, not a source of truth for search, ranking, filtering, validation, or persistence.
- Tables are first-class retrieval objects with persisted logical tables, source segments, merge metadata, audit metadata, and table JSON/YAML artifacts.
- `documents.active_run_id` may advance only after document and table validations pass.
- Failed validation runs must remain non-active, and prior active content must remain unchanged.
- `table_id` is run-scoped. `logical_table_key` is best-effort lineage and may be null.
- `/search` is the immediate mixed typed response for chunks and tables.
- Mixed-search filters are limited to `document_id`, `page_range`, and optional `result_type`.
- Local path ingest is CLI-only, constrained by allowed roots, symlink rejection, PDF validation, size limits, page limits, and checksum dedupe.

# Working Rules

- implement milestone by milestone
- run verification at each milestone
- commit milestone changes as you go
- avoid scope drift beyond the v1 system plan unless required to make the system buildable and testable
- restart API/worker after environment, migration, or runtime dependency changes before live verification
- when OpenAI returns `429 insufficient_quota`, treat it as a quota/billing/key-project issue; ingestion may still validate and promote without embeddings, but semantic search degrades to keyword-backed behavior

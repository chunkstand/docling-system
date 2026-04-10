# docling-system

Docling-based PDF ingestion and retrieval system for plumbing-code knowledge.

## What It Does

This system ingests PDF code books, parses them with Docling, stores versioned run artifacts, validates prose chunks and logical tables, and promotes only validation-passing runs to active search. Retrieval is exposed through a local REST API and a read-only browser UI.

The current workflow is operator-driven: use the CLI to ingest local PDFs, then use the API or UI to inspect documents, tables, artifacts, validation status, metrics, and mixed chunk/table search.

## Current Contracts

- `docling.json` is the canonical machine-readable document parse artifact.
- `document.yaml` is the human-readable document artifact.
- Table JSON is the canonical machine-readable table artifact.
- Table YAML is the human-readable table artifact.
- YAML is derived output, not a second source of truth.
- Search, ranking, filtering, validation, and persistence use normalized database fields and structured objects, not reparsed YAML.
- `documents.active_run_id` advances only after document and table validations pass.
- A failed validation run remains non-active, and the prior active run remains unchanged.
- `/search` is the immediate mixed typed search contract for both chunks and tables.
- `table_id` is run-scoped. `logical_table_key` is best-effort cross-run lineage and can be null.

## Stack

- FastAPI REST API
- SQLAlchemy, Alembic, psycopg
- Postgres with pgvector
- Docling PDF parsing
- OpenAI embeddings with `text-embedding-3-small` and a pinned 1536-dimension contract
- One polling worker with DB-backed leasing and retries
- Local filesystem storage under `storage/`
- Docker Compose for local Postgres
- Read-only local UI mounted at `http://localhost:8000/`

## Local Setup

1. Copy `.env.example` to `.env`.
2. Set `DOCLING_SYSTEM_OPENAI_API_KEY` if semantic embeddings should be generated.
3. Start Postgres:

```bash
docker compose up -d db
```

4. Install dependencies:

```bash
uv sync --extra dev
```

5. Run migrations:

```bash
uv run alembic upgrade head
```

6. Start the API:

```bash
uv run docling-system-api
```

7. Start the worker in a second shell:

```bash
uv run docling-system-worker
```

8. Open the UI:

```text
http://localhost:8000/
```

## Ingesting PDFs

Local-file ingest is CLI-only:

```bash
uv run docling-system-ingest-file /absolute/path/to/file.pdf
```

The CLI passes through the same checksum dedupe, run queue, worker processing, validation gate, and active-run promotion path as upload ingest.

Local path ingest policy:

- Paths must be under configured allowed roots.
- If `DOCLING_SYSTEM_LOCAL_INGEST_ALLOWED_ROOTS` is unset, the default roots are the repo working directory and `~/Documents`.
- Symlink file paths are rejected.
- Files must have a `.pdf` suffix and a `%PDF-` header.
- Duplicate content is deduped by checksum, not by path string.
- File size defaults to `104857600` bytes.
- Page count defaults to a maximum of `750` pages.

`POST /documents` remains multipart upload-based for compatibility. No arbitrary path-based ingest is exposed through public HTTP.

## API Overview

- `GET /health`
- `GET /metrics`
- `GET /documents`
- `POST /documents`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/chunks`
- `GET /documents/{document_id}/tables`
- `GET /documents/{document_id}/tables/{table_id}`
- `GET /documents/{document_id}/artifacts/json`
- `GET /documents/{document_id}/artifacts/yaml`
- `GET /documents/{document_id}/tables/{table_id}/artifacts/json`
- `GET /documents/{document_id}/tables/{table_id}/artifacts/yaml`
- `POST /documents/{document_id}/reprocess`
- `POST /search`

## Search Contract

`POST /search` returns one ranked list containing typed results:

- `result_type: "chunk"` for prose chunk hits
- `result_type: "table"` for logical table hits

Supported modes:

- `keyword`
- `semantic`
- `hybrid`

Supported filters:

- `document_id`
- `page_range`
- `result_type`

Keyword, semantic, and hybrid modes search active chunks and active tables independently, then merge results deterministically. Query embeddings are computed once per request and reused for chunk and table semantic retrieval. If embeddings fail, the system degrades to keyword-backed retrieval instead of blocking validated ingestion.

## Tables

Tables are first-class retrieval objects. The parser stores logical tables, source table segment provenance, merge metadata, repeated-header removal metadata, and audit hashes. Continued tables can be merged into one logical table when the evidence is strong enough; ambiguous continuation candidates are recorded instead of guessed.

Table telemetry is available from `GET /metrics`, including detected tables, persisted logical tables, segment counts, continuation merges, ambiguous continuations, table embedding failures, and table search hits.

## Useful Commands

```bash
uv run pytest tests
uv run pytest tests/unit
uv run alembic upgrade head
uv run docling-system-cleanup
uv run docling-system-ingest-file /absolute/path/to/file.pdf
```

## Evaluation

The fixed evaluation contract lives in [docs/evaluation_corpus.yaml](./docs/evaluation_corpus.yaml). It records the mixed-search rollout mode, embedding contract, target document types, and threshold checks for table counts, continued-table merges, golden table queries, prose queries, figure counts, figure artifact/provenance coverage, expected figure captions, and unexpected merge/split tolerance.

## Troubleshooting

If the worker logs `429 insufficient_quota` from OpenAI, the API key is authenticating but the OpenAI project behind that key does not have usable quota or billing. Ingest still completes when validation passes, but embeddings are not stored and semantic search falls back to keyword-backed behavior.

After changing `DOCLING_SYSTEM_OPENAI_API_KEY`, restart the API and worker. Existing runs need to be reprocessed to generate embeddings with the new key.

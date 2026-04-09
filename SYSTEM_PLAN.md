# Docling System Plan

## Summary

Build a PDF ingestion and retrieval system around Docling. The system accepts PDFs, parses them into structured machine-readable output, stores both canonical parse artifacts and retrieval chunks, and exposes search over keyword and semantic indexes.

## Concise Note

This system is a Docling-based PDF pipeline that converts documents into structured artifacts and searchable chunks. It combines filesystem-backed artifact storage, Postgres plus pgvector retrieval, and a simple REST interface for ingestion, status tracking, and search.

Default v1 decisions:

- Python service and worker
- Docling for parsing and chunk derivation
- Postgres + pgvector for storage and retrieval
- local filesystem for raw files and derived artifacts
- REST API as the first interface

## Architecture

Core components:

1. API service
   - accepts uploads or trusted local file-path ingestion
   - creates document records and enqueueable work
   - exposes document status and search endpoints

2. Ingestion worker
   - validates PDFs
   - computes checksums
   - runs Docling
   - writes canonical JSON and Markdown artifacts
   - derives chunks and embeddings
   - persists searchable rows

3. Postgres database
   - stores documents, chunks, status, and metadata
   - supports full-text search and vector similarity

4. Filesystem storage
   - stores original PDFs plus generated JSON and Markdown
   - uses deterministic paths so artifacts are inspectable

5. Embedding provider
   - converts chunk text into vectors
   - must be abstracted behind a provider interface

## Data Flow

1. Client uploads a PDF or provides a local file path.
2. API creates a documents row with status queued.
3. Worker copies the source PDF into managed storage.
4. Worker computes `sha256` and rejects exact duplicates.
5. Worker runs Docling and produces:
   - canonical JSON
   - Markdown
   - structured chunk source
6. Worker normalizes chunks with provenance like page range and heading.
7. Worker generates embeddings for each chunk.
8. Worker writes document and chunk rows.
9. Status becomes `completed` or `failed`.
10. Search clients query keyword, semantic, or hybrid retrieval.

## Storage and Schema

Recommended local storage tree:

```text
storage/
  source/<document-id>.pdf
  parsed/<document-id>.json
  parsed/<document-id>.md
```

### `documents`

Suggested columns:

- `id` uuid primary key
- `source_filename` text
- `storage_path` text
- `sha256` text unique
- `mime_type` text
- `title` text nullable
- `status` text
- `error_message` text nullable
- `docling_json` jsonb
- `markdown` text
- `page_count` integer nullable
- `metadata` jsonb default `{}`
- `created_at` timestamptz
- `updated_at` timestamptz

### `document_chunks`

Suggested columns:

- `id` uuid primary key
- `document_id` uuid references `documents(id)` on delete cascade
- `chunk_index` integer
- `text` text
- `heading` text nullable
- `page_from` integer nullable
- `page_to` integer nullable
- `metadata` jsonb default `{}`
- `embedding` vector
- `textsearch` generated `tsvector`
- `created_at` timestamptz

Recommended indexes:

- unique `(document_id, chunk_index)`
- GIN on `textsearch`
- HNSW on `embedding`

### `ingestion_jobs`

Optional in v1. If async handling is needed immediately, store queue state in a dedicated table. Otherwise, keep status on `documents` and add a jobs table in the second pass.

## API Plan

### `POST /documents`

Accept multipart PDF upload or a trusted local file path. Return `document_id` and current status.

### `GET /documents/{id}`

Return metadata, processing status, and artifact locations.

### `GET /documents/{id}/chunks`

Return normalized chunks with provenance.

### `POST /search`

Request fields:

- `query`
- `mode`: `keyword`, `semantic`, or `hybrid`
- `filters`
- `limit`

Response fields:

- chunk id
- document id
- score
- chunk text
- heading
- page range
- source filename

## Retrieval Design

### Keyword retrieval

Use Postgres full-text search over chunk text plus heading.

### Semantic retrieval

Use pgvector cosine similarity over chunk embeddings.

### Hybrid retrieval

For v1:

- fetch top N vector matches
- fetch top N keyword matches
- normalize scores
- merge by chunk id
- return the highest combined ranks

Important implementation note:

When pgvector ANN indexes are combined with strict metadata filters, recall can drop. Over-fetch candidates before filtering or tune HNSW search settings when needed.

## Worker Rules

Success path:

- validate file type
- compute checksum
- deduplicate
- run Docling
- persist artifacts
- chunk the document
- embed chunks
- write rows
- mark complete

Failure path:

- capture parser, storage, embedding, and database errors separately
- mark document failed
- retain original file if already copied

Idempotency:

- deduplicate by checksum
- allow safe reprocessing of an existing document
- make chunk replacement deterministic

## Recommended Project Layout

```text
docling-system/
  app/
    api/
    workers/
    services/
    db/
    models/
  storage/
  tests/
  SYSTEM_PLAN.md
  README.md
  pyproject.toml
  .env.example
```

## Milestones

### Milestone 1

- scaffold Python project
- connect Postgres
- create schema and migrations

### Milestone 2

- implement PDF ingest endpoint
- store source files
- run Docling and persist JSON plus Markdown

### Milestone 3

- derive normalized chunks
- generate embeddings
- implement keyword, semantic, and hybrid search

### Milestone 4

- add retries and reprocessing
- improve logging and duplicate handling

### Milestone 5

- add a lightweight UI
- optionally swap filesystem storage for S3-compatible storage

## Test Plan

Unit tests:

- checksum and deduplication
- chunk normalization
- hybrid rank merge
- status transitions

Integration tests:

- ingest a small PDF end to end
- persist document plus chunks
- retrieve by keyword

# Rebuilt Docling System Plan (v1)

## Summary

Build a small, durable PDF ingestion and retrieval system around Docling.

The system accepts PDF uploads, parses them into structured artifacts, stores canonical parse outputs and retrieval chunks, and exposes keyword, semantic, and hybrid search. It uses:

- Python API + worker
- Docling for extraction and chunk source
- Postgres + pgvector for retrieval storage
- local filesystem for source PDFs and derived artifacts
- REST API for ingestion, status, reprocessing, and search

This revision keeps the original scope, but hardens the design in five places that are necessary for v1:

1. public ingest is upload-only
2. async processing is durable
3. reprocessing is versioned and atomically promoted
4. embeddings are pinned to one model/dimension in v1
5. search filters are explicit and indexed

---

## Review closure

| Review finding | v1 decision |
|---|---|
| Local file-path ingest had no trust boundary | Remove path-based ingest from the public API in v1 |
| Async work lacked durable ownership | Make a DB-backed run queue mandatory |
| Reprocessing could expose mixed chunks | Version every processing attempt with `run_id` and promote atomically |
| Embedding provider was abstract but schema was not | Pin one embedding model and vector dimension in v1 |
| Search filters were undefined | Define a small indexed filter surface |
| Status model was too loose | Use explicit run states and transition rules |
| Duplicate handling was ambiguous | Make upload idempotent by checksum and return the existing document |
| Tests missed risk scenarios | Add duplicate, retry, parser-failure, reprocess, semantic, and filtered-search tests |

---

## v1 decisions

### 1. Ingest contract

`POST /documents` accepts **multipart PDF upload only**.

Path-based ingestion is **not exposed on the REST API in v1**. If local-path import is needed for development or one-off admin work, do it with an internal script or shell command outside the public API.

### 2. Duplicate contract

The system is **idempotent by file checksum**.

- API computes `sha256` for the uploaded PDF before creating new work.
- If the checksum already exists and the document has an `active_run_id`, the API returns the existing `document_id` and does **not** create a new document or new run.
- If the checksum already exists but the document has **no active successful run**, the API creates a new recovery run for that existing document and returns `202 Accepted`.
- Responses for duplicate uploads include `duplicate: true`.

This keeps duplicates simple and predictable.

### 3. Reprocessing contract

Reprocessing is explicit.

Use `POST /documents/{id}/reprocess` to create a new processing run for an existing stored source PDF.

Reprocessing does **not** create a second logical document. It creates a new versioned run for the same document.

### 4. Durable async model

A processing run is also the durable queue record.

Every document processing attempt gets a row in `document_runs`. That row carries both:

- run/version metadata
- worker lease and retry fields

So v1 does **not** need a separate queue product or external broker.

### 5. Atomic promotion model

Search never reads “whatever chunks happen to exist.”

Instead:

- every run writes chunks under its own `run_id`
- `documents.active_run_id` points to the one visible version
- only after the full run succeeds does the worker atomically promote that run to active

If a reprocess fails halfway through, the old active version stays visible.

### 6. Embeddings in v1

The embedding provider stays abstract at the code boundary, but the storage contract is fixed in v1.

- choose one embedding model before migrations
- pin one vector dimension in schema
- store `embedding_model` on each run
- changing models later requires a planned migration or a new embedding column/index set

### 7. Search filters in v1

Supported filters are intentionally small:

- `document_id`
- `page_range`

No arbitrary JSONB filtering in v1.

Filter semantics:

- `document_id` is exact match
- `page_range` uses inclusive overlap semantics against chunk `page_from/page_to`
- `source_filename` remains document metadata, but is **not** a v1 search filter because one canonical document may be uploaded under multiple filenames over time

---

## Architecture

### Core components

1. **API service**
   - accepts PDF uploads
   - computes checksum
   - resolves duplicates
   - creates document and run records
   - exposes status, chunks, reprocess, and search endpoints

2. **Ingestion worker**
   - claims due runs with a DB lease
   - validates PDFs
   - runs Docling
   - writes JSON and Markdown artifacts
   - derives retrieval chunks and embeddings
   - atomically promotes successful runs

3. **Postgres database**
   - stores documents, runs, chunks, state, and retrieval metadata
   - supports full-text search and vector similarity

4. **Filesystem storage**
   - stores source PDFs and versioned derived artifacts
   - uses deterministic paths for easy inspection

5. **Embedding provider**
   - converts chunk text into fixed-size vectors
   - one model/dimension is pinned for v1

---

## Minimal runtime model

Keep the runtime boring and explicit:

`upload -> dedupe/gate -> queued -> processing -> completed|failed`

At the run layer, use these states:

- `queued`
- `processing`
- `retry_wait`
- `completed`
- `failed`

Transition rules:

- `queued -> processing`
- `processing -> completed`
- `processing -> retry_wait`
- `processing -> failed`
- `retry_wait -> processing`

Only leased runs may move into `processing`.

---

## Data flow

1. Client uploads a PDF to `POST /documents`.
2. API validates MIME type and writes the upload to a temporary staging file.
3. API computes `sha256`.
4. If checksum already exists and the document has an active successful run, API returns the existing document with `duplicate: true`.
5. If checksum exists and there is no active successful run, API creates a new queued recovery run for the existing document and returns that run.
6. If new, API:
   - creates a `documents` row
   - moves the file into managed storage
   - creates a first `document_runs` row with status `queued`
7. Worker claims a due run using DB lease fields.
8. Worker sets run status to `processing`.
9. Worker runs Docling and produces:
   - canonical Docling JSON artifact
   - canonical Markdown artifact
   - structured chunk source
10. Worker normalizes retrieval chunks with heading and page provenance.
11. Worker generates embeddings for each chunk.
12. Worker writes chunks under that `run_id`.
13. Worker validates the run.
14. If successful, worker atomically updates `documents.active_run_id = run_id` and marks the run `completed`.
15. If failed, worker records error state and leaves the prior active run unchanged.
16. Search reads only chunks from `documents.active_run_id`.

---

## Storage layout

Recommended local storage tree:

```text
storage/
  source/<document-id>.pdf
  runs/<document-id>/<run-id>/docling.json
  runs/<document-id>/<run-id>/document.md
```

This keeps the source PDF stable and the parsed outputs versioned.

---

## Database schema

### `documents`

Canonical logical document identity.

- `id` uuid primary key
- `source_filename` text not null
- `source_path` text not null
- `sha256` text unique not null
- `mime_type` text not null
- `title` text nullable
- `page_count` integer nullable
- `active_run_id` uuid nullable
- `latest_run_id` uuid nullable
- `created_at` timestamptz not null
- `updated_at` timestamptz not null

Notes:

- one row per unique PDF bytes
- duplicates map to the same document row
- `active_run_id` is the only version used for search and chunk reads
- `source_filename` is display metadata for the canonical document, not a guaranteed record of every upload filename

### `document_runs`

Durable processing run + queue ownership record.

- `id` uuid primary key
- `document_id` uuid not null references `documents(id)` on delete cascade
- `run_number` integer not null
- `status` text not null check (`queued`, `processing`, `retry_wait`, `completed`, `failed`)
- `attempts` integer not null default `0`
- `locked_at` timestamptz nullable
- `locked_by` text nullable
- `last_heartbeat_at` timestamptz nullable
- `next_attempt_at` timestamptz nullable
- `error_message` text nullable
- `docling_json_path` text nullable
- `markdown_path` text nullable
- `chunk_count` integer nullable
- `embedding_model` text nullable
- `embedding_dim` integer nullable
- `created_at` timestamptz not null
- `started_at` timestamptz nullable
- `completed_at` timestamptz nullable

Recommended indexes:

- unique `(document_id, run_number)`
- index on `(status, next_attempt_at)`
- index on `(locked_at)`

Lease rule:

- workers claim runs from `queued` or due `retry_wait`
- stalled `processing` runs may be re-queued if heartbeat is stale past a timeout

### `document_chunks`

Searchable retrieval rows.

- `id` uuid primary key
- `document_id` uuid not null references `documents(id)` on delete cascade
- `run_id` uuid not null references `document_runs(id)` on delete cascade
- `chunk_index` integer not null
- `text` text not null
- `heading` text nullable
- `page_from` integer nullable
- `page_to` integer nullable
- `metadata` jsonb not null default `{}`
- `embedding` vector(1536)
- `textsearch` tsvector generated always as (
  `setweight(to_tsvector('english', coalesce(heading, '')), 'A') || to_tsvector('english', coalesce(text, ''))`
  ) stored
- `created_at` timestamptz not null

Recommended indexes:

- unique `(run_id, chunk_index)`
- GIN on `textsearch`
- HNSW on `embedding`
- btree on `document_id`
- btree on `page_from`
- btree on `page_to`

Search visibility rule:

- queries must join `documents.active_run_id = document_chunks.run_id`

---

## API plan

### `POST /documents`

Accept multipart PDF upload.

**New file response**

- `202 Accepted`
- returns `document_id`, `run_id`, `status = queued`, `duplicate = false`

**Duplicate file response**

- `200 OK` if the existing document already has an active successful run
- returns `document_id`, `active_run_id`, `active_run_status`, `duplicate = true`

**Duplicate file with no active successful run**

- `202 Accepted`
- returns `document_id`, `run_id`, `status = queued`, `duplicate = true`, `recovery_run = true`

### `POST /documents/{id}/reprocess`

Create a new run for the existing stored PDF.

- `202 Accepted`
- returns `document_id`, `run_id`, `status = queued`

### `GET /documents/{id}`

Return:

- document metadata
- `active_run_id`
- `active_run_status`
- `latest_run_id`
- latest run status
- `is_searchable`
- active run artifact availability
- error information if latest run failed

Do not expose raw filesystem paths on the public API. If artifact downloads are needed, expose them through dedicated endpoints.

### `GET /documents/{id}/chunks`

Return chunks for the active run only.

### `POST /search`

Request fields:

- `query`
- `mode`: `keyword`, `semantic`, or `hybrid`
- `filters`
- `limit`

Supported filters:

- `document_id`
- `page_range`

Filter semantics:

- `document_id`: exact match
- `page_range`: inclusive overlap against chunk `page_from/page_to`

Response fields:

- `chunk_id`
- `document_id`
- `run_id`
- `score`
- `chunk_text`
- `heading`
- `page_from`
- `page_to`
- `source_filename`

### `GET /documents/{id}/artifacts/json`

Return the active run's canonical Docling JSON artifact.

### `GET /documents/{id}/artifacts/markdown`

Return the active run's canonical Markdown artifact.

---

## Retrieval design

### Keyword retrieval

Use Postgres full-text search over chunk text plus heading.

### Semantic retrieval

Use pgvector cosine similarity over the fixed-size embedding column.

### Hybrid retrieval

For v1:

1. fetch top N vector matches
2. fetch top N keyword matches
3. apply the v1 filter contract on indexed columns
4. normalize scores
5. merge by `chunk_id`
6. return the best combined ranks

Implementation note:

Approximate ANN indexes trade recall for speed. When filters are present, over-fetch vector candidates before final merge/filtering.

Keyword search should apply filters directly in SQL before ranking results. Vector search may over-fetch candidates and then apply final filtering before merge.

---

## Docling usage in this system

Docling is the canonical extractor for v1.

The worker should:

1. convert the PDF into a Docling document
2. export canonical JSON
3. export canonical Markdown
4. derive retrieval chunks from the Docling structure

Chunk normalization should preserve at least:

- `chunk_index`
- `heading`
- `page_from`
- `page_to`

The parse artifacts are canonical. Retrieval chunks are derived artifacts for search.

---

## Worker rules

### Success path

- claim a run lease
- validate PDF
- run Docling
- persist versioned artifacts
- derive chunks
- embed chunks
- write rows under `run_id`
- validate counts and outputs
- atomically promote run to `active_run_id`
- mark run `completed`

### Failure path

- classify error as retryable or terminal
- if retryable:
  - increment `attempts`
  - clear lease
  - set `status = retry_wait`
  - set `next_attempt_at`
- if terminal:
  - clear lease
  - set `status = failed`
  - record `error_message`
- never modify `active_run_id` on failure

### Idempotency and safety

- upload deduplication is by checksum
- run ownership is by DB lease
- chunk writes are versioned by `run_id`
- promotion is one DB transaction at the end

---

## Retry and lease rules

Worker claim model:

- claim one eligible run with `FOR UPDATE SKIP LOCKED`
- set `locked_at`, `locked_by`, `last_heartbeat_at`
- heartbeat while processing
- if heartbeat expires past timeout, another worker may requeue the run

Retry policy:

- bounded retries only
- exponential backoff
- terminal failure after retry limit

This is enough for v1 without bringing in an external queue.

---

## Search visibility and consistency model

Artifact writes and search writes may happen before promotion, but they are not visible to readers until promotion.

That means:

- temporary staged artifacts may exist for failed runs
- failed or partial chunks are not served
- active search results remain stable during reprocessing

So artifact generation and search storage may drift internally during a run, but externally visible state changes only when the run is promoted.

---

## Retention policy in v1

Keep retention simple:

- always retain the current active run
- retain the most recent previous successful run for rollback/debugging
- retain failed runs for a short operational window
- delete superseded older successful runs and their chunks/artifacts with an explicit cleanup job

This bounds storage growth without removing the most useful recent history.

---

## Recommended project layout

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

---

## Milestones

### Milestone 1

- scaffold Python project
- connect Postgres
- create schema and migrations for `documents`, `document_runs`, and `document_chunks`

### Milestone 2

- implement `POST /documents`
- stage upload, compute checksum, and resolve duplicates
- store source files
- enqueue first run

### Milestone 3

- implement worker claim/lease/retry model
- run Docling and persist JSON + Markdown
- derive normalized chunks

### Milestone 4

- generate embeddings
- implement keyword, semantic, and hybrid search
- add `POST /documents/{id}/reprocess`
- add atomic promotion of active run

### Milestone 5

- harden logging and operational visibility
- add cleanup for abandoned staging files and expired failed-run artifacts
- add cleanup for superseded successful runs beyond retention policy

---

## Test plan

### Unit tests

- checksum generation
- duplicate contract
- state transitions for `document_runs`
- lease claim and stale-lease requeue
- chunk normalization
- hybrid rank merge

### Integration tests

- ingest a small PDF end to end
- duplicate upload with an active successful run returns existing `document_id`
- duplicate upload with no active successful run creates a recovery run
- worker crash during processing gets retried
- parser failure marks run failed without changing active run
- reprocess writes a new run and only promotes on success
- active search remains stable during failed reprocess
- semantic search returns expected chunks
- hybrid search returns merged results
- filtered search by `document_id` and page range works with defined overlap semantics

---

## Final v1 principles

Keep the system small.

- one public ingest path
- one canonical document per checksum
- one durable DB-backed run model
- one active parse version per document
- one pinned embedding model/dimension
- one small search filter contract
- one bounded retention policy for old runs

That is enough to make the Docling pipeline production-ready without turning it into a larger platform.

# Rebuilt Docling System Plan (v1)

## Summary

Build a small, durable PDF ingestion and retrieval system around Docling.

The system accepts multipart PDF uploads through the API and trusted local-file ingest through the operator CLI, parses PDFs into structured artifacts, stores canonical parse outputs plus prose chunks and logical tables, and exposes keyword, semantic, and hybrid mixed search. It uses:

- Python API + worker
- Docling for extraction and chunk source
- Postgres + pgvector for retrieval storage
- local filesystem for source PDFs and derived artifacts
- REST API for upload ingestion, status, reprocessing, table/chunk inspection, metrics, artifacts, and search

This revision keeps the original scope, but hardens the design in five places that are necessary for v1:

1. public HTTP ingest is upload-only; local path ingest is CLI-only and policy-constrained
2. async processing is durable
3. reprocessing is versioned and atomically promoted only after validation
4. embeddings are pinned to one model/dimension in v1
5. search filters are explicit and indexed
6. tables are first-class retrieval objects with JSON/YAML artifacts and segment provenance

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

Path-based ingestion is **not exposed on the REST API in v1**. Local-path import is supported only through the operator CLI `docling-system-ingest-file`, with allowed-root checks, symlink rejection, PDF validation, size limits, page limits, and checksum dedupe.

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

- every run writes chunks, logical tables, source table segments, and artifacts under its own `run_id`
- `documents.active_run_id` points to the one visible version
- only after document and table validations pass does the worker atomically promote that run to active

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
- optional `result_type`

No arbitrary JSONB filtering in v1.

Filter semantics:

- `document_id` is exact match
- `page_range` uses inclusive overlap semantics against chunk/table `page_from/page_to`
- `result_type` is optional and limits mixed search to `chunk` or `table`
- `source_filename` remains document metadata, but is **not** a v1 search filter because one canonical document may be uploaded under multiple filenames over time

---

## Architecture

### Core components

1. **API service**
   - accepts PDF uploads
   - computes checksum
   - resolves duplicates
   - creates document and run records
   - exposes status, chunks, tables, artifacts, metrics, reprocess, and search endpoints
   - serves the read-only local UI

2. **Ingestion worker**
   - claims due runs with a DB lease
   - validates PDFs
   - runs Docling
   - writes JSON and YAML artifacts
   - derives retrieval chunks, logical tables, table segments, and embeddings
   - validates persisted run outputs
   - atomically promotes validation-passing runs

3. **Postgres database**
   - stores documents, runs, chunks, logical tables, table segments, state, and retrieval metadata
   - supports full-text search and vector similarity

4. **Filesystem storage**
   - stores source PDFs and versioned derived artifacts
   - uses deterministic paths for easy inspection

5. **Embedding provider**
   - converts chunk text and table search text into fixed-size vectors
   - one model/dimension is pinned for v1

---

## Minimal runtime model

Keep the runtime boring and explicit:

`upload/CLI ingest -> dedupe/gate -> queued -> processing -> validating -> completed|failed`

At the run layer, use these states:

- `queued`
- `processing`
- `validating`
- `retry_wait`
- `completed`
- `failed`

Transition rules:

- `queued -> processing`
- `processing -> validating`
- `validating -> completed`
- `validating -> retry_wait`
- `validating -> failed`
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
   - human-readable document YAML artifact
   - structured chunk source
   - normalized logical tables and source table segments
10. Worker normalizes retrieval chunks with heading and page provenance.
11. Worker normalizes logical tables with titles, page provenance, merge metadata, search text, preview text, and segment provenance.
12. Worker generates embeddings for chunks and tables when OpenAI quota is available.
13. Worker writes chunks, tables, table segments, document artifacts, and table artifacts under that `run_id`.
14. Worker validates the run.
15. If successful, worker atomically updates `documents.active_run_id = run_id` and marks the run `completed`.
16. If failed, worker records error state and leaves the prior active run unchanged.
17. Search reads only chunks and tables from `documents.active_run_id`.

---

## Storage layout

Recommended local storage tree:

```text
storage/
  source/<document-id>.pdf
  runs/<document-id>/<run-id>/docling.json
  runs/<document-id>/<run-id>/document.yaml
  runs/<document-id>/<run-id>/tables/<table-index>.json
  runs/<document-id>/<run-id>/tables/<table-index>.yaml
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
- `active_run_id` is the only version used for search, chunk reads, and table reads
- `source_filename` is display metadata for the canonical document, not a guaranteed record of every upload filename

### `document_runs`

Durable processing run + queue ownership record.

- `id` uuid primary key
- `document_id` uuid not null references `documents(id)` on delete cascade
- `run_number` integer not null
- `status` text not null check (`queued`, `processing`, `validating`, `retry_wait`, `completed`, `failed`)
- `attempts` integer not null default `0`
- `locked_at` timestamptz nullable
- `locked_by` text nullable
- `last_heartbeat_at` timestamptz nullable
- `next_attempt_at` timestamptz nullable
- `error_message` text nullable
- `docling_json_path` text nullable
- `yaml_path` text nullable
- `chunk_count` integer nullable
- `table_count` integer nullable
- `validation_status` text nullable
- `validation_results` jsonb not null default `{}`
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
- stalled `processing` or `validating` runs may be re-queued if heartbeat is stale past a timeout

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

### `document_tables`

Searchable logical table rows.

- `id` uuid primary key
- `document_id` uuid not null references `documents(id)` on delete cascade
- `run_id` uuid not null references `document_runs(id)` on delete cascade
- `table_index` integer not null
- `title` text nullable
- `heading` text nullable
- `logical_table_key` text nullable
- `table_version` integer nullable
- `supersedes_table_id` uuid nullable
- `lineage_group` text nullable
- `status` text not null
- `page_from` integer nullable
- `page_to` integer nullable
- `row_count` integer not null
- `col_count` integer not null
- `search_text` text not null
- `preview_text` text not null
- `metadata` jsonb not null default `{}`
- `embedding` vector(1536)
- `json_path` text nullable
- `yaml_path` text nullable
- `textsearch` tsvector generated from `title`, `heading`, and `search_text`
- `created_at` timestamptz not null

Visibility rule:

- queries must join `documents.active_run_id = document_tables.run_id`

### `document_table_segments`

Source table segment provenance for logical tables.

- `id` uuid primary key
- `table_id` uuid not null references `document_tables(id)` on delete cascade
- `run_id` uuid not null references `document_runs(id)` on delete cascade
- `segment_index` integer not null
- `source_table_ref` text not null
- `page_from` integer nullable
- `page_to` integer nullable
- `segment_order` integer not null
- `metadata` jsonb not null default `{}`
- `created_at` timestamptz not null

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
- active table count and table artifact availability
- latest validation status and whether the latest run promoted
- error information if latest run failed

Do not expose raw filesystem paths on the public API. If artifact downloads are needed, expose them through dedicated endpoints.

### `GET /documents/{id}/chunks`

Return chunks for the active run only.

### `GET /documents/{id}/tables`

Return logical table summaries for the active run only.

### `GET /documents/{id}/tables/{table_id}`

Return active-run table detail, including table metadata and source segment provenance.

### `POST /search`

Request fields:

- `query`
- `mode`: `keyword`, `semantic`, or `hybrid`
- `filters`
- `limit`

Supported filters:

- `document_id`
- `page_range`
- `result_type`

Filter semantics:

- `document_id`: exact match
- `page_range`: inclusive overlap against chunk/table `page_from/page_to`
- `result_type`: optional `chunk` or `table`

Response fields:

- `result_type`
- `document_id`
- `run_id`
- `score`
- `page_from`
- `page_to`
- `source_filename`
- chunk fields: `chunk_id`, `chunk_text`, `heading`
- table fields: `table_id`, `table_title`, `table_heading`, `table_preview`, `row_count`, `col_count`

### `GET /documents/{id}/artifacts/json`

Return the active run's canonical Docling JSON artifact.

### `GET /documents/{id}/artifacts/yaml`

Return the active run's human-readable document YAML artifact.

### `GET /documents/{id}/tables/{table_id}/artifacts/json`

Return the active run's canonical normalized table JSON artifact.

### `GET /documents/{id}/tables/{table_id}/artifacts/yaml`

Return the active run's human-readable table YAML artifact.

---

## Retrieval design

### Keyword retrieval

Use Postgres full-text search over active chunk text/headings and active table titles/headings/search text.

### Semantic retrieval

Use pgvector cosine similarity over the fixed-size embedding column for chunks and tables. Query embedding is computed once per request and reused across result types.

### Hybrid retrieval

For v1:

1. fetch top N vector matches for chunks and tables
2. fetch top N keyword matches for chunks and tables
3. apply the v1 filter contract on indexed columns
4. normalize scores deterministically
5. merge by stable object identity
6. apply deterministic table-query boost when triggered
7. return the best combined typed ranks

Implementation note:

Approximate ANN indexes trade recall for speed. When filters are present, over-fetch vector candidates before final merge/filtering.

Keyword search should apply filters directly in SQL before ranking results. Vector search may over-fetch candidates and then apply final filtering before merge.

---

## Docling usage in this system

Docling is the canonical extractor for v1.

The worker should:

1. convert the PDF into a Docling document
2. export canonical JSON
3. export human-readable document YAML derived from the same normalized document source
4. derive retrieval chunks from the Docling structure
5. derive logical tables and source table segments from Docling table objects

Chunk normalization should preserve at least:

- `chunk_index`
- `heading`
- `page_from`
- `page_to`

Docling JSON is the canonical document parse artifact. Document YAML is human-readable derived output. Table JSON is the canonical normalized table artifact. Table YAML is human-readable derived output. Retrieval chunks and table rows are derived search projections.

---

## Worker rules

### Success path

- claim a run lease
- validate PDF
- run Docling
- persist versioned artifacts
- derive chunks
- derive logical tables and source segments
- embed chunks and tables when OpenAI quota is available
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
- run Docling and persist JSON + YAML
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

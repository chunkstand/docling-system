# System Review

Date: 2026-04-18
Scope: Full repository review of the Docling ingestion, retrieval, evaluation, and agent-task system.

## Summary

This codebase is strongest in run-state discipline, auditability, evaluation/replay infrastructure, and test coverage. It is weakest at the system boundary: API exposure, upload hardening, concurrency robustness, and a few scale-sensitive retrieval and evaluation assumptions.

Verification snapshot:

- `pytest -q`: `292 passed, 14 skipped`
- `ruff check .`: not run because `ruff` was not installed in the current shell environment

## Priority 1

### Unauthenticated API is bound to all interfaces

Severity: High

Relevant files:

- `app/api/main.py:235`
- `app/api/main.py:572`
- `app/api/main.py:882`
- `app/api/main.py:943`

Issue:

The API binds to `0.0.0.0` in `app/api/main.py:943`, and mutating routes such as task creation, document ingest, and replay execution have no authentication or authorization layer. Anyone who can reach port 8000 can create tasks, upload PDFs, trigger reprocessing, and spend OpenAI-backed search or chat budget.

Why it matters:

This is the highest-risk operational weakness in the system. Even for a "local" service, binding to all interfaces without auth makes accidental network exposure materially dangerous.

Recommended direction:

- Default the API bind address to `127.0.0.1` for local mode.
- Add a simple API-key dependency for mutating endpoints if any non-local access is expected.
- Keep read-only UI and mutating API trust boundaries explicit.

### HTTP upload ingest bypasses the stricter CLI ingest safety checks

Severity: High

Relevant files:

- `app/services/documents.py:45`
- `app/services/documents.py:376`
- `app/services/documents.py:319`
- `app/services/storage.py:26`
- `app/services/cleanup.py:108`

Issue:

The public HTTP ingest path only checks MIME type or filename extension before staging the full upload. It does not enforce the CLI path-ingest file-size guard, page-count guard, or PDF header validation before durable storage. `_queue_document_run()` then moves the file into managed source storage before parsing and validation, and failed-run cleanup removes run artifacts but not the stored source PDF.

Why it matters:

Invalid, oversized, or maliciously large uploads can consume disk and operational effort while still returning `202 Accepted`. The cleanup path does not fully recover that storage.

Recommended direction:

- Apply the same PDF header, size, and page-count validation policy to HTTP ingest that the CLI path uses.
- Reject invalid uploads before moving them into durable source storage.
- Add a policy for cleaning up source files associated with permanently failed, non-active documents.

### Duplicate ingest and reprocess numbering are not concurrency-safe

Severity: High

Relevant files:

- `app/services/documents.py:327`
- `app/services/documents.py:431`
- `app/db/models.py:183`
- `app/db/models.py:215`

Issue:

Duplicate detection uses a `SELECT` followed by `INSERT` against `documents.sha256`, and reprocessing computes `MAX(run_number) + 1` before inserting into a table protected by a unique `(document_id, run_number)` constraint.

Why it matters:

Concurrent uploads of the same file or simultaneous reprocess requests can race and surface as database integrity failures instead of clean duplicate/recovery behavior.

Recommended direction:

- Convert duplicate ingest to an insert-or-recover flow that handles unique-key conflicts explicitly.
- Allocate `run_number` under row-level locking for the document, or replace `MAX + 1` with a safer sequencing approach.
- Add concurrency tests for same-checksum uploads and parallel reprocess requests.

## Priority 2

### Metadata supplement search is scale-sensitive and can miss better matches

Severity: Medium

Relevant files:

- `app/services/search.py:1412`
- `app/db/models.py:183`
- `app/db/models.py:1061`

Issue:

The prose metadata supplement path uses `ILIKE '%token%'` predicates over document title, filename, and chunk heading, then applies a coarse row limit before scoring. That pattern is unindexed for the current schema and can suppress better matches that occur later than the pre-score limit.

Why it matters:

The current approach may be acceptable for a small local corpus, but it will degrade as the corpus grows and will make query quality less predictable for prose-heavy lookups.

Recommended direction:

- Prefer indexed search primitives for supplement candidate generation.
- Move the limit later in the pipeline, after relevance scoring.
- Add corpus-size-aware performance checks around the metadata supplement stage.

### Evaluation fixtures are keyed only by basename

Severity: Medium

Relevant files:

- `app/services/evaluations.py:366`
- `app/services/evaluations.py:378`
- `app/services/evaluations.py:420`
- `app/services/documents.py:337`

Issue:

Fixture lookup and deduplication are keyed only by `source_filename`, normalized to the basename. Two unrelated documents with the same filename will shadow each other in the evaluation corpus.

Why it matters:

This weakens the durability of evaluation coverage and makes regressions harder to trust once the corpus contains repeated filenames from different directories or batches.

Recommended direction:

- Add a stronger identity for fixture matching, such as checksum or an explicit corpus document key.
- Preserve `source_filename` for operator readability, but stop using it as the sole evaluation identity.

### Agent-task dependency graph permits cycles

Severity: Medium

Relevant files:

- `app/db/models.py:867`
- `app/services/agent_tasks.py:295`
- `app/services/agent_task_worker.py:162`

Issue:

The dependency model prevents self-dependency but does not prevent multi-node cycles. A cyclic task set will remain blocked forever because unblocking only checks whether dependencies completed.

Why it matters:

This is a reliability weakness in the orchestration substrate. It will not show up in happy-path testing, but it creates silent deadlock states once the graph becomes more complex.

Recommended direction:

- Reject dependency edges that introduce cycles at task creation time.
- Add operator-visible diagnostics for tasks blocked by unresolved or cyclic dependencies.
- Cover cycle rejection in unit tests.

## Strengths

### Strong run-state discipline

- Validation-gated promotion through `documents.active_run_id` is the right contract for safe reprocessing.
- Run-scoped persistence for chunks, tables, figures, and artifacts keeps historical state auditable.
- Failed runs do not overwrite active search state.

### Strong retrieval observability

- Search requests, replay runs, harness config snapshots, and evaluation records are persisted.
- The system already supports fixed-corpus comparisons and regression tracking instead of relying on ad hoc inspection.
- Table-first retrieval is treated as a first-class concern rather than an afterthought.

### Good worker reliability foundations

- Document runs and agent tasks both use DB leasing, heartbeat updates, and stale-lease recovery.
- Runtime fingerprint registration is a thoughtful safeguard against stale workers continuing on old code.

### Good test posture

- The repository has broad unit and integration coverage across ingest, search, validation, APIs, evaluations, and agent tasks.
- The current test suite passed cleanly during review.

## Overall Assessment

The internal state model is solid. The main technical debt is concentrated at the edges:

- network exposure and missing auth
- HTTP ingest hardening
- concurrency handling for duplicate/reprocess flows
- scale-sensitive retrieval heuristics
- weak evaluation identity

If those boundary concerns are addressed, the underlying run/evaluation/search architecture is strong enough to keep evolving without major rework.

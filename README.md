# docling-system

Docling-based PDF ingestion and retrieval system for plumbing-code knowledge.

## What It Does

This system ingests PDF code books, parses them with Docling, stores versioned run artifacts, validates prose chunks, logical tables, and figures, and promotes only validation-passing runs to active search. Retrieval is exposed through a local REST API and a read-only browser UI. Run-scoped retrieval evaluations are persisted and surfaced through the API and UI.

The current workflow is operator-driven: use the CLI to ingest local PDFs, then use the API or UI to inspect documents, tables, figures, artifacts, validation status, evaluation status, metrics, and mixed chunk/table search.

The UI also includes a grounded chat box that answers questions from retrieved chunks and tables in the active corpus, with source citations. If OpenAI is configured, answers are synthesized against retrieved context; otherwise the UI falls back to extractive evidence snippets. Both direct search and grounded chat can now run under named search harnesses so operators can compare retrieval profiles and reranker versions against the same corpus.

The system also records replayable failure artifacts for failed runs, exposes recent run history per document, persists direct-search telemetry with operator feedback labels, stores answer-level feedback for grounded chat responses, and includes replay/audit CLIs for checking run and retrieval invariants against the local corpus.

The current experimental retrieval-accuracy track adds a non-default `prose_v3` harness for prose-heavy queries. It widens prose candidate generation with metadata and adjacent-context expansion, persists internal `query_intent` and candidate-source telemetry on search requests, and can be evaluated separately from the production-default `default_v1`.

The repository now also includes a Postgres-backed agent-task substrate for orchestration work. Agent tasks are durable records with dependency edges, attempts, approval metadata, failure artifacts, verifier rows, operator outcome labels, and draft/apply review flows for search harness updates. Agent task attempts now persist structured cost and performance payloads so trend, value-density, and recommendation-success analytics can be computed from durable execution records instead of transient logs.

## Current Contracts

- `docling.json` is the canonical machine-readable document parse artifact.
- `document.yaml` is the human-readable document artifact.
- Table JSON is the canonical machine-readable table artifact.
- Table YAML is the human-readable table artifact.
- Figures are first-class persisted outputs with JSON/YAML artifacts and provenance metadata.
- YAML is derived output, not a second source of truth.
- Search, ranking, filtering, validation, and persistence use normalized database fields and structured objects, not reparsed YAML.
- `documents.active_run_id` advances only after document and table validations pass.
- A failed validation run remains non-active, and the prior active run remains unchanged.
- `/search` is the immediate mixed typed search contract for both chunks and tables.
- `table_id` is run-scoped. `logical_table_key` is best-effort cross-run lineage and can be null.
- Run evaluations are first-class persisted records with summary and per-query detail.
- Every successful validated ingest also writes an auto-generated evaluation fixture to `storage/evaluation_corpus.auto.yaml` so new documents do not remain unevaluated while waiting for a hand-authored fixture.
- `docs/evaluation_corpus.yaml` remains the durable hand-authored evaluation contract; fixtures are matched by `source_filename`, and if both manual and auto-generated fixtures exist for the same source filename, the manual fixture wins.
- `GET /documents/{document_id}/evaluations/latest` is the top-level persisted evaluation detail endpoint for the document's latest run.
- `GET /documents/{document_id}/figures` and `GET /documents/{document_id}/figures/{figure_id}` are top-level figure inspection endpoints for the active run.
- Table supplements are registry-driven via `config/table_supplements.yaml`; the registry selects document-specific clean supplement PDFs without changing the canonical source document contract.
- Supplement overlays preserve chapter-local page spans and original segment provenance while replacing known-bad logical table families with cleaner extracted rows.

## Stack

- FastAPI REST API
- SQLAlchemy, Alembic, psycopg
- Postgres with pgvector
- Docling PDF parsing
- OpenAI embeddings with `text-embedding-3-small` and a pinned 1536-dimension contract
- One polling worker with DB-backed leasing and retries
- One additional agent-task worker with DB-backed leasing and retries
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

7. Start the ingest/search worker in a second shell:

```bash
uv run docling-system-worker
```

8. Start the agent-task worker in a third shell if you want orchestration tasks to execute:

```bash
uv run docling-system-agent-worker
```

9. Open the UI:

```text
http://localhost:8000/
```

## Ingesting PDFs

Local-file ingest is CLI-only:

```bash
uv run docling-system-ingest-file /absolute/path/to/file.pdf
uv run docling-system-ingest-dir /absolute/path/to/folder --recursive
```

The CLI passes through the same checksum dedupe, run queue, worker processing, validation gate, and active-run promotion path as upload ingest.

Directory ingest creates a durable ingest batch, scans the directory for `.pdf` files, and queues each file through the same single-file ingest contract. Each batch item records whether the file queued a new run, attached to an existing in-flight recovery run, hit an already-active duplicate, or failed validation before queueing. Batch status stays `running` until the linked document runs reach terminal states, so `docling-system-ingest-batch-show` reflects end-to-end progress instead of only the initial fan-out step.

After a run validates successfully, the worker also writes or refreshes an auto-generated evaluation fixture under `storage/evaluation_corpus.auto.yaml` and immediately evaluates the run against the combined manual-plus-auto corpus.

Local path ingest policy:

- Paths must be under configured allowed roots.
- If `DOCLING_SYSTEM_LOCAL_INGEST_ALLOWED_ROOTS` is unset, the default roots are the repo working directory and `~/Documents`.
- Symlink file paths are rejected, including symlinked PDFs discovered inside a queued directory.
- Files must have a `.pdf` suffix and a `%PDF-` header.
- Duplicate content is deduped by checksum, not by path string.
- File size defaults to `104857600` bytes.
- Page count defaults to a maximum of `750` pages.

`POST /documents` remains multipart upload-based for compatibility. No arbitrary path-based ingest is exposed through public HTTP.

Batch CLI commands:

- `uv run docling-system-ingest-batch-list`
- `uv run docling-system-ingest-batch-show <batch_id>`

## API Overview

- `GET /health`
- `GET /metrics`
- `GET /documents`
- `POST /documents`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/runs`
- `GET /documents/{document_id}/evaluations/latest`
- `GET /documents/{document_id}/chunks`
- `GET /documents/{document_id}/tables`
- `GET /documents/{document_id}/tables/{table_id}`
- `GET /documents/{document_id}/figures`
- `GET /documents/{document_id}/figures/{figure_id}`
- `GET /documents/{document_id}/artifacts/json`
- `GET /documents/{document_id}/artifacts/yaml`
- `GET /documents/{document_id}/tables/{table_id}/artifacts/json`
- `GET /documents/{document_id}/tables/{table_id}/artifacts/yaml`
- `GET /documents/{document_id}/figures/{figure_id}/artifacts/json`
- `GET /documents/{document_id}/figures/{figure_id}/artifacts/yaml`
- `POST /documents/{document_id}/reprocess`
- `GET /runs/{run_id}/failure-artifact`
- `POST /search`
- `GET /search/requests/{search_request_id}`
- `POST /search/requests/{search_request_id}/feedback`
- `POST /search/requests/{search_request_id}/replay`
- `GET /search/harnesses`
- `POST /search/harness-evaluations`
- `GET /search/replays`
- `POST /search/replays`
- `GET /search/replays/{replay_run_id}`
- `GET /search/replays/compare`
- `POST /chat`
- `POST /chat/answers/{chat_answer_id}/feedback`
- `GET /quality/summary`
- `GET /quality/failures`
- `GET /quality/evaluations`
- `GET /quality/eval-candidates`
- `GET /quality/trends`
- `GET /agent-tasks/actions`
- `GET /agent-tasks`
- `POST /agent-tasks`
- `GET /agent-tasks/analytics/summary`
- `GET /agent-tasks/analytics/trends`
- `GET /agent-tasks/analytics/verifications`
- `GET /agent-tasks/analytics/approvals`
- `GET /agent-tasks/analytics/recommendations`
- `GET /agent-tasks/analytics/recommendations/trends`
- `GET /agent-tasks/analytics/costs`
- `GET /agent-tasks/analytics/costs/trends`
- `GET /agent-tasks/analytics/performance`
- `GET /agent-tasks/analytics/performance/trends`
- `GET /agent-tasks/analytics/value-density`
- `GET /agent-tasks/analytics/decision-signals`
- `GET /agent-tasks/analytics/workflow-versions`
- `GET /agent-tasks/traces/export`
- `GET /agent-tasks/{task_id}`
- `GET /agent-tasks/{task_id}/outcomes`
- `POST /agent-tasks/{task_id}/outcomes`
- `GET /agent-tasks/{task_id}/artifacts`
- `GET /agent-tasks/{task_id}/artifacts/{artifact_id}`
- `GET /agent-tasks/{task_id}/verifications`
- `GET /agent-tasks/{task_id}/failure-artifact`
- `POST /agent-tasks/{task_id}/approve`
- `POST /agent-tasks/{task_id}/reject`

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

Optional harness override:

- `harness_name`

Keyword, semantic, and hybrid modes search active chunks and active tables independently, then merge results deterministically. Query embeddings are computed once per request and reused for chunk and table semantic retrieval. If embeddings fail, the system degrades to keyword-backed retrieval instead of blocking validated ingestion.

Every direct search request is persisted and returned with an `X-Search-Request-Id` response header. That durable request ID supports:

- request detail inspection through `GET /search/requests/{search_request_id}`
- operator labeling through `POST /search/requests/{search_request_id}/feedback`
- one-off replay through `POST /search/requests/{search_request_id}/replay`
- batch replay suites and trend reporting through the replay and quality endpoints

Named harnesses bundle:

- a retrieval candidate profile
- a reranker implementation name and version
- a persisted config snapshot captured on every search request and replay run

Current harnesses:

- `default_v1` as the production default
- `wide_v2` as the wider candidate/replay comparison harness
- `prose_v3` as the non-default prose-accuracy experiment

Current agent-task analytics can answer:

- how task, verifier, approval, and rejection rates are trending by day or week
- whether recommendation tasks are actually producing verified drafts and applied changes
- how much replay/evaluation workload each workflow is driving
- where queueing and execution latency are accumulating
- which workflow versions are delivering the best improvement density per unit time

Replay suites currently support:

- `evaluation_queries`
- `feedback`
- `live_search_gaps`
- `cross_document_prose_regressions`

Durable search telemetry now records:

- requested and served mode
- internal `query_intent`
- candidate-source breakdown
- metadata-supplement and adjacent-context candidate counts
- per-result rerank feature snapshots

Applied review harnesses are persisted in `config/search_harness_overrides.json`, while draft harnesses remain task artifacts until verified and approved.

Use `GET /search/harnesses` to inspect the currently available harnesses.
Use `POST /search/harness-evaluations` to compare two named harnesses across replay sources without leaving the operator surface.

## Agent Tasks

The agent-task layer is a durable orchestration substrate, not a second prompt-only control plane. Each task has structured input, status, dependency edges, attempt history, version metadata, approval fields, and optional failure artifacts under `storage/agent_tasks/`.

The current registry includes read-only, draft-change, and approval-gated promotable actions. Supported task types are:

- `get_latest_evaluation`
- `list_quality_eval_candidates`
- `replay_search_request`
- `run_search_replay_suite`
- `evaluate_search_harness`
- `verify_search_harness_evaluation`
- `draft_harness_config_update`
- `verify_draft_harness_config`
- `triage_replay_regression`
- `enqueue_document_reprocess`
- `apply_harness_config_update`

Operators can inspect the live task catalog through `GET /agent-tasks/actions` or `uv run docling-system-agent-task-actions`.

Current task guarantees:

- task creation validates the requested `task_type` and typed input payload against the registry
- task creation inherits the registry-declared `side_effect_level` and `requires_approval` when callers omit them, and rejects mismatches when callers override them incorrectly
- verifier tasks automatically depend on their `target_task_id`, so they stay blocked until the target task completes
- draft and promotion-style tasks can link back to `source_task_id`, `draft_task_id`, and `verification_task_id`, which are persisted as dependencies so lineage remains visible in the task graph
- operators can attach durable outcome labels like `useful`, `not_useful`, `correct`, and `incorrect` to terminal tasks
- duplicate outcome labels from the same actor on the same task are rejected so analytics and exported traces stay clean
- the agent worker records attempts, heartbeats, retries, and replayable failure artifacts
- task artifacts can be inspected through `GET /agent-tasks/{task_id}/artifacts`
- persisted JSON artifacts can be fetched directly through `GET /agent-tasks/{task_id}/artifacts/{artifact_id}`
- verifier outcomes are persisted separately from task results and can be inspected through `GET /agent-tasks/{task_id}/verifications`
- task outcome labels can be inspected through `GET /agent-tasks/{task_id}/outcomes`
- failed tasks expose a direct failure-artifact endpoint through `GET /agent-tasks/{task_id}/failure-artifact`
- approval-gated tasks remain `awaiting_approval` until an operator approves or rejects them
- rejected tasks move to terminal `rejected` status, remain unclaimable by the worker, and preserve the previously live system state unchanged
- aggregate analytics are available through `GET /agent-tasks/analytics/summary`
- workflow-version comparisons are available through `GET /agent-tasks/analytics/workflow-versions`
- full task traces, including outcomes, artifacts, verifications, and approval metadata, can be exported through `GET /agent-tasks/traces/export`

The first workflow-style task is `triage_replay_regression`. It runs in shadow mode, mines unresolved quality candidates, evaluates a candidate harness against a baseline across replay sources, records a verifier-style recommendation on the triage task itself, and writes a durable `triage_summary.json` artifact under `storage/agent_tasks/<task_id>/`.

The first draft/apply flow is the harness review path. `draft_harness_config_update` creates a review-harness artifact without changing live search behavior, `verify_draft_harness_config` evaluates that draft ephemerally against replay sources and writes a verifier record, and `apply_harness_config_update` publishes the verified review harness into `config/search_harness_overrides.json` only after approval.

The first promotable task is `enqueue_document_reprocess`. It is approval-gated, queues a fresh run for an existing document only after approval, and leaves the current active run unchanged until the new run completes validation and promotion through the normal document lifecycle.

The current learning surface is intentionally simple and durable: operators can label finished tasks, inspect analytics over approvals, rejections, verifier outcomes, and labels, compare workflow versions, and export the resulting traces for later analysis.

## Tables

Tables are first-class retrieval objects. The parser stores logical tables, source table segment provenance, merge metadata, repeated-header removal metadata, and audit hashes. Continued tables can be merged into one logical table when the evidence is strong enough; ambiguous continuation candidates are recorded instead of guessed.

The current parser also supports a small, explicit supplement registry for known-bad scanned table families. This is a provisional v1 mechanism, not a second ingest path: the chapter PDF remains canonical, and matching registry rules selectively overlay cleaner table-family rows from a supplement PDF while retaining chapter-local page ranges and source-segment lineage.

For future repairs, the intended workflow is:

- ingest the chapter PDF as the canonical document
- add any clean supporting table PDF as a supplement input under the allowed local roots
- add or update the matching rule in `config/table_supplements.yaml`
- add fixed-corpus evaluation coverage in `docs/evaluation_corpus.yaml`, including `expected_merged_tables` where the repair should be structurally verified
- reprocess the document and confirm both query hits and structural checks pass through `GET /documents/{document_id}/evaluations/latest`

Table telemetry is available from `GET /metrics`, including detected tables, persisted logical tables, segment counts, continuation merges, ambiguous continuations, table embedding failures, and table search hits.

## Useful Commands

```bash
uv run pytest tests
uv run pytest tests/unit
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest tests/integration/test_postgres_roundtrip.py -q
uv run alembic upgrade head
uv run docling-system-cleanup
uv run docling-system-ingest-file /absolute/path/to/file.pdf
uv run docling-system-ingest-dir /absolute/path/to/folder --recursive
uv run docling-system-ingest-batch-list --limit 10
uv run docling-system-ingest-batch-show <batch_id>
uv run docling-system-agent-worker
uv run docling-system-eval-run <run_id>
uv run docling-system-eval-corpus
uv run docling-system-replay-search <search_request_id>
uv run docling-system-run-replay-suite feedback --limit 12
uv run docling-system-run-replay-suite feedback --harness-name wide_v2 --limit 12
uv run docling-system-run-replay-suite cross_document_prose_regressions --harness-name prose_v3 --limit 12
uv run docling-system-eval-reranker wide_v2 --baseline-harness-name default_v1 --limit 25
uv run docling-system-eval-reranker prose_v3 --baseline-harness-name default_v1 --source-type cross_document_prose_regressions --limit 25
uv run docling-system-export-ranking-dataset --limit 200
uv run docling-system-agent-task-actions
uv run docling-system-agent-task-create evaluate_search_harness --input-json '{"candidate_harness_name":"wide_v2","baseline_harness_name":"default_v1","source_types":["evaluation_queries","feedback"],"limit":12}'
uv run docling-system-agent-task-create verify_search_harness_evaluation --input-json '{"target_task_id":"<task_id>","max_total_regressed_count":0,"max_mrr_drop":0.0,"max_zero_result_count_increase":0,"max_foreign_top_result_count_increase":0,"min_total_shared_query_count":1}'
uv run docling-system-agent-task-create triage_replay_regression --input-json '{"candidate_harness_name":"wide_v2","baseline_harness_name":"default_v1","source_types":["evaluation_queries","feedback"],"replay_limit":12,"quality_candidate_limit":12}'
uv run docling-system-agent-task-create draft_harness_config_update --input-json '{"draft_harness_name":"wide_v2_review","base_harness_name":"wide_v2","source_task_id":"<triage_task_id>","rationale":"publish a review harness","reranker_overrides":{"result_type_priority_bonus":0.009}}'
uv run docling-system-agent-task-create verify_draft_harness_config --input-json '{"target_task_id":"<draft_task_id>","baseline_harness_name":"wide_v2","source_types":["evaluation_queries"],"limit":12,"max_total_regressed_count":0,"max_mrr_drop":0.0,"max_zero_result_count_increase":0,"max_foreign_top_result_count_increase":0,"min_total_shared_query_count":1}'
uv run docling-system-agent-task-create apply_harness_config_update --input-json '{"draft_task_id":"<draft_task_id>","verification_task_id":"<verification_task_id>","reason":"publish review harness"}'
uv run docling-system-agent-task-create enqueue_document_reprocess --input-json '{"document_id":"<document_id>","source_task_id":"<triage_task_id>","reason":"shadow-mode triage recommended reprocess"}'
uv run docling-system-agent-task-list --status queued
uv run docling-system-agent-task-analytics
uv run docling-system-agent-task-workflow-versions
uv run docling-system-agent-task-export-traces --limit 25 --workflow-version v1
uv run docling-system-agent-task-show <task_id>
uv run docling-system-agent-task-outcomes <task_id>
uv run docling-system-agent-task-label <task_id> --outcome-label useful --created-by operator@example.com --note "recommendation was accurate"
uv run docling-system-agent-task-artifacts <task_id>
uv run docling-system-agent-task-artifact <task_id> <artifact_id>
uv run docling-system-agent-task-verifications <task_id>
uv run docling-system-agent-task-failure-artifact <task_id>
uv run docling-system-agent-task-approve <task_id> --approved-by operator@example.com --approval-note "approved for reprocess"
uv run docling-system-agent-task-reject <task_id> --rejected-by reviewer@example.com --rejection-note "not enough evidence"
uv run docling-system-backfill-legacy-audit
uv run docling-system-audit
```

## Testing

The default test path is the fast unit suite:

```bash
uv run pytest tests/unit -q
```

The repository also includes a real Postgres-backed integration harness:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest tests/integration/test_postgres_roundtrip.py -q
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest tests/integration/test_agent_task_triage_roundtrip.py -q
```

That integration harness:

- uses the local Postgres instance from `docker compose up -d db`
- provisions an isolated temporary database schema per test
- uses temporary filesystem storage instead of the repo `storage/` tree
- stubs parser output and disables live embedding lookups so the run is deterministic and does not depend on OpenAI

The ranking dataset export schema is documented in [docs/ranking_dataset_schema.md](./docs/ranking_dataset_schema.md).
`GET /quality/eval-candidates` now mines three gap classes:

- failed fixed-corpus evaluation queries
- live search gaps such as zero-result or missing-table requests
- unsupported or incomplete grounded chat answers

## Evaluation

The fixed evaluation contract lives in [docs/evaluation_corpus.yaml](./docs/evaluation_corpus.yaml). It records the mixed-search rollout mode, embedding contract, target document types, and threshold checks for table counts, continued-table merges, golden table queries, prose queries, figure counts, figure artifact/provenance coverage, expected figure captions, and unexpected merge/split tolerance.

The current corpus also includes explicit cross-document prose-contamination guards and answer-side citation-purity checks for non-UPC prose documents, plus negative answer cases that require a fallback-style "no confident answer" outcome.

The worker also maintains [storage/evaluation_corpus.auto.yaml](./storage/evaluation_corpus.auto.yaml) as a source-filename-keyed auto-generated companion corpus for newly ingested documents that do not yet have hand-authored fixtures. Auto-generated fixtures are created from persisted chunks, tables, figures, and document titles after validation; they are refreshed per source filename and provide immediate retrieval/structural coverage without replacing the hand-authored corpus.

Current hand-authored fixtures include the UPC corpus plus non-UPC prose, table, figure, and Tyler's Kitchen documents such as:

- `upc_ch7`
- `upc_ch2_figures`
- `upc_ch5`
- `bitter_lesson_prose`
- `test_pdf_prose`
- `nsf_ai_ready_america_figures`
- `openrouter_spend_report_tables`
- `tyler_kitchen_soil_report`
- `tyler_kitchen_transportation_report`
- `tyler_kitchen_wildlife_report`

## Troubleshooting

If the worker logs `429 insufficient_quota` from OpenAI, the API key is authenticating but the OpenAI project behind that key does not have usable quota or billing. Ingest still completes when validation passes, but embeddings are not stored and semantic search falls back to keyword-backed behavior.

After changing `DOCLING_SYSTEM_OPENAI_API_KEY`, restart the API and worker. Existing runs need to be reprocessed to generate embeddings with the new key.

# docling-system

Docling-based PDF ingestion and retrieval system for plumbing-code knowledge.

## What It Does

This system ingests PDF code books, parses them with Docling, stores versioned run artifacts, validates prose chunks, logical tables, and figures, and promotes only validation-passing runs to active search. Retrieval is exposed through a local REST API and an operator browser UI. Run-scoped retrieval evaluations are persisted and surfaced through the API and UI.

The current workflow is operator-driven: use the CLI to ingest local PDFs, then use the API or UI to inspect documents, tables, figures, artifacts, validation status, evaluation status, metrics, and mixed chunk/table search.

The current browser UI focuses on search, replay, evaluation, document inspection, and agent workflow governance. Grounded chat remains available through the API, but there is not currently a browser chat panel mounted in the shipped UI.

The system also records replayable failure artifacts for failed runs, exposes recent run history per document, persists direct-search telemetry with operator feedback labels, stores answer-level feedback for grounded chat responses, and includes replay/audit CLIs for checking run and retrieval invariants against the local corpus.

The current experimental retrieval-accuracy track adds a non-default `prose_v3` harness for prose-heavy queries. It widens prose candidate generation with metadata and adjacent-context expansion, persists internal `query_intent` and candidate-source telemetry on search requests, and can be evaluated separately from the production-default `default_v1`.

The repository now also includes a Postgres-backed agent-task substrate for orchestration work. Agent tasks are durable records with dependency edges, attempts, approval metadata, failure artifacts, verifier rows, operator outcome labels, and draft/apply review flows for search harness updates. Agent task attempts now persist structured cost and performance payloads so trend, value-density, and recommendation-success analytics can be computed from durable execution records instead of transient logs.

The semantics stack is now portable across arbitrary user corpora. The repo ships only a generic upper ontology seed plus workflow code; the active ontology, approved fact graph, and approved cross-document graph memory live in DB-backed snapshots that can be rebuilt from whatever documents a user ingests. Shadow semantic extractors and graph builders stay additive until they pass verification and an operator approves publication.

The runtime now supports both loopback-local operator mode and authenticated remote mode. Loopback-local mode is still the smoothest path for the browser UI and ad hoc operator work. Remote mode supports either one legacy shared API key or actor-scoped credentials with per-principal capabilities for upload, inspection, quality, replay, chat, and agent-task surfaces.

The repository versioning policy lives in [docs/versioning_policy.md](./docs/versioning_policy.md).
`main` is the stable `v1` platform branch. The semantics layer is a separate additive initiative
within this repository and is not synonymous with `v2`. `v2` is reserved for a future agentic
platform project rather than the default home for semantics-layer work. Stable platform releases
continue to use `v1.x.y` tags from `main`; optional semantics experiment checkpoints should use
clearly separate non-platform tags from the semantics branch.

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
- `docs/evaluation_corpus.yaml` remains an optional hand-authored evaluation contract for explicitly identified documents. Runtime evaluation uses the auto-generated ingest corpus by default; a manual corpus is only loaded when an explicit corpus path is passed or `DOCLING_SYSTEM_MANUAL_EVALUATION_CORPUS_PATH` is configured. Runtime fixture lookup matches by document `sha256`; filename fallback is reserved for auto-generated fixtures written from ingested data.
- `GET /documents/{document_id}/evaluations/latest` is the top-level persisted evaluation detail endpoint for the document's latest run.
- `GET /documents/{document_id}/figures` and `GET /documents/{document_id}/figures/{figure_id}` are top-level figure inspection endpoints for the active run.
- Table supplements are registry-driven via `config/table_supplements.yaml`; the registry accepts config-defined regex family matchers instead of code-defined corpus matchers, and the checked-in registry ships empty by default.
- Supplement overlays preserve chapter-local page spans and original segment provenance while replacing known-bad logical table families with cleaner extracted rows.

## Stack

- FastAPI REST API
- SQLAlchemy, Alembic, psycopg
- Postgres with pgvector
- Docling PDF parsing
- OpenAI embeddings with `text-embedding-3-small` and a pinned 1536-dimension contract
- One polling worker with DB-backed leasing and retries
- One additional agent-task worker with DB-backed leasing and retries
- Local filesystem storage under `DOCLING_SYSTEM_STORAGE_ROOT`
- Docker Compose definitions for local Postgres, migrations, API, worker, and agent worker
- Static operator UI served from `/` with assets mounted under `/ui`
- Generic upper ontology seed plus DB-backed active ontology, fact-graph, and semantic-graph snapshots

## Local Setup

The manual loopback-local flow is still the recommended development path. It keeps the API in local mode, avoids auth headers for the browser UI, and matches the operator-oriented workflow used by the tests and CLIs.

1. Copy `.env.example` to `.env`.
2. Keep this checkout isolated from the stable `main` checkout. The checked-in example values in this branch use:
   - `localhost:5432/docling_system_semantics`
   - `./storage-semantics`
   - `127.0.0.1:8001`
   - `DOCLING_SYSTEM_SEMANTICS_ENABLED=0`
3. Set `DOCLING_SYSTEM_OPENAI_API_KEY` if semantic embeddings and OpenAI-backed grounded chat should be generated. The semantics sidecar still stays off until `DOCLING_SYSTEM_SEMANTICS_ENABLED=1`.
4. Ensure local Postgres is running and create the isolated semantics database if it does not already exist:

```bash
docker exec docling-system-db psql -U docling -d postgres -c 'CREATE DATABASE docling_system_semantics'
```

5. Install dependencies:

```bash
uv sync --extra dev
```

6. Run migrations:

```bash
uv run alembic upgrade head
```

7. Start the API:

```bash
uv run docling-system-api
```

8. Start the ingest/search worker in a second shell:

```bash
uv run docling-system-worker
```

Workers now register a runtime code fingerprint under `storage/runtime/process_registry.json`.
If a newer code fingerprint takes over, older workers exit before claiming the next run instead
of continuing to process documents on stale code.

9. Start the agent-task worker in a third shell if you want orchestration tasks to execute:

```bash
uv run docling-system-agent-worker
```

10. Open the UI:

```text
http://localhost:8001/
```

You can inspect the current API runtime fingerprint with:

```bash
curl http://localhost:8001/runtime/status
```

## Docker Compose Stack

The checked-in compose file now brings up the full local topology:

```bash
docker compose up --build
```

That stack includes:

- `db`
- `migrate`
- `api`
- `worker`
- `agent-worker`

Current compose behavior:

- the host DB port, host API port, DB name, bind mounts, compose project name, and container names all come from `.env`
- the checked-in example values for this checkout use `localhost:5433`, `localhost:8001`, `docling_system_semantics`, and `./storage-semantics`
- Postgres data is isolated through the semantics-specific Compose project and volume name
- the API binds `0.0.0.0:8000` inside the container and is published on the host port from `DOCLING_SYSTEM_API_PORT`
- the compose file uses `DOCLING_SYSTEM_API_KEY` when set and otherwise falls back to `docling-local-secret`
- the semantics layer remains disabled unless `DOCLING_SYSTEM_SEMANTICS_ENABLED=1`
- `GET /health` remains public
- most other remote endpoints require auth and, for many surfaces, explicit capabilities

The shipped browser UI can store an `X-API-Key` or bearer token in local browser storage and applies that credential to API requests and protected downloads. For interactive operator use, the manual loopback-local flow is still the simplest path because it avoids remote auth setup.

## Remote API Auth

API mode is inferred from the bind host unless you set `DOCLING_SYSTEM_API_MODE` explicitly:

- loopback host -> `local`
- non-loopback host -> `remote`

Remote mode requires one of:

- `DOCLING_SYSTEM_API_KEY`
- `DOCLING_SYSTEM_API_CREDENTIALS_JSON`

The current auth model supports:

- one legacy shared API key with a shared capability set configured by `DOCLING_SYSTEM_REMOTE_API_CAPABILITIES`
- actor-scoped credentials through `DOCLING_SYSTEM_API_CREDENTIALS_JSON`, with one or more principals, each with its own key and capability list
- `X-API-Key` and `Authorization: Bearer ...` credential transport

Current capability families are:

- `system:read`
- `documents:upload`
- `documents:inspect`
- `documents:review`
- `documents:reprocess`
- `search:query`
- `search:history:read`
- `search:feedback`
- `search:replay`
- `search:evaluate`
- `chat:query`
- `chat:feedback`
- `quality:read`
- `agent_tasks:read`
- `agent_tasks:write`

Important legacy-key behavior:

- if you use only `DOCLING_SYSTEM_API_KEY` and leave `DOCLING_SYSTEM_REMOTE_API_CAPABILITIES` unset, the current default capability set is limited to `documents:upload`, `search:query`, `search:feedback`, `chat:query`, and `chat:feedback`
- document inspection, semantic review, quality, replay, runtime-status, and agent-task endpoints need additional capabilities or actor-scoped credentials
- `GET /runtime/status` reports the current auth mode, effective principals, and shared capabilities when the caller has `system:read`

## Ingesting PDFs

Local-file ingest is CLI-only:

```bash
uv run docling-system-ingest-file /absolute/path/to/file.pdf
uv run docling-system-ingest-dir /absolute/path/to/folder --recursive
```

The CLI passes through the same checksum dedupe, run queue, worker processing, validation gate, and active-run promotion path as upload ingest.

Directory ingest creates a durable ingest batch, scans the directory for `.pdf` files, and queues each file through the same single-file ingest contract. Each batch item records whether the file queued a new run, attached to an existing in-flight recovery run, hit an already-active duplicate, or failed validation before queueing. Batch status stays `running` until the linked document runs reach terminal states, so `docling-system-ingest-batch-show` reflects end-to-end progress instead of only the initial fan-out step.

After a run validates successfully, the worker writes or refreshes an auto-generated evaluation fixture under `storage/evaluation_corpus.auto.yaml` and immediately evaluates the run against the ingested-data-derived corpus for that document. Hand-authored fixtures can still be added later for explicitly identified documents by passing a corpus path or setting `DOCLING_SYSTEM_MANUAL_EVALUATION_CORPUS_PATH`.

Local path ingest policy:

- Paths must be under configured allowed roots.
- If `DOCLING_SYSTEM_LOCAL_INGEST_ALLOWED_ROOTS` is unset, the default roots are the repo working directory, `~/Documents`, and `~/Downloads`.
- Symlink file paths are rejected, including symlinked PDFs discovered inside a queued directory.
- Files must have a `.pdf` suffix and a `%PDF-` header.
- Duplicate content is deduped by checksum, not by path string.
- File size and page count limits are enforced through environment settings.
- Code defaults are `268435456` bytes and `1000` pages when the limits are unset.
- The checked-in `.env.example` currently uses lower local-development limits: `104857600` bytes and `750` pages.

`POST /documents` remains multipart upload-based for compatibility. No arbitrary path-based ingest is exposed through public HTTP.

Batch CLI commands:

- `uv run docling-system-ingest-batch-list`
- `uv run docling-system-ingest-batch-show <batch_id>`

## API Overview

- `GET /health`
- `GET /runtime/status`
- `GET /metrics`
- `GET /documents`
- `POST /documents`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/runs`
- `GET /runs/{run_id}`
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
- `GET /search/harness-evaluations`
- `POST /search/harness-evaluations`
- `GET /search/harness-evaluations/{evaluation_id}`
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
- `GET /agent-tasks/{task_id}/context`
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
Use `POST /search/harness-evaluations` to compare two named harnesses across
replay sources without leaving the operator surface. The POST creates a durable
evaluation record; use `GET /search/harness-evaluations` and
`GET /search/harness-evaluations/{evaluation_id}` to inspect historical results
and the replay-run provenance behind each source.
The equivalent local inspection commands are
`docling-system-search-harness-evaluation-list` and
`docling-system-search-harness-evaluation-show <evaluation_id>`.

## Agent Tasks

The agent-task layer is a durable orchestration substrate, not a second prompt-only control plane. Each task has structured input, status, dependency edges, attempt history, version metadata, approval fields, and optional failure artifacts under `storage/agent_tasks/`.

The current registry includes read-only, draft-change, and approval-gated promotable actions. Supported task types are:

- `get_latest_evaluation`
- `get_latest_semantic_pass`
- `initialize_workspace_ontology`
- `get_active_ontology_snapshot`
- `discover_semantic_bootstrap_candidates`
- `export_semantic_supervision_corpus`
- `evaluate_semantic_candidate_extractor`
- `build_shadow_semantic_graph`
- `evaluate_semantic_relation_extractor`
- `plan_technical_report`
- `build_report_evidence_cards`
- `prepare_report_agent_harness`
- `draft_technical_report`
- `verify_technical_report`
- `prepare_semantic_generation_brief`
- `list_quality_eval_candidates`
- `refresh_eval_failure_cases`
- `inspect_eval_failure_case`
- `triage_eval_failure_case`
- `optimize_search_harness_from_case`
- `draft_harness_config_update_from_optimization`
- `replay_search_request`
- `run_search_replay_suite`
- `evaluate_search_harness`
- `verify_search_harness_evaluation`
- `draft_harness_config_update`
- `draft_semantic_registry_update`
- `draft_ontology_extension`
- `draft_graph_promotions`
- `verify_draft_harness_config`
- `verify_draft_semantic_registry_update`
- `verify_draft_ontology_extension`
- `verify_draft_graph_promotions`
- `draft_semantic_grounded_document`
- `verify_semantic_grounded_document`
- `triage_replay_regression`
- `triage_semantic_pass`
- `triage_semantic_candidate_disagreements`
- `triage_semantic_graph_disagreements`
- `enqueue_document_reprocess`
- `apply_harness_config_update`
- `apply_semantic_registry_update`
- `apply_ontology_extension`
- `apply_graph_promotions`
- `build_document_fact_graph`

Operators can inspect the live task catalog through `GET /agent-tasks/actions` or `uv run docling-system-agent-task-actions`. Migrated task types also advertise `output_schema_name`, `output_schema_version`, and `output_schema` metadata alongside the existing input contract.

At this point every task type in the current registry emits typed output and a context artifact. Complex tasks add task-specific refs and summaries; simpler read-only and promotion tasks use the generic typed-context projection so detail, trace export, and context endpoints stay consistent across the catalog.

Current task guarantees:

- task creation validates the requested `task_type` and typed input payload against the registry
- migrated task types also validate typed output payloads before completion
- task creation inherits the registry-declared `side_effect_level` and `requires_approval` when callers omit them, and rejects mismatches when callers override them incorrectly
- verifier tasks automatically depend on their `target_task_id`, so they stay blocked until the target task completes
- draft and promotion-style tasks can link back to `source_task_id`, `draft_task_id`, and `verification_task_id`, which are persisted as typed dependency edges so lineage remains visible in the task graph
- operators can attach durable outcome labels like `useful`, `not_useful`, `correct`, and `incorrect` to terminal tasks
- duplicate outcome labels from the same actor on the same task are rejected so analytics and exported traces stay clean
- the agent worker records attempts, heartbeats, retries, and replayable failure artifacts
- task artifacts can be inspected through `GET /agent-tasks/{task_id}/artifacts`
- persisted JSON artifacts can be fetched directly through `GET /agent-tasks/{task_id}/artifacts/{artifact_id}`
- migrated task types also persist `storage/agent_tasks/<task_id>/context.json` as the canonical context artifact and `storage/agent_tasks/<task_id>/context.yaml` as the derived human-readable sidecar
- task detail and trace export responses include additive context fields (`dependency_edges`, `context_summary`, `context_refs`, `context_artifact_id`, `context_freshness_status`) without changing the existing `input` / `result` payloads
- migrated context refs track `observed_sha256`, `source_updated_at`, `checked_at`, and `freshness_status`; `missing` and `schema_mismatch` block migrated consumers, while `stale` remains advisory in v1
- migrated consumers do not fall back to legacy nested payload reads; pre-context upstream tasks must be rerun into the migrated path before they can be consumed
- the full task context surface is available through `GET /agent-tasks/{task_id}/context?format=json|yaml`
- verifier outcomes are persisted separately from task results and can be inspected through `GET /agent-tasks/{task_id}/verifications`
- task outcome labels can be inspected through `GET /agent-tasks/{task_id}/outcomes`
- failed tasks expose a direct failure-artifact endpoint through `GET /agent-tasks/{task_id}/failure-artifact`
- approval-gated tasks remain `awaiting_approval` until an operator approves or rejects them
- rejected tasks move to terminal `rejected` status, remain unclaimable by the worker, and preserve the previously live system state unchanged
- aggregate analytics are available through `GET /agent-tasks/analytics/summary`
- workflow-version comparisons are available through `GET /agent-tasks/analytics/workflow-versions`
- full task traces, including outcomes, artifacts, verifications, and approval metadata, can be exported through `GET /agent-tasks/traces/export`

The first workflow-style task is `triage_replay_regression`. It runs in shadow mode, mines unresolved quality candidates, evaluates a candidate harness against a baseline across replay sources, records a verifier-style recommendation on the triage task itself, and writes a durable `triage_summary.json` artifact under `storage/agent_tasks/<task_id>/`.

The triage task is now also a migrated typed-context task. Its context summary is the primary operator-facing map: recommendation, confidence, quality-gap count, replay evidence counts, and next action. The deeper `triage_summary.json` artifact remains available by reference through the triage context refs and artifact endpoints.

`evaluate_search_harness` is now also a migrated typed-context task. Its context summary stays short by surfacing only the candidate/baseline pair plus aggregate shared-query, improvement, and regression counts, while its context refs point at the durable harness evaluation record and the baseline/candidate replay runs that produced it.

`verify_search_harness_evaluation` now consumes those migrated evaluation contexts through its `target_task` dependency edge and reloads the durable harness evaluation record when the target output carries an `evaluation_id`. Its context exposes the target evaluation ref, persisted verifier record, gate outcome, and threshold snapshot; pre-context evaluation tasks must be rerun before this verifier will consume them.

The first draft/apply flow is the harness review path. `draft_harness_config_update` creates a review-harness artifact without changing live search behavior, `verify_draft_harness_config` evaluates that draft ephemerally against replay sources and writes a verifier record, and `apply_harness_config_update` publishes the verified review harness into `config/search_harness_overrides.json` only after approval.

Within that flow, `apply_harness_config_update` now consumes the migrated `draft_task` and `verification_task` dependency edges through typed task-context refs only. The apply context summary exposes approval state and verification state, while `GET /agent-tasks/{task_id}`, `GET /agent-tasks/traces/export`, `GET /agent-tasks/{task_id}/context`, and the apply artifact endpoint all surface the same applied harness name and live-override result without requiring operators to inspect raw nested payload blobs.

The first promotable task is `enqueue_document_reprocess`. It is approval-gated, queues a fresh run for an existing document only after approval, and leaves the current active run unchanged until the new run completes validation and promotion through the normal document lifecycle.

The current semantic-generation path is deliberately narrow. `prepare_semantic_generation_brief` builds a typed cross-document semantic dossier and claim/evidence brief, `draft_semantic_grounded_document` renders a bounded `knowledge_brief` draft plus markdown sidecar from that brief, and `verify_semantic_grounded_document` enforces claim traceability, evidence coverage, and required-concept coverage before downstream use.

The technical-report harness extends that path into an LLM-ready report workflow. `plan_technical_report` turns semantic evidence and graph memory into a section, claim, and retrieval plan; `build_report_evidence_cards` converts source evidence, tables, facts, and approved graph edges into stable evidence cards; `prepare_report_agent_harness` writes `report_agent_harness.json`, a wake-up packet containing the report request, context refs, allowed tools, required skills, retrieval plan, evidence cards, graph context, claim contract, failure policy, LLM adapter contract, and verification gate; `draft_technical_report` consumes that harness through a typed `target_task` context ref; and `verify_technical_report` verifies claim traceability, graph approval, concept coverage, and refreshed wake-up context before downstream review.

The current shadow semantic-learning path is also bounded. `export_semantic_supervision_corpus` exports reviewed semantic rows, semantic expectations, and grounded-document verification outcomes as durable JSON/JSONL supervision artifacts; `evaluate_semantic_candidate_extractor` compares a shadow candidate extractor against the lexical baseline on fixed documents and semantic expectations; `triage_semantic_candidate_disagreements` compacts the resulting candidate-only gaps into typed issues, verifier-style metrics, and bounded follow-up recommendations. `prepare_semantic_generation_brief` can also include shadow candidates in additive `shadow_candidates` fields without changing the live semantic dossier or grounded claims.

For domain-agnostic bootstrap on arbitrary user data, `discover_semantic_bootstrap_candidates` now mines provisional concept candidates directly from active document corpora without assuming the current registry matches the domain. Those candidates remain explicitly provisional, but they can flow into the same governed `draft_semantic_registry_update -> verify_draft_semantic_registry_update -> apply_semantic_registry_update -> enqueue_document_reprocess` path as any other semantic contract change.

The ontology layer is now portable across workspaces. The repo ships only a generic `config/upper_ontology.yaml` seed, while the live ontology contract is stored as DB-backed `semantic_ontology_snapshots` with one active workspace pointer. `initialize_workspace_ontology` seeds an empty workspace from the upper ontology, `get_active_ontology_snapshot` exposes the current live snapshot, `draft_ontology_extension -> verify_draft_ontology_extension -> apply_ontology_extension` governs additive ontology changes without mutating repo defaults, and `build_document_fact_graph` compacts approved semantic assertions into a minimal reusable fact graph for grounded generation.

The current upper ontology now carries lightweight relation semantics instead of bare labels. Relation definitions include domain/range entity types, symmetry, literal-object allowance, cardinality hints, and inverse keys. The shadow graph path can therefore emit both generic co-occurrence memory and typed directional relations like `concept_depends_on_concept`, while `verify_draft_graph_promotions` blocks edges that violate the active ontology constraints before they reach live graph memory.

That split keeps the process portable: two different users can ingest different corpora, run the same workflow, and end up with different approved ontology snapshots and fact graphs without changing the repo code or shipping domain-specific defaults.

The current learning surface is intentionally simple and durable: operators can label finished tasks, inspect analytics over approvals, rejections, verifier outcomes, and labels, compare workflow versions, and export the resulting traces for later analysis.

The broader repo self-improvement loop is file-backed first. `config/improvement_cases.yaml`
tracks agent/codebase failures using a closed cause taxonomy and executable artifact
targets; `docling-system-improvement-case-*` commands validate, list, summarize, and
record cases before any DB/API expansion. Existing cases move through deploy and
measure stages with `docling-system-improvement-case-update`, which validates the
whole registry before writing lifecycle changes. `docling-system-hygiene-check` validates
the registry alongside the repo's existing lint, dead-code, duplicate-helper, and
file-budget gates. `docling-system-improvement-case-import` can also observe
hygiene findings, architecture governance reports, unresolved eval failure
cases, failed agent tasks, and failed agent verifications, then write deduped
open cases keyed by source reference.
`docling-system-architecture-inspect` emits the machine-readable architecture
map and validates boundary contracts as a Brown/Structurizr-style inspection;
the hygiene command runs that inspection by default. The committed map is
`docs/architecture_contract_map.json`, and severity policy lives in
`config/architecture_inspection.yaml`. `docling-system-architecture-measure-record`
persists inspection measurements under `storage/architecture_inspections/history.jsonl`,
and `docling-system-architecture-measure-summary` reports the latest trend. The
same read-only governance surface is available through
`GET /architecture/inspection` and `GET /architecture/measurements/summary`
behind the `system:read` API capability. The measurement summary reports the
current Git commit, the latest recorded measurement commit, and whether a new
measurement record is required. `docling-system-architecture-governance-report`
builds a CI-friendly JSON report that combines the current inspection report and
measurement freshness summary. By default it does not mutate local history; CI
passes `--record-current` with a build-scoped history path so the uploaded report
is fresh for the current commit without touching ignored runtime storage. The
GitHub Actions workflow at `.github/workflows/architecture-governance.yml` writes
that report to `build/architecture-governance/architecture_governance_report.json`
and uploads the `build/architecture-governance/` directory as the
`architecture-governance-report` artifact before running the architecture gates.
The workflow also dry-runs the improvement-case import against that report, so
the uploaded governance artifact is continuously checked as a consumable
feedback source for the self-improvement loop.
The same report can be fed back into the improvement loop with
`docling-system-improvement-case-import --source architecture-governance-report
--source-path build/architecture-governance/architecture_governance_report.json`
so CI architecture failures become tracked improvement cases instead of
remaining only workflow output.
`docling-system-capability-contracts --write-map` maintains
`docs/capability_contract_map.json`, the machine-readable surface map for the
service capability facades.
`docling-system-architecture-decisions --write-map` maintains
`docs/architecture_decision_map.json` from `docs/architecture_decisions.yaml`
and verifies that architecture contract-map entries have linked decision
records.

## Tables

Tables are first-class retrieval objects. The parser stores logical tables, source table segment provenance, merge metadata, repeated-header removal metadata, and audit hashes. Continued tables can be merged into one logical table when the evidence is strong enough; ambiguous continuation candidates are recorded instead of guessed.

The current parser also supports an optional supplement registry for known-bad scanned table families. This is a provisional v1 mechanism, not a second ingest path: the source PDF remains canonical, and matching registry rules selectively overlay cleaner table-family rows from a supplement PDF while retaining source page ranges and segment lineage. No sample-specific supplement rules are enabled in the checked-in config.

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
uv run ruff check .
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest tests/integration/test_postgres_roundtrip.py -q
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q
uv run alembic upgrade head
docker compose up --build
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
uv run docling-system-search-harness-evaluation-list --limit 10
uv run docling-system-search-harness-evaluation-show <evaluation_id>
uv run docling-system-optimize-search-harness wide_v2 --baseline-harness-name default_v1 --source-type evaluation_queries --field keyword_candidate_multiplier --iterations 2
uv run docling-system-export-ranking-dataset --limit 200
uv run docling-system-agent-task-actions
uv run docling-system-agent-task-create evaluate_search_harness --input-json '{"candidate_harness_name":"wide_v2","baseline_harness_name":"default_v1","source_types":["evaluation_queries","feedback"],"limit":12}'
uv run docling-system-agent-task-create verify_search_harness_evaluation --input-json '{"target_task_id":"<task_id>","max_total_regressed_count":0,"max_mrr_drop":0.0,"max_zero_result_count_increase":0,"max_foreign_top_result_count_increase":0,"min_total_shared_query_count":1}'
uv run docling-system-agent-task-create triage_replay_regression --input-json '{"candidate_harness_name":"wide_v2","baseline_harness_name":"default_v1","source_types":["evaluation_queries","feedback"],"replay_limit":12,"quality_candidate_limit":12}'
uv run docling-system-agent-task-create draft_harness_config_update --input-json '{"draft_harness_name":"wide_v2_review","base_harness_name":"wide_v2","source_task_id":"<triage_task_id>","rationale":"publish a review harness","reranker_overrides":{"result_type_priority_bonus":0.009}}'
uv run docling-system-agent-task-create verify_draft_harness_config --input-json '{"target_task_id":"<draft_task_id>","baseline_harness_name":"wide_v2","source_types":["evaluation_queries"],"limit":12,"max_total_regressed_count":0,"max_mrr_drop":0.0,"max_zero_result_count_increase":0,"max_foreign_top_result_count_increase":0,"min_total_shared_query_count":1}'
uv run docling-system-agent-task-create apply_harness_config_update --input-json '{"draft_task_id":"<draft_task_id>","verification_task_id":"<verification_task_id>","reason":"publish review harness"}'
uv run docling-system-agent-task-create export_semantic_supervision_corpus --input-json '{"document_ids":["<document_id>"],"reviewed_only":true,"include_generation_verifications":true}'
uv run docling-system-agent-task-create evaluate_semantic_candidate_extractor --input-json '{"document_ids":["<document_id>"],"candidate_extractor_name":"concept_ranker_v1","baseline_extractor_name":"registry_lexical_v1","max_candidates_per_source":3,"score_threshold":0.34}'
uv run docling-system-agent-task-create triage_semantic_candidate_disagreements --input-json '{"target_task_id":"<evaluation_task_id>","min_score":0.34,"include_expected_only":false}'
uv run docling-system-agent-task-create initialize_workspace_ontology --input-json '{}'
uv run docling-system-agent-task-create get_active_ontology_snapshot --input-json '{}'
uv run docling-system-agent-task-create draft_ontology_extension --input-json '{"source_task_id":"<bootstrap_or_triage_task_id>","rationale":"publish corpus-derived ontology extensions"}'
uv run docling-system-agent-task-create verify_draft_ontology_extension --input-json '{"target_task_id":"<draft_task_id>","max_regressed_document_count":0,"max_failed_expectation_increase":0,"min_improved_document_count":1}'
uv run docling-system-agent-task-create apply_ontology_extension --input-json '{"draft_task_id":"<draft_task_id>","verification_task_id":"<verification_task_id>","reason":"publish verified ontology extension"}'
uv run docling-system-agent-task-create build_document_fact_graph --input-json '{"document_id":"<document_id>","minimum_review_status":"approved"}'
uv run docling-system-agent-task-create prepare_semantic_generation_brief --input-json '{"title":"Integration Governance Brief","goal":"Summarize the knowledge base guidance on integration governance.","audience":"Operators","document_ids":["<document_id>"],"target_length":"medium","review_policy":"allow_candidate_with_disclosure"}'
uv run docling-system-agent-task-create draft_semantic_grounded_document --input-json '{"target_task_id":"<brief_task_id>"}'
uv run docling-system-agent-task-create verify_semantic_grounded_document --input-json '{"target_task_id":"<draft_task_id>","max_unsupported_claim_count":0,"require_full_claim_traceability":true,"require_full_concept_coverage":true}'
uv run docling-system-agent-task-create plan_technical_report --input-json '{"title":"Integration Governance Technical Report","goal":"Write a technical report from the ingested integration evidence.","audience":"Operators","document_ids":["<document_id>"],"target_length":"medium","review_policy":"allow_candidate_with_disclosure"}'
uv run docling-system-agent-task-create build_report_evidence_cards --input-json '{"target_task_id":"<plan_task_id>"}'
uv run docling-system-agent-task-create prepare_report_agent_harness --input-json '{"target_task_id":"<evidence_task_id>"}'
uv run docling-system-agent-task-create draft_technical_report --input-json '{"target_task_id":"<harness_task_id>","generator_mode":"structured_fallback"}'
uv run docling-system-agent-task-create verify_technical_report --input-json '{"target_task_id":"<draft_task_id>","max_unsupported_claim_count":0,"require_full_claim_traceability":true,"require_full_concept_coverage":true,"require_graph_edges_approved":true}'
uv run docling-system-agent-task-create enqueue_document_reprocess --input-json '{"document_id":"<document_id>","source_task_id":"<triage_task_id>","reason":"shadow-mode triage recommended reprocess"}'
uv run docling-system-agent-task-list --status queued
uv run docling-system-agent-task-analytics
uv run docling-system-agent-task-workflow-versions
uv run docling-system-agent-task-export-traces --limit 25 --workflow-version v1
uv run docling-system-agent-task-show <task_id>
uv run docling-system-agent-task-context <task_id>
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

The optional fixed evaluation contract lives in [docs/evaluation_corpus.yaml](./docs/evaluation_corpus.yaml). It records the mixed-search rollout mode, embedding contract, target document types, and threshold checks for table counts, continued-table merges, golden table queries, prose queries, figure counts, figure artifact/provenance coverage, expected figure captions, and unexpected merge/split tolerance. It is not on the default runtime path unless explicitly configured.

The current corpus also includes explicit cross-document prose-contamination guards and answer-side citation-purity checks for non-UPC prose documents, plus negative answer cases that require a fallback-style "no confident answer" outcome.

The worker also maintains [storage/evaluation_corpus.auto.yaml](./storage/evaluation_corpus.auto.yaml) as the default auto-generated corpus for ingested documents. Auto-generated fixtures are created from persisted chunks, tables, figures, and document titles after validation; they are refreshed as new runs are promoted and provide immediate retrieval and structural coverage derived from the ingested data itself.

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

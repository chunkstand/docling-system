# Current System Plan

This document supersedes the original rebuilt v1 system plan. It describes the system as it exists now: the live contracts, the architecture in the repository, the operator workflows, and the bounded orchestration layer that sits on top of ingestion, retrieval, evaluation, and search-harness management.

The repository-level branching, release-tag, and promotion rules live in
[docs/versioning_policy.md](./docs/versioning_policy.md). The semantics layer is defined separately
from the future `v2` platform lane; additive semantics-layer work does not automatically imply a
`v2` platform fork. Stable platform releases still ship from `main` under `v1.x.y`; semantics
branch checkpoints, when needed, use separate experiment tags rather than platform release tags.

## Summary

`docling-system` is now a local, operator-oriented PDF ingestion and retrieval system with five major layers:

1. versioned PDF ingest and reprocessing
2. active-run-gated chunk, table, and figure persistence
3. mixed chunk/table retrieval with search harnesses, replays, and grounded chat
4. persisted evaluation, quality, telemetry, and audit loops
5. a durable agent-task orchestration substrate for bounded review, verification, and approval workflows

The system is intentionally conservative:

- one canonical logical document per checksum
- one active run per document
- one pinned embedding contract
- one local Postgres database with pgvector
- one filesystem-backed artifact store under `storage/`
- one ingest/search worker and one agent-task worker, both using DB leasing
- explicit approval gates for promotable agent actions

## Current Goals

The system is built to support these current goals:

- ingest operator-supplied PDFs durably and repeatably
- keep machine-facing truth in Postgres rows and canonical JSON artifacts
- expose grounded retrieval over prose chunks and logical tables
- preserve enough provenance to audit parser output, table repair overlays, and figures
- make retrieval changes measurable through fixed-corpus evaluations, replay suites, and live search telemetry
- keep orchestration explicit, typed, durable, and inspectable rather than prompt-only
- make generated document claims replayable, calibrated, and auditable through persisted claim-support judgments and evaluation cases

## Current Contracts

These contracts are now part of the live system:

- `docling.json` is the canonical machine-readable document parse artifact.
- `document.yaml` is the human-readable document artifact.
- Table JSON is canonical. Table YAML is derived.
- Figure JSON is canonical. Figure YAML is derived.
- YAML is never a machine-facing source of truth for search, ranking, validation, or persistence.
- `documents.active_run_id` is the only visible retrieval version for chunks, tables, figures, document artifacts, and evaluation lookup.
- A failed or non-promoted run does not change the current active corpus.
- Tables are first-class retrieval objects with logical-table rows, source-segment provenance, merge metadata, audit hashes, and table artifacts.
- Figures are first-class persisted outputs with artifacts and provenance metadata.
- `/search` returns a single mixed typed result list across chunks and tables.
- Mixed-search filters remain intentionally small: `document_id`, `page_range`, and optional `result_type`.
- OpenAI embeddings use the pinned `text-embedding-3-small` 1536-dimension contract.
- Run evaluations are first-class persisted records, with top-level inspection through `GET /documents/{document_id}/evaluations/latest`.
- Table supplements are registry-driven from `config/table_supplements.yaml`; supplements are repair inputs for specific table families, not second canonical documents.
- Agent-task context is canonicalized as `storage/agent_tasks/<task_id>/context.json`; `context.yaml` is a human-readable sidecar.
- Migrated agent tasks consume upstream state through typed context refs, not legacy nested result payload reads.

## Runtime Topology

The deployed local system has these runtime components:

### 1. API service

The FastAPI app serves:

- document ingest and inspection endpoints
- search, replay, harness, and chat endpoints
- quality and evaluation inspection endpoints
- agent-task creation, inspection, analytics, approval, and trace export endpoints
- the read-only local browser UI under `/ui`

### 2. Ingest and retrieval worker

The main worker:

- claims queued document runs using DB-backed leases
- runs Docling parsing
- normalizes chunks, tables, and figures
- writes JSON and YAML artifacts
- generates embeddings when OpenAI is available
- validates the run
- promotes successful runs to `documents.active_run_id`
- refreshes auto-generated evaluation fixtures
- runs persisted evaluation checks for completed validated runs

### 3. Agent-task worker

The agent-task worker:

- claims executable tasks using DB-backed leases
- records attempt rows, heartbeats, retries, cost, and performance payloads
- writes task artifacts and failure artifacts
- persists verifier rows and outcome labels
- enforces approval gates for promotable tasks
- emits typed outputs and task context artifacts

### 4. Postgres + pgvector

The database stores:

- documents, runs, chunks, tables, figures, and evaluations
- direct-search request history, feedback, chat answers, and replay runs
- quality candidates and failure signals
- agent tasks, dependencies, attempts, verifier rows, artifacts, outcomes, approvals, and analytics inputs
- vector embeddings for chunk and table search

### 5. Filesystem-backed storage

Canonical artifacts live under `storage/`:

- source PDFs
- per-run parse and derived artifacts
- per-task context and failure artifacts
- task-specific JSON artifacts such as triage summaries
- the auto-generated evaluation corpus companion file

## Data Model and State Machines

### Documents and runs

`documents` is the logical-document table. A document tracks:

- source filename and managed source path
- checksum and MIME type
- title and page count when known
- `latest_run_id`
- `active_run_id`

`document_runs` is both the version record and the durable queue record. A run tracks:

- `run_number`
- `status`
- attempts, lease, and heartbeat fields
- failure stage and failure artifact path
- artifact paths for `docling.json` and `document.yaml`
- persisted chunk, table, and figure counts
- embedding model and dimension metadata
- validation status and structured validation results

Current document-run statuses are:

- `queued`
- `processing`
- `validating`
- `retry_wait`
- `completed`
- `failed`

### Retrieval objects

The active retrieval corpus is made of run-scoped:

- prose chunks
- logical tables
- figures

Key current properties:

- chunk rows preserve text, heading, page span, and search metadata
- table rows preserve title, heading, page span, search text, preview text, merge metadata, repeated-header metadata, and logical lineage when available
- figure rows preserve page location, caption, artifact paths, and provenance metadata

### Agent tasks

The agent-task substrate adds a second durable state machine for orchestration work.

Tasks persist:

- task type
- typed input and typed output
- status
- dependency edges
- workflow, prompt, tool, and model version metadata
- approval fields
- attempt history
- verifier rows
- artifacts
- outcome labels
- replayable failure artifacts

Current agent-task statuses are:

- `blocked`
- `awaiting_approval`
- `rejected`
- `queued`
- `processing`
- `retry_wait`
- `completed`
- `failed`

Dependency edges are role-aware. Current dependency kinds are:

- `explicit`
- `target_task`
- `source_task`
- `draft_task`
- `verification_task`

## Ingest, Reprocess, and Promotion Flow

### Ingest entry points

The system currently supports two ingest entry points:

- `POST /documents` for multipart PDF upload
- CLI-only local path ingest for trusted operator workflows

CLI ingest currently includes:

- `docling-system-ingest-file`
- `docling-system-ingest-dir`
- ingest-batch list/show inspection commands

Directory ingest now creates durable ingest batches and batch-item rows so operators can inspect queued, duplicate, recovery, and failed items separately from the underlying document runs.

### Local path ingest policy

Local path ingest is policy-constrained:

- paths must live under allowed roots
- if `DOCLING_SYSTEM_LOCAL_INGEST_ALLOWED_ROOTS` is unset, the default roots are the repo working directory, `~/Documents`, and `~/Downloads`
- symlinks are rejected
- files must be PDFs by extension and header
- duplicate content is deduped by checksum
- file size and page count limits are enforced

### Duplicate and recovery behavior

Deduplication is checksum-based:

- if the checksum already belongs to a document with an active successful run, the system returns the existing document as a duplicate instead of creating a new logical document
- if the checksum exists but the document does not currently have an active successful run, the system creates a new recovery run for that existing document
- reprocessing always creates a new run for an existing logical document; it never creates a second canonical document

### Worker processing flow

The current run pipeline is:

1. stage upload or local file
2. compute checksum
3. resolve duplicate or create document/run rows
4. claim the run through the polling worker lease
5. parse the PDF with Docling
6. derive canonical and human-readable document artifacts
7. normalize chunks, logical tables, source segments, and figures
8. apply configured table supplements when a matching rule exists
9. generate embeddings for chunks and tables when OpenAI is available
10. persist run-scoped rows and artifacts
11. validate the run
12. if validation passes, atomically promote the run to `documents.active_run_id`
13. refresh the auto-generated evaluation fixture and evaluate the new active run

### Promotion rule

The promotion rule remains strict:

- only a validation-passing run can become active
- failed or partial reprocessing never changes the visible active corpus
- retrieval queries always join through `documents.active_run_id`

## Retrieval and Search

### Search contract

`POST /search` returns one ranked list of typed results:

- `result_type = "chunk"`
- `result_type = "table"`

Supported search modes are:

- `keyword`
- `semantic`
- `hybrid`

Supported filters are:

- `document_id`
- `page_range`
- `result_type`

Search is active-run-only. The system never mixes retrieval rows from an in-progress or failed run into active search results.

### Search harnesses

The system now supports named search harnesses so operators can compare retrieval profiles and rerankers without changing the active document corpus.

Current harnesses are:

- `default_v1`
- `wide_v2`
- `prose_v3`

Applied review harness changes are persisted in `config/search_harness_overrides.json`. Draft harness changes remain task artifacts until verified and approved.

### Search telemetry

Every direct search request is persisted. The system records:

- requested and served mode
- query text and filters
- harness snapshot
- internal `query_intent`
- candidate-source breakdown
- metadata-supplement and adjacent-context candidate counts
- per-result rerank feature snapshots

Search feedback is also persisted and can be replayed later through the replay surface.

Search also writes a knowledge-operator evidence chain. Each persisted request now records
separate `retrieve`, `rerank`, and deterministic `judge` operator runs, with input/output
hashes, harness/config fingerprints, candidate sets, selected evidence, and parent-run
lineage. `GET /search/requests/{search_request_id}/evidence-package` exports the replayable
evidence package for the request, including source document checksums, active-run validation
state, result snapshots, chunk/table source records, table segment provenance, and package
hashes.

### Current prose experiment

The current non-default `prose_v3` harness extends prose-heavy retrieval with:

- metadata-based candidate widening
- adjacent-context expansion
- extra candidate-source telemetry

It is intentionally experimental and evaluated separately from `default_v1`.

## Grounded Chat

The UI and API now include grounded chat on top of the active retrieval corpus.

Current behavior:

- the chat flow retrieves chunks and tables from active search
- answers are synthesized with citations when OpenAI is configured
- if OpenAI is unavailable, the system falls back to extractive evidence snippets
- answer-level feedback is persisted
- the chat surface remains grounded to retrieved context rather than free-form corpus memory

## Evaluation, Replay, and Quality Loops

### Run evaluations

Run evaluations are persisted first-class records. Operators can inspect the latest active-run evaluation for a document through:

- `GET /documents/{document_id}/evaluations/latest`

Evaluations currently cover:

- structural checks
- expected table and figure counts
- merge behavior expectations
- query hit expectations
- figure provenance and artifact coverage
- figure caption expectations
- cross-document contamination guards
- answer-side citation purity and fallback behavior for certain fixtures

### Manual and auto-generated evaluation corpora

The durable human-authored evaluation corpus is:

- `docs/evaluation_corpus.yaml`

The worker also maintains:

- `storage/evaluation_corpus.auto.yaml`

Current contract:

- manual fixtures remain the durable source of truth
- auto-generated fixtures cover newly ingested documents immediately after validation
- fixture selection is keyed by `source_filename`
- if both manual and auto-generated fixtures exist for the same source filename, the manual fixture wins

### Search replay and harness evaluation

The system now supports replay and comparison workflows for retrieval changes.

Current replay surfaces include:

- one-off replay of persisted search requests
- replay suites
- named-harness comparisons
- persisted replay-run detail and comparison endpoints
- persisted harness-evaluation list and detail endpoints

Current replay suites include:

- `evaluation_queries`
- `feedback`
- `live_search_gaps`
- `cross_document_prose_regressions`

Harness evaluations are first-class persisted resources. `POST /search/harness-evaluations`
creates a durable evaluation row, stores one source row per replay source type, and
links every source row to the baseline and candidate replay runs that produced the
metrics. Operators and agents can inspect the resource through:

- `GET /search/harness-evaluations`
- `GET /search/harness-evaluations/{evaluation_id}`
- `docling-system-search-harness-evaluation-list`
- `docling-system-search-harness-evaluation-show <evaluation_id>`

The evaluation UI also reads from the durable list/detail endpoints so recent
harness comparisons remain inspectable after the original POST response is gone.

### Quality signals

The quality surface currently aggregates:

- fixed-corpus evaluation failures
- live search gaps such as zero-result and missing-table cases
- unsupported or incomplete grounded chat answers

Operators can inspect:

- summary
- failures
- evaluation statuses
- candidate gaps
- trends

## Tables, Figures, and Supplements

### Tables

Tables are a first-class system concern, not just parser byproducts.

The current table pipeline:

- persists logical tables as searchable objects
- preserves source-segment provenance
- records continuation-merge and ambiguity metadata
- removes repeated headers when evidence is strong enough
- keeps audit information to support future reranking and repair workflows

`table_id` remains run-scoped. `logical_table_key` remains best-effort lineage across runs and may be null.

### Figures

Figures are now also first-class persisted outputs.

The system persists:

- figure rows
- figure JSON artifacts
- figure YAML artifacts
- caption and provenance metadata

Top-level figure inspection lives at:

- `GET /documents/{document_id}/figures`
- `GET /documents/{document_id}/figures/{figure_id}`

### Supplement overlays

The supplement mechanism is a narrow repair path for known-bad table families.

Current supplement rules:

- live in `config/table_supplements.yaml`
- select specific clean supporting PDFs
- preserve the chapter PDF as the canonical source document
- overlay cleaner table-family rows while retaining chapter-local page spans and original source-segment lineage

The intended repair workflow is still:

1. keep the chapter PDF as the canonical document
2. add a clean supporting PDF as a supplement input under allowed local roots
3. register the repair rule
4. add evaluation coverage in `docs/evaluation_corpus.yaml`
5. reprocess and verify both retrieval and structural evaluation results

## Agent-Task Orchestration Layer

### Purpose

The agent-task layer is now a durable orchestration substrate for bounded operational work. It is not a second prompt-only memory system.

It exists to:

- inspect persisted evaluations and quality gaps
- run bounded replay and harness comparison work
- draft and verify retrieval configuration changes
- gate promotable actions behind approvals
- export durable traces for later analysis

### Current task catalog

The current registry includes:

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
- `evaluate_document_generation_context_pack`
- `draft_technical_report`
- `verify_technical_report`
- `evaluate_claim_support_judge`
- `draft_claim_support_calibration_policy`
- `verify_claim_support_calibration_policy`
- `apply_claim_support_calibration_policy`
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

### Current task guarantees

The orchestration layer now guarantees:

- typed input validation at task creation
- typed output validation for migrated tasks before completion
- additive action-catalog metadata for `output_schema_name`, `output_schema_version`, and `output_schema`
- dependency-edge persistence with role-aware `dependency_kind`
- attempt rows with heartbeats, retries, cost payloads, and performance payloads
- verifier rows persisted separately from task results
- durable outcome labels with duplicate-label rejection per actor/label/task
- replayable failure artifacts
- approval-gated task transitions for promotable actions
- task-context projection through canonical `context.json` plus derived `context.yaml`

### Context model

Task context is now explicit and structured.

Each migrated task can expose:

- `context_summary`
- `context_refs`
- `context_artifact_id`
- `context_freshness_status`
- `dependency_edges`

Context refs track:

- schema name and version
- observed content hash
- source update time
- last check time
- freshness status

Freshness statuses are currently:

- `fresh`
- `stale`
- `missing`
- `schema_mismatch`

Current enforcement:

- `missing` and `schema_mismatch` block migrated consumers
- `stale` is advisory in v1
- migrated consumers do not fall back to legacy nested payload reads
- pre-context upstream tasks must be rerun before migrated downstream tasks will consume them

### Workflow-style tasks in the current system

Current workflow-heavy paths include:

- `evaluate_search_harness`, which produces typed evaluation output and context refs to replay evidence
- `verify_search_harness_evaluation`, which verifies a target evaluation through its `target_task` context ref
- `triage_replay_regression`, which mines unresolved quality candidates, runs comparative replay work, and produces a recommendation plus a deeper triage summary artifact
- `export_semantic_supervision_corpus`, which exports reviewed semantic signals, semantic expectations, and grounded-document verification outcomes into durable supervision artifacts
- `discover_semantic_bootstrap_candidates`, which mines provisional concept candidates directly from active document corpora so the semantic layer can bootstrap on arbitrary user data without assuming the current registry already matches the domain
- `evaluate_semantic_candidate_extractor`, which compares a shadow semantic candidate extractor against the lexical baseline and fixed semantic expectations without mutating live semantics
- `triage_semantic_candidate_disagreements`, which consumes that evaluation through its `target_task` context ref and turns candidate-only gaps into typed issues plus bounded follow-up recommendations
- `draft_semantic_registry_update` can now consume either semantic triage output or bootstrap candidate discovery through its `source_task` context ref, while keeping publication on the existing verify/apply/reprocess path
- `initialize_workspace_ontology`, which seeds an empty workspace from the generic upper ontology without assuming any sample-domain semantics already exist
- `get_active_ontology_snapshot`, which exposes the DB-backed live ontology snapshot that semantic passes and generation now reference
- `draft_ontology_extension`, which turns bootstrap or semantic-triage output into a reviewable additive ontology draft without mutating live state
- `verify_draft_ontology_extension`, which checks that ontology draft against active documents before publication
- `apply_ontology_extension`, which is approval-gated and publishes the verified ontology draft as the new active workspace snapshot
- `build_document_fact_graph`, which compacts approved semantic assertions into a small reusable fact graph for grounded generation and later orchestration
- `build_shadow_semantic_graph`, which compacts reviewed semantic assertions into a reusable cross-document shadow graph without mutating live state
- `evaluate_semantic_relation_extractor`, which compares a shadow relation extractor against a deterministic baseline and fixed expected graph edges
- `triage_semantic_graph_disagreements`, which consumes that evaluation through its `target_task` context ref and turns candidate-only graph gaps into typed issues plus bounded promotion follow-ups
- `draft_graph_promotions`, which prepares a reviewable graph-memory snapshot update without changing the live graph
- `verify_draft_graph_promotions`, which verifies those promotions against ontology compatibility, domain/range relation constraints, traceability, inverse/symmetry conflicts, and stale-snapshot checks
- `apply_graph_promotions`, which is approval-gated and publishes the verified graph snapshot as the new active workspace graph memory
- `prepare_semantic_generation_brief`, which builds a typed semantic dossier, section plan, claim set, and evidence pack for one bounded `knowledge_brief`
- `prepare_semantic_generation_brief` can also consume approved graph memory so grounded briefs can pull in cross-document concept relations without reparsing raw evidence every time
- `prepare_semantic_generation_brief` can also expose additive `shadow_candidates` and `shadow_candidate_summary` fields from the candidate layer while keeping grounded drafting tied only to the live dossier
- `draft_semantic_grounded_document`, which consumes the migrated brief through its `target_task` context ref and emits a grounded document draft plus markdown sidecar without publishing anything live
- `verify_semantic_grounded_document`, which verifies claim traceability, required-concept coverage, and evidence-pack integrity through its `target_task` context ref
- `plan_technical_report -> build_report_evidence_cards -> prepare_report_agent_harness -> evaluate_document_generation_context_pack -> draft_technical_report -> verify_technical_report`, which turns the semantic dossier and approved graph memory into a report plan, typed evidence cards, a reusable `document_generation_context_pack`, a pre-generation context-pack quality gate, a verification-ready report draft, and a verifier gate that checks refreshed context, claim traceability, claim-support judgments, graph approval, and concept coverage
- technical-report drafting and verification also write `generate` and `verify` knowledge-operator runs so generated documents carry a database-backed activity trail from harness input through verifier outcome
- `evaluate_document_generation_context_pack`, which validates the context pack hash, traceable-claim ratio, context refs, blocked steps, source evidence package availability, and freshness blockers before any report draft has to be generated
- `draft_technical_report`, which now refuses to render until the latest context-pack gate for the target harness has passed and its recorded context-pack hash matches the current harness
- technical-report drafts persist a frozen claim-derivation evidence package and per-claim derivation rows; `GET /agent-tasks/{task_id}/audit-bundle` returns the draft, verification, evidence package export, claim derivations, context-pack artifact/evaluation/verifier/operator chain, operator runs, and active-run change-impact status for court-grade review
- `evaluate_claim_support_judge`, which replays governed hard-case fixture sets against the technical-report claim-support judge, persists `claim_support_fixture_sets`, `claim_support_calibration_policies`, `claim_support_evaluations`, and `claim_support_evaluation_cases`, records a judge operator run, writes a replay artifact, and exposes a typed context summary with fixture-set and active-policy hashes plus the pass/fail gate outcome
- `draft_claim_support_calibration_policy -> verify_claim_support_calibration_policy -> apply_claim_support_calibration_policy`, which governs claim-support replay policy changes through a draft row, fixture replay verifier, unchanged-draft hash checks, approval-gated activation, prior-policy retirement, and a database-enforced single active policy per policy name
- `draft_harness_config_update`, which creates a review harness artifact without changing live search behavior
- `verify_draft_harness_config`, which evaluates a draft harness and records a verifier outcome
- `apply_harness_config_update`, which consumes typed `draft_task` and `verification_task` refs and, after approval, publishes the verified harness into `config/search_harness_overrides.json`
- `enqueue_document_reprocess`, which is approval-gated and queues document reprocessing without changing the current active run until the normal ingest path completes successfully

The portable ontology workflow keeps the repo domain agnostic: `config/upper_ontology.yaml` is the only shipped semantic seed, while corpus-derived ontology snapshots, approved facts, approved graph relations, and workspace review state live in the database and can be rebuilt from arbitrary user data.

### Analytics and exports

The agent-task analytics surface is now broad enough to answer:

- task volume and state trends
- verifier pass/fail trends
- approval and rejection trends
- recommendation rates and recommendation trends
- cost summaries and cost trends
- performance summaries and performance trends
- value-density views
- workflow-version comparisons
- trace exports with outcomes, artifacts, verifications, approvals, and context summaries

## Storage Layout

The current filesystem layout is:

```text
storage/
  source/<document-id>.pdf
  runs/<document-id>/<run-id>/
    docling.json
    document.yaml
    failure.json
    tables/
      <table-index>.json
      <table-index>.yaml
    figures/
      <figure-index>.json
      <figure-index>.yaml
  agent_tasks/<task-id>/
    context.json
    context.yaml
    failure.json
    ...task-specific artifacts...
  evaluation_corpus.auto.yaml
```

The machine-facing rule stays the same:

- JSON is canonical
- YAML is derived for operator inspection
- API endpoints expose artifacts directly instead of exposing raw storage paths as the user-facing contract

## API Surface

The API now has five major domains.

### Document and artifact endpoints

These cover:

- health and metrics
- document list/detail
- upload ingest
- run history
- latest evaluation detail
- active chunks, tables, and figures
- document, table, and figure artifact download
- explicit reprocessing

### Search and chat endpoints

These cover:

- mixed retrieval
- persisted search request detail
- search feedback
- replay request creation
- replay list/detail/compare
- harness listing
- harness evaluation
- grounded chat
- chat-answer feedback

### Quality endpoints

These cover:

- quality summary
- quality failures
- evaluation status list
- evaluation candidate gaps
- quality trends

### Agent-task endpoints

These cover:

- action catalog
- task list and creation
- task detail
- full task context in JSON or YAML
- outcome labels
- artifacts
- verifier records
- failure artifacts
- approvals and rejections
- analytics and workflow-version summaries
- durable trace export

### UI

The API also mounts the operator UI under `/ui`.

The UI currently exposes:

- documents and runs
- search, replay, and feedback
- tables and figures
- evaluation and quality inspection
- active agent tasks and workflow lineage

## Operational Workflow

The current intended operator workflow is:

1. ingest PDFs through CLI local-file/directory ingest or API upload
2. let the worker parse, validate, promote, and evaluate
3. inspect document artifacts, tables, figures, and evaluations through the API or UI
4. use search to inspect the active corpus
5. label gaps through search feedback and quality inspection
6. run replay suites or harness evaluations to compare retrieval behavior
7. use agent tasks to triage regressions, draft harness updates, verify them, and require approval before publishing overrides or queueing reprocess work

## Non-Goals and Current Limits

The system deliberately does not do certain things yet.

Current non-goals or limits include:

- no public arbitrary file-path ingest over HTTP
- no multi-tenant or internet-facing product assumptions
- no unbounded autonomous agent control plane
- no hidden YAML or prompt state acting as the machine-facing source of truth
- no automatic live harness publication without verification and approval
- no multi-provider embedding matrix in the current schema
- no broad arbitrary search-filter surface beyond the current indexed filters

Other current constraints:

- semantic retrieval depends on OpenAI embeddings under the pinned contract
- if OpenAI returns `429 insufficient_quota`, validated ingest still succeeds but semantic retrieval degrades to keyword-backed behavior
- the supplement registry is intentionally narrow and provisional
- the system is still optimized for local operator use and auditability rather than high-scale distributed throughput

## Source of Truth

Going forward, this file should be treated as the high-level system reference. It supersedes the original rebuilt v1 plan and should be updated whenever the live contracts, orchestration model, evaluation surface, or operator workflow materially changes.

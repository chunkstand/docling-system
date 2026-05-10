# Data Model Boundary Plan

Purpose: reduce `app/db/models.py` centrality without destabilizing Alembic,
`Base.metadata.create_all(...)`, or active runtime imports.

Status refreshed: 2026-05-10. `app/db/models.py` remains the highest current
architecture-quality hotspot, but the first five model-domain splits are
complete or verified locally: `platform support` owns `ApiIdempotencyKey` in
`app/db/model_domains/platform.py`, `ingest` owns `IngestBatch`,
`IngestBatchItem`, `Document`, and `DocumentRun` in
`app/db/model_domains/ingest.py`, and `document_artifacts` owns
`DocumentRunEvaluation`, `DocumentRunEvaluationQuery`, `DocumentChunk`,
`DocumentTable`, `DocumentTableSegment`, and `DocumentFigure` in
`app/db/model_domains/document_artifacts.py`. The retrieval-interaction ledger
now lives in `app/db/model_domains/retrieval_interactions.py` for the verified
local Milestone 1 split, and the retrieval replay and release governance slice
now lives in `app/db/model_domains/retrieval_replay_governance.py` for the
verified local Milestone 8 split. `app.db.models` remains the public
compatibility facade at 4,525 lines. Each model-domain milestone must finish
with a local commit before another domain moves.

## Proposed Domains

- ingest: `IngestBatch`, `IngestBatchItem`, `Document`, `DocumentRun`
- document artifacts: `DocumentChunk`, `DocumentTable`, `DocumentTableSegment`,
  `DocumentFigure`, `DocumentRunEvaluation`, `DocumentRunEvaluationQuery`
- retrieval: search requests, result rows, replay rows, harness evaluations,
  releases, training runs, reranker artifacts, feedback, chat answers
- semantic memory: ontology snapshots, concepts, assertions, entities, facts,
  semantic passes, graph snapshots, governance events
- agent tasks: tasks, dependencies, attempts, artifacts, outcomes,
  verifications, operator runs, context input/output rows
- audit and evidence: evidence exports, manifests, traces, claim derivations,
  technical-report readiness gates, retrieval feedback ledgers
- claim support: fixture sets, calibration policies, evaluations, policy-change
  impacts, replay-alert waivers, fixture-corpus rows
- platform support: API idempotency keys and other cross-cutting runtime rows

## Required Sequence

1. Add import-compatibility tests that prove existing `from app.db.models import X`
   imports still work. Completed in `tests/unit/test_db_model_import_compatibility.py`.
2. Introduce domain modules under `app/db/model_domains/` while keeping
   `app/db/models.py` as the public compatibility facade. First slice completed
   with `app/db/model_domains/platform.py`.
3. Move one domain at a time and keep table names, enum values, relationship
   strings, indexes, constraints, and metadata registration unchanged.
4. Run exact Alembic DDL verification against local Postgres.
5. Run `Base.metadata.create_all(...)` against local Postgres.
6. Run `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`.
7. Update this plan and `docs/SESSION_HANDOFF.md` with the moved domain,
   verification results, residual risk, and next candidate.
8. Commit the domain split locally as its own milestone slice.

## Compatibility Harness

- Shared contract: `tests/db_model_contract.py`
- Public import contract: `tests/unit/test_db_model_import_compatibility.py`
- Postgres metadata/create-all contract: `tests/integration/test_db_model_metadata.py`

## Owner Surfaces

- hotspot facade: `app/db/models.py`
- focused owner modules: `app/db/model_domains/*.py`
- shared metadata contract: `tests/db_model_contract.py`
- import compatibility gate:
  `tests/unit/test_db_model_import_compatibility.py`
- Postgres metadata and `Base.metadata.create_all(...)` gate:
  `tests/integration/test_db_model_metadata.py`
- migration drift gate: Alembic commands run against the local Postgres target
- routing docs: this plan, `docs/hotspot_owner_resolution_plan.md`, and
  `docs/SESSION_HANDOFF.md`

## Placement Rules

- Keep `app/db/models.py` as the public compatibility facade until the repo
  deliberately changes that import contract.
- Move one bounded ORM concern at a time into `app/db/model_domains/`; do not
  mix retrieval, semantic, agent-task, and claim-support rows in the same
  milestone.
- Re-export every moved enum constant or ORM class from `app/db/models.py`
  before changing any caller imports.
- Extend the shared metadata contract for every moved table before closing the
  milestone.
- Treat generated columns, vector dimensions, named indexes, unique
  constraints, and relationship strings as compatibility surfaces, not
  implementation details.

## Weak-Point Prevention Contract

Weak point forecast: a model-domain split can appear clean while silently
changing emitted DDL, breaking `app.db.models` imports, or creating a new
`model_domains` dump file that simply relocates the hotspot.

Owner surface: `app/db/models.py`, the target `app/db/model_domains/*.py`
module, the shared metadata contract tests, Alembic, and the current handoff
and hotspot-owner plan.

Prevention gates:

- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

Fail thresholds:

- any public `app.db.models` import breaks
- any named index, unique constraint, generated column, vector dimension, or
  relationship contract drifts unexpectedly
- Alembic emits unexpected DDL or `Base.metadata.create_all(...)` changes the
  supported schema shape
- the new owner module becomes broad enough that it should have been split
  again before commit

Controlled violations:

- remove one moved symbol from the `app.db.models` re-export path and verify
  the import-compatibility test fails
- change a required index or unique-constraint expectation in the metadata
  harness and verify the integration gate fails

Future-Codex misuse scenario: the likely failure is moving replay, release, or
training rows into the same retrieval-interaction module just because they live
near the same search tables today. This plan prevents that by naming the
interaction-ledger rows explicitly, keeping the replay/release and learning
surfaces deferred, and requiring the new owner module to stay narrow enough to
pass the same gating and review pattern again in the next slice.

The harness currently protects 109 public `app.db.models` symbols: 29 enums and
80 ORM model classes. It also asserts the 80-table `Base.metadata` contract and
checks that schema-scoped Postgres `Base.metadata.create_all(...)` creates the
expected tables. The harness also protects required model indexes, unique
constraints, and their exact column ordering where required to remain aligned
with migrations, including
`ix_document_runs_status_completed_at`,
`ix_api_idempotency_keys_created_at`, ingest/document indexes, and named unique
constraints such as `uq_api_idempotency_keys_scope_key`,
`uq_ingest_batch_items_batch_relative_path`, and
`uq_document_runs_doc_run_number`.

## Completed Splits

Completed on 2026-05-09: `platform support`: `ApiIdempotencyKey`.

Reasoning:

- It is a single-table domain.
- It has no outbound ORM relationships.
- It exercises table metadata, a unique constraint, an index, JSONB storage,
  and the public `app.db.models` compatibility facade.
- The Milestone 1 Postgres check already records the expected
  `api_idempotency_keys` column contract.

Implemented result:

- Added `app/db/model_domains/platform.py`.
- Re-exported `ApiIdempotencyKey` from `app/db/models.py` for import
  compatibility.
- Moved no other ORM class.
- Preserved the `api_idempotency_keys` table, columns, JSONB response storage,
  `ix_api_idempotency_keys_created_at` index, and
  `uq_api_idempotency_keys_scope_key` unique constraint.
- Verified the created-at index columns and the `scope`, `idempotency_key`
  unique-constraint columns in both unit metadata and Postgres create-all paths.
- Verified with focused import, metadata, Alembic, architecture, and full
  DB-backed gates.

Completed on 2026-05-10: `ingest`: `IngestBatch`, `IngestBatchItem`,
`Document`, and `DocumentRun`.

Implemented result:

- Added `app/db/model_domains/ingest.py`.
- Re-exported the ingest domain models and document metadata generated-column SQL
  constants from `app/db/models.py`.
- Preserved ingest/document table names, columns, foreign keys, indexes, unique
  constraints, check constraints, and `documents.metadata_textsearch` generated
  DDL.
- Extended unit and Postgres create-all metadata contracts for ingest-domain
  columns, index columns, and unique-constraint column ordering.
- Verified with focused import, metadata, Alembic, architecture, hygiene,
  hotspot-prevention, and full DB-backed gates.

Completed on 2026-05-10: `document_artifacts`: `DocumentRunEvaluation`,
`DocumentRunEvaluationQuery`, `DocumentChunk`, `DocumentTable`,
`DocumentTableSegment`, and `DocumentFigure`.

Closeout commit:

- `060b537` (`architecture: complete hotspot owner milestone 1 document-artifacts`)

Implemented result:

- Added `app/db/model_domains/document_artifacts.py`.
- Re-exported the document-artifact models from `app/db/models.py`.
- Preserved document-artifact table names, columns, computed TSVECTOR columns,
  HNSW/GIN indexes, foreign keys, and named unique constraints.
- Extended the unit and Postgres create-all metadata contracts for
  document-artifact tables, index names, index column ordering, unique
  constraint names, and unique-constraint column ordering.
- Reduced `app/db/models.py` from 5,800 lines to 5,537 lines and ratcheted the
  `config/hygiene_policy.yaml` ceiling to match.
- Reduced the architecture-quality `max_hotspot_risk_score` from `692.67` to
  `681.91` while keeping `app/db/models.py` as the top governed hotspot.
- Verified with focused import, metadata, Alembic, architecture, hygiene,
  hotspot-prevention, and full DB-backed gates.

Verified locally on 2026-05-10: `retrieval interactions`:
`SearchRequestRecord`, `SearchRequestResult`, `RetrievalEvidenceSpan`,
`RetrievalEvidenceSpanMultiVector`, `SearchRequestResultSpan`,
`SearchFeedback`, `ChatAnswerRecord`, and `ChatAnswerFeedback`.

Implemented result:

- Added `app/db/model_domains/retrieval_interactions.py`.
- Re-exported the retrieval-interaction models from `app/db/models.py` through
  import-forwarder aliases so the hotspot-prevention gate remains green.
- Preserved retrieval table names, columns, foreign keys, named indexes, unique
  constraints, computed TSVECTOR SQL, and vector dimensions.
- Extended the unit and Postgres create-all metadata contracts for
  retrieval-interaction table columns, exact index column ordering, exact
  unique-constraint column ordering, vector dimensions, and computed SQL.
- Reduced `app/db/models.py` from 5,537 lines to 5,067 lines and ratcheted the
  `config/hygiene_policy.yaml` ceiling to match.
- Reduced the architecture-quality `max_hotspot_risk_score` from `681.91` to
  `673.78` while keeping `app/db/models.py` as the top governed hotspot.
- Verified with focused import, metadata, Alembic, evaluation-data-readiness,
  architecture, hygiene, hotspot-prevention, and full DB-backed gates.

Verified locally on 2026-05-10: `retrieval replay and release governance`:
`SearchReplayRun`, `SearchReplayQuery`, `SearchHarnessEvaluation`,
`SearchHarnessEvaluationSource`, `SearchHarnessRelease`, and
`SearchHarnessReleaseReadinessAssessment`.

Implemented result:

- Added `app/db/model_domains/retrieval_replay_governance.py`.
- Re-exported the replay/release governance models from `app/db/models.py`
  through import-forwarder aliases so the hotspot-prevention gate remains
  green.
- Preserved replay and release governance table names, columns, foreign keys,
  named indexes, unique constraints, and check constraints.
- Extended the unit and Postgres create-all metadata contracts for replay and
  release governance table columns, exact index column ordering, and exact
  unique-constraint column ordering.
- Reduced `app/db/models.py` from 5,067 lines to 4,525 lines and ratcheted the
  `config/hygiene_policy.yaml` ceiling to match.
- Reduced the architecture-quality `max_hotspot_risk_score` from `673.78` to
  `668.17` while keeping `app/db/models.py` as the top governed hotspot.
- Verified with focused import, metadata, Alembic, evaluation-data-readiness,
  architecture, hygiene, hotspot-prevention, and full DB-backed gates.

Next model-domain candidate when model work resumes:

- `retrieval learning`: `RetrievalJudgmentSet`, `RetrievalJudgment`,
  `RetrievalHardNegative`, `RetrievalTrainingRun`,
  `RetrievalLearningCandidateEvaluation`, and `RetrievalRerankerArtifact`

Deferred retrieval follow-ons after the replay/release slice proves clean:
- none; the retrieval learning family is now the active routed follow-up

Current routed follow-up after the verified High Value Technical Paydown
Milestone 8 replay/release split:

- next owner case remains `IC-F2A8110185EB` / `app/db/models.py`
- next model-domain candidate: `retrieval learning`
- target ORM family:
  `RetrievalJudgmentSet`,
  `RetrievalJudgment`,
  `RetrievalHardNegative`,
  `RetrievalTrainingRun`,
  `RetrievalLearningCandidateEvaluation`, and
  `RetrievalRerankerArtifact`

## Per-Domain Acceptance Gate

Each model-domain split is complete only when all of these are true:

- Public imports from `app.db.models` remain covered by
  `tests/unit/test_db_model_import_compatibility.py`.
- The moved classes still register the same table names, columns, indexes,
  constraints, enum values, and relationship strings in `Base.metadata`.
- Schema-scoped Postgres `Base.metadata.create_all(...)` passes through
  `tests/integration/test_db_model_metadata.py`.
- Alembic has one head, upgrades cleanly, and reports no unexpected
  autogenerate drift.
- Full DB-backed tests run with `DOCLING_SYSTEM_RUN_INTEGRATION=1`; skipped
  Postgres coverage is not an acceptable closeout.
- `docs/data_model_boundary_plan.md`, `docs/architecture_plan_01.md`, and
  `docs/SESSION_HANDOFF.md` identify what moved and what moves next.
- The verified slice is committed locally before any follow-on model-domain
  movement.

Minimum commands for each model-domain split:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_db_model_import_compatibility.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py
uv run --extra dev alembic heads
uv run --extra dev alembic current
uv run --extra dev alembic upgrade head
uv run --extra dev alembic check
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
git status --short
git diff --stat
git diff --cached --stat
```

## Stop Conditions

- Alembic emits unexpected DDL.
- `Base.metadata.create_all(...)` changes nullability or generated expressions.
- Any public `app.db.models` import breaks.
- Integration tests require skipped Postgres-backed coverage to pass.
- The verified split cannot be isolated into one local commit because unrelated
  dirty files are mixed into the same edit surface.

## Non-Goals

- No schema redesign during the split.
- No table renames.
- No enum value changes.
- No relationship rewrites unless required to preserve current behavior.

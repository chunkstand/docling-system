# Data Model Boundary Plan

Purpose: reduce `app/db/models.py` centrality without destabilizing Alembic,
`Base.metadata.create_all(...)`, or active runtime imports.

Status refreshed: 2026-05-09. `app/db/models.py` remains the highest current
architecture-quality hotspot, but the first model-domain split is complete:
`platform support` now owns `ApiIdempotencyKey` in
`app/db/model_domains/platform.py` while `app.db.models` remains the public
compatibility facade. Each model-domain milestone must finish with a local
commit before another domain moves.

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

The harness currently protects 109 public `app.db.models` symbols: 29 enums and
80 ORM model classes. It also asserts the 80-table `Base.metadata` contract and
checks that schema-scoped Postgres `Base.metadata.create_all(...)` creates the
expected tables. The harness also protects required model indexes and unique
constraints that must remain aligned with migrations, including
`ix_document_runs_status_completed_at`,
`ix_api_idempotency_keys_created_at`, and
`uq_api_idempotency_keys_scope_key`.

## Completed First Split

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
- Verified with focused import, metadata, Alembic, architecture, and full
  DB-backed gates.

Next model-domain candidate when model work resumes:

- `ingest`: `IngestBatch`, `IngestBatchItem`, `Document`, `DocumentRun`

The next overall Architecture Plan 01 milestone is not another model-domain
move; it is Milestone 3, the first `app/services/evidence.py` split.

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

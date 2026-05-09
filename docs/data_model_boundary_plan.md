# Data Model Boundary Plan

Purpose: reduce `app/db/models.py` centrality without destabilizing Alembic,
`Base.metadata.create_all(...)`, or active runtime imports.

Status refreshed: 2026-05-09. `app/db/models.py` is the highest current
architecture-quality hotspot at 6,026 lines. Do not start this split until
local Postgres is available, because the required closeout includes live
Alembic and `Base.metadata.create_all(...)` verification.

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
   imports still work.
2. Introduce domain modules under `app/db/models/` or another agreed package
   while keeping `app/db/models.py` as the public compatibility facade.
3. Move one domain at a time and keep table names, enum values, relationship
   strings, indexes, constraints, and metadata registration unchanged.
4. Run exact Alembic DDL verification against local Postgres.
5. Run `Base.metadata.create_all(...)` against local Postgres.
6. Run `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`.

## Stop Conditions

- Alembic emits unexpected DDL.
- `Base.metadata.create_all(...)` changes nullability or generated expressions.
- Any public `app.db.models` import breaks.
- Integration tests require skipped Postgres-backed coverage to pass.

## Non-Goals

- No schema redesign during the split.
- No table renames.
- No enum value changes.
- No relationship rewrites unless required to preserve current behavior.

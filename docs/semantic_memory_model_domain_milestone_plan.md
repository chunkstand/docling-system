# Semantic Memory Model-Domain Milestone Plan

Date: 2026-05-11 local
Status: Implemented locally on 2026-05-11; verification complete; broader
owner case reduced, not retired
Owner context: bounded follow-up under the open architecture-governance owner
case for `app/db/models.py`. This milestone resolves the semantic-memory ORM
concern inside the compatibility facade; it does not claim to retire the
entire `IC-F2A8110185EB` hotspot unless the governing architecture report no
longer flags that owner case after closeout.

## Purpose

Resolve the routed `semantic memory` ORM concern inside `app/db/models.py` by
moving the ontology, graph-state, concept, assertion, entity, fact, semantic
review, and governance rows into a focused owner module while preserving the
public `app.db.models` import contract, the exact Postgres schema contract,
and the current semantic-memory behavior.

## Current Evidence

Closeout verification on 2026-05-11 local:

```text
uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=584.8
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/agent_task_actions.py,
    app/services/evidence.py,
    app/schemas/agent_tasks.py
  ]

uv run docling-system-improvement-case-summary
  case_count=26
  status_counts.open=25
  oldest_open_case_id=IC-F2A8110185EB

wc -l app/db/models.py app/db/model_domains/semantic_memory.py
  345 app/db/models.py
  979 app/db/model_domains/semantic_memory.py

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  app/db/models.py is no longer listed in the top 12 churn hotspots
```

Repo-current artifact evidence:

- `app/db/model_domains/semantic_memory.py` now owns the ontology,
  graph-state, concept, assertion, entity, fact, semantic review, and
  governance ORM family.
- `app/db/models.py` remains the public compatibility facade and now
  re-exports the moved semantic-memory symbols at 345 lines.
- `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` now expose dedicated
  semantic-memory table-column, exact index-column, exact unique-constraint,
  ownership, and Postgres metadata coverage.
- `config/hygiene_policy.yaml` now ratchets `app/db/models.py` at 345 lines
  and governs the new semantic-memory owner module at 979 lines.
- `docs/data_model_boundary_plan.md`, `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`, and `docs/SESSION_HANDOFF.md` now route the next
  owner-case follow-up to a compatibility-facade / public-import-contract
  milestone rather than another model-family split.

## Implemented Result

- Added `app/db/model_domains/semantic_memory.py`.
- Re-exported the semantic-memory models from `app/db/models.py` through
  import-forwarder aliases so public imports remain unchanged.
- Extended the shared model-contract harness with semantic-memory
  table-column, exact index-column, and exact unique-constraint coverage.
- Reduced `app/db/models.py` from 1,301 lines to 345 and reduced the
  architecture-quality `max_hotspot_risk_score` from the pre-split `619.67`
  baseline to `584.8`.
- Resolved the semantic-memory ORM concern for this milestone scope while
  leaving the broader `IC-F2A8110185EB` owner case only `reduced` because the
  architecture-quality summary still lists `app/db/models.py` in
  `top_hotspot_paths`.

## Goal

Resolve the semantic-memory concern inside `app/db/models.py` by moving the
remaining semantic-memory ORM family into a dedicated
`app/db/model_domains/semantic_memory.py` owner module behind the existing
`app.db.models` compatibility facade, with stronger shared contract coverage
than exists today.

## Non-Goals

- Do not claim to retire the full `IC-F2A8110185EB` hotspot unless the live
  architecture-quality report stops flagging `app/db/models.py`.
- Do not change table names, column names, enum-like check-constraint values,
  unique-constraint names, index names, foreign-key targets, or `ondelete`
  behavior.
- Do not redesign semantic review workflows, governance-event lifecycle,
  graph-state semantics, concept/category relationships, or assertion / fact
  behavior.
- Do not weaken test, fixture, metadata, Alembic, or architecture gates.
- Do not mix non-semantic ORM families into this milestone.
- Do not move public enum definitions such as `SemanticGovernanceEventKind`,
  `SemanticTermKind`, `SemanticAssertionKind`, `SemanticCategoryBindingType`,
  or `SemanticEntityType` out of `app.db.models` as part of this milestone
  unless preserving exact current behavior requires it.

## Scope

In scope:

- `SemanticOntologySnapshot`
- `WorkspaceSemanticState`
- `SemanticGraphSnapshot`
- `WorkspaceSemanticGraphState`
- `SemanticConcept`
- `SemanticCategory`
- `SemanticTerm`
- `SemanticConceptTerm`
- `SemanticConceptCategoryBinding`
- `DocumentSemanticConceptReview`
- `DocumentSemanticCategoryReview`
- `DocumentRunSemanticPass`
- `SemanticAssertion`
- `SemanticAssertionCategoryBinding`
- `SemanticAssertionEvidence`
- `SemanticEntity`
- `SemanticFact`
- `SemanticFactEvidence`
- `SemanticGovernanceEvent`
- a new focused owner module under `app/db/model_domains/`
- `app.db.models` import-forwarding updates needed to preserve compatibility
- shared metadata contract expansion for semantic-memory tables
- Postgres `create_all(...)` and Alembic drift verification for the moved
  models
- routing-doc updates for the moved concern and the next remaining
  `IC-F2A8110185EB` follow-up

Out of scope:

- evidence, retrieval, agent-task, claim-support, or document-artifact rows
- `app.db.models` caller import rewrites away from the compatibility facade
- broad semantic-service refactors outside the ORM owner split

## Owner Surfaces

- hotspot facade:
  `app/db/models.py`
- new owner module:
  `app/db/model_domains/semantic_memory.py`
- compatibility and metadata harness:
  `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`
- migration / schema gates:
  `alembic/`,
  `uv run --extra dev alembic *`
- routing and current-state docs:
  this plan, `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`, and `docs/SESSION_HANDOFF.md`
- owner-case routing:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`

## Placement Rules

- Keep `app/db/models.py` as the public compatibility facade; do not update
  callers to import directly from the new domain module as part of this
  milestone.
- Put only the semantic-memory ORM family in the new owner module.
- Add shared contract constants for the semantic-memory tables in
  `tests/db_model_contract.py` instead of duplicating table / column
  expectations inside test bodies.
- Preserve exact index names, exact index column ordering, exact unique
  constraint names and column ordering, and the existing check-constraint
  value sets.
- Preserve relationship targets and nullable / `ondelete` semantics exactly; if
  a field is uncertain, verify from emitted Postgres metadata rather than ORM
  intuition.
- Keep public semantic enum definitions in `app.db.models` unless a precise
  compatibility reason requires a move.

## Weak-Point Prevention Contract

Weak point forecast:
This split could appear clean while silently weakening the schema harness,
dropping exact semantic-memory metadata checks, changing emitted DDL, or
simply relocating the last large ORM concern into a new dump file that should
have been split further before commit.

Owner surface:
`app/db/models.py`, the new `app/db/model_domains/semantic_memory.py`
module, the shared DB model contract tests, Alembic verification, and the
routing docs that define what counts as resolved for this milestone.

Prevention gate:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Fail threshold:

- any moved semantic-memory class remains fully implemented in
  `app/db/models.py`
- any public `app.db.models` import for the moved symbols breaks
- semantic-memory tables lack exact table-column, index-column, or exact
  unique-constraint coverage in the shared harness
- Alembic emits unexpected drift or `Base.metadata.create_all(...)` does not
  reproduce the expected schema in Postgres
- the new owner module is still broad enough that it should have been split
  again before commit

Controlled violation:

- temporarily remove one moved symbol from the `app.db.models` re-export path
  and verify the import-compatibility test fails
- temporarily change one expected semantic-memory index-column or
  unique-constraint entry and verify the Postgres metadata gate fails

Future-Codex misuse scenario:
The most likely bad follow-up is moving all remaining semantic-memory classes
into one file and calling the hotspot solved without first building the shared
contract gate, or without stopping when the new owner module is still too
large to be a clear owner surface. This milestone prevents that by making the
shared harness the first implementation step and by treating an oversized new
owner module as a stop condition rather than an acceptable shortcut.

## Milestone Sequence

### Milestone 0: Preflight Baseline Lock

Outcome label: `reduced`

Purpose:
Freeze the exact baseline and prove the repo is ready for a behavior-preserving
semantic-memory model-domain move before any ORM code changes begin.

Scope:

- refresh the current `app/db/models.py` hotspot measurements from live
  commands and record them in this plan or the handoff
- confirm the routed owner case, routed next-candidate docs, and current plan
  all agree on the semantic-memory family
- confirm local Postgres-backed verification is available for the full
  `Base.metadata.create_all(...)`, Alembic, and DB-backed pytest gates
- confirm that the missing dedicated semantic-memory metadata contract coverage
  is the first implementation step before ORM movement begins
- confirm no unrelated worktree state would prevent a narrow local milestone
  commit

Acceptance:

- the live metrics, routed owner case, and next-candidate docs agree and are
  recorded in durable docs
- the missing semantic-memory shared contract coverage is explicitly named as
  required implementation before the ORM move begins
- the repo is proven ready for DB-backed verification, not merely assumed ready

### Milestone 1: Shared Semantic-Memory Contract Gate

Outcome label: `reduced`

Purpose:
Create the dedicated semantic-memory compatibility and metadata gate before any
ORM class movement so schema drift and weakened coverage fail early.

Scope:

- add `SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS` in
  `tests/db_model_contract.py`
- add exact required semantic-memory index-name and index-column expectations
  for the moved tables
- add exact required semantic-memory unique-constraint names and column-order
  expectations where the semantic-memory tables use named unique constraints
- add dedicated ownership assertions in
  `tests/unit/test_db_model_import_compatibility.py`
- add dedicated Postgres metadata assertions in
  `tests/integration/test_db_model_metadata.py`

Acceptance:

- the semantic-memory family has dedicated shared table-column coverage
- exact index / unique-constraint contracts for semantic-memory tables are
  explicit in the shared harness instead of being implicit side effects of the
  global metadata checks
- the focused unit and Postgres metadata gates pass before code movement

### Milestone 2: Semantic-Memory Owner Split

Outcome label: `resolved`

Purpose:
Move the semantic-memory ORM concern into a focused owner module with exact
schema-contract preservation and public import compatibility intact.

Scope:

- add `app/db/model_domains/semantic_memory.py`
- move the full semantic-memory ORM family out of `app/db/models.py`
- re-export the moved symbols from `app.db.models`
- update `config/hygiene_policy.yaml` and `config/improvement_cases.yaml`
  with the post-split measurements
- refresh routing docs and the canonical handoff

Acceptance:

- `app/db/models.py` no longer contains full ORM implementations for the moved
  semantic-memory classes
- `app.db.models` stays import-compatible for all moved symbols
- the shared semantic-memory metadata harness and Postgres create-all gate pass
- the semantic-memory ORM concern itself is resolved inside the milestone
  scope even if the broader owner case remains open as a compatibility-facade
  hotspot

## Required Implementation Artifacts

- `app/db/model_domains/semantic_memory.py`
- `tests/db_model_contract.py` semantic-memory contract additions
- `tests/unit/test_db_model_import_compatibility.py` semantic-memory ownership
  assertions
- `tests/integration/test_db_model_metadata.py` semantic-memory Postgres
  contract assertions
- `config/hygiene_policy.yaml` ratchet update for `app/db/models.py` and the
  new owner module
- `config/improvement_cases.yaml` measurement and notes refresh for
  `IC-F2A8110185EB`

## Required Documentation And Handoff Updates

- update this plan with implementation results and verified metrics
- refresh `docs/data_model_boundary_plan.md`
- refresh `docs/agentic_architecture_index.md`
- refresh `docs/improvement_loop.md`
- refresh `docs/SESSION_HANDOFF.md`
- if the owner case remains open after the split, route the remaining issue by
  name instead of leaving the next step implicit

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

## Acceptance Criteria

- `tests/db_model_contract.py` exposes explicit semantic-memory table-column,
  exact index-column, and exact unique-constraint expectations
- `tests/unit/test_db_model_import_compatibility.py` proves the moved
  semantic-memory models are now owned by
  `app.db.model_domains.semantic_memory`
- `tests/integration/test_db_model_metadata.py` proves schema-scoped Postgres
  `Base.metadata.create_all(...)` preserves the semantic-memory contract
- `app/db/models.py` remains the public compatibility facade while the
  semantic-memory ORM concern itself is resolved for the milestone scope
- `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` reflect the
  post-split live measurements
- the closeout includes the implementation, tests, docs, governance artifacts,
  and canonical handoff update in one local atomic commit

## Stop Conditions

- stop if preserving exact semantic-memory schema semantics requires a migration
  or caller-facing contract change
- stop if DB-backed verification cannot run against local Postgres
- stop if the new semantic-memory owner module is still too broad to be a
  coherent owner surface; in that case, write narrower follow-on plans before
  committing code movement
- stop if the verified split cannot be isolated cleanly because unrelated dirty
  files are mixed into the same edit surface

## Local Commit Closeout Policy

- stage only the verified semantic-memory milestone slice
- include implementation, tests, routing docs, owner-case artifacts, and the
  canonical handoff update in the same atomic local commit
- do not close the milestone as complete until the local commit exists

## Residual Risks And Next Milestone Routing

- this is the last named ORM family still implemented directly inside
  `app/db/models.py`; after it moves, the broader owner case may still remain
  `reduced` if the compatibility facade itself stays a hotspot because of
  import fan-in, enum surface area, or residual facade breadth
- if the live architecture-quality report still flags `app/db/models.py` after
  closeout, the next routed follow-up should be a narrower
  compatibility-facade / public-import-contract milestone rather than another
  model-family split
- if the report no longer flags `app/db/models.py`, route the next milestone
  to the then-top open owner case from `config/improvement_cases.yaml`

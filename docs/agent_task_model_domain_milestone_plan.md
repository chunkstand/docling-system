# Agent Task Model-Domain Milestone Plan

Date: 2026-05-11 local
Status: verified locally on 2026-05-11; scoped issue resolved and broader
owner case reduced
Owner context: bounded follow-up under the open architecture-governance owner
case for `IC-F2A8110185EB` / `app/db/models.py`

## Purpose

Resolve the routed `agent tasks` ORM concern inside `app/db/models.py` by
moving the agent-task and knowledge-operator tables into a focused owner
module while preserving the public `app.db.models` import contract, the exact
Postgres schema contract, and current runtime behavior. This milestone closes
the agent-task owner slice itself; it does not claim to retire the broader
`IC-F2A8110185EB` hotspot unless the governing architecture-quality report no
longer flags `app/db/models.py`.

## Current Evidence

Live preflight signals refreshed before implementation:

```text
uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=660.8
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

wc -l app/db/models.py
  3570 app/db/models.py

uv run --extra dev alembic heads
  0076_claim_feedback_replay_src

uv run --extra dev alembic check
  No new upgrade operations detected.
```

Repo-current routing evidence before the move:

- `docs/evaluation_feedback_model_domain_milestone_plan.md` is fully closed
  and routes the next `app/db/models.py` concern back to the agent-task family.
- `docs/data_model_boundary_plan.md` names the next model-domain candidate as
  `agent tasks`:
  `AgentTask`,
  `AgentTaskDependency`,
  `AgentTaskAttempt`,
  `AgentTaskArtifact`,
  `AgentTaskArtifactImmutabilityEvent`,
  `AgentTaskOutcome`,
  `AgentTaskVerification`,
  `KnowledgeOperatorRun`,
  `KnowledgeOperatorInput`,
  `KnowledgeOperatorOutput`.
- `docs/SESSION_HANDOFF.md` routes `IC-F2A8110185EB` to the same family.
- `app/db/models.py` still owned all ten agent-task symbols before the move.
- `tests/db_model_contract.py` classified those symbols under the
  `agent_tasks` domain set but did not yet expose dedicated
  `AGENT_TASK_DOMAIN_TABLE_COLUMNS` coverage or exact required
  index/unique-constraint coverage for the agent-task and knowledge-operator
  tables.

## Goal

Move the routed agent-task ORM family into
`app/db/model_domains/agent_tasks.py` behind the existing `app.db.models`
compatibility facade, with stronger shared contract coverage than existed
before the move.

## Non-Goals

- Do not claim to retire the full `IC-F2A8110185EB` hotspot unless the live
  architecture-quality report stops flagging `app/db/models.py`.
- Do not change table names, column names, check-constraint value sets, named
  indexes, named unique constraints, foreign-key targets, or `ondelete`
  behavior.
- Do not redesign agent-task orchestration, approval flows, artifact handling,
  verification lifecycle, or operator telemetry behavior.
- Do not weaken test, fixture, lint, metadata, or Alembic gates to produce a
  green result.
- Do not mix semantic-memory, audit/evidence, or claim-support rows into this
  milestone.

## Scope

In scope:

- `AgentTask`
- `AgentTaskDependency`
- `AgentTaskAttempt`
- `AgentTaskArtifact`
- `AgentTaskArtifactImmutabilityEvent`
- `AgentTaskOutcome`
- `AgentTaskVerification`
- `KnowledgeOperatorRun`
- `KnowledgeOperatorInput`
- `KnowledgeOperatorOutput`
- a focused owner module under `app/db/model_domains/`
- `app.db.models` compatibility re-exports
- shared metadata contract expansion for agent-task tables
- Postgres `create_all(...)` and Alembic drift verification for the moved
  models
- routing-doc updates for the moved concern and the next remaining
  `IC-F2A8110185EB` follow-up

Out of scope:

- semantic-memory rows such as `SemanticOntologySnapshot`,
  `SemanticConcept`, `SemanticAssertion`, `SemanticEntity`, and
  `SemanticGovernanceEvent`
- audit/evidence rows such as `AuditBundleExport`, `EvidenceManifest`,
  `TechnicalReportReleaseReadinessDbGate`, `EvidenceTraceNode`,
  `EvidenceTraceEdge`, and `ClaimEvidenceDerivation`
- claim-support rows such as `ClaimSupportFixtureSet`,
  `ClaimSupportCalibrationPolicy`, `ClaimSupportEvaluation`, and related
  waiver/corpus tables

## Owner Surfaces

- hotspot facade: `app/db/models.py`
- new owner module: `app/db/model_domains/agent_tasks.py`
- compatibility and metadata harness:
  `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`
- migration / schema gates:
  `uv run --extra dev alembic *`
- routing and current-state docs:
  this plan, `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`, and `docs/SESSION_HANDOFF.md`
- owner-case routing:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`

## Placement Rules

- Keep `app/db/models.py` as the public compatibility facade; do not update
  callers to import directly from `app/db/model_domains/agent_tasks.py` as part
  of this milestone.
- Put only the agent-task and knowledge-operator ORM family in the new module.
- Keep `AgentTask*` and `KnowledgeOperator*` enums in `app/db/models.py`; the
  moved ORM module must not create a circular import just to preserve enum
  defaults.
- Add shared contract constants for the moved tables in
  `tests/db_model_contract.py` instead of duplicating expectations inside test
  bodies.
- Preserve exact index names, exact index column ordering, exact
  unique-constraint names and column ordering, and relationship targets.

## Weak-Point Prevention Contract

Weak point forecast:
This split could look clean while silently weakening the schema harness,
dropping exact index or unique-constraint checks for agent-task tables,
changing emitted DDL, or preserving imports only for a subset of the moved
symbols.

Owner surface:
`app/db/models.py`, `app/db/model_domains/agent_tasks.py`, the shared DB model
contract tests, Alembic verification, and the routing docs that define what
counts as resolved for this milestone.

Prevention gate:

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
- `git diff --check`

Fail threshold:

- any moved symbol remains defined as primary ORM code in `app/db/models.py`
- any public `app.db.models` import for the moved symbols breaks
- the moved tables lose exact column coverage, exact index coverage, or exact
  unique-constraint coverage in the shared harness
- Alembic emits unexpected drift or Postgres `Base.metadata.create_all(...)`
  no longer matches the supported schema shape

## Milestone Sequence

### Milestone 0: Preflight Baseline Lock

Outcome label: `reduced`

Completed locally on 2026-05-11:

- refreshed live routing, line-count, architecture-quality, and Alembic
  baseline signals before editing
- confirmed `docs/evaluation_feedback_model_domain_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`, and `docs/SESSION_HANDOFF.md` all routed
  the next owner slice to the agent-task family
- confirmed DB-backed verification was available and not silently skipped
- identified the missing shared agent-task metadata contract coverage as the
  required first implementation step

### Milestone 1: Agent-Task Contract And Owner Split

Outcome label: `resolved`

Completed locally on 2026-05-11:

- added `app/db/model_domains/agent_tasks.py`
- moved all ten routed agent-task / knowledge-operator ORM classes into the new
  owner module
- replaced the in-file ORM implementations in `app/db/models.py` with
  compatibility re-exports so public imports remain unchanged
- expanded `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` with dedicated agent-task table
  columns, exact index-column ordering, and exact unique-constraint column
  ordering coverage
- reduced `app/db/models.py` from 3,570 lines to 3,090 while keeping the new
  owner module at 515 lines

### Milestone 2: Closeout And Next Routing

Outcome label: `reduced`

Closeout evidence refreshed locally on 2026-05-11:

- `uv run docling-system-architecture-quality-report --summary` now reports
  `max_hotspot_risk_score=642.6` with `app/db/models.py` still first in
  `top_hotspot_paths`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
  now reports `app/db/models.py` at 3,090 lines with hotspot score `234840`
- the broader `IC-F2A8110185EB` owner case remains `reduced`, not `resolved`,
  because `app/db/models.py` is still in the governed hotspot list
- the next remaining routed candidate is the `audit and evidence` family:
  `AuditBundleExport`,
  `AuditBundleValidationReceipt`,
  `EvidenceManifest`,
  `TechnicalReportReleaseReadinessDbGate`,
  `TechnicalReportClaimRetrievalFeedback`,
  `EvidenceTraceNode`,
  `EvidenceTraceEdge`,
  `ClaimEvidenceDerivation`

## Required Implementation Artifacts

- `app/db/model_domains/agent_tasks.py`
- `app/db/models.py` re-export updates
- `tests/db_model_contract.py` agent-task contract additions
- `tests/unit/test_db_model_import_compatibility.py` ownership assertions for
  the moved symbols
- `tests/integration/test_db_model_metadata.py` Postgres metadata coverage for
  the moved tables

## Required Documentation And Handoff Updates

- this milestone plan
- `docs/data_model_boundary_plan.md`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`

## Required Verification Gates

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
uv run docling-system-improvement-case-validate
uv run docling-system-improvement-case-summary
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
git status --short
git diff --stat
git diff --cached --stat
```

## Acceptance Criteria

- Outcome label: `resolved` for the milestone scope. The moved agent-task and
  knowledge-operator ORM classes are owned by
  `app/db/model_domains/agent_tasks.py`, and `app/db/models.py` keeps only
  compatibility re-exports for those symbols.
- Outcome label: `reduced` for the broader owner case unless the live
  architecture-quality report no longer lists `app/db/models.py` as a hotspot.
- Shared contract coverage exists for agent-task table columns, exact required
  index columns, and exact required unique-constraint columns.
- Postgres `create_all(...)`, Alembic, and full DB-backed pytest gates remain
  green without loosening prior coverage.

## Stop Conditions

- Stop if preserving exact agent-task schema semantics requires a schema
  redesign or migration beyond a behavior-preserving owner split.
- Stop if the only path to green is weakening tests, loosening metadata
  expectations, or dropping exact index/unique checks.

## Residual Risks And Next Milestone Routing

- `app/db/models.py` remains the top governed hotspot even after the agent-task
  split, so the broader owner case is still open.
- The routed next bounded candidate should start with the remaining
  `audit and evidence` family rather than reopening the already-moved
  agent-task symbols.

## Closeout Checklist

- [x] Refresh live baseline and routed owner-case signals
- [x] Add dedicated agent-task metadata contract coverage before the move
- [x] Move the routed agent-task ORM family into a focused owner module
- [x] Preserve `app.db.models` import compatibility
- [x] Prove Postgres `create_all(...)` and Alembic drift remain clean
- [x] Refresh routing docs and the session handoff from live measurements

# Agentic Architecture Milestone Audit

Date: 2026-05-04
Status refreshed: 2026-05-09

Scope: audit the implemented architecture milestones against
`docs/agentic_architecture_milestone_plan.md` and close concrete gaps that can
be verified mechanically without changing public API, database schema, or
runtime behavior.

## Current Gate Snapshot

- `uv run docling-system-architecture-inspect`: valid with `violation_count=0`,
  `api_route_count=130`, `agent_action_count=51`, `contract_count=10`, and
  `inspection_rule_count=13`.
- `uv run docling-system-capability-contracts`: valid with `facade_count=6`,
  `function_count=110`, and no issues.
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=687.04`, and top hotspot paths
  headed by `app/db/models.py`, `app/services/evidence.py`, `app/cli.py`,
  `app/services/agent_task_actions.py`, and `tests/unit/test_cli.py`.
- `uv run ruff check app tests`: passed.
- Focused architecture tests:
  `tests/unit/test_architecture_inspection.py`,
  `tests/unit/test_architecture_quality.py`,
  `tests/unit/test_capability_contracts.py`, and
  `tests/unit/test_api_route_contracts.py` passed with `34 passed`.
- DB-backed model verification is current for `Architecture Plan 01`
  Milestone 2: `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
  passed with `1105 passed`, and the focused Postgres metadata/create-all gate
  now passes with `7 passed`.
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene` is
  current and reports `observation_count=0`.
- `uv run docling-system-evaluation-data-readiness` is current but still
  reports `regression_ready=false`, `court_grade_ready=false`, and
  `failed_gate_count=11` because the local DB has no active corpus.

## Gap Closures

- Milestone 0 now scores agent legibility against tests, examples, trace or
  replay commands, and linked architecture decision rationale, not only surface
  size and ownership.
- Milestone 1 now exposes narrower contract companions for retrieval search,
  evidence, chat/feedback, replay, harness, audit, and learning while
  preserving the `retrieval` compatibility facade.
- Milestone 1 now exposes narrower contract companions for agent task
  lifecycle, context/artifacts/evidence, approval/verification, analytics, and
  actions while preserving the `agent_orchestration` compatibility facade.
- Milestone 3 now validates stale context-builder names inside the action
  manifest validator, not only in a side test.
- Milestone 4 now samples search replay regressions directly in the trace
  review report and routes them through the improvement-case source vocabulary.
- Milestone 6 now emits improvement-case candidates for broad or low-legibility
  capability facades as well as file hotspots.
- Milestone 5 now has a compact architecture index that links milestone
  status, commands, generated maps, review surfaces, known debt, and this audit.
- `Architecture Plan 01` Milestone 2 now has the first physical data-model
  domain split: `ApiIdempotencyKey` moved into
  `app/db/model_domains/platform.py` while `app.db.models` remains an
  import-compatible facade.
- The model compatibility harness now verifies platform-support index and
  unique-constraint column ordering in both unit metadata and Postgres
  `Base.metadata.create_all(...)` paths.

## Deferred Large Refactors

The plan's physical implementation splits remain governed hotspot work, not
hidden gaps. The first `app/db/models.py` domain split is complete; additional
model domains should still move one at a time. The next active hotspot split is
`Architecture Plan 01` Milestone 3 for search evidence package helpers in
`app/services/evidence.py`. Later governed split surfaces include
`app/services/agent_task_actions.py`, `app/services/search.py`, and
`app/cli.py`. Each future split should land as a separate
behavior-preserving milestone with focused tests plus the full integration
gate.

## Verification Contract

Before landing this audit slice, run:

- `uv run ruff check app tests`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-decisions`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

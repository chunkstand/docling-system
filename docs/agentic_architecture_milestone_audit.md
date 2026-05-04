# Agentic Architecture Milestone Audit

Date: 2026-05-04

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
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`, and top
  hotspot paths headed by `app/db/models.py` and `app/services/evidence.py`.

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

## Deferred Large Refactors

The plan's physical implementation splits for `app/services/evidence.py`,
`app/services/agent_task_actions.py`, `app/services/search.py`, and
`app/db/models.py` remain governed hotspot work, not hidden gaps. They are
ranked and converted into improvement-case candidates by the architecture
quality report. Each future split should land as a separate behavior-preserving
milestone with focused tests plus the full integration gate.

## Verification Contract

Before landing this audit slice, run:

- `uv run ruff check app tests`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-decisions`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

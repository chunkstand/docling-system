# Agentic Architecture Index

This is the compact map for architecture work. Use it before reading broad
chat history or scanning the whole repository.

## Current Milestone Briefs

- `docs/architecture_plan_01.md`: active hotspot reduction plan and milestone sequence.
- `docs/agentic_architecture_milestone_plan.md`: expert-panel plan and milestone sequence.
- `docs/agentic_architecture_milestone_audit.md`: latest implementation audit and gap closures.
- `docs/data_model_boundary_plan.md`: model-domain split plan and DB verification gates.
- `docs/SESSION_HANDOFF.md`: latest broad system handoff.

## Milestone Status

- Completed through `9f60a17`: baseline quality report, capability subcontracts, agent action
  hardening, trace-first review, repository architecture map, architecture
  garbage-collection candidates, and data-model boundary plan.
- Current gate shape: architecture inspection is valid with no violations,
  capability contracts are valid across 6 facades and 110 functions, and the
  architecture quality summary reports `agent_legibility_average_score=90.0`,
  `broad_facade_count=2`, and `hotspot_count=10`.
- Governed follow-up: physical hotspot splits for `app/services/evidence.py`,
  `app/services/agent_task_actions.py`, `app/services/search.py`,
  `app/cli.py`, and `app/db/models.py`. Use the architecture quality report to
  choose one split at a time. `docs/architecture_plan_01.md` is the active
  execution order for those splits.
- Runtime caveat: DB-backed readiness and trace review require a working local
  Postgres/Docker runtime; the 2026-05-09 docs refresh could not verify those
  paths because local Postgres and Docker were unavailable.

## Executable Architecture Contracts

- `docs/architecture_boundaries.md`: human-readable boundary policy.
- `docs/architecture_decisions.yaml`: accepted architecture decisions.
- `docs/architecture_contract_map.json`: generated architecture map.
- `docs/capability_contract_map.json`: generated service capability map.
- `config/architecture_inspection.yaml`: architecture inspection severity policy.

## Agent-Facing Commands

- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report`
- `uv run docling-system-agent-task-action-index`
- `uv run docling-system-agent-trace-review`
- `uv run docling-system-improvement-case-import --source architecture-quality-report --source-path build/architecture-governance/architecture_quality_report.json --dry-run`
- `uv run docling-system-improvement-case-import --source agent-trace-review-report --source-path build/architecture-governance/agent_trace_review_report.json --dry-run`

## Review Surfaces

- Capability facades: `app/services/capabilities/`
- Agent action catalog: `app/services/agent_task_actions.py` and `app/services/agent_actions/`
- Architecture inspection: `app/architecture_inspection.py`, `app/architecture_inspection_rules.py`
- Architecture quality report: `app/architecture_quality.py`
- Trace review report: `app/agent_trace_review.py`
- Improvement intake: `app/services/improvement_case_intake.py`

## Known Debt Signals

- Top hotspot report:
  `uv run docling-system-architecture-quality-report --summary`
- Improvement-case candidates:
  `uv run docling-system-improvement-case-import --source architecture-quality-report --source-path build/architecture-governance/architecture_quality_report.json --dry-run`
- DB-backed trace findings:
  `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`

## Operating Rule

When a repeated failure appears, encode it as a test, contract-map field,
architecture rule, generated report, or improvement-case observation. Do not
leave durable architecture knowledge only in chat.

# Agentic Architecture Index

This is the compact map for architecture work. Use it before reading broad
chat history or scanning the whole repository.

## Current Milestone Briefs

- `docs/residual_weakness_resolution_milestone_plan.md`: follow-on sequence for hotspot prevention, hygiene ratchets, remaining hotspot splits, agent-task cycle reduction, and evaluation-data readiness; Milestones 1-6 are complete.
- `docs/architecture_plan_01.md`: completed hotspot reduction and improvement-intake sequence.
- `docs/hotspot_prevention_gate_milestone_plan.md`: implemented gate to block new implementation growth in known hotspot files before more split work.
- `docs/agentic_architecture_milestone_plan.md`: expert-panel plan and milestone sequence.
- `docs/agentic_architecture_milestone_audit.md`: latest implementation audit and gap closures.
- `docs/data_model_boundary_plan.md`: model-domain split plan and DB verification gates.
- `docs/SESSION_HANDOFF.md`: latest broad system handoff.

## Milestone Status

- Completed through the local `Architecture Plan 01` Milestone 8
  improvement-intake closeout:
  baseline quality report, capability subcontracts, agent action hardening,
  trace-first review, repository architecture map, architecture
  garbage-collection candidates, data-model boundary plan, and
  `Architecture Plan 01` Milestones 0-8.
- Current gate shape: architecture inspection is valid with no violations,
  capability contracts are valid across 6 facades and 110 functions, and the
  architecture quality summary reports `agent_legibility_average_score=90.0`,
  `broad_facade_count=2`, `hotspot_count=10`, and
  `max_hotspot_risk_score=692.67`.
- `app/db/models.py` remains the top hotspot, but two model domains are now
  split: `ApiIdempotencyKey` lives in `app/db/model_domains/platform.py`, and
  `IngestBatch`, `IngestBatchItem`, `Document`, and `DocumentRun` live in
  `app/db/model_domains/ingest.py` while `app.db.models` remains the public
  compatibility facade.
- The first `app/services/evidence.py` split is complete: search evidence
  package assembly/export/trace helpers now live in
  `app/services/evidence_search_packages.py`,
  `app/services/evidence_search_trace_graph.py`, and
  `app/services/evidence_search_trace_store.py`.
- The second `app/services/evidence.py` split is complete: technical-report
  PROV export relation helpers, immutable freeze payloads, hash-chain receipts,
  signing, and receipt integrity now live in
  `app/services/evidence_provenance.py`. The alignment closeout proves the
  compatibility facade covers every moved identity alias, constant, and
  settings-aware wrapper.
- The third `app/services/evidence.py` split is complete: knowledge-operator
  run recording now lives in `app/services/evidence_operator_runs.py`;
  task/artifact/verification/operator summary payload helpers now live in
  `app/services/evidence_task_payloads.py`; search and retrieval-span code
  import the focused operator-run owner directly; and `app.services.evidence`
  still re-exports `record_knowledge_operator_run`.
- The first `app/services/agent_task_actions.py` registry split is complete:
  search-harness action contract metadata and helper logic now live in
  `app/services/agent_actions/search_harness.py` while
  `app.services.agent_task_actions` remains the compatibility facade and
  execution entrypoint.
- The Residual Weakness Plan Milestone 5 cycle break is complete:
  `app/services/agent_task_action_lookup.py` is the narrow lookup seam for
  context and task services, while executor implementations still live in
  `app.services.agent_task_actions`. The general architecture probe no longer
  reports the large agent-task import-cycle component. Fan-out remains 39 for
  `app.services.agent_task_actions`, which is documented as the
  action-orchestration entrypoint rather than a context/task dependency.
- The first `app/cli.py` command-group split is complete:
  improvement-case validate/list/summary/record implementations now live in
  `app/cli_commands/improvement_cases.py` while `app.cli` remains the console
  script compatibility surface through explicit forwarding functions.
- The second `app/cli.py` command-group split is complete: ingest file, ingest
  directory, and ingest-batch inspection implementations now live in
  `app/cli_commands/ingest.py`; `pyproject.toml` console scripts still resolve
  through `app.cli`, and ingest tests now live in
  `tests/unit/test_cli_ingest.py`.
- The first `app/services/search.py` core split is complete: query-intent,
  tabular-query, identifier lookup, normalized query feature set, token/phrase
  coverage, and metadata-query token helpers now live in
  `app/services/search_query_features.py` while `app.services.search` remains
  the compatibility facade for existing query helper imports.
- The Milestone 8 improvement-intake ratchet is complete: 22
  architecture-quality candidates are imported as open improvement cases with
  structured owner surfaces, verification commands, and stop conditions.
- Governed follow-up: the residual weakness sequence is now active in
  `docs/residual_weakness_resolution_milestone_plan.md`. Its first
  implementation milestone, the hotspot-prevention gate in
  `docs/hotspot_prevention_gate_milestone_plan.md`, is complete. The second
  implementation milestone, the strict hygiene ratchet, is also complete:
  `docling-system-hygiene-check` now separates inherited budget debt from
  blocking new hygiene regressions. The third implementation milestone, Top
  Hotspot Split Pack A, is complete. The fourth implementation milestone, Top
  Hotspot Split Pack B, is complete for the evidence operator-run and
  task-payload summary concerns. The fifth implementation milestone, the
  Agent-Task Cycle Break, is complete. The sixth implementation milestone,
  Regression Evaluation-Data Readiness, is complete. The next milestone is
  Court-Grade Evaluation-Data Readiness.
- Runtime note: local Docker/Postgres is available for DB-backed milestone
  verification. Evaluation-data readiness now reports
  `regression_ready=true`, `court_grade_ready=false`, and
  `failed_gate_count=7` on the rebuilt local DB. Remaining blockers are the
  court-grade data lanes, not the regression tier.

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
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-agent-task-action-index`
- `uv run docling-system-agent-trace-review`
- `uv run docling-system-improvement-case-import --source architecture-quality-report --source-path build/architecture-governance/architecture_quality_report.json --dry-run`
- `uv run docling-system-improvement-case-import --source agent-trace-review-report --source-path build/architecture-governance/agent_trace_review_report.json --dry-run`

## Review Surfaces

- Capability facades: `app/services/capabilities/`
- Agent action catalog: `app/services/agent_task_actions.py`,
  `app/services/agent_task_action_lookup.py`, and `app/services/agent_actions/`
- Architecture inspection: `app/architecture_inspection.py`, `app/architecture_inspection_rules.py`
- Architecture quality report: `app/architecture_quality.py`
- Hotspot prevention: `config/hotspot_prevention.yaml`, `app/hotspot_prevention.py`, and `docs/hotspot_prevention_gate_milestone_plan.md`
- Hygiene ratchet: `config/hygiene_policy.yaml`, `app/hygiene.py`,
  `app/hygiene_ruff.py`, and `app/hygiene_types.py`
- Residual weakness sequence: `docs/residual_weakness_resolution_milestone_plan.md`
- Trace review report: `app/agent_trace_review.py`
- Improvement intake: `app/services/improvement_case_intake.py`
- Data model domains: `app/db/model_domains/`
- Search evidence packages: `app/services/evidence_search_*.py`
- Evidence provenance: `app/services/evidence_provenance.py`
- Search-harness action family: `app/services/agent_actions/search_harness.py`
- CLI command groups: `app/cli.py` and `app/cli_commands/`
- Search query features: `app/services/search_query_features.py`

## Known Debt Signals

- Top hotspot report:
  `uv run docling-system-architecture-quality-report --summary`
- Improvement-case candidates:
  `uv run docling-system-improvement-case-import --source architecture-quality-report --source-path build/architecture-governance/architecture_quality_report.json --dry-run`
- Improvement-case registry:
  `uv run docling-system-improvement-case-summary`
- DB-backed trace findings:
  `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- General import-cycle probe:
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown`

## Operating Rule

When a repeated failure appears, encode it as a test, contract-map field,
architecture rule, generated report, or improvement-case observation. Do not
leave durable architecture knowledge only in chat.

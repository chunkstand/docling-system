# Agentic Architecture Index

This is the compact map for architecture work. Use it before reading broad
chat history or scanning the whole repository.

## Current Milestone Briefs

- `docs/residual_weakness_resolution_milestone_plan.md`: follow-on sequence for hotspot prevention, hygiene ratchets, remaining hotspot splits, agent-task cycle reduction, and evaluation-data readiness; complete through Milestone 8.
- `docs/hotspot_owner_resolution_plan.md`: completed owner-scoped hotspot sequence through local Milestone 6; active execution has moved to the high-value paydown plan.
- `docs/high_value_technical_paydown_milestone_plan.md`: active follow-on paydown program for the next owner-scoped model split, further evidence and agent-action splits, hotspot test decomposition, and the routed UI monolith split.
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
  `max_hotspot_risk_score=673.78`.
- `app/db/models.py` remains the top hotspot, but four model domains are now
  split: `ApiIdempotencyKey` lives in `app/db/model_domains/platform.py`,
  `IngestBatch`, `IngestBatchItem`, `Document`, and `DocumentRun` live in
  `app/db/model_domains/ingest.py`, and `DocumentRunEvaluation`,
  `DocumentRunEvaluationQuery`, `DocumentChunk`, `DocumentTable`,
  `DocumentTableSegment`, and `DocumentFigure` now live in
  `app/db/model_domains/document_artifacts.py`. The retrieval-interaction
  ledger now lives in `app/db/model_domains/retrieval_interactions.py`, while
  `app.db.models` remains the public compatibility facade at 5,067 lines.
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
- The fourth `app/services/evidence.py` split is verified locally: the
  technical-report derivation package, provenance-lock assembly, export
  persistence, attach helpers, and claim-derivation payload helpers now live
  in `app/services/evidence_technical_report_exports.py`, while
  `app.services.evidence` remains the compatibility facade.
- The first `app/services/agent_task_actions.py` registry split is complete:
  search-harness action contract metadata and helper logic now live in
  `app/services/agent_actions/search_harness.py` while
  `app.services.agent_task_actions` remains the compatibility facade and
  execution entrypoint.
- The Residual Weakness Plan Milestone 5 cycle break is complete:
  `app/services/agent_task_action_lookup.py` is the narrow lookup seam for
  context and task services, while executor implementations still live in
  `app.services.agent_task_actions`. The general architecture probe no longer
  reports the large agent-task import-cycle component. Fan-out is now 36 for
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
- The Milestone 8 improvement-intake ratchet remains intact, and Hotspot Owner
  Resolution Milestone 0 is now complete locally: at the Milestone 0 closeout
  checkpoint, the registry reported `case_count=25`,
  `status_counts.open=24`, `status_counts.measured=1`, and
  `measured_case_count=2`, including explicit owner-bootstrap cases
  `IC-2112B1ADC5E8` for `app/services/audit_bundles.py` and
  `IC-0D58F1624037` for `app/services/retrieval_learning.py`. The milestone is
  closed by commit `33c7855`.
- Hotspot Owner Resolution Milestone 1 is now complete locally: the
  `document_artifacts` ORM domain lives in
  `app/db/model_domains/document_artifacts.py`, `app.db.models` re-exports the
  moved classes, and `app/db/models.py` is reduced to 5,537 lines with the
  hygiene ratchet updated to match. The milestone is closed by commit
  `060b537`.
- Hotspot Owner Resolution Milestone 2 is now complete locally: the
  technical-report evidence trace concern lives in
  `app/services/evidence_manifest_traces.py`, retrieval training replay-alert
  corpus lineage lives in
  `app/services/audit_bundle_replay_alert_corpus.py`, `app/services/evidence.py`
  is reduced to 7,143 lines, and `app/services/audit_bundles.py` is reduced to
  3,306 lines while both facades keep their existing entry surfaces. The
  milestone is closed by commit `a0bd36b`.
- Hotspot Owner Resolution Milestone 3 is now complete locally: replay-alert
  fixture coverage summary, candidate derivation, promotion receipts, and
  waiver-closure governance now live in
  `app/services/claim_support_replay_alert_promotions.py` while
  `app/services/claim_support_policy_impacts.py` remains the compatibility
  facade. The old hotspot is reduced to 2,011 lines, and the new owner module
  is governed under the same improvement case `IC-E2270F89B397` with a 1,536
  line ratchet. The milestone is closed by commit `afc324a`.
- Hotspot Owner Resolution Milestone 4 is now complete locally: replay-alert
  corpus lineage validation, judgment materialization, and hard-negative
  construction now live in
  `app/services/retrieval_learning_replay_alert_sources.py` while
  `app/services/retrieval_learning.py` remains the compatibility facade. The
  old hotspot is reduced to 2,482 lines, and the new owner module is governed
  under the same improvement case `IC-0D58F1624037` with a 578 line hygiene
  budget. The milestone is closed by commit `13e8b1c`.
- Hotspot Owner Resolution Milestone 5 is now complete locally: ranking
  helpers, reranking, hybrid-result merging, result rendering, and ranked
  result utility types now live in `app/services/search_ranking.py` while
  `app/services/search.py` remains the compatibility facade. The old hotspot
  is reduced to 2,851 lines, and the new owner module is governed under the
  same improvement case `IC-1D03DBFE8492` with a 467 line hygiene budget. The
  milestone is closed by commit `c871dd9`.
- Hotspot Owner Resolution Milestone 6 is now complete locally: the owner-case
  registry, hotspot plan, architecture index, and session handoff are aligned
  to the committed Milestones 1-5 reductions, explicit owner routing is
  confirmed for all six targeted surfaces, and at that closeout checkpoint the
  next route returned to the top remaining owner case `IC-F2A8110185EB` /
  `app/db/models.py`. The milestone is closed by commit `76526ef`.
- High Value Technical Paydown Milestone 0 is now committed locally: the plan
  is active, the UI milestone gate now points to `tests/unit/test_ui.py`,
  `config/improvement_cases.yaml` contains explicit UI owner case
  `IC-1B643BA0AD90` for `app/ui/app.js`, and the docs now record that this
  hotspot is governed through the improvement-case registry plus architecture
  probe rather than the Python-only hygiene ratchet.
- High Value Technical Paydown Milestone 1 is now committed locally: the
  retrieval-interaction ORM owner module lives in
  `app/db/model_domains/retrieval_interactions.py`, `app/db/models.py` is
  reduced from 5,537 lines to 5,067 lines, the shared metadata harness now
  protects retrieval-interaction table/index/vector/computed-column contracts,
  and the hotspot-prevention gate stays green through import-forwarder aliases.
- High Value Technical Paydown Milestone 2 is now committed locally: the
  technical-report derivation/export owner family lives in
  `app/services/evidence_technical_report_exports.py`,
  `app/services/evidence.py` is reduced from 7,143 to 6,307 architecture-probe
  lines, the focused technical-report DB-backed integration remains green, and
  the new owner module is governed at an 884-line ratchet.
- High Value Technical Paydown Milestone 3 is now committed locally: the
  technical-report action definition family lives in
  `app/services/agent_actions/report_actions.py`,
  `app/services/agent_task_actions.py` is reduced from 2,884 to 2,746
  architecture-probe lines, hotspot score falls from 170156 to 162014, and
  fan-out drops from 39 to 36 while the lookup seam stays unchanged.
- High Value Technical Paydown Milestone 4 is now committed locally: the CLI,
  search API, and document API hotspot tests are split into focused owner files
  (`tests/unit/test_cli_agent_tasks.py`,
  `tests/unit/test_cli_agent_task_analytics.py`,
  `tests/unit/test_cli_claim_support.py`,
  `tests/unit/test_cli_improvement_cases.py`,
  `tests/unit/test_cli_search_harness.py`,
  `tests/unit/test_search_api_replays.py`,
  `tests/unit/test_search_api_harnesses.py`,
  `tests/unit/test_search_api_learning_audit.py`,
  `tests/unit/test_documents_api_artifacts.py`, and
  `tests/unit/test_documents_api_semantics.py`) while the original monoliths
  are reduced to 424, 436, and 613 lines respectively and no longer appear in
  the current architecture-quality top-hotspot list.
- High Value Technical Paydown Milestone 6 is now verified locally: the
  shipped operator UI no longer depends on one 4,335-line JavaScript file.
  `app/ui/app.js` is reduced to a 107-line bootstrap, the shared runtime and
  page-family logic now live under `app/ui/modules/`, and
  `tests/unit/test_ui_static_assets.py` covers module asset inclusion and
  serving alongside `tests/unit/test_ui.py`.
- High Value Technical Paydown Milestone 7 is now verified locally: the
  paydown closeout docs, improvement-case deployment refs, readiness metrics,
  agent-trace review, and full DB-backed suite are aligned to live artifacts
  instead of the pre-closeout Milestone 6 snapshot.
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
  Regression Evaluation-Data Readiness, is complete. The seventh
  implementation milestone, Court-Grade Evaluation-Data Readiness, is complete.
  The eighth implementation milestone, Residual Weakness Closeout, is also
  complete. Follow-up work now routes through owner-scoped improvement cases
  and hotspot owners rather than another open milestone in this sequence.
- Runtime note: local Docker/Postgres is available for DB-backed milestone
  verification. Evaluation-data readiness now reports
  `regression_ready=true`, `court_grade_ready=true`, and
  `failed_gate_count=0` on the rebuilt local DB. The live DB now includes the
  reviewed five-document manual corpus, full replay/harness source coverage,
  operator feedback coverage, technical-report claim-feedback coverage, an
  active claim-support replay-alert corpus snapshot, and materialized
  retrieval-learning data.
- Residual risk note: the improvement-case registry remains the durable map for
  remaining architecture debt. Current summary:
  `case_count=26`, `status_counts.open=25`, `status_counts.measured=1`, and
  `measured_case_count=14`, with open cases concentrated in
  architecture-governance ownership rather than untracked or milestone-owned
  debt.
- Current routed follow-up: the next architecture work should use
  `docs/data_model_boundary_plan.md`; the high-value paydown plan is complete
  locally through Milestone 7, and the next routed implementation slice has
  returned to `IC-F2A8110185EB` / `app/db/models.py` with the retrieval replay
  and release governance model-domain candidate.

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

# Agentic Architecture Index

This is the compact map for architecture work. Use it before reading broad
chat history or scanning the whole repository.

## Current Milestone Briefs

- `docs/residual_weakness_resolution_milestone_plan.md`: follow-on sequence for hotspot prevention, hygiene ratchets, remaining hotspot splits, agent-task cycle reduction, and evaluation-data readiness; complete through Milestone 8.
- `docs/hotspot_owner_resolution_plan.md`: completed owner-scoped hotspot sequence through local Milestone 6; active execution has moved to the high-value paydown plan.
- `docs/high_value_technical_paydown_milestone_plan.md`: completed local paydown program covering the next owner-scoped model splits, further evidence and agent-action splits, hotspot test decomposition, and the routed UI monolith split.
- `docs/evaluation_feedback_model_domain_milestone_plan.md`: completed bounded milestone record for the `IC-F2A8110185EB` evaluation-feedback split covering `EvalObservation` and `EvalFailureCase`; Milestone 2 closeout is committed locally as `b69c4f6`, and the broader owner case remains reduced.
- `docs/agent_task_model_domain_milestone_plan.md`: completed bounded milestone record for the `IC-F2A8110185EB` agent-task split covering the agent-task and knowledge-operator ORM family; Milestone 2 closeout is committed locally as `e59f9bf`, and the broader owner case remains reduced while `app/db/models.py` stays in the hotspot list.
- `docs/audit_and_evidence_model_domain_milestone_plan.md`: completed bounded milestone record for the `IC-F2A8110185EB` audit-and-evidence split covering the audit bundle, evidence package, manifest, trace, and technical-report readiness/feedback ORM family; the broader owner case remains reduced while `app/db/models.py` stays in the hotspot list.
- `docs/claim_support_model_domain_milestone_plan.md`: completed bounded milestone record for the `IC-F2A8110185EB` claim-support split covering the replay-alert waiver, fixture-corpus, calibration, evaluation, and policy-impact ORM family; the broader owner case remains reduced while `app/db/models.py` stays in the hotspot list.
- `docs/semantic_memory_model_domain_milestone_plan.md`: completed local verified milestone record for the `IC-F2A8110185EB` semantic-memory split covering the ontology, graph-state, concept, assertion, entity, fact, semantic review, and governance ORM family; the broader owner case remains reduced while `app/db/models.py` stays in the architecture-quality routing list.
- `docs/db_models_compatibility_facade_milestone_plan.md`: completed local verified milestone brief for the `IC-F2A8110185EB` compatibility-facade / public-import-contract follow-up. Milestone 2 closes the remaining unclear-ownership gap for `app/db/models.py`; the next routed owner case is `IC-050E60059A34` / `app/services/evidence.py`.
- `docs/evidence_hotspot_owner_milestone_plan.md`: implemented locally through the evidence facade-resolution closeout for `IC-050E60059A34`; `app/services/evidence.py` is reduced to a 141-line compatibility facade, closeout commit `3fe9132` is now recorded in the registry, and follow-on case `IC-65AF4A6D8B1E` governs the oversized evidence owner-family modules.
- `docs/agent_task_orchestration_boundary_milestone_plan.md`: resolved locally through Milestone 5 closeout commit `7cf7465` for `IC-A1E186A34097` / `app/services/agent_task_actions.py` and `IC-E52B6C7B22FD` / `app/services/agent_task_context.py`; the next routed hotspot is `IC-1D03DBFE8492` / `app/services/search.py`.
- `docs/search_execution_persistence_boundary_milestone_plan.md`: resolved locally through Milestone 1 closeout commit `f55b474` for `IC-1D03DBFE8492`; search execution persistence and operator-trace payload assembly now live in `app/services/search_execution_persistence.py`, `app/services/search.py` is reduced to 2089 lines / 37 private helpers, and the next routed follow-on is the remaining execution-orchestration cluster in `execute_search(...)` and adjacent candidate-loading/detail assembly paths.
- `docs/search_execution_orchestration_boundary_milestone_plan.md`: resolved locally through Milestone 1 closeout commit `dae5e4f` for `IC-1D03DBFE8492`; search execution orchestration now lives in `app/services/search_execution_orchestration.py`, `app/services/search.py` is reduced to 1592 lines / 32 private helpers, and the broader owner case remains reduced because the architecture probe still routes the facade.
- `docs/claim_support_policy_impacts_boundary_milestone_plan.md`: resolved locally through Milestone 4 closeout commit `3d7d090` for `IC-E2270F89B397`; `app/services/claim_support_policy_impacts.py` is now a 184-line compatibility facade, the read-model and alert owner now lives in `app/services/claim_support_policy_impact_views.py` at 899 lines / 16 private helpers, the replay-lifecycle owner now lives in `app/services/claim_support_policy_impact_replay.py` at 898 lines / 11 private helpers, and the broader owner case remains reduced because the extracted owners still exceed the default 600-line budget.
- `docs/evaluations_service_boundary_milestone_plan.md`: resolved locally through Milestone 4 closeout commit `1159297` for `IC-BF180637814C`; `app/services/evaluations.py` is now a `283` line / `1` private-helper orchestration and compatibility facade, fixture and corpus ownership remains in `app/services/evaluation_fixtures.py` at `966` lines / `32` private helpers, scoring and structural ownership remains in `app/services/evaluation_scoring.py` at `897` lines / `25` private helpers, latest-evaluation summary/detail reads now live in `app/services/evaluation_reads.py` at `154` lines / `1` private helper, and the architecture probe no longer lists the evaluations facade among the top 15 churn hotspots.
- `docs/evidence_provenance_exports_boundary_milestone_plan.md`: resolved locally through closeout commit `1aa8378` on 2026-05-13 for the scoped provenance-export knot under `IC-65AF4A6D8B1E`; `app/services/evidence_provenance_exports.py` is now a 14-line compatibility facade, graph assembly now lives in `app/services/evidence_provenance_export_graph_core.py` at 549 lines, report-trace and claim-lineage graph ownership now lives in `app/services/evidence_provenance_export_graph_report.py` at 218 lines, lifecycle and persistence now live in `app/services/evidence_provenance_export_lifecycle.py` at 278 lines, and the broader owner case remains reduced because `app/services/evidence_technical_report_exports.py`, `app/services/evidence_semantic_trace.py`, `app/services/evidence_claim_feedback.py`, and `app/services/evidence_audit_views.py` still exceed the default 600-line budget.
- `docs/semantics_service_boundary_milestone_plan.md`: resolved locally through closeout commit `a2eb27e` on 2026-05-13 local / 2026-05-14 UTC for `IC-9E6B8F5D62A1`; `app/services/semantics.py` is now a 54-line / 0-private-helper compatibility facade, lifecycle ownership now lives in `app/services/semantic_pass_lifecycle.py` at 961 lines / 10 private helpers, read ownership now lives in `app/services/semantic_pass_reads.py` at 762 lines / 13 private helpers, registry preview ownership now lives in `app/services/semantic_registry_preview.py` at 558 lines / 5 private helpers, and the broader owner case remains reduced/open because the extracted lifecycle and read owners still exceed the default 600-line budget even though the architecture probe no longer lists the semantics facade among the top 12 churn hotspots.
- `docs/cli_command_dispatch_boundary_milestone_plan.md`: resolved locally through closeout commit `4a79a82` for `IC-9812A0B138D9`; runtime and maintenance command ownership remains in `app/cli_commands/runtime.py` at `463` lines, retrieval-learning and search-harness ownership now lives in `app/cli_commands/search_harness.py` at `604` lines, `app/cli.py` is reduced to `375` lines, the full architecture-quality report now measures the facade at `risk_score 425.5` with `56` changes over 90 days, and the broader CLI owner case remains reduced/open because the architecture-quality summary still routes `app/cli.py` even though the live architecture probe no longer lists it in the top 12 churn hotspots.
- `docs/agent_task_schema_aggregation_boundary_milestone_plan.md`: resolved locally through closeout commit `efe6d4e` for `IC-24F3558D6091`; `app/schemas/agent_tasks.py` is now a `38` line compatibility facade, production `app/` import fan-in is `0`, local test and integration import fan-in is `30`, and the live architecture-quality measurement is `risk_score 363.75` with `58` changes over 90 days. The broader owner case remains reduced/open because the architecture-quality summary still routes the facade even though the scoped aggregation issue is closed.
- `docs/oversized_test_hotspots_boundary_milestone_plan.md`: resolved locally through closeout commit `65c0c67` in the 2026-05-14 oversized-test closeout window. The seven selected residual files are now `159`, `328`, `92`, `389`, `117`, `428`, and `93` lines respectively for `tests/db_model_contract.py`, `tests/unit/test_agent_task_context.py`, `tests/unit/test_agent_tasks_api.py`, `tests/unit/test_evaluation_service.py`, `tests/unit/test_search_service.py`, `tests/integration/test_retrieval_learning_ledger.py`, and `tests/integration/test_technical_report_harness_roundtrip.py`; the architecture probe no longer lists any of those residual files in the top 20 hotspots; `IC-5F0E1C8B0D42`, `IC-7A628A4CBCAC`, and `IC-908E7A1D2C44` are now deployed, while `IC-D9A84C20546B`, `IC-3B4C9F2A76E1`, `IC-25C1F7B9E4DA`, and `IC-D49E037D5657` remain reduced/open because focused successor files still exceed the default `600`-line hygiene budget.
- `docs/hygiene_owner_case_routing_boundary_milestone_plan.md`: resolved locally through closeout commit `9876f67` after the claim-support, evaluations, evidence provenance-export, semantics, CLI, agent-task schema, and oversized-test packets. Milestone 0 is resolved locally through baseline commit `08a1a75`, Milestone 1 owner-case bootstrap is resolved locally through checkpoint `d4f082c`, Milestone 2 owner-case binding conversion is committed locally as `7ef99cd`, and Milestone 3 owner-case-only hygiene-contract enforcement is committed locally as `0dbd4c7`: `IC-08C078FD4F45` anchors the architecture-governance residual family, `IC-7C73737C689F` anchors the claim-support support residual family, `IC-81C531769EB3` anchors the semantic-governance residual owner, `config/hygiene_policy.yaml` still contains zero `owner_milestone` entries, and `app/hygiene.py`, `app/hygiene_types.py`, `tests/unit/test_hygiene.py`, and `docs/improvement_loop.md` now reject `owner_milestone` as a live ratchet owner reference. Milestone 4 routing-packet closeout is now resolved locally through closeout commit `9876f67`, and the next active stacked follow-on is `docs/architecture_governance_cycle_boundary_milestone_plan.md`.
- `docs/architecture_governance_cycle_boundary_milestone_plan.md`: resolved locally through closeout commit `7a4c5b0` after the claim-support, evaluations, evidence provenance-export, semantics, CLI, agent-task schema, oversized-test, and hygiene owner-case routing packets. Milestone 0 live refresh remains baseline commit `46b90a7`, and the Milestone 1 gate-first architecture import contract remains checkpoint `4338d4e`: `app/architecture_decisions.py` now uses `app/architecture_contract_catalog.py` instead of importing `app.architecture_inspection`, `app/architecture_inspection.py` now consumes `app/services/improvement_case_contracts.py` and `app/services/agent_actions/contracts.py` instead of importing the runtime intake and agent-task action owners directly, `docs/architecture_contract_map.json` records those contract-only metadata sources, and `tests/unit/test_architecture_governance_imports.py` blocks the old direct-import pattern. The architecture probe still reports `4` Python cycle components instead of the Milestone 0 baseline of `5`, but the removed component remains the targeted architecture-governance cycle containing `app.architecture_decisions`, `app.architecture_inspection`, `app.architecture_inspection_rules`, `app.hygiene`, and `app.services.improvement_case_intake`. `uv run docling-system-architecture-quality-report --summary` still reports `hotspot_count=10` with `max_hotspot_risk_score=501.06`, `uv run docling-system-hotspot-prevention-check --strict` stays at `changed_hotspots=0`, `blocked=0`, and `uv run docling-system-hygiene-check` still reports `new hygiene regressions: none`, so the packet closed the governance-cycle slice without shifting debt into a new hotspot. `IC-08C078FD4F45` remains open only as the residual oversized-owner anchor for the still-large governance family.
- `docs/runtime_health_orchestration_milestone_plan.md`: resolved locally through Milestone 4 closeout commit `a57f74f` on 2026-05-14. Milestone 0 refresh / owner-case bootstrap remains committed locally as checkpoint `289f15a`, Milestone 1 gate-first health contract remains committed locally as checkpoint `a84728c`, and Milestones 2 through 4 now close `IC-0F89DBB1CF9F`: `/runtime/status` carries the nested shared `health` report through `app/services/runtime_health.py`, the API/worker/agent-worker publish whole-process heartbeats, `app/runtime_health_cli.py` exposes `docling-system-runtime-health`, `docker-compose.yml` now wires repo-owned healthchecks for all three long-running services with a verified `10s` timeout budget, Compose runtime smoke now passes, and the full DB-backed integration gate is green at `1975 passed`.
- `docs/ci_release_gate_parity_milestone_plan.md`: resolved locally in the current checkout for `IC-2D8D5BF5A8C4`. Implementation proof remains checkpoint `ad18d74`: `app/release_gate_cli.py` owns the canonical `docling-system-release-gate-parity` command, `.github/workflows/release-gate-parity.yml` runs that same command on pull requests and pushes to `main`, every run uploads `build/release-gate-parity/release_gate_report.json`, failures upload `build/release-gate-parity/failure/`, and the remaining branch-protection choice is an out-of-repo operator policy rather than a missing repo implementation surface.
- `docs/boring_change_architecture_milestone_plan.md`: drafted stacked follow-on after the search orchestration, claim-support, evaluations, evidence provenance-export, semantics, runtime-health, and the now-closed CI parity packet. Milestone 0 assumes those prior plans close first, refreshes live system state, and then coordinates the remaining expensive-change architecture gap across residual large-file owners, cycle cleanup, and checked-in architecture or release workflows.
- `docs/search_hydration_boundary_milestone_plan.md`: resolved locally through Milestone 1 closeout commit `14390ad` for `IC-1D03DBFE8492`; the hydration-family owner module now lives in `app/services/search_hydration.py`, `app/services/search.py` is reduced to 2496 lines / 42 private helpers, and the next routed follow-on remains search execution persistence and operator-trace payload assembly.
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
  capability contracts are valid across 6 facades and 111 functions, and the
  architecture quality summary now reports
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, and `max_hotspot_risk_score=501.06`.
- `app/db/models.py` remains in the architecture-quality routing list, but the
  semantic-memory owner family is now also extracted alongside the prior
  model-domain splits, and the remaining 159-line facade now has its own
  dedicated structure gate:
  split: `ApiIdempotencyKey` lives in `app/db/model_domains/platform.py`,
  `IngestBatch`, `IngestBatchItem`, `Document`, and `DocumentRun` live in
  `app/db/model_domains/ingest.py`, and `DocumentRunEvaluation`,
  `DocumentRunEvaluationQuery`, `DocumentChunk`, `DocumentTable`,
  `DocumentTableSegment`, and `DocumentFigure` now live in
  `app/db/model_domains/document_artifacts.py`. The retrieval-interaction
  ledger now lives in `app/db/model_domains/retrieval_interactions.py`, the
  replay/release governance slice now lives in
  `app/db/model_domains/retrieval_replay_governance.py`, the retrieval-learning
  example and artifact rows now live in
  `app/db/model_domains/retrieval_learning_examples.py` and
  `app/db/model_domains/retrieval_learning_artifacts.py`, the
  agent-task and knowledge-operator rows now live in
  `app/db/model_domains/agent_tasks.py`, the
  evaluation-feedback rows now live in `app/db/model_domains/evaluation_feedback.py`,
  the audit-and-evidence rows now live in
  `app/db/model_domains/audit_and_evidence.py`, the claim-support rows now live
  in `app/db/model_domains/claim_support.py`, the semantic-memory rows now live
  in `app/db/model_domains/semantic_memory.py`, the remaining enum ownership now
  lives in `app/db/_model_enums.py`, and `app.db.models` remains the public
  compatibility facade at 159 lines.
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
- The dedicated evidence hotspot owner plan is now implemented locally:
  claim-feedback, release-readiness, manifests, semantic trace, claim-support
  impact, provenance-export, and audit-view ownership now live in
  `app/services/evidence_claim_feedback.py`,
  `app/services/evidence_release_readiness.py`,
  `app/services/evidence_manifests.py`,
  `app/services/evidence_semantic_trace.py`,
  `app/services/evidence_claim_support_impacts.py`,
  `app/services/evidence_claim_support_replay_alerts.py`,
  `app/services/evidence_provenance_exports.py`, and
  `app/services/evidence_audit_views.py`; `app/services/evidence.py` is now a
  141-line / 4-private-helper compatibility facade, the architecture probe no
  longer lists it in the top 12 churn hotspots, and follow-on case
  `IC-65AF4A6D8B1E` now governs the oversized evidence owner-family modules.
- The first `app/services/agent_task_actions.py` registry split is complete:
  search-harness action contract metadata and helper logic now live in
  `app/services/agent_actions/search_harness.py` while
  `app.services.agent_task_actions` remains the compatibility facade and
  execution entrypoint.
- The agent-task orchestration boundary Milestone 1 Registry Composition
  Contract is now implemented locally: `app/services/agent_task_actions.py`
  composes evaluation, semantic analysis/drafting/verification, report,
  claim-support, search-harness, and document-lifecycle owner registries from
  `app/services/agent_actions/*.py`, while
  `app/services/agent_task_context.py` composes core, semantic,
  technical-report, and search-harness builder registries from
  `app/services/agent_task_context_*.py`. The facades are now ratcheted at
  2,081 lines / 35 private helpers and 3,833 lines / 38 private helpers
  respectively.
- The agent-task orchestration boundary Milestone 2 Search-Harness Execution
  And Specialized Context Extraction is now implemented locally: the
  remaining search-harness executors now live in
  `app/services/agent_actions/search_harness.py`, the remaining
  search-harness context builders now live in
  `app/services/agent_task_context_search_harness.py`, and
  `evaluate_claim_support_judge` now lives in
  `app/services/agent_task_context_technical_reports.py`. The central
  facades are reduced to 1,504 lines / 25 private helpers and
  2,950 lines / 31 private helpers respectively.
- The agent-task orchestration boundary Milestone 3 Semantic Governance Family
  Composition is now implemented locally: semantic registry-update, ontology
  extension, and graph-promotion draft, verify, and apply actions now live in
  `app/services/agent_actions/semantic_governance_actions.py`, the matching
  context builders now live in
  `app/services/agent_task_context_semantic_governance.py`, and the central
  facades are reduced to 782 lines / 16 private helpers and 1,879 lines /
  21 private helpers respectively.
- The Residual Weakness Plan Milestone 5 cycle break is complete:
  `app/services/agent_task_action_lookup.py` is the narrow lookup seam for
  context and task services, while executor implementations still live in
  `app.services.agent_task_actions`. The general architecture probe no longer
  reports the large agent-task import-cycle component. Fan-out is now 39 for
  `app.services.agent_task_actions`, which is documented as the
  action-orchestration entrypoint rather than a context/task dependency.
- The agent-task orchestration boundary follow-on plan is now resolved locally:
  the Milestone 5 closeout keeps `app/services/agent_task_actions.py` at 163
  lines / 1 private helper and `app/services/agent_task_context.py` at 121
  lines / 0 private helpers, moves the remaining semantic and technical-report
  families into owner modules, tightens the narrowed facades plus under-budget
  owner modules to exact hygiene ceilings, leaves inherited ratchets only on
  the already-owned oversized extracted modules, transitions
  `IC-A1E186A34097` and `IC-E52B6C7B22FD` to deployed locally, and routes the
  next architecture hotspot to `IC-1D03DBFE8492` / `app/services/search.py`.
  The closeout commit is `7cf7465`.
  The alignment pass still routes `app/hotspot_prevention_classifier.py` into
  bounded hygiene follow-on case `IC-6C1B516A3F92` at 658 lines so the
  prevention gate remains green without broadening the closed boundary plan.
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
- The second `app/services/search.py` core split is complete:
  span-backed query builders, ranked-result hydration, selected-result
  evidence-span loading, and late-interaction hydration now live in
  `app/services/search_hydration.py` while `app.services.search` remains the
  compatibility facade. The hotspot is reduced to 2496 lines / 42 private
  helpers, the new owner module is governed at 392 lines / 11 private helpers
  under `IC-1D03DBFE8492`, and the next routed follow-on remains search
  execution persistence and operator-trace payload assembly. The closeout
  commit is `14390ad`.
- The third `app/services/search.py` core split is complete:
  ranked-result evidence payload assembly, search request/result persistence,
  result-span persistence, and knowledge-operator trace persistence now live in
  `app/services/search_execution_persistence.py` while
  `app.services.search` remains the compatibility facade. The hotspot is
  reduced to 2089 lines / 37 private helpers, the new owner module is governed
  at 423 lines / 6 private helpers under `IC-1D03DBFE8492`, and the next
  routed follow-on is the remaining execution-orchestration cluster in
  `execute_search(...)` plus adjacent candidate-loading/detail assembly paths.
  The closeout commit is `f55b474`.
- The fourth `app/services/search.py` core split is complete:
  search execution orchestration, candidate loading, metadata supplement
  staging, served-mode resolution, and execution detail assembly now live in
  `app/services/search_execution_orchestration.py` while
  `app.services.search` remains the compatibility facade through an explicit
  forwarding wrapper for `execute_search(...)`. The hotspot is reduced to 1592
  lines / 32 private helpers, the new owner module is governed at 532 lines /
  6 private helpers under `IC-1D03DBFE8492`, the architecture-quality
  top-five still excludes `app/services/search.py`, and the next routed
  stacked follow-on is `docs/claim_support_policy_impacts_boundary_milestone_plan.md`.
  The closeout commit is `dae5e4f`.
- The claim-support policy impacts boundary packet is now resolved locally:
  `app/services/claim_support_policy_impacts.py` is a 184-line / 0-private-helper
  compatibility facade, `app/services/claim_support_policy_impact_views.py`
  now owns the read-model and alert family at 899 lines / 16 private helpers,
  and `app/services/claim_support_policy_impact_replay.py` now owns replay
  queueing plus closure lifecycle at 898 lines / 11 private helpers. The
  scoped subsystem-knot is resolved, while the broader owner case
  `IC-E2270F89B397` remains reduced and open because those extracted owners and
  `app/services/claim_support_replay_alert_promotions.py` still exceed the
  default 600-line hygiene budget. The next routed follow-on is
  `docs/evaluations_service_boundary_milestone_plan.md`.
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
- A new standalone hotspot-reduction plan is now active locally for
  `app/services/audit_bundles.py` and `app/services/retrieval_learning.py` in
  `docs/audit_bundle_and_retrieval_learning_hotspots_milestone_plan.md`. The
  plan is now resolved locally through Milestone 5: Milestone 1 moved
  validation-receipt hashing, verification, row creation, and list or latest
  response assembly into
  `app/services/audit_bundle_validation_receipts.py`, reducing
  `app/services/audit_bundles.py` from 3,306 lines to 3,018 while keeping the
  existing facade contract. Milestone 2 is now committed locally as `a5f090a`,
  moving candidate evaluation and reranker-artifact flows into
  `app/services/retrieval_learning_candidates.py` and
  `app/services/retrieval_learning_artifacts.py`, reducing
  `app/services/retrieval_learning.py` from 2,482 lines to 1,470 while keeping
  the existing facade contract. Milestone 3 is now committed locally as
  `7b26bc4`, moving retrieval-training-run payload and provenance construction into
  `app/services/audit_bundle_training_runs.py`, reducing
  `app/services/audit_bundles.py` from 3,018 lines to 2,203 while keeping the
  existing facade contract. Milestone 4 now moves dataset materialization,
  source normalization, payload assembly, and retrieval-training-run
  governance into the owner family
  `app/services/retrieval_learning_datasets.py`,
  `app/services/retrieval_learning_dataset_rows.py`, and
  `app/services/retrieval_learning_dataset_sources.py`, reducing
  `app/services/retrieval_learning.py` to a 143-line compatibility facade
  while governing the new owner modules at 326, 547, and 531 lines. Milestone
  5 now moves the remaining search-harness release payload, validation, and
  PROV family into
  `app/services/audit_bundle_release_payload_serialization.py`,
  `app/services/audit_bundle_release_payload_validation.py`,
  `app/services/audit_bundle_release_payload_prov.py`, and
  `app/services/audit_bundle_release_payloads.py`, reducing
  `app/services/audit_bundles.py` to a 595-line compatibility facade with a
  20 private-helper ratchet, closing both owner-bootstrap cases as
  `deployed`, and then adding exact facade-shape gates after the first
  Milestone 5 closeout exposed residual budget and evidence drift. The next
  routed owner case is now
  `IC-050E60059A34` / `app/services/evidence.py`.
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
- High Value Technical Paydown Milestone 8 is now committed locally: the
  replay and release governance ORM owner module lives in
  `app/db/model_domains/retrieval_replay_governance.py`, `app/db/models.py`
  is reduced to 4,525 lines, and the shared metadata harness protects the
  replay/release governance table and index contract.
- High Value Technical Paydown Milestone 9 is now committed locally: the
  retrieval-learning example and artifact owner modules live in
  `app/db/model_domains/retrieval_learning_examples.py` and
  `app/db/model_domains/retrieval_learning_artifacts.py`, `app/db/models.py`
  is reduced to 3,782 lines, and the shared metadata harness now protects
  retrieval learning plus replay/release governance table, index, and
  unique-constraint contracts.
- Completed bounded milestone record:
  `docs/evaluation_feedback_model_domain_milestone_plan.md` now captures the
  verified `IC-F2A8110185EB` evaluation-feedback split. Its scoped `resolved`
  outcome is the evaluation-feedback family moving out of `app/db/models.py`
  into a dedicated owner module with exact schema-contract coverage; the
  broader owner case remains `reduced` unless the live architecture-quality
  report retires `app/db/models.py` as an open hotspot. That closeout is
  committed locally as `b69c4f6`, and the routed follow-up now returns to
  `docs/data_model_boundary_plan.md`, where the next remaining model-domain
  candidate is the agent-task family if `app/db/models.py` stays routed as an
  owner case.
- Completed bounded milestone record:
  `docs/agent_task_model_domain_milestone_plan.md` now captures the committed
  `IC-F2A8110185EB` agent-task split. Its scoped `resolved` outcome is the
  agent-task and knowledge-operator family moving out of `app/db/models.py`
  into `app/db/model_domains/agent_tasks.py` with exact schema-contract
  coverage; the broader owner case remains `reduced` because the live
  architecture-quality report still lists `app/db/models.py` as the top
  governed hotspot. The routed follow-up returns to
  `docs/data_model_boundary_plan.md`, where the next remaining model-domain
  candidate is the audit-and-evidence family if `app/db/models.py` stays
  routed as an owner case.
- Completed bounded milestone record:
  `docs/audit_and_evidence_model_domain_milestone_plan.md` now captures the
  committed `IC-F2A8110185EB` audit-and-evidence split. Its scoped `resolved`
  outcome is the audit bundle, evidence package, manifest, trace, and
  technical-report readiness/feedback family moving out of `app/db/models.py`
  into `app/db/model_domains/audit_and_evidence.py` with exact schema-contract
  coverage; the broader owner case remains `reduced` because the live
  architecture-quality report still lists `app/db/models.py` as the top
  governed hotspot. The routed follow-up returns to
  `docs/data_model_boundary_plan.md`, where the next remaining model-domain
  candidate is the claim-support family if `app/db/models.py` stays routed as
  an owner case.
- Completed bounded milestone record:
  `docs/claim_support_model_domain_milestone_plan.md` now captures the
  verified `IC-F2A8110185EB` claim-support split. Its scoped `resolved`
  outcome is the replay-alert waiver, fixture-corpus, calibration,
  evaluation, and policy-impact family moving out of `app/db/models.py` into
  `app/db/model_domains/claim_support.py` with exact schema-contract
  coverage; the broader owner case remains `reduced` because the live
  architecture-quality report still lists `app/db/models.py` as the top
  governed hotspot. The routed follow-up returns to
  `docs/data_model_boundary_plan.md`, where the next remaining model-domain
  candidate is the semantic-memory family if `app/db/models.py` stays routed
  as an owner case.
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
  `case_count=28`, `status_counts.open=20`, `status_counts.deployed=7`,
  `status_counts.measured=1`, and
  `measured_case_count=18`, with open cases concentrated in
  architecture-governance ownership rather than untracked or milestone-owned
  debt.
- Current routed follow-up:
  `docs/evidence_provenance_exports_boundary_milestone_plan.md` is now
  resolved locally on 2026-05-13. `app/services/evidence_provenance_exports.py`
  is reduced to a 14-line compatibility facade, the new graph-core owner
  lives in `app/services/evidence_provenance_export_graph_core.py` at
  549 lines, the report-lineage owner lives in
  `app/services/evidence_provenance_export_graph_report.py` at 218 lines, and
  the lifecycle owner lives in
  `app/services/evidence_provenance_export_lifecycle.py` at 278 lines. The
  broader evidence owner-family case `IC-65AF4A6D8B1E` remains reduced because
  `app/services/evidence_technical_report_exports.py`,
  `app/services/evidence_semantic_trace.py`,
  `app/services/evidence_claim_feedback.py`, and
  `app/services/evidence_audit_views.py` still exceed 600 lines, and the
  hotspot-prevention classifier follow-up case `IC-6C1B516A3F92` also remains
  open after expanding the strict provenance-export gate to 773 lines. The
  next active architecture milestone is now
  `docs/semantics_service_boundary_milestone_plan.md`.

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

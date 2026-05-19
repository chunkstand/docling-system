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
- `docs/db_models_residual_owner_family_milestone_plan.md`: resolved through the 2026-05-18 durable closeout after Milestone 4 verification for `IC-46C5B38A1D2E`, `IC-7D8AE7C83B8F`, and `IC-62C75B82F0AA`. `app/db/model_domains/audit_and_evidence.py`, `app/db/model_domains/semantic_memory.py`, and `app/db/model_domains/claim_support.py` now close at `31`, `53`, and `31` lines over focused family-local owners, the shared DB-model unit and integration roots now close at `457` and `472` lines through focused siblings, the focused verification slices passed at `609` and `335`, and the full DB-backed suite passed at `2078`.
- `docs/hotspot_routing_trap_resolution_milestone_plan.md`: resolved through the 2026-05-18 durable closeout. Raw hotspot measurements remain intact, while the report now exposes `top_routed_hotspot_paths`, `routing_trap_paths`, `stale_facade_hotspot_count`, and `raw_improvement_case_candidates`; structured trap metadata now lives in `config/hotspot_prevention.yaml`; and `app/services/improvement_case_intake.py` now imports the routed queue only. Focused governance verification passed at `105`, the routed dry-run import reported `candidate_count=12` / `imported_count=1` / `skipped_count=11`, and the full DB-backed suite passed at `2083`.
- `docs/residual_large_file_backlog_milestone_plan.md`: resolved through the 2026-05-18 durable closeout. The live architecture probe now reports `0` code files above `800`, and the later documents, verification, and governance follow-ons are now also resolved, so the next code-owning packet must be reselected from the broader coordination brief.
- `docs/evaluation_residual_owner_family_milestone_plan.md`: resolved through the 2026-05-18 durable closeout. The governed evaluation family now closes at `376`, `570`, `67`, `530`, `175`, `218`, `322`, `431`, `252`, `445`, `310`, `390`, and `378` lines across the fixture, scoring, workbench, and family-local test roots, so no governed evaluation file remains above the default `600`-line budget.
- `docs/ui_module_residual_owner_family_milestone_plan.md`: resolved through the 2026-05-18 durable closeout. Auth and fetch ownership now live in `app/ui/modules/shared_runtime.js` at `307` lines, shared UI helpers remain in `app/ui/modules/shared.js` at `517`, search rendering now lives in `app/ui/modules/shared_search_rendering.js` at `115`, and the agent family now closes at `56`, `313`, `318`, and `599` lines across `app/ui/modules/agents_collections.js`, `app/ui/modules/agents_claim_support_replay.js`, `app/ui/modules/agents_report_harness.js`, and `app/ui/modules/agents.js` while preserving `app/ui/app.js` at `107`.
- `docs/semantic_and_technical_report_residual_owner_family_milestone_plan.md`: resolved through the 2026-05-18 durable closeout. The governed family now closes at `543`, `570`, `574`, `485`, `33`, `554`, `159`, and `258` lines across the semantic triage, technical-report verification, task-context, and audit-training siblings under `IC-2D5A7E9C4B18`, and downstream report-context plus harness-integrity verification stayed green so the debt did not shift into adjacent owners.
- `docs/closeout_state_queue_alignment_milestone_plan.md`: resolved through the 2026-05-18 durable closeout as the docs-only coordination closeout above the remaining cross-cutting code packets. The handoff, parent backlog, and umbrella routing docs now agree on the same queue, the child-packet closeout wording is narrowed, and the stale `docs/shared_verification_roots_milestone_plan.md` branch is explicitly historical unless a later rebaseline revives it.
- `docs/cross_cutting_large_file_residual_milestone_plan.md`: resolved through the 2026-05-18 durable closeout after the semantic/report family. It removes the live `>800` backlog under `IC-6C3E1A7B9D52`, preserves the governance self-hosting family under `IC-08C078FD4F45` as a separate bounded packet, and now records both the verification branch and the later governance branch as resolved with the queue returned to the broader under-budget reselect step.
- `docs/documents_service_boundary_milestone_plan.md`: resolved through the 2026-05-18 durable closeout. `app/services/documents.py` is reduced to a `49` line compatibility facade, ingest ownership now lives in `app/services/document_ingest.py` at `233`, run-queue and reprocess ownership now live in `app/services/document_run_queue.py` at `324`, read ownership remains in `app/services/document_run_views.py` at `276`, and the focused document-service unit plus DB-backed integration slices stayed green so the debt did not shift into adjacent owners.
- `docs/cross_cutting_verification_roots_milestone_plan.md`: resolved through the 2026-05-18 durable closeout after the documents-service closeout. The selected verification roots now close at `324`, `331`, `540`, `269`, and `437` lines with family-local parser, search-harness, and claim-support siblings or support staying below the same-packet support ceilings, and the focused packet-local verification slices passed at `28` and `19`.
- `docs/improvement_case_governance_self_hosting_milestone_plan.md`: resolved through the 2026-05-18 durable closeout. The governed roots now close at `370`, `514`, `552`, `82`, and `218` lines, family-local siblings now close at `122`, `184`, `475`, `279`, `277`, `101`, `122`, and `551` with exact hygiene ratchets, the local `app.services.improvement_case_observations` / `app.services.improvement_cases` cycle remains removed, and the later hotspot-interpretation plus open-owner packets now clear the remaining stale reduced-facade queue debt.
- `docs/hotspot_interpretation_source_of_truth_milestone_plan.md`: resolved locally on 2026-05-18 as the prerequisite routed-hotspot closeout. Queue docs now point to the canonical routed-trap explanation, and `IC-9812A0B138D9` no longer remains an ambiguous open facade case.
- `docs/open_owner_backlog_resolution_milestone_plan.md`: resolved locally on 2026-05-18. The packet closes the reduced CLI, API, semantic-pass, and run roots as honest deployed or verified boundaries, reduces `semantic_generation_brief.py` to `505` lines with a `145`-line metrics sibling, reduces `semantic_graph_core.py` / `semantic_graph_promotions.py` to `492` / `589` with `214` / `138` line support and snapshot-lifecycle siblings, and returns the next packet selection to `top_routed_hotspot_paths`.
- `docs/claim_support_judge_integration_residual_milestone_plan.md`: resolved locally on 2026-05-18. The residual claim-support smoke root stays at `339` lines, the deleted `702`-line shared support sink is replaced by focused support owners at `13`, `277`, `344`, `75`, and `381` lines, replay-alert coverage moves into a new `152`-line sibling while promotions drops to `510`, hotspot prevention now routes the root as a deferred reduced facade, and the next routed packet advances to `IC-D49E037D5657` / `tests/integration/test_technical_report_harness_roundtrip.py`.
- `docs/shared_verification_roots_milestone_plan.md`: stale historical follow-on for older shared DB-model and evaluation verification roots. Its former targets are already reduced locally, and the resolved queue-alignment packet now classifies it as historical unless a later rebaseline selects it again explicitly.
- `docs/evidence_hotspot_owner_milestone_plan.md`: implemented locally through the evidence facade-resolution closeout for `IC-050E60059A34`; `app/services/evidence.py` is reduced to a 141-line compatibility facade, closeout commit `3fe9132` is now recorded in the registry, and follow-on case `IC-65AF4A6D8B1E` governs the oversized evidence owner-family modules.
- `docs/agent_task_orchestration_boundary_milestone_plan.md`: resolved locally through Milestone 5 closeout commit `7cf7465` for `IC-A1E186A34097` / `app/services/agent_task_actions.py` and `IC-E52B6C7B22FD` / `app/services/agent_task_context.py`; the next routed hotspot is `IC-1D03DBFE8492` / `app/services/search.py`.
- `docs/search_execution_persistence_boundary_milestone_plan.md`: resolved locally through Milestone 1 closeout commit `f55b474` for `IC-1D03DBFE8492`; search execution persistence and operator-trace payload assembly now live in `app/services/search_execution_persistence.py`, `app/services/search.py` is reduced to 2089 lines / 37 private helpers, and the next routed follow-on is the remaining execution-orchestration cluster in `execute_search(...)` and adjacent candidate-loading/detail assembly paths.
- `docs/search_execution_orchestration_boundary_milestone_plan.md`: resolved locally through Milestone 1 closeout commit `dae5e4f` for `IC-1D03DBFE8492`; search execution orchestration now lives in `app/services/search_execution_orchestration.py`, `app/services/search.py` is reduced to 1592 lines / 32 private helpers, and the broader owner case remains reduced because the architecture probe still routes the facade.
- `docs/search_compatibility_facade_boundary_milestone_plan.md`: resolved locally through closeout commit `fd9dd2a` for `IC-1D03DBFE8492`; harness/reranker ownership now lives in `app/services/search_harnesses.py` at `627` lines / `0` private helpers, low-level retrieval primitives now live in `app/services/search_retrieval_primitives.py` at `653` lines / `0` private helpers, metadata supplement plus adjacent-context ownership now lives in `app/services/search_metadata_supplement.py` at `262` lines / `0` private helpers, and `app/services/search.py` is reduced to a `231` line / `2` private-helper compatibility facade that no longer appears in the top architecture-probe hotspot queue.
- `docs/claim_support_policy_impacts_boundary_milestone_plan.md`: resolved locally through Milestone 4 closeout commit `3d7d090` for `IC-E2270F89B397`; `app/services/claim_support_policy_impacts.py` is now a 184-line compatibility facade, the read-model and alert owner now lives in `app/services/claim_support_policy_impact_views.py` at 899 lines / 16 private helpers, the replay-lifecycle owner now lives in `app/services/claim_support_policy_impact_replay.py` at 898 lines / 11 private helpers, and the broader owner case remains reduced because the extracted owners still exceed the default 600-line budget.
- `docs/claim_support_residual_owner_family_milestone_plan.md`: resolved locally through closeout commit `40024a3` across `IC-E2270F89B397` and `IC-7C73737C689F`; the packet retires the residual policy-impact, evaluation, governance, and replay-alert fixture-corpus owner families at or below the default 600-line budget, removes the live `claim_support_policy_impacts` / `claim_support_replay_alert_promotions` cycle, and updates hygiene plus improvement-case routing so both claim-support owner cases are now deployed locally.
- `docs/evaluations_service_boundary_milestone_plan.md`: resolved locally through Milestone 4 closeout commit `1159297` for `IC-BF180637814C`; `app/services/evaluations.py` remains the `283` line / `1` private-helper orchestration and compatibility facade, latest-evaluation summary/detail reads remain in `app/services/evaluation_reads.py` at `154` lines / `1` private helper, and the later evaluation residual owner-family packet now leaves the extracted fixture, scoring, workbench, and family-local test roots at `376`, `570`, `67`, `530`, `175`, `218`, `322`, `431`, `252`, `445`, `310`, `390`, and `378` lines respectively.
- `docs/evidence_provenance_exports_boundary_milestone_plan.md`: resolved locally through closeout commit `1aa8378` on 2026-05-13 for the scoped provenance-export knot under `IC-65AF4A6D8B1E`; `app/services/evidence_provenance_exports.py` is now a 14-line compatibility facade, graph assembly now lives in `app/services/evidence_provenance_export_graph_core.py` at 549 lines, report-trace and claim-lineage graph ownership now lives in `app/services/evidence_provenance_export_graph_report.py` at 218 lines, lifecycle and persistence now live in `app/services/evidence_provenance_export_lifecycle.py` at 278 lines, and the broader owner case remains reduced because `app/services/evidence_technical_report_exports.py`, `app/services/evidence_semantic_trace.py`, `app/services/evidence_claim_feedback.py`, and `app/services/evidence_audit_views.py` still exceed the default 600-line budget.
- `docs/evidence_residual_owner_family_milestone_plan.md`: resolved locally in the current checkout as the selected-four-owner closeout after the provenance-export split. Milestone 7 closes the selected packet at `45`, `48`, `36`, and `19` lines for `app/services/evidence_technical_report_exports.py`, `app/services/evidence_claim_feedback.py`, `app/services/evidence_semantic_trace.py`, and `app/services/evidence_audit_views.py`; the later manifest-trace and manifest-owner follow-ons reduce those adjacent evidence seams to `203 / 204 / 461 / 244` and `370 / 384`; and the later replay-alert follow-on now leaves the broader `IC-65AF4A6D8B1E` case locally retirement-ready rather than still blocked by a live over-budget owner.
- `docs/evidence_manifest_trace_graph_boundary_milestone_plan.md`: resolved locally in the current checkout as the predecessor standalone follow-on for `IC-65AF4A6D8B1E` after the selected evidence residual packet closed locally. Milestones 0 through 2 are now resolved locally: `app/services/evidence_manifest_traces.py` is reduced to a `203` line / `0` private-helper facade, graph canonicalization now lives in `app/services/evidence_manifest_trace_graph.py` at `204` lines, mixed trace assembly now lives in `app/services/evidence_manifest_trace_assembly.py` at `461` lines, replay lineage now lives in `app/services/evidence_manifest_trace_replay.py` at `244` lines, and `tests/unit/test_evidence_manifest_traces.py` now adds direct graph-owner coverage and a facade-size ratchet. The later manifest-owner and replay-alert follow-ons now complete the remaining evidence-owner routing in the current checkout.
- `docs/evidence_manifest_owner_boundary_milestone_plan.md`: resolved locally in the current checkout as the predecessor standalone follow-on after the manifest-trace split. Milestones 0 through 2 are now resolved locally: `app/services/evidence_manifests.py` is reduced to a `370` line / `8` private-helper manifest facade, payload assembly now lives in `app/services/evidence_manifest_payloads.py` at `384` lines / `0` private helpers, `tests/unit/test_evidence_manifests.py` adds dedicated owner coverage and the facade-size ratchet, and the later replay-alert follow-on now removes the last live over-budget evidence owner from the local checkout.
- `docs/evidence_claim_support_replay_alerts_boundary_milestone_plan.md`: resolved locally in the current checkout as the latest resolved bounded evidence-owner follow-on for `IC-65AF4A6D8B1E` after the manifest-owner split. Milestones 0 through 2 are now resolved locally: `app/services/evidence_claim_support_replay_alerts.py` is reduced to a `407` line / `4` private-helper replay-alert facade, replay-alert fixture-corpus snapshot lineage now lives in `app/services/evidence_claim_support_replay_alert_corpus.py` at `128` lines / `0` private helpers, `tests/unit/test_evidence_claim_support_replay_alerts.py` adds dedicated owner coverage and the facade-size ratchet, the focused unit gate passed at `24 passed`, the technical-report integration slice passed at `5 passed`, and the broader evidence owner-family case now has no governed file above the default `600`-line budget in the local checkout and is retirement-ready pending commit.
- `docs/semantics_service_boundary_milestone_plan.md`: resolved locally through closeout commit `a2eb27e` on 2026-05-13 local / 2026-05-14 UTC for `IC-9E6B8F5D62A1`; `app/services/semantics.py` is now a 54-line / 0-private-helper compatibility facade, the later lifecycle/read follow-on reduced the extracted semantic-pass owners under budget, and the open-owner closeout now verifies the broader semantics compatibility case as closed locally rather than merely retirement-ready.
- `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`: Milestones 0 through 5 are resolved locally in the current checkout as the latest resolved bounded semantic-owner follow-on after the replay-alert evidence packet. The refreshed packet keeps `app/services/semantic_pass_lifecycle.py` at `529` lines / `3` private helpers, `app/services/semantic_pass_reads.py` at `372` lines / `3`, and the supporting artifact/review/source-record siblings at `150`, `369`, and `415`, and the later open-owner closeout now verifies `IC-9E6B8F5D62A1`, `IC-8304248AB64C`, and `IC-ADCFFF108626` as closed locally.
- `docs/hotspot_prevention_family_boundary_milestone_plan.md`: resolved locally in the current checkout through Milestone 3 closeout. `app/hotspot_prevention_classifier.py` is now `360` lines / `1` private helper, the classifier family now also governs `app/hotspot_prevention_claim_support_rules.py` at `436 / 1`, `app/hotspot_prevention_classifier_service_rules.py` at `384 / 0`, `app/hotspot_prevention_classifier_boundary_rules.py` at `209 / 0`, and `app/hotspot_prevention_classifier_support.py` at `571 / 1`, and the companion test family now closes at `595 / 0`, `318 / 0`, `296 / 0`, and `50 / 2` across the root test, blocked-family sibling tests, wrapper sibling tests, and shared test support. The focused hotspot-prevention suite remains green at `40 passed`, the strict hotspot-prevention gate reports `blocked=0`, hygiene still reports `new hygiene regressions: none`, and the broader boring-change coordination brief must now activate the next fresh bounded packet from the refreshed post-closeout backlog.
- `docs/semantic_residual_owner_family_milestone_plan.md`: superseded historical draft. It predates the app large owner modules closeout that reduced `app/services/semantic_governance.py` to `39` lines, so the active lifecycle/read follow-on now routes through `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md` instead of reviving the older three-owner draft unchanged.
- `docs/cli_command_dispatch_boundary_milestone_plan.md`: resolved locally through closeout commit `4a79a82` for `IC-9812A0B138D9`; runtime and maintenance command ownership remains in `app/cli_commands/runtime.py` at `463` lines, retrieval-learning and search-harness ownership now lives in `app/cli_commands/search_harness.py` at `604` lines, `app/cli.py` is reduced to `375` lines, and the later hotspot-interpretation closeout now records the facade case as deployed rather than leaving it open because of raw hotspot ordering alone.
- `docs/agent_task_schema_aggregation_boundary_milestone_plan.md`: resolved locally through closeout commit `efe6d4e` for `IC-24F3558D6091`; `app/schemas/agent_tasks.py` is now a `38` line compatibility facade, production `app/` import fan-in is `0`, local test and integration import fan-in is `30`, and the live architecture-quality measurement is `risk_score 363.75` with `58` changes over 90 days. The broader owner case remains reduced/open because the architecture-quality summary still routes the facade even though the scoped aggregation issue is closed.
- `docs/oversized_test_hotspots_boundary_milestone_plan.md`: resolved locally through closeout commit `65c0c67` in the 2026-05-14 oversized-test closeout window. The seven selected residual files are now `159`, `328`, `92`, `389`, `117`, `428`, and `93` lines respectively for `tests/db_model_contract.py`, `tests/unit/test_agent_task_context.py`, `tests/unit/test_agent_tasks_api.py`, `tests/unit/test_evaluation_service.py`, `tests/unit/test_search_service.py`, `tests/integration/test_retrieval_learning_ledger.py`, and `tests/integration/test_technical_report_harness_roundtrip.py`; the architecture probe no longer lists any of those residual files in the top 20 hotspots; `IC-5F0E1C8B0D42`, `IC-7A628A4CBCAC`, and `IC-908E7A1D2C44` are now deployed, while `IC-D9A84C20546B`, `IC-3B4C9F2A76E1`, `IC-25C1F7B9E4DA`, and `IC-D49E037D5657` remain reduced/open because focused successor files still exceed the default `600`-line hygiene budget.
- `docs/hygiene_owner_case_routing_boundary_milestone_plan.md`: resolved locally through closeout commit `9876f67` after the claim-support, evaluations, evidence provenance-export, semantics, CLI, agent-task schema, and oversized-test packets. Milestone 0 is resolved locally through baseline commit `08a1a75`, Milestone 1 owner-case bootstrap is resolved locally through checkpoint `d4f082c`, Milestone 2 owner-case binding conversion is committed locally as `7ef99cd`, and Milestone 3 owner-case-only hygiene-contract enforcement is committed locally as `0dbd4c7`: `IC-08C078FD4F45` anchors the architecture-governance residual family, `IC-7C73737C689F` anchors the claim-support support residual family, `IC-81C531769EB3` anchors the semantic-governance residual owner, `config/hygiene_policy.yaml` still contains zero `owner_milestone` entries, and `app/hygiene.py`, `app/hygiene_types.py`, `tests/unit/test_hygiene.py`, and `docs/improvement_loop.md` now reject `owner_milestone` as a live ratchet owner reference. Milestone 4 routing-packet closeout is now resolved locally through closeout commit `9876f67`, and the next active stacked follow-on is `docs/architecture_governance_cycle_boundary_milestone_plan.md`.
- `docs/architecture_governance_cycle_boundary_milestone_plan.md`: resolved locally through closeout commit `7a4c5b0` after the claim-support, evaluations, evidence provenance-export, semantics, CLI, agent-task schema, oversized-test, and hygiene owner-case routing packets. Milestone 0 live refresh remains baseline commit `46b90a7`, and the Milestone 1 gate-first architecture import contract remains checkpoint `4338d4e`: `app/architecture_decisions.py` now uses `app/architecture_contract_catalog.py` instead of importing `app.architecture_inspection`, `app/architecture_inspection.py` now consumes `app/services/improvement_case_contracts.py` and `app/services/agent_actions/contracts.py` instead of importing the runtime intake and agent-task action owners directly, `docs/architecture_contract_map.json` records those contract-only metadata sources, and `tests/unit/test_architecture_governance_imports.py` blocks the old direct-import pattern. The architecture probe still reports `4` Python cycle components instead of the Milestone 0 baseline of `5`, but the removed component remains the targeted architecture-governance cycle containing `app.architecture_decisions`, `app.architecture_inspection`, `app.architecture_inspection_rules`, `app.hygiene`, and `app.services.improvement_case_intake`. `uv run docling-system-architecture-quality-report --summary` still reports `hotspot_count=10` with `max_hotspot_risk_score=501.06`, `uv run docling-system-hotspot-prevention-check --strict` stays at `changed_hotspots=0`, `blocked=0`, and `uv run docling-system-hygiene-check` still reports `new hygiene regressions: none`, so the packet closed the governance-cycle slice without shifting debt into a new hotspot. `IC-08C078FD4F45` remains open only as the residual oversized-owner anchor for the still-large governance family.
- `docs/runtime_health_orchestration_milestone_plan.md`: resolved locally through Milestone 4 closeout commit `a57f74f` on 2026-05-14. Milestone 0 refresh / owner-case bootstrap remains committed locally as checkpoint `289f15a`, Milestone 1 gate-first health contract remains committed locally as checkpoint `a84728c`, and Milestones 2 through 4 now close `IC-0F89DBB1CF9F`: `/runtime/status` carries the nested shared `health` report through `app/services/runtime_health.py`, the API/worker/agent-worker publish whole-process heartbeats, `app/runtime_health_cli.py` exposes `docling-system-runtime-health`, `docker-compose.yml` now wires repo-owned healthchecks for all three long-running services with a verified `10s` timeout budget, Compose runtime smoke now passes, and the full DB-backed integration gate is green at `1975 passed`.
- `docs/ci_release_gate_parity_milestone_plan.md`: resolved locally in the current checkout for `IC-2D8D5BF5A8C4`. Implementation proof remains checkpoint `ad18d74`: `app/release_gate_cli.py` owns the canonical `docling-system-release-gate-parity` command, `.github/workflows/release-gate-parity.yml` runs that same command on pull requests and pushes to `main`, every run uploads `build/release-gate-parity/release_gate_report.json`, failures upload `build/release-gate-parity/failure/`, and the remaining branch-protection choice is an out-of-repo operator policy rather than a missing repo implementation surface.
- `docs/app_large_owner_modules_resolution_milestone_plan.md`: resolved locally in the working tree on 2026-05-15. The selected app-side large owners are now reduced to `185`, `199`, `15`, `120`, `91`, `39`, and `404` lines respectively for `app/services/semantic_graph.py`, `app/services/docling_parser.py`, `app/services/quality.py`, `app/services/semantic_candidates.py`, `app/services/semantic_generation.py`, `app/services/semantic_governance.py`, and `app/services/runs.py`; the later open-owner closeout then resolves the accepted residuals at `505` / `145` for the generation brief family and `492` / `589` / `214` / `138` for the graph family.
- `docs/boring_change_architecture_milestone_plan.md`: refreshed broader coordination brief on 2026-05-18 after the cycle, agent-task residual, DB-model residual, hotspot-routing trap, evaluation, UI, semantic/report, cross-cutting, queue-alignment, documents-service, cross-cutting verification, governance self-hosting, hotspot-interpretation, open-owner, and claim-support residual closeouts. The older semantic residual draft remains explicitly superseded, the live `>800` backlog is now cleared, and the broader boring-change brief now advances next-packet selection to the technical-report harness family followed by the hotspot-prevention residual test root.
- `docs/python_cycle_backlog_elimination_milestone_plan.md`: resolved through the 2026-05-18 durable closeout as the selected standalone cycle packet. Milestone 0 rebaselined the stale drafted cycle map to the live search, evidence, parser, evaluation, run, and semantic-governance import edges; Milestones 1 through 3 removed every live Python cycle by converting ambiguous package imports to explicit submodule imports and by extracting `app/services/evidence_provenance_export_graph_contracts.py` plus `app/services/evidence_search_package_build.py`; and Milestone 4 wired the repo-owned regression gate `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py` into `.github/workflows/architecture-governance.yml`. `architecture_probe.py --fail-on-cycles` now reports `0` cycles while the separate `27`-file `>800` backlog remains routed through the broader boring-change plan.
- `docs/agent_task_residual_owner_family_milestone_plan.md`: resolved through the 2026-05-18 durable closeout for `IC-4098E8370B88` plus the inherited search-harness and semantic-governance owner families under `IC-A1E186A34097` and `IC-E52B6C7B22FD`. `app/services/agent_tasks.py` now closes at `324` lines with focused dependency, read, and lifecycle owners at `176`, `259`, and `197`; `app/services/agent_actions/search_harness.py` and `app/services/agent_task_context_search_harness.py` now close at `444` and `263` with focused drafting or triage successors at `453`, `386`, `468`, and `172`; `app/services/agent_actions/semantic_governance_actions.py` and `app/services/agent_task_context_semantic_governance.py` now close at `565` and `397` with ontology or graph successors at `281`, `251`, `405`, and `367`; and the residual root tests now close at `12`, `10`, `97`, and `283` lines with focused sibling suites and family-local support carrying the moved coverage. Focused verification is green at `105 passed` plus `13 passed`, the hotspot-prevention gate reports `blocked=0`, hygiene reports `new hygiene regressions: none`, the architecture probe still reports `0` cycles with `20` code files above `800`, and the full DB-backed suite passed at `2044 passed`.
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
  `hotspot_count=10`, and `max_hotspot_risk_score=496.06`.
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
  The later hotspot-prevention family packet now resolves that follow-on
  locally by reducing `app/hotspot_prevention_classifier.py` to `360` lines
  and routing the remaining rule families through exact-ratcheted siblings, so
  the prevention gate remains green without broadening the closed
  orchestration plan.
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
  6 private helpers under `IC-1D03DBFE8492`, and the architecture-quality
  top-five still excludes `app/services/search.py`.
  The closeout commit is `dae5e4f`.
- The fifth `app/services/search.py` core split is complete:
  harness and reranker ownership now lives in
  `app/services/search_harnesses.py`, low-level retrieval primitives now live
  in `app/services/search_retrieval_primitives.py`, and metadata supplement
  plus adjacent-context expansion now live in
  `app/services/search_metadata_supplement.py` while `app.services.search`
  remains the compatibility facade for public imports, alias forwarding, and
  the explicit `execute_search(...)` / `search_documents(...)` wrappers. The
  facade is reduced to 231 lines / 2 private helpers, the extracted owner
  modules close at 627 / 0, 653 / 0, and 262 / 0 respectively, and the live
  architecture probe no longer lists `app/services/search.py` in the top 20
  hotspots. The broader search owner case `IC-1D03DBFE8492` is now deployed,
  and the next stacked follow-on is
  `docs/boring_change_architecture_milestone_plan.md`.
- The claim-support residual owner-family packet is now resolved locally through
  closeout commit `40024a3`: `app/services/claim_support_policy_impacts.py`,
  `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`, and
  `app/services/claim_support_replay_alert_fixture_corpus.py` are compact
  public seams at 184 / 0, 164 / 0, 257 / 6, and 206 / 0 respectively; the
  extracted policy-impact owners now close at 207 / 0, 361 / 7, 469 / 9,
  247 / 6, 344 / 4, 424 / 1, 600 / 9, 428 / 9, and 535 / 6; the extracted
  support-family owners close at 534 / 7, 319 / 4, 339 / 1, 534 / 6, 559 / 2,
  328 / 4, and 569 / 8. No new claim-support service hotspots formed: the
  architecture-quality summary top hotspot paths still exclude claim-support
  service modules and the architecture probe top 20 no longer routes the split
  claim-support owner files. The live claim-support
  `claim_support_policy_impacts` / `claim_support_replay_alert_promotions`
  cycle is gone, `IC-E2270F89B397` and `IC-7C73737C689F` are now deployed
  locally, and the next broader coordination brief remains
  `docs/boring_change_architecture_milestone_plan.md`.
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
  that historical next-step note is now superseded by the routed queue at the
  top of this index; the next active architecture milestone must be reselected
  from `docs/boring_change_architecture_milestone_plan.md`.

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

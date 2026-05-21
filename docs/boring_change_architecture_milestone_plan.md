# Boring Change Architecture Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: drafted originally on 2026-05-13 and refreshed on 2026-05-16 to the
current system state after the search, claim-support, evaluations,
evidence-provenance, semantics, runtime-health, and CI parity closeouts, and
after the app large owner modules closeout and the narrower standalone
evidence-owner follow-on closed locally through the Milestone 7 selected-owner
closeout, then through the manifest-trace, manifest-owner, replay-alert, and
semantic lifecycle/read follow-ons. Milestones 0 and 1 are now resolved
locally in the current checkout, `docs/hotspot_prevention_family_boundary_milestone_plan.md`
was the latest resolved bounded implementation brief at the time of the
2026-05-16 refresh, `docs/python_cycle_backlog_elimination_milestone_plan.md`
and `docs/agent_task_residual_owner_family_milestone_plan.md` are now also
resolved locally on 2026-05-18, `docs/db_models_residual_owner_family_milestone_plan.md`
is now likewise resolved locally in the current checkout,
`docs/hotspot_routing_trap_resolution_milestone_plan.md` is now also resolved
locally through the routed-queue closeout, and this broader coordination brief
now routes through the Milestone 0 rebaseline in
`docs/residual_large_file_backlog_milestone_plan.md`, which now first routes
the now-resolved closeout-state and stale-queue alignment packet
`docs/closeout_state_queue_alignment_milestone_plan.md` and now returns the
now-resolved cross-cutting verification packet recorded in
`docs/cross_cutting_verification_roots_milestone_plan.md`; the
governance self-hosting packet is now likewise resolved through the durable
closeout, the later
hotspot-interpretation, open-owner, and claim-support residual follow-ons are
now also resolved locally, and the resolved documents-service packet remains
recorded in `docs/documents_service_boundary_milestone_plan.md`.
Owner context: broader coordination brief for the remaining "expensive to
change" backlog across under-budget residual owner families, stale routing risk
around already-shrunk compatibility facades, and the checked-in gates that
must keep oversized files and import cycles from regrowing. This plan remains
the active coordination brief after the hotspot-prevention companion-test
closeout, the later search API route-surface follow-on, and the later
agent-tasks API lifecycle-family follow-on, the later search-schema
facade follow-on, the later DB-model residual registry closeout, and the later
queue-honesty refresh, the later architecture-inspection test-surface
closeout, and the later agent-tasks route-surface closeout, with the routed
queue previously advanced to
`tests/integration/test_retrieval_learning_ledger.py` after retiring the stale
DB-model smoke root, the deployed audit-bundles facade, the accepted residual
API bootstrap entry, the reduced architecture-inspection smoke root, and the
reduced `app/api/routers/agent_tasks.py` route root from the active queue. The
later retrieval-learning residual-smoke closeout now routes that already-split
family off the active queue as well, so the live `top_routed_hotspot_paths`
queue was empty at that checkpoint and the next code-owning packet had to be
reselected from this broader brief rather than from a stale residual root.
Current live routing state in the current checkout:
`top_routed_hotspot_paths=[]`,
`broader_rebaseline_candidate_count=0`,
`top_broader_rebaseline_paths=[]`,
`status_counts={"deployed":67}`, and
`architecture_probe.py --fail-on-cycles` reports `0` Python cycle components.
The queue is therefore empty by the repo’s operational signals. A separate
standalone optional follow-on now exists in
`docs/db_models_caller_migration_boundary_milestone_plan.md` for proactive
`app.db.models` caller-migration work, but it is not a queue-selected packet
and should not override a future fresh live rebaseline.
The later
2026-05-19 registry-alignment sweep also deploys the stale reduced-root
agent-task, claim-support, action-test, and UI bootstrap cases left behind by
earlier packets, bringing the live case summary to `open=12`, `verified=8`,
and `deployed=40` while keeping `broad_facade_count=2`,
`legibility_gap_count=0`, and `top_routed_hotspot_paths=[]`. The later fresh
broader reselect then closes `IC-23F2C79C8AA7` as a verified reduced
documents-API route surface, moving the live counts to `open=11`,
`verified=9`, and `deployed=40` while leaving `top_routed_hotspot_paths=[]`
because the queue still has no active routed packet. The later queue-freeze
follow-on now records the explicit remaining order in
`docs/remaining_packet_queue_resolution_milestone_plan.md`: Packet A stale-open
registry closeout, Packet B verified-to-deployed closeout, Packet C
`IC-3B4C9F2A76E1`, Packet D `IC-25C1F7B9E4DA`, and Packet E final queue
exhaustion or rebaseline. The later 2026-05-19 Packet A stale-open registry
closeout now completes the first docs-only queue pass, deploys nine
already-reduced `open` cases, moves the live counts to `open=2`,
`verified=9`, and `deployed=49`, and leaves Packet B verified-to-deployed
closeout as the next queued packet while `top_routed_hotspot_paths=[]`
remains unchanged. The later 2026-05-19 Packet B verified-to-deployed registry
closeout then deploys the remaining nine verified cases, moves the live counts
to `open=2`, `verified=0`, and `deployed=58`, and leaves Packet C
`IC-3B4C9F2A76E1` as the next queued packet while
`top_routed_hotspot_paths=[]` still remains unchanged. The later 2026-05-19
Packet C residual-successor closeout then deploys `IC-3B4C9F2A76E1`, reduces
the last two over-budget agent-task context successor tests to `358` and
`236` lines over new `294`- and `426`-line support modules, moves the live
counts to `open=1`, `verified=0`, and `deployed=59`, and leaves Packet D
`IC-25C1F7B9E4DA` as the next queued packet while
`top_routed_hotspot_paths=[]` remains unchanged. The later Packet C hardening
pass then removes the temporary support-extraction exceptions, aligns the
owner-case verification contract to the actual gate stack, and keeps the
queue pointed at Packet D without reopening the reduced roots.
The later 2026-05-19 Packet D residual-ranking closeout then deploys
`IC-25C1F7B9E4DA`, reduces `tests/unit/test_search_service_ranking.py` to
`532` lines, moves source-filename ranking coverage into
`tests/unit/test_search_service_ranking_source_filename.py` at `158`, routes
the reduced search-service root as a deferred facade, moves the live counts to
`open=0`, `verified=0`, and `deployed=60`, and leaves Packet E as the only
remaining queued follow-on while `top_routed_hotspot_paths=[]` remains
unchanged. The later 2026-05-19 Packet E queue-exhaustion closeout then proves
those counts stayed closed, keeps `top_routed_hotspot_paths=[]`,
`blocked=0`, `exceptions=0`, and `violation_count=0`, and retires the
remaining packet queue with no new queued follow-on. Future work from this
broader brief now requires a fresh broader rebaseline rather than another
queued packet. The later 2026-05-19
`docs/agent_task_runtime_and_verification_boundary_milestone_plan.md`
closeout then resolves that first broader rebaseline packet, deploys
`IC-3F725D0A6C91` and `IC-86E1D4B72F0C`, and advances the live improvement-case
summary to `status_counts={"measured":1,"deployed":62}`. The later
`docs/hotspot_prevention_classifier_owner_rebaseline_milestone_plan.md`
closeout then resolves the next broader-reselect follow-on without forcing a
fake classifier split: `app/hotspot_prevention_classifier.py` stays at
`360 / 1`, the new self-hosting guard owner lives in
`app/hotspot_prevention_classifier_owner_rules.py` at `58 / 0`, the focused
classifier-family siblings are exact-ratcheted, and the live architecture-quality
summary returns to `top_routed_hotspot_paths=[]`. This broader coordination
brief is therefore back at the "fresh broader rebaseline before the next
packet" state rather than carrying an active routed classifier child packet.
That fresh broader-reselect packet then became
`docs/semantic_registry_owner_rebaseline_milestone_plan.md`, and the later
2026-05-19 semantic-registry closeout now deploys that split:
`app/services/semantic_registry.py` is reduced to a `31` line compatibility
facade over focused `400`, `85`, and `322` line contract, storage, and state
owners, `IC-0E4F1B9A2D73` is the current deployed owner case, hotspot
prevention routes the root as a compatibility-facade trap, the adjacent
semantic-owner diff slice stayed empty so no debt was transferred into preview,
ontology, candidate, graph, generation, or semantic-pass owners, and the live
routed queue remains honestly empty. The next broader-reselect packet then
became `docs/retrieval_learning_artifacts_owner_rebaseline_milestone_plan.md`,
and the later 2026-05-19 retrieval-learning closeout now deploys that split:
`app/services/retrieval_learning_artifacts.py` is reduced to a `129` line
compatibility facade over focused `20`, `181`, `228`, `59`, `232`, and `122`
line contracts, weights, impacts, governance, lifecycle, and views owners,
`IC-5F4E8C2B1A90` is the current deployed owner case, hotspot prevention routes
the root as a compatibility-facade trap, the adjacent retrieval-learning
consumer diff slice stayed empty so no debt was transferred into
`retrieval_learning.py`, `retrieval_learning_candidates.py`, the search
routers, CLI entrypoints, or integration support, and the live routed queue
remains honestly empty again. Future code-owning work from this broader brief
therefore requires another fresh broader rebaseline rather than a queued child
packet. The later 2026-05-20 hygiene-gate registry alignment sweep then
deploys `IC-20260424-hygiene-gate`, advances the then-live summary to
`status_counts={"deployed":66}`, keeps
`max_hotspot_risk_score=466.06`, and leaves
`top_routed_hotspot_paths=[]` so this coordination brief still points to a
fresh broader rebaseline rather than a hidden queued packet. The later
architecture-quality broader-rebaseline refresh is now committed locally as
`8b0ea812`; it adds
`broader_rebaseline_candidate_count=5` plus
`top_broader_rebaseline_paths=[app/services/search_retrieval_primitives.py, app/services/search_harnesses.py, app/cli_commands/search_harness.py, tests/unit/test_cli_search_harness.py, tests/unit/test_search_api_harnesses.py]`,
keeps `app/architecture_quality.py` at `522` lines by moving the shared
broader-rebaseline ranking logic into
`app/architecture_quality_support.py` at `202` lines, and keeps the next
honest packet on the search residual family instead of falling back to the
already-deployed facade traps. That broader-rebaseline refresh therefore
closes as part of the shared committed closeout state of the live checkout.
The later 2026-05-20 search span retrieval follow-on is now committed locally
as `0c007206`; it reduces `app/services/search_retrieval_primitives.py` to
`312` lines, moves span keyword/semantic plus late-interaction retrieval
ownership into `app/services/search_span_retrieval.py` at `378` lines, keeps
the search-harness and CLI/test residual owners unchanged at `627`, `604`,
`714`, and `764` lines, and advances the live broader rebaseline summary to
`broader_rebaseline_candidate_count=4` with
`top_broader_rebaseline_paths=[app/services/search_harnesses.py, app/cli_commands/search_harness.py, tests/unit/test_cli_search_harness.py, tests/unit/test_search_api_harnesses.py]`.
The later 2026-05-20 search-harness facade follow-on then reduces
`app/services/search_harnesses.py` to `82` lines, moves harness contracts,
registry, and reranking ownership into
`app/services/search_harness_contracts.py` at `79`,
`app/services/search_harness_reranker_config.py` at `29`,
`app/services/search_harness_registry.py` at `291`, and
`app/services/search_harness_reranking.py` at `203`, keeps the remaining
search CLI/test residual owners unchanged at `604`, `714`, and `764` lines,
and advances the live broader rebaseline summary to
`broader_rebaseline_candidate_count=3` with
`top_broader_rebaseline_paths=[app/cli_commands/search_harness.py, tests/unit/test_cli_search_harness.py, tests/unit/test_search_api_harnesses.py]`.
The later 2026-05-20 search-harness CLI facade follow-on then reduces
`app/cli_commands/search_harness.py` to `23` lines, moves shared parser
support plus retrieval-learning, evaluation/gate, and audit ownership into
`app/cli_commands/search_harness_support.py` at `84`,
`app/cli_commands/search_harness_learning.py` at `268`,
`app/cli_commands/search_harness_evaluations.py` at `176`, and
`app/cli_commands/search_harness_audit.py` at `111`, reduces
`tests/unit/test_cli_search_harness.py` to `18` lines with direct owner
coverage moved to focused `303`, `275`, and `152` line siblings, keeps
`tests/unit/test_search_api_harnesses.py` unchanged at `764` lines, and
advances the live broader rebaseline summary to
`broader_rebaseline_candidate_count=1` with
`top_broader_rebaseline_paths=[tests/unit/test_search_api_harnesses.py]`.
The new search-harness hotspot-prevention facade rule now lives in
`app/hotspot_prevention_classifier_search_rules.py` at `129` lines so the
shared `app/hotspot_prevention_classifier_service_rules.py` closes at `291`
lines; the dispatcher root only grows to `362` lines for route-map
maintenance, which avoids shifting the real search-harness classifier logic
back into the broader governance owners. The later 2026-05-20
hotspot-prevention policy-contract follow-on then closes the briefly reopened
test-family owner surface without reopening the broader queue: it reduces
`tests/unit/test_hotspot_prevention_policy_contracts.py` to `21` lines, moves
validation, report and CLI, diff collector, and packaging coverage into new
`164`, `123`, `40`, and `10` line siblings, grows shared support to `133`
lines, routes the reduced root under `IC-B1FD75CDA84F`, advances the then-live
summary to `status_counts={"deployed":66}`, and still leaves
`top_routed_hotspot_paths=[]` with
`top_broader_rebaseline_paths=[tests/unit/test_search_api_harnesses.py]`.
The later standalone search-harness cycle follow-on then moves the shared
`LinearRerankerConfig` seam into
`app/services/search_harness_reranker_config.py` at `29` lines, reduces
`app/services/search_harness_contracts.py` to `79`, keeps
`app/services/search_harness_reranking.py` at `203`, extends the reduced
search-harness facade routing and hygiene ratchets to the new shared owner,
and returns `architecture_probe.py --fail-on-cycles` to zero Python cycles
without changing the live broader queue beyond
`top_broader_rebaseline_paths=[tests/unit/test_search_api_harnesses.py]`.
The latest docs-only broader rerun then re-confirmed that unchanged live state
from fresh measurements, kept `top_routed_hotspot_paths=[]`,
`broader_rebaseline_candidate_count=1`, and
`top_broader_rebaseline_paths=[tests/unit/test_search_api_harnesses.py]`, and
records the selected next packet in
`docs/search_api_harness_route_surface_boundary_milestone_plan.md` so future
sessions do not restart from raw broader metrics alone.
The later 2026-05-20 search API harness route-surface follow-on then closes
that remaining broader candidate directly: implementation commit `e16f2b6c`
reduces `tests/unit/test_search_api_harnesses.py` to `40` lines, moves
definitions, evaluations, learning, and audit ownership into focused `81`,
`287`, `335`, and `248` line siblings, routes the reduced root under
`IC-5C9B1A4D7E2F`, exact-ratchets the focused family, and advances the live
summary to `status_counts={"deployed":67}`,
`broader_rebaseline_candidate_count=0`, and
`top_broader_rebaseline_paths=[]` without reopening the routed queue or
regrowing the reduced search-harness service or CLI facades.
The later governance gap-close then adds
`tests/unit/test_hotspot_prevention_search_api_harness_routes.py` plus the
matching hotspot-governance classifier support and hotspot-policy contract
fixture entries so the reduced harness root is protected by explicit
hotspot-regression coverage as well as the broader queue metrics.

## Purpose

Resolve the remaining "not yet boring to change" gap without collapsing the
post-closeout backlog back into one vague cleanup packet.

The current problem is different from the earlier 2026-05-15 pre-closeout
snapshot. Several large service packets that this plan originally waited on are
now closed locally, the app-side large-owner packet is resolved locally in the
working tree, and the immediate next execution choice is narrower again. The
remaining boring-change gap is now split across four different risks:

- future sessions can reopen already-closed facade packets if routing docs drift
  back to the raw hotspot list instead of the routed queue
- the live `>800` backlog is already zero, so the remaining work can still be
  misread if future sessions treat the cleared large-file queue as the whole
  boring-change backlog
- the next routed packet can drift stale if residual owner-family routing is
  not refreshed after each local closeout
- the raw architecture-quality hotspot list still contains some now-small
  facades, which means future sessions must treat `top_hotspot_paths` as
  measurement-only and `top_routed_hotspot_paths` as the operational queue

2026-05-18 update:

- the standalone cycle packet is now resolved locally and the live probe
  reports `0` Python cycle components
- the standalone agent-task residual owner-family packet is now also resolved
  locally with `app/services/agent_tasks.py` at `324` lines,
  `app/services/agent_actions/search_harness.py` at `444`,
  `app/services/agent_actions/semantic_governance_actions.py` at `565`, and
  `tests/integration/test_agent_task_triage_roundtrip.py` at `283`
- the standalone DB-model residual owner-family packet is now also resolved
  locally with `app/db/model_domains/audit_and_evidence.py`,
  `app/db/model_domains/semantic_memory.py`, and
  `app/db/model_domains/claim_support.py` at `31`, `53`, and `31` lines,
  plus narrowed shared DB-model roots at `457` and `472`
- `.github/workflows/architecture-governance.yml` now runs the repo-owned
  import-boundary gate
  `uv run pytest -q tests/unit/test_architecture_governance_imports.py tests/unit/test_python_cycle_imports.py`
- the evaluation and UI residual child packets are now both resolved locally
  with no governed evaluation or UI root above the default `600`-line budget,
  the large-file backlog later falls to `0` code files above `800`, the
  documents-service sink is then retired to a 49-line facade, the
  cross-cutting verification packet is now also durably resolved, the
  governance self-hosting packet is now also durably resolved, and the later
  hotspot-interpretation plus open-owner packets are now also resolved
  locally
- the routed claim-support residual test packet is now also resolved locally:
  the judge-roundtrip smoke root closes at `339` lines, focused family-local
  support closes at `13`, `277`, `344`, `75`, and `381`, replay-alert coverage
  now lives in a `152`-line sibling, replay-alert promotions closes at `510`,
  and the routed queue then advances to the technical-report harness packet
- the routed technical-report harness residual packet is now also resolved
  locally: the smoke root stays at `93` lines, family-local support stays at
  `396`, the focused context-pack surface stays at `315`, the audit family now
  closes at `398`, `313`, and `162`, integrity stays at `402`, source-evidence
  stays at `206`, and the routed queue then advanced to the hotspot-prevention
  residual test root
- the routed hotspot-prevention companion-test packet is now also resolved
  locally: the analyzer root closes at `343` lines, policy or report
  contract coverage now lives in a `317`-line sibling, blocked-family
  coverage remains at `318`, wrapper coverage remains at `296`, shared
  support remains at `50`, the focused family slice passed at `41 passed`,
  and the routed queue now returns to `IC-03D7EFA03213` /
  `tests/unit/test_search_api.py`
- the routed search API route-surface follow-on is now also resolved locally:
  implementation commit `f1f296d` reduces the residual root to `161` lines,
  request-history coverage now lives in a `152`-line sibling,
  evidence-package and trace coverage now live in a `137`-line sibling,
  replay and learning/audit siblings remain at `248` and `228`, the inherited
  harness owner remains unchanged at `764`, durable docs-and-registry
  closeout commit `8d7d316` records the deployed routed-facade state, and the routed
  queue now advances to `IC-D9A84C20546B` / `tests/unit/test_agent_tasks_api.py`
- the routed agent-tasks API lifecycle-family follow-on is now also resolved
  locally through implementation commit `790fa2d` plus durable
  docs-and-registry closeout commit `8ce05b7`: the residual root stays at
  `92` lines, analytics coverage now lives in a `360`-line sibling, artifacts
  and failure-artifact success coverage now live in a `566`-line sibling,
  lifecycle coverage now lives in a `360`-line sibling, claim-support and auth
  siblings remain at `419` and `93`, hotspot prevention now routes the root as
  a deferred reduced facade, and the routed queue now advances to
  `IC-DCEE88C7CA97` / `app/schemas/search.py`
- the routed search-schema facade follow-on is now also resolved locally
  through implementation commit `8b04845` plus durable docs-and-registry
  closeout commit `d85a3f4` for `IC-DCEE88C7CA97`:
  `app/schemas/search.py` now closes at `36` lines over focused core, history,
  explanations, replay, harness, and learning owners at `83`, `77`, `77`,
  `100`, `220`, and `280` lines, `50` app importers intentionally remain on
  the shared public path, hotspot prevention now routes the reduced root as a
  deferred reduced facade, and the routed queue now advances to
  `IC-7D8AE7C83B8F` / `tests/unit/test_db_model_import_compatibility.py`
- the routed DB-model residual owner-family packet is now also durably
  recorded through closeout commit `b9b3e46`: the extracted
  `audit_and_evidence.py`, `semantic_memory.py`, and `claim_support.py`
  composition roots now close at `31`, `53`, and `31` lines, the shared unit
  and integration roots now close at `457` and `472` lines, and the routed
  queue must now be reselected from the live post-closeout summary rather than
  from the stale pre-closeout DB-model selection
- the 2026-05-19 queue-honesty refresh now records
  `IC-5B6430FCB929` / `app/api/main.py` as deployed through `d8841fd`, routes
  `tests/unit/test_db_model_import_compatibility.py`,
  `app/services/audit_bundles.py`, and `app/api/main.py` off the active queue,
  and leaves the live routed queue ready for the architecture-inspection
  follow-on instead of any deployed surface
- the later 2026-05-19 architecture-inspection test-surface closeout then
  routes `tests/unit/test_architecture_inspection.py` off the active queue and
  leaves `["app/api/routers/agent_tasks.py"]` as the honest next routed owner
- the later 2026-05-19 agent-tasks route-surface closeout then reduces
  `app/api/routers/agent_tasks.py` to a `94` line composition surface over
  focused lifecycle and artifacts routers at `198` and `287` lines, preserves
  the parent-module test seam through `service_from_parent(...)`, and advances
  the live routed queue to
  `["tests/integration/test_retrieval_learning_ledger.py"]`
- the later 2026-05-19 governance closeout for the same packet records
  `IC-17B0E2F64A9C` as deployed, routes the reduced route root as a deferred
  facade in `config/hotspot_prevention.yaml`, exact-ratchets the three router
  files in `config/hygiene_policy.yaml`, and keeps the live queue on
  `tests/integration/test_retrieval_learning_ledger.py` instead of silently
  reopening the agent-task route family
- the later 2026-05-19 retrieval-learning residual-smoke closeout then routes
  `tests/integration/test_retrieval_learning_ledger.py` as a deferred reduced
  facade, routes `tests/integration/retrieval_learning_ledger_support.py` as
  an accepted residual boundary, exact-ratchets the focused dataset,
  candidate, and integrity siblings at `413`, `597`, and `599`, adds focused
  hotspot-prevention route coverage in
  `tests/unit/test_hotspot_prevention_retrieval_learning_routes.py` at `69`
  lines so the guardrail does not regrow the governed hotspot test roots, and
  leaves the live `top_routed_hotspot_paths` queue empty instead of pretending
  the already-split retrieval-learning family is still the next code-owning
  packet

This refreshed plan coordinates the remaining work by preserving the locally
closed app-side packet, routing the remaining test, UI, and nonselected app
backlog through narrower follow-on packets, preserving the now-zero-cycle
state, advancing the next routed packet to a live post-closeout broader
reselect once a fresh owner is chosen, and finishing with a
checked-in boring-change gate that fails on both cycles and oversized code
files.

## Current Evidence

Historical Milestone 0 routing evidence captured from the local checkout on
2026-05-16 local / 2026-05-16 UTC before the later cycle, agent-task
residual, and DB-model residual closeouts:

```text
git status -sb
  ## main...origin/main [ahead 16]
   M app/services/evidence_claim_support_replay_alerts.py
   M app/services/evidence_audit_views.py
   M app/services/evidence_manifests.py
   M app/services/evidence_manifest_traces.py
   M app/services/evidence_semantic_trace.py
   M config/hygiene_policy.yaml
   M config/improvement_cases.yaml
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
   M docs/boring_change_architecture_milestone_plan.md
   M docs/evidence_residual_owner_family_milestone_plan.md
  ?? app/services/evidence_audit_views_bundle.py
  ?? app/services/evidence_audit_views_context.py
  ?? app/services/evidence_audit_views_payloads.py
  ?? app/services/evidence_audit_views_release_readiness.py
  ?? app/services/evidence_claim_support_replay_alert_corpus.py
  ?? app/services/evidence_manifest_payloads.py
  ?? app/services/evidence_manifest_trace_assembly.py
  ?? app/services/evidence_manifest_trace_graph.py
  ?? app/services/evidence_manifest_trace_replay.py
  ?? app/services/evidence_semantic_trace_integrity.py
  ?? app/services/evidence_semantic_trace_payloads.py
  ?? app/services/evidence_semantic_trace_provenance.py
  ?? app/services/evidence_semantic_trace_source_records.py
  ?? docs/app_large_owner_modules_resolution_milestone_plan.md
  ?? docs/evidence_claim_support_replay_alerts_boundary_milestone_plan.md
  ?? docs/evidence_manifest_owner_boundary_milestone_plan.md
  ?? docs/evidence_manifest_trace_graph_boundary_milestone_plan.md
  ?? docs/semantic_residual_owner_family_milestone_plan.md

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  legibility_gap_count=0
  hotspot_count=20
  max_hotspot_risk_score=486.06
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/agent_task_actions.py,
    app/services/evidence.py,
    app/schemas/agent_tasks.py
  ]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  27 code files exceed 800 lines
  largest code files include:
    tests/unit/test_evaluation_fixtures.py = 1506
    app/ui/modules/agents.js = 1300
    tests/integration/test_agent_task_triage_roundtrip.py = 1279
    tests/unit/test_agent_task_verifications.py = 1197
    tests/integration/test_postgres_roundtrip.py = 1132
    app/services/agent_task_context_semantic_governance.py = 1126
    app/services/semantic_orchestration.py = 1092
    tests/unit/test_docling_parser.py = 1080
    app/services/agent_actions/search_harness.py = 1078
    app/services/technical_reports.py = 1075
    app/db/model_domains/audit_and_evidence.py = 1053
    tests/unit/test_agent_tasks.py = 1011
    app/db/model_domains/semantic_memory.py = 979
    app/services/evaluation_fixtures.py = 966
    app/services/eval_workbench.py = 952
    app/services/agent_actions/semantic_governance_actions.py = 943
    app/ui/modules/shared.js = 930
    app/services/audit_bundle_training_runs.py = 917
    app/services/evaluation_scoring.py = 897
    app/services/improvement_cases.py = 876
  top hotspots include:
    app/services/agent_tasks.py = 30264
    tests/integration/test_agent_task_triage_roundtrip.py = 26859
    app/cli.py = 21375
    tests/integration/test_postgres_roundtrip.py = 18112
    app/services/technical_reports.py = 17200
  Python cycle components:
    app.services.search,
    app.services.search_execution_persistence,
    app.services.search_harnesses,
    app.services.search_hydration,
    app.services.search_metadata_supplement,
    app.services.search_retrieval_primitives
    app.services.evidence_provenance_export_graph_core,
    app.services.evidence_provenance_export_graph_report
    app.services.evidence_search_packages,
    app.services.evidence_search_trace_store

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt still includes:
    app/services/semantic_generation_brief.py = 644 lines under IC-6F4E2B5A91C3
    app/services/semantic_graph_core.py = 697 lines under IC-C8D41A2F77BE
    app/services/semantic_graph_promotions.py = 718 lines under IC-C8D41A2F77BE
    app/services/agent_actions/search_harness.py = 1078 lines under IC-A1E186A34097
    app/services/agent_task_context_semantic_governance.py = 1126 lines under IC-E52B6C7B22FD
  hotspot-prevention family no longer appears in inherited budget debt after
  the Milestone 1 closeout; the root and focused sibling owners are now all
  exact-ratcheted under IC-6C1B516A3F92 and IC-15F6E41A9C77, and both owner
  cases are now recorded as deployed locally through `463d3fc`. The residual
  root test is also marked as a deferred reduced facade in
  `config/hotspot_prevention.yaml`, so the routed queue stays on the broader
  backlog instead of reopening the just-closed packet.
  no evidence owner-family module remains in inherited budget debt after the
  replay-alert follow-on; broader `IC-65AF4A6D8B1E` routing now remains open
  only as a historical staging note from the pre-closeout draft, while the
  later 2026-05-19 stale-open registry closeout now records the broader
  evidence-family case as deployed and leaves the broader coordination brief
  needing one fresh next bounded packet

uv run docling-system-improvement-case-summary
  case_count=49
  status_counts.open=33
  status_counts.deployed=15
  status_counts.measured=1
```

Repo-current structural evidence:

- `docs/SESSION_HANDOFF.md` now names this file as the active coordination
  brief, `docs/hotspot_prevention_family_boundary_milestone_plan.md` as the
  latest resolved bounded implementation brief, and the semantic lifecycle/read
  packet as the prior resolved semantic follow-on. Immediate follow-on
  planning should therefore remeasure the refreshed backlog and activate one
  new bounded packet instead of reopening the just-closed hotspot-prevention
  family.
- `docs/agentic_architecture_index.md` already records the search,
  claim-support, evaluations, evidence-provenance, semantics, runtime-health,
  and CI parity packets as closed locally. This plan must not reopen those
  packets just because their historical hotspot names still appear in older
  narratives.
- Milestone 1 now resolves the hotspot-prevention family locally: the
  classifier root is `360 / 1`, the companion test root is `595 / 0`, the
  family no longer appears in the `>800`-line backlog, and the broader brief
  can now choose the next packet from a cleaner baseline.
- The app-side large-owner service packet in
  `docs/app_large_owner_modules_resolution_milestone_plan.md`:
  `semantic_graph.py`, `docling_parser.py`, `quality.py`,
  `semantic_candidates.py`, `semantic_generation.py`,
  `semantic_governance.py`, and `runs.py` is now resolved locally in the
  working tree and should be treated as an earlier resolved app-side packet,
  not as the next immediate routing target or the latest resolved bounded
  follow-on.
- `docs/semantic_residual_owner_family_milestone_plan.md` is no longer an
  honest ready-to-execute packet because it predates the app large owner
  closeout that reduced `semantic_governance.py` to `39` lines. The resolved
  lifecycle/read follow-on now lives in
  `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`, so the old
  three-owner draft is historical context only.
- The broader backlog still includes remaining nonselected code-file offenders
  that should not be forgotten after the current hotspot-prevention family
  packet closes,
  including
  `app/ui/modules/agents.js`,
  `app/ui/modules/shared.js`,
  `app/services/semantic_orchestration.py`,
  `app/services/technical_reports.py`,
  `app/services/evaluation_fixtures.py`,
  `app/services/evaluation_scoring.py`,
  `app/services/audit_bundle_training_runs.py`,
  `app/services/improvement_cases.py`, and the remaining test monolith
  backlog. The exact queue must now be refreshed from the current `17`-file
  `>800` baseline rather than from the earlier pre-closeout DB-model list.
- The raw hotspot summary still lists `app/db/models.py`,
  `app/services/agent_task_actions.py`, `app/cli.py`,
  `app/schemas/agent_tasks.py`, and `app/services/evidence.py`, but the routed
  summary now suppresses those paths from `top_routed_hotspot_paths` and
  records them in `routing_trap_paths`. Future packet selection should use the
  routed queue rather than the raw list.
- The standalone cycle backlog packet is now also resolved locally and the live
  probe reports `0` Python cycle components. Future cycle work should stay
  attached to the checked-in regression gate from
  `docs/python_cycle_backlog_elimination_milestone_plan.md` instead of
  widening this umbrella brief again.

## Goal

Resolve the remaining boring-change gap so that:

- the active bounded packet routing stays aligned with the live backlog
- the app-side large-owner packet is closed or explicitly superseded by a
  fresher narrow packet
- every remaining `>800`-line code file is either resolved or governed by a
  narrow, durable owner packet instead of this umbrella brief
- the architecture probe reports `0` Python cycle components
- already-reduced compatibility facades stay small and do not re-accumulate
  moved implementation ownership
- the final checked-in boring-change gate fails on both code files above `800`
  lines and on Python cycles

The finish line for this plan is not "the backlog feels smaller." The finish
line is a repo where current routing is accurate, code-file size and cycle debt
are mechanically gated, and future sessions no longer have an excuse to reopen
the wrong files.

## Non-Goals

- No microservice extraction or platform rewrite.
- No reopening of the closed search, claim-support, evaluations,
  evidence-provenance, semantics, runtime-health, or CI parity packets unless a
  fresh baseline proves real regrowth inside one of those exact owner surfaces.
- No threshold increase above the current architecture-probe `800`-line gate.
- No repo-wide forced move to the default `600`-line hygiene budget in this
  sequence.
- No test weakening, skip broadening, xfail broadening, fixture deletion, or
  assertion loosening to make size reduction or cycle cleanup appear green.
- No hiding cycle debt behind local-import tricks, dynamic imports, or other
  patterns that evade the static graph while preserving the same coupling.
- No using this broad plan as permission to mix unrelated app, test, UI, and
  workflow work into one giant implementation milestone.

## Scope

In scope:

- Milestone 0 live freshness and routing rebaseline
- preserving the locally resolved state of
  `docs/app_large_owner_modules_resolution_milestone_plan.md`
- continued use and eventual closeout of the current active next packet,
  `docs/residual_large_file_backlog_milestone_plan.md`, plus the closeout-state
  coordination follow-on
  `docs/closeout_state_queue_alignment_milestone_plan.md`
- new or updated bounded routing for the remaining nonselected app, UI, and
  test large-owner backlog
- preservation of the now-zero Python cycle state through the checked-in cycle
  regression gate
- a checked-in boring-change gate around
  `architecture_probe.py --fail-on-cycles --max-file-lines 800`
- final source-of-truth alignment across the active plan, handoff, index, and
  any workflow or gate docs touched by the closeout

Out of scope:

- product-feature work unrelated to the selected owner families
- redoing already-closed facade splits just because their historical owner case
  stays visible in old docs
- pushing all inherited `601-800`-line owner files under the default `600`
  hygiene budget during this sequence
- broad UI redesign work beyond the specific large-file reduction needed for
  `app/ui/modules/agents.js` if it still remains above `800`

## Owner Surfaces

- coordination and routing docs:
  `docs/boring_change_architecture_milestone_plan.md`,
  `docs/app_large_owner_modules_resolution_milestone_plan.md`,
  `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`,
  `docs/evidence_claim_support_replay_alerts_boundary_milestone_plan.md`,
  `docs/evidence_residual_owner_family_milestone_plan.md`,
  `docs/semantic_residual_owner_family_milestone_plan.md`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  and any new narrower follow-on plan created from Milestone 0 evidence
- gate and owner routing artifacts:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`,
  `.github/workflows/architecture-governance.yml`,
  `.github/workflows/release-gate-parity.yml`,
  and any repo-owned wrapper command used to run the final boring-change gate
- current active next packet candidate:
  `docs/residual_large_file_backlog_milestone_plan.md`,
  `docs/closeout_state_queue_alignment_milestone_plan.md`,
  `docs/cross_cutting_large_file_residual_milestone_plan.md`,
  `docs/SESSION_HANDOFF.md`,
  and `docs/agentic_architecture_index.md`
- latest locally resolved packet that must stay closed:
  `app/services/semantic_pass_lifecycle.py`,
  `app/services/semantic_pass_artifacts.py`,
  `app/services/semantic_pass_reviews.py`,
  `app/services/semantic_pass_reads.py`,
  `app/services/semantic_pass_source_records.py`,
  and `app/services/semantic_registry_preview.py`
- earlier locally resolved packet that must stay closed:
  `app/services/semantic_graph.py`,
  `app/services/docling_parser.py`,
  `app/services/quality.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_generation.py`,
  `app/services/semantic_governance.py`,
  and `app/services/runs.py`
- remaining nonselected code-file backlog that must be re-measured after the
  hotspot-prevention family packet closes:
  `app/ui/modules/agents.js`,
  `app/services/agent_task_context_semantic_governance.py`,
  `app/services/semantic_orchestration.py`,
  `app/services/agent_actions/search_harness.py`,
  `app/services/technical_reports.py`,
  `app/db/model_domains/audit_and_evidence.py`,
  and any other code file still above `800` on a fresh post-milestone baseline
- remaining test-monolith backlog after the active hotspot-prevention packet:
  `tests/unit/test_evaluation_fixtures.py`,
  `tests/integration/test_agent_task_triage_roundtrip.py`,
  `tests/unit/test_agent_task_verifications.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/unit/test_agent_tasks.py`,
  `tests/unit/test_docling_parser.py`,
  and any fresh `>800` test file still present after Milestone 1
- live cycle-owner families:
  `app.services.chat`,
  `app.services.search`,
  `app.services.search_execution_persistence`,
  `app.services.search_harnesses`,
  `app.services.search_hydration`,
  `app.services.search_metadata_supplement`,
  `app.services.search_retrieval_primitives`,
  `app.services.evidence_provenance_export_graph_core`,
  `app.services.evidence_provenance_export_graph_report`,
  `app.services.evidence_search_packages`,
  and `app.services.evidence_search_trace_store`

## Placement Rules

- Treat this document as a coordination brief, not a license to code directly
  against every surface named here. New implementation should land in the
  narrow packet that actually owns the chosen slice.
- Do not regrow already-shrunk compatibility facades:
  `app/db/models.py`,
  `app/services/evidence.py`,
  `app/services/retrieval_learning.py`,
  `app/services/search.py`,
  `app/services/claim_support_policy_impacts.py`,
  `app/services/evaluations.py`,
  and `app/services/semantics.py`.
- New code extracted from the current app-side packet belongs in focused owner
  siblings near the touched family, not in already-large adjacent files such as
  `semantic_orchestration.py`, `technical_reports.py`, or `agents.js` unless
  one of those files is the explicitly selected owner for its own packet.
- New code extracted from large tests belongs in focused helper fixtures,
  support modules, or smaller sibling tests. Do not "solve" one test monolith
  by moving broad setup logic into another already-large test file.
- Cycle elimination must prefer explicit contract, lookup, or data-shaping
  seams over import tricks that only hide the same coupling.
- If a new owner module closes between `601` and `800` lines, route it in
  `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` in the same
  milestone instead of leaving it as unowned inherited debt.
- Reuse the checked-in architecture and release-gate workflows instead of
  creating parallel one-off CI paths for this closeout.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Routing stays stale and future work reopens closed facade packets. | this plan, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md` | milestone-start review against `git status -sb`, handoff, index, architecture probe, and improvement-case summary | Any active follow-on in the handoff disagrees with the index or this plan, or a closed packet is routed as active work again | Intentionally point Milestone 0 back at `search.py` or `claim_support_policy_impacts.py` and confirm review rejects the stale route | A future session sees old hotspot prose and starts coding in a now-small facade |
| This umbrella brief swallows the narrower active packet and turns into another giant mixed-scope implementation. | this plan, `docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`, `docs/evidence_claim_support_replay_alerts_boundary_milestone_plan.md`, and any new follow-on plan | staged diff review, milestone packet lint, owner-case review in `config/improvement_cases.yaml` | A milestone touches unrelated app, test, UI, and cycle families without a narrower owner packet | Intentionally add both test-monolith and semantic lifecycle/read implementation to the same milestone and confirm closeout blocks it | A future session uses the umbrella plan as permission to fix "whatever looks large" |
| Size reduction just moves debt into another already-large sibling. | touched owner files, `config/hygiene_policy.yaml`, architecture probe, hotspot prevention config | `python .../architecture_probe.py --format markdown --top 20`, `--max-file-lines 800`, `uv run docling-system-hygiene-check`, and focused `wc -l` review | Any touched sibling grows above its recorded ceiling or a new `>800` file appears without explicit routing | Temporarily move code from `semantic_generation.py` into `semantic_orchestration.py` or from one large test into another and confirm the milestone would fail | A future session minimizes the primary file by overflowing a nearby owner |
| Cycle cleanup passes only because imports were disguised, not because coupling was removed. | cycle-owner families and architecture gate workflows | `python .../architecture_probe.py --fail-on-cycles`, route-contract checks, focused import-boundary tests | The cycle disappears only by using local imports, import-time side effects, or circular runtime calls that the static graph no longer sees | Replace a direct import with a function-local import and confirm review rejects the fake fix | A future session hides the dependency instead of creating a real seam |
| Test-monolith reduction weakens behavioral coverage. | selected test packet, focused source tests, integration suite | focused `pytest` slices, DB-backed integration where required, and final `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` closeout | Assertions, fixtures, or negative coverage get weaker than the pre-split contract | Remove a key failure-path assertion while shrinking a large test and confirm coverage review blocks the change | A future session optimizes for fewer lines instead of preserving the contract |
| Final boring-change gate drifts from the repo's actual workflows. | architecture workflow, release-gate workflow, repo-owned wrapper commands, docs | `uv run docling-system-architecture-quality-report --summary`, `uv run docling-system-improvement-case-validate`, workflow review, and final gate run | Local closeout relies on a command or threshold not represented in checked-in workflows or docs | Add a local-only final command without updating workflows/docs and confirm closeout rejects the mismatch | A future session claims the repo is "boring to change" but CI does not enforce the same rule |

## Milestone Sequence

### Milestone 0 - Freshness And Routing Lock

Outcome label: reduced

Refresh the live baseline and lock the immediate next packet before any new
implementation starts. Local status: resolved locally in the current checkout;
the refreshed baseline now promotes
`docs/hotspot_prevention_family_boundary_milestone_plan.md` as the immediate
next bounded packet and treats the semantic lifecycle/read packet as the latest
resolved bounded implementation brief.

Required work:

- rerun `git status -sb`
- rerun `uv run docling-system-architecture-quality-report --summary`
- rerun `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- rerun `uv run docling-system-hygiene-check`
- rerun `uv run docling-system-improvement-case-summary`
- rerun `uv run docling-system-improvement-case-validate`
- confirm that `docs/app_large_owner_modules_resolution_milestone_plan.md`
  remains a closed local packet and that
  `docs/hotspot_prevention_family_boundary_milestone_plan.md` is the
  immediate next packet
- mark any older draft that is no longer current, including
  `docs/semantic_residual_owner_family_milestone_plan.md`, as needing
  explicit supersession before use
- refresh this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` if the routing changed
- enumerate every remaining `>800`-line code file and every cycle component
  into one of three buckets:
  closed and no longer active, already owned by a narrower packet, or needing a
  new narrower packet

Acceptance criteria:

- the handoff, architecture index, and this plan all name the same immediate
  next bounded packet
- every remaining `>800` code file and every cycle component has explicit owner
  routing
- no closed search, claim-support, evaluations, semantics, runtime-health, or
  CI parity packet is reopened by stale prose alone

### Milestone 1 - Hotspot Prevention Family Boundary

Outcome label: reduced

Close the current hotspot-prevention family packet or replace it with a
strictly fresher equivalent if the Milestone 0 baseline changed.
Local status: resolved locally in the current checkout.

Required work:

- implement `docs/hotspot_prevention_family_boundary_milestone_plan.md`
- keep its classifier/test owner-case routing, support-family seams, and final
  verification intact
- rerun the freshness commands from Milestone 0 after the packet closes
- refresh this coordination brief to remove any files that the standalone
  packet resolved and to highlight the next remaining large-file or cycle slice

Acceptance criteria:

- the hotspot-prevention family packet and its adjacent broader routing are
  resolved or honestly rerouted according to that plan's own acceptance
  criteria or are rerouted through a fresher narrow packet with equal or
  stronger gates
- the architecture probe remains at `0` cycle components after the packet
  closes
- no newly created owner file exceeds `800` lines without same-milestone owner
  routing

### Milestone 2 - Remaining Large-Owner Routing And Reduction

Outcome label: reduced

Reduce the remaining code-file backlog one narrow owner packet at a time after
the hotspot-prevention family packet lands.

Required work:

- draft and execute the next narrow packet for whichever live backlog remains
  highest leverage after Milestone 1
- expect the first candidates to be:
  - `docs/residual_large_file_backlog_milestone_plan.md` covering the
    remaining `17` code files above `800` lines across evaluation, UI,
    semantic/report, service, and cross-cutting test owners
  - `docs/closeout_state_queue_alignment_milestone_plan.md` to align the
    resolved-local child packet closeout and retire the stale
    `docs/shared_verification_roots_milestone_plan.md` branch before the next
    code-owning packet resumes
  - a broader residual test-large-owner packet covering
    `tests/unit/test_evaluation_fixtures.py`,
    `tests/unit/test_agent_task_verifications.py`,
    `tests/integration/test_postgres_roundtrip.py`,
    `tests/unit/test_docling_parser.py`, and any fresh `>800` test siblings
  - an app or UI residual packet covering
    `app/ui/modules/agents.js`,
    `app/services/agent_task_context_semantic_governance.py`,
    `app/services/semantic_orchestration.py`,
    `app/services/agent_actions/search_harness.py`,
    `app/services/technical_reports.py`,
    `app/db/model_domains/audit_and_evidence.py`, and any fresh nonselected app
    owners still above `800`
- keep only one narrow packet active at a time unless two packets have clearly
  disjoint owner surfaces and verification stacks

Acceptance criteria:

- every post-Milestone-1 `>800` code file belongs to a closed or active bounded
  packet with durable owner routing
- the count of `>800` code files never increases relative to the fresh baseline
  at the start of the selected packet
- no packet widens itself just to absorb leftover debt from unrelated owner
  families

### Milestone 3 - Cycle Backlog Elimination

Outcome label: reduced

Keep the already-eliminated Python cycle backlog at zero without hiding the same
coupling behind import tricks.

Required work:

- remove the search compatibility-family cycle spanning:
  `chat`, `search`, `search_execution_persistence`, `search_harnesses`,
  `search_hydration`, `search_metadata_supplement`, and
  `search_retrieval_primitives`
- remove the evidence-provenance export graph cycle spanning
  `evidence_provenance_export_graph_core` and
  `evidence_provenance_export_graph_report`
- remove the evidence-search packages / trace-store cycle spanning
  `evidence_search_packages` and `evidence_search_trace_store`
- route cycle work through any still-open narrower packet if a cycle member is
  already actively owned elsewhere

Acceptance criteria:

- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles` reports `0` cycle components
- no new `>800` code file or hotspot-prevention regression is introduced while
  cutting the cycles
- the closeout proves the cycle was removed by an explicit seam, not by a
  function-local import workaround

### Milestone 4 - Durable Boring-Change Gate And Source-Of-Truth Closeout

Outcome label: resolved

Finish the boring-change sequence by making the final state mechanically
enforced and durably documented.

Required work:

- wire a repo-owned final gate around
  `architecture_probe.py --fail-on-cycles --max-file-lines 800`
- align the gate with the checked-in architecture and release workflows instead
  of inventing a separate local-only closeout path
- update this plan, `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and any touched workflow or gate docs
  so the final routed backlog matches live repo state

Acceptance criteria:

- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles --max-file-lines 800` passes
- `uv run docling-system-hygiene-check` reports `new hygiene regressions: none`
- `uv run docling-system-improvement-case-validate` returns `valid=true`
- `uv run docling-system-architecture-quality-report --summary` remains green
  and does not show a new hotspot path created by the closeout itself
- this plan can be marked resolved because there are no remaining Python cycle
  components, no code files above `800` lines, and no stale routing pointing at
  already-closed packets

## Required Implementation Artifacts

- refreshed `docs/boring_change_architecture_milestone_plan.md`
- active bounded packet docs, starting with
  `docs/residual_large_file_backlog_milestone_plan.md`
- the latest resolved bounded packet record,
  `docs/hotspot_routing_trap_resolution_milestone_plan.md`, so the routed
  governance closeout does not drift back into the active queue
- the latest locally resolved packet record,
  `docs/app_large_owner_modules_resolution_milestone_plan.md`, so its closed
  state does not drift back into the active queue
- any new narrow follow-on plan created from Milestone 0 evidence, such as a
  test-large-owner packet or cycle-specific packet
- same-milestone updates to `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`, and `config/hotspot_prevention.yaml` whenever a
  new owner is introduced or rerouted
- focused source, test, and support-module changes for each narrow packet
- checked-in workflow or wrapper updates needed to enforce the final
  boring-change gate

## Required Documentation And Handoff Updates

- update this plan whenever Milestone 0 changes the active routed backlog
- update `docs/SESSION_HANDOFF.md` at the closeout of every bounded packet that
  changes the next active routing
- update `docs/agentic_architecture_index.md` whenever a packet becomes closed,
  a new narrower packet is drafted, or a residual route changes
- update `SYSTEM_PLAN.md` or other durable overview docs only if the final
  closeout leaves them materially stale against the live routed backlog or the
  enforced gate commands

## Required Verification Gates

- docs-only Milestone 0 refresh:
  `git diff --check`
- every routing refresh:
  `uv run docling-system-architecture-quality-report --summary`
- every routing refresh:
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- every packet closeout:
  `uv run docling-system-hygiene-check`
- every packet closeout:
  `uv run docling-system-improvement-case-summary`
- every packet closeout:
  `uv run docling-system-improvement-case-validate`
- every packet that touches hotspot-prevention policy:
  `uv run pytest -q tests/unit/test_hotspot_prevention.py`
- every cycle milestone:
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`
- final plan closeout:
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles --max-file-lines 800`
- every app, parser, runtime, or DB-backed implementation milestone:
  focused `ruff`, focused unit tests, and
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` according to the
  narrower packet's repo-specific verification rules

## Acceptance Criteria

- the current repo docs agree that
  `docs/hotspot_prevention_family_boundary_milestone_plan.md` is the latest
  resolved bounded packet, this document is the active coordination brief, and
  the next bounded packet must be selected from a fresh post-closeout baseline
- every live `>800`-line code file is either resolved or owned by a closed or
  active bounded packet with explicit improvement-case routing
- every live Python cycle component is either eliminated or, before final
  closeout, owned by a bounded packet that is actively being executed next
- already-closed facades such as `app/services/search.py`,
  `app/services/claim_support_policy_impacts.py`,
  `app/services/evaluations.py`, `app/services/semantics.py`,
  `app/services/evidence.py`, and `app/db/models.py` do not reacquire broad
  implementation ownership
- the final boring-change gate passes with zero cycle components and zero code
  files above `800` lines

## Stop Conditions

- Stop and rerun Milestone 0 if a just-closed bounded packet materially changes
  the largest-file or cycle baseline.
- Stop and draft a new narrower plan if the next slice does not have a clear
  single-family owner boundary.
- Stop if a proposed reduction depends on test weakening, threshold increases,
  local-import cycle hiding, or moving debt into another already-large file.
- Stop and split out a dedicated gate packet if enforcing the final boring
  change gate would otherwise require broad unrelated workflow rewrites.

## Local Commit Closeout Policy

- Milestone 0 is a docs-and-routing refresh. If committed, stage only the plan,
  handoff, index, and any directly affected routing docs.
- Every implementation milestone after Milestone 0 must close as an atomic
  commit from the narrower bounded packet, including code, tests, owner routing,
  generated artifacts, and docs or handoff updates for that milestone only.
- This umbrella brief is not complete just because a narrower packet is green.
  It is complete only when the final boring-change gate, the routing docs, and
  the relevant bounded packets all close together under the final resolved
  state.

## Residual Risks And Next Milestone Routing

- The hotspot-prevention family packet is now closed locally.
- The residual large-file parent packet now has Milestone 0 plus the
  evaluation, UI, semantic/report, cross-cutting, and queue-alignment packets
  resolved locally. The documents-service packet, the cross-cutting
  verification packet, and the governance self-hosting packet are now also
  durably resolved, and the next active code-owning packet must now be
  reselected from this broader brief rather than from the cleared large-file
  queue.
- The live `top_routed_hotspot_paths` queue is now empty after the
  retrieval-learning residual-smoke closeout; the stale deployed
  `tests/unit/test_db_model_import_compatibility.py` root, the deployed
  `app/services/audit_bundles.py` facade, the accepted residual
  `app/api/main.py` bootstrap root, the reduced
  `tests/unit/test_architecture_inspection.py` smoke root, the reduced
  `app/api/routers/agent_tasks.py` route root, and the routed
  retrieval-learning residual smoke root are no longer active queue entries.
- The reduced `app/api/routers/agent_tasks.py` route root is now explicitly
  guarded as a deferred reduced facade with exact hygiene ratchets on the new
  lifecycle and artifact routers, so this closeout no longer depends on docs
  alone to keep the split from regrowing in the wrong file.
- The reduced retrieval-learning smoke root and its family-local support module
  are now also explicitly governed, so the broader queue no longer confuses a
  deployed residual test family with the next code-owning implementation
  packet.
- The reduced `tests/unit/test_documents_api.py` route root is now also
  explicitly governed as a deferred reduced facade with exact hygiene ratchets
  on its focused access, runs, evaluations, artifact, and semantic siblings,
  so the fresh broader reselect no longer leaves one unresolved test hotspot
  behind from the earlier high-value paydown split.
- The remaining routing traps after the current refresh are small but still
  high-churn facades such as `app/db/models.py`, `app/services/evidence.py`,
  `app/cli.py`, `app/schemas/agent_tasks.py`, and `app/services/agent_tasks.py`.
  They are now explicitly recorded in `routing_trap_paths` and should stay
  governed by their existing owner cases unless live regrowth appears.
- Re-measure the large-file queue after each child-packet closeout instead of
  assuming the current ordering will hold. The parent backlog now routes
  directly to the next reselected under-budget packet and leaves
  `docs/shared_verification_roots_milestone_plan.md` historical unless a later
  explicit rebaseline selects it again.

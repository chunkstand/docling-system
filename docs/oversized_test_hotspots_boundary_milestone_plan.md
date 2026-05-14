# Oversized Test Hotspots Boundary Milestone Plan

Date: 2026-05-14 local / 2026-05-14 UTC
Status: resolved locally in the 2026-05-14 oversized-test closeout window
after the Milestone 0 refresh; the scoped oversized-test hotspot issue is
closed, the broader owner cases now remain explicitly `deployed` or
`reduced/open` from refreshed evidence, and the next bounded follow-on routes
to `docs/hygiene_owner_case_routing_boundary_milestone_plan.md`
Owner context: closeout under `IC-5F0E1C8B0D42`,
`IC-3B4C9F2A76E1`, `IC-D9A84C20546B`, `IC-7A628A4CBCAC`,
`IC-25C1F7B9E4DA`, `IC-908E7A1D2C44`, and `IC-D49E037D5657`.
Milestone 0 refreshed the post-schema state, Milestones 1 through 6 reduced
or retired the selected test surfaces, and the next follow-on is hygiene
owner-case routing rather than another oversized-test umbrella.

## Local Closeout

Milestones 0 through 6 are resolved locally in the 2026-05-14 oversized-test
closeout window. The scoped oversized-test knot is closed: all seven selected
residual files now sit below their packet thresholds, the architecture probe no
longer lists any of the selected residual files among the top 20 hotspots, and
the remaining broad follow-on debt is routed explicitly instead of being left
as an unlabeled oversized-test bucket.

Local closeout results:

- reduced `tests/db_model_contract.py` from `3700` lines to `159` and moved the
  shared ORM contract families into `tests/db_model_contract_domains/`, where
  the extracted domain files now top out at `588` lines
- reduced `tests/unit/test_agent_task_context.py` to `328` lines and moved the
  freshness, reports and claim-support, semantic-generation,
  semantic-governance, semantic-graph, and semantic-graph promotion scenarios
  into focused files; the broader owner case remains reduced and open because
  three focused successors still measure `636`, `630`, and `653` lines against
  the default `600`-line hygiene budget
- reduced `tests/unit/test_agent_tasks_api.py` to `92` lines and moved the
  claim-support, lifecycle, artifacts, and auth or capability route families
  into focused files; the broader owner case remains reduced and open because
  `tests/unit/test_agent_tasks_api_lifecycle.py` still measures `756` lines
- confirmed `tests/unit/test_evaluation_service.py` was already down to
  `389` lines at the Milestone 0 refresh after the earlier evaluation-owner
  splits, so no new decomposition was required and the owner case remains
  deployed
- reduced `tests/unit/test_search_service.py` to `117` lines and moved
  metadata supplement, ranking, orchestration, and persistence assertions into
  focused files; the broader owner case remains reduced and open because
  `tests/unit/test_search_service_ranking.py` still measures `621` lines
- reduced `tests/integration/test_retrieval_learning_ledger.py` to `428` lines
  and `tests/integration/test_technical_report_harness_roundtrip.py` to
  `93` lines, added family-local support modules at `362` and `396` lines, and
  moved the scenario families into focused integration files; the
  retrieval-learning owner case is now deployed, while the broader
  technical-report owner case remains reduced and open because the audit
  surface still measures `799` lines
- updated hotspot-prevention, hygiene, and improvement-case routing so the four
  previously unowned hotspots now have explicit owner cases and exact residual
  budgets, while the next bounded implementation brief now routes to
  `docs/hygiene_owner_case_routing_boundary_milestone_plan.md`

Local closeout verification:

- `git diff --check`: pass
- `uv run ruff check app/hotspot_prevention_classifier.py app/hotspot_prevention_classifier_support.py tests/db_model_contract.py tests/db_model_contract_domains tests/integration/test_db_model_metadata.py tests/unit/test_db_model_import_compatibility.py tests/unit/test_db_models_facade_contract.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_context_*.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_tasks_api_*.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_cli_agent_tasks.py tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_search_service.py tests/unit/test_search_hydration.py tests/unit/test_search_execution_persistence.py tests/unit/test_search_execution_orchestration.py tests/unit/test_search_metadata_supplement.py tests/unit/test_search_service_ranking.py tests/unit/test_search_service_orchestration.py tests/unit/test_search_service_persistence.py tests/integration/test_retrieval_learning_ledger.py tests/integration/retrieval_learning_ledger_support.py tests/integration/test_retrieval_learning_ledger_*.py tests/integration/test_technical_report_harness_roundtrip.py tests/integration/technical_report_harness_support.py tests/integration/test_technical_report_harness_*.py tests/unit/test_hotspot_prevention.py config/improvement_cases.yaml config/hygiene_policy.yaml config/hotspot_prevention.yaml`: pass
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py tests/unit/test_db_models_facade_contract.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_context_*.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_tasks_api_*.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_cli_agent_tasks.py tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_search_service.py tests/unit/test_search_hydration.py tests/unit/test_search_execution_persistence.py tests/unit/test_search_execution_orchestration.py tests/unit/test_search_metadata_supplement.py tests/unit/test_search_service_ranking.py tests/unit/test_search_service_orchestration.py tests/unit/test_search_service_persistence.py tests/unit/test_hotspot_prevention.py`: `741 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py tests/integration/test_retrieval_learning_ledger.py tests/integration/retrieval_learning_ledger_support.py tests/integration/test_retrieval_learning_ledger_*.py tests/integration/test_technical_report_harness_roundtrip.py tests/integration/test_technical_report_harness_*.py tests/integration/test_semantic_governance_ledger.py`: `339 passed`
- `uv run docling-system-hotspot-prevention-check --strict`: `known_hotspots=21`, `changed_hotspots=6`, `blocked=0`, `allowed=39`, `exceptions=2`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-validate`: `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=33`, `status_counts.open=22`, `status_counts.deployed=10`, `status_counts.measured=1`, `measured_case_count=28`, `oldest_open_case_id=IC-9812A0B138D9`
- `uv run docling-system-architecture-quality-report --summary`: `agent_legibility_average_score=90.0`, `broad_facade_count=2`, `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`: top hotspot remains `app/services/search.py`; none of the seven selected residual files remain in the top 20 hotspot list; Python cycle components=`5`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1957 passed`

## Purpose

Resolve the remaining oversized test hotspots that still make the system costly
to review and easy for future sessions to misuse:

- `tests/db_model_contract.py`
- `tests/unit/test_agent_task_context.py`
- `tests/integration/test_retrieval_learning_ledger.py`
- `tests/integration/test_technical_report_harness_roundtrip.py`
- `tests/unit/test_evaluation_service.py`
- `tests/unit/test_search_service.py`
- `tests/unit/test_agent_tasks_api.py`

The scoped problem is not just raw line count. These files currently mix
multiple concern families in the same test surface:

- shared contract manifest plus multi-domain DB expectations
- registry or compatibility assertions plus many owner-family scenarios
- route smoke coverage plus route-family detail and error-path assertions
- end-to-end integration smoke plus lineage, integrity, audit, and tamper
  scenarios

This plan resolves that scoped knot by decomposing each selected hotspot into
focused owner-family or scenario-family test files, preserving a thin
compatibility or smoke surface where one still adds value, and explicitly
forbidding the work from being "solved" by moving everything into a new
generic helper sink, `conftest.py` sprawl, or another oversized support file.

## Current Evidence

Milestone 0 refresh baseline captured from the local checkout on 2026-05-13
local / 2026-05-13 UTC before the owner-case bootstrap and file decomposition:

```text
git status -sb
  ## main...origin/main [ahead 11]
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
  ?? docs/agent_task_schema_aggregation_boundary_milestone_plan.md
  ?? docs/cli_command_dispatch_boundary_milestone_plan.md

wc -l tests/db_model_contract.py tests/unit/test_agent_task_context.py tests/integration/test_retrieval_learning_ledger.py tests/integration/test_technical_report_harness_roundtrip.py tests/unit/test_evaluation_service.py tests/unit/test_search_service.py tests/unit/test_agent_tasks_api.py
   3700 tests/db_model_contract.py
   2972 tests/unit/test_agent_task_context.py
   2339 tests/integration/test_retrieval_learning_ledger.py
   2030 tests/integration/test_technical_report_harness_roundtrip.py
   2237 tests/unit/test_evaluation_service.py
   1845 tests/unit/test_search_service.py
   1810 tests/unit/test_agent_tasks_api.py

uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=531.06
  top_hotspot_paths=[
    app/db/models.py,
    app/services/agent_task_actions.py,
    app/cli.py,
    app/schemas/agent_tasks.py,
    app/services/evidence.py
  ]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Largest files include:
    tests/db_model_contract.py = 3700
    tests/unit/test_agent_task_context.py = 2972
    tests/integration/test_retrieval_learning_ledger.py = 2339
    tests/unit/test_evaluation_service.py = 2237
    tests/integration/test_technical_report_harness_roundtrip.py = 2030
    tests/unit/test_search_service.py = 1845
    tests/unit/test_agent_tasks_api.py = 1810
  Hotspots include:
    tests/unit/test_agent_tasks_api.py score = 66970
    tests/integration/test_technical_report_harness_roundtrip.py score = 64960
    tests/db_model_contract.py score = 55500
    tests/unit/test_evaluation_service.py score = 51451
    tests/integration/test_retrieval_learning_ledger.py score = 44441
    tests/unit/test_search_service.py score = 33210
    tests/unit/test_agent_task_context.py score = 29720
  Suggested gate: --max-file-lines 800

uv run docling-system-improvement-case-summary
  case_count=28
  status_counts.open=21
  status_counts.deployed=6
  status_counts.measured=1

uv run docling-system-hygiene-check
  inherited budget debt listed for app/ only
  new hygiene regressions: none

rg tests target paths in config/improvement_cases.yaml
  explicit owner cases already exist for:
    tests/unit/test_agent_tasks_api.py -> IC-D9A84C20546B
    tests/unit/test_evaluation_service.py -> IC-7A628A4CBCAC
    tests/integration/test_technical_report_harness_roundtrip.py -> IC-D49E037D5657
  no dedicated owner case currently exists for:
    tests/db_model_contract.py
    tests/unit/test_agent_task_context.py
    tests/integration/test_retrieval_learning_ledger.py
    tests/unit/test_search_service.py

rg tests target paths in config/hotspot_prevention.yaml
  no dedicated hotspot-prevention entries currently exist for the selected
  seven test files
```

Repo-current structural evidence:

- `tests/db_model_contract.py` is not a normal test module. It is the shared
  ORM contract manifest imported by
  `tests/integration/test_db_model_metadata.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/unit/test_db_models_facade_contract.py`. Its size comes from
  multi-domain public-surface and table/index/constraint manifests, not from a
  single scenario family.
- `tests/unit/test_agent_task_context.py` currently mixes registry-composition
  assertions, freshness refresh, dependency-output error handling, and many
  semantic, graph, ontology, technical-report, search-harness, and
  claim-support builder scenarios in one file.
- `tests/integration/test_retrieval_learning_ledger.py` currently mixes replay
  alert corpus lineage, claim-feedback lineage, candidate evaluation, reranker
  artifact creation, audit-bundle tamper detection, stale-bundle refresh, and
  dataset roundtrip coverage in one file.
- `tests/integration/test_technical_report_harness_roundtrip.py` currently
  contains one oversized end-to-end scenario plus many local helper builders,
  which means provenance, readiness, audit-bundle, context-pack, and
  immutability coverage all rise and fall together.
- `tests/unit/test_evaluation_service.py` mixes fixture loading, fixture
  generation, auto-fixture persistence, evaluate-run orchestration, structural
  checks, retrieval scoring, and answer-case scoring in one file.
- `tests/unit/test_search_service.py` mixes query-shape helpers, metadata
  supplement logic, ranking behavior, hybrid merge logic, keyword fallback, and
  end-to-end `execute_search(...)` behavior in one file even after the search
  service owner splits.
- `tests/unit/test_agent_tasks_api.py` mixes claim-support routes, task
  lifecycle, artifact and provenance routes, structured error paths, and
  capability/auth behavior in one file even though the prior claim-support and
  evidence packets already route those code families separately.
- The broader coordination packet
  `docs/boring_change_architecture_milestone_plan.md` already names the
  remaining test backlog, but it is intentionally broader than this user
  request. This plan creates the dedicated owner-level packet for the selected
  seven files so the later boring-change packet can consume a narrowed
  post-closeout state instead of owning these splits directly.

## Goal

Resolve the scoped oversized-test debt so that:

- each selected hotspot is decomposed into focused owner-family or
  scenario-family test files
- each residual compatibility or smoke surface is narrow and governed rather
  than remaining a scenario sink
- every selected test file and every new focused file created by this packet is
  at or below `800` lines after closeout
- residual unit or contract compatibility surfaces close at or below `600`
  lines unless a documented integration smoke exception is explicitly accepted
- the four currently unowned test hotspots gain explicit improvement-case
  routing before code motion spreads
- hotspot prevention and hygiene ratchets make the new test boundaries
  executable
- the scoped decomposition issue is `resolved` when the selected seven files
  are no longer oversized multi-family hotspots
- the broader owner cases remain `reduced` unless refreshed live architecture
  evidence proves full hotspot retirement

## Non-Goals

- No production service refactor beyond import or test-surface updates already
  required by the earlier queued packets.
- No test weakening, skip broadening, fixture deletion, xfail broadening, or
  reduced assertion depth just to make smaller files pass.
- No new generic `tests/helpers.py`, cross-repo `tests/support.py`, or broad
  `conftest.py` sink that re-aggregates the same debt.
- No broad rewrite of unrelated large tests outside the selected seven files.
- No attempt to re-open already reduced test families such as
  `tests/unit/test_search_api.py`,
  `tests/unit/test_agent_task_actions.py`, or
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
  unless Milestone 0 proves they regressed again.

## Scope

In scope:

- Milestone 0 stacked-state refresh after the six prior queued packets close
- missing owner-case bootstrap for the four currently unowned test hotspots
- focused decomposition of the seven selected test hotspots
- narrow compatibility or smoke residuals for the original filenames where they
  still add value
- hotspot-prevention and hygiene ratchets for the residual compatibility
  surfaces
- closeout updates for docs, handoff, improvement cases, and hygiene policy

Out of scope:

- generic test-framework cleanup across the whole repo
- moving production logic into test helpers
- introducing a new shared test utility layer used by unrelated domains
- large-file cleanup for later-stack test surfaces not named in this packet

## Owner Surfaces

- shared ORM contract surface:
  `tests/db_model_contract.py`,
  `tests/integration/test_db_model_metadata.py`,
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/unit/test_db_models_facade_contract.py`
- agent-task context and route surfaces:
  `tests/unit/test_agent_task_context.py`,
  `tests/unit/test_agent_tasks_api.py`,
  `tests/unit/test_agent_tasks.py`,
  `tests/unit/test_agent_task_worker.py`,
  `tests/unit/test_agent_action_contracts.py`,
  `tests/unit/test_cli_agent_tasks.py`
- search and evaluations unit surfaces:
  `tests/unit/test_evaluation_service.py`,
  `tests/unit/test_search_service.py`,
  `tests/unit/test_search_hydration.py`,
  `tests/unit/test_search_execution_persistence.py`,
  `tests/unit/test_search_execution_orchestration.py`
- integration ledger and technical-report roundtrip surfaces:
  `tests/integration/test_retrieval_learning_ledger.py`,
  `tests/integration/test_technical_report_harness_roundtrip.py`,
  `tests/integration/test_semantic_governance_ledger.py`
- prior owner packets whose focused tests must be reused rather than duplicated:
  `docs/evaluations_service_boundary_milestone_plan.md`,
  `docs/evidence_provenance_exports_boundary_milestone_plan.md`,
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
  `docs/search_execution_persistence_boundary_milestone_plan.md`,
  `docs/search_execution_orchestration_boundary_milestone_plan.md`,
  `docs/agent_task_schema_aggregation_boundary_milestone_plan.md`
- governance and routing surfaces:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `tests/unit/test_hotspot_prevention.py`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- Keep the original seven filenames only as thin compatibility, registry, or
  smoke surfaces after closeout. They must not remain the default place for new
  scenario coverage.
- New focused tests must mirror real owner families or scenario families, not
  vague buckets like `test_misc.py`, `test_more_routes.py`, or
  `test_regressions.py`.
- `tests/db_model_contract.py` may shrink into a shared manifest or index, but
  its extracted pieces must mirror the real model-domain ownership. Do not move
  its content into a single second sink such as
  `tests/db_model_contract_support.py`.
- If support extraction is truly necessary for integration families, allow at
  most one local support module per family:
  `tests/integration/retrieval_learning_ledger_support.py` and
  `tests/integration/technical_report_harness_support.py`.
  Do not create a generic support layer reused across unrelated families.
- New route-family tests for `tests/unit/test_agent_tasks_api.py` belong in
  focused files such as
  `tests/unit/test_agent_tasks_api_claim_support.py`,
  `tests/unit/test_agent_tasks_api_artifacts.py`,
  `tests/unit/test_agent_tasks_api_lifecycle.py`, and
  `tests/unit/test_agent_tasks_api_auth.py`.
- New owner-family tests for `tests/unit/test_agent_task_context.py` belong in
  focused files such as
  `tests/unit/test_agent_task_context_registry.py`,
  `tests/unit/test_agent_task_context_freshness.py`,
  `tests/unit/test_agent_task_context_semantic_generation.py`,
  `tests/unit/test_agent_task_context_semantic_graph.py`, and
  `tests/unit/test_agent_task_context_reports_claim_support.py`.
- New evaluation-family tests must align to the earlier planned owner surfaces
  `tests/unit/test_evaluation_fixtures.py`,
  `tests/unit/test_evaluation_scoring.py`, and
  `tests/unit/test_evaluation_reads.py` rather than growing
  `tests/unit/test_evaluation_service.py`.
- New search-family tests must align to the earlier search owner surfaces and
  any residual query-feature or ranking files, not grow
  `tests/unit/test_search_service.py`.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The split only replaces one monolith with a new generic helper sink. | `tests/`, `conftest.py`, any new `*_support.py`, `config/hotspot_prevention.yaml`, `tests/unit/test_hotspot_prevention.py` | hotspot-prevention rules plus `wc -l` review in closeout | A new generic cross-family support file or `conftest.py` growth becomes the real owner of unrelated scenario setup | Add a temporary `tests/helpers.py` or broad `conftest.py` helper for multiple families and confirm the gate or closeout review fails | A future session moves shared fixtures into one convenient support file until it becomes the next hotspot |
| The original hotspot files stay large because new scenarios keep landing in them during the split. | the original seven hotspot files, architecture probe, `wc -l` readback | targeted unit or integration suites plus line-count readback and architecture probe | Any selected original file remains above its closeout budget or grows while new focused files are added | Add a temporary new scenario test to one residual compatibility file and confirm the no-growth rule or line-budget review fails | A future session keeps using the old filename because imports and fixtures are already there |
| Assertions are weakened or scenarios are dropped to make decomposition easier. | touched test families, targeted suites, final full pytest run | focused pytest commands, `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`, and diff review for skips or xfails | any skip, xfail, assertion deletion, or narrower contract coverage replaces the prior behavior without stronger equivalent coverage | Remove one tamper, provenance, or structured-error assertion and confirm the relevant focused suite fails | A future session claims the split is done because the file is smaller even though failure-path coverage got thinner |
| Four of the seven hotspots remain unowned in the improvement-case register, so future routing stays ambiguous. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, docs routing | `uv run docling-system-improvement-case-validate` plus routing doc review | Any selected hotspot lacks an explicit owner case or an exact closeout route | Leave `tests/unit/test_search_service.py` or `tests/db_model_contract.py` without a case and confirm the milestone does not pass closeout review | A future session treats these tests as incidental verification surfaces instead of owner-managed debt |
| Decomposition fights the earlier owner packets and duplicates tests they already introduced. | new focused test files, prior packet test files, targeted pytest suites | packet-aligned targeted suites plus duplicate-surface review | new tests duplicate an existing owner test instead of narrowing the residual compatibility surface | Re-add already split claim-support or evidence assertions to `tests/unit/test_agent_tasks_api.py` and confirm the review or focused suite fails | A future session forgets prior packet routing and recreates the same route coverage in the legacy file |

Accepted residual risk after closeout: some residual compatibility or smoke
files may still appear in hotspot rankings because of churn or central import
fan-in even after they fall below the size thresholds. If that happens, keep
their owner cases open as `reduced` and route only the remaining narrow issue
from fresh post-closeout evidence.

## Milestone Sequence

This plan is intentionally stacked behind the current claim-support,
evaluations, evidence provenance-export, semantics, CLI, and agent-task schema
packets. Milestone 0 is mandatory and must run before any test decomposition
starts.

### Milestone 0 - Post-Schema System-State Refresh

Status: resolved locally in the 2026-05-14 oversized-test closeout window
Outcome label: `resolved`

Purpose:

- convert the current repo state from "six earlier packets drafted or in
  flight" into the fresh baseline used by this plan
- promote this test-hotspot plan to the active bounded follow-on only after the
  six prior packets are actually complete

Implementation:

- confirm
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
  `docs/evaluations_service_boundary_milestone_plan.md`,
  `docs/evidence_provenance_exports_boundary_milestone_plan.md`,
  `docs/semantics_service_boundary_milestone_plan.md`,
  `docs/cli_command_dispatch_boundary_milestone_plan.md`, and
  `docs/agent_task_schema_aggregation_boundary_milestone_plan.md`
  each have real closeout commits recorded and are no longer merely drafted
- rerun live test-hotspot evidence after those closeouts:
  `git status -sb`,
  `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-improvement-case-summary`,
  `uv run docling-system-hygiene-check`,
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`,
  and `wc -l` for the seven selected test files
- refresh this plan's evidence section if the earlier closeouts already shrank,
  rerouted, or replaced any of the selected files
- update `docs/SESSION_HANDOFF.md` and `docs/agentic_architecture_index.md` so
  this plan becomes the active bounded implementation brief

Acceptance:

- all six prior packets are complete, verified, and committed locally before
  test decomposition begins
- the seven selected files still represent the active oversized test-hotspot
  debt or the plan is rewritten before code motion starts
- this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` reflect the refreshed post-stack state

### Milestone 1 - Owner-Case And Gate Bootstrap

Status: resolved locally in the 2026-05-14 oversized-test closeout window
Outcome label: `resolved`

Implementation:

- create explicit improvement cases for the currently unowned hotspots:
  `tests/db_model_contract.py`,
  `tests/unit/test_agent_task_context.py`,
  `tests/integration/test_retrieval_learning_ledger.py`, and
  `tests/unit/test_search_service.py`
- keep the existing owner cases for
  `tests/unit/test_agent_tasks_api.py`,
  `tests/unit/test_evaluation_service.py`, and
  `tests/integration/test_technical_report_harness_roundtrip.py`; do not
  replace them with a new broad umbrella case
- add hotspot-prevention entries for the residual compatibility or smoke files
  and the allowed support-module pattern
- add or tighten hygiene entries so the residual compatibility surfaces have
  exact closeout budgets and owner_case_id routing
- extend `tests/unit/test_hotspot_prevention.py` with controlled violations for
  generic helper sinks and no-growth residual compatibility files

Acceptance:

- all seven selected hotspot files have explicit owner routing by the end of
  the milestone
- hotspot prevention can block generic helper-sink growth and residual
  compatibility-file regrowth
- closeout docs name the owner cases precisely rather than referring to
  "remaining large tests" in the abstract

### Milestone 2 - Shared ORM Contract Harness Decomposition

Status: reduced locally in the 2026-05-14 oversized-test closeout window
Outcome label: `reduced`

Implementation:

- reduce `tests/db_model_contract.py` to a narrow shared contract manifest or
  index
- extract domain-specific contract data into a bounded
  `tests/db_model_contract_domains/` owner family that mirrors the actual model
  domains instead of one second sink file
- preserve `tests/unit/test_db_model_import_compatibility.py`,
  `tests/unit/test_db_models_facade_contract.py`, and
  `tests/integration/test_db_model_metadata.py` as the consuming contract
  surfaces
- keep public contract counts, table names, index names, unique constraints,
  computed SQL, and domain surface expectations under equivalent or stronger
  coverage

Acceptance:

- `tests/db_model_contract.py` closes at `<= 600` lines
- every extracted domain manifest aligns to a real model-domain owner
- the consuming DB model compatibility and metadata suites remain green without
  weaker assertions

### Milestone 3 - Agent-Task Test Family Decomposition

Status: reduced locally in the 2026-05-14 oversized-test closeout window
Outcome label: `reduced`

Implementation:

- reduce `tests/unit/test_agent_task_context.py` to a thin registry or
  compatibility surface by moving freshness, semantic-generation,
  semantic-graph, ontology, technical-report, search-harness, and
  claim-support scenarios into focused owner-family files
- reduce `tests/unit/test_agent_tasks_api.py` to a thin route compatibility
  surface by moving claim-support, artifacts and provenance, lifecycle, and
  auth or capability scenarios into focused route-family files
- reuse the earlier claim-support, evidence provenance, agent-task schema, and
  agent-task orchestration owner packets rather than duplicating their focused
  assertions in the residual files

Acceptance:

- `tests/unit/test_agent_task_context.py` closes at `<= 600` lines
- `tests/unit/test_agent_tasks_api.py` closes at `<= 600` lines
- all moved context-builder and route-family assertions land in explicit
  focused files rather than one new second hotspot
- targeted agent-task suites remain behavior-stable

### Milestone 4 - Evaluations And Search Unit Test Decomposition

Status: reduced locally in the 2026-05-14 oversized-test closeout window
Outcome label: `reduced`

Implementation:

- align the residual evaluation unit coverage to the earlier evaluation owner
  split by moving fixture, scoring, and latest-read scenarios into
  `tests/unit/test_evaluation_fixtures.py`,
  `tests/unit/test_evaluation_scoring.py`, and
  `tests/unit/test_evaluation_reads.py`
- reduce `tests/unit/test_evaluation_service.py` to a narrow compatibility or
  orchestration surface that only keeps the assertions not already owned by the
  focused files
- align the residual search unit coverage to the earlier search owner splits by
  moving query-feature, ranking, and remaining owner-family assertions into
  focused search files while preserving the existing
  `tests/unit/test_search_hydration.py`,
  `tests/unit/test_search_execution_persistence.py`, and
  `tests/unit/test_search_execution_orchestration.py`
- reduce `tests/unit/test_search_service.py` to a narrow compatibility surface
  for the public search facade behavior that still belongs there

Acceptance:

- `tests/unit/test_evaluation_service.py` closes at `<= 600` lines
- `tests/unit/test_search_service.py` closes at `<= 600` lines
- focused owner-family tests exist for moved evaluation and search assertions
- the residual compatibility files no longer blend multiple unrelated owner
  families

### Milestone 5 - Retrieval-Learning And Technical-Report Integration Decomposition

Status: resolved locally for the scoped integration-monolith issue in the
2026-05-14 oversized-test closeout window; broader owner routing is now
`deployed` for retrieval-learning and `reduced/open` for technical-report
Outcome label: `resolved` for the scoped integration-monolith issue and
`reduced` for the broader owner cases unless live hotspot routing fully retires

Implementation:

- reduce `tests/integration/test_retrieval_learning_ledger.py` by splitting
  dataset lineage, candidate and artifact creation, and audit-bundle or tamper
  scenarios into focused integration files, with at most one local support
  module for that family
- reduce `tests/integration/test_technical_report_harness_roundtrip.py` by
  splitting context-pack, release-readiness, provenance or immutability, and
  audit-bundle scenarios into focused integration files, with at most one local
  support module for that family
- keep one thin end-to-end smoke or compatibility roundtrip surface in each
  original filename if it still adds value after the split

Acceptance:

- `tests/integration/test_retrieval_learning_ledger.py` closes at `<= 800`
  lines
- `tests/integration/test_technical_report_harness_roundtrip.py` closes at
  `<= 800` lines
- no new integration support file exceeds `<= 400` lines or `<= 10` private
  helpers
- tamper, lineage, audit, provenance, and readiness assertions remain under
  equivalent or stronger focused coverage

### Milestone 6 - Closeout, Ratchets, And Residual Routing

Status: reduced locally in the 2026-05-14 oversized-test closeout window
Outcome label: `reduced`

Implementation:

- update `config/improvement_cases.yaml` with refreshed measurements and
  `resolved` or `reduced` language for all seven selected test hotspots
- update `config/hygiene_policy.yaml` with exact verified budgets for the
  residual compatibility or smoke files and any new bounded support files
- refresh `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  this plan with the closeout hash, verification commands, and post-closeout
  routing
- stage only the verified test-hotspot milestone slice and close with one local
  atomic commit

Acceptance:

- every selected file and every new focused file created by this packet is at
  or below `800` lines
- every residual unit or contract compatibility surface is at or below `600`
  lines unless a documented integration smoke exception is explicitly accepted
- all required verification gates below pass in the same closeout window
- the scoped oversized-test issue is recorded as resolved in this plan even if
  some broader owner cases remain `reduced`

## Required Implementation Artifacts

- updated residual compatibility or smoke files for all seven selected targets
- focused owner-family or scenario-family replacement test files for the moved
  coverage
- `tests/db_model_contract_domains/` domain-aligned contract family
- at most one local support file for retrieval-learning integration and at most
  one local support file for technical-report harness integration
- updated hotspot-prevention policy and classifier
- updated `tests/unit/test_hotspot_prevention.py`
- updated improvement-case and hygiene registers

## Required Documentation And Handoff Updates

- update this plan with actual closeout status, evidence, and residual routing
- update `docs/SESSION_HANDOFF.md` so the active plan and next routed follow-on
  are accurate after closeout
- update `docs/agentic_architecture_index.md` so the compact architecture queue
  reflects the verified post-closeout state
- update `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` in
  the same commit as the implementation and tests

## Required Verification Gates

- `git diff --check`
- `uv run ruff check tests/db_model_contract.py tests/db_model_contract_domains tests/integration/test_db_model_metadata.py tests/unit/test_db_model_import_compatibility.py tests/unit/test_db_models_facade_contract.py tests/unit/test_agent_task_context.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_cli_agent_tasks.py tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_search_service.py tests/unit/test_search_hydration.py tests/unit/test_search_execution_persistence.py tests/unit/test_search_execution_orchestration.py tests/integration/test_retrieval_learning_ledger.py tests/integration/test_technical_report_harness_roundtrip.py tests/unit/test_hotspot_prevention.py config/improvement_cases.yaml config/hygiene_policy.yaml config/hotspot_prevention.yaml app/hotspot_prevention_classifier.py`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py tests/unit/test_db_models_facade_contract.py tests/unit/test_agent_task_context.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_cli_agent_tasks.py tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_search_service.py tests/unit/test_search_hydration.py tests/unit/test_search_execution_persistence.py tests/unit/test_search_execution_orchestration.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py tests/integration/test_retrieval_learning_ledger.py tests/integration/test_technical_report_harness_roundtrip.py tests/integration/test_semantic_governance_ledger.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

Equivalent or broader contract coverage is required. Do not weaken tests, add
skips, narrow gates, or move assertions out of the failure path just to make
verification pass.

## Acceptance Criteria

- None of the seven selected test files remain oversized multi-family hotspots.
- Each moved assertion family lands in a focused owner-family or scenario-family
  file rather than in a new generic helper sink.
- The four previously unowned test hotspots have explicit improvement-case
  routing and closeout measurements.
- Every selected file and every new focused test file created by this packet is
  at or below `800` lines.
- Residual unit or contract compatibility surfaces are at or below `600`
  lines unless the plan records a specific accepted integration-smoke
  exception.
- The focused and full verification stack remains equivalent or stronger than
  before the split.

## Stop Conditions

- If Milestone 0 shows any of the six earlier queued packets are incomplete,
  unverified, or rerouted, stop and refresh this plan before implementation.
- If the decomposition requires a new generic helper sink or broad `conftest.py`
  growth to remain manageable, stop and rewrite the approach instead of
  shifting the debt.
- If a selected test file has already been decomposed by an earlier packet and
  this plan's assumed owner files no longer exist, stop and rebaseline the
  packet rather than duplicating the split.
- If any focused replacement only passes by removing negative coverage, tamper
  coverage, or structured-error assertions, do not close the milestone.

## Local Commit Closeout Policy

- Close this milestone with one local atomic commit after all required gates
  pass.
- Include tests, governance config, this plan, and the updated handoff and
  architecture index in that same commit.
- Stage only the verified test-hotspot slice. Do not include unrelated dirty
  worktree changes from other owner packets.
- Mark the implementation complete only after the commit exists locally and the
  closeout docs record the actual verification commands and results.

## Residual Risks And Next Milestone Routing

If any residual compatibility or smoke file still appears in the architecture
probe after it falls below the size thresholds, keep its owner case open as
`reduced` and route only the remaining narrow issue from fresh post-closeout
evidence. The most likely next routed follow-ons after a real closeout are:

- additional post-stack large-test cleanup from
  `docs/boring_change_architecture_milestone_plan.md`
- any still-open owner-service hotspots that the narrowed test files continue
  to exercise heavily

Choose the next packet only after the refreshed post-closeout architecture
summary, improvement-case summary, and line-count evidence are recorded in the
handoff.

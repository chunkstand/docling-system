# Evaluations Service Boundary Milestone Plan

Date: 2026-05-13 local / 2026-05-13 UTC
Status: drafted on 2026-05-13 as a stacked follow-on after
`docs/search_execution_orchestration_boundary_milestone_plan.md` and
`docs/claim_support_policy_impacts_boundary_milestone_plan.md`; do not start
implementation until both prior packets close locally
Owner context: queued follow-on under `IC-BF180637814C` /
`app/services/evaluations.py`. This plan assumes the current search execution
orchestration packet completes first, the queued claim-support boundary packet
completes second, and Milestone 0 then refreshes the live system state before
any evaluation-service code moves.

## Purpose

Resolve the mixed-responsibility debt that remains in
`app/services/evaluations.py` after the earlier helper extractions into
`app/services/evaluation_execution.py` and
`app/services/evaluation_fixture_cache.py`.

The scoped problem is not only file size. The remaining service still owns
multiple distinct concern families in one place:

- fixture loading and fixture matching
- auto-fixture generation and persistence
- retrieval and answer scoring
- structural evaluation checks
- run orchestration and row lifecycle
- latest-evaluation summary/detail reads

This plan resolves that scoped knot behind the existing compatibility facade by
splitting fixture ownership, scoring ownership, and latest-read ownership into
three focused owner modules, while explicitly forbidding the work from
spilling into `app/services/eval_workbench.py`, `app/services/documents.py`,
`app/services/search_harness_evaluations.py`, or into a spray of extra
`evaluation_*` files.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-13
local / 2026-05-13 UTC:

```text
git status -sb
  ## main...origin/main [ahead 8]
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
  ?? docs/claim_support_policy_impacts_boundary_milestone_plan.md
  ?? docs/evaluations_service_boundary_milestone_plan.md
  ?? docs/search_execution_orchestration_boundary_milestone_plan.md

wc -l app/services/evaluations.py tests/unit/test_evaluation_service.py app/services/evaluation_execution.py app/services/evaluation_fixture_cache.py app/services/eval_workbench.py app/services/search_harness_evaluations.py app/services/documents.py
  2159 app/services/evaluations.py
  2237 tests/unit/test_evaluation_service.py
   226 app/services/evaluation_execution.py
    34 app/services/evaluation_fixture_cache.py
   952 app/services/eval_workbench.py
   342 app/services/search_harness_evaluations.py
   822 app/services/documents.py

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

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 15
  tests/unit/test_evaluation_service.py: 23 revisions, 2237 lines, score 51451
  app/services/evaluations.py: 20 revisions, 2159 lines, score 43180
  Python cycle component includes:
    app.services.chat,
    app.services.documents,
    app.services.evaluations,
    app.services.runs,
    app.services.search,
    app.services.search_execution_persistence,
    app.services.search_hydration,
    app.services.semantics

config/improvement_cases.yaml
  IC-BF180637814C remains open for app/services/evaluations.py
  observed_failure=line_count=2159, changes_90d=20, risk_score=227.64

config/hygiene_policy.yaml
  app/services/evaluations.py currently allows max_lines=2161 and
  max_private_helpers=61 with no owner-case ratchet
```

Repo-current structural evidence:

- `docs/search_execution_orchestration_boundary_milestone_plan.md`,
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`, and this
  evaluation follow-on are all still drafted in the worktree. The active
  execution packet remains the search orchestration plan, with the
  claim-support split queued behind it. This evaluation plan must therefore
  begin with a system-state refresh after both prior milestones complete and
  are committed.
- `app/services/evaluations.py` still groups the main concern families together:
  `load_evaluation_fixtures(...)`,
  `fixture_for_document(...)`,
  `build_auto_evaluation_fixture_document(...)`,
  `ensure_auto_evaluation_fixture(...)`,
  `_evaluate_retrieval_case(...)`,
  `_evaluate_answer_case(...)`,
  `_summarize_structural_checks(...)`,
  `evaluate_run(...)`,
  `get_latest_evaluation_summary(...)`,
  `get_latest_evaluations_by_run_id(...)`,
  `get_latest_evaluation_summaries(...)`, and
  `get_latest_document_evaluation(...)`.
- The service already depends on partial owner seams that this milestone should
  preserve rather than bypass:
  `app/services/evaluation_execution.py` owns batch execution and query-row
  persistence, and `app/services/evaluation_fixture_cache.py` owns cached
  corpus-document loading.
- Public and near-public callers currently depend on the `app.services.evaluations`
  facade for multiple identities:
  `app/services/runs.py`,
  `app/services/evaluation_corpus_runner.py`,
  `app/services/quality.py`,
  `app/services/semantic_backfill.py`,
  `app/services/evaluation_embedding_cache.py`,
  `app/services/knowledge_base_reset.py`,
  `app/services/documents.py`,
  `app/services/capabilities/evaluation.py`, and `app/cli.py`.
- `app/services/documents.py` exposes the externally reachable latest-evaluation
  route family through `get_latest_document_evaluation_detail(...)`, and
  `/documents/{document_id}/evaluations/latest` plus
  `/documents/{document_id}/evaluations/latest/explain` must remain stable.
- Current direct unit coverage is itself a hotspot:
  `tests/unit/test_evaluation_service.py` is `2237` lines and a separate open
  owner case (`IC-7A628A4CBCAC`). This milestone must not solve the service
  hotspot by pushing more coverage into that test file.
- `config/hotspot_prevention.yaml` does not currently govern
  `app/services/evaluations.py`, so future growth is not blocked by the same
  facade-prevention workflow already used for search, evidence, and agent-task
  hotspots.
- Adjacent evaluation-family files are already large enough that they must not
  absorb this debt:
  `app/services/eval_workbench.py` is `952` lines and
  `app/services/documents.py` is `822` lines. `app/services/evaluation_execution.py`
  is intentionally small and should stay an execution helper rather than become
  the next evaluation monolith.

## Goal

Resolve the scoped service-boundary knot by the end of this stacked plan so
that:

- `app/services/evaluations.py` becomes a narrow orchestration and compatibility
  facade rather than the owner of fixture, scoring, structural, and latest-read
  implementations.
- At most three new owner modules are introduced:
  `app/services/evaluation_fixtures.py`,
  `app/services/evaluation_scoring.py`, and
  `app/services/evaluation_reads.py`.
- Existing execution helpers remain in `app/services/evaluation_execution.py`;
  this milestone must not re-expand that helper into a second oversized owner.
- Latest-evaluation API and capability contracts stay import-stable and
  behavior-stable.
- The scoped issue is `resolved` when the selected concern families no longer
  live together in `app/services/evaluations.py`.
- The broader owner case `IC-BF180637814C` is `reduced` unless refreshed live
  architecture evidence proves the hotspot is fully retired.

## Non-Goals

- No search, claim-support, evidence, agent-task, or semantic refactor in this
  packet.
- No API path, request-model, or response-model contract redesign.
- No DB schema, ORM model, or migration change.
- No rewrite of `app/services/eval_workbench.py` or
  `app/services/search_harness_evaluations.py`.
- No attempt to close the separate test hotspot owner case for
  `tests/unit/test_evaluation_service.py`; this milestone may reduce it, but it
  must not broaden that scope.
- No broad split into more than three new owner modules.

## Scope

In scope:

- Milestone 0 stacked-state refresh after the search and claim-support packets
  close
- hotspot-prevention bootstrap for `app/services/evaluations.py`
- one fixture/corpus owner module:
  `app/services/evaluation_fixtures.py`
- one scoring/structural owner module:
  `app/services/evaluation_scoring.py`
- one latest-read owner module:
  `app/services/evaluation_reads.py`
- direct unit coverage for the new owners
- compatibility coverage for `app/services/evaluations.py`
- route-boundary and integration verification for the existing
  `/documents/{document_id}/evaluations/latest` family and evaluation-run flow
- hygiene, improvement-case, and capability-contract updates for the narrowed
  facade and the new owners
- architecture index and handoff updates in the same closeout commit

Out of scope:

- adding a fourth new `evaluation_*.py` owner file
- moving explain/workbench logic out of `app/services/eval_workbench.py`
- solving the existing hotspot in `tests/unit/test_evaluation_service.py`
- moving route registration out of `app/api/routers/documents.py`
- changing corpus YAML contract semantics or making YAML a new source of truth

## Owner Surfaces

- compatibility facade:
  `app/services/evaluations.py`
- new fixture/corpus owner:
  `app/services/evaluation_fixtures.py`
- new scoring/structural owner:
  `app/services/evaluation_scoring.py`
- new latest-read owner:
  `app/services/evaluation_reads.py`
- existing helper surfaces that may be called but must not absorb new owner debt:
  `app/services/evaluation_execution.py`,
  `app/services/evaluation_fixture_cache.py`,
  `app/services/eval_workbench.py`,
  `app/services/documents.py`,
  `app/services/search_harness_evaluations.py`
- importer and compatibility surfaces:
  `app/services/runs.py`,
  `app/services/evaluation_corpus_runner.py`,
  `app/services/quality.py`,
  `app/services/semantic_backfill.py`,
  `app/services/evaluation_embedding_cache.py`,
  `app/services/knowledge_base_reset.py`,
  `app/services/capabilities/evaluation.py`,
  `app/cli.py`
- route surfaces:
  `app/api/routers/documents.py`
- tests:
  `tests/unit/test_evaluation_service.py`,
  `tests/unit/test_evaluation_fixtures.py`,
  `tests/unit/test_evaluation_scoring.py`,
  `tests/unit/test_evaluation_reads.py`,
  `tests/unit/test_documents_api.py`,
  `tests/unit/test_quality_service.py`,
  `tests/unit/test_eval_config.py`,
  `tests/unit/test_capability_contracts.py`,
  `tests/unit/test_api_architecture.py`,
  `tests/unit/test_hotspot_prevention.py`,
  and the evaluation integration roundtrip family
- governance and routing surfaces:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- New fixture and corpus logic belongs in
  `app/services/evaluation_fixtures.py`, including:
  fixture dataclasses, fixture normalization, fixture-path resolution, fixture
  matching, auto-fixture query generation, auto-fixture materialization, and
  `ensure_auto_evaluation_fixture(...)`.
- New scoring and structural logic belongs in
  `app/services/evaluation_scoring.py`, including:
  retrieval ranking evaluation, answer evaluation, rank-metric summaries,
  structural checks, merge-expectation matching, and related helper logic.
- New latest-read logic belongs in
  `app/services/evaluation_reads.py`, including:
  summary DTO assembly, latest-evaluation selection by run, latest-evaluation
  summaries by run set, and latest-document evaluation detail assembly.
- Keep `app/services/evaluations.py` as the stable import surface for existing
  callers and route-capability composition.
- Keep `app/services/evaluation_execution.py` focused on batch execution and
  row persistence; do not turn it into the owner of fixture generation,
  structural checks, or latest-read assembly.
- Do not move new implementation into `app/services/eval_workbench.py` or
  `app/services/documents.py`; those files already carry separate ownership and
  should only take compatibility adjustments if absolutely required.
- Do not create additional files such as
  `evaluation_auto_queries.py`, `evaluation_metrics.py`, or
  `evaluation_detail_views.py` in this milestone.
- Put new owner-module unit tests in focused test files rather than growing
  `tests/unit/test_evaluation_service.py` into a larger hotspot.

## Weak-Point Prevention Contract

Freshness check: Milestone 0 must rerun live routing and architecture commands
after the search orchestration and claim-support boundary milestones close.
This stacked plan is invalid if either prior packet remains uncommitted or if
the targeted evaluation concern families no longer live in
`app/services/evaluations.py`.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| No hotspot-prevention rule exists for the evaluation facade, so the split can regress immediately after closeout. | `config/hotspot_prevention.yaml`, `app/hotspot_prevention_classifier.py`, `app/services/evaluations.py` | `uv run pytest -q tests/unit/test_hotspot_prevention.py` and `uv run docling-system-hotspot-prevention-check --strict` | The facade can accept new fixture/scoring/read helpers without a failing gate. | Add or update a classifier case proving evaluation-fixture or latest-read growth inside `app/services/evaluations.py` is blocked. | A future session drops new fixture parsing into `app/services/evaluations.py` because it already imports YAML and search helpers. |
| Debt shifts from the service hotspot into adjacent evaluation-family files or the giant unit test hotspot. | `app/services/evaluation_execution.py`, `app/services/eval_workbench.py`, `app/services/documents.py`, `tests/unit/test_evaluation_service.py` | `wc -l` readback in closeout review plus targeted owner-module tests | `tests/unit/test_evaluation_service.py` grows above `2237` lines, or adjacent helper files absorb new concern families. | New focused tests must land in `tests/unit/test_evaluation_fixtures.py`, `tests/unit/test_evaluation_scoring.py`, and `tests/unit/test_evaluation_reads.py`. | A future session keeps the service shorter by moving more cases into `tests/unit/test_evaluation_service.py` or dumping logic into `eval_workbench.py`. |
| Fixture extraction breaks auto-corpus identity matching, sha256 handling, or retrieval-backed query filtering. | `app/services/evaluation_fixtures.py` | `uv run pytest -q tests/unit/test_evaluation_fixtures.py tests/unit/test_eval_config.py` | Auto-fixture refresh, sha256 disambiguation, or configured/manual corpus loading changes behavior without a failing test. | Preserve or replace the current fixture-path, sha256-collision, and retrieval-backed query tests with equivalent or stronger owner tests. | A future session rewrites fixture selection around filename-only matches and silently changes duplicate-document behavior. |
| Latest-read extraction breaks `/documents/{document_id}/evaluations/latest` or capability callers. | `app/services/evaluation_reads.py`, `app/services/documents.py`, `app/services/capabilities/evaluation.py`, `app/api/routers/documents.py` | `uv run pytest -q tests/unit/test_documents_api.py tests/unit/test_capability_contracts.py tests/unit/test_api_architecture.py` and DB-backed route tests | The route payload, not-found error contract, or evaluation capability facade changes unexpectedly. | Preserve the existing `document_evaluation_not_found` error path and latest-detail route assertions. | A future session points routes directly at `app.services.evaluation_reads` and bypasses the capability/documents seam. |
| The split reduces file size but worsens the existing service import cycle or creates a new evaluation-family hub. | `app/services/evaluations.py`, new owner modules, architecture controls | `uv run docling-system-architecture-inspect`, `uv run docling-system-capability-contracts`, and `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 15` | Cycle count increases, new forbidden imports appear, or capability contracts drift. | Keep owner modules service-local and forbid API/router imports or private cross-service imports. | A future session fixes the file by importing router-level helpers or making `evaluation_reads.py` the new omnivorous facade. |

## Milestone Sequence

### Milestone 0: Post-Search-And-Claim-Support System-State Refresh
Outcome label: resolved

- Assume `docs/search_execution_orchestration_boundary_milestone_plan.md` has
  closed and committed first, then
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md` has closed and
  committed second.
- Rerun the live architecture-quality, architecture-probe, improvement-case,
  hotspot-prevention, and evaluation-readiness commands after those closeouts.
- Refresh this plan, `docs/agentic_architecture_index.md`, and
  `docs/SESSION_HANDOFF.md` so the evaluation packet becomes the next active
  queued implementation brief only after the prior two packets are no longer
  draft-only worktree artifacts.
- Stop immediately if the prior two milestones are not complete, if
  `IC-BF180637814C` has already been rerouted, or if the targeted concern
  families have already moved.

### Milestone 1: Evaluation Facade Prevention Bootstrap
Outcome label: resolved

- Add explicit hotspot-prevention coverage for `app/services/evaluations.py`
  before moving large code blocks.
- Update `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_classifier.py` so fixture ownership, scoring
  ownership, structural ownership, and latest-read ownership are blocked from
  regrowing inside the facade.
- Add or extend controlled-violation coverage in
  `tests/unit/test_hotspot_prevention.py`.
- Update hygiene ratchets so the final facade and new owners have concrete
  ceilings rather than the current permissive `2161`-line budget.

### Milestone 2: Fixture And Corpus Owner Extraction
Outcome label: reduced

- Extract fixture dataclasses, corpus-path selection, fixture normalization,
  fixture matching, auto-fixture query generation, retrieval-backed query
  filtering, auto-fixture persistence, and `ensure_auto_evaluation_fixture(...)`
  into `app/services/evaluation_fixtures.py`.
- Re-export compatibility identities from `app/services/evaluations.py` so
  callers such as `knowledge_base_reset.py` and `evaluation_embedding_cache.py`
  stay stable during the packet.
- Add focused owner tests in `tests/unit/test_evaluation_fixtures.py`.
- Keep `tests/unit/test_evaluation_service.py` at or below its current line
  count by moving focused cases instead of adding more monolithic coverage.

### Milestone 3: Scoring And Structural Owner Extraction
Outcome label: reduced

- Extract retrieval ranking helpers, answer scoring helpers, failure-kind
  classification, reciprocal-rank summaries, merge-expectation checks, and
  structural summary assembly into `app/services/evaluation_scoring.py`.
- Keep `app/services/evaluation_execution.py` as the batch executor and row
  persistence seam; it may call the new scoring owner, but it must not become
  the owner of the scoring logic itself.
- Add focused owner tests in `tests/unit/test_evaluation_scoring.py`.
- Preserve the current retrieval and answer summary semantics, including
  `retrieval_rank_metrics` and `structural_passed`.

### Milestone 4: Latest-Read Owner Extraction And Facade Reduction
Outcome label: resolved for the scoped mixed-responsibility knot and reduced for broader owner case `IC-BF180637814C` unless live evidence proves full retirement

- Extract summary DTO assembly and latest-evaluation read helpers into
  `app/services/evaluation_reads.py`.
- Keep `app/services/evaluations.py` as the public orchestration/compatibility
  surface for `evaluate_run(...)`, `resolve_baseline_run_id(...)`, and stable
  re-exports.
- Preserve `app/services/documents.py`,
  `app/services/capabilities/evaluation.py`, and the
  `/documents/{document_id}/evaluations/latest` route family without contract
  drift.
- Close out the milestone with refreshed hygiene budgets, improvement-case
  measurement updates, architecture routing docs, and one local atomic commit.

## Required Implementation Artifacts

- `app/services/evaluations.py`
- `app/services/evaluation_fixtures.py`
- `app/services/evaluation_scoring.py`
- `app/services/evaluation_reads.py`
- compatibility adjustments only, if needed:
  `app/services/evaluation_execution.py`,
  `app/services/documents.py`,
  `app/services/runs.py`,
  `app/services/quality.py`,
  `app/services/semantic_backfill.py`,
  `app/services/evaluation_corpus_runner.py`,
  `app/services/evaluation_embedding_cache.py`,
  `app/services/knowledge_base_reset.py`,
  `app/services/capabilities/evaluation.py`,
  `app/cli.py`
- governance and tests:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `tests/unit/test_evaluation_service.py`,
  `tests/unit/test_evaluation_fixtures.py`,
  `tests/unit/test_evaluation_scoring.py`,
  `tests/unit/test_evaluation_reads.py`,
  `tests/unit/test_documents_api.py`,
  `tests/unit/test_quality_service.py`,
  `tests/unit/test_eval_config.py`,
  `tests/unit/test_capability_contracts.py`,
  `tests/unit/test_api_architecture.py`,
  `tests/unit/test_hotspot_prevention.py`

## Required Documentation And Handoff Updates

- update this plan with completion status, outcome labels, verification, and
  any bounded residual routing
- update `docs/agentic_architecture_index.md`
- update `docs/SESSION_HANDOFF.md`
- update `config/improvement_cases.yaml` with deployed ref and measured residual
  state for `IC-BF180637814C`
- update `config/hygiene_policy.yaml` with post-split ceilings for the facade
  and new owner modules

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/evaluations.py app/services/evaluation_fixtures.py app/services/evaluation_scoring.py app/services/evaluation_reads.py app/services/evaluation_execution.py app/services/documents.py app/services/runs.py app/services/quality.py app/services/semantic_backfill.py app/services/evaluation_corpus_runner.py app/services/evaluation_embedding_cache.py app/services/knowledge_base_reset.py app/services/capabilities/evaluation.py tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_documents_api.py tests/unit/test_quality_service.py tests/unit/test_eval_config.py tests/unit/test_capability_contracts.py tests/unit/test_api_architecture.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_documents_api.py tests/unit/test_quality_service.py tests/unit/test_eval_config.py tests/unit/test_capability_contracts.py tests/unit/test_api_architecture.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py tests/integration/test_eval_workbench_roundtrip.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 15`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- Milestone 0 refreshes the stacked system state after the search and
  claim-support packets close and updates routing docs to reflect the new
  active queue order.
- `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_classifier.py` explicitly govern
  `app/services/evaluations.py`, and the controlled-violation tests prove that
  fixture, scoring, structural, and latest-read growth in the facade is
  blocked.
- No more than three new owner modules are introduced, and they are exactly:
  `app/services/evaluation_fixtures.py`,
  `app/services/evaluation_scoring.py`, and
  `app/services/evaluation_reads.py`.
- `app/services/evaluations.py` no longer owns fixture parsing, auto-fixture
  generation, scoring detail assembly, structural check bodies, or
  latest-evaluation detail assembly.
- `app/services/evaluations.py` closes at `<= 550` lines and `<= 12` private
  helpers.
- `app/services/evaluation_fixtures.py` closes at `<= 950` lines and
  `<= 25` private helpers.
- `app/services/evaluation_scoring.py` closes at `<= 950` lines and
  `<= 25` private helpers.
- `app/services/evaluation_reads.py` closes at `<= 450` lines and
  `<= 10` private helpers.
- `tests/unit/test_evaluation_service.py` does not grow above its current
  `2237` lines; new owner coverage lands in focused test files instead.
- `app/services/evaluation_execution.py`, `app/services/eval_workbench.py`, and
  `app/services/documents.py` do not absorb new owner families beyond minimal
  adapter changes.
- `/documents/{document_id}/evaluations/latest` and
  `/documents/{document_id}/evaluations/latest/explain` preserve current HTTP
  behavior, including the `document_evaluation_not_found` error path.
- Capability contracts remain valid and continue to expose the evaluation
  facade through `app/services/capabilities/evaluation.py`.
- Evaluation data readiness remains valid after the split; the milestone must
  not weaken fixture generation or retrieval-backed evaluation coverage just to
  get green.
- The broader owner case `IC-BF180637814C` is marked `reduced` unless the live
  architecture-quality evidence removes the hotspot or proves a narrower owner
  contract enough to close it as `resolved`.

## Stop Conditions

- The search orchestration milestone or the claim-support boundary milestone is
  not complete and committed locally.
- The targeted evaluation concern families have already moved, making this
  drafted baseline stale.
- The split requires more than three new owner modules.
- Any proposed new owner exceeds the ceilings in this plan.
- The split depends on moving core logic into `app/services/eval_workbench.py`,
  `app/services/documents.py`, `app/services/search_harness_evaluations.py`, or
  by growing `tests/unit/test_evaluation_service.py` beyond its current size.
- Route or integration failures imply an API, schema, or persistence contract
  change outside this packet.
- Architecture inspection, capability contracts, or architecture probe evidence
  show a worse cycle story after the split.

## Local Commit Closeout Policy

This milestone is complete only after:

- implementation, tests, governance updates, and docs/handoff updates are all
  present together
- the full verification gate set passes
- the stacked routing docs reflect the post-closeout next owner case
- one local atomic commit lands for this milestone only

Do not mark the milestone complete if the code is green but the improvement
case, hygiene budgets, architecture index, or session handoff still describe
the old evaluation-service ownership.

## Residual Risks And Next Milestone Routing

- `tests/unit/test_evaluation_service.py` remains a separate hotspot owner case
  (`IC-7A628A4CBCAC`) even if this service milestone succeeds. If the owner
  split lands cleanly, the next evaluation-family follow-on should probably
  target test decomposition rather than reopen the service boundary.
- The broader owner case `IC-BF180637814C` may remain open if the evaluation
  facade still carries enough orchestration weight to appear in hotspot
  reporting. In that case, route the residual specifically as
  orchestration-only debt rather than reopening fixture or read ownership.
- The existing Python cycle that includes `app.services.evaluations` may remain
  even after this split. If the cycle count does not improve, route that as a
  separate cycle-reduction milestone rather than broadening this packet.

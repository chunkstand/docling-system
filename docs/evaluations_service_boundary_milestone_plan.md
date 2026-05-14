# Evaluations Service Boundary Milestone Plan

Date: 2026-05-13 local / 2026-05-13 UTC
Status: resolved locally on 2026-05-13 after Milestones 0-4 resolved
locally; `docs/search_execution_orchestration_boundary_milestone_plan.md`
closed as `dae5e4f`,
`docs/claim_support_policy_impacts_boundary_milestone_plan.md` closed as
`3d7d090`, Milestone 1 closed locally as `9e3a8e4`, Milestone 2 closed
locally as `3817659`, Milestone 3 closed locally as `b05def0`, and
Milestone 4 closed locally as `1159297`
Owner context: active follow-on under `IC-BF180637814C` /
`app/services/evaluations.py`. This plan assumes the current search execution
orchestration packet closed first as `dae5e4f`, the claim-support boundary
packet closed second as `3d7d090`, and Milestone 0 refreshed the live system
state before any evaluation-service code moves.

## Local Progress

Milestone 4 is now resolved locally. This plan is resolved locally through the
latest-read owner extraction and evaluation-facade reduction closeout.

Local Milestone 4 snapshot:

- fixture and corpus ownership remains in
  `app/services/evaluation_fixtures.py`, including fixture dataclasses,
  manual/auto corpus resolution, fixture matching, auto-query generation,
  retrieval-backed query filtering, and `ensure_auto_evaluation_fixture(...)`
- retrieval scoring, answer evaluation, failure-kind classification,
  reciprocal-rank summaries, merge-expectation checks, and structural summary
  assembly now live in `app/services/evaluation_scoring.py`
- latest-evaluation summary DTO assembly plus summary/detail read helpers now
  live in `app/services/evaluation_reads.py` at `154` lines / `1` private
  helper
- reduced `app/services/evaluations.py` to the narrower orchestration and
  compatibility facade at `283` lines / `1` private helper, while the
  fixture owner remains at `966` lines / `32` private helpers, the scoring
  owner remains at `897` lines / `25` private helpers, and the new read owner
  closes under the same owner case
- preserved importer stability for callers that continue to import the
  orchestration entrypoints and compatibility helpers from
  `app.services.evaluations`
- preserved `app/services/documents.py`,
  `app/services/capabilities/evaluation.py`, and the
  `/documents/{document_id}/evaluations/latest` route family without contract
  drift while adding focused read-owner coverage in
  `tests/unit/test_evaluation_reads.py` at `199` lines
- ratcheted `config/hygiene_policy.yaml` to the measured post-split ceilings
  for the narrowed facade and the new read owner module while keeping the
  fixture and scoring owner ratchets unchanged
- strict hotspot prevention now reports `known_hotspots=9`,
  `changed_hotspots=1`, `blocked=0`, `allowed=4`, `exceptions=0`
- architecture quality remains `hotspot_count=10` with
  `max_hotspot_risk_score=501.06`; the architecture-quality summary top-five
  still excludes the evaluation facade, and the architecture probe no longer
  lists `app/services/evaluations.py` among the top 15 churn hotspots or the
  remaining Python cycle components
- broader owner case `IC-BF180637814C` is now resolved locally as a deployed
  facade-reduction result rather than remaining an open reduced hotspot case
- local closeout commit: `1159297`
- next routed stacked follow-on: `docs/evidence_provenance_exports_boundary_milestone_plan.md`

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

Milestone 2 baseline evidence captured from the local checkout before the
fixture/corpus extraction began on 2026-05-13 local / 2026-05-13 UTC:

```text
git status -sb
  ## main...origin/main [ahead 13]

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
  max_hotspot_risk_score=516.06
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

- `docs/search_execution_orchestration_boundary_milestone_plan.md` is resolved
  locally through closeout commit `dae5e4f`, and
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md` is resolved
  locally through closeout commit `3d7d090`. This evaluation follow-on is now
  the next active bounded implementation brief, and Milestone 0 is resolved
  locally through the stacked-state refresh performed in the claim-support
  closeout alignment pass.
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
Status: resolved locally on 2026-05-13 during the claim-support closeout
alignment pass
Outcome label: resolved

- `docs/search_execution_orchestration_boundary_milestone_plan.md` closed
  locally first as `dae5e4f`, then
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md` closed
  locally second as `3d7d090`.
- Reran the live architecture-quality, architecture-probe, improvement-case,
  hotspot-prevention, and evaluation-readiness commands after those closeouts.
- Refreshed this plan, `docs/agentic_architecture_index.md`, and
  `docs/SESSION_HANDOFF.md` so the evaluation packet is now the next active
  bounded implementation brief instead of a queued draft-only follow-on.
- The refresh window closed with architecture quality
  `hotspot_count=10`, `max_hotspot_risk_score=516.06`, strict hotspot
  prevention `known_hotspots=8`, `changed_hotspots=0`, `blocked=0`,
  improvement-case summary `case_count=28`, `open=21`, `deployed=6`,
  `measured=1`, and evaluation-data readiness
  `regression_ready=true`, `court_grade_ready=true`.

### Milestone 1: Evaluation Facade Prevention Bootstrap
Status: resolved locally on 2026-05-13; Milestone 2 is now the next
implementation gate
Outcome label: resolved

- `config/hotspot_prevention.yaml` now governs
  `app/services/evaluations.py` as an evaluation-service compatibility facade
  that routes future implementation into `app/services/evaluation_*.py`
- `app/hotspot_prevention_classifier.py` now blocks new fixture/corpus,
  scoring, structural-check, and latest-read logic in the facade while still
  allowing narrow explicit forwarding wrappers
- `tests/unit/test_hotspot_prevention.py` now proves that fixture refresh,
  answer scoring, structural summary, and latest-read growth are rejected for
  `app/services/evaluations.py`, and that a forwarding wrapper to a future
  owner module remains allowed
- `config/hygiene_policy.yaml` now ratchets
  `app/services/evaluations.py` to its exact pre-extraction size and pre-budgets
  the three planned owner modules before Milestones 2-4

### Milestone 2: Fixture And Corpus Owner Extraction
Status: resolved locally on 2026-05-13; Milestone 3 is now the next
implementation gate
Outcome label: reduced

- extracted fixture dataclasses, corpus-path selection, fixture normalization,
  fixture matching, auto-fixture query generation, retrieval-backed query
  filtering, auto-fixture persistence, and
  `ensure_auto_evaluation_fixture(...)` into
  `app/services/evaluation_fixtures.py`
- kept `app/services/evaluations.py` as the stable import facade for
  compatibility identities used by `knowledge_base_reset.py`,
  `evaluation_embedding_cache.py`, the evaluation runner, and the Postgres
  integration harness
- added focused owner tests in `tests/unit/test_evaluation_fixtures.py` and
  reduced `tests/unit/test_evaluation_service.py` to the remaining
  orchestration and execution-seam assertions
- left `app/services/evaluation_scoring.py`,
  `app/services/evaluation_reads.py`, and their unit files absent on purpose;
  those owner surfaces remain reserved for Milestones 3-4 instead of being
  introduced early in the fixture packet
- local closeout commit: `3817659`
- verification on the resolved slice:
  `48 passed` in `tests/unit/test_evaluation_fixtures.py` and
  `tests/unit/test_evaluation_service.py`;
  `113 passed` across the Milestone 2 unit boundary suite;
  `12 passed` in the targeted Postgres integration trio;
  `1898 passed` in the full `DOCLING_SYSTEM_RUN_INTEGRATION=1` suite;
  hotspot prevention strict `blocked=0`;
  hygiene `new hygiene regressions: none`;
  architecture inspect `valid=true`;
  capability contracts `valid=true`;
  architecture quality `hotspot_count=10`, `max_hotspot_risk_score=501.06`;
  evaluation readiness `regression_ready=true`, `court_grade_ready=true`

### Milestone 3: Scoring And Structural Owner Extraction
Status: resolved locally on 2026-05-13; Milestone 4 is now the next
implementation gate
Outcome label: reduced

- extracted retrieval ranking helpers, answer scoring helpers, failure-kind
  classification, reciprocal-rank summaries, merge-expectation checks, and
  structural summary assembly into `app/services/evaluation_scoring.py`
- kept `app/services/evaluation_execution.py` as the batch executor and row
  persistence seam without shifting the scoring ownership into the executor
- kept `app/services/evaluations.py` as the stable orchestration and
  compatibility facade, now reduced to `400` lines / `2` private helpers
- added focused owner tests in `tests/unit/test_evaluation_scoring.py` and
  reduced `tests/unit/test_evaluation_service.py` to `389` lines while the new
  scoring owner tests close at `381` lines
- preserved the current retrieval and answer summary semantics, including
  `retrieval_rank_metrics` and `structural_passed`
- ratcheted `config/hygiene_policy.yaml` to the measured post-split ceilings:
  `app/services/evaluations.py` at `400` lines / `2` private helpers,
  `app/services/evaluation_fixtures.py` at `966` lines / `32` private
  helpers, and `app/services/evaluation_scoring.py` at `897` lines /
  `25` private helpers
- local closeout commit: `b05def0`
- verification on the resolved slice:
  `15 passed` in `tests/unit/test_evaluation_service.py` and
  `tests/unit/test_evaluation_scoring.py`;
  `114 passed` across the Milestone 3 unit boundary suite;
  `12 passed` in the targeted Postgres integration trio;
  `1899 passed` in the full `DOCLING_SYSTEM_RUN_INTEGRATION=1` suite;
  hotspot prevention strict `blocked=0`;
  hygiene `new hygiene regressions: none`;
  architecture inspect `valid=true`;
  capability contracts `valid=true`;
  architecture quality `hotspot_count=10`, `max_hotspot_risk_score=501.06`;
  evaluation readiness `regression_ready=true`, `court_grade_ready=true`

### Milestone 4: Latest-Read Owner Extraction And Facade Reduction
Status: resolved locally on 2026-05-13; the evaluation service boundary plan is
now resolved locally through Milestone 4
Outcome label: resolved

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

Results:

- extracted evaluation summary DTO assembly and latest-evaluation summary and
  detail reads into `app/services/evaluation_reads.py`
- kept `app/services/evaluations.py` as the stable orchestration and
  compatibility facade for `evaluate_run(...)`,
  `resolve_baseline_run_id(...)`, and the public latest-read import surface,
  now reduced to `283` lines / `1` private helper
- preserved `app/services/documents.py`,
  `app/services/capabilities/evaluation.py`, and the
  `/documents/{document_id}/evaluations/latest` route family without contract
  drift while proving the facade wrappers through focused unit coverage in
  `tests/unit/test_evaluation_reads.py`
- ratcheted `config/hygiene_policy.yaml` to the measured post-split ceilings:
  `app/services/evaluations.py` at `283` lines / `1` private helper,
  `app/services/evaluation_fixtures.py` at `966` lines / `32` private
  helpers, `app/services/evaluation_scoring.py` at `897` lines /
  `25` private helpers, and `app/services/evaluation_reads.py` at
  `154` lines / `1` private helper
- updated `config/improvement_cases.yaml` so `IC-BF180637814C` now records the
  Milestone 4 facade-resolution state with a pending local closeout hash
  placeholder that must be aligned in a follow-up commit
- architecture quality remains `hotspot_count=10` with
  `max_hotspot_risk_score=501.06`; the architecture probe top 15 no longer
  lists `app/services/evaluations.py` or the remaining Python cycle
  components, so the broader owner case is resolved locally rather than merely
  reduced
- local closeout commit: `1159297`
- next routed stacked follow-on:
  `docs/evidence_provenance_exports_boundary_milestone_plan.md`

Verification on the resolved slice:

- `git diff --check`: pass
- `uv run ruff check app/services/evaluations.py app/services/evaluation_fixtures.py app/services/evaluation_scoring.py app/services/evaluation_reads.py app/services/evaluation_execution.py app/services/documents.py app/services/runs.py app/services/quality.py app/services/semantic_backfill.py app/services/evaluation_corpus_runner.py app/services/evaluation_embedding_cache.py app/services/knowledge_base_reset.py app/services/capabilities/evaluation.py tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_documents_api.py tests/unit/test_quality_service.py tests/unit/test_eval_config.py tests/unit/test_capability_contracts.py tests/unit/test_api_architecture.py tests/unit/test_hotspot_prevention.py`: pass
- `uv run pytest -q tests/unit/test_evaluation_reads.py tests/unit/test_evaluation_service.py tests/unit/test_documents_api.py`:
  `34 passed`
- `uv run pytest -q tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_documents_api.py tests/unit/test_quality_service.py tests/unit/test_eval_config.py tests/unit/test_capability_contracts.py tests/unit/test_api_architecture.py tests/unit/test_hotspot_prevention.py`:
  `122 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py tests/integration/test_eval_workbench_roundtrip.py`:
  `12 passed`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `known_hotspots=9`, `changed_hotspots=1`, `blocked=0`, `allowed=4`,
  `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=28`,
  `status_counts.open=20`, `status_counts.deployed=7`,
  `status_counts.measured=1`, `measured_case_count=18`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `regression_ready=true`, `court_grade_ready=true`, `failed_gate_count=0`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 15`:
  `app/services/evaluations.py` is absent from the top 15 churn hotspots and
  absent from the remaining Python cycle components; the top hotspot is now
  `app/cli.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1907 passed`

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
- `app/services/evaluation_fixtures.py` closes at or below its measured
  post-Milestone-2 ratchet unless a later extraction reduces it further; the
  current exact ceiling is `966` lines and `32` private helpers.
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

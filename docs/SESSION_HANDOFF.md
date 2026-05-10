# Session Handoff

Date: 2026-05-10 local / 2026-05-10 UTC
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `main`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Latest committed checkpoint: local `Architecture Plan 01` Milestone 6 search
query-feature split closeout.

## Current Position

The checkout is on `main`. Local `main` is ahead of `origin/main` by 21
commits after the Milestone 6 search split closeout; `origin/main` is `6933eca`
(`Add Docker pg_dump fallback for reset`).

The latest Milestone 6 closeout commit contains the first `app/services/search.py`
core split and its verification/docs updates:

- `app/services/search.py`
- `app/services/search_query_features.py`
- `tests/unit/test_search_query_features.py`
- `docs/architecture_plan_01.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/agentic_architecture_milestone_audit.md`
- `docs/agentic_architecture_milestone_plan.md`
- `docs/data_model_boundary_plan.md`
- `README.md`
- `SYSTEM_PLAN.md`

The current system is a local-first, durable document-intelligence platform with:

- active-run-gated PDF ingest, parsing, validation, and promotion
- mixed chunk/table retrieval, grounded chat, search replay, and harness governance
- figure, table, chunk, span, evidence, and audit-bundle provenance in Postgres plus canonical JSON artifacts
- authenticated remote mode with route capability contracts and mutation-key gates
- additive semantic ontology, fact-graph, and graph-memory workflows
- technical-report generation with context-pack evaluation, claim provenance locks, support-judge calibration, and audit bundles
- DB-backed agent-task orchestration with typed actions, context refs, approvals, attempts, outcomes, traces, and cost/performance telemetry
- architecture, capability, decision, hygiene, improvement-case, and trace-review governance commands

## Recent Local Milestones Since `origin/main`

The 21 local commits ahead of `origin/main` are:

- local Milestone 6 closeout commit for the first `app/services/search.py`
  core split
- local Milestone 5 alignment closeout commit for explicit `app.cli`
  forwarding compatibility and residual CLI split documentation
- local Milestone 5 closeout commit for the first `app/cli.py` command-group
  split
- local Milestone 4 alignment closeout commit documenting the remaining
  agent-task import-cycle signal and next action-family split target
- local Milestone 4 closeout commit for `Architecture Plan 01`
- local closeout-doc policy hardening commit after `Architecture Plan 01`
  Milestone 3
- local Milestone 3 alignment closeout commit for `Architecture Plan 01`
- local Milestone 3 closeout commit for `Architecture Plan 01`
- `980cc8c` `architecture: harden milestone 2 alignment`
- `b6eb75d` `architecture: complete milestone 2 model domain split`
- `bb03b83` `architecture: complete milestone 1 compatibility harness`
- `5f4598b` `Split agent task action executors`
- `7fe2dbc` `Split technical report services`
- `482daa3` `Clear near-threshold hygiene blockers`
- `637559a` `Split hygiene blocker modules`
- `b59d4d5` `Split agent task hygiene modules`
- `25ac117` `Harden search and retrieval hygiene boundaries`
- `8654bde` `Split search replay and release gate hygiene`
- `1e05afd` `refactor evidence payload helpers`
- `9f60a17` `complete agentic architecture governance milestones`
- `d1b38df` `docs: refresh current system state`

These commits moved the repo toward agent-legible modular-monolith governance:
narrower retrieval and agent-orchestration capability contract companions,
agent-action manifest validation, trace-first review, architecture quality
reporting, improvement-case import from generated reports, and a data-model
boundary plan for `app/db/models.py`.

## Current Architecture And Governance State

Current read-only gates from this checkout:

```text
uv run docling-system-architecture-inspect
  valid=true, violation_count=0, api_route_count=130,
  agent_action_count=51, contract_count=10, inspection_rule_count=13

uv run docling-system-capability-contracts
  valid=true, facade_count=6, function_count=110, issues=[]

uv run docling-system-architecture-decisions
  valid=true, decision_count=9, issues=[]

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=687.04
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/evidence.py,
    app/services/agent_task_actions.py,
    tests/unit/test_cli.py
  ]
```

The architecture boundary model is clean, but hotspot debt remains real. The
top governed split targets are `app/db/models.py`, `app/services/evidence.py`,
`app/cli.py`, `app/services/agent_task_actions.py`, and `app/services/search.py`.
The latest architecture probe records `app/services/search.py` at 3,250 lines
and 84,500 hotspot score after the first search-core split.

## Runtime Gate Snapshot

Milestone 0 restored the DB-backed runtime gate on 2026-05-09.

Commands run:

```bash
open -a Docker
docker version
docker compose config --quiet
docker compose up -d db
docker compose ps
uv run --extra dev alembic heads
uv run --extra dev alembic current
uv run --extra dev alembic upgrade head
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run ruff check app tests
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
uv run docling-system-evaluation-data-readiness
uv run docling-system-agent-trace-review --limit 5 --skip-hygiene
```

Results:

```text
Docker Desktop: running after `open -a Docker`.
Compose config: valid.
Compose runtime: `docling-system-db` healthy on localhost:5432; `worker` and `agent-worker` running.
Alembic heads: `0076_claim_feedback_replay_src (head)`.
Alembic current: `0076_claim_feedback_replay_src (head)`.
Alembic upgrade head: completed with no pending migrations.
Full DB-backed tests: `872 passed in 51.00s`.
Ruff: All checks passed.
Architecture inspection: valid, `violation_count=0`.
Capability contracts: valid, `facade_count=6`, `function_count=110`, `issues=[]`.
Architecture quality summary: `agent_legibility_average_score=90.0`, `broad_facade_count=2`, `hotspot_count=10`.
Evaluation-data readiness: command runs against Postgres; `regression_ready=false`, `court_grade_ready=false`, `failed_gate_count=11`.
Agent trace review: command runs against Postgres; `observation_count=0`.
```

## Data Model Compatibility Harness Snapshot

Milestone 1 implemented, verified, and locally committed the pre-split
compatibility harness on 2026-05-09. No ORM classes moved.

Files added or updated for the harness:

- `app/db/models.py`
- `tests/db_model_contract.py`
- `tests/unit/test_db_model_import_compatibility.py`
- `tests/integration/test_db_model_metadata.py`
- `docs/data_model_boundary_plan.md`
- `docs/architecture_plan_01.md`

Focused verification:

```bash
uv run pytest -q tests/unit/test_db_model_import_compatibility.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run ruff check app tests
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
uv run --extra dev alembic check
```

Results:

```text
model import compatibility: 221 passed.
Postgres model metadata/create-all check: 3 passed.
Postgres integration suite: 72 passed.
Full DB-backed suite: 1096 passed in 47.41s.
Ruff: passed.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid.
Architecture quality summary: hotspot_count=10, max_hotspot_risk_score=674.68.
Alembic check: no new upgrade operations detected.
```

The harness protects 109 public `app.db.models` symbols: 29 enums and 80 ORM
model classes. It also asserts the full 80-table `Base.metadata` contract and
checks schema-scoped Postgres `Base.metadata.create_all(...)`. During closeout,
the harness also closed a pre-existing Alembic metadata drift by declaring the
migrated `ix_document_runs_status_completed_at` index on `DocumentRun` metadata
and testing required model indexes in unit and Postgres create-all paths.

## Data Model Domain Split Snapshot

Milestone 2 implemented, verified, and locally committed the first physical ORM
model-domain split on 2026-05-09.

Files added or updated for the split:

- `app/db/model_domains/__init__.py`
- `app/db/model_domains/platform.py`
- `app/db/models.py`
- `tests/db_model_contract.py`
- `tests/unit/test_db_model_import_compatibility.py`
- `tests/integration/test_db_model_metadata.py`
- `docs/data_model_boundary_plan.md`
- `docs/architecture_plan_01.md`

Implemented result:

- `ApiIdempotencyKey` moved to `app/db/model_domains/platform.py`.
- `app/db/models.py` remains import-compatible by re-exporting
  `ApiIdempotencyKey`.
- No other ORM classes moved.
- `api_idempotency_keys` table name, columns, JSONB response storage,
  `ix_api_idempotency_keys_created_at`, and
  `uq_api_idempotency_keys_scope_key` are preserved and covered.
- The platform-support contract now checks exact index and unique-constraint
  column ordering in both unit metadata and Postgres create-all paths.
- `app/db/models.py` is now 6,006 lines; the new platform domain module is
  35 lines.

Focused verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_db_model_import_compatibility.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py
uv run --extra dev alembic heads
uv run --extra dev alembic current
uv run --extra dev alembic upgrade head
uv run --extra dev alembic check
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
```

Results:

```text
model import compatibility: 226 passed.
Postgres model metadata/create-all check: 7 passed.
Alembic heads/current: 0076_claim_feedback_replay_src (head).
Alembic upgrade head: completed with no pending migrations.
Alembic check: no new upgrade operations detected.
Full DB-backed suite: 1105 passed in 48.41s.
Ruff: passed.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture quality summary: hotspot_count=10, max_hotspot_risk_score=687.04.
```

## Evidence Service Split Snapshot

Milestone 3 implemented, verified, and locally committed the first physical
evidence-service split on 2026-05-09.

Files added or updated for the split:

- `app/services/evidence.py`
- `app/services/evidence_common.py`
- `app/services/evidence_records.py`
- `app/services/evidence_search_packages.py`
- `app/services/evidence_search_trace_graph.py`
- `app/services/evidence_search_trace_store.py`
- `tests/unit/test_evidence_search_packages.py`
- `docs/architecture_plan_01.md`
- `docs/agentic_architecture_index.md`
- `docs/agentic_architecture_milestone_audit.md`
- `docs/agentic_architecture_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`

Implemented result:

- Search evidence package assembly, export persistence, trace graph
  persistence, trace integrity, and response assembly moved out of
  `app/services/evidence.py`.
- `app.services.evidence` remains import-compatible for
  `get_search_evidence_package`, `persist_search_evidence_package_export`,
  `export_search_evidence_package`, and
  `get_search_evidence_package_export_trace`.
- Shared trace row/spec helpers now live in `app/services/evidence_common.py`;
  the shared evidence export payload helper lives in
  `app/services/evidence_records.py`.
- `app/services/evidence.py` is now 8,608 lines. The new search-evidence
  modules are 338, 421, and 296 lines.

Focused verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_evidence_common.py tests/unit/test_evidence_records.py tests/unit/test_evidence_provenance.py tests/unit/test_evidence_search_packages.py
uv run pytest -q tests/unit/test_search_api.py tests/unit/test_search_service.py tests/unit/test_search_history.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_evidence_operator_runs_roundtrip.py
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-decisions
uv run docling-system-architecture-quality-report --summary
uv run docling-system-hygiene-check
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Results:

```text
Evidence helper tests: 27 passed.
Search API/service/history tests: 70 passed.
Search evidence operator-run roundtrip: 1 passed.
Full DB-backed suite: 1109 passed in 47.48s.
Ruff: passed.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture decisions: valid, decision_count=9.
Architecture quality summary: hotspot_count=10, max_hotspot_risk_score=687.04.
Hygiene: no ruff, vulture, duplicate-helper, improvement-case, or architecture
findings; inherited file/helper budget debt remains.
```

## Agent Action Registry Split Snapshot

Milestone 4 implemented, verified, and locally committed the first physical
agent-action registry family split on 2026-05-09.

Files added or updated for the split:

- `app/services/agent_task_actions.py`
- `app/services/agent_actions/search_harness.py`
- `tests/unit/test_agent_action_contracts.py`
- `docs/architecture_plan_01.md`
- `docs/agentic_architecture_index.md`
- `docs/agentic_architecture_milestone_audit.md`
- `docs/agentic_architecture_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`

Implemented result:

- Search-harness action contract metadata and helper logic moved into
  `app/services/agent_actions/search_harness.py`.
- `app.services.agent_task_actions` remains the public action registry facade
  and execution entrypoint; current executor import paths remain available.
- Covered search-harness action types are
  `optimize_search_harness_from_case`,
  `draft_harness_config_update_from_optimization`, `replay_search_request`,
  `run_search_replay_suite`, `evaluate_search_harness`,
  `verify_search_harness_evaluation`, `draft_harness_config_update`,
  `verify_draft_harness_config`, `triage_replay_regression`, and
  `apply_harness_config_update`.
- `app/services/agent_task_actions.py` is now 2,884 lines; the new
  search-harness registry/helper module is 539 lines.

Focused verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_agent_task_actions.py tests/unit/test_agent_action_contracts.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_task_triage.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py
uv run docling-system-agent-task-action-index
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-decisions
uv run docling-system-architecture-quality-report --summary
uv run docling-system-hygiene-check
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Results:

```text
Focused agent-action and adjacent agent-task tests: 136 passed.
DB-backed semantic and triage orchestration roundtrips: 9 passed.
Full DB-backed suite: 1110 passed in 48.43s.
Ruff: passed.
Agent task action index: generated successfully.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture decisions: valid, decision_count=9.
Architecture quality summary: hotspot_count=10, max_hotspot_risk_score=687.04.
Hygiene: no ruff, vulture, improvement-case, or architecture findings;
inherited file/helper budget debt remains.
```

Alignment check:

```text
Architecture probe:
  command: python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown
  result: 3 Python cycle components remain.
  agent_task_actions: 2,884 lines, fan-out 39 local modules, still part of the
  large agent-task cycle component.

Registry composition:
  command: uv run python -c '<import action registry and print counts/modules>'
  result: total_actions=51, search_harness_actions=10,
  executor_modules=['app.services.agent_task_actions'].

Closeout gates:
  git diff --check: passed.
  uv run ruff check app tests: passed.
  uv run pytest -q tests/unit/test_agent_action_contracts.py: 9 passed.
  uv run docling-system-agent-task-action-index: generated successfully.
  uv run docling-system-architecture-inspect: valid, violation_count=0.
  uv run docling-system-capability-contracts: valid, facade_count=6,
  function_count=110.
  uv run docling-system-architecture-decisions: valid, decision_count=9.
  uv run docling-system-architecture-quality-report --summary:
  agent_legibility_average_score=90.0, broad_facade_count=2,
  hotspot_count=10, max_hotspot_risk_score=687.04.
  DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs:
  1110 passed in 49.04s.
```

Milestone 4 should therefore be read as the first search-harness registry/helper
split, not as an executor implementation move. The next action-family split
target is a search-harness executor dependency seam, or a semantic executor
family with more isolated dependencies, before moving executor implementations
out of the compatibility facade.

## CLI Command Group Split Snapshot

Milestone 5 implemented the first `app/cli.py` command-group split on
2026-05-10.

Implemented result:

- Introduced `app/cli_commands/`.
- Moved the improvement-case validate/list/summary/record command
  implementations into `app/cli_commands/improvement_cases.py`.
- Kept the existing console scripts on `app.cli:run_improvement_case_validate`,
  `app.cli:run_improvement_case_list`, `app.cli:run_improvement_case_summary`,
  and `app.cli:run_improvement_case_record`.
- Alignment pass replaced a lint-suppressed import re-export with explicit
  forwarding functions in `app.cli`, so console entrypoints resolve to stable
  `app.cli` callables while implementation logic stays in
  `app/cli_commands/improvement_cases.py`.
- Added parser/help coverage for the moved command group in
  `tests/unit/test_cli.py`.
- Reduced `app/cli.py` from 1,452 lines to 1,283 lines; the new command module
  is 149 lines.

Focused verification:

```bash
uv run ruff check app tests
uv run pytest -q tests/unit/test_cli.py
uv run python -c '<import app.cli and print moved callable modules>'
uv run docling-system-architecture-quality-report --summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown
```

Results:

```text
Ruff: passed.
Focused CLI tests: 55 passed.
Entrypoint compatibility: moved run_improvement_case_* console scripts resolve
through app.cli forwarding functions and preserve their callable names.
Architecture quality summary: agent_legibility_average_score=90.0,
broad_facade_count=2, hotspot_count=10, max_hotspot_risk_score=687.04.
Architecture probe: app/cli.py is 1,283 probe-counted lines and its hotspot
score is 67,999; the remaining Python cycle components are outside this CLI
slice.
Full DB-backed suite: 1111 passed in 49.25s.
```

## Search Core Split Snapshot

Milestone 6 implemented the first `app/services/search.py` core concern split
on 2026-05-10.

Implemented result:

- Added `app/services/search_query_features.py` as the focused owner for
  query-intent classification, tabular-query detection, identifier lookup
  detection, normalized query feature sets, token/phrase coverage helpers, and
  metadata-query token extraction.
- Kept `app.services.search` import-compatible for existing query helper names,
  including `QueryFeatureSet`, `is_tabular_query`, `_classify_query_intent`,
  `_looks_like_identifier_lookup`, `_build_query_feature_set`,
  `_token_coverage`, and `_strong_document_phrase_match`.
- Preserved search API, ranking, metadata-supplement, replay, telemetry, and
  `execute_search` / `search_documents` contracts.
- Added focused compatibility tests in `tests/unit/test_search_query_features.py`.
- Reduced `app/services/search.py` from 3,429 lines to 3,250 lines; the new
  query-feature owner module is 199 lines.
- Reduced the architecture-probe hotspot score for `app/services/search.py`
  from 89,154 to 84,500 while keeping the general architecture-probe cycle
  count at the prior 3 known components.

Focused verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_search_query_features.py tests/unit/test_search_service.py tests/unit/test_search_api.py
uv run pytest -q tests/unit/test_search_history.py tests/unit/test_search_replays.py tests/unit/test_search_release_gate.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_search_replays_roundtrip.py tests/integration/test_search_harness_releases.py
uv run docling-system-run-replay-suite --help
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Results:

```text
Ruff: passed across app and tests.
Search query feature/service/API tests: 70 passed.
Search history/replay/release-gate tests: 20 passed.
DB-backed search replay/release roundtrips: 4 passed.
Replay-suite CLI help: resolved successfully.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture quality summary: agent_legibility_average_score=90.0,
broad_facade_count=2, hotspot_count=10, max_hotspot_risk_score=687.04.
Architecture probe: app/services/search.py is 3,250 probe-counted lines and
84,500 hotspot score; Python cycle components remain at 3.
Full DB-backed suite: 1114 passed in 48.38s.
```

## Architecture Milestone Closeout Policy

The architecture plan was revised on 2026-05-09 so each milestone is complete
only after focused verification, cross-milestone gates, affected docs, handoff
updates, scoped staging, and a local commit. Push remains a separate action and
should happen only when explicitly requested.

The revised closeout rule is:

- run focused tests for the moved or guarded contract
- run `git diff --check`, Ruff, architecture inspection, capability contracts,
  and the architecture-quality summary
- run `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` for DB, API,
  storage, search, evidence, agent-task, worker, or runtime-facing changes
- run Alembic head/current/upgrade/check plus Postgres metadata create-all
  verification for model or migration changes
- update closeout docs before commit: always refresh this handoff and the active
  milestone/status doc, then refresh any other affected durable docs
- stage only the milestone slice and commit locally before starting the next
  milestone

Milestones 1, 2, 3, 4, 5, and 6 satisfy the revised local commit closeout rule.
Milestone 7 may begin from this committed checkpoint.

## Active Weak Points

- Evaluation-data readiness is still false because the local DB has no active
  document corpus, persisted run evaluations, auto/generated regression corpus,
  hand-verified gold corpus, feedback ledgers, replay coverage, harness-source
  coverage, or retrieval-learning materialization.
- Hygiene remains intentionally strict and currently fails on oversized modules,
  especially `app/db/models.py`, `app/services/evidence.py`,
  `app/services/audit_bundles.py`, `app/services/claim_support_policy_impacts.py`,
  `app/services/retrieval_learning.py`, and `app/services/search.py`.
- The first model-domain split reduced `app/db/models.py`, but it remains the
  top architecture-quality hotspot and should not receive additional unrelated
  ORM concerns.
- The first evidence split reduced `app/services/evidence.py`, but it remains a
  major architecture-quality hotspot. Future evidence splits should move one
  owner concern at a time behind the same compatibility facade.
- The first agent-action registry split reduced
  `app/services/agent_task_actions.py`, but it remains a hotspot and part of the
  general architecture probe's large agent-task cycle component. Future
  action-family splits should move one owner concern at a time behind the same
  compatibility facade, starting with a search-harness executor dependency seam
  or a semantic executor family with isolated dependencies before moving executor
  paths.
- The first CLI command-group split reduced `app/cli.py`, but it remains a
  public operator hotspot and is not yet a globally thin dispatch surface.
  Future CLI splits should move one command group at a time behind explicit
  `app.cli` forwarding functions and pair each move with help or parser
  coverage.
- The first search-core split reduced `app/services/search.py`, but search
  remains a retrieval-quality hotspot. Future search splits should move one
  coherent concern at a time behind `app.services.search` compatibility names,
  with replay and ranking behavior covered before changing another search
  concern.
- The improvement-case registry has not yet imported the current
  architecture-quality hotspot candidates, so generated hotspot signals are not
  all represented as tracked cases.
- Court-grade readiness cannot be claimed until the live DB passes
  `docling-system-evaluation-data-readiness` with enough hand-verified fixtures,
  operator feedback, claim feedback, governed hard cases, replay coverage, and
  retrieval-learning materialization.

## Next Milestone

Milestone 0 is complete: local runtime verification is available. Milestone 1
is complete: the data-model compatibility harness is in place. Milestone 2 is
complete: `ApiIdempotencyKey` moved behind the `app.db.models` compatibility
facade. Milestone 3 is complete: search evidence package helpers moved behind
the `app.services.evidence` compatibility facade. Milestone 4 is complete:
search-harness action registry metadata and helper logic moved behind the
`app.services.agent_task_actions` compatibility facade. Milestone 5 is complete:
improvement-case CLI commands moved behind the `app.cli` compatibility facade.
Milestone 6 is complete: query-feature and query-intent helpers moved behind
the `app.services.search` compatibility facade.

The next architecture milestone is `Architecture Plan 01` Milestone 7: split
the next `app/services/evidence.py` concern while preserving the evidence
facade and artifact contracts.

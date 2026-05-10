# Architecture Plan 01

Date: 2026-05-09
Status: active plan; Milestones 0-4 complete; local commit-on-closeout policy
active as of 2026-05-09

Purpose: reduce centralization in the current modular monolith without
weakening the existing API, CLI, database, worker, retrieval, agent-task, or
architecture-governance contracts.

This plan is the next implementation sequence after the agentic architecture
governance milestones. The architecture boundary gate is green, but the system
is still too centralized in a small number of files. The work here is
behavior-preserving modularization, not a rewrite.

## Current Evidence

Current architecture signals:

- `uv run docling-system-architecture-inspect` is valid with
  `violation_count=0`.
- `uv run docling-system-capability-contracts` is valid across 6 facades and
  110 functions.
- `uv run docling-system-architecture-quality-report --summary` reports:
  - `agent_legibility_average_score=90.0`
  - `broad_facade_count=2`
  - `hotspot_count=10`
  - `max_hotspot_risk_score=687.04`
  - top hotspot paths:
    - `app/db/models.py`
    - `app/cli.py`
    - `app/services/evidence.py`
    - `app/services/agent_task_actions.py`
    - `tests/unit/test_cli.py`

Interpretation: this is not an architecture-contract failure. The weakness is
maintainability and change amplification. Central files are still large enough
that future agents and humans will copy local patterns from broad modules,
increasing entropy even when boundary checks remain green.

## Goal

Make the repo easier to change safely by reducing the size, fan-in, and
conceptual load of the current hotspots while preserving the existing modular
monolith shape:

- public capability facades remain stable
- `app.db.models` remains import-compatible until all callers can safely move
- external API, CLI command, database table, enum, artifact, and response
  contracts remain stable unless a milestone explicitly changes one
- each milestone lands as an atomic, verified slice with updated docs and
  handoff notes when behavior or operating rules change
- each milestone is committed locally before the next milestone begins

## Non-Goals

- No microservice extraction.
- No schema redesign as part of a model split.
- No table renames, enum value changes, relationship rewrites, or generated
  expression changes during behavior-preserving model moves.
- No broad rewrite of search, evidence, CLI, or agent-task orchestration.
- No YAML or manually curated docs becoming a source of truth for runtime
  behavior.
- No "clean code" pass that cannot show a reduced hotspot, cleaner contract, or
  smaller future change surface.

## Architecture Method

Use the `code-architecture-governance` workflow for this sequence:

1. Start from live repo artifacts, not chat history.
2. Pick one hotspot per milestone.
3. Keep public facades stable while splitting internal implementation modules.
4. Design the gate before editing.
5. Prefer deep modules with narrow public surfaces over shallow wrapper layers.
6. Convert repeated architecture lessons into tests, generated maps, contract
   fields, or improvement cases.
7. Stop before schema, service-boundary, or destructive changes that cannot be
   verified locally.

The architecture skill is the right mechanism because this is a governance and
evolution problem, not a framework-selection problem. The desired movement is:

```text
contract green + centralized internals
  -> contract green + narrower owner modules + executable verification
```

## Completion And Local Commit Policy

A milestone is not complete until the implementation, verification, docs, and
local commit are all done. Treat the local commit as part of the milestone gate,
not as a later cleanup task.

Required closeout order:

1. Finish only the scoped milestone change.
2. Run focused tests that prove the moved or guarded contract still behaves the
   same.
3. Run the cross-milestone architecture and quality gates in this plan.
4. Run DB-backed integration tests for any DB, API, storage, search, evidence,
   agent-task, worker, or runtime-facing change.
5. Refresh closeout docs: always update `docs/SESSION_HANDOFF.md` and this
   active milestone plan, then refresh any other affected durable docs.
6. Run `git diff --check` after final docs edits.
7. Review `git status --short`, `git diff --stat`, and staged diff scope.
8. Stage only the milestone slice.
9. Commit locally on `main` with a message that names the milestone.

Push is not automatic. Push only when explicitly requested after local commit
verification.

Commit command shape:

```bash
git status --short
git diff --stat
git add path/to/milestone-file ...
git diff --cached --stat
git commit -m "architecture: complete milestone <N> <short-name>"
git status -sb
```

If unrelated dirty files are present, leave them unstaged. If a required gate
cannot run, do not commit the milestone; record the blocker in the handoff with
the exact command, failure, and next action.

## Acceptance Criteria Standard

Each milestone's acceptance criteria must be concrete enough that a future
agent can prove completion without trusting prose. Acceptance must include:

- Contract proof: public imports, API payloads, CLI command names, action
  manifest entries, DB table names, enum values, artifact paths, and response
  shapes remain stable unless the milestone explicitly changes them.
- Behavioral proof: focused unit tests cover the moved concern or newly guarded
  contract.
- Runtime proof: DB-backed tests run with
  `DOCLING_SYSTEM_RUN_INTEGRATION=1` when the milestone touches persistence,
  routes, storage artifacts, search, evidence, agent tasks, workers, or
  runtime promotion paths.
- Schema proof: model or migration milestones run Alembic head/current/upgrade
  checks, Alembic autogenerate drift checks, and the
  `Base.metadata.create_all(...)` Postgres verification path.
- Architecture proof: architecture inspection, capability contracts, and the
  quality summary remain current after edits.
- Documentation proof: this plan, affected boundary docs, and
  `docs/SESSION_HANDOFF.md` match the implemented state.
- Git proof: the milestone is represented by one local commit containing only
  the verified milestone slice.

No milestone may be accepted by reducing test coverage, relying on skipped
Postgres-backed tests, or treating a green architecture inspection as a
substitute for runtime verification.

## Milestone Sequence

### Milestone 0: Restore Runtime Verification

Status: complete on 2026-05-09.

Goal: make the DB-backed gate available before touching model or persistence
boundaries.

Rationale: `app/db/models.py` is the top governed hotspot, but model movement is
unsafe without live Postgres, Alembic, and `Base.metadata.create_all(...)`
verification.

Scope:

- Start Docker/Postgres or point `DOCLING_SYSTEM_DATABASE_URL` at a working
  local Postgres.
- Verify the current system before any architecture split.
- Do not change application code in this milestone unless a local runtime issue
  blocks verification and the fix is required to make the existing system run.

Required commands:

```bash
docker compose ps
uv run --extra dev alembic heads
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run docling-system-evaluation-data-readiness
uv run docling-system-agent-trace-review --limit 5 --skip-hygiene
uv run docling-system-architecture-quality-report --summary
```

Acceptance:

- Docker/Postgres or equivalent local Postgres is available.
- Alembic has a single head.
- Full integration tests run with Postgres-backed coverage instead of silent
  skips.
- Runtime readiness and trace review either pass or produce specific tracked
  blockers.

Stop conditions:

- Docker daemon is unavailable and no alternative Postgres URL is provided.
- Integration tests skip DB coverage.
- Alembic has multiple heads.
- Runtime readiness fails for a code issue unrelated to architecture planning.

Closeout:

- Update `docs/SESSION_HANDOFF.md` with the runtime state.
- If blockers remain, record the exact command, failure, and next action.
- Commit any runtime-gate docs or fixes locally before Milestone 1 begins.

Implemented result:

- Docker Desktop is running.
- `docling-system-db` is healthy on `localhost:5432`.
- `docling-system-worker` and `docling-system-agent-worker` are running.
- Alembic has a single head: `0076_claim_feedback_replay_src`.
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` passed with
  `872 passed in 51.00s`.
- `uv run docling-system-evaluation-data-readiness` now reaches Postgres and
  reports expected empty-corpus blockers instead of a connection failure.
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene` now
  reaches Postgres and reports `observation_count=0`.

Milestone 1 is unblocked.

### Milestone 1: Data Model Compatibility Harness

Status: complete on 2026-05-09.

Goal: make `app/db/models.py` splittable before moving any ORM classes.

Rationale: the safest first step is to prove the current import and metadata
contract. That gives every later model-domain split a fixed acceptance target.

Scope:

- Add tests that enumerate representative existing imports from
  `app.db.models`.
- Add a metadata registration test that proves expected table names remain in
  `Base.metadata`.
- Add a create-all verification helper or test path that can run against local
  Postgres without changing production schema.
- Document the first domain to move and why.

Likely files:

- `tests/unit/test_db_model_import_compatibility.py`
- `tests/integration/test_db_model_metadata.py` or an existing DB integration
  test surface
- `docs/data_model_boundary_plan.md`
- `docs/SESSION_HANDOFF.md`

Required commands:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_db_model_import_compatibility.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
```

Acceptance:

- Current `from app.db.models import X` imports remain explicitly protected.
- Metadata registration is covered before physical movement begins.
- Schema-scoped Postgres `Base.metadata.create_all(...)` coverage proves the
  expected table contract.
- No ORM class is moved yet unless the compatibility harness is already passing.
- The harness and docs are committed locally before Milestone 2 begins.

Stop conditions:

- The harness requires changing table definitions.
- The harness passes only by reducing coverage or skipping Postgres.
- The split design cannot preserve `app.db.models` as a compatibility facade.

Closeout:

- Commit as a standalone compatibility-harness milestone before moving model
  classes.
- Under the revised closeout policy, the current Milestone 1 working-tree slice
  must be committed locally before Milestone 2 begins.

Completed result:

- Added `tests/db_model_contract.py` as the shared model-boundary contract for
  expected public symbols, model domains, table names, and the first platform
  support table columns.
- Added `tests/unit/test_db_model_import_compatibility.py` to prove all current
  public `app.db.models` enum and ORM symbols remain importable from the
  compatibility facade.
- Added `tests/integration/test_db_model_metadata.py` to force the
  schema-scoped Postgres `Base.metadata.create_all(...)` path and verify all 80
  expected tables exist in the temporary schema.
- Synchronized the `DocumentRun` model metadata with the migrated
  `ix_document_runs_status_completed_at` cleanup index and added unit plus
  Postgres create-all coverage for required model indexes.
- No ORM classes were moved in this milestone.

Verification:

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
Full DB-backed suite: 1096 passed.
Ruff: passed.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid.
Architecture quality summary: hotspot_count=10, max_hotspot_risk_score=674.68.
Alembic check: no new upgrade operations detected.
```

Milestone 2 is unblocked. Use `platform support` as the first split domain
unless live evidence shows stronger coverage for an alternate first domain.

### Milestone 2: First Data Model Domain Split

Status: complete on 2026-05-09.

Goal: reduce `app/db/models.py` centrality by moving one low-risk model domain
behind an import-compatible facade.

Rationale: `app/db/models.py` has the highest governed risk score. The first
move should prove the package shape and verification method with the smallest
domain that still exercises table, enum, relationship, and metadata behavior.

Recommended first domain:

- `platform support`: `ApiIdempotencyKey`

Alternative first domain if coverage is stronger:

- `ingest`: `IngestBatch`, `IngestBatchItem`, `Document`, `DocumentRun`

Scope:

- Introduce a domain module such as `app/db/model_domains/platform.py`.
- Keep `app/db/models.py` as the public compatibility facade.
- Move one domain only.
- Preserve table names, enum values, relationship strings, indexes,
  constraints, metadata registration, and imports.
- Do not redesign schema.

Required commands:

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

Acceptance:

- Existing imports from `app.db.models` continue to work.
- Alembic has a single head, upgrades cleanly, and `alembic check` reports no
  unexpected model/schema drift.
- `Base.metadata.create_all(...)` verification passes against local Postgres.
- Full integration tests pass with DB-backed coverage.
- `app/db/models.py` line count and hotspot risk move in the right direction.
- The moved domain is represented by one local commit after docs and handoff are
  updated.

Stop conditions:

- Alembic detects schema drift.
- `Base.metadata.create_all(...)` changes emitted schema.
- Relationship resolution breaks.
- Any public `app.db.models` import breaks.

Closeout:

- Update `docs/data_model_boundary_plan.md` with the domain moved, verification
  result, and next domain candidate.
- Update `docs/SESSION_HANDOFF.md`.
- Commit the model-domain split locally before any second domain is moved.

Completed result:

- Added `app/db/model_domains/platform.py` as the first focused ORM model-domain
  module.
- Kept `app/db/models.py` as the public compatibility facade by re-exporting
  `ApiIdempotencyKey`.
- Moved only the `platform support` domain class: `ApiIdempotencyKey`.
- Preserved the `api_idempotency_keys` table name, columns, JSONB response
  storage, created-at index, and `scope` plus `idempotency_key` unique
  constraint.
- Strengthened the model compatibility harness so unit and Postgres
  `create_all` paths now verify required platform-support indexes, unique
  constraints, and their exact column ordering, not only table columns.
- Reduced `app/db/models.py` to 6,006 lines while leaving the new platform
  domain module at 35 lines.

Verification:

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

Milestone 3 is complete. The evidence service now has a focused search evidence
package split while `app.services.evidence` remains the compatibility facade.

### Milestone 3: Evidence Service Split 01

Goal: split the first coherent evidence concern out of
`app/services/evidence.py` while keeping `app.services.evidence` as the public
facade.

Rationale: `evidence.py` is the largest service file and a high raw
churn-size hotspot. It mixes search evidence packages, technical-report
evidence, claim feedback ledgers, trace graphs, provenance exports, and
agent-task audit bundle assembly. This is exactly the kind of central module
that encourages future copy-paste expansion.

Recommended first extraction:

- search evidence package read/export/trace response helpers

Scope:

- Create a focused module such as `app/services/evidence_search_packages.py`.
- Move cohesive search-evidence package functions and private helpers only.
- Keep public imports available from `app.services.evidence`.
- Preserve response payloads, artifact paths, hashes, trace semantics, and
  route behavior.
- Do not touch technical-report, claim-support, or provenance-export logic in
  the same milestone.

Likely tests:

- evidence package unit tests, if present
- search history/API tests that inspect evidence packages
- route tests for missing artifact/error behavior if touched
- focused tests for compatibility exports from `app.services.evidence`

Required commands:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_evidence_common.py tests/unit/test_evidence_records.py tests/unit/test_evidence_provenance.py
uv run pytest -q tests/unit/test_search_api.py tests/unit/test_search_service.py tests/unit/test_search_history.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_evidence_operator_runs_roundtrip.py
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Acceptance:

- `app.services.evidence` remains import-compatible for moved functions.
- Search evidence package behavior is unchanged.
- The extracted module has a clear owner concern and bounded public surface.
- `evidence.py` hotspot risk decreases.
- Storage-backed artifact and missing-file error behavior remain covered when a
  moved function touches artifact routes or payload assembly.
- The milestone lands as one local commit after docs and handoff are updated.

Stop conditions:

- The extraction requires changing API payload shape.
- The extraction needs schema changes.
- The compatibility facade becomes a duplicate implementation instead of a
  forwarding surface.

Closeout:

- Update this plan if the next evidence domain changes.
- Update `docs/SESSION_HANDOFF.md` with verification and residual risk.
- Commit the evidence split locally before starting another evidence concern.

Completed result:

- Moved search evidence package assembly, export persistence, trace graph
  persistence, trace integrity, and response assembly into:
  - `app/services/evidence_search_packages.py`
  - `app/services/evidence_search_trace_graph.py`
  - `app/services/evidence_search_trace_store.py`
- Kept `app.services.evidence` import-compatible for
  `get_search_evidence_package`, `persist_search_evidence_package_export`,
  `export_search_evidence_package`, and
  `get_search_evidence_package_export_trace`.
- Preserved legacy private record-helper aliases on `app.services.evidence`
  while moving shared trace row/spec helpers into `app/services/evidence_common.py`
  and the shared evidence export payload helper into
  `app/services/evidence_records.py`.
- Reduced `app/services/evidence.py` from 9,502 lines to 8,608 lines. The new
  search-evidence modules are 338, 421, and 296 lines, keeping each new owner
  module under the hygiene file budget.

Verification:

```text
git diff --check: passed.
Ruff: passed.
Evidence helper tests: 27 passed.
Search API/service/history tests: 70 passed.
Search evidence operator-run roundtrip: 1 passed.
Full DB-backed suite: 1109 passed in 47.48s.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture decisions: valid, decision_count=9.
Architecture quality summary: hotspot_count=10, max_hotspot_risk_score=687.04.
Hygiene: no ruff, vulture, duplicate-helper, improvement-case, or architecture
findings; inherited file/helper budget debt remains.
```

Milestone 4 is unblocked. The next architecture milestone is the first
agent-task action registry split.

### Milestone 4: Agent Task Action Registry Split 01

Status: complete on 2026-05-09.

Goal: reduce `app/services/agent_task_actions.py` by turning it into registry
composition plus domain action modules.

Rationale: agent actions are a public tool surface for future agents. The
action catalog currently has strong contracts, but the implementation file is
still too broad and participates in a large agent-action import cycle in the
general architecture probe.

Recommended first extraction:

- semantic action executors, or search-harness action executors, whichever has
  the most isolated tests

Scope:

- Create focused modules under `app/services/agent_actions/`.
- Move one action family and its private helpers.
- Keep `list_agent_task_actions`, `build_agent_task_action_manifest`,
  `build_agent_task_action_index`, `validate_agent_task_action_contracts`,
  `get_agent_task_action`, and execution entrypoints stable.
- Preserve task type strings, input/output schemas, side-effect levels,
  approval requirements, examples, context builders, and response payloads.

Required commands:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_agent_task_actions.py tests/unit/test_agent_action_contracts.py
uv run pytest -q tests/unit/test_agent_tasks_api.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py
uv run docling-system-agent-task-action-index
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Acceptance:

- The agent action manifest and index remain stable except for intentional
  source-location changes.
- Moved action executors remain available through the public registry.
- No action type, schema, or side-effect contract changes.
- The general import-cycle signal is reduced or the remaining cycle is
  documented with a next split target.
- DB-backed orchestration roundtrips still pass for moved action families that
  create tasks, attempts, outcomes, artifacts, or context rows.
- The milestone lands as one local commit after docs and handoff are updated.

Stop conditions:

- A moved action changes task input or output behavior.
- Context builder names drift.
- Action registration order becomes nondeterministic.
- Tests require broad fixture rewrites unrelated to the move.

Closeout:

- Update `docs/architecture_boundaries.md` only if the action-module boundary
  rule changes.
- Update `docs/SESSION_HANDOFF.md`.
- Commit the action-family split locally before moving another family.

Completed result:

- Added `app/services/agent_actions/search_harness.py` as the first focused
  agent-action registry family module.
- Moved search-harness action contract metadata and helper logic for:
  `optimize_search_harness_from_case`,
  `draft_harness_config_update_from_optimization`, `replay_search_request`,
  `run_search_replay_suite`, `evaluate_search_harness`,
  `verify_search_harness_evaluation`, `draft_harness_config_update`,
  `verify_draft_harness_config`, `triage_replay_regression`, and
  `apply_harness_config_update`.
- Kept `app/services/agent_task_actions.py` as the public compatibility facade
  and execution entrypoint. Executor import paths remain available for current
  tests and operator-facing behavior.
- Preserved all task type strings, payload/output schemas, side-effect levels,
  approval requirements, context-builder names, input examples, response
  payloads, action index output, and manifest validation behavior.
- Added focused contract coverage proving the search-harness action family is
  represented by the focused registry module.
- Reduced `app/services/agent_task_actions.py` from 3,320 lines to 2,884
  lines. The new search-harness registry/helper module is 539 lines.

Verification:

```text
git diff --check: passed.
Ruff: passed across app and tests.
Focused agent-action contract/action tests: 136 passed.
DB-backed semantic and triage orchestration roundtrips: 9 passed.
Full DB-backed suite: 1110 passed in 48.43s.
Agent task action index: generated successfully.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture decisions: valid, decision_count=9.
Architecture quality summary: agent_legibility_average_score=90.0,
broad_facade_count=2, hotspot_count=10, max_hotspot_risk_score=687.04.
Hygiene: no ruff, vulture, improvement-case, or architecture findings;
inherited file/helper budget debt remains.
```

Milestone 5 is unblocked. The next architecture milestone is the first
operator-facing CLI command group split.

### Milestone 5: CLI Command Group Split

Goal: split `app/cli.py` into capability-oriented command modules while
preserving every console entrypoint and help contract.

Rationale: `app/cli.py` is a high-risk hotspot because it is a public operator
surface with many commands and a large mirrored test file. CLI changes are easy
to break subtly through argument, output, and exit-code drift.

Scope:

- Introduce `app/cli_commands/`.
- Move one command group at a time, starting with the least DB-sensitive group.
- Keep existing console scripts and top-level function names stable.
- Do not combine command migration with service behavior changes.
- Add help-output or parser compatibility tests for each moved command group.

Candidate command groups:

- architecture/governance commands
- improvement-case commands
- search harness/replay commands
- ingest/evaluation commands
- knowledge-base reset commands

Required commands:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_cli.py
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
```

Acceptance:

- Existing CLI tests pass.
- Console entrypoints resolve to the same callable names.
- Help text and required/optional arguments remain compatible unless an
  intentional change is documented.
- `app/cli.py` becomes a thin compatibility and dispatch surface.
- The moved command group has direct help/parser coverage or an existing CLI
  regression test that fails on argument or exit-code drift.
- The milestone lands as one local commit after docs and handoff are updated.

Stop conditions:

- Command behavior changes without explicit acceptance.
- Help text drifts in a way that invalidates existing operator docs.
- Command migration requires service behavior changes.

Closeout:

- Update README command examples only if visible command usage changes.
- Update `docs/SESSION_HANDOFF.md`.
- Commit the CLI command-group split locally before moving another command
  group.

### Milestone 6: Search Core Split 01

Goal: continue reducing `app/services/search.py` by isolating one internal
search concern behind stable public search functions.

Rationale: search is central to retrieval quality and eval loops. It should be
modular enough that query planning, candidate retrieval, scoring, hydration,
and explanation payloads can evolve independently.

Recommended first extraction:

- query feature extraction and query-intent helpers, or result hydration,
  depending on which has cleaner focused coverage at implementation time

Scope:

- Keep `execute_search` and `search_documents` stable.
- Move one coherent internal concern into a focused module.
- Preserve ranking behavior, result shape, telemetry, search request records,
  trace payloads, and replay compatibility.
- Do not retune ranking weights as part of the split.

Required commands:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_api.py
uv run pytest -q tests/unit/test_search_history.py tests/unit/test_search_replays.py tests/unit/test_search_release_gate.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_search_replays_roundtrip.py tests/integration/test_search_harness_releases.py
uv run docling-system-run-replay-suite --help
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Acceptance:

- Search results and replay outputs remain behaviorally equivalent for existing
  tests.
- Extracted module has a bounded public surface.
- `search.py` hotspot risk decreases without making retrieval facade broader.
- Replay and release-gate contracts remain executable after the split.
- The milestone lands as one local commit after docs and handoff are updated.

Stop conditions:

- Ranking behavior changes without an explicit eval-backed reason.
- Replay compatibility breaks.
- The split requires search schema or API changes.

Closeout:

- Update retrieval/search docs only if the public contract changes.
- Update `docs/SESSION_HANDOFF.md`.
- Commit the search-core split locally before moving another search concern.

### Milestone 7: Evidence Service Split 02

Goal: continue `evidence.py` decomposition after the first extraction proves
the facade pattern.

Candidate domains:

- technical-report evidence closure
- claim derivation and retrieval feedback ledger
- evidence trace graph persistence
- agent-task audit bundle and provenance export

Selection rule:

- Choose the domain with the highest combination of churn, failing tests,
  review friction, and caller breadth at the time of implementation.

Gate:

- Same as Milestone 3, plus focused tests for the selected domain.

Acceptance:

- One additional evidence concern becomes a focused owner module.
- Public facade compatibility remains intact.
- No schema or artifact contract drift.
- Focused tests for the selected evidence domain pass before the full
  DB-backed integration gate.
- The milestone lands as one local commit after docs and handoff are updated.

### Milestone 8: Improvement Intake Ratchet

Goal: make current hotspot findings durable improvement cases so architecture
work remains queued and measurable.

Rationale: the handoff says generated hotspot candidates are not all represented
as tracked cases. If the architecture quality report is the source of hotspot
truth, its candidates should feed the improvement registry.

Scope:

- Generate `build/architecture-governance/architecture_quality_report.json`.
- Dry-run architecture-quality improvement-case import.
- Resolve dedupe behavior and source identifiers.
- Record accepted hotspot cases with owner surface, verification command, and
  stop condition.

Required commands:

```bash
git diff --check
uv run docling-system-architecture-quality-report --output-path build/architecture-governance/architecture_quality_report.json
uv run docling-system-improvement-case-import --source architecture-quality-report --source-path build/architecture-governance/architecture_quality_report.json --dry-run
uv run docling-system-improvement-case-summary
uv run docling-system-hygiene-check
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
```

Acceptance:

- Current top hotspot candidates are represented in the improvement flow or
  explicitly deduped.
- Each accepted case has an owner surface and verification command.
- Hygiene does not gain new non-budget regressions.
- Generated architecture-quality input is refreshed in the same milestone if it
  is committed or used as evidence.
- The milestone lands as one local commit after docs and handoff are updated.

Stop conditions:

- Import dedupe would create duplicate cases for the same hotspot.
- Generated report path or source vocabulary is unstable.
- Improvement-case status changes are not measurable.

## Cross-Milestone Verification Contract

Every implementation milestone must run:

```bash
git diff --check
uv run ruff check app tests
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
```

Every milestone must also record the focused test commands that prove the
specific moved contract. The focused commands are part of acceptance, not
optional supporting evidence.

Milestones touching DB models, migrations, API routes, storage-backed artifact
routes, search execution, evidence persistence, agent tasks, or runtime
workers must also run:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Milestones touching model definitions or Alembic must also run:

```bash
uv run --extra dev alembic heads
uv run --extra dev alembic current
uv run --extra dev alembic upgrade head
uv run --extra dev alembic check
# plus the repo's Base.metadata.create_all(...) verification path
```

If local Postgres is unavailable, do not close DB-backed milestones. Record the
blocker and switch to a non-DB hotspot only if the user agrees or the current
milestone explicitly allows it.

Before every milestone commit, run:

```bash
git status --short
git diff --stat
git diff --cached --stat
```

The staged diff must contain only the milestone slice and affected docs.
Unrelated dirty or untracked files must stay unstaged.

## Documentation Contract

Each milestone closeout must update durable docs before the milestone commit.
Closeout docs are mandatory even when the code/test slice is already complete:

- `docs/SESSION_HANDOFF.md`: always update for milestone closeout.
- `docs/architecture_plan_01.md`: always update status, verification evidence,
  residual risk, and next milestone routing for this architecture sequence.
- `docs/data_model_boundary_plan.md`: update for model split work.
- `docs/architecture_boundaries.md`: update only for boundary-policy changes.
- `README.md` or `SYSTEM_PLAN.md`: update only when user-facing capability or
  operator behavior changes.

Do not leave milestone state only in chat.

Do not defer the commit after docs are updated. A milestone with passing tests
but no local commit is an open working-tree state, not a closed milestone.

## Priority Order

Use this order unless live evidence changes:

1. Restore runtime verification.
2. Add model import/metadata compatibility harness.
3. Move one low-risk model domain behind `app.db.models`.
4. Split search evidence packages out of `app/services/evidence.py` (complete).
5. Split one agent-task action family out of `app/services/agent_task_actions.py`.
6. Split one CLI command group out of `app/cli.py`.
7. Split one search core concern out of `app/services/search.py`.
8. Import or dedupe architecture-quality hotspot improvement cases.

If runtime verification remains blocked, start with the evidence split only
after recording the runtime blocker and confirming the split does not touch
schema, migrations, active-run promotion, or DB create-all behavior.

## Success Definition

This plan is succeeding when:

- architecture inspection remains green
- capability contracts remain green
- full integration verification is available for DB-backed milestones
- hotspot risk for the top files trends downward
- `app/db/models.py`, `app/services/evidence.py`, `app/cli.py`,
  `app/services/agent_task_actions.py`, and `app/services/search.py` become
  compatibility or orchestration surfaces instead of dense implementation
  centers
- future agents can locate the right owner module and verification command
  without rereading broad chat history

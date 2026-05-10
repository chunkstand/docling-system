# Residual Weakness Resolution Milestone Plan

Date: 2026-05-10
Status: in progress; Milestone 1 complete
Owner context: follow-on plan after `Architecture Plan 01` Milestones 0-8.

## Purpose

Resolve the remaining weaknesses identified after the `Architecture Plan 01`
closeout:

- no strict diff-time gate prevents new implementation growth in known hotspots
- top hotspots remain in the data model, CLI, evidence, agent-task, and CLI test
  surfaces
- the architecture probe still reports 3 Python cycle components, including the
  large agent-task cycle
- evaluation-data readiness remains false on the empty local DB
- strict hygiene budget debt remains across large implementation modules

This plan turns those weaknesses into milestone-sized implementation slices with
owner surfaces, executable prevention gates, and closeout criteria. It is a
follow-on architecture and readiness sequence, not a rewrite.

## Current Evidence

Refreshed on 2026-05-10:

```text
uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=693.04
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/evidence.py,
    app/services/agent_task_actions.py,
    tests/unit/test_cli.py
  ]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  Python cycle components: 3
  top hotspot score: app/db/models.py = 420420
  app/services/evidence.py = 8261 lines, score 380006
  app/services/agent_task_actions.py fan-out = 39 local modules

uv run docling-system-hygiene-check
  failed only strict duplicate/file-budget findings
  no ruff regressions
  no improvement-case findings
  no architecture findings

uv run docling-system-evaluation-data-readiness
  regression_ready=false
  court_grade_ready=false
  passed_gate_count=0
  failed_gate_count=11
```

The architecture contract is green, but maintainability, prevention, and
readiness are not complete.

## Goal

Close the remaining weakness set without weakening the repo's existing
contracts:

- block new implementation growth in known hotspots at diff time
- turn inherited strict-hygiene debt into ratcheted, owner-scoped work instead
  of permanent tolerated failure
- continue hotspot splits behind stable public facades
- remove the large agent-task cycle component or reduce it to a documented,
  narrow orchestration cycle with a failing gate for new cycles
- make evaluation-data readiness pass first at `regression_ready=true`, then at
  `court_grade_ready=true`
- close every milestone with focused tests, architecture gates, updated docs,
  and an atomic local commit

## Non-Goals

- No microservice extraction.
- No schema redesign unless a later milestone explicitly scopes and verifies it.
- No DB table, enum, API, artifact, CLI, or public import contract changes as a
  side effect of modularization.
- No suppressing hygiene findings by loosening budgets without a ratchet and an
  owner surface.
- No declaring court-grade readiness from docs alone; the live readiness command
  must pass.
- No broad "clean code" sweep across unrelated files.

## Scope

In scope:

- architecture and hotspot prevention gates
- hygiene budget ratchets and strict-debt reduction
- additional facade-preserving splits for known hotspots
- import-cycle reduction focused on the agent-task component first
- live evaluation-data readiness work and supporting runbooks
- docs, handoff, generated architecture reports, and improvement-case status
  updates needed to prove closeout

Out of scope:

- unrelated UI polish
- new product features that do not close one listed weakness
- remote deployment or CI changes unless a milestone explicitly routes the new
  gate there after local behavior is proven
- changing runtime source-of-truth rules for canonical JSON, derived YAML,
  active-run promotion, or evaluation artifacts

## Owner Surfaces

- Hotspot prevention: `docs/hotspot_prevention_gate_milestone_plan.md`,
  `config/hotspot_prevention.yaml`, `app/hotspot_prevention.py`, CLI entrypoint,
  and focused gate tests.
- Hygiene ratchet: `config/hygiene_policy.yaml`, `app/hygiene.py`,
  `config/improvement_cases.yaml`, `docs/improvement_loop.md`.
- Data model split: `app/db/models.py`, `app/db/model_domains/`,
  `tests/db_model_contract.py`, DB metadata/create-all tests, Alembic checks.
- CLI split: `app/cli.py`, `app/cli_commands/`, console-script forwarding
  tests, `tests/unit/test_cli.py`, focused `tests/unit/test_cli_*.py` files.
- Evidence and audit splits: `app/services/evidence.py`,
  `app/services/evidence_*.py`, `app/services/audit_bundles.py`,
  technical-report and search-evidence tests.
- Search and retrieval-learning splits: `app/services/search.py`,
  `app/services/search_*.py`, `app/services/retrieval_learning.py`,
  search/replay/ranking tests.
- Agent-task cycle break: `app/services/agent_task_actions.py`,
  `app/services/agent_actions/`, `app/services/agent_task_context*.py`,
  `app/services/agent_tasks.py`, action index and agent-task tests.
- Evaluation-data readiness: `docs/evaluation_data_readiness.md`,
  `docs/evaluation_corpus.yaml`, `storage/evaluation_corpus.auto.yaml`,
  persisted evaluation rows, replay/harness rows, feedback ledgers, and
  retrieval-learning materialization.
- Durable docs: `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, this plan, affected boundary/runbook
  docs, and active milestone status docs.

## Placement Rules

- Keep large public modules as compatibility facades until all callers can move.
- Place new implementation in existing focused owner directories:
  `app/db/model_domains/`, `app/cli_commands/`,
  `app/services/agent_actions/`, and focused `app/services/<domain>_*.py`
  modules.
- Place new tests beside the concern they protect instead of adding broad test
  groups to existing hotspot test files.
- Keep YAML as derived or human-readable output; readiness, search, and
  evaluation gates must use DB fields, canonical JSON artifacts, or typed
  service contracts.
- Every new exception to a prevention or hygiene gate must cite an improvement
  case ID or milestone ID, owner surface, and expiration or follow-up condition.

## Weak-Point Prevention Contract

Weak point forecast: future work could fix one listed weakness while creating a
new hotspot, hiding inherited hygiene debt, breaking facade compatibility,
preserving the agent-task cycle under a different import path, or claiming
evaluation readiness from prose instead of live data. Each forecasted weakness
has an owner surface, executable prevention gate, fail threshold, and controlled
violation below.

| Weak point | Owner surface | Prevention gate | Fail threshold | Controlled violation |
| --- | --- | --- | --- | --- |
| New hotspot implementation growth | `config/hotspot_prevention.yaml`, `app/hotspot_prevention.py` | `uv run docling-system-hotspot-prevention-check --strict` | Any new blocked implementation category in a known hotspot without a valid exception | Fixture diff adds a private helper to `app/services/evidence.py` and strict mode exits non-zero |
| Permanent strict-hygiene debt | `config/hygiene_policy.yaml`, `app/hygiene.py` | `uv run docling-system-hygiene-check` plus ratchet summary | A touched strict-debt file grows file/helper debt or lacks a ratchet case | Fixture or unit test increases a tracked file budget and fails the hygiene ratchet |
| Facade split breaks callers | Public facade modules and focused owner tests | Focused compatibility tests plus capability contracts | Public imports, CLI names, action types, DB metadata, or API payloads change unintentionally | Test imports moved names through the original facade and compares owner module identity |
| Agent-task cycle survives by moving imports around | Agent-task action/context/service modules | Architecture probe cycle gate plus action index | Large agent-task cycle remains after the cycle-break milestone, or a new cycle appears | Fixture or test module creates a forbidden action/context back-import and fails the cycle gate |
| Evaluation readiness becomes prose-only | Readiness command and live DB evidence | `uv run docling-system-evaluation-data-readiness` | `regression_ready=false` after the regression milestone, or `court_grade_ready=false` after the court-grade milestone | Empty DB or missing feedback source fixture remains a failing readiness gate |
| Future Codex adds tests to broad files | `tests/unit/test_cli.py`, agent/evidence/search test suites | Hotspot prevention plus focused test placement review | New broad test group lands in a known test hotspot when a focused file exists | Fixture diff adds a new CLI command group test to `tests/unit/test_cli.py` and strict mode fails |

Future-Codex misuse scenario: the likely failure is adding "just one helper" to
the current broad module because the facade is already imported by callers. The
prevention gates must name the preferred owner module and fail before commit,
so the correct path is visible in the tool output rather than only in this plan.

## Milestone Sequence

### Milestone 0: Residual Baseline Lock

Status: planned.

Purpose: freeze current evidence before changing gates or splitting more code.

Scope:

- Regenerate current architecture-quality, architecture-probe, hygiene, and
  evaluation-readiness evidence.
- Record the current hotspot, cycle, hygiene, and readiness values in this plan
  or the handoff.
- Confirm `config/improvement_cases.yaml` still validates and still contains the
  architecture-quality cases imported during `Architecture Plan 01` Milestone 8.

Acceptance:

- `uv run docling-system-architecture-quality-report --summary` reports the
  current top hotspots.
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
  records current cycles, file sizes, fan-out, and hotspot scores.
- `uv run docling-system-hygiene-check` records only inherited strict budget
  debt unless a new regression exists.
- `uv run docling-system-evaluation-data-readiness` records exact failing gates.
- `uv run docling-system-improvement-case-validate` passes.

Closeout:

- Update `docs/SESSION_HANDOFF.md` with the baseline snapshot.
- Commit only the baseline docs or generated evidence that the milestone chooses
  to track.

### Milestone 1: Hotspot Prevention Gate

Status: complete.

Purpose: implement the existing prevention plan before more split work.

Source plan: `docs/hotspot_prevention_gate_milestone_plan.md`.

Scope:

- Add tracked hotspot policy.
- Add deterministic diff analyzer and strict CLI gate.
- Cover blocked additions, allowed facade maintenance, deletion-only reductions,
  and expiring exceptions.
- Make the gate part of architecture closeout docs.

Acceptance:

- `uv run docling-system-hotspot-prevention-check --strict` passes on a clean
  checkout.
- Fixture diffs that add implementation to `app/db/models.py`, `app/cli.py`,
  `app/services/evidence.py`, `app/services/agent_task_actions.py`,
  `app/services/search.py`, and `tests/unit/test_cli.py` fail strict mode.
- Fixture diffs that move logic out and leave compatibility forwarding pass.
- Gate output names the preferred owner module and failed policy rule.
- `uv run pytest -q tests/unit/test_hotspot_prevention.py` passes.

Completed result:

- Added tracked policy in `config/hotspot_prevention.yaml`.
- Added deterministic diff analyzer and CLI in `app/hotspot_prevention.py`.
- Split policy, diff parsing, and classification into focused
  `app/hotspot_prevention_*.py` modules so the gate does not add new
  file-budget debt.
- Added `docling-system-hotspot-prevention-check` as a standalone entrypoint.
- Added focused policy, analyzer, exception, strict-mode, and entrypoint tests
  in `tests/unit/test_hotspot_prevention.py`.
- Hardened alignment coverage for `git diff --numstat` line-count reporting,
  expired exception failure, and `--base`/`--staged` diff selection.
- Updated architecture boundary and routing docs so future hotspot splits run
  the strict gate before closeout.

Stop conditions:

- Strict mode cannot distinguish deletion/move reductions from new growth.
- The gate needs broad unrelated changes before policy behavior is proven.

### Milestone 2: Hygiene Budget Ratchet

Status: planned.

Purpose: convert inherited strict-hygiene failures into enforceable
no-new-debt ratchets and owner-scoped reduction cases.

Scope:

- Add or tighten per-file baseline fields for strict-debt files.
- Report inherited debt separately from new regressions.
- Link each large module to an improvement case or milestone.
- Fail touched-file growth in strict-debt surfaces unless a valid exception is
  present.

Initial debt owners:

- `app/db/models.py`
- `app/services/evidence.py`
- `app/services/audit_bundles.py`
- `app/services/claim_support_policy_impacts.py`
- `app/services/retrieval_learning.py`
- `app/services/search.py`
- smaller near-budget governance modules only when touched

Acceptance:

- `uv run docling-system-hygiene-check` emits a stable inherited-debt section
  and a separate new-regression section.
- A touched strict-debt file cannot grow file/helper budget without a failing
  gate or valid exception.
- The ratchet does not require solving all inherited debt in one milestone.
- Tests prove both a tolerated inherited-debt baseline and a failing touched-file
  growth case.

### Milestone 3: Top Hotspot Split Pack A

Status: planned.

Purpose: reduce the top data-model, CLI, and CLI-test hotspots behind stable
facades.

Scope:

- Move the next low-risk ORM model domain from `app/db/models.py` into
  `app/db/model_domains/`.
- Move one more CLI command group from `app/cli.py` into `app/cli_commands/`
  while keeping explicit `app.cli` forwarding functions for console scripts.
- Split one broad CLI test group out of `tests/unit/test_cli.py` into a focused
  `tests/unit/test_cli_<command_family>.py` file.

Acceptance:

- `app.db.models` import compatibility tests still pass for existing public
  classes/enums.
- Postgres metadata/create-all tests pass for moved model domains.
- CLI entrypoint forwarding tests prove existing console-script callables still
  resolve through `app.cli`.
- Architecture quality shows non-growth for the moved hotspot files.
- Hotspot-prevention strict mode passes.

Verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_db_model_import_compatibility.py tests/unit/test_cli.py tests/unit/test_cli_<command_family>.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py
uv run --extra dev alembic heads
uv run --extra dev alembic current
uv run --extra dev alembic upgrade head
uv run --extra dev alembic check
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
```

### Milestone 4: Top Hotspot Split Pack B

Status: planned.

Purpose: reduce remaining evidence, audit, search, and retrieval-learning
implementation hotspots one owner concern at a time.

Scope:

- Move one coherent concern from `app/services/evidence.py` into a focused
  `app/services/evidence_*.py` owner module.
- Move one coherent concern from `app/services/audit_bundles.py` or
  `app/services/retrieval_learning.py` into a focused owner module.
- Move one coherent concern from `app/services/search.py` only after replay and
  ranking behavior are covered.

Acceptance:

- Existing public service import surfaces remain compatible.
- Focused tests prove moved helper identity or behavior through the public
  facade.
- Search, replay, evidence, and technical-report tests that touch the moved
  concern pass.
- Architecture quality and hygiene show no growth in the touched hotspot files.
- No new Python import-cycle component is introduced.

Stop conditions:

- A split requires changing persisted artifacts, search ranking semantics,
  support-judge behavior, or audit-bundle JSON without a separately scoped
  runtime milestone.

### Milestone 5: Agent-Task Cycle Break

Status: planned.

Purpose: remove the large agent-task import-cycle component and reduce
`app/services/agent_task_actions.py` fan-out.

Scope:

- Inspect the cycle component from the architecture probe.
- Introduce a narrow dependency seam between action definitions, context
  builders, executor implementations, task service operations, and verification
  services.
- Move one executor family into `app/services/agent_actions/` only after its
  dependencies are made directional.
- Preserve action type names, context-builder names, input/output models, action
  index output, and API behavior.

Acceptance:

- The architecture probe no longer reports the large agent-task cycle component.
- `app/services/agent_task_actions.py` fan-out is reduced below the current 39
  local modules or is explicitly documented as the orchestration entrypoint with
  no cycle participation.
- `uv run docling-system-agent-task-action-index` succeeds.
- Focused agent-task and action-contract tests pass.
- DB-backed agent-task roundtrips pass.

Verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_agent_task_actions.py tests/unit/test_agent_action_contracts.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py
uv run docling-system-agent-task-action-index
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
```

### Milestone 6: Regression Evaluation-Data Readiness

Status: planned.

Purpose: make the live database pass the regression-readiness tier before
claiming broad retrieval or reranker regression coverage.

Scope:

- Ingest and validate a representative active document corpus.
- Run persisted document evaluations.
- Populate or refresh auto-generated regression corpus data.
- Run replay suites for `evaluation_queries`, `live_search_gaps`, and
  `cross_document_prose_regressions`.
- Keep generated corpus artifacts and readiness report fresh.

Acceptance:

- `uv run docling-system-evaluation-data-readiness` reports
  `regression_ready=true`.
- Regression blockers are empty.
- `court_grade_ready` may remain false only with explicit remaining
  court-grade blockers.
- The readiness docs distinguish regression readiness from court-grade
  readiness.

Stop conditions:

- No representative PDFs are available for ingestion.
- OpenAI quota or runtime failures prevent evaluations and cannot be isolated
  from corpus setup.
- The readiness command fails due to code defects rather than missing data.

### Milestone 7: Court-Grade Evaluation-Data Readiness

Status: planned.

Purpose: make readiness strong enough for auditable technical-report and
claim-support gates.

Scope:

- Add hand-verified gold fixtures with exact source-page/span expectations.
- Label operator feedback across required feedback types.
- Generate technical-report claim feedback across required labels and statuses.
- Promote governed claim-support hard cases into an active replay-alert corpus.
- Run replay suites for every required source, including
  `technical_report_claim_feedback`.
- Run harness evaluations with all source types.
- Materialize retrieval-learning judgment sets and completed training runs from
  feedback, replay, and claim-feedback sources.

Acceptance:

- `uv run docling-system-evaluation-data-readiness` reports
  `court_grade_ready=true`.
- `failed_gate_count=0`.
- The report shows at least the configured thresholds for gold corpus,
  feedback, claim feedback, replay/harness source coverage, and
  retrieval-learning materialization.
- Generated readiness artifacts and docs are refreshed in the same milestone.

### Milestone 8: Residual Weakness Closeout

Status: planned.

Purpose: prove the five selected weaknesses are resolved or explicitly routed
with narrower residual risk.

Acceptance:

- Hotspot prevention strict mode is part of closeout and passes.
- Architecture quality shows no new hotspot growth and records reductions for
  the split milestones.
- Architecture probe reports no large agent-task cycle component and no new
  Python cycle component.
- Hygiene either passes strict budgets or fails only accepted, ratcheted debt
  with open owner-scoped cases and no touched-file growth.
- Evaluation-data readiness reports `court_grade_ready=true`, or the handoff
  explicitly states the remaining data-only blockers and why court-grade
  readiness is not being claimed.
- `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, this plan,
  readiness docs, and affected runbooks match the implemented state.

## Required Implementation Artifacts

- Hotspot prevention policy, analyzer, CLI, and tests.
- Hygiene ratchet policy updates and tests.
- Focused owner modules for each split.
- Compatibility tests for every public facade or entrypoint preserved by a
  split.
- Cycle-gate evidence from the architecture probe.
- Readiness artifacts and DB-backed evidence for regression and court-grade
  readiness milestones.

## Required Documentation And Handoff Updates

Every milestone must update:

- `docs/SESSION_HANDOFF.md`
- this plan's status and completed-result section
- `docs/agentic_architecture_index.md` when next routing changes

Update these only when affected:

- `docs/hotspot_prevention_gate_milestone_plan.md`
- `docs/architecture_boundaries.md`
- `docs/evaluation_data_readiness.md`
- `docs/improvement_loop.md`
- `README.md`
- `SYSTEM_PLAN.md`

## Required Verification Gates

Every milestone:

```bash
git diff --check
uv run ruff check app tests
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
uv run docling-system-hotspot-prevention-check --strict
```

Architecture split milestones:

```bash
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
uv run docling-system-hygiene-check
```

Runtime, DB, search, evidence, agent-task, worker, or readiness milestones:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Model or migration milestones:

```bash
uv run --extra dev alembic heads
uv run --extra dev alembic current
uv run --extra dev alembic upgrade head
uv run --extra dev alembic check
```

Readiness milestones:

```bash
uv run docling-system-evaluation-data-readiness
uv run docling-system-agent-trace-review --limit 5 --skip-hygiene
```

## Acceptance Criteria

The plan is complete when:

- all milestones are closed or explicitly rerouted with a documented stop
  condition
- the prevention gate blocks new hotspot implementation growth
- current top hotspots trend down or are ratcheted with owner-scoped cases
- the large agent-task cycle component is removed or made a narrow, documented,
  non-growing orchestration exception
- hygiene has no unowned strict debt and no touched-file growth
- evaluation-data readiness passes the tier being claimed
- full closeout verification and docs refresh are committed atomically

## Stop Conditions

Stop and update the handoff before continuing if:

- a milestone requires API, DB, CLI, action-type, or artifact contract changes
  outside its scope
- Postgres or runtime dependencies are unavailable for a DB-backed closeout
- OpenAI quota prevents readiness evidence and no local fallback can verify the
  data lane being claimed
- the hotspot or hygiene gate produces false positives that would block
  deletion-only or facade-preserving reductions
- import-cycle reduction requires a broad rewrite instead of a directional seam
- unrelated dirty files cannot be separated from the milestone slice

## Local Commit Closeout Policy

Each milestone closes as one local commit after verification passes:

```bash
git status --short
git diff --stat
git add <milestone files only>
git diff --cached --stat
git commit -m "<area>: complete residual weakness milestone <N> <short-name>"
git status -sb
```

Stage only the verified milestone slice. Leave unrelated dirty or untracked
files unstaged. Push remains separate and only happens when explicitly
requested.

## Residual Risks And Next Routing

Milestone 1 is complete. The first next milestone is Milestone 2, the hygiene
budget ratchet, so the repo can distinguish inherited strict-hygiene debt from
new regressions. Only then should the repo resume broad hotspot splits or
agent-task cycle reduction.

If evaluation-data readiness is needed for an external review sooner than the
architecture cleanup, Milestone 6 may run in parallel as an operational data
milestone, but it must not claim court-grade readiness until Milestone 7 passes.

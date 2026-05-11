# Evaluation Feedback Model-Domain Milestone Plan

Date: 2026-05-10 local
Status: Milestone 2 closeout committed locally as `b69c4f6` on 2026-05-11; broader owner case reduced
Owner context: bounded follow-up under the open architecture-governance owner
case for `app/db/models.py`. This milestone resolves the `evaluation feedback`
ORM concern inside the compatibility facade; it does not claim to retire the
entire `IC-F2A8110185EB` hotspot unless the governing architecture report no
longer flags that owner case after closeout.

## Purpose

Resolve the next routed model-domain concern inside `app/db/models.py` by
moving `EvalObservation` and `EvalFailureCase` into a focused owner module while
preserving the public `app.db.models` import contract, the exact Postgres
schema contract, and the current evaluation-feedback behavior. This milestone
exists to close a specific ownership gap inside the hotspot rather than merely
lowering line count without durable contract coverage.

## Current Evidence

Live repo signals refreshed before writing this milestone:

```text
uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=658.21
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/agent_task_actions.py,
    app/services/evidence.py,
    app/schemas/agent_tasks.py
  ]

uv run docling-system-improvement-case-summary
  case_count=26
  status_counts.open=25
  oldest_open_case_id=IC-F2A8110185EB

wc -l app/db/models.py
  3782 app/db/models.py

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  app/db/models.py score=283650
```

Repo-current artifact evidence:

- `docs/SESSION_HANDOFF.md` routes the next owner-scoped implementation slice
  to `IC-F2A8110185EB` / `app/db/models.py` with the `evaluation feedback`
  model-domain candidate.
- `docs/data_model_boundary_plan.md` names `EvalObservation` and
  `EvalFailureCase` as the next model-domain candidate when this owner case
  resumes.
- `config/improvement_cases.yaml` records `IC-F2A8110185EB` as still open with
  `app/db/models.py` at 3,782 lines.
- `app/db/models.py` still owns both `EvalObservation` and `EvalFailureCase`.
- `tests/db_model_contract.py` already classifies
  `EvalObservation` / `EvalFailureCase` under the `evaluation_feedback` domain
  symbol set and expected table names, but it does not yet expose a dedicated
  `EVALUATION_FEEDBACK_DOMAIN_TABLE_COLUMNS` contract or explicit required
  index/unique-constraint coverage for the evaluation-feedback tables. The
  missing shared harness coverage is the first gate to add before the move.

## Goal

Resolve the evaluation-feedback concern inside `app/db/models.py` by moving
`EvalObservation` and `EvalFailureCase` into a dedicated
`app/db/model_domains/evaluation_feedback.py` owner module behind the existing
`app.db.models` compatibility facade, with stronger shared contract coverage
than exists today.

## Non-Goals

- Do not claim to retire the full `IC-F2A8110185EB` hotspot unless the live
  architecture-quality report stops flagging `app/db/models.py`.
- Do not change table names, column names, enum-like check-constraint values,
  unique-constraint names, index names, foreign-key targets, or `ondelete`
  behavior.
- Do not redesign evaluation-feedback workflows, API behavior, failure-case
  lifecycle, or replay logic.
- Do not weaken test, fixture, lint, metadata, or Alembic gates to produce a
  green result.
- Do not mix unrelated model families into the same milestone.

## Scope

In scope:

- `EvalObservation` and `EvalFailureCase`
- a new focused owner module under `app/db/model_domains/`
- `app.db.models` import-forwarding updates needed to preserve compatibility
- shared metadata contract expansion for evaluation-feedback tables
- Postgres `create_all(...)` and Alembic drift verification for the moved
  models
- routing-doc updates for the moved concern and the next remaining
  `IC-F2A8110185EB` follow-up

Out of scope:

- agent-task, semantic-memory, claim-support, or retrieval-learning rows
- unrelated hotspot reductions in `app/services/evidence.py`,
  `app/services/agent_task_actions.py`, or `app/cli.py`
- report-only reductions that leave the evaluation-feedback concern in
  `app/db/models.py`

## Owner Surfaces

- hotspot facade:
  `app/db/models.py`
- new owner module:
  `app/db/model_domains/evaluation_feedback.py`
- compatibility and metadata harness:
  `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`
- migration / schema gates:
  `alembic/`,
  `uv run --extra dev alembic *`
- routing and current-state docs:
  this plan, `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`, and `docs/SESSION_HANDOFF.md`
- owner-case routing:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`

## Placement Rules

- Keep `app/db/models.py` as the public compatibility facade; do not update
  callers to import directly from the new domain module as part of this
  milestone.
- Put only the evaluation-feedback ORM family in the new module:
  `EvalObservation` and `EvalFailureCase`.
- Add shared contract constants for the evaluation-feedback tables in
  `tests/db_model_contract.py` instead of duplicating table/column expectations
  inside test bodies.
- Preserve exact index names, exact index column ordering, exact unique
  constraint names and column ordering, and the existing check-constraint
  value sets.
- Preserve relationship targets and nullable/`ondelete` semantics exactly; if a
  field is uncertain, verify from emitted Postgres metadata rather than ORM
  intuition.
- If a new helper or constant is needed for the moved models, place it in the
  new owner module unless it is already a cross-domain compatibility symbol.

## Weak-Point Prevention Contract

Weak point forecast:
This split could appear clean while silently weakening the schema harness,
dropping index or unique-constraint checks for `eval_observations` and
`eval_failure_cases`, changing emitted DDL, or loosening tests just enough to
pass after the move. It could also leave the concern effectively unresolved by
moving code without preserving the public `app.db.models` contract.

Owner surface:
`app/db/models.py`, the new `app/db/model_domains/evaluation_feedback.py`
module, the shared DB model contract tests, Alembic verification, and the
routing docs that define what counts as resolved for this milestone.

Prevention gate:

- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `git diff --check`

Fail threshold:

- `EvalObservation` or `EvalFailureCase` remain defined in `app/db/models.py`
  as full ORM implementations rather than compatibility re-exports
- any `app.db.models` import for the moved symbols breaks
- the evaluation-feedback tables lose exact column coverage, exact index
  coverage, or exact unique-constraint coverage in the shared contract harness
- Alembic emits unexpected drift or `Base.metadata.create_all(...)` does not
  reproduce the expected schema in Postgres
- tests become easier by deletion, looser assertions, reduced negative-path
  coverage, or removal of exact metadata checks

Controlled violation:

- temporarily remove one moved symbol from the `app.db.models` re-export path
  and verify the import-compatibility test fails
- temporarily change one expected evaluation-feedback unique-constraint or
  index-column ordering entry and verify the Postgres metadata gate fails

Future-Codex misuse scenario:
The most likely bad follow-up is moving the classes into a new file while
dropping exact metadata checks because the symbols already exist in the public
contract set. This milestone prevents that by requiring the evaluation-feedback
tables to gain dedicated shared column/index/unique harness coverage before the
move, and by treating weakened coverage as a milestone failure rather than an
acceptable shortcut.

## Milestone Sequence

### Milestone 0: Preflight Baseline Lock

Outcome label: `reduced`

Purpose:
Freeze the exact baseline and prove the repo is ready for a behavior-preserving
model-domain move before any ORM code changes begin.

Scope:

- refresh the current `app/db/models.py` hotspot measurements from live
  commands and record them in this plan or the handoff
- confirm the routed owner case, routed next-candidate docs, and current plan
  all agree on `EvalObservation` / `EvalFailureCase`
- confirm local Postgres-backed verification is available for the full
  `Base.metadata.create_all(...)`, Alembic, and DB-backed pytest gates
- add the missing shared evaluation-feedback contract coverage to the baseline
  work queue:
  `EVALUATION_FEEDBACK_DOMAIN_TABLE_COLUMNS`,
  exact required index-name and index-column expectations for
  `eval_observations` and `eval_failure_cases`,
  and exact unique-constraint expectations for
  `uq_eval_observations_observation_key` and
  `uq_eval_failure_cases_case_key`
- confirm no unrelated worktree state would prevent a narrow local milestone
  commit

Preflight conditions:

- `uv run docling-system-architecture-quality-report --summary` still reports
  `app/db/models.py` as the top routed hotspot for `IC-F2A8110185EB`
- `docs/SESSION_HANDOFF.md`, `docs/data_model_boundary_plan.md`, and this plan
  all route the next candidate to the evaluation-feedback family
- `uv run docling-system-improvement-case-validate` passes
- `uv run docling-system-improvement-case-summary` still reports
  `IC-F2A8110185EB` as the oldest open owner case
- `DOCLING_SYSTEM_RUN_INTEGRATION=1` Postgres-backed verification is available
  and not being silently skipped
- `uv run --extra dev alembic heads`, `current`, and `check` all pass before
  the move
- `git status --short` shows only changes that can be separated safely into the
  milestone slice

Acceptance:

- the baseline metrics, routed owner case, and next-candidate docs agree and
  are recorded in durable docs
- the missing evaluation-feedback metadata contract coverage is explicitly named
  as required implementation before the ORM move begins
- the repo is proven ready for DB-backed verification, not merely assumed ready
- the milestone stops before code movement if any preflight condition fails

Status update:

- verified locally on 2026-05-11 and later committed locally as `b69c4f6`
- live routing remains aligned across `docs/SESSION_HANDOFF.md`,
  `docs/data_model_boundary_plan.md`, `docs/agentic_architecture_index.md`,
  `config/improvement_cases.yaml`, and this plan
- live preflight gates confirmed the current owner route and DB-backed baseline:
  `uv run docling-system-architecture-quality-report --summary` reported
  `hotspot_count=10`, `max_hotspot_risk_score=658.21`, and
  `app/db/models.py` still first in `top_hotspot_paths`;
  `uv run docling-system-improvement-case-summary` kept
  `IC-F2A8110185EB` as `oldest_open_case_id`;
  `uv run docling-system-improvement-case-validate` returned `valid=true`;
  `uv run --extra dev alembic heads`, `current`, and `check` stayed clean; and
  the focused import and Postgres metadata gates passed at
  `358 passed` and `132 passed`
- the missing dedicated evaluation-feedback metadata contract coverage remains
  the required first implementation step of Milestone 1; Milestone 0 closes
  without moving `EvalObservation` or `EvalFailureCase`

Closeout:

- update this plan, `docs/agentic_architecture_index.md`, and
  `docs/SESSION_HANDOFF.md` if the routed baseline changed
- do not start Milestone 1 until the preflight gate is satisfied

### Milestone 1: Evaluation-Feedback Contract And Owner Split

Outcome label: `resolved`

Purpose:
Move the evaluation-feedback ORM concern into a focused owner module with exact
schema-contract coverage and preserved public imports.

Scope:

- add the missing shared gate coverage for the evaluation-feedback family in
  `tests/db_model_contract.py`
- add `app/db/model_domains/evaluation_feedback.py` containing only
  `EvalObservation` and `EvalFailureCase`
- preserve all table metadata, check constraints, indexes, unique constraints,
  JSONB defaults, and foreign keys exactly
- replace the in-file ORM implementations in `app/db/models.py` with
  compatibility re-exports that keep
  `from app.db.models import EvalObservation, EvalFailureCase` unchanged

Acceptance:

- `EvalObservation` and `EvalFailureCase` are owned by
  `app/db/model_domains/evaluation_feedback.py`
- `app/db/models.py` keeps only compatibility re-exports for those symbols
- `tests/db_model_contract.py` exposes explicit evaluation-feedback table,
  index, and unique-constraint contracts
- import compatibility, Postgres metadata, Alembic, and full DB-backed pytest
  gates all pass without loosening prior coverage

Status update:

- verified locally on 2026-05-11 and committed locally as `b69c4f6`
- added `app/db/model_domains/evaluation_feedback.py` containing only
  `EvalObservation` and `EvalFailureCase`
- replaced the in-file ORM implementations in `app/db/models.py` with
  compatibility re-exports so
  `from app.db.models import EvalObservation, EvalFailureCase` remains
  unchanged
- expanded `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` with dedicated
  evaluation-feedback table-column, exact index-column, and exact
  unique-constraint coverage
- reduced `app/db/models.py` from 3,782 lines to 3,570 and reduced the live
  architecture-quality `max_hotspot_risk_score` from `658.21` to `653.8`
- the broader `IC-F2A8110185EB` owner case remains `reduced`, not `resolved`,
  because `uv run docling-system-architecture-quality-report --summary` still
  lists `app/db/models.py` in `top_hotspot_paths`
- refreshed `config/improvement_cases.yaml`,
  `docs/data_model_boundary_plan.md`, `docs/agentic_architecture_index.md`,
  and `docs/SESSION_HANDOFF.md` after the commit so the repo-wide route points
  back to the agent-task family instead of treating this plan as the next
  active execution slice

### Milestone 2: Closeout And Next Routing

Outcome label: `reduced`

Purpose:
Refresh owner-case measurements, prove the milestone result from live gates,
and route the next remaining `IC-F2A8110185EB` concern without overstating
closure.

Scope:

- update `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`
  with the new `app/db/models.py` measurement and the new owner module
  coverage
- route the next remaining `IC-F2A8110185EB` concern explicitly in
  `docs/data_model_boundary_plan.md`, `docs/agentic_architecture_index.md`,
  and `docs/SESSION_HANDOFF.md`
- close the milestone only after all required verification gates pass and the
  verified slice is committed locally

Acceptance:

- for the milestone scope, `resolved` means the evaluation-feedback ORM concern
  no longer lives as primary ORM code in `app/db/models.py`
- for the broader owner case, the result is still `reduced` unless the live
  architecture-quality report no longer flags `app/db/models.py`
- the next remaining `app/db/models.py` concern is named explicitly from fresh
  live measurements rather than copied from older prose

## Required Implementation Artifacts

- `app/db/model_domains/evaluation_feedback.py`
- `app/db/models.py` re-export updates
- `tests/db_model_contract.py` evaluation-feedback contract additions
- `tests/unit/test_db_model_import_compatibility.py` ownership assertions for
  the moved symbols
- `tests/integration/test_db_model_metadata.py` Postgres metadata coverage for
  evaluation-feedback tables, indexes, and unique constraints
- any minimal Alembic-related compatibility updates required to keep drift at
  zero without changing schema shape

## Required Documentation And Handoff Updates

- this milestone plan
- `docs/data_model_boundary_plan.md`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`

If the architecture-quality summary changes materially, refresh the measurement
values cited in the touched docs from live commands rather than carrying older
numbers forward.

## Required Verification Gates

Milestone 0 preflight and Milestone 1/2 closeout gates:

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
uv run docling-system-improvement-case-validate
uv run docling-system-improvement-case-summary
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
git status --short
git diff --stat
git diff --cached --stat
```

Additional controlled-violation checks before final closeout:

```bash
uv run pytest -q tests/unit/test_db_model_import_compatibility.py -k evaluation_feedback
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py -k eval
```

## Acceptance Criteria

- Outcome label: `resolved`
  for the milestone scope. `EvalObservation` and `EvalFailureCase` are owned by
  `app/db/model_domains/evaluation_feedback.py`, and `app/db/models.py` keeps
  only compatibility re-exports for those symbols.
- Outcome label: `reduced`
  for the broader owner case unless the live architecture-quality report no
  longer lists `app/db/models.py` as an open hotspot. The plan must not claim
  the full `IC-F2A8110185EB` case is resolved without that governing signal.
- `tests/db_model_contract.py` exposes explicit evaluation-feedback table,
  index, and unique-constraint contracts rather than relying only on the broad
  symbol registry.
- Milestone 0 preflight conditions are completed before the ORM move begins:
  live routing docs agree, DB-backed verification is available, the owner case
  is still current, and the missing shared evaluation-feedback contract coverage
  is explicitly included in the implementation slice.
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py` passes,
  including ownership assertions that the public symbols now come from the new
  owner module.
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
  passes with evaluation-feedback table, index, and unique-constraint coverage
  in the Postgres `create_all(...)` path.
- `uv run --extra dev alembic heads`, `current`, `upgrade head`, and `check`
  all pass with one head and no unexpected upgrade operations.
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` passes; skipped
  Postgres-backed coverage is not acceptable closeout for this milestone.
- `uv run docling-system-architecture-quality-report --summary` and the
  architecture probe are refreshed from the live repo state before closeout.
- Tests are not weakened to achieve green. Any changed test, fixture, or gate
  must preserve equivalent or broader contract coverage than the
  pre-milestone baseline, with exact metadata checks retained or expanded.
- The milestone is not complete until the verified slice is committed locally
  with updated docs and handoff artifacts.

## Stop Conditions

- Stop if preserving exact evaluation-feedback schema semantics requires a
  schema redesign or data migration beyond a behavior-preserving owner split.
- Stop if `EvalObservation` / `EvalFailureCase` are coupled to another model
  family strongly enough that moving them alone would create a broader
  cross-domain dump file.
- Stop if full DB-backed verification fails and the failure cannot be isolated
  to this milestone slice.
- Stop if the only path to green is weakening tests, loosening metadata
  expectations, or dropping controlled-violation checks.

## Local Commit Closeout Policy

- Stage only the verified evaluation-feedback milestone slice.
- Leave unrelated dirty or untracked files alone.
- Include implementation, tests, routing docs, measurement updates, and the
  session handoff in the same atomic local commit.
- Record the commit hash in `docs/SESSION_HANDOFF.md` and any active milestone
  status docs touched at closeout.
- Treat the milestone as incomplete until that commit exists.
- Do not commit if any required verification gate fails or if unrelated changes
  cannot be separated safely.

## Residual Risks And Next Milestone Routing

- If this milestone passes, the evaluation-feedback concern is resolved for its
  scoped issue, but `IC-F2A8110185EB` may still remain open as a broader
  `app/db/models.py` hotspot.
- The closeout must measure the new `app/db/models.py` line count and
  architecture-quality summary from the live repo before routing the next
  follow-up.
- The next owner-case route after this milestone should be whichever remaining
  `app/db/models.py` concern the refreshed `docs/data_model_boundary_plan.md`
  names explicitly. Do not reuse older routing prose without a freshness check.
- refreshed routing now names the agent-task family as the next remaining
  `app/db/models.py` concern if model-domain work continues:
  `AgentTask`, `AgentTaskDependency`, `AgentTaskAttempt`,
  `AgentTaskArtifact`, `AgentTaskArtifactImmutabilityEvent`,
  `AgentTaskOutcome`, `AgentTaskVerification`, `KnowledgeOperatorRun`,
  `KnowledgeOperatorInput`, and `KnowledgeOperatorOutput`

## Closeout Checklist

- [x] Complete Milestone 0 preflight and baseline-lock conditions
- [x] Add dedicated evaluation-feedback metadata contract coverage before the move
- [x] Move `EvalObservation` and `EvalFailureCase` into a focused owner module
- [x] Preserve `app.db.models` import compatibility
- [x] Prove Postgres `create_all(...)` and Alembic drift remain clean
- [x] Prove tests did not get easier just to pass
- [x] Refresh routing docs and handoff from live measurements
- [x] Commit the verified milestone slice locally

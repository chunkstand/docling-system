# Claim Support Model-Domain Milestone Plan

Date: 2026-05-11 local
Status: Completed locally on 2026-05-11; broader owner case reduced
Owner context: bounded follow-up under the open architecture-governance owner
case for `app/db/models.py`. This milestone resolves the claim-support ORM
concern inside the compatibility facade; it does not claim to retire the
entire `IC-F2A8110185EB` hotspot unless the governing architecture report no
longer flags that owner case after closeout.

## Purpose

Resolve the routed `claim support` ORM concern inside `app/db/models.py` by
moving the replay-alert waiver, fixture-corpus, calibration, evaluation, and
policy-impact rows into a focused owner module while preserving the public
`app.db.models` import contract, the exact Postgres schema contract, and the
current claim-support behavior.

## Current Evidence

Pre-split baseline:

```text
uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=631.43

wc -l app/db/models.py
  2089 app/db/models.py

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  app/db/models.py score=162942
```

Post-split verification:

```text
uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=612.67

wc -l app/db/models.py app/db/model_domains/claim_support.py
  1301 app/db/models.py
   829 app/db/model_domains/claim_support.py

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  app/db/models.py score=101478
```

Repo-current artifact evidence:

- `docs/evaluation_feedback_model_domain_milestone_plan.md` was reviewed as the
  last completed bounded model-domain record and confirmed the established
  split pattern: shared contract expansion first, owner-module move second,
  routing-doc closeout third.
- `docs/data_model_boundary_plan.md` routed the next `IC-F2A8110185EB`
  follow-up to the `claim support` family.
- `tests/db_model_contract.py` already classified the claim-support symbols
  under the `claim_support` domain set but did not yet expose a dedicated
  `CLAIM_SUPPORT_DOMAIN_TABLE_COLUMNS` harness or exact claim-support
  index/unique-constraint coverage before this milestone.

## Goal

Resolve the claim-support concern inside `app/db/models.py` by moving the nine
claim-support ORM classes into `app/db/model_domains/claim_support.py` behind
the existing `app.db.models` compatibility facade, with dedicated shared
contract coverage for every moved table.

## Non-Goals

- Do not claim to retire the full `IC-F2A8110185EB` hotspot unless the live
  architecture-quality report stops flagging `app/db/models.py`.
- Do not change table names, column names, check-constraint values,
  index names, unique-constraint names, foreign-key targets, or `ondelete`
  behavior.
- Do not redesign replay-alert governance, fixture-corpus workflows,
  calibration policy behavior, evaluation logic, or policy-change impact
  lifecycle.
- Do not weaken test, fixture, metadata, Alembic, or architecture gates.
- Do not mix semantic-memory rows into this milestone.

## Scope

In scope:

- `ClaimSupportReplayAlertFixtureCoverageWaiverLedger`
- `ClaimSupportReplayAlertFixtureCoverageWaiverEscalation`
- `ClaimSupportFixtureSet`
- `ClaimSupportReplayAlertFixtureCorpusSnapshot`
- `ClaimSupportReplayAlertFixtureCorpusRow`
- `ClaimSupportCalibrationPolicy`
- `ClaimSupportEvaluation`
- `ClaimSupportEvaluationCase`
- `ClaimSupportPolicyChangeImpact`
- `app/db/model_domains/claim_support.py`
- `app.db.models` compatibility re-exports
- shared metadata contract expansion for claim-support tables
- routing-doc and governance-artifact refresh for the moved concern

Out of scope:

- semantic-memory rows
- additional evidence, agent-task, or retrieval model movement
- caller import rewrites away from `app.db.models`

## Owner Surfaces

- hotspot facade: `app/db/models.py`
- new owner module: `app/db/model_domains/claim_support.py`
- compatibility and metadata harness:
  `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`
- migration / schema gates:
  `alembic/`,
  `uv run --extra dev alembic *`
- routing and current-state docs:
  this plan, `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`, and `docs/SESSION_HANDOFF.md`
- owner-case routing:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`

## Placement Rules

- Keep `app/db/models.py` as the public compatibility facade.
- Keep only the claim-support ORM family in
  `app/db/model_domains/claim_support.py`.
- Add shared contract constants for the claim-support tables in
  `tests/db_model_contract.py` instead of duplicating expectations inside test
  bodies.
- Preserve exact index names, exact index column ordering, exact unique
  constraint names and column ordering, and the existing check-constraint value
  sets.

## Weak-Point Prevention Contract

Weak point forecast:
This split could look clean while silently weakening the schema harness,
dropping exact coverage for claim-support indexes or unique constraints,
changing emitted DDL, or breaking the `app.db.models` compatibility facade.

Owner surface:
`app/db/models.py`, `app/db/model_domains/claim_support.py`, the shared DB
model contract tests, Alembic verification, and the routing docs that define
what counts as resolved for this milestone.

Prevention gate:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Fail threshold:

- any moved claim-support class remains fully implemented in `app/db/models.py`
- any public `app.db.models` import for the moved symbols breaks
- any claim-support table loses exact column, index, or unique-constraint
  coverage in the shared harness
- Alembic emits unexpected drift or `Base.metadata.create_all(...)` no longer
  matches the supported Postgres schema shape

Controlled violation:

- remove one moved symbol from the `app.db.models` re-export path and verify
  the import-compatibility test fails
- change one expected claim-support unique-constraint or index-column ordering
  entry and verify the Postgres metadata gate fails

Future-Codex misuse scenario:
The most likely bad follow-up is moving a large family into a new file while
leaving the shared harness unchanged because the public symbols still import.
This milestone prevents that by requiring dedicated claim-support
table-column, index-column, and unique-constraint coverage before the move is
considered complete.

## Milestone Closeout

Implemented result:

- added `app/db/model_domains/claim_support.py`
- moved the nine routed claim-support ORM classes out of `app/db/models.py`
- kept `app.db.models` import-compatible by re-exporting the moved classes
  through import-forwarder aliases
- extended `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` to cover claim-support table
  columns, exact index column ordering, and exact unique-constraint column
  ordering
- reduced `app/db/models.py` from 2,089 lines to 1,301 and governed the new
  owner module at 829 lines through the hygiene policy ratchet
- refreshed routing docs and owner-case measurements so the next model-domain
  candidate now routes to the semantic-memory family

## Required Documentation And Handoff Updates

- update this plan as the completed bounded milestone record
- refresh `docs/data_model_boundary_plan.md`
- refresh `docs/agentic_architecture_index.md`
- refresh `docs/improvement_loop.md`
- refresh `docs/SESSION_HANDOFF.md`
- refresh `config/hygiene_policy.yaml` and `config/improvement_cases.yaml`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

## Acceptance Criteria

- `tests/unit/test_db_model_import_compatibility.py` proves the moved
  claim-support classes are now owned by
  `app.db.model_domains.claim_support`.
- `tests/db_model_contract.py` exposes explicit claim-support table-column,
  exact index-column, and exact unique-constraint expectations.
- `tests/integration/test_db_model_metadata.py` proves the schema-scoped
  Postgres `Base.metadata.create_all(...)` path preserves the claim-support
  schema contract.
- `app/db/models.py` remains the public compatibility facade while the
  claim-support ORM concern itself is resolved inside the milestone scope.
- architecture quality improves from the pre-split `631.43` baseline to the
  post-split `612.67` summary while `app/db/models.py` remains a governed
  hotspot only in the broader owner-case sense.

## Stop Conditions

- Stop if preserving exact claim-support schema semantics requires a migration
  or caller-facing contract change.
- Stop if DB-backed verification cannot run against local Postgres.
- Stop if the claim-support family must be split again before this milestone
  can close cleanly.

## Local Commit Closeout Policy

- Stage only the verified claim-support milestone slice.
- Include implementation, tests, routing docs, owner-case artifacts, and the
  canonical handoff update in the same atomic local commit.

## Residual Risks And Next Milestone Routing

- `app/db/models.py` remains the public compatibility facade and is still a
  governed hotspot because the semantic-memory family remains inside it.
- If model-domain work continues, the next routed owner slice is the
  `semantic memory` family under `IC-F2A8110185EB`.

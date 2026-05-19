# Evaluation Residual Owner Family Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved through the 2026-05-18 durable closeout. The evaluation
family now has no governed file above the default `600`-line budget, and exact
family-local ratchets have been refreshed.
Owner context: follow-on packet for the extracted evaluation owners after the
deployed `app/services/evaluations.py` facade closeout under
`IC-BF180637814C`. This packet now records the local closeout that removes the
evaluation family from both the live `>800` backlog and the local `601-800`
residual set.

## Purpose

Resolve the residual evaluation owner debt without reopening the deployed
`app/services/evaluations.py` facade work.

The routed weakness is no longer that `app/services/evaluations.py` itself is a
monolith. That issue is already closed locally. The remaining debt was in the
extracted owners and the oversized shared fixture root:

- `app/services/evaluation_fixtures.py` at `966` lines
- `app/services/evaluation_scoring.py` at `897` lines
- `app/services/eval_workbench.py` at `952` lines
- `tests/unit/test_evaluation_fixtures.py` at `1506` lines

## Current Evidence

- The live architecture probe rerun for this packet now reports `13` code files
  above `800` with `0` Python cycle components; none of the evaluation-family
  roots remain in the `>800` backlog.
- The family now closes at:
  `app/services/evaluation_fixtures.py` = `376`,
  `app/services/evaluation_fixture_auto_generation.py` = `570`,
  `app/services/evaluation_fixture_materialization.py` = `67`,
  `app/services/evaluation_scoring.py` = `530`,
  `app/services/evaluation_scoring_answers.py` = `175`,
  `app/services/evaluation_scoring_structural.py` = `218`,
  `app/services/eval_workbench.py` = `322`,
  `app/services/eval_workbench_refresh.py` = `431`,
  `app/services/eval_workbench_inspection.py` = `252`,
  `tests/unit/test_evaluation_fixtures.py` = `445`,
  `tests/unit/test_evaluation_fixture_persistence.py` = `310`,
  `tests/unit/test_evaluation_fixtures_auto_queries.py` = `390`,
  and `tests/unit/test_evaluation_fixtures_auto_query_filtering.py` = `378`.
- `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` now keep the
  full evaluation family on `IC-4B6E9F8D2A10` with exact local ratchets for the
  closed roots, including the newly added materialization, answer-scoring,
  refresh, and test siblings.
- Focused verification is green:
  `uv run ruff check ...` passed,
  `uv run pytest -q ...` passed at `64 passed`,
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs ...` passed at
  `12 passed`,
  `uv run docling-system-improvement-case-validate` returned `valid=true`,
  `uv run docling-system-improvement-case-summary` reported
  `case_count=59` / `open=43` / `deployed=15` / `measured_case_count=55`,
  `uv run docling-system-architecture-quality-report --summary` still reports
  `hotspot_count=10` / `max_hotspot_risk_score=496.06`,
  and `uv run docling-system-hygiene-check` now reports
  `new hygiene regressions: none`.

## Goal

Reduce the evaluation residual family so that:

- `app/services/evaluations.py` remains the narrow deployed facade.
- every governed evaluation owner and test root falls at or below the default
  `600`-line budget with explicit family-local routing.
- any new owner or test sibling created by the packet receives exact
  same-milestone hygiene ownership instead of becoming an untracked sink.
- evaluation fixture, scoring, workbench, and DB-backed evaluation coverage are
  at least as strong as before the split.

## Non-Goals

- No reopening of `app/services/evaluations.py` as a mixed-ownership service.
- No moving evaluation implementation into `documents.py`, `runs.py`,
  `semantic_backfill.py`, or unrelated capability facades.
- No weakening of fixture, scoring, workbench, or Postgres-backed integration
  coverage to achieve a line-count reduction.

## Scope

In scope:

- `app/services/evaluation_fixtures.py`
- `app/services/evaluation_fixture_auto_generation.py`
- `app/services/evaluation_fixture_materialization.py`
- `app/services/evaluation_scoring.py`
- `app/services/evaluation_scoring_answers.py`
- `app/services/evaluation_scoring_structural.py`
- `app/services/eval_workbench.py`
- `app/services/eval_workbench_refresh.py`
- `app/services/eval_workbench_inspection.py`
- `tests/unit/test_evaluation_fixtures.py`
- `tests/unit/test_evaluation_fixture_persistence.py`
- `tests/unit/test_evaluation_fixtures_auto_queries.py`
- `tests/unit/test_evaluation_fixtures_auto_query_filtering.py`
- focused sibling files created for evaluation fixtures, scoring, workbench, or
  test support
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `docs/evaluation_residual_owner_family_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

Out of scope:

- broad evaluation product behavior changes
- unrelated search, documents, parser, or semantic service refactors
- changing the deployed evaluation API or capability facade contract

## Owner Surfaces

- service owners:
  `app/services/evaluation_fixtures.py`,
  `app/services/evaluation_fixture_auto_generation.py`,
  `app/services/evaluation_fixture_materialization.py`,
  `app/services/evaluation_scoring.py`,
  `app/services/evaluation_scoring_answers.py`,
  `app/services/evaluation_scoring_structural.py`,
  `app/services/eval_workbench.py`,
  `app/services/eval_workbench_refresh.py`,
  `app/services/eval_workbench_inspection.py`
- deployed facade:
  `app/services/evaluations.py`
- unit and integration roots:
  `tests/unit/test_evaluation_service.py`,
  `tests/unit/test_evaluation_fixtures.py`,
  `tests/unit/test_evaluation_fixture_persistence.py`,
  `tests/unit/test_evaluation_fixtures_auto_queries.py`,
  `tests/unit/test_evaluation_fixtures_auto_query_filtering.py`,
  `tests/unit/test_evaluation_scoring.py`,
  `tests/unit/test_evaluation_reads.py`,
  `tests/unit/test_eval_workbench_service.py`,
  `tests/unit/test_eval_workbench_api.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/integration/test_eval_workbench_roundtrip.py`,
  `tests/integration/test_multivector_retrieval.py`

## Placement Rules

- Keep `app/services/evaluations.py` as a narrow orchestration and compatibility
  facade.
- Move fixture, scoring, workbench, and evaluation-test ownership into
  family-local siblings rather than into `documents.py`, `runs.py`, or generic
  shared helper sinks.
- If shared test scaffolding is needed, keep it evaluation-local and below the
  default `600`-line budget.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The split shrinks one evaluation file by bloating another nearby service. | evaluation service files, `config/hygiene_policy.yaml`, architecture probe | focused `ruff` and `pytest`, hygiene check, architecture probe | any touched evaluation owner stays above its ratchet or a new `>800` sibling appears | temporarily dump moved scoring code into `eval_workbench.py` and confirm closeout rejects it | a later session follows shared vocabulary and recreates the monolith one file over |
| The test root gets smaller by deleting fixture scenarios instead of isolating them. | evaluation unit roots, integration roots | focused unit slice plus DB-backed integration slice | lower line count comes from weaker assertion coverage or narrower fixture scenarios | replace a full table or fixture assertion block with a smoke assertion and confirm review or tests reject the packet | future Codex optimizes for line count instead of contract coverage |
| Workbench or scoring logic regrows the deployed facade. | `app/services/evaluations.py`, focused siblings | facade-size readback, hygiene check, architecture probe | `app/services/evaluations.py` grows beyond its deployed ratchet or regains mixed ownership | temporarily add a moved workbench helper back to the facade and confirm the packet fails | a later session treats the public facade as the easiest place to land new logic |

## Milestone Sequence

### Milestone 0. Baseline Lock
Outcome label: reduced

Refresh line counts, confirm `IC-4B6E9F8D2A10` routing, and freeze the service,
test, and integration gates before code motion.

### Milestone 1. Fixture And Scoring Service Split
Outcome label: reduced

Reduce `app/services/evaluation_fixtures.py` and
`app/services/evaluation_scoring.py` below `800` without regrowing
`app/services/evaluations.py`.

### Milestone 2. Workbench And Fixture-Test Split
Outcome label: reduced

Reduce `app/services/eval_workbench.py` and
`tests/unit/test_evaluation_fixtures.py` below `800` through family-local
owners or test-support siblings.

### Milestone 3. Closeout
Outcome label: resolved

Close the evaluation residual packet only after the full governed family is at
or below `600`, docs are updated, and the focused plus DB-backed verification
slices are green.

## Required Implementation Artifacts

- focused evaluation owner siblings or test-support files needed to reduce the
  routed roots
- refreshed `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`
- updated closeout docs and handoff artifacts

## Required Documentation And Handoff Updates

- `docs/evaluation_residual_owner_family_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/evaluation_fixtures.py app/services/evaluation_fixture_auto_generation.py app/services/evaluation_fixture_materialization.py app/services/evaluation_scoring.py app/services/evaluation_scoring_answers.py app/services/evaluation_scoring_structural.py app/services/eval_workbench.py app/services/eval_workbench_refresh.py app/services/eval_workbench_inspection.py tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_fixture_persistence.py tests/unit/test_evaluation_fixtures_auto_queries.py tests/unit/test_evaluation_fixtures_auto_query_filtering.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_eval_workbench_service.py tests/unit/test_eval_workbench_api.py`
- `uv run pytest -q tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_fixture_persistence.py tests/unit/test_evaluation_fixtures_auto_queries.py tests/unit/test_evaluation_fixtures_auto_query_filtering.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_eval_workbench_service.py tests/unit/test_eval_workbench_api.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_eval_workbench_roundtrip.py tests/integration/test_multivector_retrieval.py`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- The full governed evaluation family closes at or below `600` lines.
- `app/services/evaluations.py` stays at or below its deployed narrow ratchet.
- No replacement owner or test root exceeds `600` lines, and the new siblings
  carry explicit family-local routing plus exact ratchets.
- The focused unit slice and DB-backed evaluation slice pass without weaker
  assertions or broader skips.

## Current Local State

This packet is now resolved locally in the current checkout.

- The governed family now measures:
  `376`, `570`, `67`, `530`, `175`, `218`, `322`, `431`, `252`, `445`, `310`,
  `390`, and `378` lines across the evaluation fixtures, scoring, workbench,
  and family-local test roots.
- Retrieval-backed auto-fixture materialization now lives in
  `app/services/evaluation_fixture_materialization.py`, answer-case scoring now
  lives in `app/services/evaluation_scoring_answers.py`, workbench refresh and
  upsert ownership now lives in `app/services/eval_workbench_refresh.py`,
  persistence-focused fixture coverage now lives in
  `tests/unit/test_evaluation_fixture_persistence.py`, and late heuristic
  filtering now lives in
  `tests/unit/test_evaluation_fixtures_auto_query_filtering.py`.
- `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` now ratchet
  the closed family roots exactly under `IC-4B6E9F8D2A10`, including the
  previously missing explicit override for `app/services/eval_workbench_inspection.py`.
- The closeout commit required by this packet has not been created yet because
  the broader worktree is still dirty with unrelated in-flight architecture
  work.

## Stop Conditions

- Stop if a fresh probe changes the evaluation family membership before code
  motion begins.
- Stop if the reduction requires moving evaluation logic into unrelated service
  families.
- Stop if a green result depends on weaker evaluation assertions or broader
  integration skips.

## Local Commit Closeout Policy

- Close this packet with one atomic local commit that contains only the
  evaluation owner changes, focused tests, routing updates, and doc or handoff
  updates for this packet.

## Residual Risks And Next Milestone Routing

- The evaluation family is locally retirement-ready, but the registry must stay
  open until an atomic closeout commit records this packet without capturing
  unrelated dirty worktree changes.
- The next active bounded packet remains
  `docs/ui_module_residual_owner_family_milestone_plan.md`.
- After this packet closes, return to
  `docs/residual_large_file_backlog_milestone_plan.md` and activate
  `docs/ui_module_residual_owner_family_milestone_plan.md` unless a fresh
  rebaseline changes the queue.

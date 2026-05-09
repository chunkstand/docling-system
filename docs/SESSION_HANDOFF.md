# Session Handoff

Date: 2026-05-09 local / 2026-05-09 UTC
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `main`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Latest local code checkpoint before this docs refresh: `9f60a17` (`complete agentic architecture governance milestones`)

## Current Position

The checkout is on `main` at `9f60a17c02c79979dd24c2e730cfd8f18f1ba32e`
before this documentation closeout commit. At the start of the closeout,
`main` was clean and ahead of `origin/main` by 9 commits; `origin/main` was
`6933eca` (`Add Docker pg_dump fallback for reset`). Recheck branch parity after
the docs commit and any push.

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

The 9 local commits ahead of `origin/main` are:

- `5f4598b` `Split agent task action executors`
- `7fe2dbc` `Split technical report services`
- `482daa3` `Clear near-threshold hygiene blockers`
- `637559a` `Split hygiene blocker modules`
- `b59d4d5` `Split agent task hygiene modules`
- `25ac117` `Harden search and retrieval hygiene boundaries`
- `8654bde` `Split search replay and release gate hygiene`
- `1e05afd` `refactor evidence payload helpers`
- `9f60a17` `complete agentic architecture governance milestones`

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
  top_hotspot_paths=[
    app/db/models.py,
    app/services/evidence.py,
    app/cli.py,
    app/services/agent_task_actions.py,
    tests/unit/test_cli.py
  ]
```

The architecture boundary model is clean, but hotspot debt remains real. The
top governed split targets are `app/db/models.py`, `app/services/evidence.py`,
`app/cli.py`, `app/services/agent_task_actions.py`, and `app/services/search.py`.

## Verification Snapshot

Commands run for this docs closeout:

```bash
uv run ruff check app tests
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-decisions
uv run docling-system-architecture-quality-report --summary
uv run docling-system-hygiene-check
uv run docling-system-improvement-case-summary
uv run pytest -q tests/unit/test_architecture_inspection.py tests/unit/test_architecture_quality.py tests/unit/test_capability_contracts.py tests/unit/test_api_route_contracts.py
uv run docling-system-evaluation-data-readiness
uv run docling-system-agent-trace-review --limit 5 --skip-hygiene
docker compose ps
```

Results:

```text
ruff: All checks passed.
architecture inspection: passed, violation_count=0.
capability contracts: passed, valid=true.
architecture decisions: passed, valid=true.
architecture quality summary: passed, hotspot_count=10.
focused architecture tests: 34 passed in 11.85s.
improvement-case summary: 1 measured case, 0 open actionable buckets.
hygiene: exits 1; Ruff/Vulture/improvement-case/architecture findings are clean, but file/helper budget findings remain.
evaluation-data readiness: blocked by local Postgres connection refusal on localhost:5432.
agent trace review: blocked by local Postgres connection refusal on localhost:5432.
docker compose ps: failed because Docker daemon is not running.
full Postgres-backed pytest: not run in this closeout because local Postgres/Docker are unavailable.
```

## Active Weak Points

- Documentation and branch state needed this closeout because the prior handoff
  still described `498908b` as current and said `HEAD` matched `origin/main`.
- Local runtime verification is blocked until Docker/Postgres are running again.
- Hygiene remains intentionally strict and currently fails on oversized modules,
  especially `app/db/models.py`, `app/services/evidence.py`,
  `app/services/audit_bundles.py`, `app/services/claim_support_policy_impacts.py`,
  `app/services/retrieval_learning.py`, and `app/services/search.py`.
- The improvement-case registry has not yet imported the current
  architecture-quality hotspot candidates, so generated hotspot signals are not
  all represented as tracked cases.
- Court-grade readiness cannot be claimed until the live DB passes
  `docling-system-evaluation-data-readiness` with enough hand-verified fixtures,
  operator feedback, claim feedback, governed hard cases, replay coverage, and
  retrieval-learning materialization.

## Next Milestone

First restore local runtime verification:

1. Start Docker/Postgres or point `DOCLING_SYSTEM_DATABASE_URL` at a working local Postgres.
2. Run `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`.
3. Run `uv run docling-system-evaluation-data-readiness`.
4. Run `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`.

After runtime verification is available, choose one hotspot split as an atomic
milestone. The most defensible next architecture slice is the data-model
boundary plan for `app/db/models.py`, because it is the highest-risk hotspot and
already has a required sequence in `docs/data_model_boundary_plan.md`.

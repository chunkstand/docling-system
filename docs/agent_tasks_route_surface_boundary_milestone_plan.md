# Agent Tasks Route Surface Boundary Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: resolved locally in the current checkout after the routed follow-on for
`app/api/routers/agent_tasks.py` reduced the root router to a composition
surface and moved the remaining HTTP families into focused sibling routers.
Owner context: routed architecture-governance follow-on after
`docs/architecture_inspection_test_surface_boundary_milestone_plan.md`
advanced the live queue to `app/api/routers/agent_tasks.py`.

## Purpose

Reduce the residual agent-tasks router root so future API growth does not
reopen one mixed boundary module.

This packet closes the route seam by:

- keeping `app/api/routers/agent_tasks.py` focused on the public
  `/agent-tasks/actions` route plus router composition
- moving task list, create, detail, outcome, verification, and
  approval-rejection routes into `app/api/routers/agent_task_lifecycle.py`
- moving context, artifact, failure-artifact, audit-bundle,
  evidence-manifest, evidence-trace, and provenance routes into
  `app/api/routers/agent_task_artifacts.py`
- preserving the parent-module service alias seam through
  `service_from_parent(...)` so the existing API tests and route helpers keep
  patching `app.api.routers.agent_tasks`
- keeping analytics and claim-support route families in their existing focused
  sibling routers instead of pushing more ownership back into the root file

## Non-Goals

- No API contract changes to `/agent-tasks`, `/agent-tasks/actions`, the
  analytics family, or the claim-support policy-impact routes.
- No service-layer refactor of `app/services/agent_tasks.py`,
  `app/services/evidence.py`, or the agent orchestration capability.
- No broader queue-honesty or stale-registry cleanup beyond updating the live
  routed packet docs for this closeout.

## Scope

In scope:

- `app/api/routers/agent_tasks.py`
- `app/api/routers/agent_task_lifecycle.py`
- `app/api/routers/agent_task_artifacts.py`
- `app/api/routers/agent_task_analytics.py`
- `app/api/routers/claim_support_policy_impacts.py`
- `app/api/routers/agent_task_route_services.py`
- `tests/unit/test_agent_tasks_api.py`
- `tests/unit/test_agent_tasks_api_*.py`
- `tests/unit/test_hotspot_prevention_policy_contracts.py`
- `tests/unit/test_api_route_contracts.py`
- current routing docs and handoff

Out of scope:

- `tests/integration/test_retrieval_learning_ledger.py`
- `config/improvement_cases.yaml`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- broader architecture-governance queue refresh outside this routed packet

## 2026-05-19 Local Closeout Update

The local route split now keeps the root agent-tasks router at `94` lines while
the moved ownership closes at `198` lines in
`app/api/routers/agent_task_lifecycle.py` and `287` lines in
`app/api/routers/agent_task_artifacts.py`.

`app/api/routers/agent_tasks.py` now owns only:

- the public `/agent-tasks/actions` route
- router composition for the lifecycle, analytics, artifacts, and
  claim-support siblings
- the parent-module alias seam that lets focused subrouters resolve patched
  services from `app.api.routers.agent_tasks` during tests

The moved siblings now own the concrete route behavior without changing the
existing capability gates, mutation-key gates, or HTTP payload contracts.

Live verification in the local checkout:

```text
uv run ruff check app/api/routers/agent_tasks.py \
  app/api/routers/agent_task_analytics.py \
  app/api/routers/agent_task_artifacts.py \
  app/api/routers/agent_task_lifecycle.py \
  app/api/routers/claim_support_policy_impacts.py \
  app/api/routers/agent_task_route_services.py \
  tests/unit/test_agent_tasks_api.py \
  tests/unit/test_agent_tasks_api_*.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py \
  tests/unit/test_api_route_contracts.py
  pass

uv run pytest -q tests/unit/test_agent_tasks_api.py \
  tests/unit/test_agent_tasks_api_*.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py \
  tests/unit/test_api_route_contracts.py
  57 passed

git diff --check
  pass

uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=40
  changed_hotspots=0
  blocked=0
  allowed=0

uv run docling-system-architecture-inspect
  valid=true
  violation_count=0

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=20
  max_hotspot_risk_score=486.06
  top_routed_hotspot_paths=[
    "tests/integration/test_retrieval_learning_ledger.py"
  ]

uv run docling-system-improvement-case-summary
  status_counts={"measured":1,"deployed":28,"open":21,"verified":10}

uv run docling-system-improvement-case-validate
  valid=true

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  0 Python cycle components
  0 code files above 800 lines
```

## Current Structural Evidence

- `app/api/routers/agent_tasks.py` is now a `94` line route-composition and
  action-catalog surface.
- `app/api/routers/agent_task_lifecycle.py` now owns the task list, create,
  detail, outcome, verification, and approval/rejection route families at
  `198` lines.
- `app/api/routers/agent_task_artifacts.py` now owns the context, artifact,
  failure-artifact, audit-bundle, evidence-manifest, evidence-trace, and
  provenance route families at `287` lines.
- `app/api/routers/agent_task_analytics.py` remains the focused analytics
  router and continues to resolve service calls through the parent-module seam.
- `app/api/routers/claim_support_policy_impacts.py` remains the focused
  claim-support policy-impact router and continues to resolve service calls
  through the parent-module seam.
- The live routed queue no longer selects `app/api/routers/agent_tasks.py`
  and now advances to `tests/integration/test_retrieval_learning_ledger.py`
  from the current architecture-quality summary.

## Residual Risks And Next Routing

- The parent-module alias seam is intentional. Future route splits in the
  agent-task family should preserve it or replace it with an equally explicit
  test-facing seam before removing it.
- Future agent-task API growth should land in the focused lifecycle,
  artifacts, analytics, or claim-support routers rather than reopening
  `app/api/routers/agent_tasks.py`.
- The next routed packet now comes from the broader coordination brief with the
  current live queue advanced to `tests/integration/test_retrieval_learning_ledger.py`.

# Agent Tasks Route Surface Boundary Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: resolved through implementation commit `17d6f8e`, and the current
governance closeout now records the reduced root as a routed deferred facade,
exact-ratchets the new sibling routers, and aligns the registry with the live
queue.
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
- routing the reduced root as a deferred reduced facade in
  `config/hotspot_prevention.yaml`
- exact-ratcheting the reduced root and its new sibling routers in
  `config/hygiene_policy.yaml`
- recording the route root as a deployed improvement case so the registry does
  not lag behind the code and queue state
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
- `app/hotspot_prevention_classifier.py`
- `app/hotspot_prevention_classifier_boundary_rules.py`
- `tests/unit/test_agent_tasks_api.py`
- `tests/unit/test_agent_tasks_api_*.py`
- `tests/unit/test_hotspot_prevention_agent_task_routes.py`
- `tests/unit/test_hotspot_prevention_policy_contracts.py`
- `tests/unit/test_hotspot_prevention.py`
- `tests/unit/test_api_route_contracts.py`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- current routing docs and handoff

Out of scope:

- `tests/integration/test_retrieval_learning_ledger.py`
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

`config/hotspot_prevention.yaml` now routes `app/api/routers/agent_tasks.py`
as a deferred reduced facade with the lifecycle, artifacts, analytics, and
claim-support routers as the preferred next owner surfaces, and
`config/hygiene_policy.yaml` exact-ratchets the reduced root plus the two new
router siblings so this packet does not simply move growth into a fresh
unguarded sink.

Live verification in the local checkout:

```text
uv run ruff check app/hotspot_prevention_classifier.py \
  app/hotspot_prevention_classifier_boundary_rules.py \
  app/api/routers/agent_tasks.py \
  app/api/routers/agent_task_analytics.py \
  app/api/routers/agent_task_artifacts.py \
  app/api/routers/agent_task_lifecycle.py \
  app/api/routers/claim_support_policy_impacts.py \
  app/api/routers/agent_task_route_services.py \
  tests/unit/test_agent_tasks_api.py \
  tests/unit/test_agent_tasks_api_*.py \
  tests/unit/test_hotspot_prevention_agent_task_routes.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py \
  tests/unit/test_api_route_contracts.py
  pass

uv run pytest -q tests/unit/test_agent_tasks_api.py \
  tests/unit/test_agent_tasks_api_*.py \
  tests/unit/test_hotspot_prevention_agent_task_routes.py \
  tests/unit/test_hotspot_prevention.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py \
  tests/unit/test_api_route_contracts.py
  68 passed

DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q
  2109 passed

git diff --check
  pass

uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=41
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
  status_counts={"measured":1,"deployed":29,"open":21,"verified":10}

uv run docling-system-improvement-case-validate
  valid=true

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  0 Python cycle components
  0 code files above 800 lines
```

Closeout-state recheck after the current governance alignment pass:

```text
uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=41
  changed_hotspots=0
  blocked=0
  allowed=0

uv run docling-system-hygiene-check
  new hygiene regressions: none

uv run docling-system-improvement-case-summary
  status_counts={"measured":1,"deployed":29,"open":21,"verified":10}

uv run docling-system-improvement-case-validate
  valid=true

uv run docling-system-architecture-quality-report --summary
  top_routed_hotspot_paths=[
    "tests/integration/test_retrieval_learning_ledger.py"
  ]
  stale_facade_hotspot_count=18
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
- `config/hotspot_prevention.yaml` now routes the reduced route root away from
  future lifecycle, artifact, analytics, and claim-support implementation
  growth.
- `config/hygiene_policy.yaml` now exact-ratchets
  `app/api/routers/agent_tasks.py`, `app/api/routers/agent_task_lifecycle.py`,
  and `app/api/routers/agent_task_artifacts.py` at `94`, `198`, and `287`
  lines with owner case `IC-17B0E2F64A9C`.
- `app/hotspot_prevention_classifier.py` now closes at `355` lines, staying
  within its existing ratchet while adding the reduced-route guard.
- `tests/unit/test_hotspot_prevention.py` remains the governed hotspot root at
  `341` lines, and the new route-specific regression coverage now lives in
  `tests/unit/test_hotspot_prevention_agent_task_routes.py` at `47` lines
  instead of regrowing that residual test surface.
- `config/improvement_cases.yaml` now records `IC-17B0E2F64A9C` as deployed so
  the registry, the routed queue, and the current code state agree.
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

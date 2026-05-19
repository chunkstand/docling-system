# Retrieval Learning Ledger Smoke Surface Boundary Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: resolved locally in the current checkout after the prior
`65c0c67` oversized-test split and the current governance closeout routed the
residual smoke root and family-local support module off the active queue,
exact-ratcheted the focused sibling files, and aligned the deployed owner case
with the live architecture-quality report.
Owner context: routed architecture-governance follow-on after
`docs/agent_tasks_route_surface_boundary_milestone_plan.md` advanced the live
queue to `tests/integration/test_retrieval_learning_ledger.py`.

## Purpose

Close the remaining governance gap for the already-split retrieval-learning
integration family so the active queue stops treating the reduced smoke root as
the next code-owning implementation surface.

This packet closes that gap by:

- routing `tests/integration/test_retrieval_learning_ledger.py` as a deferred
  reduced facade in `config/hotspot_prevention.yaml`
- routing `tests/integration/retrieval_learning_ledger_support.py` as an
  accepted residual family-local support boundary
- exact-ratcheting the focused dataset, candidate, and integrity sibling files
  in `config/hygiene_policy.yaml`
- refreshing `IC-908E7A1D2C44` in `config/improvement_cases.yaml` so the
  deployed registry state matches the current routed queue
- leaving the already-split integration tests behavior-stable instead of
  redistributing scenarios again without evidence of a fresh structural need

## Non-Goals

- No production retrieval-learning service changes.
- No second decomposition pass over the retrieval-learning integration family.
- No new shared integration support layer outside
  `tests/integration/retrieval_learning_ledger_support.py`.
- No broader queue refresh beyond recording that this family is now routed off
  the active queue.

## Scope

In scope:

- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- `tests/unit/test_hotspot_prevention_policy_contracts.py`
- `tests/integration/test_retrieval_learning_ledger.py`
- `tests/integration/retrieval_learning_ledger_support.py`
- `tests/integration/test_retrieval_learning_ledger_datasets.py`
- `tests/integration/test_retrieval_learning_ledger_candidates.py`
- `tests/integration/test_retrieval_learning_ledger_integrity.py`
- current routing docs and handoff

Out of scope:

- `tests/integration/test_technical_report_harness_roundtrip.py`
- `tests/unit/test_search_service.py`
- any broader under-budget reselect after this family leaves the active queue

## 2026-05-19 Local Closeout Update

The retrieval-learning family remains structurally unchanged from the earlier
oversized-test split:

- `tests/integration/test_retrieval_learning_ledger.py` stays at `428` lines
- `tests/integration/retrieval_learning_ledger_support.py` stays at `362`
  lines
- `tests/integration/test_retrieval_learning_ledger_datasets.py` stays at
  `413` lines
- `tests/integration/test_retrieval_learning_ledger_candidates.py` stays at
  `597` lines
- `tests/integration/test_retrieval_learning_ledger_integrity.py` stays at
  `599` lines

What changed in this packet is the governance around those already-reduced
surfaces:

- the residual smoke root is now a deferred reduced facade with explicit route
  targets for datasets, candidates, integrity, and family-local support
- the family-local support module is now an accepted residual boundary instead
  of an un-routed hotspot
- the focused sibling files now have exact hygiene ratchets, so the queue
  closeout does not merely hide growth in new ungoverned sinks
- the deployed improvement case now records this routed residual state

Live verification in the local checkout:

```text
uv run ruff check tests/unit/test_hotspot_prevention_policy_contracts.py \
  tests/integration/test_retrieval_learning_ledger.py \
  tests/integration/test_retrieval_learning_ledger_datasets.py \
  tests/integration/test_retrieval_learning_ledger_candidates.py \
  tests/integration/test_retrieval_learning_ledger_integrity.py \
  tests/integration/retrieval_learning_ledger_support.py
  pass

DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs \
  tests/integration/test_retrieval_learning_ledger.py \
  tests/integration/test_retrieval_learning_ledger_datasets.py \
  tests/integration/test_retrieval_learning_ledger_candidates.py \
  tests/integration/test_retrieval_learning_ledger_integrity.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  20 passed

DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q
  2109 passed

git diff --check
  pass

uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=41
  changed_hotspots=0
  blocked=0
  allowed=0

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt:
    app/services/agent_task_context_semantic_analysis.py = 770
    app/services/agent_task_context_technical_reports.py = 643

uv run docling-system-improvement-case-summary
  status_counts={"measured":1,"deployed":29,"open":21,"verified":10}

uv run docling-system-improvement-case-validate
  valid=true

uv run docling-system-architecture-inspect
  valid=true
  violation_count=0

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=20
  max_hotspot_risk_score=486.06
  stale_facade_hotspot_count=19
  top_routed_hotspot_paths=[]
```

## Current Structural Evidence

- `tests/integration/test_retrieval_learning_ledger.py` remains the `428` line
  end-to-end smoke and audit-closeout surface from the earlier split.
- `tests/integration/retrieval_learning_ledger_support.py` remains the `362`
  line family-local fixture and builder surface under the same verified
  `<= 400` and `<= 10` helper ceilings.
- The focused sibling files remain at `413`, `597`, and `599` lines and are
  now exact-ratcheted under `IC-908E7A1D2C44`.
- `config/hotspot_prevention.yaml` now routes the reduced smoke root away from
  future dataset, candidate, integrity, and replay-alert scenario growth and
  routes the support module as an accepted residual boundary.
- `config/improvement_cases.yaml` now records the same routed residual state in
  the deployed owner case instead of leaving the active queue to rediscover the
  already-closed family.
- The live routed queue no longer selects the retrieval-learning family;
  `top_routed_hotspot_paths` is now empty from the current
  architecture-quality summary.

## Residual Risks And Next Routing

- The retrieval-learning family still appears in measurement-only hotspot and
  routing-trap views because the smoke root remains high churn, but it is no
  longer an active code-owning packet.
- Future retrieval-learning scenario growth should land in the focused dataset,
  candidate, and integrity siblings rather than reopening the smoke root or
  broadening the family-local support module.
- The next code-owning packet must now be reselected from
  `docs/boring_change_architecture_milestone_plan.md` or a fresher narrow brief
  because the live `top_routed_hotspot_paths` queue is empty after this
  closeout.

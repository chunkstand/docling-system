# Documents API Route Surface Boundary Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: resolved through the 2026-05-19 verified-to-deployed registry closeout
after the broader-reselect follow-on reduced `IC-23F2C79C8AA7` into a
deployed route-smoke surface, exact-ratcheted the focused siblings, and
routed the root off the active queue without shifting debt into another
ungoverned test sink.
Owner context: fresh broader reselect after
`docs/retrieval_learning_ledger_smoke_surface_boundary_milestone_plan.md`
left `top_routed_hotspot_paths=[]` and the remaining live open cases needed a
new code-owning packet selection.

## Purpose

Close the last unresolved document-route test hotspot left behind by the
earlier high-value paydown split so future API growth does not reopen one mixed
test root.

This packet closes that gap by:

- keeping `tests/unit/test_documents_api.py` focused on core upload/list smoke
  and not-found compatibility assertions
- moving access, actor-capability, run-history, and latest-evaluation coverage
  into focused siblings
- routing the reduced root as a deferred reduced facade in
  `config/hotspot_prevention.yaml`
- exact-ratcheting the reduced root and the full focused owner family in
  `config/hygiene_policy.yaml`
- refreshing `IC-23F2C79C8AA7` in `config/improvement_cases.yaml` so the
  registry reflects the now-reduced route surface instead of leaving it open
  at the older `613`-line state
- adding focused hotspot-prevention regression coverage in
  `tests/unit/test_hotspot_prevention_documents_api_routes.py` instead of
  regrowing `tests/unit/test_hotspot_prevention.py`

## Non-Goals

- No production API contract changes in `app/api/routers/documents.py`.
- No document-service or evaluation-service refactor.
- No new document-route helper layer outside the focused test siblings.
- No broader queue refresh beyond recording that this routed follow-on is now
  closed and the live queue remains empty.

## Scope

In scope:

- `tests/unit/test_documents_api.py`
- `tests/unit/test_documents_api_access.py`
- `tests/unit/test_documents_api_runs.py`
- `tests/unit/test_documents_api_evaluations.py`
- `tests/unit/test_documents_api_artifacts.py`
- `tests/unit/test_documents_api_semantics.py`
- `tests/unit/test_hotspot_prevention_documents_api_routes.py`
- `app/hotspot_prevention_classifier_support.py`
- `tests/unit/test_hotspot_prevention_policy_contracts.py`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- current routing docs and handoff

Out of scope:

- `app/api/routers/documents.py`
- `tests/unit/test_document_service.py`
- any broader fresh reselect after this deployed closeout

## 2026-05-19 Local Closeout Update

The documents API family now closes at these post-split sizes:

- `tests/unit/test_documents_api.py` at `154` lines
- `tests/unit/test_documents_api_access.py` at `253` lines
- `tests/unit/test_documents_api_runs.py` at `137` lines
- `tests/unit/test_documents_api_evaluations.py` at `93` lines
- `tests/unit/test_documents_api_artifacts.py` at `286` lines
- `tests/unit/test_documents_api_semantics.py` at `394` lines

The reduced root now owns only:

- the core create/list smoke assertions
- not-found compatibility assertions for detail, runs, and chunks
- idempotency-key forwarding coverage

The focused siblings now own the rest of the route-family behavior without
changing the underlying API contracts:

- `tests/unit/test_documents_api_access.py` owns API-key and bearer-capability
  coverage for create, list, detail, and chunks routes
- `tests/unit/test_documents_api_runs.py` owns run-detail, run-history, and
  run-summary route coverage
- `tests/unit/test_documents_api_evaluations.py` owns latest-evaluation
  success and error-path coverage
- the previously extracted artifact and semantic siblings remain the focused
  homes for those earlier route families

`config/hotspot_prevention.yaml` now routes the reduced root away from future
access, run, evaluation, artifact, and semantic scenario growth, while
`config/hygiene_policy.yaml` exact-ratchets the full focused owner family so
this packet does not simply move bulk into fresh ungoverned files.

Live verification in the local checkout:

```text
uv run ruff check tests/unit/test_documents_api.py \
  tests/unit/test_documents_api_access.py \
  tests/unit/test_documents_api_runs.py \
  tests/unit/test_documents_api_evaluations.py \
  tests/unit/test_documents_api_artifacts.py \
  tests/unit/test_documents_api_semantics.py \
  tests/unit/test_hotspot_prevention_documents_api_routes.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  pass

uv run pytest -q tests/unit/test_documents_api.py \
  tests/unit/test_documents_api_access.py \
  tests/unit/test_documents_api_runs.py \
  tests/unit/test_documents_api_evaluations.py \
  tests/unit/test_documents_api_artifacts.py \
  tests/unit/test_documents_api_semantics.py \
  tests/unit/test_hotspot_prevention_documents_api_routes.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  48 passed

DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q
  2119 passed

git diff --check
  pass

uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=42
  changed_hotspots=1
  blocked=0

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt: none

uv run docling-system-improvement-case-validate
  valid=true

uv run docling-system-architecture-inspect
  valid=true
  violation_count=0

uv run docling-system-architecture-quality-report --summary
  broad_facade_count=2
  legibility_gap_count=0
  top_routed_hotspot_paths=[]
```

## Current Structural Evidence

- `tests/unit/test_documents_api.py` is now a `154`-line document-route smoke
  root instead of a `613`-line mixed owner.
- The three new focused siblings stay at `253`, `137`, and `93` lines and
  keep route behavior grouped by access control, run surfaces, and latest-
  evaluation coverage.
- The earlier artifact and semantic siblings stay at `286` and `394` lines,
  so the full document-route family now fits into focused under-budget owners.
- `tests/unit/test_hotspot_prevention_documents_api_routes.py` provides
  focused analyzer coverage for blocked broad scenario regrowth, blocked helper
  sinks, and allowed smoke-contract assertions without regrowing the governed
  hotspot-prevention roots.
- `config/improvement_cases.yaml` now records `IC-23F2C79C8AA7` as deployed at
  the reduced `154`-line state instead of leaving the packet open against the
  old `613`-line measurement.

## Residual Risks And Next Routing

- The live `top_routed_hotspot_paths` queue remains empty after this packet, so
  the next code-owning step still requires a fresh broader reselect from the
  remaining open cases rather than a stale routed follow-on.
- `IC-23F2C79C8AA7` is now a deployed reduced owner surface; no later registry
  sweep is required to finish the packet.
- Future document-route behavior should land in the focused access, runs,
  evaluations, artifact, or semantic siblings rather than broadening
  `tests/unit/test_documents_api.py` again.

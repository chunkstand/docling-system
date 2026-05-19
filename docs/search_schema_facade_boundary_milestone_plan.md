# Search Schema Facade Boundary Milestone Plan

Date: 2026-05-18 local / 2026-05-19 UTC
Status: resolved locally in the current checkout for `IC-DCEE88C7CA97`;
`app/schemas/search.py` is now a narrow compatibility facade, the concrete
schema definitions now live in focused owner modules, and the routed queue now
advances to the next under-budget packet instead of reopening the facade.
Owner context: routed architecture-governance follow-on for
`IC-DCEE88C7CA97` after the agent-tasks API lifecycle closeout returned the
queue to `app/schemas/search.py`. The shared public path had intentionally
high fan-in, but it still mixed core request/result models, request-history
detail and feedback responses, explanation schemas, replay contracts, and the
existing harness or retrieval-learning export surface in one hotspot-marked
module.

## Purpose

Reduce the residual search schema root without shifting debt into a new export
sink, a broad importer-migration churn packet, or an oversized governance
helper.

This packet closes the remaining seam by:

- keeping `app/schemas/search.py` as the shared public import path for current
  callers
- moving core request/result schemas into `app/schemas/search_core.py`
- moving request-history and feedback detail schemas into
  `app/schemas/search_history.py`
- moving explanation schemas into `app/schemas/search_explanations.py`
- moving replay run and comparison schemas into
  `app/schemas/search_replays.py`
- exact-ratcheting the reduced facade plus the focused owner family
- routing the reduced root as a deferred reduced facade in
  `config/hotspot_prevention.yaml`
- extending hotspot-prevention classifier coverage without regrowing the
  existing classifier hotspot owners

## Non-Goals

- No importer sweep away from `app.schemas.search`; the public compatibility
  path remains intentional in this packet.
- No API contract changes for search request, explanation, replay, harness, or
  retrieval-learning schemas.
- No new `_search_schema_exports.py`, `search_public.py`, or similar export
  sink file.
- No search-service or router behavior change outside the schema owner split.
- No test weakening, skip broadening, or xfail broadening to get the refactor
  green.

## Scope

In scope:

- `app/schemas/search.py`
- `app/schemas/search_core.py`
- `app/schemas/search_history.py`
- `app/schemas/search_explanations.py`
- `app/schemas/search_replays.py`
- `app/schemas/search_harness.py`
- `app/schemas/search_learning.py`
- `app/hotspot_prevention_classifier.py`
- `app/hotspot_prevention_classifier_boundary_rules.py`
- `app/hotspot_prevention_classifier_support.py`
- `app/hotspot_prevention_classifier_schema_facades.py`
- `tests/unit/test_search_schema_facade_contract.py`
- `tests/unit/test_hotspot_prevention_search_schema_facade.py`
- `tests/unit/test_hotspot_prevention_policy_contracts.py`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- current routing docs and handoff

Out of scope:

- broad search-family importer churn
- `app/api/routers/search.py`
- `app/services/search.py`
- `tests/unit/test_search_api_harnesses.py`

## 2026-05-18 Local Closeout Update

The local follow-on now keeps `app/schemas/search.py` at `36` lines while the
focused schema owners close at `83`, `77`, `77`, `100`, `220`, and `280`
lines respectively across `search_core.py`, `search_history.py`,
`search_explanations.py`, `search_replays.py`, `search_harness.py`, and
`search_learning.py`. The reduced facade contains only the owner-module
registry plus the shared `__getattr__` and `__dir__` forwarding helpers.

The packet intentionally preserves the public import contract: `50` app-side
importers still use `app.schemas.search`, and the live architecture probe
still shows `app.schemas.search` imported by `75` local modules. That high
fan-in is now deliberate compatibility-facade pressure, not proof that the old
mixed schema owner is still open.

To avoid shifting governance debt into the classifier family, the schema-facade
policy logic now lives in
`app/hotspot_prevention_classifier_schema_facades.py` at `204` lines. The
existing classifier owners close back under their ratchets at `360`, `148`,
and `481` lines respectively for
`app/hotspot_prevention_classifier.py`,
`app/hotspot_prevention_classifier_boundary_rules.py`, and
`app/hotspot_prevention_classifier_support.py`.

`config/hotspot_prevention.yaml` now routes `app/schemas/search.py` as a
deferred reduced facade with the focused owner modules as the preferred future
surfaces, and `config/hygiene_policy.yaml` exact-ratchets the full
post-split family so this packet does not simply move the hotspot into a fresh
unguarded schema or classifier sink.

Live verification in the local checkout:

```text
git diff --check
  pass

uv run ruff check app/schemas/search.py \
  app/schemas/search_core.py \
  app/schemas/search_history.py \
  app/schemas/search_explanations.py \
  app/schemas/search_replays.py \
  app/schemas/search_harness.py \
  app/schemas/search_learning.py \
  app/hotspot_prevention_classifier.py \
  app/hotspot_prevention_classifier_boundary_rules.py \
  app/hotspot_prevention_classifier_support.py \
  app/hotspot_prevention_classifier_schema_facades.py \
  tests/unit/test_search_schema_facade_contract.py \
  tests/unit/test_hotspot_prevention_search_schema_facade.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  pass

uv run pytest -q tests/unit/test_search_schema_facade_contract.py \
  tests/unit/test_hotspot_prevention_search_schema_facade.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py \
  tests/unit/test_search_legibility.py \
  tests/unit/test_search_history.py \
  tests/unit/test_search_replays.py \
  tests/unit/test_search_harness_evaluations.py \
  tests/unit/test_search_harness_optimization.py \
  tests/unit/test_retrieval_learning_candidates.py \
  tests/unit/test_retrieval_learning_artifacts.py
  50 passed

uv run pytest -q tests/unit/test_search_service.py \
  tests/unit/test_search_service_ranking.py \
  tests/unit/test_search_service_persistence.py \
  tests/unit/test_search_service_orchestration.py \
  tests/unit/test_search_execution_orchestration.py \
  tests/unit/test_search_execution_persistence.py \
  tests/unit/test_search_hydration.py \
  tests/unit/test_search_metadata_supplement.py \
  tests/unit/test_search_api.py \
  tests/unit/test_search_api_request_history.py \
  tests/unit/test_search_api_evidence.py \
  tests/unit/test_search_api_replays.py \
  tests/unit/test_evaluation_scoring.py \
  tests/unit/test_evaluation_service.py \
  tests/unit/test_chat_service.py
  86 passed

uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=36
  changed_hotspots=1
  blocked=0
  allowed=27

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt remains limited to
  app/services/agent_task_context_semantic_analysis.py and
  app/services/agent_task_context_technical_reports.py

uv run docling-system-improvement-case-summary
  status_counts={"measured":1,"deployed":20,"open":24,"verified":14}

uv run docling-system-improvement-case-validate
  valid=true

uv run docling-system-architecture-quality-report --summary
  top_routed_hotspot_paths=[
    "tests/unit/test_db_model_import_compatibility.py",
    "app/api/main.py",
    "tests/unit/test_architecture_inspection.py",
    "app/api/routers/agent_tasks.py",
    "app/services/audit_bundles.py"
  ]
  stale_facade_hotspot_count=15

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles --max-file-lines 800
  0 Python cycle components
  0 code files above 800 lines
  app.schemas.search imported by 75 local modules
```

## Current Structural Evidence

- `app/schemas/search.py` is now a `36` line compatibility facade with a
  compact owner registry and the shared `__getattr__` / `__dir__` forwarding
  surface only.
- `app/schemas/search_core.py` now owns page-range, filter, request, score,
  evidence-span, result, and logged-result schemas at `83` lines.
- `app/schemas/search_history.py` now owns feedback, request-detail, and
  replay-diff/response schemas at `77` lines.
- `app/schemas/search_explanations.py` now owns explanation result,
  diagnosis, and explanation-response schemas at `77` lines.
- `app/schemas/search_replays.py` now owns replay-run request, summary, detail,
  query, and comparison schemas at `100` lines.
- `app/schemas/search_harness.py` remains the focused harness schema owner at
  `220` lines and is unchanged except for explicit public export declaration.
- `app/schemas/search_learning.py` remains the focused retrieval-learning
  schema owner at `280` lines and is unchanged except for explicit public
  export declaration.
- No new export-catalog sink file was introduced; facade exports are resolved
  directly from owner `__all__` declarations.

## Residual Risks And Next Routing

- Future schema additions must land in the focused owner modules or the
  existing harness and retrieval-learning owners rather than reopening
  `app/schemas/search.py`.
- The reduced root now carries intentional public fan-in, so future sessions
  must treat it as a deferred reduced facade rather than a default next packet.
- The next active routed packet is `IC-7D8AE7C83B8F` /
  `tests/unit/test_db_model_import_compatibility.py`.

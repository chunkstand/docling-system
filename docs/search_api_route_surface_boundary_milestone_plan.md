# Search API Route Surface Boundary Milestone Plan

Date: 2026-05-18 local / 2026-05-19 UTC
Status: resolved locally through implementation commit `f1f296d` and durable
docs-and-registry closeout commit `8d7d316`, which reduce the residual root
test, move the remaining request-history and evidence-package coverage into
focused sibling tests, and route the reduced root out of the active hotspot
queue.
Owner context: routed architecture-governance follow-on for
`IC-03D7EFA03213` after the hotspot-prevention companion-test closeout moved
the queue back to `tests/unit/test_search_api.py`. The root file was already
under the default `600`-line hygiene budget, but it still mixed top-level
search smoke, request-history detail or explanation, evidence-package, trace,
and feedback contracts in the same high-churn owner surface.

## Purpose

Reduce the residual search API root so future route changes do not funnel back
through one mixed test file.

This packet closes the remaining narrow seam by:

- keeping `tests/unit/test_search_api.py` focused on the public `/search` and
  `/search/executions` entrypoints
- moving request-history, explanation, and feedback coverage into
  `tests/unit/test_search_api_request_history.py`
- moving evidence-package export and trace coverage into
  `tests/unit/test_search_api_evidence.py`
- routing the reduced root as a deferred reduced facade in
  `config/hotspot_prevention.yaml`
- exact-ratcheting the reduced root and the new sibling files so this packet
  does not simply push growth into a fresh ungoverned sink

## Non-Goals

- No replay, harness, or learning-audit rewrite in this packet.
- No new coverage moved into the inherited
  `tests/unit/test_search_api_harnesses.py` hotspot.
- No API contract changes to `app/api/routers/search.py`.
- No attempt to clear every search-family hotspot in one pass.

## Scope

In scope:

- `tests/unit/test_search_api.py`
- `tests/unit/test_search_api_request_history.py`
- `tests/unit/test_search_api_evidence.py`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- current routing docs and handoff

Out of scope:

- `tests/unit/test_search_api_harnesses.py`
- `tests/unit/test_search_api_replays.py`
- `tests/unit/test_search_api_learning_audit.py`
- `app/api/routers/search.py`

## 2026-05-18 Local Closeout Update

The local follow-on now keeps the root search API test at `161` lines while
the moved coverage closes at `152` and `137` lines in
`tests/unit/test_search_api_request_history.py` and
`tests/unit/test_search_api_evidence.py`. Replay, harness, and learning/audit
coverage remain in their established sibling files at `248`, `764`, and `228`
lines respectively, so this packet narrows the root without pushing new lines
into the inherited harness hotspot.

`config/hotspot_prevention.yaml` now routes `tests/unit/test_search_api.py` as
a deferred reduced facade with the focused sibling tests as the preferred next
owner surfaces, and `config/hygiene_policy.yaml` exact-ratchets the reduced
root plus the two new sibling files.

Live verification in the local checkout:

```text
uv run ruff check tests/unit/test_search_api.py \
  tests/unit/test_search_api_request_history.py \
  tests/unit/test_search_api_evidence.py \
  tests/unit/test_search_api_replays.py \
  tests/unit/test_search_api_harnesses.py \
  tests/unit/test_search_api_learning_audit.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  pass

uv run pytest -q tests/unit/test_search_api.py \
  tests/unit/test_search_api_request_history.py \
  tests/unit/test_search_api_evidence.py \
  tests/unit/test_search_api_replays.py \
  tests/unit/test_search_api_harnesses.py \
  tests/unit/test_search_api_learning_audit.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  43 passed

uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=35
  changed_hotspots=1
  blocked=0
  allowed=1
  tests/unit/test_search_api.py: allowed/deletion

uv run docling-system-hygiene-check
  new hygiene regressions: none

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=20
  max_hotspot_risk_score=486.06
  top_routed_hotspot_paths=[
    "tests/unit/test_agent_tasks_api.py",
    "app/schemas/search.py",
    "app/api/main.py",
    "tests/unit/test_db_model_import_compatibility.py",
    "tests/unit/test_architecture_inspection.py"
  ]
  stale_facade_hotspot_count=13

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  0 Python cycle components
  0 code files above 800 lines
```

Closeout-state recheck after the durable docs-and-registry alignment commit
`8d7d316`:

```text
uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=35
  changed_hotspots=0
  blocked=0
  allowed=0

uv run docling-system-hygiene-check
  new hygiene regressions: none

uv run docling-system-improvement-case-summary
  status_counts={"measured":1,"deployed":19,"open":26,"verified":13}

uv run docling-system-improvement-case-validate
  valid=true

uv run docling-system-architecture-quality-report --summary
  top_routed_hotspot_paths=[
    "tests/unit/test_agent_tasks_api.py",
    "app/schemas/search.py",
    "app/api/main.py",
    "tests/unit/test_db_model_import_compatibility.py",
    "tests/unit/test_architecture_inspection.py"
  ]
  stale_facade_hotspot_count=13

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  largest search-family inherited owner remains
  tests/unit/test_search_api_harnesses.py at 764 lines
  0 Python cycle components
```

## Current Structural Evidence

- `tests/unit/test_search_api.py` is now a narrow top-level search-route smoke
  surface at `161` lines.
- `tests/unit/test_search_api_request_history.py` now owns request detail,
  explanation, and feedback coverage at `152` lines.
- `tests/unit/test_search_api_evidence.py` now owns evidence-package export
  and trace coverage at `137` lines.
- `tests/unit/test_search_api_replays.py` remains `248` lines and unchanged in
  this packet.
- `tests/unit/test_search_api_harnesses.py` remains `764` lines and unchanged
  in this packet; it is inherited debt, not debt introduced by this split.
- `tests/unit/test_search_api_learning_audit.py` remains `228` lines and
  unchanged in this packet.
- The routed queue no longer selects the reduced root and now advances to
  `IC-D9A84C20546B` / `tests/unit/test_agent_tasks_api.py`.

## Residual Risks And Next Routing

- The reduced search API root is now correctly routed as a deferred reduced
  facade, but the inherited `tests/unit/test_search_api_harnesses.py` owner
  remains above the default budget and may become a later packet if churn
  raises it back into the routed queue.
- The next active routed packet is `IC-D9A84C20546B` /
  `tests/unit/test_agent_tasks_api.py`.
- Future search-family changes should add coverage in the focused request,
  evidence, replay, harness, and learning-audit sibling files rather than
  reopening `tests/unit/test_search_api.py`.

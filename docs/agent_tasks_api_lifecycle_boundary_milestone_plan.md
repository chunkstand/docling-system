# Agent Tasks API Lifecycle Boundary Milestone Plan

Date: 2026-05-18 local / 2026-05-19 UTC
Status: resolved locally through implementation commit `790fa2d` plus durable
docs-and-registry closeout commit `8ce05b7`, which retires the last oversized
focused sibling under `IC-D9A84C20546B`, keeps the root API smoke file small,
and records the reduced facade without routing debt back into the family.
Owner context: routed architecture-governance follow-on for
`IC-D9A84C20546B` after the search API route-surface closeout returned the
queue to `tests/unit/test_agent_tasks_api.py`. The root file was already down
to `92` lines, but the remaining lifecycle owner still mixed analytics and
trace-export coverage with task lifecycle, outcome, artifact, verification,
and approval route behavior in a `756` line sibling.

## Purpose

Reduce the remaining agent-tasks API family hotspot so the case closes without
shifting growth into another ungoverned sibling or a new support sink.

This packet closes the remaining seam by:

- keeping `tests/unit/test_agent_tasks_api.py` as a narrow compatibility and
  route-smoke surface
- reducing `tests/unit/test_agent_tasks_api_lifecycle.py` to task list, create,
  detail, outcome, verification, and approval lifecycle coverage only
- moving analytics and trace-export coverage into
  `tests/unit/test_agent_tasks_api_analytics.py`
- moving artifact list/detail and failure-artifact success coverage into the
  existing `tests/unit/test_agent_tasks_api_artifacts.py`
- exact-ratcheting the focused agent-tasks API family so the packet does not
  simply push growth into a different sibling file
- routing the reduced root as a deferred reduced facade in
  `config/hotspot_prevention.yaml`

## Non-Goals

- No new generic `*_support.py` helper sink for the unit test family.
- No API contract changes to `app/api/routers/agent_tasks.py` or
  `app/api/routers/agent_task_analytics.py`.
- No rewrite of the claim-support or auth siblings beyond exact ratchets.
- No broader agent-task service or schema refactor in this packet.

## Scope

In scope:

- `tests/unit/test_agent_tasks_api.py`
- `tests/unit/test_agent_tasks_api_lifecycle.py`
- `tests/unit/test_agent_tasks_api_analytics.py`
- `tests/unit/test_agent_tasks_api_artifacts.py`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `config/hotspot_prevention.yaml`
- current routing docs and handoff

Out of scope:

- `tests/unit/test_agent_tasks_api_claim_support.py`
- `tests/unit/test_agent_tasks_api_auth.py`
- `app/api/routers/agent_tasks.py`
- `app/api/routers/agent_task_analytics.py`

## 2026-05-18 Local Closeout Update

The local follow-on now keeps the root agent-tasks API file at `92` lines,
reduces `tests/unit/test_agent_tasks_api_lifecycle.py` to `360` lines, adds
`tests/unit/test_agent_tasks_api_analytics.py` at `360` lines, and grows the
existing artifacts sibling only to `566` lines while keeping the claim-support
and auth siblings unchanged at `419` and `93` lines. The full focused family
now closes below the default `600`-line hygiene budget without creating a new
generic support file.

`config/hotspot_prevention.yaml` now routes `tests/unit/test_agent_tasks_api.py`
as a deferred reduced facade with the focused family as the preferred future
owner surfaces, and `config/hygiene_policy.yaml` exact-ratchets the reduced
root plus the focused sibling files.

Live verification in the local checkout:

```text
uv run ruff check tests/unit/test_agent_tasks_api.py \
  tests/unit/test_agent_tasks_api_*.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  pass

uv run pytest -q tests/unit/test_agent_tasks_api.py \
  tests/unit/test_agent_tasks_api_*.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py
  49 passed

uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=35
  changed_hotspots=0
  blocked=0
  allowed=0

uv run docling-system-hygiene-check
  new hygiene regressions: none

uv run docling-system-improvement-case-summary
  status_counts={"measured":1,"deployed":19,"open":25,"verified":14}

uv run docling-system-improvement-case-validate
  valid=true

uv run docling-system-architecture-quality-report --summary
  top_routed_hotspot_paths=[
    "app/schemas/search.py",
    "app/api/main.py",
    "tests/unit/test_db_model_import_compatibility.py",
    "tests/unit/test_architecture_inspection.py",
    "app/api/routers/agent_tasks.py"
  ]
  stale_facade_hotspot_count=14

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  0 Python cycle components
  0 code files above 800 lines
```

Closeout-state recheck after the durable docs-and-registry alignment:

```text
uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=35
  changed_hotspots=0
  blocked=0
  allowed=0

uv run docling-system-hygiene-check
  new hygiene regressions: none

uv run docling-system-improvement-case-summary
  status_counts={"measured":1,"deployed":20,"open":25,"verified":13}

uv run docling-system-improvement-case-validate
  valid=true

uv run docling-system-architecture-quality-report --summary
  top_routed_hotspot_paths=[
    "app/schemas/search.py",
    "app/api/main.py",
    "tests/unit/test_db_model_import_compatibility.py",
    "tests/unit/test_architecture_inspection.py",
    "app/api/routers/agent_tasks.py"
  ]
  stale_facade_hotspot_count=14
```

The durable docs-and-registry closeout commit `8ce05b7` records the packet as
deployed while preserving `790fa2d` as the implementation reference in
`config/improvement_cases.yaml`.

## Current Structural Evidence

- `tests/unit/test_agent_tasks_api.py` remains the `92` line compatibility and
  route-smoke surface.
- `tests/unit/test_agent_tasks_api_analytics.py` now owns analytics summary,
  trend, decision-signal, workflow-summary, and trace-export route coverage at
  `360` lines.
- `tests/unit/test_agent_tasks_api_artifacts.py` now owns context,
  audit-bundle, evidence-manifest, evidence-trace, provenance, artifact detail,
  and failure-artifact route coverage at `566` lines.
- `tests/unit/test_agent_tasks_api_lifecycle.py` now owns task list, create,
  detail, outcome, verification, and approval lifecycle coverage at `360`
  lines.
- `tests/unit/test_agent_tasks_api_claim_support.py` remains `419` lines and
  unchanged in this packet.
- `tests/unit/test_agent_tasks_api_auth.py` remains `93` lines and unchanged
  in this packet.
- The routed queue no longer selects the reduced root and now advances to
  `IC-DCEE88C7CA97` / `app/schemas/search.py`.

## Residual Risks And Next Routing

- The reduced root is now ready to be treated as a deferred reduced facade, but
  future agent-task API growth must continue landing in the focused analytics,
  claim-support, artifacts, lifecycle, and auth siblings rather than reopening
  the root file.
- The next active routed packet is `IC-DCEE88C7CA97` /
  `app/schemas/search.py`.

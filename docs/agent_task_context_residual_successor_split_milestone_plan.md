# Agent-Task Context Residual Successor Split Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: resolved through the 2026-05-19 Packet C residual-successor split.
`IC-3B4C9F2A76E1` is now deployed, the reduced roots and new support modules
are exact-ratcheted and hotspot-governed, and Packet D
`IC-25C1F7B9E4DA` is now the next queued packet.
Owner context: code-owning closeout for the last over-budget focused successor
tests left behind by the earlier `tests/unit/test_agent_task_context.py`
family split.

## Purpose

Finish the agent-task context residual test lane without reopening the reduced
compatibility root or shifting the debt into a fresh ungoverned helper sink.

## Scope

In scope:

- `tests/unit/test_agent_task_context_reports_claim_support.py`
- `tests/unit/agent_task_context_reports_claim_support_support.py`
- `tests/unit/test_agent_task_context_semantic_graph_promotions.py`
- `tests/unit/agent_task_context_semantic_graph_promotions_support.py`
- `tests/unit/test_hotspot_prevention_agent_task_context_routes.py`
- `tests/unit/test_hotspot_prevention_policy_contracts.py`
- `app/hotspot_prevention_classifier_support.py`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- `docs/agent_task_context_residual_successor_split_milestone_plan.md`
- `docs/remaining_packet_queue_resolution_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/agent_task_residual_owner_family_milestone_plan.md`
- `docs/oversized_test_hotspots_boundary_milestone_plan.md`

Out of scope:

- `tests/unit/test_search_service_ranking.py`
- broader search-service residual routing
- any service-layer implementation changes under `app/services/agent_task_context*.py`

## Current Evidence

Milestone 0 rebaseline from the live checkout before the split confirmed that
only the two focused successor files still violated the default `600`-line
budget:

```text
uv run docling-system-improvement-case-summary
  case_count=61
  status_counts={"measured":1,"deployed":58,"open":2}

wc -l tests/unit/test_agent_task_context.py \
  tests/unit/test_agent_task_context_reports_claim_support.py \
  tests/unit/test_agent_task_context_semantic_graph_promotions.py
    328 tests/unit/test_agent_task_context.py
    636 tests/unit/test_agent_task_context_reports_claim_support.py
    653 tests/unit/test_agent_task_context_semantic_graph_promotions.py
```

## Closeout Summary

Packet C extracts the shared payload and fake-session scaffolding into
family-local support modules and leaves the focused roots as narrow behavior
surfaces:

- `tests/unit/test_agent_task_context.py` remains at `328` lines.
- `tests/unit/test_agent_task_context_reports_claim_support.py` now closes at
  `358` lines.
- `tests/unit/agent_task_context_reports_claim_support_support.py` now closes
  at `294` lines.
- `tests/unit/test_agent_task_context_semantic_graph_promotions.py` now closes
  at `236` lines.
- `tests/unit/agent_task_context_semantic_graph_promotions_support.py` now
  closes at `426` lines.

Hotspot prevention now routes the two reduced roots as deferred reduced
facades and the two support modules as accepted residual boundaries, while
hygiene exact-ratchets all four files under `IC-3B4C9F2A76E1`.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The split just moves the debt into a new helper sink. | support modules, hygiene policy | exact line ratchets plus support-module hotspot prevention | Either new support module lands above `600` lines. | Leave one support module above `600` and confirm Packet C cannot close. | Future Codex replaces one oversized test file with one oversized support file. |
| The reduced roots regrow because future scenario additions still land there. | reduced roots, hotspot prevention | deferred reduced-facade routing plus focused route-behavior tests | New broad scenario groups or helper scaffolding are allowed in the reduced roots. | Remove the route entries and confirm the policy tests fail. | Future Codex quietly reopens the reduced roots instead of creating focused siblings. |
| The closeout passes only because the hotspot-prevention gate is weakened. | hotspot policy, strict check | strict hotspot-prevention run with only narrow support-extraction exceptions | Packet C requires broad unscoped exceptions or blocked findings remain. | Add a wildcard-like exception and confirm policy review rejects it. | Future Codex can hide unrelated regrowth behind the Packet C exception. |

## Required Verification Gates

- `git diff --check`
- `uv run ruff check tests/unit/test_agent_task_context.py tests/unit/test_agent_task_context_freshness.py tests/unit/test_agent_task_context_semantic_generation.py tests/unit/test_agent_task_context_reports_claim_support.py tests/unit/agent_task_context_reports_claim_support_support.py tests/unit/test_agent_task_context_semantic_governance.py tests/unit/test_agent_task_context_semantic_governance_ontology.py tests/unit/agent_task_context_semantic_governance_support.py tests/unit/test_agent_task_context_semantic_graph.py tests/unit/test_agent_task_context_semantic_graph_promotions.py tests/unit/agent_task_context_semantic_graph_promotions_support.py tests/unit/test_hotspot_prevention_agent_task_context_routes.py tests/unit/test_hotspot_prevention_policy_contracts.py app/hotspot_prevention_classifier_support.py`
- `uv run pytest -q tests/unit/test_agent_task_context.py tests/unit/test_agent_task_context_freshness.py tests/unit/test_agent_task_context_semantic_generation.py tests/unit/test_agent_task_context_reports_claim_support.py tests/unit/test_agent_task_context_semantic_governance.py tests/unit/test_agent_task_context_semantic_governance_ontology.py tests/unit/test_agent_task_context_semantic_graph.py tests/unit/test_agent_task_context_semantic_graph_promotions.py tests/unit/test_hotspot_prevention_agent_task_context_routes.py tests/unit/test_hotspot_prevention_policy_contracts.py`
- `uv run pytest -q tests/unit/test_agent_task_context.py tests/unit/test_agent_task_context_reports_claim_support.py tests/unit/test_agent_task_context_semantic_graph_promotions.py tests/integration/test_technical_report_harness_integrity.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-validate`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q`

## Acceptance Criteria

- `IC-3B4C9F2A76E1` is recorded as deployed in `config/improvement_cases.yaml`.
- The reduced roots and new support modules all close at or below `600` lines.
- Live counts move from `open=2`, `verified=0`, `deployed=58` to
  `open=1`, `verified=0`, `deployed=59`.
- Packet D `IC-25C1F7B9E4DA` becomes the next queued packet in the queue plan,
  handoff, and architecture index.

## Stop Conditions

- Stop if either new support module regrows above `600` lines.
- Stop if the strict hotspot-prevention gate still blocks Packet C after the
  narrow support-extraction exceptions are added.
- Stop if the queue docs disagree about Packet D being the next packet.

## Local Commit Closeout Policy

- Close Packet C with one atomic commit that includes the test split,
  governance updates, registry closeout, and durable queue-doc refresh.

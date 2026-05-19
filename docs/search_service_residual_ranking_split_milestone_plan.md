# Search-Service Residual Ranking Split Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: resolved through the 2026-05-19 Packet D residual ranking split.
`IC-25C1F7B9E4DA` is now deployed, the reduced search-service root is routed as
a deferred facade, and the later Packet E queue-exhaustion sweep retires the
remaining queue without creating a new follow-on packet.
Owner context: code-owning closeout for the last over-budget focused successor
left behind by the earlier `tests/unit/test_search_service.py` family split.

## Purpose

Finish the residual search-service test lane without reopening the reduced root
or leaving the final ranking assertions in one over-budget owner file.

## Scope

In scope:

- `tests/unit/test_search_service.py`
- `tests/unit/test_search_service_ranking.py`
- `tests/unit/test_search_service_ranking_source_filename.py`
- `tests/unit/test_hotspot_prevention_search_service_routes.py`
- `tests/unit/test_hotspot_prevention_policy_contracts.py`
- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- `docs/search_service_residual_ranking_split_milestone_plan.md`
- `docs/remaining_packet_queue_resolution_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/oversized_test_hotspots_boundary_milestone_plan.md`

Out of scope:

- search-service implementation changes under `app/services/search*.py`
- broader Packet E queue-exhaustion and honesty sweep work

## Current Evidence

Milestone 0 rebaseline from the live checkout before the split confirmed that
the residual root was already small and only the ranking successor still
exceeded the default `600`-line budget:

```text
uv run docling-system-improvement-case-summary
  case_count=61
  status_counts={"measured":1,"deployed":59,"open":1}

wc -l tests/unit/test_search_service.py \
  tests/unit/test_search_service_ranking.py
    117 tests/unit/test_search_service.py
    621 tests/unit/test_search_service_ranking.py
```

## Closeout Summary

Packet D moves the source-filename ranking assertions into a focused sibling and
leaves the original ranking owner as the generic hybrid, table, and prose
ranking surface:

- `tests/unit/test_search_service.py` remains at `117` lines.
- `tests/unit/test_search_service_ranking.py` now closes at `532` lines.
- `tests/unit/test_search_service_ranking_source_filename.py` now closes at
  `158` lines.

Hotspot prevention now routes the reduced search-service root as a deferred
facade, hygiene exact-ratchets the residual root and both ranking owners, and
focused route-behavior coverage enforces that new ranking scenarios stay out of
the reduced root.

The later Packet D alignment sweep updates the owner-case deployment ref to
`4fa696a`, confirms the live registry stays at `open=0`, `verified=0`, and
`deployed=60`, and removes stale "Packet D remains open" wording from the
current-state adjacent summaries. The later Packet E queue-exhaustion sweep
then retires the queue plan itself, so this Packet D closeout no longer stands
as a "next packet" handoff surface.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The split only moves the debt into a fresh ranking sink. | ranking owners, hygiene policy | exact line ratchets on the ranking owners | Any focused ranking owner regrows above `600` lines. | Leave the new source-filename ranking sibling above `600` and confirm Packet D cannot close. | Future Codex swaps one oversized ranking file for another. |
| Future ranking scenarios leak back into the reduced smoke root. | `tests/unit/test_search_service.py`, hotspot prevention | deferred reduced-facade routing plus focused route-behavior tests | New ranking scenario groups or helper scaffolding are allowed in the reduced root. | Remove the routing and confirm the route-behavior tests fail. | Future Codex reopens the residual smoke surface instead of using a focused sibling. |
| The queue closes the open case but leaves stale queue truth behind. | handoff, queue plan, architecture index | durable-doc alignment review | Current-state docs disagree about Packet E or the live counts. | Update only the owner case and leave Packet D listed as next. | Future Codex reruns Packet D or assumes the queue is exhausted without an explicit Packet E sweep. |

## Required Verification Gates

- `git diff --check`
- `uv run ruff check tests/unit/test_search_service.py tests/unit/test_search_metadata_supplement.py tests/unit/test_search_service_ranking.py tests/unit/test_search_service_ranking_source_filename.py tests/unit/test_search_service_orchestration.py tests/unit/test_search_service_persistence.py tests/unit/test_hotspot_prevention_search_service_routes.py tests/unit/test_hotspot_prevention_policy_contracts.py`
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_metadata_supplement.py tests/unit/test_search_service_ranking.py tests/unit/test_search_service_ranking_source_filename.py tests/unit/test_search_service_orchestration.py tests/unit/test_search_service_persistence.py tests/unit/test_hotspot_prevention_search_service_routes.py tests/unit/test_hotspot_prevention_policy_contracts.py`
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_service_ranking.py tests/unit/test_search_service_ranking_source_filename.py tests/unit/test_search_api.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-validate`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q`

## Acceptance Criteria

- `IC-25C1F7B9E4DA` is recorded as deployed in `config/improvement_cases.yaml`.
- The reduced root and both focused ranking owners all close at or below
  `600` lines.
- Live counts move from `open=1`, `verified=0`, `deployed=59` to
  `open=0`, `verified=0`, `deployed=60`.
- At the Packet D checkpoint, Packet E becomes the next queued packet in the
  queue plan, handoff, and architecture index until the later Packet E sweep
  exhausts the queue.

## Stop Conditions

- Stop if either focused ranking owner regrows above `600` lines.
- Stop if the strict hotspot-prevention gate still blocks Packet D after the
  reduced-root routing is in place.
- Stop if the queue docs disagree about Packet E being the next packet at the
  Packet D checkpoint.

## Local Commit Closeout Policy

- Close Packet D with one atomic commit that includes the test split,
  governance updates, registry closeout, and durable queue-doc refresh.

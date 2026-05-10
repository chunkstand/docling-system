# Agentic Architecture Milestone Audit

Date: 2026-05-04
Status refreshed: 2026-05-10

Scope: audit the implemented architecture milestones against
`docs/agentic_architecture_milestone_plan.md` and close concrete gaps that can
be verified mechanically without changing public API, database schema, or
runtime behavior.

## Current Gate Snapshot

- `uv run docling-system-architecture-inspect`: valid with `violation_count=0`,
  `api_route_count=130`, `agent_action_count=51`, `contract_count=10`, and
  `inspection_rule_count=13`.
- `uv run docling-system-capability-contracts`: valid with `facade_count=6`,
  `function_count=110`, and no issues.
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=687.04`, and top hotspot paths
  headed by `app/db/models.py`, `app/cli.py`, `app/services/evidence.py`,
  `app/services/agent_task_actions.py`, and `tests/unit/test_cli.py`.
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown`:
  3 Python cycle components remain. `app.services.agent_task_actions` still has
  fan-out 39 and participates in the large agent-task cycle component.
- `uv run ruff check app tests`: passed.
- Focused architecture tests:
  `tests/unit/test_architecture_inspection.py`,
  `tests/unit/test_architecture_quality.py`,
  `tests/unit/test_capability_contracts.py`, and
  `tests/unit/test_api_route_contracts.py` passed with `34 passed`.
- DB-backed model verification is current for `Architecture Plan 01`
  Milestone 2: `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
  passed with `1105 passed`, and the focused Postgres metadata/create-all gate
  now passes with `7 passed`.
- DB-backed service verification is current for the `Architecture Plan 01`
  Milestone 4 alignment closeout:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` passed with
  `1110 passed in 49.04s`.
- CLI verification is current for `Architecture Plan 01` Milestone 5:
  `uv run pytest -q tests/unit/test_cli.py` passed with `55 passed`.
- Search verification is current for `Architecture Plan 01` Milestone 6:
  focused query feature/service/API tests passed with `70 passed`,
  search history/replay/release-gate tests passed with `20 passed`, and
  DB-backed search replay/release roundtrips passed with `4 passed`.
- Full DB-backed verification is current for `Architecture Plan 01` Milestone 6:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q` passed with
  `1114 passed in 49.01s` after the alignment closeout.
- Evidence verification is current for `Architecture Plan 01` Milestone 7:
  focused evidence/technical-report tests passed with `39 passed`, the
  DB-backed technical-report harness roundtrip passed with `1 passed`, and
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q` passed with
  `1115 passed in 54.05s`.
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene` is
  current and reports `observation_count=0`.
- `uv run docling-system-evaluation-data-readiness` is current but still
  reports `regression_ready=false`, `court_grade_ready=false`, and
  `failed_gate_count=11` because the local DB has no active corpus.

## Gap Closures

- Milestone 0 now scores agent legibility against tests, examples, trace or
  replay commands, and linked architecture decision rationale, not only surface
  size and ownership.
- Milestone 1 now exposes narrower contract companions for retrieval search,
  evidence, chat/feedback, replay, harness, audit, and learning while
  preserving the `retrieval` compatibility facade.
- Milestone 1 now exposes narrower contract companions for agent task
  lifecycle, context/artifacts/evidence, approval/verification, analytics, and
  actions while preserving the `agent_orchestration` compatibility facade.
- Milestone 3 now validates stale context-builder names inside the action
  manifest validator, not only in a side test.
- Milestone 4 now samples search replay regressions directly in the trace
  review report and routes them through the improvement-case source vocabulary.
- Milestone 6 now emits improvement-case candidates for broad or low-legibility
  capability facades as well as file hotspots.
- Milestone 5 now has a compact architecture index that links milestone
  status, commands, generated maps, review surfaces, known debt, and this audit.
- `Architecture Plan 01` Milestone 2 now has the first physical data-model
  domain split: `ApiIdempotencyKey` moved into
  `app/db/model_domains/platform.py` while `app.db.models` remains an
  import-compatible facade.
- The model compatibility harness now verifies platform-support index and
  unique-constraint column ordering in both unit metadata and Postgres
  `Base.metadata.create_all(...)` paths.
- `Architecture Plan 01` Milestone 3 now has the first evidence service split:
  search evidence package assembly/export/trace graph behavior moved into
  `app/services/evidence_search_packages.py`,
  `app/services/evidence_search_trace_graph.py`, and
  `app/services/evidence_search_trace_store.py` while `app.services.evidence`
  remains import-compatible.
- Shared trace row/spec helpers and evidence export payload helpers were
  centralized in `app/services/evidence_common.py` and
  `app/services/evidence_records.py` so the split does not introduce
  duplicate-helper hygiene findings.
- `Architecture Plan 01` Milestone 4 now has the first agent-task action
  registry split: search-harness action contract metadata and helper logic live
  in `app/services/agent_actions/search_harness.py` while
  `app.services.agent_task_actions` remains the public registry facade and
  execution entrypoint.
- The Milestone 4 alignment gap is closed by documenting that the completed
  slice moved registry/helper ownership, not executor implementations. The
  remaining import-cycle signal is tracked with a next action-family target:
  search-harness executor dependency seam or a more isolated semantic executor
  family.
- `Architecture Plan 01` Milestone 5 now has the first physical CLI command
  group split: improvement-case validate/list/summary/record implementations
  live in `app/cli_commands/improvement_cases.py` while `app.cli` remains the
  console script compatibility surface through explicit forwarding functions.
- The Milestone 5 alignment gap is closed by replacing lint-suppressed
  import-only re-exports with explicit `app.cli` forwarding functions and
  import-resolved console-script coverage.
- `Architecture Plan 01` Milestone 6 now has the first physical search-core
  split: query-intent classification, tabular-query detection, identifier
  lookup detection, normalized query feature sets, token/phrase coverage
  helpers, and metadata-query token extraction live in
  `app/services/search_query_features.py` while `app.services.search` remains
  import-compatible for existing public and private helper names.
- The Milestone 6 alignment check confirmed that `app/services/search.py`
  dropped from 3,429 to 3,250 probe-counted lines and its architecture-probe
  hotspot score dropped from 89,154 to 87,750 without adding a new static
  import-cycle component. The focused compatibility test now covers every
  forwarded query-feature helper alias exposed by `app.services.search`.
- `Architecture Plan 01` Milestone 7 now has the second physical
  `app/services/evidence.py` split: technical-report PROV export relation
  helpers, immutable freeze payloads, hash-chain receipts, signing, and receipt
  integrity live in `app/services/evidence_provenance.py` while
  `app.services.evidence` remains import-compatible for existing PROV helper
  names.
- The Milestone 7 alignment check confirmed that `app/services/evidence.py`
  dropped from 8,608 to 8,261 probe-counted lines and its post-commit
  architecture-probe hotspot score dropped from 387,360 to 380,006 without
  adding a new static import-cycle component.

## Deferred Large Refactors

The plan's physical implementation splits remain governed hotspot work, not
hidden gaps. The first `app/db/models.py` domain split is complete; additional
model domains should still move one at a time. The first two
`app/services/evidence.py` splits are complete; additional evidence domains
should still move one at a time. The first `app/services/agent_task_actions.py`
registry/helper split is complete; additional action families should still move
one at a time. The first `app/cli.py` command-group split is complete;
additional CLI groups should still move one at a time behind compatibility
forwarding functions. The first `app/services/search.py` core split is
complete; additional search concerns should still move one at a time behind the
same compatibility facade with replay/ranking coverage. The next active
architecture milestone is `Architecture Plan 01` Milestone 8 for the
improvement-intake ratchet. Later governed split surfaces include additional
evidence concerns, additional CLI command groups, additional search concerns,
and additional agent-action families. The next agent-action family split should first
introduce a dependency seam for executor movement or choose a family whose
executors do not keep the broad agent-task cycle intact.
Each future split should land as a separate
behavior-preserving milestone with focused tests plus the full integration
gate.

## Verification Contract

Before landing this audit slice, run:

- `uv run ruff check app tests`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-decisions`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

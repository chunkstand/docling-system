# Semantics Service Boundary Milestone Plan

Date: 2026-05-13 local / 2026-05-14 UTC
Status: resolved locally through closeout commit `a2eb27e` on 2026-05-13
local / 2026-05-14 UTC after
`docs/search_execution_orchestration_boundary_milestone_plan.md`,
`docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
`docs/evaluations_service_boundary_milestone_plan.md`, and
`docs/evidence_provenance_exports_boundary_milestone_plan.md` all closed
first. Milestones 0-5 completed, `app/services/semantics.py` is now a 54-line
compatibility facade, and the broader `IC-9E6B8F5D62A1` owner case is now
locally retirement-ready pending commit because the later lifecycle
or reads follow-on now keeps
`app/services/semantic_pass_lifecycle.py` at 529 lines,
`app/services/semantic_pass_reads.py` at 372 lines, the extracted lifecycle
artifact owner `app/services/semantic_pass_artifacts.py` at 150 lines, and the
extracted review or projection owner `app/services/semantic_pass_reviews.py`
at 369 lines while the extracted read source-record owner now also lives in
`app/services/semantic_pass_source_records.py` at 415 lines and all governed
semantic owners are under the default 600-line budget or the 800-line
secondary owner ceiling.
Owner context: local closeout under `IC-9E6B8F5D62A1`; the lifecycle/read
follow-on is now the latest resolved bounded semantic packet in
`docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`, where
Milestones 0 through 5 are resolved locally and the broader semantic owner
family is retirement-ready pending commit. The broader repo current active
bounded follow-on now routes through
`docs/hotspot_prevention_family_boundary_milestone_plan.md`.

## Local Closeout Summary

- Closeout commit: `a2eb27e`
- Milestone 0 refreshed the stacked post-search-orchestration, claim-support,
  evaluations, and evidence provenance-export state and promoted this plan to
  the active bounded implementation brief before the semantics split landed.
- Milestones 1-4 added explicit semantics owner-case and hotspot-prevention
  governance, extracted semantic pass lifecycle ownership into
  `app/services/semantic_pass_lifecycle.py`, active-pass
  row/detail/continuity reads into
  `app/services/semantic_pass_reads.py`, and registry preview ownership into
  `app/services/semantic_registry_preview.py` at 558 lines / 5 private
  helpers.
- `app/services/semantics.py` is now a 54-line compatibility facade that only
  re-exports the stable semantics surface and preserves the registry-preview
  forwarding wrapper through an allowed facade seam.
- The later semantic lifecycle or reads follow-on now reduces
  `app/services/semantic_pass_lifecycle.py` to 529 lines / 3 private helpers,
  moves semantic artifact ownership into
  `app/services/semantic_pass_artifacts.py` at 150 lines / 0 private helpers,
  and moves review or projection ownership into
  `app/services/semantic_pass_reviews.py` at 369 lines / 4 private helpers,
  reduces `app/services/semantic_pass_reads.py` to 372 lines / 3 private
  helpers, and moves source materialization or record shaping into
  `app/services/semantic_pass_source_records.py` at 415 lines / 4 private
  helpers.
- Route, capability, worker, and backfill behavior remained stable through the
  existing semantics surface while the split added focused owner coverage in
  `tests/unit/test_semantic_pass_lifecycle.py`,
  `tests/unit/test_semantic_pass_reads.py`, and
  `tests/unit/test_semantic_registry_preview.py`.
- The broader owner case is now locally retirement-ready pending commit
  because the extracted lifecycle, read, artifact, review, and read
  source-record owners are all under budget, and the latest architecture
  probe no longer lists the semantic runtime family inside the current
  three-component Python cycle baseline.
- The broader repo has now advanced to the hotspot-prevention family follow-on
  in `docs/hotspot_prevention_family_boundary_milestone_plan.md`, where
  `IC-6C1B516A3F92` currently governs
  `app/hotspot_prevention_classifier.py` at `999` lines / `1` private helper
  and companion test routing now also lives under `IC-15F6E41A9C77` for
  `tests/unit/test_hotspot_prevention.py` at `1244` lines / `2` private
  helpers.

## Local Verification

- `git diff --check`: pass
- `uv run ruff check app/services/semantics.py app/services/semantic_pass_lifecycle.py app/services/semantic_pass_reads.py app/services/semantic_registry_preview.py app/services/runs.py app/services/semantic_backfill.py app/services/semantic_ontology.py app/services/agent_task_verifications.py app/services/capabilities/semantics.py app/api/routers/semantics.py app/hotspot_prevention_classifier.py tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py`: pass
- `uv run pytest -q tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py`: `95 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py tests/integration/test_semantic_bootstrap_roundtrip.py tests/integration/test_semantic_candidate_roundtrip.py tests/integration/test_semantic_generation_roundtrip.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`: `17 passed`
- `uv run docling-system-hotspot-prevention-check --strict`: `known_hotspots=11`, `changed_hotspots=1`, `blocked=0`, `allowed=31`, `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`: `valid=true`, `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-improvement-case-validate`: `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=29`, `status_counts.open=21`, `status_counts.deployed=7`, `status_counts.measured=1`, `measured_case_count=19`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`: top hotspot remains `app/cli.py`, `app/services/semantics.py` is absent from the top 12 churn hotspots, and the remaining Python cycle count is `5`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1926 passed`

## Purpose

Resolve the under-governed owner-module knot that still lives in
`app/services/semantics.py`.

The scoped problem is not only file size. The current service still mixes
multiple distinct concern families in one place:

- semantic pass row preparation and execution lifecycle
- projection refresh and review-overlay persistence
- active-pass row/detail/continuity reads
- registry preview materialization and expectation-delta reporting

This plan resolves that scoped knot behind the existing compatibility facade by
splitting lifecycle ownership, read ownership, and preview ownership into three
focused owner modules while explicitly forbidding the work from spilling into
already-large adjacent semantic modules such as
`app/services/semantic_graph.py`,
`app/services/semantic_candidates.py`,
`app/services/semantic_generation.py`,
`app/services/semantic_governance.py`,
`app/services/semantic_orchestration.py`, or
`app/services/semantic_registry.py`.

## Original Baseline Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-13
local / 2026-05-13 UTC:

```text
git status -sb
  ## main...origin/main [ahead 8]
   M app/hotspot_prevention_classifier.py
   M app/services/search.py
   M config/hotspot_prevention.yaml
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
   M tests/unit/test_hotspot_prevention.py
  ?? app/services/search_execution_orchestration.py
  ?? docs/claim_support_policy_impacts_boundary_milestone_plan.md
  ?? docs/evaluations_service_boundary_milestone_plan.md
  ?? docs/evidence_provenance_exports_boundary_milestone_plan.md
  ?? docs/search_execution_orchestration_boundary_milestone_plan.md
  ?? tests/unit/test_search_execution_orchestration.py

wc -l app/services/semantics.py app/services/semantic_graph.py app/services/semantic_generation.py app/services/semantic_candidates.py app/services/semantic_governance.py app/services/semantic_orchestration.py app/services/semantic_registry.py app/services/semantic_backfill.py app/api/routers/semantics.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/integration/test_postgres_roundtrip.py
  2309 app/services/semantics.py
  1847 app/services/semantic_graph.py
  1259 app/services/semantic_generation.py
  1357 app/services/semantic_candidates.py
  1157 app/services/semantic_governance.py
  1092 app/services/semantic_orchestration.py
   726 app/services/semantic_registry.py
   494 app/services/semantic_backfill.py
   226 app/api/routers/semantics.py
   394 tests/unit/test_documents_api_semantics.py
   232 tests/unit/test_semantic_orchestration.py
  1132 tests/integration/test_postgres_roundtrip.py

uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=531.06
  top_hotspot_paths=[
    app/db/models.py,
    app/services/agent_task_actions.py,
    app/cli.py,
    app/schemas/agent_tasks.py,
    app/services/evidence.py
  ]

uv run docling-system-improvement-case-summary
  case_count=28
  status_counts.open=21
  actionable_buckets.oldest_open_case_id=IC-9812A0B138D9

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  app/services/semantics.py: 2309 lines
  app/services/semantics.py hotspot score=20781
  Python cycle component includes:
    app.services.chat,
    app.services.documents,
    app.services.evaluations,
    app.services.runs,
    app.services.search,
    app.services.search_execution_persistence,
    app.services.search_hydration,
    app.services.semantics

config/hygiene_policy.yaml
  app/services/semantics.py currently allows max_lines=2309 and
  max_private_helpers=28 with no owner_case_id or ratchet
```

Repo-current structural evidence:

- `docs/search_execution_orchestration_boundary_milestone_plan.md`,
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
  `docs/evaluations_service_boundary_milestone_plan.md`, and
  `docs/evidence_provenance_exports_boundary_milestone_plan.md` are all still
  drafted in the worktree. The current checkout also already contains in-flight
  search orchestration implementation surfaces in `app/services/search.py`,
  `app/services/search_execution_orchestration.py`,
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`, and
  `tests/unit/test_hotspot_prevention.py`. The active execution packet
  therefore remains the search orchestration plan, with claim-support,
  evaluations, and evidence provenance exports queued behind it, and this
  semantics follow-on must begin with a system-state refresh after all four
  prior packets complete and are committed.
- `app/services/semantics.py` still groups the main concern families together:
  `_prepare_semantic_pass_row(...)`,
  `execute_semantic_pass(...)`,
  `_refresh_semantic_pass_projection(...)`,
  `review_active_semantic_assertion(...)`,
  `review_active_semantic_assertion_category_binding(...)`,
  `get_active_semantic_pass_row(...)`,
  `get_active_semantic_pass_detail(...)`,
  `get_active_semantic_continuity(...)`, and
  `preview_semantic_registry_update_for_document(...)`.
- Runtime, route, and capability callers currently depend on the
  `app.services.semantics` facade through:
  `app/services/runs.py`,
  `app/services/semantic_backfill.py`,
  `app/services/semantic_facts.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_generation.py`,
  `app/services/semantic_graph.py`,
  `app/services/semantic_ontology.py`,
  `app/services/agent_task_verifications.py`,
  `app/services/agent_actions/semantic_analysis_actions.py`,
  `app/services/capabilities/semantics.py`, and
  `app/api/routers/semantics.py`.
- The externally reachable route family is narrow but real:
  `/documents/{document_id}/semantics/latest`,
  `/documents/{document_id}/semantics/latest/continuity`,
  `/documents/{document_id}/semantics/latest/artifacts/{format}`,
  and the two review mutation endpoints must remain behavior-stable, including
  the structured `404`, `403`, and `409` paths already covered in
  `tests/unit/test_documents_api_semantics.py`.
- `app/services/semantics.py` currently has no explicit owner routing in
  `config/improvement_cases.yaml` and no dedicated hotspot-prevention rule in
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`, or
  `tests/unit/test_hotspot_prevention.py`. This is the governance gap that
  makes the debt under-governed rather than only oversized.
- Adjacent semantic owners are already large enough that they must not absorb
  this debt:
  `app/services/semantic_graph.py` is `1847` lines,
  `app/services/semantic_candidates.py` is `1357` lines,
  `app/services/semantic_generation.py` is `1259` lines,
  `app/services/semantic_governance.py` is `1157` lines,
  `app/services/semantic_orchestration.py` is `1092` lines, and
  `app/services/semantic_registry.py` is `726` lines.
- The semantics owner also participates in the remaining service cycle tracked
  by the architecture probe. This plan may reduce pressure on that cycle, but
  it must not expand scope into a broad cycle-break project or move logic into
  `app/services/documents.py`, `app/services/runs.py`, or the search and
  evaluations owners.

## Goal

Resolve the scoped service-boundary knot by the end of this stacked plan so
that:

- `app/services/semantics.py` becomes a narrow compatibility facade and public
  import seam rather than the owner of lifecycle, projection refresh, read, and
  preview implementations.
- A dedicated improvement case and hotspot-prevention rule exist for the
  semantics facade before broad code motion begins.
- At most three new owner modules are introduced:
  `app/services/semantic_pass_lifecycle.py`,
  `app/services/semantic_pass_reads.py`, and
  `app/services/semantic_registry_preview.py`.
- Existing route, capability, worker, and backfill imports remain stable
  through `app.services.semantics`.
- The scoped issue is `resolved` when semantic pass lifecycle, projection
  refresh and review persistence, active-pass reads, and registry preview no
  longer coexist in `app/services/semantics.py`.
- The broader semantics architecture debt is `reduced` unless refreshed live
  evidence proves the hotspot is fully retired.

## Non-Goals

- No search, claim-support, evaluations, evidence, or agent-task refactor in
  this packet.
- No API path, request-model, or response-model redesign for the semantics
  routes.
- No DB schema, ORM model, migration, or storage-contract change.
- No rewrite of `app/services/semantic_graph.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_generation.py`,
  `app/services/semantic_governance.py`,
  `app/services/semantic_orchestration.py`, or
  `app/services/semantic_registry.py`.
- No semantic fact-graph redesign and no move of lifecycle logic into
  `app/services/semantic_backfill.py` or `app/services/runs.py`.
- No attempt to solve the entire semantic subsystem in one packet.
- No broad split into more than three new owner modules.

## Scope

In scope:

- Milestone 0 stacked-state refresh after the search, claim-support,
  evaluations, and evidence provenance-export packets close
- governance bootstrap for `app/services/semantics.py`:
  dedicated improvement-case routing plus hotspot-prevention coverage
- one lifecycle owner module:
  `app/services/semantic_pass_lifecycle.py`
- one read owner module:
  `app/services/semantic_pass_reads.py`
- one registry-preview owner module:
  `app/services/semantic_registry_preview.py`
- direct owner-module unit coverage
- compatibility coverage for `app/services/semantics.py`
- route-boundary and DB-backed integration verification for semantic pass,
  review, continuity, backfill, and registry-preview behavior
- hygiene, improvement-case, architecture-index, and handoff updates for the
  narrowed facade

Out of scope:

- adding a fourth new `semantic_*.py` owner file
- moving lifecycle, read, or preview logic into
  `semantic_graph.py`, `semantic_candidates.py`, `semantic_generation.py`,
  `semantic_governance.py`, `semantic_orchestration.py`, `semantic_registry.py`,
  `runs.py`, or `semantic_backfill.py`
- changing route registration in `app/api/routers/semantics.py`
- changing semantic artifact schema versions, evaluation versions, or storage
  paths
- solving the remaining oversized semantic owner-family modules in this packet

## Owner Surfaces

- compatibility facade:
  `app/services/semantics.py`
- new lifecycle owner:
  `app/services/semantic_pass_lifecycle.py`
- new read owner:
  `app/services/semantic_pass_reads.py`
- new preview owner:
  `app/services/semantic_registry_preview.py`
- importer and compatibility surfaces:
  `app/services/runs.py`,
  `app/services/semantic_backfill.py`,
  `app/services/semantic_ontology.py`,
  `app/services/agent_task_verifications.py`,
  `app/services/semantic_facts.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_generation.py`,
  `app/services/semantic_graph.py`,
  `app/services/capabilities/semantics.py`,
  `app/api/routers/semantics.py`
- adjacent owners that may be called but must not absorb this debt:
  `app/services/semantic_graph.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_generation.py`,
  `app/services/semantic_governance.py`,
  `app/services/semantic_orchestration.py`,
  `app/services/semantic_registry.py`,
  `app/services/semantic_backfill.py`,
  `app/services/runs.py`
- focused tests:
  `tests/unit/test_semantic_pass_lifecycle.py`,
  `tests/unit/test_semantic_pass_reads.py`,
  `tests/unit/test_semantic_registry_preview.py`,
  `tests/unit/test_documents_api_semantics.py`,
  `tests/unit/test_semantic_orchestration.py`,
  `tests/unit/test_semantic_backfill_api.py`,
  `tests/unit/test_run_logic.py`,
  `tests/unit/test_hotspot_prevention.py`,
  and the semantic integration roundtrip family
- governance and routing surfaces:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- New semantic pass lifecycle ownership belongs in
  `app/services/semantic_pass_lifecycle.py`, including:
  semantic pass row preparation,
  source collection and materialization orchestration,
  summary and evaluation refresh wiring,
  projection refresh,
  artifact persistence wiring,
  assertion and category-binding review persistence,
  and the lifecycle-local lookup helpers needed by those mutations.
- New active-pass read ownership belongs in
  `app/services/semantic_pass_reads.py`, including:
  active-pass row lookup,
  detail and continuity reads,
  response assembly,
  fact-count lookup,
  and any read-side record shaping needed by semantic graph, generation,
  candidate, fact, route, or capability callers.
- New registry-preview ownership belongs in
  `app/services/semantic_registry_preview.py`, including:
  preview materialization,
  candidate assertion and binding shaping,
  before/after expectation delta calculation,
  and the preview response payload returned to ontology and agent-task
  verification callers.
- `app/services/semantics.py` remains the public compatibility facade. It may
  contain only:
  import forwarders,
  explicit forwarding wrappers,
  thin dependency-seam helpers,
  shared constant definitions that are part of the public import surface,
  and deletion-only cleanup.
- If a helper is needed by more than one new owner, place it in the owner that
  naturally owns the underlying concern and import it there. Do not create a
  fourth shared-helper module just to shuffle private functions around.
- Do not move new implementation into
  `semantic_graph.py`, `semantic_candidates.py`, `semantic_generation.py`,
  `semantic_governance.py`, `semantic_orchestration.py`, or
  `semantic_registry.py`.
- Keep `app/services/capabilities/semantics.py` and
  `app/api/routers/semantics.py` behavior-stable; they may update import
  targets or aliases, but they must not become new owners of semantics-service
  logic.

## Weak Point Forecast

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The facade keeps growing because the service has no explicit owner-case or hotspot-prevention governance today | `config/improvement_cases.yaml`, `config/hotspot_prevention.yaml`, `app/hotspot_prevention_classifier.py`, `app/services/semantics.py` | `uv run docling-system-hotspot-prevention-check --strict`, `uv run docling-system-improvement-case-validate`, and `tests/unit/test_hotspot_prevention.py` | Code motion starts before a dedicated semantics owner case and facade rule exist | Add a temporary helper such as `def _preview_semantic_registry_delta(...):` to the facade and confirm the gate blocks it | A future session adds “one more semantics helper” because the file has no explicit prevention rule |
| The split silently moves debt into already-large semantic owners | `app/services/semantic_graph.py`, `app/services/semantic_candidates.py`, `app/services/semantic_generation.py`, `app/services/semantic_governance.py`, `app/services/semantic_orchestration.py`, staged diff | `git diff --stat` review plus `uv run docling-system-hygiene-check` | New implementation bodies land in adjacent oversized semantic files instead of the planned new owners | Temporarily move preview logic into `semantic_registry.py` or read shaping into `semantic_graph.py` and confirm staged-slice review or hygiene closeout rejects it | A future session sees “semantic” in the filename and appends the helper to the wrong residual owner |
| Lifecycle, read, and preview concerns are only separated on paper while still cohabiting the same file | `app/services/semantic_pass_lifecycle.py`, `app/services/semantic_pass_reads.py`, `app/services/semantic_registry_preview.py`, `app/services/semantics.py` | `uv run docling-system-hygiene-check` plus file-shape review | More than three new owner modules are introduced, or one selected concern family still has implementation bodies in the facade at closeout | Leave `get_active_semantic_pass_detail(...)` or `preview_semantic_registry_update_for_document(...)` in the facade and confirm acceptance review fails | A future session creates one new module but leaves the rest of the knot in place and still calls the milestone done |
| Route, rerun continuity, review persistence, or registry-preview behavior drifts while internals move | `app/api/routers/semantics.py`, `app/services/capabilities/semantics.py`, semantic integration tests | Named unit and integration verification below | Any latest-pass, continuity, artifact, review, backfill, or registry-preview contract regresses | Temporarily drop a continuity field or review overlay refresh and confirm the unit/integration family fails | A future session assumes the split is “internal only” and skips HTTP-boundary and rerun proof |

Accepted residual risk after closeout: the broader semantics family may still
contain oversized owner modules even if the scoped `app/services/semantics.py`
boundary knot is resolved. If that happens, route the remaining debt from fresh
post-closeout evidence rather than stretching this plan into a semantic
subsystem rewrite.

## Milestone Sequence

This plan is intentionally stacked behind the current search, claim-support,
evaluations, and evidence provenance-export packets. Milestone 0 is mandatory
and must run before any semantics-service code changes start.

### Milestone 0 - Post-Search-Claim-Support-Evaluations-Evidence System-State Refresh

Status: resolved locally
Outcome label: `resolved`

Purpose:

- convert the current repo state from “four prior packets drafted or in flight”
  into the fresh baseline used by this plan
- promote this semantics plan to the active bounded follow-on only after the
  prior four milestones are actually complete

Implementation:

- confirm
  `docs/search_execution_orchestration_boundary_milestone_plan.md`,
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
  `docs/evaluations_service_boundary_milestone_plan.md`, and
  `docs/evidence_provenance_exports_boundary_milestone_plan.md`
  each have a real closeout commit recorded and are no longer merely drafted
- rerun live routing and hotspot evidence after those closeouts:
  `git status -sb`,
  `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-improvement-case-summary`,
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`,
  and `wc -l` for the active semantics owner files
- update `docs/SESSION_HANDOFF.md` and `docs/agentic_architecture_index.md` so
  this semantics plan becomes the active bounded implementation brief
- refresh this plan's evidence section if the prior closeouts changed the live
  counts materially

Acceptance:

- all four prior packets are complete, verified, and committed locally before
  semantics implementation begins
- the targeted concern families still live in `app/services/semantics.py`
- this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` reflect the refreshed post-stack state
- if the targeted concern families have already moved or the prior packets are
  incomplete, stop and rewrite this plan instead of continuing

### Milestone 1 - Semantics Owner-Case And Facade Prevention Bootstrap

Status: resolved locally
Outcome label: `resolved`

Implementation:

- add a dedicated improvement case for `app/services/semantics.py` in
  `config/improvement_cases.yaml` and bind `config/hygiene_policy.yaml` to that
  new `owner_case_id`
- add a hotspot-prevention rule for `app/services/semantics.py` with target
  role `semantic service compatibility facade`
- block new categories for:
  semantic pass lifecycle execution,
  projection refresh and review persistence,
  active-pass read payload assembly,
  and registry preview or expectation-delta logic
- allow only import forwarders, alias forwarders, explicit forwarding wrappers,
  and deletions on the facade
- extend `app/hotspot_prevention_classifier.py` and
  `tests/unit/test_hotspot_prevention.py` with a controlled violation for the
  new rule

Acceptance:

- `uv run docling-system-hotspot-prevention-check --strict` passes on the real
  milestone diff
- `uv run docling-system-improvement-case-validate` passes with the new
  semantics owner case
- the new controlled violation fails when introduced
- the rule allows a narrow forwarding facade but blocks new implementation in
  the compatibility surface

### Milestone 2 - Semantic Pass Lifecycle Owner Extraction

Status: resolved locally
Outcome label: `reduced`

Implementation:

- add `app/services/semantic_pass_lifecycle.py`
- move the lifecycle family into that owner module:
  `_prepare_semantic_pass_row(...)`,
  `execute_semantic_pass(...)`,
  `_refresh_semantic_pass_projection(...)`,
  `review_active_semantic_assertion(...)`,
  `review_active_semantic_assertion_category_binding(...)`,
  and the lifecycle-owned helper bodies needed to support those paths
- preserve stable imports through `app/services/semantics.py`
- add direct owner coverage in
  `tests/unit/test_semantic_pass_lifecycle.py`
- keep post-promotion orchestration in `app/services/runs.py` and bulk planning
  in `app/services/semantic_backfill.py` as callers, not as new owners

Acceptance:

- the selected lifecycle and projection-refresh family no longer has
  implementation bodies in `app/services/semantics.py` except for narrow
  forwarding seams
- `app/services/semantic_pass_lifecycle.py` closes within `<= 961` lines and
  `<= 10` private helpers
- `app/services/runs.py` and `app/services/semantic_backfill.py` do not gain
  new lifecycle implementation debt
- the new owner module does not import `app.services.semantics` directly

### Milestone 3 - Active-Pass Read Owner Extraction

Status: resolved locally
Outcome label: `reduced`

Implementation:

- add `app/services/semantic_pass_reads.py`
- move the active-pass read family into that owner module:
  `get_active_semantic_pass_row(...)`,
  `get_active_semantic_pass_detail(...)`,
  `get_active_semantic_continuity(...)`,
  detail response assembly,
  continuity payload shaping,
  fact-count lookup,
  and the read-side helper bodies required by those responses
- preserve stable imports through `app/services/semantics.py`
- add direct owner coverage in `tests/unit/test_semantic_pass_reads.py`
- keep read-side callers in `semantic_graph.py`, `semantic_generation.py`,
  `semantic_candidates.py`, `semantic_facts.py`, routes, and capabilities as
  import consumers rather than new owners

Acceptance:

- the selected row/detail/continuity family no longer has implementation
  bodies in `app/services/semantics.py` except for narrow forwarding seams
- `app/services/semantic_pass_reads.py` closes within `<= 762` lines and
  `<= 13` private helpers
- `semantic_graph.py`, `semantic_generation.py`, `semantic_candidates.py`, and
  `semantic_facts.py` do not absorb new response-shaping logic
- route and capability behavior remain stable through the existing semantics
  route family

### Milestone 4 - Registry Preview Extraction And Compatibility Reduction

Status: resolved locally
Outcome label: `resolved` for the scoped service-boundary issue and `reduced`
for the broader owner case unless the live hotspot fully retires

Implementation:

- add `app/services/semantic_registry_preview.py`
- move the preview family into that owner module:
  `preview_semantic_registry_update_for_document(...)`,
  candidate assertion and binding preview helpers,
  before or after expectation-delta helpers,
  and preview payload assembly
- preserve stable imports through `app/services/semantics.py`
- add direct owner coverage in
  `tests/unit/test_semantic_registry_preview.py`
- keep registry persistence and snapshot ownership in
  `app/services/semantic_registry.py` and keep ontology workflow ownership in
  `app/services/semantic_ontology.py`

Acceptance:

- the selected preview family no longer has implementation bodies in
  `app/services/semantics.py` except for narrow forwarding seams
- `app/services/semantic_registry_preview.py` closes within `<= 558` lines and
  `<= 5` private helpers
- `app/services/semantic_registry.py` and
  `app/services/semantic_ontology.py` do not absorb preview execution debt
- `app/services/semantics.py` closes within `<= 600` lines and
  `<= 10` private helpers
- no fourth new semantic owner file is introduced
- the scoped issue is resolved because lifecycle, projection refresh and
  review persistence, active-pass reads, and registry preview no longer cohabit
  the same file

### Milestone 5 - Closeout, Ratchets, And Residual Routing

Status: resolved locally
Outcome label: `reduced`

Implementation:

- update `config/hygiene_policy.yaml` with exact verified ceilings for the
  narrowed facade and all new owner modules
- update `config/improvement_cases.yaml` so the new semantics owner case
  records the refreshed measurements and broader owner-case state after the
  split
- refresh `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  this plan with the closeout hash, verification commands, and post-closeout
  routing
- stage only the verified semantics milestone slice and close with one local
  atomic commit

Acceptance:

- all required verification gates below pass in the same closeout window
- the scoped service-boundary issue is recorded as resolved in this plan
- the broader owner case is marked `reduced` unless live architecture evidence
  proves full retirement
- the same closeout commit contains code, tests, governance config, and docs

## Required Implementation Artifacts

- `app/services/semantic_pass_lifecycle.py`
- `app/services/semantic_pass_reads.py`
- `app/services/semantic_registry_preview.py`
- updated `app/services/semantics.py`
- updated hotspot-prevention policy and classifier
- updated direct owner-module unit tests
- updated route-boundary and integration coverage where needed
- updated improvement-case and hygiene routing
- updated architecture index and handoff

## Required Documentation And Handoff Updates

- this plan:
  `docs/semantics_service_boundary_milestone_plan.md`
- architecture index:
  `docs/agentic_architecture_index.md`
- canonical handoff:
  `docs/SESSION_HANDOFF.md`
- improvement-case registry:
  `config/improvement_cases.yaml`
- hygiene ratchets:
  `config/hygiene_policy.yaml`

Milestone 0 must also update the active-follow-up references in the handoff and
index after the evidence provenance-export milestone completes.

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/semantics.py app/services/semantic_pass_lifecycle.py app/services/semantic_pass_reads.py app/services/semantic_registry_preview.py app/services/runs.py app/services/semantic_backfill.py app/services/semantic_ontology.py app/services/agent_task_verifications.py app/services/capabilities/semantics.py app/api/routers/semantics.py app/hotspot_prevention_classifier.py tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py tests/integration/test_semantic_bootstrap_roundtrip.py tests/integration/test_semantic_candidate_roundtrip.py tests/integration/test_semantic_generation_roundtrip.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

If any verification command fails, the milestone does not close and must not be
committed as complete.

## Acceptance Criteria

- Milestone 0 refreshes the repo's live system state after the search,
  claim-support, evaluations, and evidence provenance-export packets close and
  promotes this plan to the active bounded follow-on.
- `app/services/semantics.py` gains explicit improvement-case routing and
  hotspot-prevention governance before broad refactoring begins.
- No more than three new owner modules are introduced.
- The selected lifecycle, projection refresh and review persistence, row or
  detail or continuity reads, and registry preview concerns no longer live
  together in the compatibility facade by closeout.
- `app/services/semantic_pass_lifecycle.py`,
  `app/services/semantic_pass_reads.py`, and
  `app/services/semantic_registry_preview.py` remain under the stated line and
  helper ceilings.
- `app/services/semantics.py` closes at `<= 600` lines and
  `<= 10` private helpers with only allowed forwarding or compatibility seams.
- Existing route paths, capability calls, post-promotion execution wiring,
  backfill behavior, and registry-draft verification behavior remain stable.
- The architecture probe does not increase Python cycle components above the
  refreshed Milestone 0 baseline of `5`.
- Test coverage is equivalent or stronger than before the split; no test,
  fixture, or gate is weakened to get green.
- The scoped service-boundary issue is `resolved` in this plan, while the
  broader owner case is only `reduced` unless refreshed live evidence proves
  the hotspot is retired.

## Stop Conditions

- Stop if Milestone 0 shows any of the four prior packets are not yet complete
  and committed.
- Stop if the selected concern families have already moved or the file no
  longer matches this plan's baseline shape after the prior closeouts.
- Stop if preserving route and runtime behavior requires more than three new
  owner modules.
- Stop if any new owner module cannot be kept within the stated line and
  helper ceilings.
- Stop if the split requires moving new logic into
  `semantic_graph.py`, `semantic_candidates.py`, `semantic_generation.py`,
  `semantic_governance.py`, `semantic_orchestration.py`, or
  `semantic_registry.py`.
- Stop if targeted route or integration verification fails in a way that
  implies an API, schema, storage, or persistence contract change outside this
  packet.
- Stop if the architecture probe shows the Python cycle count would rise above
  `5` or the split requires a cross-service cycle-reduction project outside
  this bounded milestone.

## Local Commit Closeout Policy

- Stage only the verified semantics milestone slice.
- Leave unrelated dirty and untracked files alone.
- Include implementation, tests, config, docs, and handoff updates in the same
  local atomic commit.
- Record the closeout commit hash in this plan and in `docs/SESSION_HANDOFF.md`.
- Treat the milestone as incomplete until that commit exists.
- Do not commit if any required verification gate fails.

## Residual Risks And Next Milestone Routing

- Most likely residual risk: one or more new semantic owner modules may still
  be oversized relative to the default budget even if the selected
  `app/services/semantics.py` knot is resolved. If so, route them as explicit
  new residual debt rather than stretching this plan.
- Another residual risk is that the broader service cycle may remain even after
  this boundary split. That does not invalidate the scoped resolution here; it
  only affects what comes next.
- After closeout, choose the next follow-on from fresh post-closeout evidence
  in `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-improvement-case-summary`, and the architecture probe.
- Do not predeclare the post-semantics target before that evidence exists.

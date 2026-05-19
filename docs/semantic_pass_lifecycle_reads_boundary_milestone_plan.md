# Semantic Pass Lifecycle And Reads Boundary Milestone Plan

Date: 2026-05-16 local / 2026-05-16 UTC
Status: resolved through the 2026-05-19 verified-to-deployed registry closeout
as the latest resolved bounded semantic-owner follow-on before
`docs/hotspot_prevention_family_boundary_milestone_plan.md`;
Milestones 0 through 5 are now resolved locally, dedicated owner-case routing
exists for `app/services/semantic_pass_lifecycle.py` and
`app/services/semantic_pass_reads.py`, `app/services/semantic_pass_lifecycle.py`
now measures `529` lines / `3` private helpers, artifact ownership now lives
in `app/services/semantic_pass_artifacts.py` at `150` lines / `0` private
helpers, review and projection ownership now lives in
`app/services/semantic_pass_reviews.py` at `369` lines / `4` private helpers,
`app/services/semantic_pass_reads.py` now measures `372` lines / `3` private
helpers, source-materialization and record-shaping ownership now lives in
`app/services/semantic_pass_source_records.py` at `415` lines / `4` private
helpers, and the broader `IC-9E6B8F5D62A1` case plus selected owner cases
`IC-8304248AB64C` and `IC-ADCFFF108626` are now durably deployed after the
later open-owner closeout and the 2026-05-19 verified-to-deployed registry
closeout. The broader
coordination brief now reselects from the routed hotspot/test queue in
`docs/boring_change_architecture_milestone_plan.md`.
Owner context: standalone residual semantic-owner packet after the semantics
service-boundary closeout reduced `app/services/semantics.py` to a narrow
compatibility facade and the later app large owner modules closeout reduced
`app/services/semantic_governance.py` to `39` lines. This packet intentionally
targets only the residual semantic pass lifecycle/read owner family and its
closeout routing, not the already-closed governance root or the separately
routed semantic graph and generation residuals.

## Purpose

Resolve the remaining semantic pass owner-family debt without reopening
semantic-governance or broadening the slice into unrelated semantic,
agent-task, or test-monolith work.

The scoped problem is no longer the facade in `app/services/semantics.py`.
That public surface is already narrow. This packet began with both
`app/services/semantic_pass_lifecycle.py` and
`app/services/semantic_pass_reads.py` above the default `600`-line budget.
The current checkout now keeps the lifecycle root at `529` lines and the
read root at `372` lines, and Milestones 4 and 5 have completed the local
closeout sweep for the selected owner family. The packet now records the
deployed state so the lifecycle/read owner cases, the broader semantic parent
case, and the active handoff or routing docs all converge on the same durable
closeout while the repo-wide cycle baseline stays at three components.

## Current Evidence

Milestone 0 baseline refreshed from the local checkout on 2026-05-15 local /
2026-05-15 UTC after the replay-alert evidence packet closed locally and
before the owner-case bootstrap updates in this slice landed:

```text
git status -sb
  ## main...origin/main [ahead 16]
   M app/services/docling_parser.py
   M app/services/evidence_audit_views.py
   M app/services/evidence_claim_support_replay_alerts.py
   M app/services/evidence_manifest_traces.py
   M app/services/evidence_manifests.py
   M app/services/evidence_semantic_trace.py
   M app/services/quality.py
   M app/services/runs.py
   M app/services/semantic_candidates.py
   M app/services/semantic_generation.py
   M app/services/semantic_governance.py
   M app/services/semantic_graph.py
   M config/hygiene_policy.yaml
   M config/improvement_cases.yaml
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
   M docs/boring_change_architecture_milestone_plan.md
   M docs/evidence_residual_owner_family_milestone_plan.md
   M tests/unit/test_evidence_audit_views.py
   M tests/unit/test_evidence_facade_contract.py
   M tests/unit/test_evidence_semantic_trace.py
  ?? docs/evidence_claim_support_replay_alerts_boundary_milestone_plan.md
  ?? docs/semantic_residual_owner_family_milestone_plan.md

wc -l app/services/semantic_pass_lifecycle.py app/services/semantic_pass_reads.py app/services/semantic_governance.py app/services/semantic_registry_preview.py
   961 app/services/semantic_pass_lifecycle.py
   762 app/services/semantic_pass_reads.py
    39 app/services/semantic_governance.py
   558 app/services/semantic_registry_preview.py

python - <<'PY'
from pathlib import Path
for path_str in [
    "app/services/semantic_pass_lifecycle.py",
    "app/services/semantic_pass_reads.py",
    "app/services/semantic_governance.py",
    "app/services/semantic_registry_preview.py",
]:
    path = Path(path_str)
    count = 0
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("def _") or stripped.startswith("async def _"):
            count += 1
    print(f"{path_str} private_helpers={count}")
PY
  app/services/semantic_pass_lifecycle.py private_helpers=10
  app/services/semantic_pass_reads.py private_helpers=13
  app/services/semantic_governance.py private_helpers=0
  app/services/semantic_registry_preview.py private_helpers=5

uv run docling-system-hygiene-check
  new hygiene regressions: none
  inherited budget debt still includes:
    app/services/semantic_generation_brief.py = 644 lines under IC-6F4E2B5A91C3
    app/services/semantic_graph_core.py = 697 lines under IC-C8D41A2F77BE
    app/services/semantic_graph_promotions.py = 718 lines under IC-C8D41A2F77BE
  semantic_pass_lifecycle.py and semantic_pass_reads.py do not yet have
  dedicated owner-case routing in the stale pre-Milestone-0 state

uv run docling-system-improvement-case-summary
  case_count=46
  status_counts.open=30
  measured_case_count=41

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=501.06

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Python cycle components: 3
  code files above 800 lines: 30
  largest remaining semantic residuals include:
    app/services/semantic_pass_lifecycle.py = 961
    app/services/semantic_pass_reads.py = 762
    app/services/semantic_orchestration.py = 1092
```

Current structural evidence:

- `app/services/semantics.py` is already a 54-line compatibility facade under
  `IC-9E6B8F5D62A1`; the live residual is the extracted lifecycle/read pair,
  not the old central facade.
- `app/services/semantic_governance.py` is now a 39-line compatibility facade,
  and its extracted governance owners all remain at or below the default
  `600`-line budget. Governance is therefore out of scope for this packet.
- `app/services/semantic_pass_lifecycle.py` still mixes semantic pass
  execution, row persistence, artifact persistence, review-overlay loading,
  registry-definition syncing, projection refresh, and review mutation flows.
- `app/services/semantic_pass_reads.py` now owns summary projection,
  continuity projection, and the public active-pass row/detail entrypoints,
  while source materialization and record shaping no longer cohabit in the
  same file.
- `app/services/semantic_pass_source_records.py` now owns semantic source
  materialization, evidence or binding record shaping, review-overlay detail
  shaping, and the public source-artifact path helper for the selected
  read-family seam.
- the fresh architecture probe still reports a three-component Python cycle
  baseline, but the live cycle components no longer include the selected
  lifecycle/read owners. This packet now remains selected on file-budget and
  owner-boundary grounds while still preserving the repo-wide cycle baseline.
- `docs/semantic_residual_owner_family_milestone_plan.md` is a stale historical
  draft that still assumes `semantic_governance.py` is a live residual and must
  not be executed unchanged

Milestone 0 closeout verification in the current checkout now reports:

- `uv run docling-system-improvement-case-summary` ->
  `case_count=48`, `status_counts.open=32`, `measured_case_count=43`
- dedicated lifecycle/read owner-case routing is now present in
  `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` under
  `IC-8304248AB64C` and `IC-ADCFFF108626`

Final local closeout baseline in the current checkout after the Milestone 5
residual semantic pass owner closeout:

```text
wc -l app/services/semantic_pass_lifecycle.py app/services/semantic_pass_artifacts.py app/services/semantic_pass_reviews.py app/services/semantic_pass_reads.py app/services/semantic_pass_source_records.py tests/unit/test_semantic_pass_reads.py
   529 app/services/semantic_pass_lifecycle.py
   150 app/services/semantic_pass_artifacts.py
   369 app/services/semantic_pass_reviews.py
   372 app/services/semantic_pass_reads.py
   415 app/services/semantic_pass_source_records.py
   146 tests/unit/test_semantic_pass_reads.py

python - <<'PY'
from pathlib import Path
for path_str in [
    "app/services/semantic_pass_lifecycle.py",
    "app/services/semantic_pass_artifacts.py",
    "app/services/semantic_pass_reviews.py",
    "app/services/semantic_pass_reads.py",
    "app/services/semantic_pass_source_records.py",
]:
    path = Path(path_str)
    count = 0
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("def _") or stripped.startswith("async def _"):
            count += 1
    print(f"{path_str} private_helpers={count}")
PY
  app/services/semantic_pass_lifecycle.py private_helpers=3
  app/services/semantic_pass_artifacts.py private_helpers=0
  app/services/semantic_pass_reviews.py private_helpers=4
  app/services/semantic_pass_reads.py private_helpers=3
  app/services/semantic_pass_source_records.py private_helpers=4

uv run ruff check app/services/semantics.py app/services/semantic_pass_lifecycle.py app/services/semantic_pass_artifacts.py app/services/semantic_pass_reviews.py app/services/semantic_pass_reads.py app/services/semantic_pass_source_records.py app/services/semantic_registry_preview.py app/services/runs.py app/services/semantic_backfill.py app/services/semantic_ontology.py app/services/agent_task_verifications.py app/services/capabilities/semantics.py app/api/routers/semantics.py app/hotspot_prevention_classifier.py tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py
  pass

uv run pytest -q tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py
  108 passed

DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_semantic_candidate_roundtrip.py tests/integration/test_semantic_generation_roundtrip.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_semantic_bootstrap_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py
  8 passed

uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=27
  changed_hotspots=0
  blocked=0

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Python cycle components: 3
  code files above 800 lines: 29
```

Milestone 4 focused closeout verification in the current checkout now reports:

- `uv run pytest -q tests/unit/test_semantic_pass_reads.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_backfill_api.py tests/unit/test_semantic_registry_preview.py`
  -> `21 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py`
  -> `2 passed`
- `uv run docling-system-hotspot-prevention-check --strict` ->
  `known_hotspots=27`, `changed_hotspots=0`, `blocked=0`
- `uv run docling-system-capability-contracts` -> `valid=true`
- `uv run docling-system-improvement-case-validate` -> `valid=true`
- `uv run docling-system-improvement-case-summary` ->
  `case_count=48`, `status_counts.open=32`, `measured_case_count=43`
- `uv run docling-system-hygiene-check` -> `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect` ->
  `valid=true`, `violation_count=0`
- `uv run docling-system-architecture-quality-report --summary` ->
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=496.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
  -> `3` Python cycle components, `29` code files above `800`
- `git diff --check` -> pass

Milestone 5 full closeout verification in the current checkout now reports:

- `uv run ruff check app/services/semantics.py app/services/semantic_pass_lifecycle.py app/services/semantic_pass_artifacts.py app/services/semantic_pass_reviews.py app/services/semantic_pass_reads.py app/services/semantic_pass_source_records.py app/services/semantic_registry_preview.py app/services/runs.py app/services/semantic_backfill.py app/services/semantic_ontology.py app/services/agent_task_verifications.py app/services/capabilities/semantics.py app/api/routers/semantics.py app/hotspot_prevention_classifier.py tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py`
  -> pass
- `uv run pytest -q tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py`
  -> `108 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_semantic_candidate_roundtrip.py tests/integration/test_semantic_generation_roundtrip.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_semantic_bootstrap_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py`
  -> `8 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
  -> `2037 passed in 74.43s (0:01:14)`
- `uv run docling-system-hotspot-prevention-check --strict` ->
  `known_hotspots=27`, `changed_hotspots=0`, `blocked=0`
- `uv run docling-system-capability-contracts` -> `valid=true`
- `uv run docling-system-improvement-case-validate` -> `valid=true`
- `uv run docling-system-improvement-case-summary` ->
  `case_count=48`, `status_counts.open=32`, `measured_case_count=43`
- `uv run docling-system-hygiene-check` -> `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect` ->
  `valid=true`, `violation_count=0`
- `uv run docling-system-architecture-quality-report --summary` ->
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=496.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
  -> `3` Python cycle components, `29` code files above `800`
- `git diff --check` -> pass

## Goal

Resolve the lifecycle and read residual semantic-owner family so that:

- `app/services/semantic_pass_lifecycle.py` and
  `app/services/semantic_pass_reads.py` each have explicit durable owner-case
  routing before further code motion
- Milestone 1 and later reductions can shrink each owner toward the default
  `600`-line budget without pushing implementation into `semantics.py`,
  `runs.py`, `semantic_backfill.py`, or other already-large siblings
- the selected owner work does not increase the repo-wide cycle baseline above
  `3`
- the current semantics route, backfill, worker, and capability contracts stay
  behavior-compatible

## Non-Goals

- No reopening of `app/services/semantic_governance.py` or its extracted
  governance siblings.
- No broad semantic cleanup of `semantic_orchestration.py`,
  `semantic_registry.py`,
  `semantic_graph.py`,
  `semantic_generation.py`, or
  `semantic_candidates.py`.
- No test-monolith cleanup.
- No weakening of semantic unit, integration, route, or backfill coverage.

## Scope

In scope:

- Milestone 0 live refresh and owner-case bootstrap for
  `semantic_pass_lifecycle.py` and `semantic_pass_reads.py`
- lifecycle-family decomposition inside `semantic_pass_lifecycle.py`
- read-family decomposition inside `semantic_pass_reads.py`
- routing, hygiene, handoff, and broader-plan updates required by the selected
  lifecycle/read owner packet

Out of scope:

- governance-family reductions already closed locally
- graph, generation, candidate, or orchestration residuals outside the
  lifecycle/read seam
- general search, documents, or runtime cycle cleanup beyond preserving the
  current baseline

## Owner Surfaces

- lifecycle family:
  `app/services/semantic_pass_lifecycle.py`,
  new focused lifecycle siblings under `app/services/semantic_pass_*.py`,
  `app/services/semantics.py`,
  `tests/unit/test_semantic_pass_lifecycle.py`
- read family:
  `app/services/semantic_pass_reads.py`,
  new focused read siblings under `app/services/semantic_pass_*.py`,
  `app/services/semantics.py`,
  `app/api/routers/semantics.py`,
  `tests/unit/test_semantic_pass_reads.py`,
  `tests/unit/test_documents_api_semantics.py`
- adjacent callers that must remain stable:
  `app/services/semantic_backfill.py`,
  `app/services/agent_task_verifications.py`,
  `app/services/capabilities/semantics.py`,
  `app/services/runs.py`,
  `app/api/routers/semantics.py`,
  `tests/unit/test_semantic_orchestration.py`,
  `tests/unit/test_semantic_backfill_api.py`,
  `tests/integration/test_semantic_backfill_roundtrip.py`,
  `tests/integration/test_postgres_roundtrip.py`
- routing and prevention:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/semantic_residual_owner_family_milestone_plan.md`,
  `docs/boring_change_architecture_milestone_plan.md`,
  this plan

## Placement Rules

- Keep `app/services/semantics.py` as the public semantics compatibility seam.
  Do not move implementation back into it.
- New lifecycle or read logic belongs in focused `app/services/semantic_pass_*`
  siblings, not in `runs.py`, `semantic_backfill.py`, `semantic_orchestration.py`,
  `semantic_registry.py`, or the already-routed graph and generation owners.
- Preserve public entrypoints imported by routes, workers, backfill, and
  capabilities. Narrowing a selected file into a forwarding facade is allowed
  only when existing callers remain stable.
- No new or touched file may exceed `800` lines at milestone closeout. Any new
  or touched owner between `601` and `800` lines must receive same-milestone
  owner-case routing and a hygiene ratchet.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Lifecycle reduction is faked by moving broad implementation into `runs.py`, `semantic_backfill.py`, or `semantics.py` instead of splitting the owner cleanly. | `semantic_pass_lifecycle.py`, adjacent semantic callers, staged diff | `uv run docling-system-hygiene-check`, staged `wc -l`, focused lifecycle tests | Any touched adjacent caller grows with moved lifecycle implementation or the lifecycle owner remains above its routed ceiling without explicit residual routing | Temporarily move projection-refresh helpers into `runs.py` or the facade and confirm closeout review rejects the slice | A future session sees runtime-adjacent helpers and treats `runs.py` as the easiest overflow bucket |
| Read-side work only renames helpers without separating source materialization from active-pass detail or continuity projections. | `semantic_pass_reads.py`, new read owners, read tests | `uv run pytest -q tests/unit/test_semantic_pass_reads.py tests/unit/test_documents_api_semantics.py`, file-shape review | Public entrypoints stay in the same broad owner while the internal concern families remain cohabiting | Leave continuity and detail materialization together in the same file and confirm milestone acceptance fails | Future Codex performs a cosmetic shuffle and claims the file is modular because the names changed |
| The new packet lands code changes without durable owner-case routing for both residual owners. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, this plan, handoff | `uv run docling-system-improvement-case-validate`, `uv run docling-system-improvement-case-summary` | `semantic_pass_lifecycle.py` or `semantic_pass_reads.py` is touched without a durable case entry | Create a temporary routed slice with changed lifecycle code but no case entry and confirm validation or closeout review blocks it | Future Codex treats extracted owner files as already owned because they came from a closed facade plan |
| The packet reopens governance or graph-generation debt because the residual semantic draft was not narrowed honestly. | this plan, `docs/semantic_residual_owner_family_milestone_plan.md`, staged diff | docs alignment review, architecture probe, owner-case review | `semantic_governance.py`, `semantic_graph_core.py`, or `semantic_generation_brief.py` enters scope without fresh evidence | Intentionally add governance extraction text back into this packet and confirm closeout review rejects it | A future session revives the stale draft wholesale instead of using the live lifecycle/read scope |

Accepted residual after closeout:

- If either selected owner closes between `601` and `800` lines, that is
  accepted only with explicit same-milestone routed residual ownership,
  hygiene ratchet coverage, and an outcome label of `reduced`.
- If the repo-wide cycle count remains at `3`, that is accepted only when the
  selected owners close without increasing the cycle count and the remaining
  cycle cleanup is explicitly routed as separate work.

## Milestone Sequence

### Milestone 0 - Live Refresh And Owner-Case Bootstrap

Status: resolved locally in the current checkout
Outcome label: reduced

- Refresh `git status -sb`, selected `wc -l`, `uv run
  docling-system-hygiene-check`, `uv run
  docling-system-improvement-case-summary`, `uv run
  docling-system-architecture-quality-report --summary`, and the architecture
  probe.
- Create dedicated improvement cases for
  `app/services/semantic_pass_lifecycle.py` and
  `app/services/semantic_pass_reads.py`.
- Transition the already-shrunk compatibility roots
  `IC-9E6B8F5D62A1` and `IC-81C531769EB3` to their honest locally deployed
  state so the lifecycle/read pair becomes the only live semantic residual
  route.
- Update hygiene ownership, handoff, architecture index, and broader routing so
  this packet becomes the active bounded brief and the older
  semantic residual draft is explicitly superseded.

Acceptance:

- both selected owners have explicit durable routing before code moves
- `IC-9E6B8F5D62A1` and `IC-81C531769EB3` no longer pretend that the facade or
  governance root is still the active residual blocker
- this plan, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`,
  and `docs/boring_change_architecture_milestone_plan.md` reflect the same live
  baseline and next bounded packet
- no production code changed outside routing and docs

### Milestone 1 - Semantic Pass Lifecycle Execution And Projection Boundary

Status: resolved locally in the current checkout
Outcome label: reduced

- Split semantic pass execution, persistence, and projection-refresh ownership
  from review-mutation and registry-definition syncing inside
  `semantic_pass_lifecycle.py`.
- Preserve public lifecycle entrypoints used through `app/services/semantics.py`
  and current callers.

Acceptance:

- `app/services/semantic_pass_lifecycle.py` is materially reduced from the
  Milestone 0 baseline to `664` lines / `5` private helpers
- review-overlay, projection-refresh, and review-mutation ownership now lives
  in `app/services/semantic_pass_reviews.py` at `369` lines / `4` private
  helpers, and no touched adjacent semantic owner absorbs lifecycle
  implementation
- `tests/unit/test_semantic_pass_lifecycle.py` passes and the broader semantic
  unit and integration verification slices remain green
- if the owner remains above `600`, the residual is explicitly routed to
  Milestone 2

### Milestone 2 - Semantic Pass Lifecycle Closeout

Status: resolved locally in the current checkout
Outcome label: resolved

- Extract remaining artifact payload, review-mutation, and projection-owner
  logic needed to bring `semantic_pass_lifecycle.py` within the final budget.
- Preserve current review endpoints and artifact expectations.

Acceptance:

- `app/services/semantic_pass_lifecycle.py` now measures `529` lines /
  `3` private helpers
- semantic artifact payload and persistence ownership now lives in
  `app/services/semantic_pass_artifacts.py` at `150` lines / `0` private
  helpers, and no new lifecycle-family owner exceeds `800` lines
- focused lifecycle and route semantics coverage stays green

### Milestone 3 - Semantic Pass Reads Materialization Boundary

Status: resolved locally in the current checkout
Outcome label: reduced

- Split source-materialization and record-shaping ownership from row/detail and
  continuity response assembly inside `semantic_pass_reads.py`.
- Preserve the existing public active-pass row/detail and continuity
  entrypoints.

Acceptance:

- `app/services/semantic_pass_reads.py` is reduced from the Milestone 0
  baseline to `372` lines / `3` private helpers
- source-materialization and record-shaping ownership now lives in
  `app/services/semantic_pass_source_records.py` at `415` lines / `4` private
  helpers, and no new read-family owner exceeds `800` lines
- `tests/unit/test_semantic_pass_reads.py` and
  `tests/unit/test_documents_api_semantics.py` pass, with the broader
  semantic unit and integration slices still green at `108 passed` and
  `8 passed`

### Milestone 4 - Semantic Pass Read Closeout And Retirement Sweep

Status: resolved locally in the current checkout
Outcome label: resolved

- Refresh the read-family closeout baseline now that Milestone 3 already
  reduced `semantic_pass_reads.py` below the default budget.
- Confirm the new source-record owner stays bounded, update routing and
  retirement state honestly, and preserve route and backfill compatibility
  through the semantics facade.

Acceptance:

- `app/services/semantic_pass_reads.py` still measures `<= 600` lines on a
  fresh closeout baseline
- `app/services/semantic_pass_source_records.py` remains `<= 800` lines and is
  ratcheted in hygiene state
- no new read-family owner exceeds `800` lines
- focused reads, route, and backfill coverage remain green
- `IC-ADCFFF108626` and the broader semantic compatibility routing are ready
  for retirement pending an atomic closeout commit

### Milestone 5 - Residual Semantic Pass Owner Closeout

Status: resolved locally in the current checkout
Outcome label: resolved

- Re-run the full selected verification stack and refresh line-count, routing,
  hygiene, and architecture evidence.
- Update this plan with actual closeout status, outcome labels, and any
  accepted routed residuals.
- Update the handoff and architecture index with the active next routing and
  any milestone commit hashes.

Acceptance:

- both selected owners measure `<= 600` lines on a fresh closeout baseline
- both selected owners keep durable improvement-case routing and hygiene-owner
  coverage
- the architecture probe does not report more than the Milestone 0 cycle
  baseline of `3`
- the final full DB-backed integration suite passes

## Required Implementation Artifacts

- focused lifecycle and read owner modules under `app/services/`
- `app/services/semantic_pass_artifacts.py` as the lifecycle artifact owner
- `app/services/semantic_pass_reviews.py` as the new lifecycle review and
  projection owner
- `app/services/semantic_pass_source_records.py` as the read source and record
  shaping owner
- improvement-case entries for `semantic_pass_lifecycle.py` and
  `semantic_pass_reads.py`
- refreshed locally deployed routing for `IC-9E6B8F5D62A1` and
  `IC-81C531769EB3`
- updated hygiene ownership for the selected residual owners and any accepted
  new `601-800` owner modules

## Required Documentation And Handoff Updates

- update this plan with actual milestone status, evidence, and residual routing
- update `docs/SESSION_HANDOFF.md` with the active semantic pass lifecycle/read
  milestone, verification commands, and next routing
- update `docs/agentic_architecture_index.md` so the current drafted brief
  points to this lifecycle/read packet instead of the stale semantic residual
  draft or the already-resolved replay-alert packet
- mark `docs/semantic_residual_owner_family_milestone_plan.md` as superseded by
  this standalone packet

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/semantics.py app/services/semantic_pass_lifecycle.py app/services/semantic_pass_artifacts.py app/services/semantic_pass_reviews.py app/services/semantic_pass_reads.py app/services/semantic_pass_source_records.py app/services/semantic_registry_preview.py app/services/runs.py app/services/semantic_backfill.py app/services/semantic_ontology.py app/services/agent_task_verifications.py app/services/capabilities/semantics.py app/api/routers/semantics.py app/hotspot_prevention_classifier.py tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py`
- `uv run pytest -q tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_semantic_candidate_roundtrip.py tests/integration/test_semantic_generation_roundtrip.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_semantic_bootstrap_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-architecture-inspect`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- `app/services/semantic_pass_lifecycle.py` and
  `app/services/semantic_pass_reads.py` each have explicit dedicated routing
  before Milestone 1 code motion
- no selected-family implementation debt is hidden in
  `semantics.py`,
  `runs.py`,
  `semantic_backfill.py`,
  `semantic_orchestration.py`,
  or `semantic_registry.py`
- no new owner module in the selected families exceeds `800` lines
- any newly created owner module between `601` and `800` lines is explicitly
  routed and ratcheted in the same milestone
- focused unit and integration slices pass without weakened coverage

## Stop Conditions

- Milestone 0 shows the selected lifecycle/read owner set is no longer the live
  next semantic debt surface
- reducing a selected owner would require pushing implementation into another
  already-large semantic sibling
- the only available prevention move is to grow
  `app/hotspot_prevention_classifier.py` beyond its current ceiling without a
  same-milestone extraction
- route, backfill, or lifecycle verification fails because of unrelated system
  breakage that prevents trustworthy milestone proof
- user-owned edits appear in the same selected files and cannot be cleanly
  separated from the milestone slice

## Local Commit Closeout Policy

- Close each milestone with a local atomic commit after verification passes.
- Stage only the verified milestone slice.
- Leave unrelated dirty or untracked files alone unless the user explicitly
  asks to clean or commit them.
- Include code, tests, config updates, docs, and handoff changes for that
  milestone in the same commit.
- Treat a verified but uncommitted milestone as ready-to-close, not complete.

## Residual Risks And Next Routing

- This plan resolves only the extracted lifecycle/read semantic owner family.
  Broader semantic backlog such as `semantic_orchestration.py`,
  `semantic_generation_brief.py`, `semantic_graph_core.py`, and
  `semantic_graph_promotions.py` remains outside this packet unless the user
  later selects it explicitly.
- If the selected owners close without reducing the repo-wide cycle count below
  `3`, route cycle-only cleanup through a fresh standalone packet instead of
  broadening this one after the fact.
- After this packet closes, the next semantic or app-side hotspot should be
  chosen from fresh live evidence rather than by reviving the older broader
  owner lists unchanged.

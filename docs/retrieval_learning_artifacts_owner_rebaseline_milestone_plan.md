# Retrieval Learning Artifacts Owner Rebaseline Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: deployed locally on 2026-05-19 after Milestones 0 through 3 completed.
The root now closes at `129 / 0` over
`app/services/retrieval_learning_artifact_contracts.py` at `20 / 0`,
`app/services/retrieval_learning_artifact_weights.py` at `181 / 4`,
`app/services/retrieval_learning_artifact_impacts.py` at `228 / 2`,
`app/services/retrieval_learning_artifact_governance.py` at `59 / 0`,
`app/services/retrieval_learning_artifact_lifecycle.py` at `232 / 0`, and
`app/services/retrieval_learning_artifact_views.py` at `122 / 0`, with
`IC-5F4E8C2B1A90` recorded as the deployed owner case. The packet now closes as
its own atomic milestone and returns the live routed queue to
`top_routed_hotspot_paths=[]`.
Owner context: fresh broader rebaseline after
`docs/semantic_registry_owner_rebaseline_milestone_plan.md` reduced
`app/services/semantic_registry.py` to a deployed local compatibility facade
and kept the routed queue empty without reopening the unrelated
classifier-family closeout.

## Purpose

Resolve the next real retrieval-learning owner boundary without pretending the
empty routed queue means the remaining debt is only in tests.

At the live 2026-05-19 rebaseline:

- `tests/unit/test_search_replays.py` (`776`) and
  `tests/unit/test_search_api_harnesses.py` (`764`) are larger, but they are
  verification roots
- `app/services/retrieval_learning_artifacts.py` is the strongest remaining
  app-side owner surface at `774` lines with `16` defs/classes and `7` private
  helpers
- the root still mixes request translation, feature-weight proposal synthesis,
  trace and claim-impact analysis, semantic-governance event materialization,
  response serialization, durable row writes, and list/detail reads
- the file sits under only a broad `774 / 7` hygiene ceiling through the older
  family case `IC-0D58F1624037`, not a dedicated owner case for the current
  surface

This packet exists to route that mixed retrieval-learning artifact owner into
focused family-local modules while preserving the completed
`app/services/retrieval_learning.py` compatibility facade and keeping the
now-deployed semantic-registry packet as a separate closeout.

## Local Closeout Update

- Milestones 0 through 3 are now deployed locally. The retrieval-learning
  artifact split landed entirely inside the new
  `retrieval_learning_artifact_*` family, the root is now a narrow facade at
  `129 / 0`, and the live routed queue remains `top_routed_hotspot_paths=[]`.
- Verification now includes the focused retrieval-learning, API, CLI, and
  hotspot-policy unit slice at `62 passed`, the focused DB-backed integration
  slice at `4 passed`, `uv run docling-system-hotspot-prevention-check --strict`
  at `blocked=0` with `exceptions=0`, `uv run docling-system-hygiene-check`
  with no inherited debt or regressions, and
  `uv run docling-system-improvement-case-summary` at
  `status_counts={"measured":1,"deployed":64}`, plus the full
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` gate at
  `2149 passed`.
- Debt-shift audit: `git diff --stat` over `app/services/retrieval_learning.py`,
  `app/services/retrieval_learning_candidates.py`,
  `app/services/capabilities/retrieval_learning_contract.py`,
  `app/services/capabilities/retrieval_services.py`,
  `app/api/routers/search.py`, `app/api/routers/search_learning.py`,
  `app/cli.py`, `app/cli_commands/search_harness.py`, and
  `tests/integration/retrieval_learning_ledger_support.py` remained empty
  after the split, so the packet did not transfer reranker-artifact debt into
  adjacent retrieval-learning consumers or support modules.

## Current Evidence

Live baseline from the 2026-05-19 checkout when this packet was drafted:

```text
git status -sb
  ## main...origin/main [ahead 3]
   M README.md
   M app/hotspot_prevention_classifier.py
   M app/services/semantic_registry.py
   M config/hotspot_prevention.yaml
   M config/hygiene_policy.yaml
   M config/improvement_cases.yaml
   M docs/SESSION_HANDOFF.md
   M docs/agent_task_runtime_and_verification_boundary_milestone_plan.md
   M docs/agentic_architecture_index.md
   M docs/boring_change_architecture_milestone_plan.md
   M docs/hotspot_prevention_classifier_owner_rebaseline_milestone_plan.md
   M tests/unit/test_hotspot_prevention_family_rules.py
   M tests/unit/test_hotspot_prevention_policy_contracts.py
   M tests/unit/test_semantic_registry.py
  ?? app/hotspot_prevention_classifier_owner_rules.py
  ?? app/services/semantic_registry_contracts.py
  ?? app/services/semantic_registry_state.py
  ?? app/services/semantic_registry_storage.py
  ?? docs/semantic_registry_owner_rebaseline_milestone_plan.md

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=20
  legibility_gap_count=0
  stale_facade_hotspot_count=20
  max_hotspot_risk_score=471.06
  top_routed_hotspot_paths=[]

uv run docling-system-improvement-case-summary
  case_count=64
  status_counts={"measured":1,"deployed":62,"verified":1}
  actionable_buckets.open_unconverted_count=0
  actionable_buckets.converted_unverified_count=0
  actionable_buckets.verified_undeployed_count=1

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Largest files include:
    tests/unit/test_search_replays.py = 776
    app/services/retrieval_learning_artifacts.py = 774
    tests/unit/test_search_api_harnesses.py = 764
    tests/unit/agent_task_actions_support.py = 741
    app/services/ingest_batches.py = 692
  Hotspots still include:
    tests/integration/test_retrieval_learning_ledger.py = 428 lines, score 8560
    app/services/search.py = 231 lines, score 7854
  Python cycles: none detected

wc -l app/services/retrieval_learning_artifacts.py \
  app/services/retrieval_learning_candidates.py \
  app/services/retrieval_learning.py \
  app/db/model_domains/retrieval_learning_artifacts.py \
  tests/unit/test_retrieval_learning_artifacts.py
     774 app/services/retrieval_learning_artifacts.py
     412 app/services/retrieval_learning_candidates.py
     143 app/services/retrieval_learning.py
     482 app/db/model_domains/retrieval_learning_artifacts.py
     100 tests/unit/test_retrieval_learning_artifacts.py

python - <<'PY'
from pathlib import Path
for path_str in [
    "app/services/retrieval_learning_artifacts.py",
    "app/services/retrieval_learning_candidates.py",
    "app/services/retrieval_learning.py",
    "app/db/model_domains/retrieval_learning_artifacts.py",
    "tests/unit/test_retrieval_learning_artifacts.py",
]:
    text = Path(path_str).read_text().splitlines()
    defs = sum(
        1
        for line in text
        if line.startswith("def ")
        or line.startswith("async def ")
        or line.startswith("class ")
    )
    priv = sum(
        1
        for line in text
        if line.startswith("def _") or line.startswith("async def _")
    )
    print(f"{path_str} defs_or_classes={defs} private_helpers={priv}")
PY
  app/services/retrieval_learning_artifacts.py defs_or_classes=16 private_helpers=7
  app/services/retrieval_learning_candidates.py defs_or_classes=12 private_helpers=1
  app/services/retrieval_learning.py defs_or_classes=7 private_helpers=0
  app/db/model_domains/retrieval_learning_artifacts.py defs_or_classes=3 private_helpers=0
  tests/unit/test_retrieval_learning_artifacts.py defs_or_classes=2 private_helpers=0

config/hygiene_policy.yaml
  app/services/retrieval_learning_artifacts.py:
    max_lines: 774
    max_private_helpers: 7
    owner_case_id: IC-0D58F1624037
```

Structural and contract evidence:

- `app/services/retrieval_learning_artifacts.py` currently contains:
  - `feature_weight_candidate(...)` plus training-payload helper logic
  - `change_impact_report(...)` plus trace-owner and claim-derivation lookup
  - semantic-governance event materialization
  - response serialization for summary and detail payloads
  - `create_retrieval_reranker_artifact(...)`, `list_*`, and `get_*`
- `tests/unit/test_retrieval_learning_artifacts.py` is only `100` lines and
  currently covers feature-weight heuristics and request translation, while the
  heavier behavior is spread across:
  - `tests/unit/test_retrieval_learning_facade_contract.py`
  - `tests/unit/test_search_api_harnesses.py`
  - `tests/unit/test_search_api_learning_audit.py`
  - `tests/unit/test_cli_search_harness.py`
  - `tests/integration/test_retrieval_learning_ledger_candidates.py`
  - `tests/integration/test_search_harness_releases.py`
- the public `app/services/retrieval_learning.py` facade is already narrow at
  `143 / 0` and has exact contract coverage. The next split must not regrow
  that facade or move service logic into routers, CLI commands, or capability
  adapters.
- `app/db/model_domains/retrieval_learning_artifacts.py` is already a separate
  `482` line ORM owner. This packet is service-boundary work, not DB-model or
  migration work.
- this packet was drafted while the checkout was not clean and while the
  semantic-registry packet was still waiting to land. The next
  retrieval-learning milestone therefore still requires explicit Milestone 0
  worktree isolation before any code-owning split begins.

## Goal

Resolve the retrieval-learning artifact owner boundary so that:

- `app/services/retrieval_learning_artifacts.py` becomes a narrow public facade
  or coordination surface at `max_lines <= 260` and
  `max_private_helpers <= 4`
- feature-weight proposal synthesis, change-impact and trace analysis,
  lifecycle writes, and detail/list read assembly no longer cohabit the same
  file
- `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, and
  `config/hotspot_prevention.yaml` gain explicit current-state governance for
  the retrieval-learning artifact family rather than leaving the root under the
  older broad shared family case alone
- `app/services/retrieval_learning.py`, capability adapters, API routes, CLI
  entrypoints, and search-learning error contracts remain behavior-stable
- the packet closes without shifting debt into
  `app/services/retrieval_learning_candidates.py`,
  `app/services/retrieval_learning.py`,
  `app/services/audit_bundle_release_payload_serialization.py`,
  `app/services/audit_bundle_release_payloads.py`,
  `app/api/routers/search.py`, `app/api/routers/search_learning.py`, or
  `tests/integration/retrieval_learning_ledger_support.py`

## Non-Goals

- No reopening of `app/services/retrieval_learning.py` as the primary owner.
- No DB model, Alembic, or schema-contract redesign.
- No move of retrieval-learning service logic into routers, CLI commands,
  capability adapters, or integration support modules.
- No rewrite of search-harness evaluation or release-gate behavior beyond the
  seam work required to preserve current contracts.
- No weakening of API, CLI, facade-contract, or DB-backed integration
  coverage to get a passing result.
- No bundling of the now-deployed semantic-registry closeout or unrelated
  follow-on work into the retrieval-learning milestone commit.

## Scope

In scope:

- `app/services/retrieval_learning_artifacts.py`
- new `app/services/retrieval_learning_artifact_*.py` family-local owners
- `app/services/retrieval_learning.py` only for compatibility imports or
  delegation seams
- `app/services/capabilities/retrieval_learning_contract.py`
- `app/services/capabilities/retrieval_services.py`
- `app/api/routers/search.py`
- `app/api/routers/search_learning.py`
- `app/cli.py`
- `app/cli_commands/search_harness.py`
- `tests/unit/test_retrieval_learning_artifacts.py`
- `tests/unit/test_retrieval_learning_artifact_weights.py`
- `tests/unit/test_retrieval_learning_artifact_views.py`
- `tests/unit/test_retrieval_learning_facade_contract.py`
- `tests/unit/test_search_api_harnesses.py`
- `tests/unit/test_search_api_learning_audit.py`
- `tests/unit/test_cli_search_harness.py`
- `tests/unit/test_hotspot_prevention_policy_contracts.py`
- `tests/integration/test_retrieval_learning_ledger_candidates.py`
- `tests/integration/test_search_harness_releases.py`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `config/hotspot_prevention.yaml`
- current-state docs and handoff

Out of scope:

- `tests/unit/test_search_replays.py`
- `tests/unit/test_search_api_harnesses.py` beyond assertions directly needed
  for reranker-artifact contracts
- `app/services/ingest_batches.py`
- `app/services/search_harnesses.py` except for direct seam adjustments proven
  necessary by the extraction
- any new packet for the residual test roots or ingest family

## Owner Surfaces

Primary owner surfaces:

- `app/services/retrieval_learning_artifacts.py`
- the final family-local successor modules created under
  `app/services/retrieval_learning_artifact_*.py`
- the dedicated improvement case and hygiene budgets for that family

Compatibility and consumer surfaces that must remain stable:

- `app/services/retrieval_learning.py`
- `app/services/capabilities/retrieval_learning_contract.py`
- `app/services/capabilities/retrieval_services.py`
- `app/api/routers/search.py`
- `app/api/routers/search_learning.py`
- `app/cli.py`
- `app/cli_commands/search_harness.py`

Adjacent surfaces that must not silently absorb the debt:

- `app/services/retrieval_learning_candidates.py`
- `app/services/audit_bundle_release_payload_serialization.py`
- `app/services/audit_bundle_release_payloads.py`
- `tests/integration/retrieval_learning_ledger_support.py`
- `app/db/model_domains/retrieval_learning_artifacts.py`

## Placement Rules

- Keep the public compatibility surface in `app/services/retrieval_learning.py`
  exact. New logic belongs in `app/services/retrieval_learning_artifact_*.py`,
  not back in the facade.
- Keep API routes and CLI entrypoints thin. Do not move owner logic into
  `app/api/routers/search.py`, `app/api/routers/search_learning.py`,
  `app/cli.py`, or `app/cli_commands/search_harness.py`.
- Keep DB ownership in `app/db/model_domains/retrieval_learning_artifacts.py`.
  Service-boundary code must not migrate into model properties or ORM helpers.
- Keep family-local helper code close to the owner modules. If a support module
  is required, it must stay under the same `retrieval_learning_artifact_*`
  family and carry its own ratchet; do not create a broad `retrieval_learning`
  utility sink.
- If a split changes consumer imports, redirect those imports through focused
  owner modules or the existing compatibility facade rather than broadening
  cross-family coupling.
- Preserve machine-readable error behavior for reranker-artifact detail routes.

## Weak-Point Prevention Contract

### Milestone 0

- Weak point forecast: a new retrieval-learning packet starts on top of the
  still-dirty semantic-registry and classifier-family slices, so later commits
  cannot be atomic or reviewable.
- Owner surface: current worktree state plus `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and this packet.
- Prevention gate: fresh `git status -sb`, live architecture summary refresh,
  and a milestone-local rule that no code-owning retrieval-learning commit may
  start until the semantic-registry verified slice is either committed or
  explicitly parked outside the retrieval-learning diff.
- Fail threshold: the retrieval-learning implementation diff still includes
  unrelated semantic-registry or classifier-family edits when Milestone 1
  begins.
- Controlled violation: a dry-run staging review must show that the retrieval
  milestone can be staged without `app/services/semantic_registry*.py`,
  `app/hotspot_prevention_classifier*.py`, or unrelated policy tests.
- Future-Codex misuse scenario: a future session sees `top_routed_hotspot_paths=[]`
  and starts editing the biggest app file directly without isolating the live
  dirty slice; Milestone 0 prevents that by making worktree isolation an
  explicit baseline gate.

### Milestone 1

- Weak point forecast: feature-weight and request-translation extraction causes
  root regrowth in `app/services/retrieval_learning.py` or spreads heuristics
  into CLI or API layers.
- Owner surface: `app/services/retrieval_learning_artifacts.py`,
  `app/services/retrieval_learning.py`, and the new feature-weight owner.
- Prevention gate: facade-contract tests, CLI contract tests, and exact
  ratchets on `app/services/retrieval_learning.py`.
- Fail threshold: the public facade grows above `143 / 0`, new artifact logic
  lands in routers or CLI modules, or the root still owns feature-weight logic
  after Milestone 1.
- Controlled violation: focused unit tests must fail if the facade stops
  delegating `create_retrieval_reranker_artifact(...)` through the runtime
  seams.
- Future-Codex misuse scenario: a future session adds another reranker tweak to
  the facade because it is the obvious public import surface; Milestone 1
  prevents that by establishing a family-local artifact owner for that logic.

### Milestone 2

- Weak point forecast: change-impact and trace-owner logic migrates into audit
  bundle serializers, integration support, or model-domain code because those
  surfaces already touch the same payloads.
- Owner surface: the new impact/governance owner, adjacent audit bundle
  serializers, and integration support.
- Prevention gate: targeted DB-backed integration coverage for reranker
  artifact change impact, plus a debt-shift diff review over the adjacent
  audit, support, and model-domain files.
- Fail threshold: change-impact behavior moves into adjacent owners or the root
  still cohosts impact assembly plus semantic-governance event materialization
  after Milestone 2.
- Controlled violation: integration coverage must fail if affected-claim or
  derivation impact reporting stops materializing or if the route returns a
  non-machine-readable failure.
- Future-Codex misuse scenario: a future session adds trace or provenance logic
  to an audit bundle serializer because it already emits the artifact payload;
  Milestone 2 prevents that by making the change-impact owner explicit and
  verified.

### Milestone 3

- Weak point forecast: final lifecycle and read/write extraction leaves the
  root smaller but creates one new oversized sibling or hides logic inside a
  broad support module.
- Owner surface: final `retrieval_learning_artifact_*` family, hygiene policy,
  hotspot prevention, and improvement-case routing.
- Prevention gate: exact line/helper ratchets, hotspot-prevention strict check,
  architecture quality summary, and a no-debt-shift review over adjacent
  retrieval-learning files.
- Fail threshold: `app/services/retrieval_learning_artifacts.py` stays above
  `260 / 4`, any new family-local owner exceeds `360 / 6` without its own
  follow-on routing, or the live docs still say no follow-on exists after the
  packet is chosen.
- Controlled violation: hotspot-prevention and hygiene tests must fail if the
  root or a new sibling regrows past its exact ratchet.
- Future-Codex misuse scenario: a future session treats the reduced root as a
  convenient mixed owner again because the configs only carry broad ceilings;
  Milestone 3 prevents that by landing dedicated owner-case routing and exact
  ratchets for the final family shape.

## Milestone Sequence

### Milestone 0: Rebaseline, Isolate, And Bootstrap The Owner Gate

Outcome label: reduced.

- Refresh the live baseline with `git status -sb`,
  `uv run docling-system-improvement-case-summary`,
  `uv run docling-system-architecture-quality-report --summary`, and the
  architecture probe before touching code.
- Start from a fresh isolated Milestone 0 worktree so the retrieval-learning
  implementation can land as an atomic commit.
- Create a dedicated improvement-case entry for
  `app/services/retrieval_learning_artifacts.py` instead of leaving the file
  governed only through the older shared family case.
- Add or extend structure gates before large edits:
  - preserve the exact `app/services/retrieval_learning.py` facade contract
  - preserve machine-readable API error behavior
  - preserve CLI output contract for artifact creation
  - add family-local structure tests or route assertions if current coverage is
    too indirect to catch owner regrowth
- Record this packet as the queued broader-reselect follow-on in the handoff,
  index, and broader architecture brief while `top_routed_hotspot_paths`
  remains honestly empty.

### Milestone 1: Extract Feature-Weight And Artifact-Proposal Ownership

Outcome label: reduced.

- Move request translation, training-payload row helpers, feature-weight
  synthesis, and harness override proposal assembly into a focused family-local
  owner such as `app/services/retrieval_learning_artifact_weights.py`.
- Keep `app/services/retrieval_learning_artifacts.py` delegating to that owner
  rather than retaining duplicate logic.
- Expand focused unit coverage so feature-weight and request-translation
  behavior is owned by dedicated tests, not only by the current small root test
  plus broad integration coverage.
- Preserve `app/services/retrieval_learning.py` as the public import surface
  and keep CLI or router seams unchanged.

### Milestone 2: Extract Change-Impact And Governance Ownership

Outcome label: reduced.

- Move training reference collection, trace-owner queries, affected-claim and
  derivation assembly, and semantic-governance event materialization into one
  or two focused family-local owners such as
  `app/services/retrieval_learning_artifact_impacts.py` and
  `app/services/retrieval_learning_artifact_governance.py`.
- Keep audit bundle release serializers and integration support modules as
  consumers only; do not let them become the new implementation sink.
- Add focused DB-backed integration coverage that proves reranker artifacts
  still record change-impact payloads, semantic-governance links, and release
  context correctly after the extraction.

### Milestone 3: Extract Lifecycle And Read Assembly, Then Close Out

Outcome label: resolved.

- Move response serialization plus list/detail reads and durable artifact-write
  orchestration into focused family-local owners such as
  `app/services/retrieval_learning_artifact_views.py` and
  `app/services/retrieval_learning_artifact_lifecycle.py`.
- Reduce `app/services/retrieval_learning_artifacts.py` to a narrow public
  facade or coordination surface at `<= 260` lines and `<= 4` private helpers.
- Land exact hygiene ratchets and hotspot-prevention routing for the final
  family shape, including the dedicated owner case and any accepted residual
  boundary that remains intentionally broad.
- Run the full DB-backed verification stack, refresh handoff and architecture
  docs, and close the packet with an atomic milestone commit containing only
  the retrieval-learning artifact family slice.

## Required Implementation Artifacts

- This plan file
- one dedicated improvement-case entry for
  `app/services/retrieval_learning_artifacts.py`
- exact hygiene budgets for the final root and successor owner modules
- focused family-local owner modules under
  `app/services/retrieval_learning_artifact_*.py`
- focused unit and integration coverage proving the extracted seams
- refreshed handoff and architecture-index routing that names this packet while
  the routed queue remains empty

## Required Documentation And Handoff Updates

- `docs/retrieval_learning_artifacts_owner_rebaseline_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `config/hotspot_prevention.yaml`
- `README.md` only if the current-state summary or recommended next packet
  changes as part of the milestone closeout

## Required Verification Gates

Milestone 0 baseline and docs gate:

```text
git diff --check
uv run docling-system-improvement-case-summary
uv run docling-system-architecture-quality-report --summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
```

Focused implementation gates:

```text
uv run ruff check app/services/retrieval_learning.py \
  app/services/retrieval_learning_artifacts.py \
  app/services/capabilities/retrieval_learning_contract.py \
  app/services/capabilities/retrieval_services.py \
  app/api/routers/search.py \
  app/api/routers/search_learning.py \
  app/cli.py \
  app/cli_commands/search_harness.py \
  tests/unit/test_retrieval_learning_artifacts.py \
  tests/unit/test_retrieval_learning_artifact_weights.py \
  tests/unit/test_retrieval_learning_artifact_views.py \
  tests/unit/test_retrieval_learning_facade_contract.py \
  tests/unit/test_search_api_harnesses.py \
  tests/unit/test_search_api_learning_audit.py \
  tests/unit/test_cli_search_harness.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py \
  tests/integration/test_retrieval_learning_ledger_candidates.py \
  tests/integration/test_search_harness_releases.py

uv run pytest -q tests/unit/test_retrieval_learning_artifacts.py \
  tests/unit/test_retrieval_learning_artifact_weights.py \
  tests/unit/test_retrieval_learning_artifact_views.py \
  tests/unit/test_retrieval_learning_facade_contract.py \
  tests/unit/test_search_api_harnesses.py \
  tests/unit/test_search_api_learning_audit.py \
  tests/unit/test_cli_search_harness.py \
  tests/unit/test_hotspot_prevention_policy_contracts.py

DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q \
  tests/integration/test_retrieval_learning_ledger_candidates.py \
  tests/integration/test_search_harness_releases.py

uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-hygiene-check
uv run docling-system-improvement-case-validate
uv run docling-system-improvement-case-summary
uv run docling-system-architecture-quality-report --summary
uv run docling-system-architecture-inspect
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py \
  --fail-on-cycles --max-file-lines 800
```

Final closeout gate:

```text
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
git diff --check
```

## Acceptance Criteria

- The retrieval-learning artifact implementation begins only after the
  semantic-registry verified slice is either committed or explicitly isolated
  from the retrieval-learning diff.
- `app/services/retrieval_learning_artifacts.py` closes at `<= 260` lines and
  `<= 4` private helpers.
- Every extracted owner module stays at `<= 360` lines and `<= 6` private
  helpers unless the milestone explicitly creates a separate accepted residual
  routing record for it.
- `app/services/retrieval_learning.py` remains at `<= 143` lines and `0`
  private helpers with the exact facade contract preserved.
- API error-path coverage for reranker-artifact detail routes remains
  machine-readable.
- CLI artifact-creation output remains behavior-stable.
- The focused unit and integration suites above pass without deleting or
  loosening existing assertions.
- `uv run docling-system-hotspot-prevention-check --strict` stays green with
  no new blocked hotspot growth.
- `uv run docling-system-hygiene-check` reports no new regressions and no
  inherited budget debt from this packet.
- `uv run docling-system-improvement-case-validate` stays `valid=true`.
- `uv run docling-system-architecture-inspect` stays `valid=true` with
  `violation_count=0`.
- The architecture probe still reports no Python cycles.
- The handoff, index, and broader architecture brief all point to this packet
  while the routed queue remains honestly empty.
- The final milestone commit stages only the retrieval-learning artifact code,
  tests, configs, and docs required by this packet.

## Stop Conditions

- Stop if the semantic-registry verified slice cannot be isolated cleanly from
  the retrieval-learning implementation. Close that packet first instead of
  mixing milestones.
- Stop if reducing the root below `260 / 4` would require changing public API,
  CLI, or schema contracts rather than internal ownership.
- Stop if the extraction begins to move service logic into
  `app/services/retrieval_learning.py`, routers, CLI commands, audit bundle
  serializers, integration support, or DB-model code.
- Stop if the new family-local owners would themselves require a second stacked
  packet larger than the current root reduction without first landing the
  intermediate narrowed state and routing that residual explicitly.

## Local Commit Closeout Policy

- Milestone 0 is complete only after the live baseline is refreshed, the packet
  is recorded in the handoff/index/parent brief, and the retrieval-learning
  implementation can be staged without unrelated semantic-registry or
  classifier-family edits.
- Milestones 1 and 2 should land as atomic commits with only their code, test,
  config, and doc updates if they materially change the family shape.
- Milestone 3 is complete only after the full DB-backed suite passes, the
  architecture gates are refreshed, the current-state docs are updated, and the
  final commit contains only the retrieval-learning artifact family slice.

## Residual Risks And Next Routing

- The retrieval-learning family still has adjacent larger test roots after this
  packet. If the service owner closes cleanly, the next broader reselect will
  likely shift to `tests/unit/test_search_replays.py`,
  `tests/unit/test_search_api_harnesses.py`, or `app/services/ingest_batches.py`
  depending on fresh churn evidence.
- If Milestone 3 cannot resolve the root below the target without destabilizing
  search-harness release behavior, close the packet as `reduced` and route the
  remaining owner explicitly to the offending successor module rather than
  silently accepting new family drift.

# Semantic Registry Owner Rebaseline Milestone Plan

Date: 2026-05-19 local / 2026-05-19 UTC
Status: deployed locally on 2026-05-19 after Milestones 0 through 3 completed
and the classifier-family blocker was isolated into its own closeout commit.
The root now closes at `31 / 0` over
`app/services/semantic_registry_contracts.py` at `400 / 2`,
`app/services/semantic_registry_storage.py` at `85 / 3`, and
`app/services/semantic_registry_state.py` at `322 / 3`, with
`IC-0E4F1B9A2D73` recorded as the deployed owner case. The packet now closes as
its own atomic milestone rather than waiting behind the unrelated
classifier-family control-plane work.
Owner context: fresh broader rebaseline packet for the next non-trap
large-owner surface after the classifier-family control-plane refresh. The live
`top_routed_hotspot_paths` queue is empty again, so this packet selects the
next technical pass from the broader architecture evidence rather than from a
still-active routed child queue.

## Purpose

Resolve the next real semantic service owner boundary instead of reopening a
deferred facade or pretending the empty routed queue means no debt remains.

At the Milestone 0 baseline, the live backlog had shifted away from routed
facade traps and back to under-governed large owners. Among the non-trap
candidates, the strongest next surface was `app/services/semantic_registry.py`:

- it remains a `726` line / `31` definition / `9` private-helper mixed owner
- it has local import fan-in of `36`
- it still mixes payload contract parsing, seed-file load/write and cache,
  lookup helpers, relation validation, snapshot persistence, workspace-state
  synchronization, and active-registry resolution
- `config/hygiene_policy.yaml` gives it only a broad `730 / 9` ceiling and no
  `owner_case_id`
- `config/improvement_cases.yaml` does not currently create a dedicated owner
  case for it

This packet exists to rebaseline that surface honestly, preserve the completed
classifier-family work as a separate closeout, and route the next code-owning
split into focused semantic registry owners rather than back into the already
reduced `app/services/semantics.py` facade or adjacent semantic modules.

## Local Closeout Update

- Milestones 0 through 3 are now deployed locally. The classifier-family dirty
  slice was isolated into the preceding closeout commit, the semantic-registry
  split landed entirely inside the registry family, and the routed queue remains
  `top_routed_hotspot_paths=[]`.
- Verification now includes `uv run pytest -q` on the focused semantic unit
  slice at `28 passed`, the focused semantic and governance policy slice at
  `30 passed`, the DB-backed semantic integration slice at `12 passed`,
  `uv run docling-system-hotspot-prevention-check --strict` at `blocked=0`,
  `uv run docling-system-hygiene-check` with no regressions, and the full
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` gate at
  `2143 passed`.
- Debt-shift audit: `git diff --stat` over
  `app/services/semantic_registry_preview.py`, `app/services/semantic_ontology.py`,
  `app/services/semantic_candidates.py`, `app/services/semantic_graph.py`,
  `app/services/semantic_generation.py`, `app/services/semantic_pass_lifecycle.py`,
  `app/services/semantic_pass_reads.py`, the focused semantic unit roots, and
  the focused semantic integration roots remained empty after the split, so the
  packet did not transfer registry debt into adjacent semantic owners.

## Milestone 0 Baseline Evidence

Live baseline from the Milestone 0 2026-05-19 checkout before the split:

```text
git status -sb
  ## main...origin/main [ahead 3]
   M README.md
   M app/hotspot_prevention_classifier.py
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
  ?? app/hotspot_prevention_classifier_owner_rules.py

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=20
  legibility_gap_count=0
  stale_facade_hotspot_count=20
  max_hotspot_risk_score=471.06
  top_routed_hotspot_paths=[]

uv run docling-system-improvement-case-summary
  case_count=63
  status_counts={"measured":1,"deployed":62}
  actionable_buckets.open_unconverted_count=0
  actionable_buckets.verified_undeployed_count=0

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Largest files include:
    tests/unit/test_search_replays.py = 776
    app/services/retrieval_learning_artifacts.py = 774
    tests/unit/test_search_api_harnesses.py = 764
    app/services/semantic_registry.py = 726
    app/services/ingest_batches.py = 692
  Python import fan-in includes:
    app.services.semantic_registry = 36
  Python cycles: none detected

wc -l app/services/semantic_registry.py \
  app/services/semantic_registry_preview.py \
  app/services/semantic_ontology.py \
  app/services/semantic_governance.py \
  app/services/semantic_candidates.py \
  app/services/semantic_graph.py \
  app/services/semantic_generation.py \
  app/services/semantic_pass_lifecycle.py \
  app/services/semantic_pass_reads.py \
  tests/unit/test_semantic_registry.py \
  tests/unit/test_semantic_registry_preview.py \
  tests/integration/test_semantic_governance_ledger.py \
  tests/integration/test_postgres_roundtrip_semantics.py
     726 app/services/semantic_registry.py
     558 app/services/semantic_registry_preview.py
     280 app/services/semantic_ontology.py
      39 app/services/semantic_governance.py
     120 app/services/semantic_candidates.py
     185 app/services/semantic_graph.py
      91 app/services/semantic_generation.py
     529 app/services/semantic_pass_lifecycle.py
     372 app/services/semantic_pass_reads.py
     100 tests/unit/test_semantic_registry.py
     121 tests/unit/test_semantic_registry_preview.py
     438 tests/integration/test_semantic_governance_ledger.py
     503 tests/integration/test_postgres_roundtrip_semantics.py

python - <<'PY'
from pathlib import Path
for path_str in [
    "app/services/semantic_registry.py",
    "app/services/semantic_registry_preview.py",
    "app/services/semantic_ontology.py",
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
  app/services/semantic_registry.py defs_or_classes=31 private_helpers=9
  app/services/semantic_registry_preview.py defs_or_classes=9 private_helpers=5
  app/services/semantic_ontology.py defs_or_classes=8 private_helpers=2

config/hygiene_policy.yaml
  app/services/semantic_registry.py:
    max_lines: 730
    max_private_helpers: 9
    no owner_case_id is currently recorded
```

Milestone 0 structural evidence:

- `app/services/semantic_registry.py` currently groups:
  semantic registry dataclasses, payload validation and normalization,
  seed-path resolution, registry load/write/cache, relation and entity-type
  lookup helpers, relation-instance validation, snapshot persistence,
  workspace-state synchronization, and live registry resolution.
- `app/services/semantic_registry_preview.py` is already a separate `558 / 5`
  owner and must not reabsorb registry persistence or contract debt.
- `app/services/semantic_pass_lifecycle.py` (`529 / 3`) and
  `app/services/semantic_pass_reads.py` (`372 / 3`) are already governed
  owners and must not become spillover sinks for registry work.
- `app/services/semantic_candidates.py`, `app/services/semantic_graph.py`,
  `app/services/semantic_generation.py`, and `app/services/semantic_ontology.py`
  are current consumers or adjacent semantic owners, not the default target for
  new registry extraction debt.
- The current worktree is not clean. The in-flight classifier-family closeout
  is still dirty across source, config, docs, and tests, so the next code-owning
  semantic packet must begin with explicit worktree isolation and must not mix
  classifier closeout and semantic-registry implementation in one milestone.

## Goal

Resolve the semantic registry owner boundary so that:

- `app/services/semantic_registry.py` becomes a narrow public facade or
  coordination surface at `max_lines <= 260` and `max_private_helpers <= 4`
- registry contract parsing and validation, registry load/write/cache, and
  workspace snapshot or activation state no longer cohabit the same file
- `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, and
  `config/hotspot_prevention.yaml` gain explicit current-state governance for
  the semantic registry family instead of leaving the root under a generic line
  ceiling
- existing semantic preview, ontology, candidate, graph, generation, and
  agent-task semantic-verification behavior remains stable
- the packet closes without transferring debt into
  `semantic_registry_preview.py`, `semantic_ontology.py`, or the already-routed
  semantic pass owners

## Non-Goals

- No reopening of `app/services/semantics.py` as the primary owner surface.
- No rewrite of the semantic preview owner in
  `app/services/semantic_registry_preview.py` unless Milestone 0 proves a
  contract seam has genuinely regrown there.
- No ORM or migration work.
- No change to semantic ontology snapshot semantics, task-type names, or API
  surface contracts unless an exact test or integration failure proves a bug in
  the current implementation.
- No mixing of the still-dirty classifier-family completion slice with the
  semantic registry implementation milestone.
- No weakening of semantic registry, semantic preview, semantic governance, or
  semantic roundtrip coverage to get a green result.

## Scope

In scope:

- `app/services/semantic_registry.py`
- new `app/services/semantic_registry_*.py` owner modules
- `app/services/semantic_registry_preview.py` only for compatibility seams,
  import updates, or direct tests required by the new owners
- `app/services/semantic_ontology.py` only for import placement or focused
  contract adjustments proven necessary by Milestone 0
- direct registry consumers such as
  `app/services/semantic_bootstrap.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_candidate_evaluation.py`,
  `app/services/semantic_graph_build.py`,
  `app/services/semantic_facts.py`,
  `app/services/semantic_pass_artifacts.py`,
  `app/services/agent_task_verifications.py`, and
  `app/services/agent_actions/semantic_governance_actions.py`
  only where imports or owner seams must be redirected
- `tests/unit/test_semantic_registry.py`
- `tests/unit/test_semantic_registry_preview.py`
- directly affected semantic unit and integration tests
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `config/hotspot_prevention.yaml`
- `docs/semantic_registry_owner_rebaseline_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`

Out of scope:

- unrelated large tests such as `tests/unit/test_search_replays.py` or
  `tests/unit/test_search_api_harnesses.py`
- retrieval-learning, ingest, or CLI owner families
- unrelated dirty worktree files outside the semantic-registry routing/doc slice

## Owner Surfaces

- root public semantic registry surface:
  `app/services/semantic_registry.py`
- semantic registry contract and normalization owner(s):
  future `app/services/semantic_registry_*.py` modules created by this packet
- semantic registry snapshot and workspace-state owner(s):
  future `app/services/semantic_registry_*.py` modules created by this packet
- preview compatibility consumer:
  `app/services/semantic_registry_preview.py`
- ontology and downstream semantic consumers:
  `app/services/semantic_ontology.py`,
  `app/services/semantic_bootstrap.py`,
  `app/services/semantic_candidates.py`,
  `app/services/semantic_candidate_evaluation.py`,
  `app/services/semantic_graph_build.py`,
  `app/services/semantic_facts.py`,
  `app/services/semantic_pass_artifacts.py`
- semantic registry unit and integration verification:
  `tests/unit/test_semantic_registry.py`,
  `tests/unit/test_semantic_registry_preview.py`,
  `tests/integration/test_semantic_governance_ledger.py`,
  `tests/integration/test_postgres_roundtrip_semantics.py`,
  `tests/integration/test_semantic_bootstrap_roundtrip.py`,
  `tests/integration/test_semantic_candidate_roundtrip.py`,
  `tests/integration/test_semantic_generation_roundtrip.py`,
  `tests/integration/test_semantic_graph_roundtrip.py`,
  `tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`
- control-plane ownership:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`

## Placement Rules

- Keep `app/services/semantic_registry.py` as the public import path for
  existing callers. If the implementation moves, preserve compatibility through
  narrow forwarding or import-reexport seams.
- Separate at least these concern families:
  registry contract parsing or validation,
  file-path load/write/cache behavior,
  workspace snapshot or activation state.
- Do not move registry persistence or normalization debt into
  `app/services/semantic_registry_preview.py`, `app/services/semantic_ontology.py`,
  `app/services/semantic_candidates.py`, `app/services/semantic_graph.py`, or
  `app/services/semantic_generation.py`.
- Prefer no more than three new `semantic_registry_*` owner modules. If the
  split needs more than three, stop and write a narrower follow-on instead of
  diffusing the boundary.
- Add hotspot-prevention or owner-routing guards only after Milestone 0 proves
  the post-split facade shape and preferred owner paths.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The packet starts while the classifier-family completion slice is still unclosed, mixing two milestones into one commit. | current worktree, handoff, this plan | `git status -sb` review plus Milestone 0 closeout policy | Semantic-registry implementation begins while classifier-family source/config/test/doc changes are still intended to land separately. | Attempt to stage semantic-registry code together with the classifier-family dirty slice and confirm Milestone 0 rejects it. | A future session sees both lanes dirty and bundles them into one "architecture cleanup" commit. |
| The root file shrinks only because mixed logic is dumped into another generic semantic helper sink. | `app/services/semantic_registry.py`, new `semantic_registry_*.py` owners, hygiene policy | staged `wc -l`, staged def-count review, `uv run docling-system-hygiene-check` | A new owner file exceeds its same-milestone target or still mixes unrelated registry concerns without explicit routing. | Move contract parsing and snapshot activation into one catch-all helper and confirm acceptance review fails. | A future session renames the monolith but preserves the same mixed boundary. |
| Preview, ontology, or other adjacent semantic owners absorb registry implementation debt. | `semantic_registry_preview.py`, `semantic_ontology.py`, semantic pass owners, semantic consumers | targeted `git diff --stat` review plus semantic unit and integration slices | New registry logic lands primarily in preview, ontology, graph, candidate, or generation modules instead of the planned registry owners. | Route registry snapshot activation through `semantic_registry_preview.py` and confirm closeout rejects it. | A future session appends logic to the nearest semantic file because it already imports the registry. |
| The packet lands code changes without a dedicated owner case or routed control-plane entry, so the same root regrows later. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, `config/hotspot_prevention.yaml` | `uv run docling-system-improvement-case-validate`, summary review, hotspot-prevention strict gate | No explicit owner case or ratchet exists for the semantic-registry root and successor modules at closeout. | Complete the split but omit the owner-case bootstrap and confirm validation or closeout review blocks the milestone. | A future session finishes the refactor locally but leaves the control plane unable to enforce it. |
| Semantic registry persistence behavior changes silently because unit-only coverage misses DB-backed activation or snapshot flows. | semantic registry integrations and semantic governance ledger tests | DB-backed integration slice plus full suite closeout gate | Any semantic snapshot activation, workspace-state sync, or registry-draft flow regresses without an integration failure. | Skip the integration slice after changing snapshot persistence and confirm the milestone cannot close. | A future session trusts unit coverage even though registry state is persisted and activated through the DB. |

## Milestone Sequence

### Milestone 0: Worktree Isolation, Live Rebaseline, And Owner Bootstrap

Outcome label: reduced.

Before any semantic-registry code split begins:

- close, commit, or explicitly preserve the current classifier-family dirty
  slice so this packet starts from a clean semantic-registry scope
- rerun the live architecture-quality summary, architecture probe, hygiene
  check, and improvement-case summary
- record `app/services/semantic_registry.py` as the selected next owner surface
  for this broader reselect
- create dedicated improvement-case and hygiene ownership for the semantic
  registry root, and define the post-split routing target shape this packet
  intends to enforce

Milestone 0 is complete only if:

- the packet is the queued standalone follow-on in the handoff and index
- semantic-registry work is isolated from the classifier-family closeout
- current live evidence still supports `app/services/semantic_registry.py` as
  the selected next owner
- the packet establishes gate-first ownership rather than starting with an
  ad hoc file split

### Milestone 1: Contract And File-Backed Registry Extraction

Outcome label: reduced.

Extract registry contract parsing, normalization, lookup helpers, and seed-file
load/write/cache behavior into focused registry owner modules while keeping
`app/services/semantic_registry.py` as the public import path.

Target constraints:

- `app/services/semantic_registry.py` shrinks substantially toward facade shape
- contract and file-backed concerns no longer cohabit the same file
- preview and ontology modules remain consumers, not new registry sinks

### Milestone 2: Snapshot And Workspace-State Extraction

Outcome label: reduced.

Extract snapshot persistence, workspace-state synchronization, active snapshot
resolution, and registry activation behavior into focused registry owner
modules.

Target constraints:

- DB-backed activation and snapshot behavior no longer cohabits the root with
  contract and seed-file logic
- semantic governance ledger and semantics roundtrip coverage remain stable
- no more than three total new `semantic_registry_*` owner modules are created

### Milestone 3: Facade Reduction, Ratchets, And Queue Reroute

Outcome label: resolved.

Close the scoped semantic-registry owner issue by:

- reducing the root to a narrow compatibility surface
- exact-ratcheting the root and successor modules
- updating improvement cases and hotspot-prevention routing
- refreshing the handoff, architecture index, and broader coordination brief
- rerunning the routed queue to confirm the root is no longer the next honest
  owner by default

## Required Implementation Artifacts

- updated `app/services/semantic_registry.py`
- focused new `app/services/semantic_registry_*.py` owner modules
- updated semantic registry unit and integration tests
- updated `config/improvement_cases.yaml`
- updated `config/hygiene_policy.yaml`
- updated `config/hotspot_prevention.yaml`
- updated handoff and architecture-index docs

## Required Documentation And Handoff Updates

- this plan:
  `docs/semantic_registry_owner_rebaseline_milestone_plan.md`
- canonical handoff:
  `docs/SESSION_HANDOFF.md`
- architecture index:
  `docs/agentic_architecture_index.md`
- broader coordination brief:
  `docs/boring_change_architecture_milestone_plan.md`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/semantic_registry.py app/services/semantic_registry_preview.py app/services/semantic_ontology.py app/services/semantic_bootstrap.py app/services/semantic_candidates.py app/services/semantic_candidate_evaluation.py app/services/semantic_graph_build.py app/services/semantic_facts.py app/services/semantic_pass_artifacts.py tests/unit/test_semantic_registry.py tests/unit/test_semantic_registry_preview.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_orchestration.py tests/unit/test_agent_task_actions_semantic_registry.py tests/unit/test_agent_task_verifications_semantics.py`
- `uv run pytest -q tests/unit/test_semantic_registry.py tests/unit/test_semantic_registry_preview.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_orchestration.py tests/unit/test_agent_task_actions_semantic_registry.py tests/unit/test_agent_task_verifications_semantics.py tests/unit/test_semantic_bootstrap.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_semantic_governance_ledger.py tests/integration/test_postgres_roundtrip_semantics.py tests/integration/test_semantic_bootstrap_roundtrip.py tests/integration/test_semantic_candidate_roundtrip.py tests/integration/test_semantic_generation_roundtrip.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- Milestone 0 proves the classifier-family dirty slice is isolated and that the
  semantic-registry packet is the active queued broader-reselect follow-on.
- `app/services/semantic_registry.py` gains explicit owner-case and hygiene
  governance before broad refactoring begins.
- Contract parsing, seed-file load/write/cache, and snapshot or workspace-state
  activation no longer live together in the same file by closeout.
- `app/services/semantic_registry.py` closes at `<= 260` lines and
  `<= 4` private helpers.
- No new `semantic_registry_*` owner file exceeds `<= 450` lines or
  `<= 8` private helpers.
- `app/services/semantic_registry_preview.py` stays at or below its current
  `558 / 5` budget unless Milestone 0 explicitly proves a stricter exact
  ratchet during the same packet.
- Preview, ontology, semantic candidate, semantic graph, semantic generation,
  semantic governance, and semantic pass behavior remain stable across the
  targeted unit and integration suite.
- Improvement-case validation, hygiene, hotspot prevention, architecture
  inspection, and the full DB-backed suite remain green at closeout.

## Stop Conditions

- Stop if the classifier-family completion slice is not actually ready to
  close or preserve separately.
- Stop if Milestone 0 shows `app/services/semantic_registry.py` is no longer
  the strongest next non-trap owner surface.
- Stop if preserving semantic behavior would require more than three new
  `semantic_registry_*` owner modules.
- Stop if the split would push new registry debt into preview, ontology, or
  adjacent semantic owners rather than into focused registry modules.
- Stop if targeted semantic integrations imply an API, storage, schema, or
  migration change outside this packet.

## Local Commit Closeout Policy

- Do not stage the current classifier-family completion slice with the semantic
  registry implementation milestone.
- Milestone 0 may close as a docs-only routing packet after the semantic
  reselect is recorded durably.
- Later code milestones must stage only the verified semantic-registry source,
  tests, control-plane files, generated artifacts, and handoff/doc updates
  touched by that milestone.
- Each milestone is incomplete until its own atomic local commit exists.

## Residual Risks And Next Milestone Routing

- If Milestone 0 proves that a narrower semantic-registry subfamily, such as
  snapshot activation only, is the real hard-to-change surface, stop and write
  that narrower child packet rather than forcing the whole registry root
  through one oversized split.
- If the final reroute still leaves the root selected indirectly through a
  fresh live hotspot, route the next packet from the updated live
  `top_routed_hotspot_paths` or architecture probe evidence rather than from
  this packet’s assumptions.

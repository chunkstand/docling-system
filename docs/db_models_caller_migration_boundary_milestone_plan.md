# DB Models Caller Migration Boundary Milestone Plan

Date: 2026-05-20 local / 2026-05-20 UTC
Status: resolved locally in the current checkout on 2026-05-20. The packet
completed the `app.db.models` caller migration by adding bounded
`app/db/public/*` facades, moving ordinary production and routine test callers
onto the narrow public modules, and leaving the legacy shim behind an explicit
machine-checked allowlist. The newer
`docs/production_trap_set_centrality_reduction_milestone_plan.md` remains the
broader optional follow-on for the remaining governed production trap set, but
this DB-only fan-in lane is no longer an open subpacket underneath it.
Owner context: [app/db/models.py](/Users/chunkstand/Documents/docling-system/app/db/models.py:1)
is already the governed public compatibility facade under
`IC-F2A8110185EB`; the remaining debt is importer gravity, not remaining ORM
ownership. The live architecture queue is empty, so this packet is a proactive
blast-radius reduction brief rather than a queued hotspot split.

## Purpose

Reduce the blast radius of the public `app.db.models` facade by introducing
bounded public DB import surfaces, migrating callers off the monolithic facade
family by family, and mechanically blocking new direct imports that would
rebuild the current `337`-import gravity.

## Current Evidence

- `uv run docling-system-architecture-quality-report --summary` currently
  reports `top_routed_hotspot_paths=[]`,
  `broader_rebaseline_candidate_count=0`,
  `top_broader_rebaseline_paths=[]`, and
  `status_counts={"deployed":67}`. This is not an active queued packet; it is
  discretionary technical paydown.
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 25`
  measured the Milestone 0 baseline at `337` local `app.db.models` importers,
  still the highest import fan-in in the repo at packet start.
- A repo-wide importer census at Milestone 0 found `337` Python files
  importing `app.db.models`: `224` under `app/`, `113` under `tests/`, and
  `221` under `app/services/`; the densest current bounded cluster was
  `app/services/agent_actions/` with `26` direct importers.
- The earlier compatibility-facade packet intentionally froze
  `app/db/models.py` as the only public caller surface and explicitly said
  “do not require broad caller rewrites away from `app.db.models`” and “do not
  create a second de facto public import path.” That constraint was correct for
  closing the facade packet, but it is now the exact boundary this packet must
  change on purpose.
- `app/db/models.py` is already a `159`-line pure compatibility facade with
  delayed internal imports and explicit forwarders only; it is guarded by
  `tests/unit/test_db_models_facade_contract.py`.
- The residual DB-model owner-family packet is also already closed. The
  remaining debt is not in `app/db/model_domains/*` line count or schema
  ownership; it is in how broadly callers still depend on the legacy facade.

## Closeout Summary

- Added bounded public caller surfaces under `app/db/public/` for the
  `agent_tasks`, `audit_and_evidence`, `claim_support`,
  `document_artifacts`, `evaluation_feedback`, `ingest`, `platform`,
  `retrieval`, and `semantic_memory` model families.
- Added the repo-owned policy artifact
  `config/db_model_import_policy.yaml` plus
  `tests/unit/test_db_model_public_import_routes.py` so the exact legacy
  allowlist, direct-import counts, and the internal-only
  `app.db.model_domains.*` rule are machine-checked.
- Migrated `328` production, unit-test, and integration callers from
  `app.db.models` to the narrow public modules without introducing new
  `app.db.model_domains.*` application callers.
- Reduced the live direct-import census from the Milestone 0 `337`-import
  legacy gravity to `9` allowlisted compatibility and metadata harness files
  (`0` under `app/`, `9` under `tests/`).
- Cleared the dense production cohorts named by the packet: the live importer
  census now reports `0` direct legacy imports under
  `app/services/agent_actions`, `app/services/agent_task*`,
  `app/services/claim_support*`, `app/services/court_grade_readiness*`,
  `app/services/retrieval*`, `app/services/run*`, `app/services/search*`, and
  `app/services/semantic*`.
- The latest architecture probe no longer lists `app.db.models` in the top
  import fan-in table. The new bounded public roots now absorb that caller
  gravity with `app.db.public.agent_tasks=173`,
  `app.db.public.retrieval=80`, `app.db.public.ingest=69`,
  `app.db.public.semantic_memory=68`,
  `app.db.public.audit_and_evidence=55`,
  `app.db.public.claim_support=40`, and
  `app.db.public.document_artifacts=38`.

## Verification Snapshot

- `git diff --check`: pass
- `uv run ruff check app/db app/services tests`: pass
- `uv run pytest -q tests/unit/test_db_models_facade_contract.py tests/unit/test_db_model_import_compatibility.py tests/unit/test_db_model_import_compatibility_audit_and_evidence.py tests/unit/test_db_model_import_compatibility_claim_support.py tests/unit/test_db_model_import_compatibility_semantic_memory.py tests/unit/test_db_model_public_import_routes.py`: `617 passed`
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_db_model_metadata.py tests/integration/test_db_model_metadata_audit_and_evidence.py tests/integration/test_db_model_metadata_claim_support.py tests/integration/test_db_model_metadata_semantic_memory.py`: `335 passed`
- `uv run --extra dev alembic heads`: `0076_claim_feedback_replay_src (head)`
- `uv run --extra dev alembic current`: `0076_claim_feedback_replay_src (head)`
- `uv run --extra dev alembic upgrade head`: pass
- `uv run --extra dev alembic check`: `No new upgrade operations detected.`
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `2192 passed`, `1` docling deprecation warning
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-validate`: `valid=true`
- `uv run docling-system-improvement-case-summary`: `status_counts={"deployed":67}`
- `uv run docling-system-architecture-inspect`: `valid=true`, `violation_count=0`
- `uv run docling-system-architecture-quality-report --summary`: `top_routed_hotspot_paths=[]`, `broader_rebaseline_candidate_count=0`, `max_hotspot_risk_score=466.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`: pass, `Python cycles: none detected`

## Alignment And Debt-Shift Review

- The active packet docs, handoff, architecture index, and broader trap-set
  brief now agree that this DB caller-migration lane is resolved locally and
  is no longer an open queued subpacket.
- The packet-local debt-shift audit over closeout commit `4284cd5d` stayed
  bounded: `app/db/public/*` closes at `5` to `75` lines, direct
  `app.db.models` imports fell from `337` to `9`, and no ordinary caller now
  imports `app.db.model_domains.*`.
- `uv run docling-system-hotspot-prevention-check --strict`,
  `uv run docling-system-hygiene-check`,
  `uv run docling-system-architecture-inspect`, and
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`
  all stayed green after the closeout, so the packet did not reopen cycles,
  routed hotspots, or architecture violations.
- The selected production trap roots stayed flat on fan-out except
  `app/services/audit_bundles.py`, which moved from `14` to `15` local imports
  because one legacy `app.db.models` dependency became bounded retrieval plus
  audit-and-evidence public-module imports. The root remains `596` lines, no
  sibling public facade regrew into a broad sink, and the live routed queue
  stayed empty.
- No changed Python file crossed upward through the `600` or `800` line
  thresholds in `HEAD^..4284cd5d`; the only threshold crossing was downward,
  with `app/services/claim_support_replay_alert_promotions.py` moving
  `600 -> 597`.

## Goal

- Keep `app/db/models.py` as a legacy compatibility shim during migration, but
  stop treating it as the only approved public import path.
- Introduce bounded public DB import facades that mirror the already split ORM
  domain families.
- Migrate callers off `app.db.models` by bounded cohorts until direct imports
  are confined to an explicit, machine-checked allowlist.
- Add a durable import-policy gate that ratchets the legacy direct-import count
  downward and blocks new `app.db.models` imports outside the allowlist.

## Non-Goals

- Do not move additional ORM classes out of `app/db/model_domains/`.
- Do not change table names, columns, indexes, constraints, relationship
  names, foreign keys, vector dimensions, or Alembic behavior.
- Do not migrate callers directly to internal `app.db.model_domains.*`
  modules.
- Do not delete `app/db/models.py` in the first migration packet.
- Do not widen the public model or enum surface beyond the current governed
  symbols in `tests/db_model_contract.py`.
- Do not weaken DB-model compatibility, metadata, or integration gates to make
  the migration pass.

## Scope

- `app/db/models.py`
- new bounded public DB facade package under `app/db/public/`
- `tests/db_model_contract.py`
- `tests/unit/test_db_models_facade_contract.py`
- new import-policy tests such as
  `tests/unit/test_db_model_public_import_routes.py`
- `config/architecture_inspection.yaml` and architecture-governance rules if
  the import-policy gate belongs in the repo-wide architecture inspection
  workflow
- selected caller cohorts in `app/`, `tests/unit/`, and `tests/integration/`
  chosen from the baseline importer census
- routing and closeout docs:
  `docs/db_models_caller_migration_boundary_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/boring_change_architecture_milestone_plan.md`,
  `docs/architecture_boundaries.md`,
  `docs/architecture_decisions.yaml`, and
  `docs/architecture_decision_map.json`

## Out Of Scope

- `app/db/model_domains/*` schema-owner rewrites
- unrelated search, evidence, agent-task, worker, readiness, or UI refactors
- migration-number churn or DDL changes
- opportunistic cleanup of unrelated dirty files already in the worktree

## Owner Surfaces

- Legacy shim:
  `app/db/models.py`
- New public DB import package:
  `app/db/public/__init__.py` plus domain-scoped public modules such as
  `agent_tasks.py`, `audit_and_evidence.py`, `claim_support.py`,
  `document_artifacts.py`, `evaluation_feedback.py`, `ingest.py`,
  `platform.py`, `retrieval.py`, and `semantic_memory.py`
- Contract and import-policy sources:
  `tests/db_model_contract.py`,
  `tests/unit/test_db_models_facade_contract.py`,
  `tests/unit/test_db_model_public_import_routes.py`
- Optional governance extensions:
  `app/architecture_inspection.py`,
  `tests/unit/test_architecture_inspection.py`,
  `config/architecture_inspection.yaml`
- Selected caller cohorts under `app/`, `tests/unit/`, and
  `tests/integration/`

## Placement Rules

- New caller-facing DB import surfaces must live under `app/db/public/`.
- `app/db/model_domains/` stays internal to `app/db/`; do not let app or test
  callers import `app.db.model_domains.*` directly.
- Each new public DB facade must map to one existing domain family from
  `tests/db_model_contract.py`; do not recreate a second all-symbol facade.
- `app/db/models.py` remains the temporary legacy shim and public
  compatibility check surface until the packet’s final milestone says
  otherwise.
- Production callers must import the narrowest matching `app.db.public.*`
  module available for their model family.
- Compatibility and metadata harness files may remain on `app.db.models` only
  when the import-policy allowlist explicitly names them.
- If a caller genuinely spans multiple model families, prefer multiple narrow
  imports over adding a cross-family convenience facade.

## Weak-Point Prevention Contract

- Weak point forecast: the new public package becomes a second monolith that
  simply duplicates `app.db.models`.
  Owner surface: `app/db/public/*.py`, `tests/db_model_contract.py`
  Prevention gate: bounded export-manifest tests and per-module line-count
  review in the final diff
  Fail threshold: any new public DB facade exports unrelated domain families or
  regrows into a broad all-symbol surface
  Controlled violation: add a cross-domain export to a public DB facade and
  prove the export-manifest gate fails
  Future-Codex misuse scenario: a future session adds “just one more” shared
  model to `app/db/public/retrieval.py` or `app/db/public/agent_tasks.py`
  because the module already exists; the domain-scoped export gate must reject
  that drift

- Weak point forecast: callers bypass the new public facades and import
  `app.db.model_domains.*` directly, replacing one dependency problem with a
  worse internal-coupling problem
  Owner surface: importer policy test and architecture inspection rules
  Prevention gate: repo-wide scan that rejects non-allowlisted
  `app.db.model_domains.*` imports outside `app/db/` and DB-model contract
  tests
  Fail threshold: any application or non-contract test caller imports
  `app.db.model_domains.*` directly
  Controlled violation: add a fixture file with a direct internal domain import
  and prove the policy gate fails
  Future-Codex misuse scenario: a future session migrates one file quickly by
  pointing it at `app.db.model_domains.semantic_memory_reviews` instead of the
  bounded public facade

- Weak point forecast: the packet adds new public facades but leaves direct
  `app.db.models` import count flat, so fan-in never actually contracts
  Owner surface: importer-census policy artifact and route test
  Prevention gate: machine-checked importer inventory with ratcheted maximums
  for `app/`, `tests/`, and selected migration cohorts
  Fail threshold: the allowed direct-import counts do not go down from the
  baseline after a migration milestone closes
  Controlled violation: temporarily add a new `from app.db.models import ...`
  statement in a non-allowlisted file and prove the policy test fails
  Future-Codex misuse scenario: another packet lands and uses the legacy facade
  because it is simpler, silently rebuilding the import hotspot

- Weak point forecast: migration rewrites break compatibility, metadata, or DB
  behavior even though model definitions do not move
  Owner surface: `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`, Alembic commands, full
  DB-backed suite
  Prevention gate: compatibility tests, metadata tests, Alembic heads/current/
  upgrade/check, and the full `DOCLING_SYSTEM_RUN_INTEGRATION=1` suite
  Fail threshold: any import break, metadata drift, Alembic failure, or DB
  regression appears during the migration
  Controlled violation: point a migrated caller at an incomplete public facade
  and prove import compatibility or integration gates fail
  Future-Codex misuse scenario: a future session trims an export from
  `app.db.models` or forgets to mirror a required enum in a new public module

## Milestone Sequence

### Milestone 0: Freshness Lock And Contract Reset

Outcome label: `reduced`

Purpose:
Rebaseline the live import-gravity problem and explicitly supersede the earlier
“only public caller surface” rule for this packet.

Scope:

- refresh the importer census for `app.db.models`
- record current counts for total files, `app/`, `tests/`, and selected dense
  cohorts
- add or amend the architecture decision and boundary docs to allow bounded
  `app/db/public/*` facades for caller migration
- define the selected migration cohorts for the first implementation pass

Acceptance:

- durable docs record that `app/db/models.py` remains the legacy shim but is no
  longer the only approved public caller surface
- the baseline importer census is checked in or reproducible from a repo-owned
  gate
- the packet names the initial migration cohorts before implementation begins

### Milestone 1: Public DB Facade Package And Policy Gate

Outcome label: `reduced`

Purpose:
Create the new bounded import surfaces and the gate that will measure actual
fan-in reduction.

Scope:

- add `app/db/public/` domain facades
- extend `tests/db_model_contract.py` with public-facade export manifests
- add a repo-owned import-policy test and any supporting config artifact
- update facade-contract tests so the new public modules may use
  `app.db._model_enums` internally without making that private module a caller
  surface

Acceptance:

- every new public DB facade re-exports one bounded domain family only
- the import-policy gate blocks new direct `app.db.models` imports outside the
  allowlist and blocks direct `app.db.model_domains.*` imports outside allowed
  repo-internal surfaces
- `app/db/models.py` remains structurally identical in purpose: a legacy
  compatibility shim, not a regrown implementation surface

### Milestone 2: Production Caller Cohort Migration

Outcome label: `reduced`

Purpose:
Move the densest production callers off the legacy shim first.

Scope:

- migrate `app/services/agent_actions/**` away from `app.db.models`
- migrate the adjacent `agent_task_*`, `claim_support_*`, `retrieval_*`,
  `search_*`, `semantic_*`, `run_*`, and readiness callers selected in
  Milestone 0 where a bounded public DB facade now exists
- keep each migration cohort aligned to the narrowest matching public DB module

Acceptance:

- the selected production cohorts no longer import `app.db.models` directly
- the total `app/` direct-import count is lower than the Milestone 0 baseline
- no production caller imports `app.db.model_domains.*` directly
- the packet does not regrow `app/db/models.py` or any existing model-domain
  owner module

### Milestone 3: Test And Integration Caller Migration

Outcome label: `reduced`

Purpose:
Remove routine test and integration dependence on the legacy shim while keeping
explicit compatibility harnesses on the allowlist.

Scope:

- migrate ordinary unit and integration callers to `app/db/public/*`
- keep only explicit compatibility, metadata, and legacy-import contract tests
  on the direct `app.db.models` allowlist
- tighten the importer-count ratchet after test migration lands

Acceptance:

- direct `app.db.models` imports in `tests/unit/` and `tests/integration/`
  are confined to the explicit allowlist
- compatibility and metadata harness coverage remains equivalent or stronger
- the total direct-import count decreases again from the Milestone 2 state

### Milestone 4: Legacy Shim Contraction And Honest Residual Route

Outcome label: `resolved`

Purpose:
Resolve the blast-radius problem for this packet by leaving `app.db.models` as
an explicitly legacy, low-churn compatibility shim with only allowlisted
callers.

Scope:

- shrink the allowlist to compatibility-boundary surfaces only
- update architecture quality / inspection reporting if needed so future drift
  is visible in the repo-owned controls
- refresh durable docs, routing notes, and residual risk status

Acceptance:

- ordinary `app/` production callers no longer import `app.db.models`
  directly
- direct `app.db.models` imports are limited to an explicit, machine-checked
  allowlist for the legacy shim and compatibility harnesses
- the importer policy becomes the source of truth for future ratcheting
- the packet closes without reopening DB-model owner-family or schema debt

## Required Implementation Artifacts

- `app/db/public/` package with bounded domain facades
- repo-owned direct-import policy artifact and test
- updated DB-model contract manifests for new public facades
- migrated caller cohorts in `app/`, `tests/unit/`, and `tests/integration/`
- updated architecture decision/boundary docs for the new public import policy

## Required Documentation And Handoff Updates

- `docs/db_models_caller_migration_boundary_milestone_plan.md`
- `docs/data_model_boundary_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/architecture_boundaries.md`
- `docs/architecture_decisions.yaml`
- `docs/architecture_decision_map.json`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/db app/services tests`
- `uv run pytest -q tests/unit/test_db_models_facade_contract.py tests/unit/test_db_model_import_compatibility.py tests/unit/test_db_model_public_import_routes.py`
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 25`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --fail-on-cycles`

## Acceptance Criteria

- `app/db/models.py` stays a governed legacy compatibility shim and does not
  regrow new ORM or schema ownership.
- New caller-facing DB import surfaces exist under `app/db/public/` and each
  one maps to a single existing model-domain family.
- No new application or ordinary test caller imports `app.db.model_domains.*`
  directly.
- Direct `app.db.models` imports are ratcheted downward by repo-owned policy
  and end this packet confined to an explicit allowlist.
- Production import gravity around `app.db.models` is materially lower than the
  current `337`-import probe baseline and the `223` direct-import `app/`
  baseline.
- DB-model compatibility, metadata, Alembic, and full DB-backed suite
  verification stay green.
- Docs, handoff, and architecture control artifacts describe the new public DB
  import policy and the remaining residual import allowlist honestly.

## Stop Conditions

- Stop if migration requires schema or Alembic changes rather than caller-path
  changes.
- Stop if the proposed `app/db/public/*` package collapses into a second broad
  all-symbol facade instead of bounded domain surfaces.
- Stop if a selected cohort cannot be migrated without direct
  `app.db.model_domains.*` imports and no bounded public module can represent
  its needs cleanly.
- Stop if the packet only adds new public facades but cannot reduce the
  measured direct-import counts from the Milestone 0 baseline.
- Stop if unrelated dirty worktree files would have to be staged together with
  the packet to close the milestone.

## Local Commit Closeout Policy

Close each milestone as an atomic local commit containing only the bounded
public DB facades, migrated callers, contract tests, policy gates, and the
matching docs and handoff updates for that milestone. Do not bundle unrelated
search, hotspot-prevention, or other in-progress worktree changes into the
caller-migration commits.

## Residual Risks And Next Milestone Routing

- This packet changes a previously explicit contract, so Milestone 0 must land
  the boundary and decision update before large-scale caller rewrites begin.
- If Milestone 2 proves the selected production cohorts are too cross-cutting,
  split the remaining migration by domain family and keep the importer-policy
  ratchet active between follow-ons.
- If the final allowlist still contains ordinary production callers after
  Milestone 4, close the packet as `reduced` instead of `resolved` and route
  the remaining direct-import cohorts through the importer census rather than
  reopening `app/db/models.py` itself.

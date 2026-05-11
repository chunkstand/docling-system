# DB Models Compatibility Facade Milestone Plan

Date: 2026-05-11 local
Status: Milestone 2 facade ownership narrowing implemented, aligned, and
committed locally as `8340dc0`; `IC-F2A8110185EB` is now deployed as an
ownership-resolution case and the next routed owner case is
`IC-050E60059A34` / `app/services/evidence.py`
Owner context: bounded follow-up under architecture-governance owner case
`IC-F2A8110185EB` for `app/db/models.py`. This milestone targets the
remaining `unclear_ownership` weakness in the public `app.db.models`
compatibility facade after the model-domain splits. It may resolve the owner
case even if architecture-quality still routes `app/db/models.py` as a hotspot,
but only if the remaining surface is converted into an explicit, machine-checked
compatibility contract.

## Purpose

Resolve the remaining ownership ambiguity in `app/db/models.py` by turning it
from an incidental high-fan-in import surface into an explicit, governed
compatibility facade with exact allowed contents, exact public export contract
checks, and a prevention gate that blocks future ORM or facade-growth drift.

## Current Evidence

Live repo signals refreshed after Milestone 2 verification:

```text
uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=561.06
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/agent_task_actions.py,
    app/services/evidence.py,
    app/schemas/agent_tasks.py
  ]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  app.db.models import fan-in=166
  app/db/models.py is not in the top 12 churn hotspots

wc -l app/db/models.py app/db/_model_enums.py
  159 app/db/models.py
  221 app/db/_model_enums.py

python - <<'PY'
from tests.db_model_contract import (
    PUBLIC_DB_MODELS_EXPORT_SYMBOLS,
    PUBLIC_MODEL_IMPORT_SYMBOLS,
    ENUM_SYMBOLS,
    MODEL_SYMBOLS,
)
print(len(PUBLIC_DB_MODELS_EXPORT_SYMBOLS), len(PUBLIC_MODEL_IMPORT_SYMBOLS), len(ENUM_SYMBOLS), len(MODEL_SYMBOLS))
PY
  public_db_models_exports=111
  public_import_symbols=109
  enum_symbols=29
  model_symbols=80

uv run docling-system-improvement-case-summary
  case_count=26
  status_counts.open=24
  status_counts.deployed=1
  status_counts.measured=1
  oldest_open_case_id=IC-050E60059A34
```

Repo-current artifact evidence:

- `config/improvement_cases.yaml` now records `IC-F2A8110185EB` as `deployed`
  at local closeout commit `8340dc0`, with `cause_class: unclear_ownership`
  resolved by the explicit compatibility facade contract for `app/db/models.py`.
- `docs/SESSION_HANDOFF.md` now treats this plan as the completed closeout
  brief for the `app/db/models.py` owner case and routes the next bounded
  follow-up to `IC-050E60059A34` / `app/services/evidence.py`.
- `docs/data_model_boundary_plan.md` records that no further model-family split
  remains under this owner case; the remaining work is compatibility-facade
  governance rather than additional ORM movement.
- `app/db/models.py` is now a 159-line pure compatibility facade. Enum
  ownership lives in `app/db/_model_enums.py`, delayed import bootstrapping
  remains private, and the governed public export surface still covers 111
  symbols.
- `tests/unit/test_db_model_import_compatibility.py` proves import
  compatibility, and `tests/unit/test_db_models_facade_contract.py` constrains
  the allowed structure of `app/db/models.py` itself while blocking the new
  private enum support module from becoming a second public import surface.

## Goal

Resolve the `unclear_ownership` problem for `app/db/models.py` by making the
facade’s allowed contents, export surface, and owner obligations explicit and
machine-checked, while preserving the existing `app.db.models` public import
contract for callers.

## Non-Goals

- Do not move additional ORM model families; the model-domain split sequence is
  already complete for this owner case.
- Do not change table names, columns, indexes, unique constraints, check
  constraint values, foreign keys, or Alembic behavior.
- Do not require broad caller rewrites away from `app.db.models`.
- Do not remove or rename public symbols unless a replacement preserves the
  exact import contract and the plan’s compatibility gate proves it.
- Do not treat lower line count alone as success; this milestone is about
  explicit ownership and prevention, not just smaller files.
- Do not create a second de facto public import path for model enums or ORM
  classes.

## Scope

In scope:

- `app/db/models.py` as the public compatibility facade
- any narrow support module(s) under `app/db/` needed to make the facade more
  explicit while keeping `app.db.models` as the only public caller surface
- public enum ownership and export grouping if moving them is required to make
  the facade contract explicit
- `tests/unit/test_db_model_import_compatibility.py`
- a new dedicated facade-structure gate such as
  `tests/unit/test_db_models_facade_contract.py`
- `tests/db_model_contract.py` if export manifests, counts, or allowed symbol
  groupings need to become more explicit
- architecture-governance rules if a structural facade rule belongs in
  `app/architecture_inspection_rules.py` and its tests/config
- owner-case routing artifacts:
  `config/improvement_cases.yaml`,
  `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`,
  `docs/SESSION_HANDOFF.md`,
  and this milestone plan

Out of scope:

- any runtime semantic-memory behavior changes
- search, evidence, agent-task, audit, or claim-support service refactors
- migration-number changes or schema redesign
- introducing new public caller guidance that bypasses `app.db.models`

## Owner Surfaces

- public facade: `app/db/models.py`
- optional facade-support modules under `app/db/`
- public contract tests:
  `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`,
  and the new facade-structure test file
- architecture governance:
  `app/architecture_inspection_rules.py`,
  `tests/unit/test_architecture_inspection.py`,
  and `config/architecture_inspection.yaml` if a repo-level rule is added
- owner-case registry and routing docs:
  `config/improvement_cases.yaml`,
  `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`,
  `docs/SESSION_HANDOFF.md`

## Placement Rules

- Keep `app/db/models.py` as the only public import path for callers.
- If helper modules are required, place them under `app/db/`; do not place
  facade-support logic under `app/services/`, `tests/`, or ad hoc scripts.
- Do not move callers to helper modules as part of this milestone.
- Put structural facade rules in a dedicated unit test and, if justified, in
  architecture inspection; do not rely on a one-off shell check as the durable
  contract.
- Keep `tests/db_model_contract.py` or a directly paired contract artifact as
  the source of truth for public symbol expectations.
- `app/db/models.py` must not regain direct ORM implementations, mapped
  columns, schema expressions, or SQLAlchemy table declarations.

## Weak-Point Prevention Contract

Weak point forecast:
This milestone could claim ownership clarity while only shuffling imports
around, leaving the facade’s allowed structure implicit. It could also
overcorrect by introducing a second public import path or by forcing caller
rewrites just to satisfy a cleanliness goal.

Owner surface:
`app/db/models.py`, the dedicated facade-structure gate, architecture
inspection rules if added, and the owner-case registry that decides whether
`IC-F2A8110185EB` remains an unresolved ownership case.

Prevention gate:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `uv run pytest -q tests/unit/test_db_models_facade_contract.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Fail threshold:

- `app/db/models.py` still permits silent addition of ORM implementations or
  new public exports without a gate failure
- any public `app.db.models` import breaks or requires caller rewrites
- a helper module becomes a second informal public import path
- the owner case stays `open` for `unclear_ownership` without a narrower,
  explicit routed reason
- verification only proves line-count reduction instead of explicit facade
  ownership

Controlled violation:

- temporarily add a direct ORM class or SQLAlchemy schema import to
  `app/db/models.py` and verify the new facade-structure gate fails
- temporarily add an unexpected public export symbol and verify the import
  contract gate fails

Future-Codex misuse scenario:
The most likely bad follow-up is a future session adding one more enum, alias,
or ORM helper directly into `app/db/models.py` because the file is already a
widely imported convenience surface. This milestone prevents that by making the
allowed facade contents explicit and mechanically enforced before any more
changes land.

## Milestone Sequence

### Milestone 0: Baseline Lock And Contract Framing

Outcome label: `reduced`

Purpose:
Freeze the live facade facts and make the remaining issue explicit before any
implementation work begins.

Scope:

- refresh the current architecture-quality summary, architecture probe fan-in,
  line count, and public symbol counts
- record in durable docs that the remaining issue is `unclear_ownership`, not a
  remaining ORM family split
- choose the governing contract target:
  explicit facade rule, public export manifest, or both

Acceptance:

- the plan, handoff, and owner-case docs agree that the next milestone is a
  compatibility-facade / public-import-contract milestone
- the live baseline records `app/db/models.py` line count, import fan-in, and
  public symbol counts
- the remaining issue is framed in terms of ownership clarity, not generic
  cleanliness language

### Milestone 1: Facade Contract Gate

Outcome label: `reduced`

Purpose:
Create the failing-or-baseline gate that proves what `app/db/models.py` is
allowed to contain and export before any narrowing edits land.

Scope:

- add a dedicated facade-structure test file
- make the exact public export set explicit and testable
- assert that `app/db/models.py` contains only allowed facade content kinds,
  such as import-forwarders, explicitly allowed delayed-import bootstrapping,
  and public enum declarations if they remain in-file
- if appropriate, add or extend an architecture-inspection rule so the repo
  treats facade drift as a first-class boundary violation

Acceptance:

- the repo has a dedicated gate for `app/db/models.py` structure, not only
  import compatibility
- controlled violations fail for unexpected exports and direct ORM/schema
  implementation drift
- the gate passes against the current intended facade shape before broader
  narrowing edits begin

Implemented locally on 2026-05-11:

- added `tests/unit/test_db_models_facade_contract.py` as the dedicated
  facade-structure gate for `app/db/models.py`
- extended `tests/db_model_contract.py` so the facade export contract now
  explicitly includes 111 supported public symbols: the prior 109 import
  symbols plus `DOCUMENT_METADATA_NORMALIZE_SQL` and
  `DOCUMENT_METADATA_TEXTSEARCH_SQL`
- tightened `app/db/models.py` so support imports and delayed-import holders
  are private implementation details while preserving the Milestone 1
  345-line facade footprint
- added controlled-violation coverage proving the gate rejects unexpected
  export additions, direct ORM-class growth, and direct schema-call growth
- left repo-wide architecture inspection unchanged for this milestone because
  the unit gate now captures the exact facade contract more precisely than a
  broad repo rule would

Verified results:

- `git diff --check`: pass
- `uv run ruff check app tests`: pass
- `uv run pytest -q tests/unit/test_db_models_facade_contract.py`:
  `5 passed`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `568 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `335 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1838 passed in 52.05s`
- `uv run docling-system-improvement-case-validate`:
  `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`:
  `case_count=26`, `status_counts.open=25`, `status_counts.measured=1`
- `uv run docling-system-architecture-inspect`:
  `valid=true`, `violation_count=0`
- `uv run docling-system-capability-contracts`:
  `valid=true`, `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=598.8`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`:
  `app.db.models` import fan-in=`166`; the facade is not listed in the top 12
  churn hotspots

### Milestone 2: Facade Ownership Narrowing

Outcome label: `resolved`

Purpose:
Turn the remaining `app/db/models.py` surface into an explicitly governed
compatibility facade with no hidden ownership ambiguity.

Scope:

- narrow `app/db/models.py` so it contains only the minimum compatibility
  surface allowed by the new gate
- if needed, move facade-support definitions such as enum declarations or
  export grouping helpers into narrow `app/db/` support modules while keeping
  `app.db.models` as the only public import path
- update the owner-case registry so `IC-F2A8110185EB` is no longer open for
  `unclear_ownership`, or route any remaining issue under a narrower, different
  cause with explicit evidence

Acceptance:

- `app/db/models.py` is provably a compatibility facade rather than a mixed
  ownership surface
- public imports remain stable for callers
- the owner case is no longer open for `unclear_ownership`
- if architecture-quality still lists `app/db/models.py`, the remaining issue
  is explicitly named and routed as something narrower than unclear ownership

Implemented locally on 2026-05-11:

- moved the remaining 29 public enum definitions out of `app/db/models.py`
  into new private support module `app/db/_model_enums.py`
- reduced `app/db/models.py` from 345 lines to 159 while keeping it as the only
  caller-facing public import surface
- tightened the facade-structure gate so any top-level class definition in
  `app/db/models.py` is now a failure, and only approved support-module imports
  are allowed
- extended import-compatibility coverage so every public enum re-export is
  proven to resolve back to `app/db._model_enums`
- added a private-surface guard that fails if other repo modules begin
  importing `app.db._model_enums` directly
- updated hygiene ownership budgets and owner-case registry state so the
  unclear-ownership case is verified rather than still routed as open

Verified results:

- `git diff --check`: pass
- `uv run ruff check app tests`: pass
- `uv run pytest -q tests/unit/test_db_models_facade_contract.py`:
  `6 passed`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `569 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `335 passed`
- `uv run --extra dev alembic heads`: `0076_claim_feedback_replay_src (head)`
- `uv run --extra dev alembic current`: `0076_claim_feedback_replay_src (head)`
- `uv run --extra dev alembic upgrade head`: pass
- `uv run --extra dev alembic check`: `No new upgrade operations detected.`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1840 passed in 55.47s`
- `uv run docling-system-improvement-case-validate`:
  `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`:
  `case_count=26`, `status_counts.open=24`, `status_counts.deployed=1`,
  `status_counts.measured=1`, `oldest_open_case_id=IC-050E60059A34`
- `uv run docling-system-architecture-inspect`:
  `valid=true`, `violation_count=0`
- `uv run docling-system-capability-contracts`:
  `valid=true`, `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=561.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`:
  `app.db.models` import fan-in=`166`; the facade is not listed in the top 12
  churn hotspots

## Required Implementation Artifacts

- `app/db/models.py`
- any new narrow facade-support module(s) under `app/db/`
- `tests/unit/test_db_models_facade_contract.py`
- updates to `tests/unit/test_db_model_import_compatibility.py`
- updates to `tests/db_model_contract.py` if export manifests or allowed symbol
  groupings become more explicit
- `app/architecture_inspection_rules.py`,
  `tests/unit/test_architecture_inspection.py`, and
  `config/architecture_inspection.yaml` if the structural rule belongs in
  repo-wide architecture governance
- `config/improvement_cases.yaml` owner-case closeout or reroute update

## Required Documentation And Handoff Updates

- update this milestone plan with implementation results and verified metrics
- refresh `docs/data_model_boundary_plan.md`
- refresh `docs/agentic_architecture_index.md`
- refresh `docs/improvement_loop.md`
- refresh `docs/SESSION_HANDOFF.md`
- if `IC-F2A8110185EB` is not fully resolved, route the exact remaining issue
  by cause and owner instead of leaving “facade follow-up” generic

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `uv run pytest -q tests/unit/test_db_models_facade_contract.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

## Acceptance Criteria

- the repo has an explicit, automated contract for what `app/db/models.py` may
  contain and export
- `app/db/models.py` no longer permits direct ORM or schema logic growth
  without a failing gate
- `app.db.models` remains import-compatible for the current public symbol set
  unless a change is explicitly planned and compatibility is re-proven
- `IC-F2A8110185EB` no longer remains open with `cause_class:
  unclear_ownership`
- if the file remains in `top_hotspot_paths`, the owner-case registry and docs
  explain why that is acceptable under the explicit compatibility contract
- the closeout includes implementation, tests, owner-case artifacts, docs, and
  handoff updates in one local atomic commit

## Stop Conditions

- stop if resolving ownership clarity requires breaking the `app.db.models`
  public import contract
- stop if the new gate cannot distinguish allowed facade content from forbidden
  schema/ORM content cleanly enough to be durable
- stop if the milestone drifts into broad caller rewrites or unrelated service
  refactors
- stop if the owner-case reroute cannot be made explicit and artifact-backed
  after the implementation

## Local Commit Closeout Policy

- stage only the verified compatibility-facade milestone slice
- include implementation, tests, owner-case registry updates, routing docs, and
  the canonical handoff update in the same atomic local commit
- do not close the milestone as complete until the local commit exists

## Residual Risks And Next Milestone Routing

- this milestone resolves `IC-F2A8110185EB` as an unclear-ownership case, but
  `app/db/models.py` may continue to appear in architecture-quality routing
  because it is an intentional high-fan-in compatibility facade
- the next architecture milestone should now route to the current oldest open
  case from `config/improvement_cases.yaml`: `IC-050E60059A34` /
  `app/services/evidence.py`
- if architecture-quality still routes `app/db/models.py` after ownership is
  explicit, the next route must name the narrower remaining issue precisely
  rather than reopening `unclear_ownership`
- if the facade-support modules themselves become broad, route a later
  follow-up to those modules by exact owner surface instead of treating
  `app/db/models.py` as the problem again

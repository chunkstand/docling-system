# Hotspot Owner Resolution Plan

Date: 2026-05-09 local / 2026-05-10 UTC
Status: complete locally at `76526ef`; active follow-on execution now lives in `docs/high_value_technical_paydown_milestone_plan.md`, with Milestones 1-5 verified and committed locally and High Value Technical Paydown Milestone 6 next
Owner context: follow-on plan after Residual Weakness Plan Milestone 8 closeout.

## Purpose

Resolve the remaining owner-scoped architecture debt in the current large
hotspot modules:

- `app/db/models.py`
- `app/services/evidence.py`
- `app/services/audit_bundles.py`
- `app/services/claim_support_policy_impacts.py`
- `app/services/retrieval_learning.py`
- `app/services/search.py`

The residual-weakness umbrella milestone is complete. What remains is a
targeted hotspot-reduction sequence that moves one owner concern at a time out
of these broad files without weakening DB, API, retrieval, evidence, or agent
workflow contracts.

## Current Evidence

Status refreshed from live repo commands on 2026-05-10 local / 2026-05-10 UTC:

```text
uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=673.78
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/agent_task_actions.py,
    app/services/evidence.py,
    tests/unit/test_cli.py
  ]

wc -l app/db/models.py app/services/evidence.py app/services/audit_bundles.py app/services/claim_support_policy_impacts.py app/services/retrieval_learning.py app/services/search.py
  5067 app/db/models.py
  6307 app/services/evidence.py
  3306 app/services/audit_bundles.py
  2011 app/services/claim_support_policy_impacts.py
  2482 app/services/retrieval_learning.py
  2851 app/services/search.py

wc -l app/services/claim_support_replay_alert_promotions.py app/services/retrieval_learning_replay_alert_sources.py app/services/search_ranking.py
  1536 app/services/claim_support_replay_alert_promotions.py
   578 app/services/retrieval_learning_replay_alert_sources.py
   467 app/services/search_ranking.py

uv run docling-system-hygiene-check
  inherited budget debt includes:
    app/db/models.py owner=IC-F2A8110185EB
    app/services/agent_task_actions.py owner=IC-A1E186A34097
    app/services/evidence.py owner=IC-050E60059A34
    app/services/audit_bundles.py owner=IC-2112B1ADC5E8
    app/services/claim_support_policy_impacts.py owner=IC-E2270F89B397
    app/services/claim_support_replay_alert_promotions.py owner=IC-E2270F89B397
    app/services/retrieval_learning.py owner=IC-0D58F1624037
    app/services/search.py owner=IC-1D03DBFE8492
  new hygiene regressions: none

uv run docling-system-improvement-case-summary
  case_count=26
  status_counts.open=25
  status_counts.measured=1
  measured_case_count=8
  oldest_open_case_id=IC-F2A8110185EB
```

Current explicit improvement-case owners already exist for:

- `app/db/models.py`: `IC-F2A8110185EB`
- `app/services/evidence.py`: `IC-050E60059A34`
- `app/services/audit_bundles.py`: `IC-2112B1ADC5E8`
- `app/services/claim_support_policy_impacts.py`: `IC-E2270F89B397`
- `app/services/retrieval_learning.py`: `IC-0D58F1624037`
- `app/services/search.py`: `IC-1D03DBFE8492`
- `app/ui/app.js`: `IC-1B643BA0AD90` in the active follow-on paydown plan

Milestone 0 owner bootstrap is now complete locally: `config/improvement_cases.yaml`
contains explicit owner cases for `audit_bundles` and `retrieval_learning`, and
`config/hygiene_policy.yaml` now routes both surfaces through those case IDs
instead of `owner_milestone=residual-weakness-milestone-2`.

## Goal

Reduce hotspot centrality and make ownership explicit without weakening the
repo's existing architecture and runtime contracts:

- convert every targeted surface to explicit owner-scoped governance
- reduce size and hotspot risk one bounded concern at a time
- preserve public facades, DB metadata, CLI names, API contracts, and retrieval
  behavior while moving code into focused owner modules
- keep hotspot prevention and hygiene ratchets green through every split
- close each reduction slice as an atomic local commit with updated docs and
  handoff state

## Non-Goals

- No microservice extraction.
- No broad rewrite of evidence, retrieval, or claim-support subsystems.
- No schema redesign or table rename unless a later milestone explicitly scopes
  and verifies it.
- No API, CLI, artifact, or public import contract breakage as a side effect of
  modularization.
- No umbrella sweep that edits multiple hotspot families in one milestone
  without a shared owner contract.
- No silent reassignment of inherited debt to a milestone name when a case ID
  should own it.

## Scope

In scope:

- improvement-case ownership bootstrap for `audit_bundles` and
  `retrieval_learning`
- focused owner-module extraction behind existing facades
- model-domain continuation for `app/db/models.py`
- evidence and audit-bundle concern splits
- claim-support policy-impact concern splits
- retrieval-learning concern splits
- search concern splits
- docs, improvement-case registry, hygiene ownership, and handoff updates
  required to prove each slice

Out of scope:

- new user-facing product features
- unrelated UI or agent-task work
- court-grade readiness expansion beyond preserving the already-green state
- changing canonical JSON, derived YAML, active-run promotion, or evaluation
  source-of-truth rules

## Owner Surfaces

- `app/db/models.py`
  - primary owner path: `app/db/model_domains/`
  - compatibility harness: `tests/db_model_contract.py`,
    `tests/unit/test_db_model_import_compatibility.py`,
    `tests/integration/test_db_model_metadata.py`
  - current supporting plan: `docs/data_model_boundary_plan.md`
- `app/services/evidence.py`
  - primary owner path: `app/services/evidence_*.py`
  - likely adjacent owners: `app/services/evidence_common.py`,
    `app/services/evidence_records.py`,
    `app/services/evidence_provenance.py`,
    `app/services/evidence_search_*.py`,
    `app/services/evidence_operator_runs.py`,
    `app/services/evidence_task_payloads.py`
- `app/services/audit_bundles.py`
  - primary owner path: new focused `app/services/audit_bundle_*.py` modules
    or existing adjacent evidence/report owners when the concern naturally fits
- `app/services/claim_support_policy_impacts.py`
  - primary owner path: focused `app/services/claim_support_policy_*.py`
    modules and existing adjacent `claim_support_*` owners
- `app/services/retrieval_learning.py`
  - primary owner path: focused `app/services/retrieval_learning_*.py` modules
    and existing replay/training-set owners
- `app/services/search.py`
  - primary owner path: `app/services/search_*.py`
  - current adjacent owners already exist for replay, release, legibility, and
    query-feature concerns
- governance and tracking surfaces:
  `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`,
  `docs/improvement_loop.md`, `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`, and this plan

## Placement Rules

- Keep each current broad file as a compatibility facade until callers can stay
  import-stable through re-exports or forwarding functions.
- New implementation must land in an existing owner family when one exists:
  `app/db/model_domains/`, `app/services/evidence_*.py`,
  `app/services/search_*.py`, `app/services/claim_support_*.py`.
- When no owner family exists yet, create one narrow module family instead of
  adding more helpers to the hotspot file.
- Place new tests in focused files near the moved concern. Do not grow
  broad hotspot test files just because they already exist.
- Every milestone that changes `config/improvement_cases.yaml` or
  `config/hygiene_policy.yaml` must validate both files and keep ownership
  aligned.
- `app/services/audit_bundles.py` and `app/services/retrieval_learning.py`
  may not remain owned only by `residual-weakness-milestone-2` after the
  bootstrap milestone in this plan.

## Weak-Point Prevention Contract

Weak point forecast: future work could convert these broad files into a series
of facade-preserving partial wins without ever making ownership explicit,
continue leaving `audit_bundles` and `retrieval_learning` under milestone-owned
debt, or move code into new side modules that immediately become the next
untracked hotspot. Another likely failure is a runtime-sensitive split that
claims success from docs or focused tests while replay, readiness, or DB
contracts quietly drift.

Owner surface: each hotspot file owns its compatibility facade; the focused
module families listed in `Owner Surfaces` own the extracted implementation;
`config/improvement_cases.yaml` and `config/hygiene_policy.yaml` own explicit
debt routing; this plan, `docs/agentic_architecture_index.md`, and
`docs/SESSION_HANDOFF.md` own the durable execution sequence and current
routing.

Freshness check: rerun `uv run docling-system-architecture-quality-report
--summary`, `uv run docling-system-hygiene-check`, and
`uv run docling-system-improvement-case-summary` before each milestone closes.
For any runtime-facing milestone, rerun
`uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
and `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene` in the
same closeout window. If the closeout docs cite older values than the current
commands emit, the milestone fails and the docs must be refreshed before
commit.

| Weak point | Owner surface | Prevention gate | Fail threshold | Controlled violation |
| --- | --- | --- | --- | --- |
| Ownerless or milestone-owned debt persists | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml` | `uv run docling-system-improvement-case-validate` and `uv run docling-system-hygiene-check` | `audit_bundles` or `retrieval_learning` still depend on `owner_milestone=residual-weakness-milestone-2` after bootstrap | Add a case-less ratchet entry for `audit_bundles` in a fixture or temp edit and verify validation fails |
| Split breaks public compatibility | hotspot file plus focused compatibility tests | focused unit/integration tests, capability contracts, DB metadata checks where applicable | any public import, CLI command, DB metadata contract, or API payload changes unintentionally | import moved symbols through the old facade in tests and verify they still resolve |
| New logic lands back in the hotspot file | hotspot file and owner-module family | `uv run docling-system-hotspot-prevention-check --strict` | any milestone diff adds blocked implementation to a known hotspot instead of the owner module | add a private helper to the hotspot in a negative fixture and verify strict mode fails |
| A new owner module just becomes the next giant dump file | new `*_*.py` owner modules, hygiene policy, architecture probe | `uv run docling-system-hygiene-check` and architecture probe line-count review | newly introduced owner module exceeds the target file budget or absorbs unrelated concerns in the same milestone | introduce an oversized mixed-concern fixture module and verify the budget or review rule would block it |
| Runtime-sensitive split claims success from docs only | runtime-facing services and DB model domains | `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` plus surface-specific gates | any service split closes without DB-backed integration verification when runtime paths were touched | comment out the runtime suite in a trial run or change runtime code without running integration gates |
| Retrieval-ledger model split drifts vector, TSVECTOR, or FK contracts | `app/db/models.py`, `app/db/model_domains/retrieval_interactions.py`, `tests/db_model_contract.py`, `tests/integration/test_db_model_metadata.py` | import-compatibility tests, metadata/create-all checks, Alembic drift checks, and the full DB-backed suite | any retrieval-ledger index, unique constraint, computed column, vector dimension, or cross-table FK changes unintentionally | remove a required retrieval index or stop re-exporting one moved model in a controlled diff and verify the metadata/import harness fails |
| Search or retrieval quality regresses during modularization | `app/services/search.py`, `app/services/retrieval_learning.py`, replay/eval surfaces | replay, harness, readiness, and full test gates | replay, harness, or readiness signals degrade after a split | run a targeted search change without replay coverage and treat any drop in the governed outputs as a blocking failure |

Future-Codex misuse scenario: the likely failure is adding one more helper to
`app/services/evidence.py`, `app/services/search.py`, or
`app/services/retrieval_learning.py` because the module already has context and
imports. This plan prevents that by forcing explicit owner-case routing, using
existing owner module families, and keeping hotspot prevention strict on every
slice.

## Milestone Sequence

### Milestone 0: Owner Bootstrap And Baseline Lock

Purpose: convert the selected surfaces into explicit owner-scoped work before
further code movement.

Scope:

- Refresh architecture quality, hygiene, probe, and improvement-case summary
  evidence.
- Add explicit improvement cases for `app/services/audit_bundles.py` and
  `app/services/retrieval_learning.py`.
- Update `config/hygiene_policy.yaml` so those surfaces use `owner_case_id`
  instead of `owner_milestone=residual-weakness-milestone-2`.
- Record this plan in the architecture index and handoff.

Acceptance:

- `config/improvement_cases.yaml` contains explicit open owner cases for
  `audit_bundles` and `retrieval_learning`.
- `uv run docling-system-hygiene-check` shows those surfaces owned by case IDs,
  not by the old residual milestone name.
- `uv run docling-system-improvement-case-summary` remains valid and shows the
  updated open-case routing.

Status update:

- Implemented and verified locally on 2026-05-09 MDT / 2026-05-10 UTC.
- Closed by commit `33c7855` (`architecture: complete hotspot owner milestone 0 bootstrap`).
- New owner cases: `IC-2112B1ADC5E8` for `app/services/audit_bundles.py` and
  `IC-0D58F1624037` for `app/services/retrieval_learning.py`.
- Milestone 1 is complete locally; the next routed implementation slice is
  Milestone 2 unless a narrower verified evidence/audit split replaces the
  current candidate.

### Milestone 1: `app/db/models.py` Domain Continuation

Purpose: continue shrinking the top hotspot by moving one ORM domain behind the
existing compatibility facade.

Scope:

- Resume the next documented domain split from
  `docs/data_model_boundary_plan.md`, starting with `document_artifacts` unless
  a narrower verified candidate is found.
- Preserve all current `app.db.models` imports, table metadata, indexes,
  constraints, relationship strings, and Alembic compatibility.

Acceptance:

- moved domain classes live under `app/db/model_domains/`
- `app/db/models.py` re-exports the moved symbols without caller breakage
- DB metadata, Alembic, and full integration gates remain green
- architecture quality or hygiene evidence shows narrower ownership or reduced
  hotspot centrality for the surface

Status update:

- Implemented locally as the `document_artifacts` domain split.
- Closed by commit `060b537` (`architecture: complete hotspot owner milestone 1 document-artifacts`).
- Moved `DocumentRunEvaluation`, `DocumentRunEvaluationQuery`,
  `DocumentChunk`, `DocumentTable`, `DocumentTableSegment`, and
  `DocumentFigure` into `app/db/model_domains/document_artifacts.py`.
- Reduced `app/db/models.py` from 5,800 lines to 5,537 lines, ratcheted the
  hygiene ceiling to match, and lowered the architecture-quality
  `max_hotspot_risk_score` to `681.91`.
- The next routed implementation slice is Milestone 2: Evidence And Audit
  Bundle Split Pack.

### Milestone 2: Evidence And Audit Bundle Split Pack

Purpose: reduce the central evidence and audit assembly hotspots without
breaking audit bundle or evidence export behavior.

Scope:

- Move one evidence concern at a time out of `app/services/evidence.py` into a
  focused `evidence_*.py` owner.
- Introduce a narrow owner family for `app/services/audit_bundles.py` and move
  one coherent concern at a time behind the existing call surface.
- Keep technical-report, evidence-package, and audit-bundle behavior stable.

Acceptance:

- `app/services/evidence.py` and `app/services/audit_bundles.py` each lose at
  least one owner concern to focused modules
- focused tests cover the moved concern through the original facade or entry
  surface
- hotspot prevention and hygiene remain green with no touched-file debt growth

Status update:

- Implemented locally as a behavior-preserving evidence/audit owner split.
- Closed by commit `a0bd36b` (`architecture: complete hotspot owner milestone 2 evidence-audit`).
- Added `app/services/evidence_manifest_traces.py` for the technical-report
  evidence trace graph build, persistence, and integrity concern while keeping
  `app/services/evidence.py` as the compatibility facade.
- Added `app/services/audit_bundle_replay_alert_corpus.py` for retrieval
  training replay-alert corpus lineage payload assembly and staleness checks
  while keeping `app/services/audit_bundles.py` as the entry surface.
- Reduced `app/services/evidence.py` from 8,076 lines to 7,143 and
  `app/services/audit_bundles.py` from 3,862 lines to 3,306.
- Ratcheted `config/hygiene_policy.yaml` so
  `app/services/evidence_manifest_traces.py` is governed under
  `owner_case_id: IC-050E60059A34` with `ratchet_max_lines: 980`.
- Focused integration coverage passed on
  `test_technical_report_harness_roundtrip`,
  `test_retrieval_training_audit_bundle_flags_tampered_replay_alert_corpus_lineage`,
  and
  `test_release_audit_bundle_refreshes_stale_replay_alert_corpus_training_bundle`.
- Full DB-backed verification, architecture inspection, hotspot prevention,
  hygiene, evaluation-data readiness, and agent-trace review all passed.
- The next routed implementation slice is Milestone 3: Claim Support Policy
  Impacts Split.

### Milestone 3: Claim Support Policy Impacts Split

Purpose: break up the policy-impact hotspot into narrower claim-support owner
surfaces.

Scope:

- separate policy-diff computation, payload assembly, and reporting or
  persistence concerns from `app/services/claim_support_policy_impacts.py`
- keep existing claim-support policy contracts and evaluation behavior stable

Acceptance:

- at least one coherent concern moves into focused `claim_support_policy_*.py`
  or adjacent owner modules
- focused tests and runtime integration verification pass
- the improvement case and hygiene owner for the file are updated with the
  verified reduction result

Status update:

- Implemented and verified locally as the replay-alert fixture coverage owner
  split.
- Closed by commit `afc324a` (`architecture: complete hotspot owner milestone 3 claim-support`).
- Added `app/services/claim_support_replay_alert_promotions.py` and moved the
  replay-alert fixture coverage summary, candidate derivation, fixture
  promotion, and waiver-closure governance workflow behind the existing
  `app/services/claim_support_policy_impacts.py` compatibility surface.
- Reduced `app/services/claim_support_policy_impacts.py` from 3,477 lines to
  2,011 while ratcheting the file to `ratchet_max_lines: 2011` and
  `ratchet_max_private_helpers: 42`.
- Added a hygiene ratchet entry for
  `app/services/claim_support_replay_alert_promotions.py` under
  `owner_case_id: IC-E2270F89B397` with `ratchet_max_lines: 1536` and
  `ratchet_max_private_helpers: 24`.
- Updated `config/improvement_cases.yaml` so
  `IC-E2270F89B397` records the verified Milestone 3 reduction result.
- Full DB-backed verification, architecture inspection, hotspot prevention,
  hygiene, evaluation-data readiness, and agent-trace review all passed.
- The next routed implementation slice is Milestone 5: Search Core Split
  Continuation.

### Milestone 4: Retrieval Learning Split

Purpose: turn `app/services/retrieval_learning.py` into a compatibility surface
over narrower training-data and judgment-set owners.

Scope:

- separate at least one concern such as judgment-set materialization,
  hard-negative selection, replay-source conversion, or training-example export
- keep replay, learning materialization, and evaluation contracts stable

Acceptance:

- `retrieval_learning` has an explicit case owner and at least one focused
  `retrieval_learning_*.py` owner module
- targeted retrieval-learning tests and full DB-backed integration tests pass
- readiness remains `court_grade_ready=true`

Status update:

- Implemented and verified locally as the replay-alert corpus source owner
  split.
- Closed by commit `13e8b1c` (`architecture: complete hotspot owner milestone 4 retrieval-learning`).
- Added `app/services/retrieval_learning_replay_alert_sources.py` and moved the
  replay-alert corpus lineage validation, judgment materialization, and hard-negative
  construction concern behind the existing `app/services/retrieval_learning.py`
  compatibility surface.
- Reduced `app/services/retrieval_learning.py` from 3,028 lines to 2,482 while
  ratcheting the file to `ratchet_max_lines: 2482` and
  `ratchet_max_private_helpers: 46`.
- Added a hygiene budget entry for
  `app/services/retrieval_learning_replay_alert_sources.py` under
  `owner_case_id: IC-0D58F1624037` with `max_lines: 578` and
  `max_private_helpers: 10`.
- Updated `config/improvement_cases.yaml` so `IC-0D58F1624037` records the
  verified Milestone 4 reduction result.
- Focused retrieval-learning tests, full DB-backed integration verification,
  architecture inspection, hotspot prevention, hygiene, evaluation-data
  readiness, and agent-trace review all passed.
- The next routed implementation slice is Milestone 5: Search Core Split
  Continuation.

### Milestone 5: Search Core Split Continuation

Purpose: continue shrinking `app/services/search.py` by moving one coherent
runtime concern behind the existing search facade.

Scope:

- move one concern such as result hydration, ranking helpers, telemetry payload
  assembly, or release/readiness composition into focused `search_*.py` owners
- preserve mixed-search behavior, replay behavior, and current release gates

Acceptance:

- `app/services/search.py` delegates one more coherent concern to a focused
  owner module family
- search, replay, harness, and readiness signals remain green
- hotspot prevention blocks any new helper growth in `app/services/search.py`

Status update:

- Implemented and verified locally as the search-ranking owner split.
- Added `app/services/search_ranking.py` and moved ranking helpers, reranking,
  hybrid-result merging, result rendering, and ranked-result utility types
  behind the existing `app/services/search.py` compatibility surface.
- Reduced `app/services/search.py` from 3,250 lines to 2,851 while ratcheting
  the file to `ratchet_max_lines: 2851`; the facade still carries 53 private
  helpers under an aligned helper ceiling of 65.
- Added a hygiene budget entry for `app/services/search_ranking.py` under
  `owner_case_id: IC-1D03DBFE8492` with `max_lines: 467` and
  `max_private_helpers: 0`.
- Updated `config/improvement_cases.yaml` so `IC-1D03DBFE8492` records the
  verified Milestone 5 reduction result.
- Focused search tests, runtime integration verification, full DB-backed
  verification, architecture inspection, hotspot prevention, hygiene,
  evaluation-data readiness, and agent-trace review all passed.
- The next routed implementation slice is Milestone 6: Closeout And Case
  Lifecycle Alignment.

### Milestone 6: Closeout And Case Lifecycle Alignment

Purpose: close the sequence with aligned docs, owner cases, and verified
follow-up routing.

Scope:

- update this plan, `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`, and affected boundary or domain plans
- update improvement-case status, deployment refs, and metric evidence for any
  surfaces that achieved verified reductions
- confirm no targeted surface remains routed only through a milestone-owned debt
  label when a case owner should exist

Acceptance:

- every targeted surface has explicit owner routing
- every completed split milestone records its commit hash and verified result in
  the handoff
- remaining debt is either accepted with a case owner or routed to the next
  hotspot milestone explicitly

Status update:

- Implemented and verified locally as the plan closeout and case-lifecycle
  alignment pass.
- Updated `config/improvement_cases.yaml` so the six targeted hotspot owner
  cases now carry the correct committed deployment refs and post-milestone
  measurement evidence for Milestones 1-5.
- Corrected the stale owner-case payload on `IC-F2A8110185EB`, which had been
  carrying the Milestone 3 claim-support measurement instead of the Milestone 1
  `app/db/models.py` reduction.
- Confirmed `config/hygiene_policy.yaml` routes all six targeted surfaces
  through explicit `owner_case_id` entries; none of the selected hotspots still
  rely on `owner_milestone=residual-weakness-milestone-2`.
- Added the missing Milestone 3 commit reference to
  `docs/SESSION_HANDOFF.md` and aligned this plan, the architecture index, and
  the handoff to one completed-sequence state.
- The hotspot owner milestone sequence is now complete locally. The follow-on
  High Value Technical Paydown plan has since verified and committed
  Milestones 1-5, so the current routed owner-scoped implementation should
  resume with `IC-1B643BA0AD90` / `app/ui/app.js`.

### Milestone 7: Retrieval Interaction Model Split

Status: historical carry-forward scope only. This retrieval-interaction split
has now been verified locally through
`docs/high_value_technical_paydown_milestone_plan.md` Milestone 1, and the
active follow-on has advanced through Milestone 2 evidence work and now routes
to the Milestone 3 agent-action split.

Purpose: resume the top-hotspot reduction path by moving the live
search-and-chat interaction ledger rows out of `app/db/models.py` and into a
focused retrieval owner module behind the existing public compatibility facade.

Scope:

- add `app/db/model_domains/retrieval_interactions.py`
- move the live retrieval interaction rows:
  `SearchRequestRecord`,
  `SearchRequestResult`,
  `RetrievalEvidenceSpan`,
  `RetrievalEvidenceSpanMultiVector`,
  `SearchRequestResultSpan`,
  `SearchFeedback`,
  `ChatAnswerRecord`, and
  `ChatAnswerFeedback`
- preserve `app.db.models` import compatibility via re-exports
- extend the shared metadata contract for the moved retrieval-interaction
  tables, including required indexes, unique constraints, exact column
  ordering, vector dimensions, and computed TSVECTOR fields
- ratchet `config/hygiene_policy.yaml` to the new verified `app/db/models.py`
  line count and add a focused budget entry for the new owner module

Out of scope for this milestone:

- `SearchReplayRun`, `SearchReplayQuery`, harness release rows, retrieval
  learning rows, or audit bundle rows
- search ranking or service-layer behavior changes
- API, CLI, or user-facing feature work

Acceptance:

- `app/db.models` still exports the moved retrieval-interaction symbols and
  `tests/unit/test_db_model_import_compatibility.py` proves the old imports
  remain valid
- the metadata harness covers the moved retrieval-interaction tables and
  required retrieval indexes, unique constraints, and computed/vector column
  contracts
- `uv run --extra dev alembic check` reports no unexpected drift and
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
  remains green
- full DB-backed verification stays green, including
  `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
  with `failed_gate_count=0`
- `app/db/models.py` shrinks below the current 5,537-line ratchet ceiling and
  `uv run docling-system-architecture-quality-report --summary` does not raise
  hotspot count or max hotspot risk

Planned implementation notes:

- keep this as one bounded ORM-owner slice, not a whole retrieval-domain move
- prefer moving the live search/chat ledger rows first because they form a
  coherent contract cluster and reduce the highest-value active hotspot without
  pulling replay, release, or training governance into the same milestone
- defer the remaining retrieval ORM surfaces to follow-on milestones after this
  split proves the new owner-module pattern

## Required Implementation Artifacts

- focused owner modules under `app/db/model_domains/`, `app/services/evidence_*.py`,
  `app/services/audit_bundle_*.py`, `app/services/claim_support_policy_*.py`,
  `app/services/retrieval_learning_*.py`, or `app/services/search_*.py`
- focused tests for each moved concern
- updated improvement-case entries and hygiene ownership where applicable
- refreshed domain or boundary plans for touched surfaces

## Required Documentation And Handoff Updates

Every milestone in this plan must update:

- this plan
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`

Update when affected:

- `docs/data_model_boundary_plan.md`
- `docs/improvement_loop.md`
- `docs/architecture_boundaries.md`
- `README.md`
- `SYSTEM_PLAN.md`

## Required Verification Gates

Every milestone:

```bash
git diff --check
uv run ruff check app tests
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-hygiene-check
```

When `config/improvement_cases.yaml` or `config/hygiene_policy.yaml` changes:

```bash
uv run docling-system-improvement-case-validate
uv run docling-system-improvement-case-summary
```

Architecture split milestones:

```bash
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
```

Model-domain milestones:

```bash
uv run pytest -q tests/unit/test_db_model_import_compatibility.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py
uv run --extra dev alembic heads
uv run --extra dev alembic current
uv run --extra dev alembic upgrade head
uv run --extra dev alembic check
```

Runtime, retrieval, evidence, audit, claim-support, or search milestones:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json
uv run docling-system-agent-trace-review --limit 5 --skip-hygiene
```

## Acceptance Criteria

This plan is complete only when:

- all six selected surfaces have explicit owner-scoped routing
- `audit_bundles` and `retrieval_learning` no longer rely on
  `owner_milestone=residual-weakness-milestone-2`
- each targeted hotspot has either a lower current burden
  (line count, helper count, hotspot risk, or fan-out) or a narrower verified
  owner contract than the baseline recorded here
- public facades, DB metadata, runtime behavior, replay governance, and
  evaluation readiness remain intact
- every milestone closes with updated docs, handoff, and an atomic local commit

## Stop Conditions

Stop and update the handoff before continuing if:

- a split requires cross-domain contract changes that do not fit the current
  milestone
- a new owner module cannot be defined narrowly enough to avoid simply moving
  the hotspot elsewhere
- DB metadata, Alembic, replay, readiness, or trace-review gates fail and the
  failure cannot be isolated to the milestone slice
- unrelated dirty files prevent isolating the milestone into a single commit
- architecture quality evidence becomes stale or contradictory during the work

## Local Commit Closeout Policy

Each milestone closes as one local commit after verification passes:

```bash
git status --short
git diff --stat
git add <milestone files only>
git diff --cached --stat
git commit -m "<area>: complete hotspot owner milestone <N> <short-name>"
git status -sb
```

Stage only the verified milestone slice. Leave unrelated dirty or untracked
files unstaged. Push remains separate and only happens when explicitly
requested.

## Residual Risks And Next Routing

Residual risks during this plan:

- some files may require multiple milestones because they contain more than one
  owner concern
- architecture quality may not move every targeted surface into the top-hotspot
  list at the same time, so hygiene debt and line-count evidence must also be
  used
- remaining small Python cycle components are not in scope for this plan unless
  one of these hotspot splits naturally removes them

If a targeted surface stabilizes with clear owner modules but still exceeds
budget, route the residual debt through its improvement case rather than
reopening a broad umbrella milestone. If a new cross-cutting hotspot family
appears, create a new focused plan instead of expanding this one beyond the six
selected surfaces.

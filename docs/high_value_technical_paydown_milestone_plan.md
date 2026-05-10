# High Value Technical Paydown Milestone Plan

Date: 2026-05-10 local / 2026-05-10 UTC
Status: active locally with Milestones 1-5 verified and committed; next
implementation slice is Milestone 6 UI monolith split
Owner context: new standalone paydown plan written after the Hotspot Owner
Resolution sequence closed locally through Milestone 6. This plan does not add
new milestones to the prior hotspot-owner plan; it starts a fresh,
high-value debt program from the current live repo state.

## Purpose

Resolve the highest-value remaining technical and mechanical debt identified in
the current architecture review:

- keep `audit_bundles` and `retrieval_learning` on explicit owner-case routing
  rather than milestone-owned debt
- continue the `app/db/models.py` hotspot reduction behind the current public
  compatibility facade
- keep shrinking `app/services/evidence.py` by owner family
- reduce `app/services/agent_task_actions.py` fan-out through additional
  `app/services/agent_actions/*` extraction
- split oversized hotspot tests and the browser UI monolith so review and
  change costs fall with implementation complexity

This plan treats the owner-case conversion for `audit_bundles` and
`retrieval_learning` as a verified baseline that must remain true; it does not
reopen the already-closed hotspot-owner sequence.

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
    app/schemas/agent_tasks.py
  ]

uv run docling-system-hygiene-check
  inherited budget debt includes:
    app/db/models.py owner=IC-F2A8110185EB
    app/services/agent_task_actions.py owner=IC-A1E186A34097
    app/services/audit_bundles.py owner=IC-2112B1ADC5E8
    app/services/evidence.py owner=IC-050E60059A34
    app/services/retrieval_learning.py owner=IC-0D58F1624037
  new hygiene regressions: none

uv run docling-system-improvement-case-summary
  case_count=26
  status_counts.open=25
  status_counts.measured=1
  measured_case_count=13
  oldest_open_case_id=IC-F2A8110185EB

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  top hotspot app/db/models.py score=364824
  app/services/evidence.py score=302736
  app/services/agent_task_actions.py score=162014
  app/ui/app.js score=108375
  app/services/agent_task_actions.py fan-out=36
  Python cycle components=3

wc -l app/db/models.py app/services/evidence.py app/services/agent_task_actions.py tests/unit/test_cli.py tests/unit/test_cli_agent_tasks.py tests/unit/test_agent_task_actions.py tests/integration/test_claim_support_judge_evaluation_roundtrip.py tests/unit/test_search_api.py tests/unit/test_search_api_harnesses.py tests/unit/test_documents_api.py tests/unit/test_documents_api_semantics.py app/ui/app.js
   5067 app/db/models.py
   6307 app/services/evidence.py
   2746 app/services/agent_task_actions.py
    424 tests/unit/test_cli.py
    622 tests/unit/test_cli_agent_tasks.py
    417 tests/unit/test_agent_task_actions.py
    337 tests/integration/test_claim_support_judge_evaluation_roundtrip.py
    436 tests/unit/test_search_api.py
    764 tests/unit/test_search_api_harnesses.py
    613 tests/unit/test_documents_api.py
    394 tests/unit/test_documents_api_semantics.py
   4335 app/ui/app.js
```

Current routing notes:

- `app/services/audit_bundles.py` already routes through
  `IC-2112B1ADC5E8`.
- `app/services/retrieval_learning.py` already routes through
  `IC-0D58F1624037`.
- `app/services/agent_task_actions.py`, `tests/unit/test_cli.py`,
  `tests/unit/test_agent_task_actions.py`,
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`,
  `tests/unit/test_search_api.py`, and `tests/unit/test_documents_api.py`
  already have explicit improvement cases in `config/improvement_cases.yaml`.
- `app/ui/app.js` now routes through explicit improvement case
  `IC-1B643BA0AD90`.
- High Value Technical Paydown Milestone 1 is now committed locally under
  `IC-F2A8110185EB`; `app/db/models.py` remains the compatibility facade while
  the retrieval-interaction owner surface now lives in
  `app/db/model_domains/retrieval_interactions.py`.
- High Value Technical Paydown Milestone 2 is now committed locally under
  `IC-050E60059A34`; the technical-report derivation/export owner family now
  lives in `app/services/evidence_technical_report_exports.py` while
  `app/services/evidence.py` remains the compatibility facade at 6,307
  architecture-probe lines.
- High Value Technical Paydown Milestone 3 is now committed locally under
  `IC-A1E186A34097`; the technical-report action definition family now lives
  in `app/services/agent_actions/report_actions.py` while
  `app/services/agent_task_actions.py` remains the compatibility registry
  entrypoint at 2,746 architecture-probe lines with fan-out 36.
- High Value Technical Paydown Milestone 4 is now committed locally under
  `IC-FD18EE2D3309`, `IC-03D7EFA03213`, and `IC-23F2C79C8AA7`; the CLI,
  search API, and document API hotspot tests now route through focused owner
  files while the original monoliths are reduced to 424, 436, and 613 lines.
- High Value Technical Paydown Milestone 5 is now committed locally under
  `IC-934588120F94` and `IC-40CA7C1FFA84`; the agent-task action and
  claim-support judge roundtrip hotspot tests now route through focused owner
  files, the residual replay-alert change-impact monolith now routes through
  activation, prevalidation, promotion, and governance files, and the
  original monoliths remain reduced to 417 and 337 lines.
- the active follow-up after the committed Milestone 5 closeout is Milestone 6:
  UI monolith split for `IC-1B643BA0AD90`.

## Goal

Retire the highest-value remaining debt in the current repo without weakening
runtime safety, public compatibility surfaces, or the architecture gates that
already govern the system.

Success means:

- no selected surface depends on milestone-owned debt routing
- `app/db/models.py`, `app/services/evidence.py`, and
  `app/services/agent_task_actions.py` each lose one bounded concern behind
  stable facades
- the major oversized hotspot tests are split along owner boundaries instead of
  remaining monolithic assertion dumps
- `app/ui/app.js` stops being the sole JavaScript implementation surface for
  the shipped operator UI
- architecture, hygiene, replay/readiness, and DB-backed verification remain
  green throughout

## Non-Goals

- No microservice extraction.
- No schema redesign, table rename, or enum value change as part of the ORM
  hotspot reduction.
- No broad rewrite of the evidence or agent-task subsystems.
- No user-facing UI redesign; the UI milestone is structural and maintainability
  focused.
- No redoing already-closed owner-case conversion work merely to restate it in
  a new plan.
- No umbrella milestone commit that mixes multiple unrelated hotspot families
  without a shared owner contract.

## Scope

In scope:

- baseline validation that `audit_bundles` and `retrieval_learning` remain
  explicitly owner-routed
- explicit owner-case bootstrap for `app/ui/app.js`
- `app/db/models.py` retrieval-interaction domain split
- one additional `app/services/evidence.py` owner-family split
- one additional `app/services/agent_task_actions.py` action-family split
- focused hotspot-test decomposition aligned to owner surfaces
- UI module decomposition for `app/ui/app.js`
- the docs, improvement-case registry, hygiene policy, and handoff updates
  needed to keep the work durable

Out of scope:

- unrelated semantics, downloader, or parser changes
- new product features in the operator UI
- changing API capabilities or public route families unless a touched milestone
  requires a compatibility-preserving internal rewire
- reopening the old hotspot-owner milestone numbering

## Owner Surfaces

- governance and routing:
  `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`,
  `docs/SESSION_HANDOFF.md`, and this plan
- ORM hotspot:
  `app/db/models.py`, `app/db/model_domains/`, `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`,
  `docs/data_model_boundary_plan.md`
- evidence hotspot:
  `app/services/evidence.py`, `app/services/evidence_*.py`,
  `tests/unit/test_evidence_*.py`,
  `tests/integration/test_technical_report_harness_roundtrip.py`,
  `tests/integration/test_retrieval_learning_ledger.py`
- agent-task action hotspot:
  `app/services/agent_task_actions.py`, `app/services/agent_actions/`,
  `tests/unit/test_agent_task_actions.py`,
  `tests/unit/test_agent_task_action_lookup.py`
- test hotspot pack:
  `tests/unit/test_cli.py`,
  `tests/unit/test_agent_task_actions.py`,
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`,
  `tests/unit/test_search_api.py`,
  `tests/unit/test_documents_api.py`
- UI hotspot:
  `app/ui/app.js`, `app/ui/*.html`, `app/ui/styles.css`, and new
  `app/ui/modules/*.js` owners plus new focused UI smoke tests

## Placement Rules

- Keep `app/db/models.py`, `app/services/evidence.py`, and
  `app/services/agent_task_actions.py` as compatibility facades until a later
  deliberate contract change says otherwise.
- New backend implementation must land in an existing owner family when one
  exists:
  `app/db/model_domains/`, `app/services/evidence_*.py`,
  `app/services/agent_actions/*.py`.
- New test files must follow the production owner split. Do not create one new
  giant “split tests” file.
- UI decomposition must create a real module family under `app/ui/modules/`;
  `app/ui/app.js` should become bootstrap and composition glue, not another
  monolith with helpers merely moved around.
- Every milestone that changes `config/improvement_cases.yaml` or
  `config/hygiene_policy.yaml` must validate both and keep routing aligned.
- Runtime-facing milestones must preserve evaluation readiness and replay
  signals. Docs-only success is not valid for these slices.

## Weak-Point Prevention Contract

Weak point forecast: this program could devolve into superficial line-count
chasing, where code is moved without clarifying ownership, replay/readiness
drifts quietly, test splits create duplicate fixtures instead of clearer
surfaces, or the UI split just recreates a second monolith under a new folder.

Owner surface: the hotspot facades own compatibility, the focused owner modules
own the extracted concerns, the shared test and metadata contracts own
behavioral safety, `config/improvement_cases.yaml` and
`config/hygiene_policy.yaml` own routing, and the handoff plus this plan own
the durable execution sequence.

Freshness check: rerun
`uv run docling-system-architecture-quality-report --summary`,
`uv run docling-system-hygiene-check`, and
`uv run docling-system-improvement-case-summary` before each milestone closes.
For any runtime-facing milestone, rerun
`uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
and `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene` in the
same closeout window.

| Weak point | Owner surface | Prevention gate | Fail threshold | Controlled violation |
| --- | --- | --- | --- | --- |
| Baseline owner-case routing regresses | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml` | `uv run docling-system-improvement-case-validate` and `uv run docling-system-hygiene-check` | `audit_bundles`, `retrieval_learning`, or the new UI case fall back to milestone-owned or missing routing | remove a case ID or replace it with a milestone owner in a temp edit and verify validation fails |
| ORM split changes schema or public imports | `app/db/models.py`, `app/db/model_domains/*.py`, metadata harness | import-compatibility tests, metadata/create-all tests, Alembic drift checks, full DB-backed suite | any table, index, constraint, vector, TSVECTOR, or public import contract drifts unexpectedly | stop re-exporting one moved ORM class or alter a required index expectation and verify the harness fails |
| Evidence split just relocates generic helpers | `app/services/evidence.py`, `app/services/evidence_*.py` | focused unit tests, runtime integration tests, hotspot prevention, hygiene | the new owner module exceeds budget or still mixes unrelated evidence concerns | add an unrelated payload helper to the new owner module in a negative fixture and verify hygiene/review blocks it |
| Agent action split restores broad dispatcher coupling | `app/services/agent_task_actions.py`, `app/services/agent_actions/*.py`, lookup seam tests | focused action-family tests, architecture probe, lookup-seam tests | fan-out stays flat because logic remains in the registry facade or a cycle returns | reintroduce direct context/task imports to the registry surface in a temp change and verify the lookup-cycle gate fails |
| Test splitting reduces confidence instead of increasing clarity | hotspot test files and their new focused replacements | full suite plus focused target files, `git diff --check`, architecture-quality report | assertions are dropped, duplicated, or moved into another oversized file | create a temporary split that omits one assertion family and verify focused tests catch the gap |
| UI split creates a second monolith | `app/ui/app.js`, `app/ui/modules/*.js`, new UI smoke tests | `node --check`, focused UI smoke tests, architecture probe line-count review | one new UI module absorbs unrelated concerns or `app/ui/app.js` stays effectively monolithic | move all existing logic into one new module in a trial branch and reject it when the file budget or review rule fails |

Future-Codex misuse scenario: the most likely failure is using the biggest
existing file as the easiest place to add one more helper because the file
already has context, imports, and tests. This plan prevents that by making
owner families explicit, requiring focused destination modules, and treating
hotspot-prevention and hygiene as blocking gates rather than advisory reports.

## Milestone Sequence

### Milestone 0: Baseline Lock And UI Routing Bootstrap

Purpose: start from clean routing and make the untracked UI hotspot explicit
before any implementation milestones begin.

Scope:

- verify that `audit_bundles` and `retrieval_learning` still route through
  explicit owner cases
- add an explicit improvement case for `app/ui/app.js`
- record that the UI hotspot is governed through the improvement-case registry
  and architecture probe output, not the current Python-only hygiene ratchet
- record this plan and the current baseline metrics in durable docs

Acceptance:

- `app/services/audit_bundles.py` and `app/services/retrieval_learning.py`
  remain case-owned in both `config/improvement_cases.yaml` and
  `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml` contains an explicit owner case for
  `app/ui/app.js`
- the plan and handoff both state that `app/ui/app.js` routing is tracked in
  the improvement-case registry because `uv run docling-system-hygiene-check`
  only governs Python files under `app/`
- `uv run docling-system-improvement-case-summary` and
  `uv run docling-system-hygiene-check` stay green with no new regressions

Status update:

- verified locally on 2026-05-10; see `docs/SESSION_HANDOFF.md` for the full
  gate output and routed follow-up

### Milestone 1: Retrieval Interaction Model Split

Purpose: reduce the top hotspot by moving the live search-and-chat interaction
ledger rows out of `app/db/models.py` and into a focused retrieval-interaction
owner module.

Scope:

- add `app/db/model_domains/retrieval_interactions.py`
- move:
  `SearchRequestRecord`,
  `SearchRequestResult`,
  `RetrievalEvidenceSpan`,
  `RetrievalEvidenceSpanMultiVector`,
  `SearchRequestResultSpan`,
  `SearchFeedback`,
  `ChatAnswerRecord`, and
  `ChatAnswerFeedback`
- keep `app.db.models` import-compatible via re-exports
- extend the metadata harness for retrieval-interaction table columns, required
  indexes, unique constraints, vector dimensions, and computed columns

Acceptance:

- `app/db/models.py` re-exports the moved symbols without caller breakage
- Alembic and `Base.metadata.create_all(...)` remain drift-free
- `app/db/models.py` shrinks below the current 5,537-line ratchet ceiling
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
  remains green with `failed_gate_count=0`

Status update:

- verified locally on 2026-05-10
- added `app/db/model_domains/retrieval_interactions.py`
- moved `SearchRequestRecord`, `SearchRequestResult`,
  `RetrievalEvidenceSpan`, `RetrievalEvidenceSpanMultiVector`,
  `SearchRequestResultSpan`, `SearchFeedback`, `ChatAnswerRecord`, and
  `ChatAnswerFeedback` behind the existing `app.db.models` facade
- extended the shared metadata harness for retrieval-interaction table columns,
  index names, exact index column ordering, unique constraints, vector
  dimensions, and computed TSVECTOR SQL
- reduced `app/db/models.py` from 5,537 lines to 5,067 lines and ratcheted
  `config/hygiene_policy.yaml` to match
- the next routed implementation slice is Milestone 2 under
  `IC-050E60059A34` / `app/services/evidence.py`

### Milestone 2: Evidence Owner-Family Continuation

Purpose: keep shrinking `app/services/evidence.py` through one more bounded
owner-family extraction behind the existing facade.

Scope:

- move one coherent evidence concern into `app/services/evidence_records.py`,
  `app/services/evidence_manifest_traces.py`, or a new narrow
  `app/services/evidence_*.py` owner if no current family fits
- default candidate: search/chat evidence export record assembly, manifest row
  composition, or adjacent payload serialization that still lives in the
  facade
- add focused unit coverage for the moved concern instead of growing broad
  evidence tests

Acceptance:

- `app/services/evidence.py` loses one coherent implementation concern
- the destination owner module stays under a governed file budget
- technical-report and retrieval-learning runtime integrations remain green
- architecture quality and hygiene show no new hotspot growth

Status update:

- verified locally on 2026-05-10
- added `app/services/evidence_technical_report_exports.py`
- moved the technical-report derivation package builder, provenance-lock
  assembly, export persistence, export attach helpers, and claim-derivation
  payload helpers out of `app/services/evidence.py`
- kept `app.services.evidence` import-compatible for
  `build_technical_report_derivation_package`,
  `apply_technical_report_derivation_links`,
  `persist_technical_report_evidence_export`,
  `attach_artifact_to_evidence_export`, and
  `attach_operator_run_to_evidence_export`
- added focused facade and owner coverage in
  `tests/unit/test_evidence_technical_report_exports.py`
- ratcheted `config/hygiene_policy.yaml` so `app/services/evidence.py` now has
  `ratchet_max_lines: 6307` and `ratchet_max_private_helpers: 81`, while the
  new owner module is governed at `ratchet_max_lines: 884`
- reduced `app/services/evidence.py` architecture-probe lines from `7143` to
  `6307` and hotspot score from `342864` to `302736`
- the next routed implementation slice is Milestone 3 under
  `IC-A1E186A34097` / `app/services/agent_task_actions.py`

### Milestone 3: Agent Action Family Split

Purpose: reduce `app/services/agent_task_actions.py` fan-out and surface area
by extracting one complete action family behind the existing registry facade.

Scope:

- move one bounded action family into `app/services/agent_actions/*.py`,
  including contract metadata, builders, helper logic, and executor wiring
- default candidate: report evidence/readiness/context-pack or another narrower
  already-clustered family if fresh inspection finds a better fit
- preserve `app/services/agent_task_actions.py` as the compatibility registry
  entrypoint and keep `app/services/agent_task_action_lookup.py` as the lookup
  seam

Acceptance:

- one action family no longer lives primarily in
  `app/services/agent_task_actions.py`
- lookup-seam tests remain green and no new large cycle component appears
- architecture probe fan-out and hotspot evidence do not worsen

Status update:

- verified locally on 2026-05-10
- added `app/services/agent_actions/report_actions.py`
- moved the technical-report action definition family for
  `plan_technical_report`, `build_report_evidence_cards`,
  `prepare_report_agent_harness`,
  `evaluate_document_generation_context_pack`, `draft_technical_report`, and
  `verify_technical_report` out of
  `app/services/agent_task_actions.py`
- kept `app.services.agent_task_actions` import-compatible as the action
  registry facade by composing the new owner registry into the existing action
  index
- added focused registry-composition coverage in
  `tests/unit/test_agent_task_actions.py` while keeping
  `tests/unit/test_agent_task_action_lookup.py` as the lookup seam gate
- ratcheted `config/hygiene_policy.yaml` so
  `app/services/agent_task_actions.py` now has `ratchet_max_lines: 2746` and
  `ratchet_max_private_helpers: 36`, while the new owner module is governed
  under `IC-A1E186A34097`
- reduced `app/services/agent_task_actions.py` architecture-probe lines from
  `2884` to `2746`, hotspot score from `170156` to `162014`, and fan-out from
  `39` to `36`
- the next routed implementation slice is Milestone 6 under
  `IC-1B643BA0AD90`

### Milestone 4: Test Hotspot Split Pack A

Purpose: reduce review friction on the current broad route and CLI test files.

Scope:

- split `tests/unit/test_cli.py` by command-group owner surfaces
- split `tests/unit/test_search_api.py` and `tests/unit/test_documents_api.py`
  by route family or capability surface
- keep assertion intent and API-boundary coverage intact

Acceptance:

- the original hotspot test files shrink materially
- new focused test files align to `app/cli_commands/*`, search route families,
  and document route families
- no HTTP-boundary error-path coverage is lost

Status update:

- verified locally on 2026-05-10
- reduced `tests/unit/test_cli.py` from 2,210 lines to 424 lines by moving
  agent-task, claim-support replay, and improvement-case coverage into
  `tests/unit/test_cli_agent_tasks.py`,
  `tests/unit/test_cli_agent_task_analytics.py`,
  `tests/unit/test_cli_claim_support.py`, and
  `tests/unit/test_cli_improvement_cases.py`, then moved the remaining
  search-harness CLI coverage into `tests/unit/test_cli_search_harness.py`
- reduced `tests/unit/test_search_api.py` from 1,660 lines to 436 lines by
  moving replay, harness/release, and learning/audit coverage into
  `tests/unit/test_search_api_replays.py`,
  `tests/unit/test_search_api_harnesses.py`, and
  `tests/unit/test_search_api_learning_audit.py`
- reduced `tests/unit/test_documents_api.py` from 1,273 lines to 613 lines by
  moving artifact and semantics coverage into
  `tests/unit/test_documents_api_artifacts.py` and
  `tests/unit/test_documents_api_semantics.py`
- kept the architecture quality summary flat at `max_hotspot_risk_score=673.78`
  while removing the three original test files from the current top-hotspot
  list
- verified the focused split pack with `uv run pytest -q ...` over the 13 split
  files (`119 passed in 4.13s`) and the full DB-backed suite with
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
  (`1317 passed in 51.44s`)
- the next routed implementation slice is Milestone 5 under
  `IC-934588120F94` and `IC-40CA7C1FFA84`

### Milestone 5: Test Hotspot Split Pack B

Purpose: reduce the heaviest action and claim-support test monoliths.

Scope:

- split `tests/unit/test_agent_task_actions.py` by action family
- split `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
  by scenario family or ledger surface
- keep fixture contracts stable and avoid duplicating large shared setup blocks

Acceptance:

- both hotspot files shrink materially without dropping scenario coverage
- the new files align to the owner surfaces created or confirmed in earlier
  milestones
- full DB-backed integration verification remains green

Status update:

- verified locally on 2026-05-10
- reduced `tests/unit/test_agent_task_actions.py` from 4,161 lines to 417
  lines by moving search-harness, semantic registry, ontology, semantic graph,
  and semantic document coverage into
  `tests/unit/test_agent_task_actions_search_harness.py`,
  `tests/unit/test_agent_task_actions_semantic_registry.py`,
  `tests/unit/test_agent_task_actions_ontology.py`,
  `tests/unit/test_agent_task_actions_semantic_graph.py`, and
  `tests/unit/test_agent_task_actions_semantic_documents.py`
- reduced `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
  from 4,368 lines to 337 lines by moving policy activation and waiver
  coverage into
  `tests/integration/test_claim_support_policy_activation_roundtrip.py`,
  change-impact and replay-closure coverage into
  `tests/integration/test_claim_support_policy_change_impacts_roundtrip.py`,
  and mined-failure governance coverage into
  `tests/integration/test_claim_support_policy_mined_failures_roundtrip.py`
- kept the original hotspot files out of the current architecture-probe top
  hotspot list while the new change-impact file remains the main residual
  large claim-support test surface at 2,297 lines
- verified the focused split pack with `uv run pytest -q ...` over the six
  unit split files (`52 passed in 0.93s`) and the four DB-backed integration
  split files
  (`DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q ...`: `17 passed in 4.76s`)
- the next routed implementation slice is Milestone 6 under `IC-1B643BA0AD90`

### Milestone 6: UI Monolith Split

Purpose: stop `app/ui/app.js` from being the sole JavaScript implementation
surface for the shipped operator UI.

Scope:

- create `app/ui/modules/*.js` for shared runtime, routing/view bootstrap, and
  page-family logic
- keep the shipped HTML entrypoints stable:
  `app/ui/index.html`,
  `app/ui/search.html`,
  `app/ui/evals.html`,
  `app/ui/agents.html`,
  `app/ui/documents.html`, and
  `app/ui/semantics.html`
- leave visual design and feature scope unchanged unless required to preserve
  module boundaries
- add focused UI smoke tests for bootstrap/static asset behavior

Acceptance:

- `app/ui/app.js` becomes bootstrap/composition glue rather than the sole
  implementation surface
- at least one focused UI test file exists and passes
- every JavaScript file under `app/ui/` passes `node --check`

### Milestone 7: Closeout And Reroute

Purpose: close the new paydown program with aligned routing, docs, and next-step
selection.

Scope:

- update this plan, `docs/SESSION_HANDOFF.md`, and the affected owner docs with
  the verified results
- update improvement-case deployment refs and measurements for completed
  milestones
- rerun architecture quality, hygiene, readiness, and probe outputs and route
  the next highest-value residual debt explicitly

Acceptance:

- every completed milestone records its commit hash and verified result
- the selected debt surfaces are either reduced, explicitly accepted, or routed
  to the next plan with owner-case precision
- no claimed closeout depends on stale metrics

## Required Implementation Artifacts

- focused owner modules under:
  `app/db/model_domains/`,
  `app/services/evidence_*.py`,
  `app/services/agent_actions/*.py`,
  `app/ui/modules/*.js`
- focused test files aligned to the split owner surfaces
- updated improvement-case and hygiene entries where routing changes
- refreshed supporting docs such as `docs/data_model_boundary_plan.md`

## Required Documentation And Handoff Updates

Every milestone in this plan must update:

- this plan
- `docs/SESSION_HANDOFF.md`

Update when affected:

- `docs/data_model_boundary_plan.md`
- `docs/agentic_architecture_index.md`
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
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
```

When `config/improvement_cases.yaml` or `config/hygiene_policy.yaml` changes:

```bash
uv run docling-system-improvement-case-validate
uv run docling-system-improvement-case-summary
```

Model-domain milestone:

```bash
uv run pytest -q tests/unit/test_db_model_import_compatibility.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py
uv run --extra dev alembic heads
uv run --extra dev alembic current
uv run --extra dev alembic upgrade head
uv run --extra dev alembic check
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json
uv run docling-system-agent-trace-review --limit 5 --skip-hygiene
```

Evidence and agent-action milestones:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json
uv run docling-system-agent-trace-review --limit 5 --skip-hygiene
```

Test hotspot milestones:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

UI milestone:

```bash
find app/ui -name '*.js' -print0 | xargs -0 -n1 node --check
uv run pytest -q tests/unit/test_ui.py
```

## Acceptance Criteria

This plan is complete only when all of these are true:

- `audit_bundles` and `retrieval_learning` remain explicit owner-case debt and
  `app/ui/app.js` gains the same routing precision
- `app/db/models.py`, `app/services/evidence.py`, and
  `app/services/agent_task_actions.py` each lose one bounded concern behind
  stable facades
- the selected hotspot test files are split into focused owner-aligned files
  without losing assertion coverage
- `app/ui/app.js` is no longer the sole JavaScript implementation surface
- architecture inspection, capability contracts, hotspot prevention, hygiene,
  and the full required runtime gates remain green
- each milestone closes with updated docs, handoff, and one atomic local commit

## Stop Conditions

Stop and update the handoff before continuing if:

- a milestone requires a public contract change that does not fit the current
  slice
- a new owner module cannot stay narrow enough to avoid becoming the next dump
  file
- DB metadata, Alembic, readiness, trace-review, or full-suite verification
  fails and the failure cannot be isolated to the milestone
- the UI split needs a product redesign rather than a structural split
- unrelated dirty files prevent the verified slice from landing as one isolated
  commit

## Local Commit Closeout Policy

Each milestone closes as one local atomic commit after verification passes:

```bash
git status --short
git diff --stat
git add <milestone files only>
git diff --cached --stat
git commit -m "<area>: complete high-value paydown milestone <N> <short-name>"
git status -sb
```

Do not stage unrelated dirty files, including pre-existing doc changes outside
the current milestone slice.

## Residual Risks And Next Milestone Routing

Residual risks after this plan, if all milestones pass, will likely shift to
the remaining `search.py`, `agent_task_context.py`, or import-cycle surfaces
rather than the specific files named here. The final closeout milestone must
rerun the architecture-quality report and route the next plan to the highest
remaining owner-scoped hotspot instead of assuming the current ordering still
holds.

## Closeout Checklist

- [x] Baseline routing validated and UI owner case added
- [ ] Retrieval-interaction ORM split completed and verified
- [ ] One additional evidence owner-family split completed and verified
- [ ] One additional agent action family split completed and verified
- [ ] Oversized route/CLI tests split and verified
- [ ] Oversized agent-task/claim-support tests split and verified
- [ ] UI monolith split into modules and smoke-tested
- [x] Docs, handoff, improvement cases, and hygiene routing updated
- [ ] Each milestone committed atomically after verification

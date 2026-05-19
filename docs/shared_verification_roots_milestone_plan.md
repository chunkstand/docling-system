# Shared Verification Roots Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: drafted originally as a queued standalone verification follow-on, but
now stale for direct execution after the 2026-05-18 DB-model and evaluation
residual closeouts. It is now historical for live queueing purposes behind
the resolved `docs/closeout_state_queue_alignment_milestone_plan.md`;
rebaseline this packet before activating it again.
Owner context: mechanical verification debt across the shared DB-model harness
roots and the evaluation-fixture verification root after the earlier
oversized-test packet reduced the first generation of monolith test files.

## Purpose

Resolve the selected verification debt without reopening already-closed
compatibility facades or turning this into another repo-wide test cleanup
umbrella.

2026-05-18 stale-plan note:

- `tests/unit/test_db_model_import_compatibility.py` and
  `tests/integration/test_db_model_metadata.py` are already reduced locally to
  `457` and `472` lines by the later DB-model residual owner-family packet.
- `tests/unit/test_evaluation_fixtures.py` is already reduced locally to `445`
  lines by the later evaluation residual owner-family packet.
- Do not execute this packet as written without a fresh Milestone 0 rebaseline
  that selects any still-relevant shared verification roots from the live
  queue.

The current weakness is not missing verification. The repo already has strong
contract coverage. The problem is that some of the remaining high-value
verification still lives in broad shared roots that are expensive to reason
about and easy to misuse:

- `tests/unit/test_db_model_import_compatibility.py` is still `612` lines.
- `tests/integration/test_db_model_metadata.py` is still `562` lines.
- `tests/unit/test_evaluation_fixtures.py` is still `1506` lines and remains
  the largest file in the repo.

Those files now sit in an awkward state:

- the DB-model residual packet already knows the two shared DB-model harness
  roots are likely to regrow, but they are still mostly treated as verification
  commands rather than as explicit verification-owner surfaces
- the evaluation service and oversized-test packets reduced adjacent roots, but
  `tests/unit/test_evaluation_fixtures.py` still has no dedicated owner packet
  or exact test-root routing
- none of the three selected roots currently have direct
  `artifact_target_path` ownership in `config/improvement_cases.yaml`
- none of the three selected roots currently have exact file-budget entries in
  `config/hygiene_policy.yaml`

This plan resolves that debt by:

- locking explicit routing for the selected verification roots
- decomposing the DB-model import and metadata roots into narrow shared roots
  plus domain-family siblings
- decomposing the evaluation-fixture root into a narrow shared root plus
  focused family-local suites
- preserving or strengthening exact verification coverage rather than shrinking
  files by dropping assertions

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-18
local / 2026-05-18 UTC:

```text
git status -sb
  ## main...origin/main
   M config/hotspot_prevention.yaml
   M config/hygiene_policy.yaml
   M config/improvement_cases.yaml
   M docs/SESSION_HANDOFF.md
   M docs/agentic_architecture_index.md
   M docs/boring_change_architecture_milestone_plan.md
  ?? docs/db_models_residual_owner_family_milestone_plan.md
  ?? docs/residual_large_file_backlog_milestone_plan.md
  plus active uncommitted implementation work across service and test owners

wc -l tests/unit/test_db_model_import_compatibility.py
      tests/integration/test_db_model_metadata.py
      tests/unit/test_evaluation_fixtures.py
    612 tests/unit/test_db_model_import_compatibility.py
    562 tests/integration/test_db_model_metadata.py
   1506 tests/unit/test_evaluation_fixtures.py

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  largest files include:
    tests/unit/test_evaluation_fixtures.py = 1506
    app/ui/modules/agents.js = 1300
    tests/unit/test_agent_task_verifications.py = 1197
    tests/integration/test_postgres_roundtrip.py = 1132
    app/services/semantic_orchestration.py = 1092
    tests/unit/test_docling_parser.py = 1080
    app/services/technical_reports.py = 1075
    app/db/model_domains/audit_and_evidence.py = 1053
    app/db/model_domains/semantic_memory.py = 979
    app/services/evaluation_fixtures.py = 966
    app/services/eval_workbench.py = 952
    app/ui/modules/shared.js = 930
  import fan-out includes:
    tests.unit.test_db_model_import_compatibility = 16 local imports
  Python cycles:
    none detected
```

Repo-current structural evidence:

- `docs/SESSION_HANDOFF.md` names
  `docs/db_models_residual_owner_family_milestone_plan.md` as the latest
  active bounded packet and the broader
  `docs/residual_large_file_backlog_milestone_plan.md` as the queued
  large-file coordination brief.
- `docs/agentic_architecture_index.md` records the oversized-test hotspot
  packet as resolved locally, but it also records that successor test hotspots
  and residual verification roots remain open or reduced.
- `docs/db_models_residual_owner_family_milestone_plan.md` already treats
  `tests/unit/test_db_model_import_compatibility.py` and
  `tests/integration/test_db_model_metadata.py` as direct owner surfaces, and
  it already names the default focused sibling split:
  `tests/unit/test_db_model_import_compatibility_{audit_and_evidence,semantic_memory,claim_support}.py`
  plus the matching
  `tests/integration/test_db_model_metadata_{audit_and_evidence,semantic_memory,claim_support}.py`
  files.
- `docs/db_models_residual_owner_family_milestone_plan.md` only requires the
  shared DB-model roots to close at or below `600` lines. That is a good first
  ratchet, but it still leaves them larger than a cheap shared manifest root
  should be.
- `config/improvement_cases.yaml` has no direct
  `artifact_target_path` entry for
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`, or
  `tests/unit/test_evaluation_fixtures.py`. The selected roots appear only in
  verification commands for:
  `IC-F2A8110185EB` (`app/db/models.py`),
  `IC-BF180637814C` (`app/services/evaluations.py`),
  `IC-7A628A4CBCAC` (`tests/unit/test_evaluation_service.py`), and
  `IC-5F0E1C8B0D42` (`tests/db_model_contract.py`).
- `config/hygiene_policy.yaml` currently has no exact file-budget entries for
  the three selected roots.
- `docs/oversized_test_hotspots_boundary_milestone_plan.md` already warned that
  new evaluation-family coverage should move into
  `tests/unit/test_evaluation_fixtures.py`,
  `tests/unit/test_evaluation_scoring.py`, and
  `tests/unit/test_evaluation_reads.py` rather than regrowing
  `tests/unit/test_evaluation_service.py`, but no later packet turned that
  warning into explicit routing for the still-large fixture root.
- `docs/boring_change_architecture_milestone_plan.md` already routes the two
  DB-model shared harness roots through the active DB-model packet and calls
  for a broader residual test-large-owner packet covering
  `tests/unit/test_evaluation_fixtures.py` and other open test monoliths.

## Goal

Resolve the selected shared verification-root debt so that:

- `tests/unit/test_db_model_import_compatibility.py` closes as a narrow shared
  import-compatibility manifest at or below `400` lines
- `tests/integration/test_db_model_metadata.py` closes as a narrow shared
  metadata manifest at or below `400` lines
- `tests/unit/test_evaluation_fixtures.py` closes as a narrow shared fixture
  root at or below `500` lines
- domain- or scenario-specific verification moves into focused sibling test
  files instead of regrowing the shared roots
- any new focused sibling between `401` and `600` lines receives same-milestone
  routing and a hygiene budget
- any new family-local support file stays at or below `400` lines and does not
  become a new generic sink
- coverage remains equivalent or stronger than today across the focused suites
  and final DB-backed closeout gate

The finish line for this plan is not "the tests are a bit better organized."
The finish line is a repo where the three selected roots are narrow shared
entrypoints, the moved verification has explicit ownership, and the same
coverage is still enforced through focused suites and the final DB-backed
closeout.

## Non-Goals

- No reopening of the deployed `app/db/models.py` compatibility facade.
- No broad evaluation-service code split of
  `app/services/evaluation_fixtures.py`,
  `app/services/evaluation_scoring.py`, or `app/services/eval_workbench.py`
  unless Milestone 2 proves a direct service-boundary change is required to
  preserve verification fidelity.
- No repo-wide cleanup of unrelated large tests such as
  `tests/unit/test_agent_task_verifications.py`,
  `tests/integration/test_postgres_roundtrip.py`, or
  `tests/unit/test_docling_parser.py`.
- No new generic `tests/helpers.py`, broad `conftest.py` sink, or
  `tests/support.py` dump file.
- No weakening of assertions, fixture coverage, skips, xfails, or integration
  gates to make the files smaller.
- No turning this packet into a general large-file service plan; the broader
  service and test backlog remains routed through
  `docs/residual_large_file_backlog_milestone_plan.md`.

## Scope

In scope:

- `tests/unit/test_db_model_import_compatibility.py`
- `tests/integration/test_db_model_metadata.py`
- `tests/unit/test_evaluation_fixtures.py`
- `tests/db_model_contract.py`
- `tests/db_model_contract_domains/*.py`
- `tests/unit/test_db_models_facade_contract.py`
- focused new DB-model harness siblings such as
  `tests/unit/test_db_model_import_compatibility_*.py` and
  `tests/integration/test_db_model_metadata_*.py`
- focused new evaluation-fixture siblings such as
  `tests/unit/test_evaluation_fixtures_*.py` or equivalently narrow
  family-local names chosen during Milestone 0
- family-local support files created specifically for the selected roots
- direct evaluation verification siblings:
  `tests/unit/test_evaluation_service.py`,
  `tests/unit/test_evaluation_scoring.py`,
  `tests/unit/test_evaluation_reads.py`
- direct DB-backed evaluation and metadata integrations:
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/integration/test_eval_workbench_roundtrip.py`,
  `tests/integration/test_multivector_retrieval.py`
- `docs/shared_verification_roots_milestone_plan.md`
- `docs/db_models_residual_owner_family_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `config/hotspot_prevention.yaml`
- `tests/unit/test_hotspot_prevention.py`

Out of scope:

- unrelated successor test hotspots left open by the oversized-test closeout
- evaluation-service implementation refactors beyond what is required to keep
  the verification roots honest
- JS, UI, service, or DB-model owner-family large-file reduction outside the
  exact verification roots named above
- unrelated dirty-worktree changes already present in the checkout

## Owner Surfaces

- shared DB-model verification roots:
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`,
  `tests/db_model_contract.py`,
  `tests/db_model_contract_domains/*.py`,
  `tests/unit/test_db_models_facade_contract.py`
- evaluation verification roots:
  `tests/unit/test_evaluation_fixtures.py`,
  `tests/unit/test_evaluation_service.py`,
  `tests/unit/test_evaluation_scoring.py`,
  `tests/unit/test_evaluation_reads.py`,
  `tests/integration/test_postgres_roundtrip.py`,
  `tests/integration/test_eval_workbench_roundtrip.py`,
  `tests/integration/test_multivector_retrieval.py`
- routing and prevention:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `config/hotspot_prevention.yaml`,
  `tests/unit/test_hotspot_prevention.py`
- queue and closeout docs:
  this plan,
  `docs/db_models_residual_owner_family_milestone_plan.md`,
  `docs/residual_large_file_backlog_milestone_plan.md`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`

## Placement Rules

- Keep `tests/unit/test_db_model_import_compatibility.py` and
  `tests/integration/test_db_model_metadata.py` as narrow shared manifest or
  smoke roots. Domain-specific ownership must move into focused siblings named
  for the actual model family, not into one new generic harness file.
- Keep `tests/unit/test_evaluation_fixtures.py` as a narrow shared fixture root
  or smoke root. Scenario-specific assertions must move into focused siblings
  named for a real fixture family, not into `test_evaluation_fixtures_more.py`
  or a broad generic support helper.
- Do not solve test-root debt by moving assertion logic into already-large
  service owners such as `app/services/evaluation_fixtures.py`,
  `app/services/evaluation_scoring.py`, `app/services/eval_workbench.py`, or
  unrelated service modules.
- Do not grow `tests/conftest.py` or create new cross-family helper sinks. If a
  support file is necessary, keep it family-local, narrowly named, and within
  the support budget.
- Any new or touched focused sibling between `401` and `600` lines must receive
  same-milestone routing in `config/improvement_cases.yaml` and
  `config/hygiene_policy.yaml`.
- Any new or touched verification root or support file above `600` lines fails
  the milestone.
- If Milestone 0 proves the active DB-model packet already landed the exact
  shared-root split for the two DB-model harness files, do not duplicate that
  code motion here. Refresh this plan and consume the verified result instead.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A shared root becomes smaller only by moving assertions into a new generic test sink. | touched test roots, family-local support files, `tests/conftest.py`, `config/hotspot_prevention.yaml` | staged `wc -l` review, hotspot-prevention checks, focused pytest suites | A new generic helper or broad `conftest.py` growth becomes the real owner of unrelated scenarios | Add a temporary `tests/helpers.py` or broaden `tests/conftest.py` for multiple unrelated families and confirm the milestone fails review or prevention gates | A future session keeps shrinking file counts by hiding the same debt in a generic support module |
| DB-model shared roots remain broad because domain-specific assertions keep landing in the root files. | `tests/unit/test_db_model_import_compatibility.py`, `tests/integration/test_db_model_metadata.py`, focused siblings | `wc -l` readback, focused unit and integration suites, DB-model routing docs | Either shared root remains above its closeout budget or moved domain-family assertions never leave the root | Add a moved audit-and-evidence assertion only to the shared root and confirm Milestone 1 cannot close | A future session preserves the owner split in models but keeps one giant shared test root |
| Evaluation fixtures become smaller only because scenarios were deleted or assertions weakened. | `tests/unit/test_evaluation_fixtures.py`, focused evaluation siblings, evaluation integrations | focused evaluation unit slice, DB-backed evaluation integrations, diff review for skips or xfails | Any scenario family disappears or is materially weakened without stronger focused replacement coverage | Remove one retrieval-fixture or structural-failure assertion and confirm the focused slice or review blocks closeout | A future session optimizes for a shorter file rather than preserving evaluation confidence |
| This packet duplicates or fights the active DB-model residual packet. | this plan, `docs/db_models_residual_owner_family_milestone_plan.md`, handoff or index docs | Milestone 0 queue review and docs alignment | The plan invents a second conflicting split map for the DB-model harness roots instead of consuming the active packet's route | Draft conflicting sibling names for the DB-model harness roots and confirm Milestone 0 requires a refresh before implementation | A future session sees two plans touching the same roots and lands overlapping decompositions |
| The selected roots stay implicitly covered in command lists but never become explicit routed owner surfaces. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, this plan, handoff or index docs | improvement-case validation, hygiene check, docs review | Milestone 0 or later closes without explicit routing for `tests/unit/test_evaluation_fixtures.py` and any residual selected root that still lacks direct ownership | Leave `tests/unit/test_evaluation_fixtures.py` as a command-only surface and confirm closeout review fails | A future session assumes that appearing in a pytest command is the same thing as being durably owned |
| Closeout goes green only because the final verification scope got easier. | all touched test roots, focused siblings, integration commands, closeout docs | focused verification commands plus final full DB-backed suite | The milestone passes because coverage, skips, or assertions got weaker rather than more focused | Narrow one metadata or fixture assertion and confirm the targeted suite or full DB-backed closeout rejects it | A future session deletes hard cases to land the split faster |

Accepted residuals during the sequence:

- A focused sibling between `401` and `600` lines is accepted only when the
  same milestone records explicit routing and a file budget for that sibling.
- No selected shared root above its stated closeout budget is accepted at final
  closeout.

## Milestone Sequence

### Milestone 0. Live Rebaseline And Explicit Verification-Root Routing
Outcome label: reduced

Purpose: freeze the exact selected-root baseline, align this packet with the
already-active DB-model residual packet, and convert command-only verification
surfaces into explicit routed owners before broad code motion begins.

Required work:

- rerun `wc -l`, the architecture probe, and targeted registry searches for
  the three selected roots
- confirm whether the active DB-model packet still owns the shared harness
  split for the two DB-model roots or whether its scope drifted
- add exact owner-case and hygiene routing for
  `tests/unit/test_evaluation_fixtures.py`
- decide whether the two DB-model harness roots should remain governed only by
  the active DB-model packet or should also receive explicit residual
  verification-root routing once that packet lands
- update this plan, the handoff, and the index so the queue order is honest

Milestone 0 is complete only when:

- all three selected roots have explicit routing or a named active packet owner
- the queue order is clear: active DB-model packet first, then this packet if
  the selected roots still remain open
- the selected roots have explicit closeout budgets recorded in the plan and,
  where applicable, in hygiene or improvement-case artifacts

### Milestone 1. DB-Model Shared Harness Root Decomposition
Outcome label: resolved

Purpose: retire the selected DB-model verification-root debt by turning the two
shared harness roots into narrow manifest or smoke surfaces and moving
domain-family coverage into focused siblings.

Required work:

- execute the shared-root portion of
  `docs/db_models_residual_owner_family_milestone_plan.md` or refresh this plan
  if that packet already landed the exact split
- create or verify focused siblings for:
  `audit_and_evidence`, `semantic_memory`, and `claim_support`
- keep `tests/db_model_contract.py` and
  `tests/unit/test_db_models_facade_contract.py` as the narrow compatibility
  manifest and public-import guard rather than regrowing them
- if needed, add exact file budgets and owner routing for any focused sibling
  between `401` and `600` lines

Milestone 1 is complete only when:

- `tests/unit/test_db_model_import_compatibility.py` is at or below `400`
  lines
- `tests/integration/test_db_model_metadata.py` is at or below `400` lines
- moved domain-family assertions live in focused siblings rather than the
  shared roots
- exact import-compatibility, metadata, Alembic, and full DB-backed
  verification all remain green

### Milestone 2. Evaluation-Fixture Root Decomposition
Outcome label: resolved

Purpose: retire the selected evaluation verification-root debt by turning
`tests/unit/test_evaluation_fixtures.py` into a narrow shared fixture root and
moving scenario-family coverage into focused suites.

Required work:

- classify the current scenario families inside
  `tests/unit/test_evaluation_fixtures.py`
- move those scenario families into focused sibling roots named for real owner
  boundaries discovered during Milestone 0
- keep `tests/unit/test_evaluation_service.py` narrow and prevent moved
  coverage from regrowing it
- keep any family-local support file narrow, explicit, and below the support
  budget
- if Milestone 2 proves that preserving fidelity requires a broad evaluation
  service-owner split, stop and route that code debt through the broader
  `docs/residual_large_file_backlog_milestone_plan.md` rather than widening
  this verification packet

Milestone 2 is complete only when:

- `tests/unit/test_evaluation_fixtures.py` is at or below `500` lines
- moved scenario-family coverage lives in focused siblings or narrow
  family-local support files
- no new generic support sink or broad `conftest.py` growth appears
- the focused evaluation unit slice and the direct DB-backed evaluation
  integrations remain equivalent or stronger than before

### Milestone 3. Verification-Root Closeout And Queue Refresh
Outcome label: resolved

Purpose: close the selected verification-root packet with fresh evidence,
durable docs, and explicit routing for anything that remains between `401` and
`600` lines.

Required work:

- rerun the selected `wc -l` readback and architecture probe
- update this plan, the handoff, the index, and any touched routing artifacts
- confirm that any accepted `401-600` focused sibling is explicitly routed
- rerun the final full DB-backed suite so the verification packet closes on a
  real end-to-end gate, not only targeted test slices

Milestone 3 is complete only when:

- all three selected shared roots meet their closeout budgets
- any accepted focused sibling between `401` and `600` lines is routed in the
  same closeout
- the selected verification roots no longer depend on implicit command-only
  ownership
- the final full DB-backed suite passes

## Required Implementation Artifacts

- `docs/shared_verification_roots_milestone_plan.md`
- updated routing entries in `config/improvement_cases.yaml` for
  `tests/unit/test_evaluation_fixtures.py` and any residual focused sibling
  that requires explicit owner routing
- updated file budgets in `config/hygiene_policy.yaml` for the selected roots
  and any accepted focused sibling or support file
- focused DB-model harness siblings:
  `tests/unit/test_db_model_import_compatibility_*.py` and
  `tests/integration/test_db_model_metadata_*.py`
- focused evaluation-fixture siblings such as
  `tests/unit/test_evaluation_fixtures_*.py` or equivalent family-local names
  chosen during Milestone 0
- any necessary family-local support file used by the focused evaluation or
  DB-model verification siblings

## Required Documentation And Handoff Updates

- update this plan with milestone status, verification, and closeout hashes
- update `docs/db_models_residual_owner_family_milestone_plan.md` if Milestone
  1 consumes or tightens its planned harness split
- update `docs/residual_large_file_backlog_milestone_plan.md` if Milestone 0
  or Milestone 2 changes how the broader backlog routes the selected
  evaluation-root debt
- update `docs/SESSION_HANDOFF.md` with the active packet, queued order, and
  selected-root line counts
- update `docs/agentic_architecture_index.md` so future sessions can discover
  this packet without reading broad history

## Required Verification Gates

Base gates for every milestone:

- `git diff --check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-hotspot-prevention-check --strict`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `wc -l tests/unit/test_db_model_import_compatibility.py tests/integration/test_db_model_metadata.py tests/unit/test_evaluation_fixtures.py`

DB-model harness gates:

- `uv run ruff check tests/db_model_contract.py tests/db_model_contract_domains tests/unit/test_db_model_import_compatibility*.py tests/unit/test_db_models_facade_contract.py tests/integration/test_db_model_metadata*.py config/improvement_cases.yaml config/hygiene_policy.yaml`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py tests/unit/test_db_model_import_compatibility_*.py tests/unit/test_db_models_facade_contract.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py tests/integration/test_db_model_metadata_*.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`

Evaluation verification-root gates:

- `uv run ruff check tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_fixtures_*.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py config/improvement_cases.yaml config/hygiene_policy.yaml`
- `uv run pytest -q tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_fixtures_*.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_eval_workbench_roundtrip.py tests/integration/test_multivector_retrieval.py`

Final closeout gate:

- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- `tests/unit/test_db_model_import_compatibility.py` is at or below `400`
  lines and functions as a narrow shared import-compatibility manifest.
- `tests/integration/test_db_model_metadata.py` is at or below `400` lines and
  functions as a narrow shared metadata manifest.
- `tests/unit/test_evaluation_fixtures.py` is at or below `500` lines and
  functions as a narrow shared fixture root.
- Domain-family or scenario-family verification lives in focused siblings
  rather than regrowing the shared roots.
- No new generic test sink or broad `conftest.py` growth appears.
- Any accepted focused sibling between `401` and `600` lines has explicit
  routing and a file budget in the same milestone.
- The focused suites and final full DB-backed suite pass without weakening
  coverage.

## Stop Conditions

- Stop and refresh Milestone 0 if the active DB-model residual packet lands the
  shared-root split before this packet starts, so implementation does not
  duplicate code motion.
- Stop if preserving evaluation verification fidelity requires a broad
  evaluation service-owner decomposition; route that through the broader
  large-file backlog packet instead of widening this verification packet.
- Stop if a proposed split only gets green by weakening assertions, adding
  skips, or moving scenario ownership into a generic support sink.
- Stop if new focused siblings remain above `600` lines without same-milestone
  routing.
- Stop before commit if the final full DB-backed suite is not green.

## Local Commit Closeout Policy

- Execute this packet milestone by milestone.
- Each milestone closes only with one local atomic commit containing the
  selected test-root changes, routing updates, docs, and handoff updates for
  that milestone only.
- Do not mix unrelated dirty-worktree changes into a verification-root
  closeout commit.
- A verified but uncommitted milestone is ready-to-close, not complete.

## Residual Risks And Next Milestone Routing

- The immediate next active bounded implementation brief remains
  `docs/db_models_residual_owner_family_milestone_plan.md`.
- This verification-root packet should remain queued until the active DB-model
  packet either closes or reroutes, because two of the three selected roots are
  already direct owner surfaces there.
- If the active DB-model packet lands the shared-root decomposition exactly as
  planned, this packet should refresh Milestone 0 and begin directly on the
  evaluation-fixture root.
- If the active DB-model packet only gets the two shared DB-model roots down to
  the looser `<=600` budget but leaves them broader than the shared-root target
  here, this packet still owns the follow-on tightening to `<=400`.
- Unrelated successor test hotspots such as
  `tests/unit/test_agent_task_verifications.py`,
  `tests/integration/test_postgres_roundtrip.py`, and other open verification
  monoliths remain under the broader
  `docs/residual_large_file_backlog_milestone_plan.md` queue and are not
  resolved by this packet.

# Cross-Cutting Large File Residual Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved locally in the current checkout through the 2026-05-18
cross-cutting closeout. The live >800 backlog is now gone, the stale
shared-verification branch is explicitly historical, and the governance
self-hosting follow-on is now also resolved locally, so the live queue now
returns to the broader under-budget reselect step.
Owner context: follow-on packet for the remaining large document-service and
verification roots that do not belong to the narrower evaluation, UI, or
semantic/report packets. The adjacent architecture-governance self-hosting
family under `IC-08C078FD4F45` now spans
`app/architecture_inspection.py`,
`app/architecture_inspection_rules.py`,
`app/services/improvement_case_intake.py`,
`app/services/improvement_cases.py`, and
`tests/unit/test_improvement_case_intake.py`.

## Purpose

Resolve the remaining mixed service and verification backlog without collapsing
everything back into one vague cleanup change.

## 2026-05-18 Closeout Update

This parent packet is now resolved locally in the current checkout.

- `app/services/documents.py` now measures `49` lines as a compatibility
  facade after ingest ownership moved into
  `app/services/document_ingest.py` at `233` lines and run-queue plus
  reprocess ownership moved into
  `app/services/document_run_queue.py` at `324` lines, while read ownership
  remains in `app/services/document_run_views.py` at `276` lines.
- `tests/unit/test_agent_task_verifications.py` now measures `324` lines with
  draft coverage moved into
  `tests/unit/test_agent_task_verifications_drafts.py` at `567` lines and
  family-local helpers kept in
  `tests/unit/agent_task_verification_support.py` at `328` lines.
- `tests/integration/test_postgres_roundtrip.py` now measures `331` lines with
  semantic and failure-path coverage moved into
  `tests/integration/test_postgres_roundtrip_semantics.py` at `503` lines and
  `tests/integration/test_postgres_roundtrip_failures.py` at `181` lines, plus
  family-local helper reuse in
  `tests/integration/postgres_roundtrip_support.py` at `159` lines.
- `tests/unit/test_docling_parser.py` now measures `540` lines with logical-table
  coverage moved into `tests/unit/test_docling_parser_logical_tables.py` at
  `160` lines and supplement coverage in
  `tests/unit/test_docling_parser_table_supplements.py` at `391` lines.
- `tests/integration/test_search_harness_releases.py` now measures `269` lines
  with readiness coverage moved into
  `tests/integration/test_search_harness_release_readiness.py` at `224` lines
  and family-local support narrowed to
  `tests/integration/search_harness_release_support.py` at `242` lines plus
  `tests/integration/search_harness_release_audit_support.py` at `296` lines.
- `tests/integration/test_claim_support_policy_activation_roundtrip.py` now
  measures `439` lines with waiver coverage moved into
  `tests/integration/test_claim_support_policy_activation_waivers.py` at `351`
  lines and retired-identity coverage moved into
  `tests/integration/test_claim_support_policy_activation_retired_identity.py`
  at `85` lines.
- The adjacent governance self-hosting family under `IC-08C078FD4F45` is now
  also resolved locally: the governed roots close at `370`, `514`, `552`,
  `82`, and `218`, the family-local siblings close at `122`, `184`, `475`,
  `279`, `277`, `101`, `122`, and `551`, and the local
  `app.services.improvement_case_observations` /
  `app.services.improvement_cases` cycle remains removed.
- The live architecture probe now reports `0` code files above `800` and
  `0` Python cycle components, `uv run docling-system-hygiene-check` reports
  `new hygiene regressions: none`, and the focused plus DB-backed verification
  slices remain green.

This packet therefore closes the large-file backlog requirement and the
cross-cutting verification follow-on while preserving the later governance
self-hosting closeout as a separate bounded packet rather than a hidden debt
shift into the cross-cutting family.

The narrowed routed residual family now closes at:

- `tests/unit/test_agent_task_verifications.py` at `324` lines
- `tests/integration/test_postgres_roundtrip.py` at `331` lines
- `app/services/improvement_case_intake.py` at `552` lines under `IC-08C078FD4F45`
- `tests/unit/test_docling_parser.py` at `540` lines
- `tests/integration/test_search_harness_releases.py` at `269` lines
- `tests/unit/test_improvement_case_intake.py` at `218` lines under `IC-08C078FD4F45`
- `app/architecture_inspection_rules.py` at `514` lines under `IC-08C078FD4F45`
- `tests/integration/test_claim_support_policy_activation_roundtrip.py` at `439` lines
- `app/services/document_ingest.py` at `233` lines with exact hygiene ratchets
- `app/services/document_run_queue.py` at `324` lines with exact hygiene ratchets
- `app/services/document_run_views.py` at `276` lines with exact hygiene ratchets
- `app/services/documents.py` at `49` lines as a compatibility facade
- `app/services/improvement_cases.py` at `82` lines under `IC-08C078FD4F45`

## Current Evidence

- The live architecture probe now reports `0` code files above `800` with
  `0` Python cycle components.
- `config/improvement_cases.yaml` keeps the document and verification family
  routed through `IC-6C3E1A7B9D52`, while the governance self-hosting family
  remains under `IC-08C078FD4F45`.
- `config/hygiene_policy.yaml` exact-ratchets the new `49/233/276/324`
  document-owner quartet plus the already narrowed `324`, `331`, `503`, and
  `567` line verification owners, and now also exact-ratchets the new parser,
  search-harness, and claim-support siblings or support created by the
  verification follow-on, while the later governance packet exact-ratchets its
  own roots and siblings instead of inheriting a stale under-budget exception.
- `docs/documents_service_boundary_milestone_plan.md` is now resolved locally
  in the current checkout. The document-service sink is retired without moving
  work into `runs.py`, `ingest_batches.py`, or evaluation owners.
- `docs/cross_cutting_verification_roots_milestone_plan.md` is now resolved
  locally in the current checkout after reducing the selected mixed-scenario
  verification roots below the default `600`-line budget without pulling the
  governance self-hosting family into the same slice.
- `docs/improvement_case_governance_self_hosting_milestone_plan.md` is now
  also resolved locally in the current checkout. It closes the residual
  `IC-08C078FD4F45` family at `370/514/552/82/218` plus exact-ratcheted
  siblings, so the next narrow code-owning packet must be reselected from
  `docs/boring_change_architecture_milestone_plan.md`.
- The earlier closeout-state coordination packet is now resolved locally, so
  this parent packet no longer depends on a pending queue-alignment step before
  routing returns to the code-owning follow-ons.

## Goal

Reduce the cross-cutting residual family so that:

- every routed root in this packet falls below `800` lines
- `app/services/improvement_cases.py` and
  the remaining governance self-hosting residuals remain explicitly routed
  under `IC-08C078FD4F45`
- no test split weakens parser, document-service, claim-support, search-release,
  or Postgres-backed coverage
- any new `601-800` residual created by the packet is routed in the same
  milestone with explicit hygiene ownership

## Non-Goals

- No broad search, claim-support, parser, or agent-task feature rewrite.
- No weakening of DB-backed integration coverage just to shrink test files.
- No using `app/services/documents.py` or `tests/integration/test_postgres_roundtrip.py`
  as generic sinks for unrelated moved logic.

## Scope

In scope:

- `app/services/documents.py`
- `app/services/improvement_cases.py`
- `tests/unit/test_agent_task_verifications.py`
- `tests/integration/test_postgres_roundtrip.py`
- `tests/unit/test_docling_parser.py`
- `tests/integration/test_search_harness_releases.py`
- `tests/unit/test_improvement_case_intake.py`
- `tests/integration/test_claim_support_policy_activation_roundtrip.py`
- family-local support or sibling files created to narrow the routed roots
- `tests/unit/test_document_service.py`
- `tests/unit/test_documents_api.py`
- `tests/unit/test_documents_api_artifacts.py`
- `tests/unit/test_documents_api_semantics.py`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`
- `docs/cross_cutting_large_file_residual_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`

Out of scope:

- changes already owned by the evaluation, UI, or semantic/report packets
- reopening closed compatibility facades because they still appear in raw
  hotspot lists
- broad architecture-governance workflow rewrites beyond the governed
  improvement-case test pair

## Owner Surfaces

- `app/services/documents.py`
- `app/services/improvement_cases.py`
- the routed unit and integration roots listed above
- any focused sibling or support files created by the packet

## Placement Rules

- Keep document-service logic in document-local owners, not in evaluation or
  parser sinks.
- Keep parser, release, claim-support, and Postgres integration coverage in
  family-local roots instead of one new giant smoke file.
- Preserve `IC-08C078FD4F45` as the owner case for the governance pair unless a
  narrower explicit successor is created inside the governance self-hosting
  follow-on.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A large verification root shrinks by deleting scenarios rather than splitting them honestly. | routed unit and integration roots | focused unit slice plus DB-backed integration slice | lower line count comes from weaker assertions or narrower scenario coverage | replace a scenario block with a smoke assertion and confirm review or tests reject it | future Codex optimizes for file size instead of contract coverage |
| The packet moves mixed logic into `documents.py` or another nearby service sink. | `app/services/documents.py`, sibling services, hygiene config | focused `ruff`, document-service tests, hygiene check, architecture probe | `documents.py` or a new sibling becomes the replacement monolith | dump parser or evaluation helpers into `documents.py` and confirm closeout rejects it | a later session uses the nearest service instead of creating a family-local owner |
| Governance routing drifts and loses the link between `app/services/improvement_cases.py` and `tests/unit/test_improvement_case_intake.py`. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, packet docs | improvement-case validate and summary, docs review | one of the governance roots loses explicit owner-case routing | remove the test-root owner binding and confirm closeout rejects the packet | future Codex sees the service root but forgets the paired oversized support test |

## Milestone Sequence

### Milestone 0. Baseline Lock
Outcome label: reduced

Refresh the routed root list, confirm `IC-6C3E1A7B9D52` and
`IC-08C078FD4F45`, and freeze the focused unit and integration slices before
code motion.

### Milestone 1. Documents Service Boundary Follow-on
Outcome label: reduced

`docs/documents_service_boundary_milestone_plan.md` is now resolved locally in
the current checkout. The packet retires the `app/services/documents.py` sink
without widening scope into the unrelated governance self-hosting family or
the oversized verification roots.

### Milestone 2. Verification Roots Follow-on
Outcome label: reduced

Execute `docs/cross_cutting_verification_roots_milestone_plan.md` after the
documents-service follow-on closes to reduce the selected mixed-scenario
verification roots below the default hygiene budget without creating a new test
support sink.

### Milestone 3. Governance Self-Hosting Follow-on
Outcome label: reduced

Execute `docs/improvement_case_governance_self_hosting_milestone_plan.md`
after the documents-service and verification follow-ons close to reduce the
residual `IC-08C078FD4F45` self-hosting family without reopening the already
closed architecture-governance cycle packet. This follow-on is now also
resolved locally in the current checkout.

### Milestone 4. Closeout
Outcome label: resolved

Close the packet only after every routed root is below `800`, the docs are
updated, and the focused plus DB-backed verification slices are green.

## Required Implementation Artifacts

- focused service, test, or support siblings needed to narrow the routed roots
- refreshed routing config in `config/improvement_cases.yaml` and
  `config/hygiene_policy.yaml`
- updated closeout docs and handoff artifacts

## Required Documentation And Handoff Updates

- `docs/cross_cutting_large_file_residual_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/documents.py tests/unit/test_document_service.py tests/unit/test_documents_api.py tests/unit/test_documents_api_artifacts.py tests/unit/test_documents_api_semantics.py tests/unit/test_agent_task_verifications.py tests/unit/test_docling_parser.py tests/unit/test_improvement_case_intake.py tests/integration/test_postgres_roundtrip.py tests/integration/test_search_harness_releases.py tests/integration/test_claim_support_policy_activation_roundtrip.py`
- `uv run pytest -q tests/unit/test_document_service.py tests/unit/test_documents_api.py tests/unit/test_documents_api_artifacts.py tests/unit/test_documents_api_semantics.py tests/unit/test_agent_task_verifications.py tests/unit/test_docling_parser.py tests/unit/test_improvement_case_intake.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_search_harness_releases.py tests/integration/test_claim_support_policy_activation_roundtrip.py`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- Every routed root in this packet falls below `800` lines.
- `app/services/improvement_cases.py` and
  `tests/unit/test_improvement_case_intake.py` remain explicitly routed under
  `IC-08C078FD4F45` or a narrower same-milestone successor case.
- No replacement owner or test root exceeds `800`, and any `601-800` residual
  is routed in the same milestone.
- The focused unit slice and DB-backed integration slice pass without weaker
  assertions or broader skips.

## Stop Conditions

- Stop if a fresh probe changes the routed root set before code motion begins.
- Stop if the packet starts mixing unrelated family work that belongs in one of
  the earlier child packets.
- Stop if a green result depends on deleting verification coverage instead of
  isolating it.

## Local Commit Closeout Policy

- Close this packet with one atomic local commit containing only the routed
  service, test, or support changes, focused verification, routing updates, and
  doc or handoff updates for this packet.

## Residual Risks And Next Milestone Routing

- If any routed root remains between `601` and `800`, keep it explicitly routed
  under `IC-6C3E1A7B9D52` or `IC-08C078FD4F45` and name the next narrow
  follow-on before closeout.
- If the documents-service follow-on closes cleanly while the remaining
  verification or governance roots stay open, update this parent packet and the
  handoff to name the next narrower slice instead of treating this parent plan
  as directly executable code motion.
- If the verification-roots follow-on closes cleanly while the governance
  self-hosting family remains open, keep `IC-08C078FD4F45` explicitly routed
  and name the governance follow-on in the handoff before attempting parent
  closeout. This condition is now resolved locally because the governance
  self-hosting packet also closed in the current checkout.
- After this packet closes, return to
  `docs/residual_large_file_backlog_milestone_plan.md` for the final
  zero-oversized closeout. Do not reactivate
  `docs/shared_verification_roots_milestone_plan.md` unless a later explicit
  rebaseline selects a new live shared verification owner.

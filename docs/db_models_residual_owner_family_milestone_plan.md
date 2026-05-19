# DB Models Residual Owner Family Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved through the 2026-05-18 durable closeout after Milestone 4
verification and after the
`docs/agent_task_residual_owner_family_milestone_plan.md` closeout.
Owner context: residual owner-family follow-on after the deployed
`app/db/models.py` compatibility-facade case `IC-F2A8110185EB`. This packet
targets the still-oversized extracted model-domain owners
`app/db/model_domains/audit_and_evidence.py`,
`app/db/model_domains/semantic_memory.py`, and
`app/db/model_domains/claim_support.py`, plus the directly-adjacent DB-model
contract harness surfaces they are most likely to regrow.

## 2026-05-18 Closeout Update

This packet is now resolved locally in the current checkout through Milestone 4
verification.

- `app/db/models.py` remains the deployed `159`-line public compatibility
  facade under `IC-F2A8110185EB`.
- Residual owner-family routing now lives under `IC-46C5B38A1D2E`,
  `IC-7D8AE7C83B8F`, and `IC-62C75B82F0AA` instead of borrowing the deployed
  facade-only case.
- `app/db/model_domains/audit_and_evidence.py`,
  `app/db/model_domains/semantic_memory.py`, and
  `app/db/model_domains/claim_support.py` now close at `31`, `53`, and `31`
  lines as narrow composition surfaces.
- The extracted family-local model owners now close at `207`, `214`, `388`,
  `317`, `129`, `223`, `193`, `238`, `143`, `156`, `197`, `264`, `241`, and
  `190` lines across the new `audit_and_evidence_*`, `semantic_memory_*`, and
  `claim_support_*` modules; no governed new owner exceeds the default
  `600`-line budget.
- `tests/unit/test_db_model_import_compatibility.py` and
  `tests/integration/test_db_model_metadata.py` now close at `457` and `472`
  lines after moving audit-and-evidence, claim-support, and semantic-memory
  ownership or metadata checks into focused sibling files at `45`, `45`, `51`,
  `43`, `43`, and `43` lines.
- Focused verification is green:
  `609 passed` for the unit and facade slice,
  `335 passed` for the focused DB-backed metadata slice,
  Alembic `heads/current/upgrade head/check` passed,
  `uv run docling-system-improvement-case-validate` returned `valid=true`,
  `uv run docling-system-hygiene-check` reported `new hygiene regressions:
  none`, `uv run docling-system-improvement-case-summary` reported
  `case_count=55` with `status_counts.open=39`,
  `status_counts.deployed=15`, and `measured_case_count=51`,
  `uv run docling-system-architecture-quality-report --summary` remained at
  `hotspot_count=10` / `max_hotspot_risk_score=496.06`, the architecture probe
  reports `17` code files above `800` lines with `0` Python cycle components,
  and the full DB-backed suite passed at `2078 passed`.
- The next routed bounded packet is now
  `docs/hotspot_routing_trap_resolution_milestone_plan.md`. The queued
  `docs/shared_verification_roots_milestone_plan.md` brief now needs a
  Milestone 0 rebaseline because this packet already resolved two of its three
  originally selected root surfaces.

## Purpose

Resolve the residual DB-model owner-family debt without reopening the
already-closed `app/db/models.py` facade work.

The scoped weakness is no longer that `app/db/models.py` still contains mixed
ORM ownership. That issue is already resolved locally by the deployed
compatibility-facade contract in
`docs/db_models_compatibility_facade_milestone_plan.md`. The live debt has
moved into the extracted owners. Milestone 0 captured the pre-split baseline at
`1053`, `979`, and `829` lines for
`app/db/model_domains/audit_and_evidence.py`,
`app/db/model_domains/semantic_memory.py`, and
`app/db/model_domains/claim_support.py`. The packet is now resolved locally:
those roots close at `31`, `53`, and `31` lines as narrow composition
surfaces, while the actual ORM ownership now lives in focused
`audit_and_evidence_*`, `semantic_memory_*`, and `claim_support_*` files.

The routing trap is likewise closed locally. The public compatibility facade is
still intentionally high fan-in and stable, but the actual residual file-budget
risk no longer hides under the deployed facade case `IC-F2A8110185EB`. It now
lives under dedicated residual owner routing for the extracted owners and the
focused harness roots that prove them.

This plan resolves that residual owner-family debt by:

- bootstrapping honest residual owner routing for the three extracted domain
  files
- splitting each domain owner into narrower family-local model modules under
  `app/db/model_domains/`
- keeping `app/db/models.py` frozen as the public compatibility facade
- preserving exact Alembic and `Base.metadata.create_all(...)` behavior
- keeping shared DB-model contract coverage equivalent or broader than the
  current harness

## Current Evidence

This packet now carries two evidence checkpoints so the file stays honest about
what was baseline debt and what is now resolved local state.

Milestone 0 pre-split baseline captured before code motion:

- the architecture probe listed
  `app/db/model_domains/audit_and_evidence.py`,
  `app/db/model_domains/semantic_memory.py`, and
  `app/db/model_domains/claim_support.py` at `1053`, `979`, and `829` lines
  with `app.db.models` still at `13038` hotspot risk and `265` local importers
- hygiene still routed those three extracted domain files under the deployed
  compatibility-facade case `IC-F2A8110185EB`
- `uv run docling-system-improvement-case-summary` then reported
  `case_count=52`, `status_counts.open=36`, `status_counts.deployed=15`, and
  `measured_case_count=48`
- the shared DB-model harness roots measured `612` lines for
  `tests/unit/test_db_model_import_compatibility.py` and `562` lines for
  `tests/integration/test_db_model_metadata.py`

Post-closeout verified state in the current checkout:

- `app/db/models.py` remains the `159`-line public compatibility facade
- `app/db/model_domains/audit_and_evidence.py`,
  `app/db/model_domains/semantic_memory.py`, and
  `app/db/model_domains/claim_support.py` now close at `31`, `53`, and `31`
  lines as narrow composition surfaces
- the moved ORM ownership now lives in focused family-local files at `207`,
  `214`, `388`, `317`, `129`, `223`, `193`, `238`, `143`, `156`, `197`,
  `264`, `241`, and `190` lines across the new
  `audit_and_evidence_*`, `semantic_memory_*`, and `claim_support_*` modules
- `tests/unit/test_db_model_import_compatibility.py` and
  `tests/integration/test_db_model_metadata.py` now close at `457` and `472`
  lines, while focused sibling suites close at `45`, `45`, `51`, `43`, `43`,
  and `43` lines
- focused verification is green:
  `609 passed` for the DB-model unit and facade slice,
  `335 passed` for the focused DB-backed metadata slice,
  Alembic `heads/current/upgrade head/check` passed,
  `uv run docling-system-improvement-case-validate` returned `valid=true`,
  `uv run docling-system-hygiene-check` reported `new hygiene regressions:
  none`, and the full DB-backed suite passed at `2078 passed`
- the broader architecture and routing checks remain aligned:
  `uv run docling-system-improvement-case-summary` now reports
  `case_count=55`, `status_counts.open=39`, `status_counts.deployed=15`, and
  `measured_case_count=51`;
  `uv run docling-system-architecture-quality-report --summary` remains at
  `hotspot_count=10` and `max_hotspot_risk_score=496.06`;
  the architecture probe now reports `17` code files above `800` and `0`
  Python cycle components
- `git status -sb` still shows unrelated dirty local work in the broader
  checkout, so the packet is resolved locally but not yet closed by an atomic
  commit

Repo-current structural evidence:

- `config/improvement_cases.yaml` now assigns explicit residual owner cases to
  the extracted owner families and shared harness roots:
  `IC-46C5B38A1D2E`,
  `IC-7D8AE7C83B8F`, and
  `IC-62C75B82F0AA`.
- `config/hygiene_policy.yaml` now ratchets the extracted domain owners and the
  focused DB-model sibling suites under those residual owner cases instead of
  borrowing the deployed facade-only case.
- `docs/data_model_boundary_plan.md`, `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` now all agree that this
  residual DB-model packet is the latest locally resolved bounded brief and
  that the next routed bounded packet is
  `docs/hotspot_routing_trap_resolution_milestone_plan.md`.
- `app/db/model_domains/audit_and_evidence.py`,
  `app/db/model_domains/semantic_memory.py`, and
  `app/db/model_domains/claim_support.py` are now thin composition surfaces;
  the actual ORM ownership sits in focused family-local owners.
- `tests/db_model_contract.py` is already a narrow shared compatibility
  manifest at `159` lines, and the domain-local source-of-truth already lives in
  `tests/db_model_contract_domains/audit_and_evidence.py`,
  `tests/db_model_contract_domains/semantic_memory.py`, and
  `tests/db_model_contract_domains/claim_support.py`.
- the shared unit and integration roots are now under the packet threshold
  precisely because the domain-family checks moved into focused siblings instead
  of regrowing the shared roots

## Goal

Resolve the residual DB-model owner-family debt so that:

- `app/db/models.py` remains frozen as the public compatibility facade at or
  below its current `159`-line ratchet.
- `app/db/model_domains/audit_and_evidence.py`,
  `app/db/model_domains/semantic_memory.py`, and
  `app/db/model_domains/claim_support.py` each become narrow domain-family
  composition or compatibility surfaces at or below `600` lines.
- any new focused owner file created by this packet under
  `app/db/model_domains/` stays at or below `600` lines.
- the shared DB-model harness preserves exact table columns, exact index names,
  exact index-column ordering, exact unique-constraint names, exact
  unique-constraint column ordering, vector dimensions, and computed SQL with
  equivalent or broader contract coverage.
- `tests/unit/test_db_model_import_compatibility.py` and
  `tests/integration/test_db_model_metadata.py` remain narrow shared harness
  roots rather than becoming the next residual model-domain monoliths.
- the deployed facade case `IC-F2A8110185EB` stops carrying the extracted
  residual file-budget debt, which instead gets explicit residual owner routing.

## Non-Goals

- No reopening of the deployed `app/db/models.py` compatibility-facade case.
- No attempt to reduce `app.db.models` fan-in by rewriting callers away from the
  public import path.
- No table rename, column rename, foreign-key target change, relationship name
  change, check-constraint value change, named index change, named
  unique-constraint change, vector-dimension change, or generated SQL change.
- No broad service, API, CLI, search, evidence, or agent-task refactor.
- No weakening of tests, fixtures, Alembic gates, or metadata checks.
  Do not weaken the current DB-model contract stack just to make the new owner
  files fit their budgets.
- No new generic `app/db/model_domains/common_residual.py` or
  `tests/db_model_contract_domains/shared_residual.py` sink that simply
  relocates the same mixed ownership.

## Scope

In scope:

- Milestone 0 live-state refresh and residual owner-case bootstrap
- `app/db/model_domains/audit_and_evidence.py`
- `app/db/model_domains/semantic_memory.py`
- `app/db/model_domains/claim_support.py`
- focused new owner files under `app/db/model_domains/` created by this packet,
  including `audit_and_evidence_*.py`, `semantic_memory_*.py`, and
  `claim_support_*.py` or equivalent narrow family-local names chosen during
  implementation
- `tests/db_model_contract.py`
- `tests/db_model_contract_domains/audit_and_evidence.py`
- `tests/db_model_contract_domains/semantic_memory.py`
- `tests/db_model_contract_domains/claim_support.py`
- `tests/unit/test_db_model_import_compatibility.py`
- `tests/integration/test_db_model_metadata.py`
- focused new domain-local DB-model harness roots such as
  `tests/unit/test_db_model_import_compatibility_*.py` and
  `tests/integration/test_db_model_metadata_*.py` if Milestone 0 proves the
  current shared roots would otherwise regrow
- `tests/unit/test_db_models_facade_contract.py`
- `docs/db_models_residual_owner_family_milestone_plan.md`
- `docs/data_model_boundary_plan.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `config/improvement_cases.yaml`
- `config/hygiene_policy.yaml`

Out of scope:

- changing the public `app.db.models` import contract for callers
- reopening already-under-budget domain owners such as
  `app/db/model_domains/agent_tasks.py` or
  `app/db/model_domains/evaluation_feedback.py`
- generic test hotspot cleanup outside the directly-adjacent DB-model harness
  roots
- closing unrelated app or UI large-file backlog

## Owner Surfaces

- public compatibility facade:
  `app/db/models.py`
- residual domain owners:
  `app/db/model_domains/audit_and_evidence.py`,
  `app/db/model_domains/semantic_memory.py`,
  `app/db/model_domains/claim_support.py`
- focused residual owner files created by this packet under
  `app/db/model_domains/`
- shared contract harness:
  `tests/db_model_contract.py`
  and `tests/db_model_contract_domains/*.py`
- shared import and metadata harness roots:
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`,
  `tests/unit/test_db_models_facade_contract.py`
- focused new domain-local harness siblings created by this packet under
  `tests/unit/` and `tests/integration/`
- migration and schema gates:
  `uv run --extra dev alembic *`
- routing and governance artifacts:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`,
  `docs/data_model_boundary_plan.md`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/boring_change_architecture_milestone_plan.md`

## Placement Rules

- Keep `app/db/models.py` as the only public caller import surface.
- Keep `app/db/models.py` import-forwarding only; do not move ORM
  implementations, enum ownership, or helper logic back into the facade.
- Split each residual domain owner into family-local sibling files under
  `app/db/model_domains/` rather than creating another large mixed owner.
- Keep family boundaries explicit:
  audit or evidence export ownership apart from trace or derivation ownership,
  ontology or registry ownership apart from assertion or fact ownership, and
  waiver or corpus ownership apart from evaluation or policy-impact ownership.
- Keep `tests/db_model_contract.py` as the narrow shared manifest root and place
  domain-specific table or index or unique-constraint or computed-SQL data in
  `tests/db_model_contract_domains/`.
- If shared harness roots would exceed `600` lines, move domain-specific import
  or metadata assertions into focused sibling files rather than broadening the
  roots.
- Preserve exact DDL semantics. When emitted SQL is non-trivial, verify the
  exact emitted schema against Postgres rather than relying on ORM intuition.

## Proposed Family-Local Split Map

Milestone 0 should start from these default family boundaries unless the live
readback proves a different grouping is both clearer and still under budget.
Any deviation from this map must be recorded in this plan and reflected in the
matching contract fragments and focused test siblings.

- `app/db/model_domains/audit_and_evidence_audit_bundles.py`:
  `AuditBundleExport`, `AuditBundleValidationReceipt`
- `app/db/model_domains/audit_and_evidence_manifests.py`:
  `EvidencePackageExport`, `EvidenceManifest`
- `app/db/model_domains/audit_and_evidence_technical_reports.py`:
  `TechnicalReportReleaseReadinessDbGate`,
  `TechnicalReportClaimRetrievalFeedback`
- `app/db/model_domains/audit_and_evidence_trace.py`:
  `EvidenceTraceNode`, `EvidenceTraceEdge`, `ClaimEvidenceDerivation`
- `app/db/model_domains/semantic_memory_snapshots.py`:
  `SemanticOntologySnapshot`, `WorkspaceSemanticState`,
  `SemanticGraphSnapshot`, `WorkspaceSemanticGraphState`
- `app/db/model_domains/semantic_memory_registry.py`:
  `SemanticConcept`, `SemanticCategory`, `SemanticTerm`,
  `SemanticConceptTerm`, `SemanticConceptCategoryBinding`
- `app/db/model_domains/semantic_memory_reviews.py`:
  `DocumentSemanticConceptReview`, `DocumentSemanticCategoryReview`,
  `DocumentRunSemanticPass`
- `app/db/model_domains/semantic_memory_assertions.py`:
  `SemanticAssertion`, `SemanticAssertionCategoryBinding`,
  `SemanticAssertionEvidence`
- `app/db/model_domains/semantic_memory_facts.py`:
  `SemanticEntity`, `SemanticFact`, `SemanticFactEvidence`
- `app/db/model_domains/semantic_memory_governance.py`:
  `SemanticGovernanceEvent`
- `app/db/model_domains/claim_support_waivers.py`:
  `ClaimSupportReplayAlertFixtureCoverageWaiverLedger`,
  `ClaimSupportReplayAlertFixtureCoverageWaiverEscalation`
- `app/db/model_domains/claim_support_fixtures.py`:
  `ClaimSupportFixtureSet`,
  `ClaimSupportReplayAlertFixtureCorpusSnapshot`,
  `ClaimSupportReplayAlertFixtureCorpusRow`
- `app/db/model_domains/claim_support_evaluations.py`:
  `ClaimSupportCalibrationPolicy`, `ClaimSupportEvaluation`,
  `ClaimSupportEvaluationCase`
- `app/db/model_domains/claim_support_policy_impacts.py`:
  `ClaimSupportPolicyChangeImpact`

Default focused harness siblings if Milestone 0 proves the shared roots would
regrow:

- `tests/unit/test_db_model_import_compatibility_audit_and_evidence.py`
- `tests/unit/test_db_model_import_compatibility_semantic_memory.py`
- `tests/unit/test_db_model_import_compatibility_claim_support.py`
- `tests/integration/test_db_model_metadata_audit_and_evidence.py`
- `tests/integration/test_db_model_metadata_semantic_memory.py`
- `tests/integration/test_db_model_metadata_claim_support.py`

## Weak-Point Prevention Contract

Weak point forecast: the most likely failure modes are reopening the deployed
facade instead of the extracted owners, creating another oversized
`model_domains` dump file, silently changing emitted DDL while line counts
improve, regrowing the shared DB-model harness roots, or leaving the residual
owners hidden under a deployed owner case.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A future session reopens `app/db/models.py` because the architecture-quality summary still routes it. | `app/db/models.py`, `tests/unit/test_db_models_facade_contract.py`, routing docs | Facade-contract test, `wc -l app/db/models.py`, routing-doc review | The packet edits the public facade for anything other than import-forwarder maintenance or line count rises above `159`. | Temporarily add a direct ORM definition or enum owner back into `app/db/models.py` and confirm the facade gate fails. | A later session sees the hotspot path and dumps new model code back into the facade. |
| A residual domain split only renames the monolith by creating one new large sibling file. | `app/db/model_domains/audit_and_evidence*.py`, `semantic_memory*.py`, `claim_support*.py`, hygiene policy | `wc -l` readback, `uv run docling-system-hygiene-check`, focused DB-model harness tests | Any new family-local owner created by this packet exceeds `600` lines or still mixes unrelated concern families. | Leave a temporary `semantic_memory_core.py` or `claim_support_core.py` containing multiple unrelated families and confirm review or hygiene blocks closeout. | A future session claims success by moving all remaining tables into one different big file. |
| DDL or metadata semantics drift while the split looks behavior-preserving at the Python layer. | domain owner files, `tests/db_model_contract_domains/*.py`, `tests/integration/test_db_model_metadata*.py`, Alembic | exact Postgres metadata tests, Alembic commands, full DB-backed suite | Any table-column set, named index, named unique constraint, vector dimension, computed SQL, or `Base.metadata.create_all(...)` result changes unexpectedly. | Temporarily change one required index-column ordering or unique-constraint expectation and confirm the Postgres metadata gate fails. | A future session preserves imports but silently changes emitted schema. |
| The shared import or metadata harness roots become the next monolith while protecting the split. | `tests/unit/test_db_model_import_compatibility.py`, `tests/integration/test_db_model_metadata.py`, focused sibling files | `wc -l` readback, focused unit or integration suites | The shared unit or integration root grows above `600` without moving domain-specific assertions into focused siblings. | Temporarily add a moved domain-family assertion only to the shared root and confirm the milestone checklist requires a focused sibling or a root reduction before closeout. | A future session keeps the data-model owners small by piling all new checks into one shared test root. |
| Residual owner routing stays attached to deployed `IC-F2A8110185EB`, leaving the next session no honest owner for the extracted files. | `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`, routing docs | improvement-case validation, hygiene check, routing-doc review | The extracted residual owners still borrow only the deployed facade case after Milestone 0. | Remove a residual owner-case or hygiene reassignment in a temporary diff and confirm closeout blocks the milestone. | A future session sees large model-domain files but no explicit residual owner and reopens the wrong case. |
| Closeout goes green only because coverage got easier. | all touched tests, contract fragments, and verification docs | full focused DB-model suite plus full DB-backed suite | Any check passes because tests, fixtures, or gates were weakened rather than replaced with equivalent or broader contract coverage. | Temporarily narrow one import-compatibility or metadata assertion and confirm the focused suite or review rejects the regression. | A future session deletes precise DDL assertions to make a split land quickly. |

## Milestone Sequence

### Milestone 0 - Live Refresh And Residual Owner Bootstrap

Outcome label: reduced

Purpose: freeze the exact residual DB-model baseline and give the extracted
owners honest routing before any code motion starts.

Closeout result on 2026-05-18 local:

- Bootstrapped dedicated residual owner routing under `IC-46C5B38A1D2E`,
  `IC-7D8AE7C83B8F`, and `IC-62C75B82F0AA`.
- Reassigned the extracted roots away from the deployed facade-only case in
  `config/hygiene_policy.yaml`.
- Locked the default class-to-file split map used by Milestones 1 through 3.
- Decided up front to add focused sibling harness files because the shared
  unit and integration roots were already at `612` and `562` lines.

Required work:

- Re-run the architecture-quality summary, architecture probe, hygiene check,
  improvement-case summary, and `wc -l` readback for the selected domain owners
  and harness roots.
- Confirm `app/db/models.py` remains the deployed compatibility facade and is
  not the implementation target for this packet.
- Create honest residual owner routing for the extracted domain files. Either:
  bootstrap dedicated residual owner cases for
  `app/db/model_domains/audit_and_evidence.py`,
  `app/db/model_domains/semantic_memory.py`, and
  `app/db/model_domains/claim_support.py`, or justify one narrower residual
  owner-family case that replaces the current borrowed facade routing.
- Reassign the three extracted domain files in `config/hygiene_policy.yaml`
  away from the deployed facade-only routing.
- Lock the planned class-to-file map for each domain family. If the default map
  in this plan changes, record the deviation and why the replacement split is
  narrower or more stable.
- Decide whether the shared DB-model harness roots need focused sibling files
  before the first domain split. If the current `612`-line unit root or
  `562`-line integration root would regrow, add the focused test files first.

Acceptance criteria:

- This plan captures the live extracted-domain line counts, `app.db.models`
  fan-in, and shared harness line counts.
- `app/db/models.py` remains a deployed compatibility facade in the routing
  docs, not the selected implementation surface.
- The extracted residual owners no longer rely solely on the deployed facade
  case for hygiene routing.
- The chosen class families and target files are explicit before broad code
  motion begins.
- The shared DB-model harness plan for root files versus focused siblings is
  explicit before broad implementation begins.

### Milestone 1 - Audit And Evidence Residual Owner Split

Outcome label: resolved

Purpose: reduce `app/db/model_domains/audit_and_evidence.py` to a narrow
domain-family composition or compatibility surface.

Closeout result on 2026-05-18 local:

- Moved the audit-and-evidence ORM family into
  `audit_and_evidence_audit_bundles.py`,
  `audit_and_evidence_manifests.py`,
  `audit_and_evidence_technical_reports.py`, and
  `audit_and_evidence_trace.py`.
- Reduced `app/db/model_domains/audit_and_evidence.py` to a `31`-line
  composition surface.

Required work:

- Split audit bundle export or validation ownership away from evidence package
  or manifest ownership, technical-report readiness or retrieval feedback
  ownership, and trace or derivation ownership.
- Prefer the four-family split in this plan:
  `audit_and_evidence_audit_bundles.py`,
  `audit_and_evidence_manifests.py`,
  `audit_and_evidence_technical_reports.py`, and
  `audit_and_evidence_trace.py`, unless Milestone 0 captured a narrower and
  clearly documented alternative.
- Keep only the narrow domain-family composition or import-forwarding surface in
  `app/db/model_domains/audit_and_evidence.py`.
- Expand `tests/db_model_contract_domains/audit_and_evidence.py` and the
  matching unit or integration harness only as needed to preserve exact DDL
  coverage.
- If shared harness roots would regrow, move audit-and-evidence-specific import
  and metadata assertions into focused sibling test files.

Acceptance criteria:

- `app/db/model_domains/audit_and_evidence.py` closes at or below `600` lines.
- Any new audit-and-evidence family-local owner file created by this milestone
  closes at or below `600` lines.
- Exact table, index, unique-constraint, and relationship contracts remain
  stable with equivalent or broader contract coverage.

### Milestone 2 - Semantic Memory Residual Owner Split

Outcome label: resolved

Purpose: reduce `app/db/model_domains/semantic_memory.py` to a narrow
domain-family composition or compatibility surface.

Closeout result on 2026-05-18 local:

- Moved the semantic-memory ORM family into
  `semantic_memory_snapshots.py`,
  `semantic_memory_registry.py`,
  `semantic_memory_reviews.py`,
  `semantic_memory_assertions.py`,
  `semantic_memory_facts.py`, and
  `semantic_memory_governance.py`.
- Reduced `app/db/model_domains/semantic_memory.py` to a `53`-line composition
  surface.

Required work:

- Split ontology or graph snapshot ownership away from registry vocabulary
  ownership, document semantic review or pass ownership, assertion or fact
  lineage ownership, and governance-event ownership.
- Prefer the six-family split in this plan:
  `semantic_memory_snapshots.py`, `semantic_memory_registry.py`,
  `semantic_memory_reviews.py`, `semantic_memory_assertions.py`,
  `semantic_memory_facts.py`, and `semantic_memory_governance.py`,
  unless Milestone 0 captured a narrower and clearly documented alternative.
- Keep only the narrow domain-family composition or import-forwarding surface in
  `app/db/model_domains/semantic_memory.py`.
- Expand `tests/db_model_contract_domains/semantic_memory.py` and the matching
  unit or integration harness only as needed to preserve exact DDL coverage.
- If shared harness roots would regrow, move semantic-memory-specific import and
  metadata assertions into focused sibling test files.

Acceptance criteria:

- `app/db/model_domains/semantic_memory.py` closes at or below `600` lines.
- Any new semantic-memory family-local owner file created by this milestone
  closes at or below `600` lines.
- Exact table, index, unique-constraint, vector-dimension, and computed-SQL
  contracts remain stable with equivalent or broader contract coverage.

### Milestone 3 - Claim Support Residual Owner Split

Outcome label: resolved

Purpose: reduce `app/db/model_domains/claim_support.py` to a narrow
domain-family composition or compatibility surface.

Closeout result on 2026-05-18 local:

- Moved the claim-support ORM family into `claim_support_waivers.py`,
  `claim_support_fixtures.py`, `claim_support_evaluations.py`, and
  `claim_support_policy_impacts.py`.
- Reduced `app/db/model_domains/claim_support.py` to a `31`-line composition
  surface.

Required work:

- Split waiver ledger or escalation ownership away from fixture-set or corpus
  ownership, calibration or evaluation ownership, and policy-impact ownership.
- Prefer the four-family split in this plan:
  `claim_support_waivers.py`, `claim_support_fixtures.py`,
  `claim_support_evaluations.py`, and
  `claim_support_policy_impacts.py`, unless Milestone 0 captured a narrower and
  clearly documented alternative.
- Keep only the narrow domain-family composition or import-forwarding surface in
  `app/db/model_domains/claim_support.py`.
- Expand `tests/db_model_contract_domains/claim_support.py` and the matching
  unit or integration harness only as needed to preserve exact DDL coverage.
- If shared harness roots would regrow, move claim-support-specific import and
  metadata assertions into focused sibling test files.

Acceptance criteria:

- `app/db/model_domains/claim_support.py` closes at or below `600` lines.
- Any new claim-support family-local owner file created by this milestone
  closes at or below `600` lines.
- Exact table, index, unique-constraint, and relationship contracts remain
  stable with equivalent or broader contract coverage.

### Milestone 4 - Shared Harness And Durable Closeout

Outcome label: resolved

Purpose: close the residual DB-model owner-family packet without leaving the
shared harness roots or routing docs as the next hidden hotspot.

Closeout result on 2026-05-18 local:

- Kept `tests/db_model_contract.py` as the narrow shared manifest root while
  preserving domain-local contract detail in
  `tests/db_model_contract_domains/`.
- Reduced `tests/unit/test_db_model_import_compatibility.py` and
  `tests/integration/test_db_model_metadata.py` to `457` and `472` lines by
  moving owner-family checks into focused sibling suites.
- Refreshed the routed docs and governance artifacts so the next bounded packet
  is now `docs/hotspot_routing_trap_resolution_milestone_plan.md`.

Required work:

- Keep `tests/db_model_contract.py` as the narrow shared manifest root and move
  any necessary domain-specific expansions into
  `tests/db_model_contract_domains/`.
- If needed, split `tests/unit/test_db_model_import_compatibility.py` and
  `tests/integration/test_db_model_metadata.py` into focused sibling files so
  the shared roots remain narrow.
- Refresh `config/improvement_cases.yaml`, `config/hygiene_policy.yaml`,
  `docs/data_model_boundary_plan.md`, `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`, and
  `docs/boring_change_architecture_milestone_plan.md` so the residual DB-model
  owners are routed explicitly and the deployed facade case remains closed.

Acceptance criteria:

- `tests/unit/test_db_model_import_compatibility.py` and
  `tests/integration/test_db_model_metadata.py` each close at or below `600`
  lines if they remain shared roots.
- Any new focused DB-model harness sibling file created by this packet closes
  at or below `800` lines.
- The three extracted domain owners no longer appear in hygiene as inherited
  over-budget files under the deployed facade-only case.
- The final routing docs agree that `app/db/models.py` remains the closed public
  facade and that the extracted domain owners are the surfaces this packet
  resolved.

## Required Implementation Artifacts

- `docs/db_models_residual_owner_family_milestone_plan.md`
- updated routing docs:
  `docs/data_model_boundary_plan.md`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  `docs/boring_change_architecture_milestone_plan.md`
- updated governance artifacts:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`
- focused residual owner files under `app/db/model_domains/`
- expected default owner files:
  `app/db/model_domains/audit_and_evidence_*.py`,
  `app/db/model_domains/semantic_memory_*.py`,
  `app/db/model_domains/claim_support_*.py`
- updated domain-local DB-model contract fragments
- any focused DB-model harness sibling files created by Milestone 0 or 4

## Required Documentation And Handoff Updates

- Update this plan with milestone status, verification, and closeout commit
  hashes as each milestone lands.
- Update `docs/data_model_boundary_plan.md` whenever the routed residual
  DB-model owner family changes shape or the next remaining domain candidate
  changes.
- Update `docs/SESSION_HANDOFF.md` whenever this packet changes position in the
  queued architecture backlog or when one of the residual owner cases changes
  lifecycle state.
- Update `docs/agentic_architecture_index.md` when this packet moves from
  drafted to active, from active to closed, or routes a narrower successor.
- Update `docs/boring_change_architecture_milestone_plan.md` so the umbrella
  brief names this packet explicitly instead of treating the DB-model residuals
  as an implicit `app/db/models.py` trap.

## Required Verification Gates

- Milestone 0 refresh:
  `git status -sb`
  `uv run docling-system-architecture-quality-report --summary`
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
  `uv run docling-system-hygiene-check`
  `uv run docling-system-improvement-case-summary`
  `wc -l app/db/models.py app/db/model_domains/audit_and_evidence.py app/db/model_domains/semantic_memory.py app/db/model_domains/claim_support.py tests/db_model_contract.py tests/unit/test_db_model_import_compatibility.py tests/integration/test_db_model_metadata.py tests/unit/test_db_models_facade_contract.py`
- Implementation milestones:
  `git diff --check`
  `uv run ruff check app/db tests/db_model_contract.py tests/db_model_contract_domains tests/unit/test_db_model_import_compatibility*.py tests/unit/test_db_models_facade_contract.py tests/integration/test_db_model_metadata*.py config/improvement_cases.yaml config/hygiene_policy.yaml`
  `uv run pytest -q tests/unit/test_db_model_import_compatibility.py tests/unit/test_db_model_import_compatibility_*.py tests/unit/test_db_models_facade_contract.py`
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py tests/integration/test_db_model_metadata_*.py`
  `uv run --extra dev alembic heads`
  `uv run --extra dev alembic current`
  `uv run --extra dev alembic upgrade head`
  `uv run --extra dev alembic check`
  `uv run docling-system-improvement-case-validate`
  `uv run docling-system-improvement-case-summary`
  `uv run docling-system-architecture-inspect`
  `uv run docling-system-capability-contracts`
  `uv run docling-system-hotspot-prevention-check --strict`
  `uv run docling-system-hygiene-check`
  `uv run docling-system-architecture-quality-report --summary`
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
  `wc -l app/db/models.py app/db/model_domains/audit_and_evidence.py app/db/model_domains/semantic_memory.py app/db/model_domains/claim_support.py tests/db_model_contract.py tests/unit/test_db_model_import_compatibility.py tests/integration/test_db_model_metadata.py tests/unit/test_db_models_facade_contract.py`
- Final runtime verification:
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- `app/db/models.py` remains a pure compatibility facade at or below `159`
  lines.
- `app/db/model_domains/audit_and_evidence.py`,
  `app/db/model_domains/semantic_memory.py`, and
  `app/db/model_domains/claim_support.py` each close at or below `600` lines.
- Any new family-local DB-model owner file created by this packet closes at or
  below `600` lines.
- `tests/db_model_contract.py` remains a narrow shared manifest root, and the
  shared import or metadata harness roots do not become the next hidden
  hotspot.
- Exact DDL coverage remains intact. Do not weaken the current DB-model contract
  stack; replacement coverage must provide equivalent or broader contract
  coverage.
- Residual owner routing no longer hides the extracted domain files under the
  deployed facade-only case.
- The final handoff, data-model boundary plan, architecture index, and umbrella
  brief all agree on the resolved state and the next backlog item.

## Stop Conditions

- Stop if Milestone 0 shows the selected extracted domain owners are no longer
  the honest residual DB-model surfaces.
- Stop if the only way to reduce a domain owner is to move ORM implementations
  or enum ownership back into `app/db/models.py`.
- Stop if a split cannot preserve exact Alembic and Postgres metadata behavior.
- Stop if implementation only works by creating another oversized shared
  `model_domains` sink or another oversized shared test root.
- Stop before commit if focused DB-model verification or the full DB-backed
  suite fails.
- Stop before commit if the active cycle-lane dirty worktree cannot be kept
  separate from this packet’s milestone slice.

## Local Commit Closeout Policy

Every milestone is complete only after verification passes, the required docs
and handoff updates land, and a local atomic commit records the milestone
slice. Before that point the milestone is ready-to-close, not complete.

For each milestone:

- stage only the verified residual DB-model owner-family slice
- leave unrelated dirty or untracked files alone
- include code, tests, governance artifacts, and docs or handoff changes that
  describe the milestone in the same commit
- record the closeout commit hash in this plan and in `docs/SESSION_HANDOFF.md`
- do not mark a milestone complete if verification passed only because the
  checks got easier

## Residual Risks And Next Milestone Routing

- This packet is now the latest locally resolved bounded implementation brief
  in the current checkout after the locally verified closeout of
  `docs/agent_task_residual_owner_family_milestone_plan.md`.
- If one domain family still honestly exceeds `600` lines after the narrower
  split, mark that exact subfamily `reduced`, give it dedicated owner routing,
  and spin a fresh narrower follow-on rather than widening this packet.
- The next routed bounded packet is now
  `docs/hotspot_routing_trap_resolution_milestone_plan.md`.
- After that packet, return to
  `docs/boring_change_architecture_milestone_plan.md` for the next selected
  large-file or model-boundary lane instead of reopening `app/db/models.py`.

## Closeout Checklist

- [x] Milestone 0 freshness readback captured and residual owner routing bootstrapped
- [x] `audit_and_evidence.py` reduced below packet threshold
- [x] `semantic_memory.py` reduced below packet threshold
- [x] `claim_support.py` reduced below packet threshold
- [x] Shared DB-model harness roots kept narrow or split into focused siblings
- [x] Exact Alembic and Postgres metadata verification passed
- [x] Improvement-case and hygiene routing updated
- [x] Plan, data-model boundary plan, handoff, architecture index, and umbrella brief updated
- [ ] Atomic closeout commit recorded for each completed milestone

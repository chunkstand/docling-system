# Audit And Evidence Model-Domain Milestone Plan

Date: 2026-05-11 local
Status: implemented locally on 2026-05-11; scoped issue resolved and broader
owner case reduced
Owner context: bounded follow-up under the open architecture-governance owner
case for `IC-F2A8110185EB` / `app/db/models.py`

## Purpose

Resolve the routed `audit and evidence` ORM concern inside
`app/db/models.py` by moving the audit/export, evidence manifest, trace, and
technical-report readiness/feedback tables into a focused owner module while
preserving the public `app.db.models` import contract, the exact Postgres
schema contract, and current runtime behavior. This milestone closes the
audit-and-evidence owner slice itself; it does not claim to retire the broader
`IC-F2A8110185EB` hotspot unless the live architecture-quality report no
longer flags `app/db/models.py`.

## Current Evidence

Live preflight signals refreshed before implementation:

```text
uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=649.6
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/agent_task_actions.py,
    app/services/evidence.py,
    app/schemas/agent_tasks.py
  ]

uv run docling-system-improvement-case-summary
  case_count=26
  status_counts.open=25
  oldest_open_case_id=IC-F2A8110185EB

wc -l app/db/models.py
  3090 app/db/models.py

uv run --extra dev alembic check
  No new upgrade operations detected.
```

Repo-current routing evidence before the move:

- `docs/agent_task_model_domain_milestone_plan.md` closed the prior bounded
  split and routed the next `app/db/models.py` concern to the audit-and-evidence
  family.
- `docs/data_model_boundary_plan.md` and `docs/SESSION_HANDOFF.md` routed the
  same follow-up:
  `AuditBundleExport`,
  `AuditBundleValidationReceipt`,
  `EvidencePackageExport`,
  `EvidenceManifest`,
  `TechnicalReportReleaseReadinessDbGate`,
  `TechnicalReportClaimRetrievalFeedback`,
  `EvidenceTraceNode`,
  `EvidenceTraceEdge`, and
  `ClaimEvidenceDerivation`.
- `tests/db_model_contract.py` already classified those symbols under
  `audit_and_evidence`, but it did not yet expose dedicated table-column
  coverage or exact required index / unique-constraint coverage for the moved
  tables.

## Goal

Move the routed audit-and-evidence ORM family into
`app/db/model_domains/audit_and_evidence.py` behind the existing
`app.db.models` compatibility facade, with stronger shared contract coverage
than existed before the move.

## Non-Goals

- Do not claim to retire the full `IC-F2A8110185EB` hotspot unless the live
  architecture-quality report stops flagging `app/db/models.py`.
- Do not change table names, column names, check-constraint value sets, named
  indexes, named unique constraints, foreign-key targets, or `ondelete`
  behavior.
- Do not redesign audit bundle generation, evidence packaging, provenance
  manifests, trace graph semantics, or technical-report readiness logic.
- Do not mix semantic-memory or claim-support rows into this milestone.

## Scope

In scope:

- `AuditBundleExport`
- `AuditBundleValidationReceipt`
- `EvidencePackageExport`
- `EvidenceManifest`
- `TechnicalReportReleaseReadinessDbGate`
- `TechnicalReportClaimRetrievalFeedback`
- `EvidenceTraceNode`
- `EvidenceTraceEdge`
- `ClaimEvidenceDerivation`
- a focused owner module under `app/db/model_domains/`
- `app.db.models` compatibility re-exports
- shared metadata contract expansion for the moved tables
- Postgres `create_all(...)` and Alembic drift verification for the moved
  models
- routing-doc updates for the moved concern and the next remaining
  `IC-F2A8110185EB` follow-up

Out of scope:

- semantic-memory rows such as `SemanticOntologySnapshot`,
  `SemanticConcept`, `SemanticAssertion`, `SemanticEntity`, and
  `SemanticGovernanceEvent`
- claim-support rows such as
  `ClaimSupportReplayAlertFixtureCoverageWaiverLedger`,
  `ClaimSupportFixtureSet`,
  `ClaimSupportCalibrationPolicy`,
  `ClaimSupportEvaluation`, and related replay-alert corpus / policy-impact
  tables

## Owner Surfaces

- hotspot facade: `app/db/models.py`
- new owner module: `app/db/model_domains/audit_and_evidence.py`
- compatibility and metadata harness:
  `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`,
  `tests/integration/test_db_model_metadata.py`
- migration / schema gates:
  `uv run --extra dev alembic *`
- routing and current-state docs:
  this plan, `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`, and `docs/SESSION_HANDOFF.md`
- owner-case routing:
  `config/improvement_cases.yaml`,
  `config/hygiene_policy.yaml`

## Placement Rules

- Keep `app/db/models.py` as the public compatibility facade; do not update
  callers to import directly from `app/db/model_domains/audit_and_evidence.py`
  as part of this milestone.
- Keep the routed audit/export, manifest, trace, and technical-report
  readiness/feedback ORM family together in the new module.
- Add shared contract constants for the moved tables in
  `tests/db_model_contract.py` instead of duplicating expectations inside test
  bodies.
- Preserve exact index names, exact index column ordering, exact
  unique-constraint names and column ordering, and relationship targets.

## Weak-Point Prevention Contract

Weak point forecast:
This split could look clean while silently weakening the schema harness,
dropping exact index or unique-constraint checks for audit/evidence tables,
changing emitted DDL, or preserving imports only for a subset of the moved
symbols.

Owner surface:
`app/db/models.py`, `app/db/model_domains/audit_and_evidence.py`, the shared
DB model contract tests, Alembic verification, and the routing docs that
define what counts as resolved for this milestone.

Prevention gate:

- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
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
- `git diff --check`

Fail threshold:

- any moved symbol remains defined as primary ORM code in `app/db/models.py`
- any public `app.db.models` import for the moved symbols breaks
- the moved tables lose exact column coverage, exact index coverage, or exact
  unique-constraint coverage in the shared harness
- Alembic emits unexpected drift or Postgres `Base.metadata.create_all(...)`
  no longer matches the supported schema shape

## Milestone Sequence

### Milestone 0: Preflight Baseline Lock

Outcome label: `reduced`

Completed locally on 2026-05-11:

- refreshed live routing, line-count, architecture-quality, and Alembic
  baseline signals before editing
- confirmed `docs/agent_task_model_domain_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`, and `docs/SESSION_HANDOFF.md` all routed
  the next owner slice to the audit-and-evidence family
- confirmed DB-backed verification was available and not silently skipped
- identified the missing shared audit-and-evidence metadata contract coverage
  as the required first implementation step

### Milestone 1: Audit-And-Evidence Contract And Owner Split

Outcome label: `resolved`

Completed locally on 2026-05-11:

- added `app/db/model_domains/audit_and_evidence.py`
- moved all nine routed audit-and-evidence ORM classes into the new owner
  module
- replaced the in-file ORM implementations in `app/db/models.py` with
  compatibility re-exports so public imports remain unchanged
- expanded `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` with dedicated
  audit-and-evidence table columns, exact index-column ordering, and exact
  unique-constraint column ordering coverage
- reduced `app/db/models.py` from 3,090 lines to 2,089 while keeping the new
  owner module at 1,053 lines

### Milestone 2: Closeout And Next Routing

Outcome label: `reduced`

Closeout evidence refreshed locally on 2026-05-11:

- `uv run docling-system-architecture-quality-report --summary` now reports
  `max_hotspot_risk_score=624.43` with `app/db/models.py` still first in
  `top_hotspot_paths`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
  now reports `app/db/models.py` at 2,089 lines with hotspot score `160853`
- the broader `IC-F2A8110185EB` owner case remains `reduced`, not `resolved`,
  because `app/db/models.py` is still in the governed hotspot list
- the next remaining routed candidate is now the `claim support` family:
  `ClaimSupportReplayAlertFixtureCoverageWaiverLedger`,
  `ClaimSupportReplayAlertFixtureCoverageWaiverEscalation`,
  `ClaimSupportFixtureSet`,
  `ClaimSupportReplayAlertFixtureCorpusSnapshot`,
  `ClaimSupportReplayAlertFixtureCorpusRow`,
  `ClaimSupportCalibrationPolicy`,
  `ClaimSupportEvaluation`,
  `ClaimSupportEvaluationCase`, and
  `ClaimSupportPolicyChangeImpact`

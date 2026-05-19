# Documents Service Boundary Milestone Plan

Date: 2026-05-18 local / 2026-05-18 UTC
Status: resolved locally in the current checkout through the 2026-05-18
documents-service boundary closeout. `app/services/documents.py` is now a
`49`-line compatibility facade, the new document-local owners stay under the
default `600`-line budget, and the next routed packet after this closeout was
`docs/cross_cutting_verification_roots_milestone_plan.md`, which is now also
resolved locally.
Owner context: narrower service-boundary packet for `app/services/documents.py`
under `IC-6C3E1A7B9D52`. The broader cross-cutting packet and the adjacent
architecture-governance pair under `IC-08C078FD4F45` remain active outside
this packet.

## Purpose

Resolve the `app/services/documents.py` replacement-monolith risk without
dragging the unrelated verification-root and architecture-governance backlog
into the same implementation slice.

The current weakness is not just line count. `app/services/documents.py`
currently mixes:

- upload and local-file PDF validation
- staged admission, duplicate detection, idempotent replay, and remote
  backpressure
- row locking, recovery-run creation, and reprocess orchestration
- run summary shaping and progress projection
- document list or detail projection
- the document-side latest-evaluation access seam

## 2026-05-18 Closeout Update

- `app/services/documents.py` now measures `49` lines as a compatibility
  facade after ingest ownership moved into
  `app/services/document_ingest.py` at `233` lines and run-queue plus
  reprocess ownership moved into
  `app/services/document_run_queue.py` at `324` lines, while read ownership
  remains in `app/services/document_run_views.py` at `276` lines.
- `config/hygiene_policy.yaml` now exact-ratchets all four document-family
  owners under `IC-6C3E1A7B9D52`, so the split does not simply move the sink
  into a new sibling.
- The focused document-service unit slice passed at `75 passed`, and the
  DB-backed document roundtrip plus batch-ingest slice passed at `5 passed`, so
  this packet is now a verified closeout rather than a further narrowing
  backlog item.

That mixed ownership makes the document lifecycle expensive to change and
creates a high risk that future sessions will keep shortening nearby owners by
dumping more work into `documents.py`.

## Current Evidence

- The live line-count snapshot on 2026-05-18 now reports
  `app/services/documents.py` at `49`,
  `app/services/document_ingest.py` at `233`,
  `app/services/document_run_queue.py` at `324`, and
  `app/services/document_run_views.py` at `276`.
- `config/hygiene_policy.yaml` now exact-ratchets
  `app/services/documents.py`,
  `app/services/document_ingest.py`,
  `app/services/document_run_queue.py`, and
  `app/services/document_run_views.py`
  under `IC-6C3E1A7B9D52`.
- `config/improvement_cases.yaml` records the broader cross-cutting residual
  family under `IC-6C3E1A7B9D52`; the documents-service sink is now closed
  locally and the remaining open family work shifts to the verification roots.
- `app/services/capabilities/run_lifecycle.py` currently treats
  `app.services.documents` as the compatibility surface for:
  `list_documents`, `ingest_upload`, `get_document_detail`,
  `list_document_runs`, `get_document_run_summary`, and
  `reprocess_document`.
- `app/api/routers/documents.py` binds externally reachable routes directly
  through the run-lifecycle and evaluation capability seams. Route behavior and
  response models must remain stable for:
  `/documents`,
  `/documents/{document_id}`,
  `/documents/{document_id}/runs`,
  `/runs/{run_id}`,
  `/documents/{document_id}/evaluations/latest`,
  `/documents/{document_id}/evaluations/latest/explain`, and
  `/documents/{document_id}/reprocess`.
- The document service still owns local-ingest compatibility edges used outside
  the API path:
  `app/services/ingest_batches.py`,
  `app/cli.py`, and
  `app/cli_commands/ingest.py`
  currently depend on `allowed_ingest_roots(...)` and
  `ingest_local_file(...)`.
- Earlier evaluation-boundary work intentionally preserved the latest-evaluation
  seam in `documents.py`; this packet must preserve that public behavior rather
  than re-own evaluation reads inside new document owners.
- The broader cross-cutting packet remains active in
  `docs/cross_cutting_large_file_residual_milestone_plan.md`, but the user has
  selected the documents-service sink as the next narrower slice before the
  remaining governance and verification-root debt.

## Goal

Resolve the scoped `documents.py` sink so that:

- `app/services/documents.py` becomes a narrow compatibility facade and
  orchestration seam at or below `350` lines
- document-ingest, run-queue, and read or projection ownership no longer live
  together in the same root
- `app.services.documents`,
  `app/services/capabilities/run_lifecycle.py`, and
  `app/api/routers/documents.py`
  preserve import-stable and behavior-stable public seams
- local-file ingest remains compatible for CLI and batch-ingest callers
- the latest-evaluation document route family remains delegated through the
  evaluation owner family rather than sliding back into document-local logic
- no new document-family owner exceeds `600` lines without same-milestone
  routing and hygiene ownership

The scoped issue is `resolved` when the mixed ingest, queue, and read concern
families no longer co-reside in `app/services/documents.py`, the public seams
stay stable, and `documents.py` no longer appears in the live `>800` backlog.

## Non-Goals

- No table, chunk, or figure service rewrite; those owners already live in
  `app/services/tables.py`, `app/services/chunks.py`, and
  `app/services/figures.py`.
- No evaluation-service redesign, schema change, or route redesign.
- No parser, run-processor, search, claim-support, or agent-task refactor in
  this packet.
- No split of the unrelated cross-cutting verification monoliths owned by the
  parent packet.
- No moving logic into `app/services/runs.py`, `app/services/ingest_batches.py`,
  or `app/services/evaluation_reads.py` as a hidden sink.
- No weakening of API, CLI, local-ingest, or DB-backed document lifecycle
  verification just to satisfy a line-count target.

## Scope

In scope:

- `app/services/documents.py`
- `app/services/capabilities/run_lifecycle.py`
- `app/api/routers/documents.py`
- `app/services/ingest_batches.py`
- `app/cli.py`
- `app/cli_commands/ingest.py`
- focused new document-family owners, expected to be
  `app/services/document_ingest.py`,
  `app/services/document_run_queue.py`, and
  `app/services/document_reads.py`,
  or equivalently narrow document-local names selected during Milestone 0 if a
  naming conflict appears
- `tests/unit/test_document_service.py`
- `tests/unit/test_documents_api.py`
- `tests/unit/test_documents_api_artifacts.py`
- `tests/unit/test_documents_api_semantics.py`
- `tests/unit/test_cli_ingest.py`
- `tests/integration/test_postgres_roundtrip.py`
- `tests/integration/test_batch_ingest_roundtrip.py`
- `config/improvement_cases.yaml` and `config/hygiene_policy.yaml` if any new
  document-family owner between `401` and `600` lines needs explicit routing
- this plan plus the affected routing or handoff docs

Out of scope:

- `app/services/improvement_cases.py`
- `tests/unit/test_improvement_case_intake.py`
- `tests/unit/test_agent_task_verifications.py`
- `tests/unit/test_docling_parser.py`
- `tests/integration/test_search_harness_releases.py`
- `tests/integration/test_claim_support_policy_activation_roundtrip.py`
- the final zero-oversized closeout owned by
  `docs/residual_large_file_backlog_milestone_plan.md`

## Owner Surfaces

- `app/services/documents.py`
- the extracted document-family owners created by this packet
- `app/services/capabilities/run_lifecycle.py`
- `app/api/routers/documents.py`
- `app/services/ingest_batches.py`
- `app/cli.py`
- `app/cli_commands/ingest.py`
- the document-family unit and integration roots listed above
- routing and hygiene docs if new owner files require same-milestone binding

## Placement Rules

- Keep upload and local-file PDF validation, staged admission, duplicate or
  idempotent replay handling, and remote backpressure in document-ingest or
  document-queue owners, not in `runs.py`, `ingest_batches.py`, or CLI glue.
- Keep row locking, next-run numbering, recovery-run creation, and reprocess
  orchestration in a document-local queue or lifecycle owner, not in
  `app/services/runs.py`.
- Keep document list or detail projection and run-summary shaping in
  document-read owners, not in tables, figures, or evaluation owners.
- Preserve `app.services.documents` as the import-stable compatibility surface
  for the symbols currently consumed through the run-lifecycle capability and
  CLI or batch-ingest paths.
- Preserve the `run_lifecycle` capability surface and
  `app/api/routers/documents.py` route bindings; do not point public routes at
  raw owner modules.
- Preserve the existing latest-evaluation delegation path through the
  evaluation-family owners; do not reintroduce evaluation-read ownership into
  new document-local owners.
- Do not create a generic `document_common.py`, `document_utils.py`, or
  `documents_helpers.py` sink. New owners must be named by concern family.
- Any new document-family owner that lands between `401` and `600` lines must
  receive same-milestone routing and an exact hygiene ratchet. No new owner may
  exceed `600` lines.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The split shortens `documents.py` by moving mixed lifecycle logic into `runs.py`, `ingest_batches.py`, or another nearby sink. | `app/services/documents.py`, extracted document-family owners, `app/services/runs.py`, `app/services/ingest_batches.py` | focused `ruff`, `wc -l` review, hygiene check, architecture probe | a nearby non-document owner absorbs document-ingest or document-read logic, or a new owner exceeds `600` lines | temporarily route staged-admission helpers into `runs.py` or directory-ingest helpers into `ingest_batches.py` and confirm closeout rejects the slice | a future session chooses the nearest existing owner instead of the document-local boundary |
| Public route or capability behavior changes while internal code moves. | `app/services/capabilities/run_lifecycle.py`, `app/api/routers/documents.py`, document-family tests | unit API route tests, capability-contract tests, DB-backed document roundtrip tests | any route payload, status code, location header, or delegated latest-evaluation behavior changes unexpectedly | remove the `Location` header or bypass the evaluation delegation and confirm tests fail | a later session points the router directly at a raw owner module and silently changes the public seam |
| Local-file ingest compatibility breaks for CLI or batch-ingest flows. | `app/services/documents.py`, `app/services/ingest_batches.py`, `app/cli.py`, `app/cli_commands/ingest.py` | `tests/unit/test_cli_ingest.py`, `tests/integration/test_batch_ingest_roundtrip.py`, focused document-service tests | `allowed_ingest_roots(...)` or `ingest_local_file(...)` no longer behave compatibly for non-API callers | swap CLI or batch-ingest to a non-forwarding symbol and confirm focused tests fail | a future session preserves the API path but forgets the local operator and batch-ingest entrypoints |
| `documents.py` stops being a monolith only because coverage or failure-path assertions were deleted. | `tests/unit/test_document_service.py`, `tests/unit/test_documents_api.py`, `tests/unit/test_documents_api_artifacts.py`, `tests/unit/test_documents_api_semantics.py`, `tests/integration/test_postgres_roundtrip.py` | focused unit slice plus DB-backed integration slice | line count falls but upload, reprocess, local-ingest, or failure-artifact assertions are removed or weakened | replace a real document lifecycle assertion block with a smoke assertion and confirm review or tests reject the change | a future session optimizes for file size and a green subset instead of contract fidelity |

## Milestone Sequence

### Milestone 0. Rebaseline And Boundary Lock
Outcome label: reduced

Refresh the live line counts, importer set, route bindings, and verification
roots for the selected document-service slice before code motion starts.

This milestone must:

- freeze the current public symbol list consumed through
  `app.services.documents`,
  `app/services/capabilities/run_lifecycle.py`,
  `app/services/ingest_batches.py`,
  `app/cli.py`, and
  `app/cli_commands/ingest.py`
- capture the current concern-family map inside `documents.py`
- confirm the latest-evaluation route family still delegates through the
  evaluation owner family
- confirm no concurrent local edits are already rewriting `documents.py` in a
  conflicting direction

### Milestone 1. Ingest And Queue Extraction
Outcome label: reduced

Extract upload or local-ingest validation, staged admission, duplicate or
idempotent replay handling, remote backpressure, row locking, recovery-run
creation, and reprocess orchestration into focused document-family owners while
keeping `app.services.documents` as the compatibility facade.

Preferred owner targets:

- `app/services/document_ingest.py`
- `app/services/document_run_queue.py`

This milestone must preserve CLI and batch-ingest compatibility and must not
move the selected concern families into `runs.py` or `ingest_batches.py`.

### Milestone 2. Read And Projection Extraction
Outcome label: reduced

Extract document list or detail projection, run-summary shaping, and related
read helpers into a focused document-read owner while preserving the
run-lifecycle capability and route behavior.

Preferred owner target:

- `app/services/document_reads.py`

This milestone must keep latest-evaluation delegation in the evaluation family
and must not move document-active chunk, table, or figure reads back into
`documents.py`.

### Milestone 3. Closeout
Outcome label: resolved

Close the packet only after:

- `app/services/documents.py` is at or below `350` lines
- the routed document-service sink is no longer part of the live `>800`
  backlog
- no new document-family owner exceeds `600` lines
- any `401-600` owner has same-milestone routing and hygiene ownership
- the focused unit and DB-backed integration gates are green
- the routing docs and handoff all point future sessions at the correct next
  packet

## Required Implementation Artifacts

- narrowed `app/services/documents.py` compatibility facade
- focused document-family owners for ingest, queue, and read or projection
  ownership
- any required forwarding wrappers in
  `app/services/capabilities/run_lifecycle.py`,
  `app/services/ingest_batches.py`,
  `app/cli.py`, or
  `app/cli_commands/ingest.py`
- document-family unit and integration coverage updates that prove the moved
  seams remain behavior-stable
- refreshed routing config if new document-family owners need same-milestone
  binding

## Required Documentation And Handoff Updates

- `docs/documents_service_boundary_milestone_plan.md`
- `docs/cross_cutting_large_file_residual_milestone_plan.md`
- `docs/residual_large_file_backlog_milestone_plan.md`
- `docs/boring_change_architecture_milestone_plan.md`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/services/documents.py app/services/document_ingest.py app/services/document_run_queue.py app/services/document_run_views.py app/services/capabilities/run_lifecycle.py app/api/routers/documents.py app/services/ingest_batches.py app/cli.py app/cli_commands/ingest.py tests/unit/test_document_service.py tests/unit/test_documents_api.py tests/unit/test_documents_api_artifacts.py tests/unit/test_documents_api_semantics.py tests/unit/test_cli_ingest.py tests/integration/test_postgres_roundtrip.py tests/integration/test_batch_ingest_roundtrip.py`
- `uv run pytest -q tests/unit/test_document_service.py tests/unit/test_documents_api.py tests/unit/test_documents_api_artifacts.py tests/unit/test_documents_api_semantics.py tests/unit/test_cli_ingest.py tests/unit/test_capability_contracts.py tests/unit/test_api_architecture.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_batch_ingest_roundtrip.py`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`

## Acceptance Criteria

- `app/services/documents.py` closes at or below `350` lines and no longer
  contains mixed ingest, queue, and read concern families.
- `app.services.documents` remains the import-stable compatibility surface for
  the symbols consumed through the run-lifecycle capability and local-ingest
  callers.
- `app/api/routers/documents.py` keeps the current route family, response-model
  contracts, handled-error behavior, and `Location` header behavior for create
  and reprocess responses.
- `app/services/capabilities/run_lifecycle.py` still delegates document upload,
  detail, run-summary, and reprocess behavior through the preserved document
  facade rather than raw owner modules.
- CLI and batch-ingest flows remain green through focused verification for
  `allowed_ingest_roots(...)` and `ingest_local_file(...)`.
- No new document-family owner exceeds `600` lines, and any new owner between
  `401` and `600` lines is routed in `config/improvement_cases.yaml` and
  `config/hygiene_policy.yaml` during the same milestone.
- The final architecture probe no longer lists `app/services/documents.py` in
  the live `>800` backlog.

## Stop Conditions

- Stop if a fresh rebaseline shows `app/services/documents.py` is already being
  split by unrelated local work that cannot be separated safely.
- Stop if preserving the public route or capability seam would require a broad
  API redesign, DB schema change, or runtime rewrite.
- Stop if the planned extraction pushes document lifecycle ownership into
  `runs.py`, `ingest_batches.py`, or evaluation owners instead of document-local
  modules.
- Stop if a green result depends on deleting or weakening document lifecycle,
  CLI ingest, or DB-backed integration assertions instead of preserving them in
  focused owners.

## Local Commit Closeout Policy

- Close this packet with one atomic local commit containing only the narrowed
  document-service slice, focused tests, any required routing or hygiene
  updates, and the aligned plan or handoff docs for this packet.
- Stage only the verified milestone slice and leave unrelated dirty or
  untracked files alone.
- Treat the packet as ready-to-close, not complete, until that local atomic
  commit exists and its hash is recorded in `docs/SESSION_HANDOFF.md`.

## Residual Risks And Next Milestone Routing

- This packet resolves the `documents.py` sink only. The broader cross-cutting
  packet later resolved its verification branch and governance pair under
  `IC-08C078FD4F45` in separate bounded closeouts.
- After this packet closed, the next active code-owning follow-on became
  `docs/cross_cutting_verification_roots_milestone_plan.md`, followed by
  `docs/improvement_case_governance_self_hosting_milestone_plan.md`; both are
  now also resolved locally in the current checkout.
- Do not reactivate `docs/shared_verification_roots_milestone_plan.md` until
  the cross-cutting parent packet is honestly reduced again and the large-file
  queue ahead of it is current.

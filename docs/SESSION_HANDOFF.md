# Session Handoff

Date: 2026-04-18 local / 2026-04-18 UTC
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `main`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Latest committed checkpoint before this handoff update: `0c0ad92` (`Add system review document`)

## Session Outcome

This session focused on a full-system review, Priority 1 hardening work, a broader edge-hardening roadmap, and a final gap-closing pass on the newly hardened edge surfaces.

At the end of the session:

- local `main` includes the full hardening stack from this session
- the working tree is clean after this handoff update is committed
- the current codebase has stronger defaults at the system boundary:
  - explicit local vs remote API mode semantics
  - API-key protection for remote mutating and reading access
  - capability-gated high-power remote routes
  - storage-owned artifact delivery
  - shared ingest admission with remote-mode backpressure
  - command idempotency for document create and reprocess
  - more consistent machine-readable error responses on exposed search/task edges

## What Was Accomplished

### 1. Full System Review

A fresh full-system review was completed and saved in:

- [docs/system-review-2026-04-18.md](/Users/chunkstand/Documents/docling-system/docs/system-review-2026-04-18.md)

The review identified the original Priority 1 risks:

- unauthenticated or weakly protected network exposure
- HTTP ingest skipping some of the stricter admission safeguards
- race-prone duplicate ingest and reprocess flows

It also identified broader edge concerns around auth, ingress consistency, artifact serving, idempotency, and remote-safe defaults.

### 2. Priority 1 Hardening

Priority 1 was fixed vertically first.

Commit:

- `19746ab` `Fix priority 1 hardening issues`

What landed:

- safer API exposure defaults
- upload validation and cleanup hardening
- concurrency-safe duplicate/reprocess behavior
- targeted tests for API runtime, document service, cleanup, and document APIs

### 3. Edge-Hardening Roadmap Implementation

The broader roadmap was then implemented milestone by milestone.

Commits:

- `f91160c` `Add explicit local and remote API modes`
- `10e3007` `Harden artifact delivery through storage-owned paths`
- `31acb5f` `Add shared ingest admission with remote backpressure`
- `dd8bf48` `Add structured errors and command idempotency`
- `cf4626d` `Gate remote capabilities and expose durable run resources`

What these milestones changed:

- API mode is now explicit:
  - `local` mode remains loopback-oriented
  - `remote` mode requires an API key
  - runtime metadata now exposes resolved API mode
- artifact delivery no longer trusts raw DB-stored filesystem paths:
  - canonical storage paths are preferred
  - out-of-root file serving is blocked
- ingest admission is now shared across upload and local-file flows:
  - staged-file admission validates size, PDF shape, page limits, dedupe, and queue entry more consistently
  - remote mode can reject new document work when inflight run capacity is exhausted
- document create and reprocess now support idempotency keys:
  - duplicate retries replay the original durable response
  - mismatched reuse of the same idempotency key is rejected
- mutating remote routes now require specific capabilities:
  - document upload
  - document reprocess
  - agent-task writes
  - search query/feedback/replay/evaluation
  - chat query/feedback
- async creation surfaces now return better durable contracts:
  - `GET /runs/{run_id}` exists
  - relevant `POST` routes set `Location` headers for the created durable resource

### 4. Follow-Up Gap Closures After Roadmap Implementation

After the roadmap landed, the edge surfaces were re-audited and three additional high-signal gaps were closed.

Commits:

- `48c1e2e` `Require auth for remote read endpoints`
- `4520cda` `Gate sensitive remote read surfaces by capability`
- `f68bdfe` `Normalize search edge error contracts`

What these follow-up fixes changed:

- remote `GET` and `HEAD` access now requires the API key by default:
  - `/health` remains public
  - local mode remains unchanged
- authenticated remote reads are no longer implicitly trusted:
  - sensitive read surfaces now require explicit capabilities
  - this includes runtime diagnostics, quality endpoints, agent-task reads, raw document inspection/artifact routes, and replay/history reads
- search/task edge failures now return more stable machine-readable errors:
  - route-level validation wrappers now emit `error_code`
  - search history and replay not-found/validation failures now emit structured API errors instead of plain strings

### 5. Session Artifacts And Docs

Docs committed in this session:

- `0c0ad92` `Add system review document`

This handoff update will be committed after the file is written.

## Files Touched During This Session

Primary implementation files:

- [app/api/main.py](/Users/chunkstand/Documents/docling-system/app/api/main.py)
- [app/core/config.py](/Users/chunkstand/Documents/docling-system/app/core/config.py)
- [app/api/errors.py](/Users/chunkstand/Documents/docling-system/app/api/errors.py)
- [app/services/documents.py](/Users/chunkstand/Documents/docling-system/app/services/documents.py)
- [app/services/storage.py](/Users/chunkstand/Documents/docling-system/app/services/storage.py)
- [app/services/idempotency.py](/Users/chunkstand/Documents/docling-system/app/services/idempotency.py)
- [app/services/search_history.py](/Users/chunkstand/Documents/docling-system/app/services/search_history.py)
- [app/services/search_replays.py](/Users/chunkstand/Documents/docling-system/app/services/search_replays.py)
- [app/db/models.py](/Users/chunkstand/Documents/docling-system/app/db/models.py)
- [alembic/versions/0022_api_idempotency_keys.py](/Users/chunkstand/Documents/docling-system/alembic/versions/0022_api_idempotency_keys.py)

Primary test files added or updated:

- [tests/unit/test_api_runtime.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_api_runtime.py)
- [tests/unit/test_health.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_health.py)
- [tests/unit/test_documents_api.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_documents_api.py)
- [tests/unit/test_reprocess_api.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_reprocess_api.py)
- [tests/unit/test_document_service.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_document_service.py)
- [tests/unit/test_cleanup.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_cleanup.py)
- [tests/unit/test_agent_tasks_api.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_agent_tasks_api.py)
- [tests/unit/test_search_api.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_search_api.py)
- [tests/unit/test_idempotency_service.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_idempotency_service.py)
- [tests/unit/test_search_history.py](/Users/chunkstand/Documents/docling-system/tests/unit/test_search_history.py)

## Verification

Verification was run after each milestone and again at the end.

Final full-suite result at the end of the session:

- `pytest -q`
- result: `336 passed, 14 skipped`

Focused milestone verification also ran repeatedly across the touched API and service slices, including:

- API runtime and health
- documents API and reprocess API
- document service and cleanup
- agent-tasks API
- search API and search history/idempotency slices

## Commits From This Session

Chronological hardening and docs commits from this session:

- `19746ab` `Fix priority 1 hardening issues`
- `f91160c` `Add explicit local and remote API modes`
- `10e3007` `Harden artifact delivery through storage-owned paths`
- `31acb5f` `Add shared ingest admission with remote backpressure`
- `dd8bf48` `Add structured errors and command idempotency`
- `cf4626d` `Gate remote capabilities and expose durable run resources`
- `48c1e2e` `Require auth for remote read endpoints`
- `4520cda` `Gate sensitive remote read surfaces by capability`
- `f68bdfe` `Normalize search edge error contracts`
- `0c0ad92` `Add system review document`

## Current State Of The System

What is now true:

- `local` and `remote` API modes are explicit and enforced
- non-loopback remote serving requires an API key
- remote reads as well as remote writes are protected
- high-power remote read and write surfaces are capability-gated
- artifact download routes are storage-root-constrained
- document create/reprocess support idempotent retries
- document ingest admission is more consistent across entry paths
- remote ingest can shed load when inflight document runs are already at capacity
- durable run resources are first-class and directly readable
- direct application `HTTPException` construction is centralized through `api_error(...)`
- agent-task creation rejects dependency graphs that already contain cycles
- search harness evaluations are first-class persisted resources with source replay provenance
- the current full unit/integration test suite is green in local verification

## Residual Risks And Next Steps

The highest-signal residuals after this session are:

- capability enforcement is still deployment-wide rather than actor-aware authorization

Recommended next step:

1. Only add actor-aware authz if the deployment model becomes genuinely multi-user or hosted.

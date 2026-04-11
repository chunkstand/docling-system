# Session Handoff

Date: 2026-04-10 (local) / 2026-04-11 UTC runtime timestamps
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `codex/docling-system-build`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Last committed checkpoint: `924eae9` (`Add structural merge checks to evaluations`)

## Executive Summary

The system has moved past the earlier evaluation-storage checkpoint and now has a stronger, more practical ingestion baseline for UPC work.

The important durable pieces remain in place:

- `docs/evaluation_corpus.yaml` drives persisted run-scoped evaluations
- production search can execute against explicit `run_id` values
- evaluation summaries and query rows are stored in Postgres
- latest evaluation results are exposed through API and UI
- validation still gates promotion of `documents.active_run_id`

This follow-up work added four concrete operational improvements:

- chapter 4 now has a fixture in the fixed evaluation corpus and evaluates cleanly
- chapter 5 table normalization was hardened so title-only/empty spacer fragments no longer create false zero-row logical tables
- known-bad table families can now be repaired through a registry-driven supplement mechanism in `config/table_supplements.yaml` instead of hardcoded one-off parser rules
- evaluation fixtures can now enforce structural merge expectations through `expected_merged_tables`, so repaired families are checked by persisted evaluation instead of only by ad hoc artifact inspection

The current registry contains the first real repair rule:

- `UPC_CH_5.pdf` can overlay the corrupted `TABLE 510.1.2(n)` family from the clean `510.1.2.pdf` supplement while preserving chapter-local page spans and original table-segment provenance

The current fixed-corpus structural merge check contains the first real repair assertion:

- `upc_ch5` requires the repaired `TABLE 510.1.2(2)` family to exist as a merged overlay-backed logical table on pages `109-113` with `overlay_family_key=TABLE 510.1.2(2)`

The branch is committed, the runtime is healthy, and the system is ready for the next UPC chapters.

## Current Runtime State

At handoff time:

- Postgres is healthy on `localhost:5432`
- API is running on `http://127.0.0.1:8000`
- one worker process is running
- Alembic head is `0008_run_evaluations`
- run queue is empty: `0 queued`, `0 processing`, `0 validating`, `0 retry_wait`

Verification:

```bash
curl -sS http://127.0.0.1:8000/health
uv run alembic current
```

Results:

```json
{"status":"ok"}
```

```text
0008_run_evaluations (head)
```

Current active document set:

```json
[
  {
    "source_filename": "UPC_CH_5.pdf",
    "active_run_id": "7d8559b8-848f-40bc-bf39-2e6da7f8c15f",
    "latest_validation_status": "passed",
    "table_count": 41,
    "figure_count": 41,
    "latest_evaluation_fixture": "upc_ch5",
    "latest_evaluation_status": "completed"
  },
  {
    "source_filename": "UPC_CH_4.pdf",
    "active_run_id": "9def6693-353e-4580-832e-391e4a8cdd12",
    "latest_validation_status": "passed",
    "table_count": 3,
    "figure_count": 0,
    "latest_evaluation_fixture": "upc_ch4",
    "latest_evaluation_status": "completed"
  },
  {
    "source_filename": "UPC_Appendix_B.pdf",
    "active_run_id": "79bba82b-37b7-4e07-a915-380b83f98527",
    "latest_validation_status": "passed",
    "latest_evaluation_status": "skipped"
  },
  {
    "source_filename": "UPC_Appendix_N.pdf",
    "active_run_id": "befc5635-1cab-456c-b8bf-0aa27fd6497f",
    "latest_validation_status": "passed",
    "table_count": 1,
    "figure_count": 0,
    "latest_evaluation_fixture": "born_digital_simple",
    "latest_evaluation_status": "completed"
  },
  {
    "source_filename": "UPC_CH_1.pdf",
    "active_run_id": "2c95e372-0b2a-46f0-9c1e-f6c3a85b5137",
    "latest_validation_status": "passed",
    "table_count": 0,
    "figure_count": 0,
    "latest_evaluation_fixture": "prose_control",
    "latest_evaluation_status": "completed"
  },
  {
    "source_filename": "UPC_Ch_2.pdf",
    "active_run_id": "2c094484-7651-4efd-b26a-0b9b8ca9237c",
    "latest_validation_status": "passed",
    "table_count": 0,
    "figure_count": 18,
    "latest_evaluation_fixture": "upc_ch2_figures",
    "latest_evaluation_status": "completed"
  },
  {
    "source_filename": "UPC_CH_3.pdf",
    "active_run_id": "0ac3a1ff-5a6b-47d6-90a1-31157b0e055c",
    "latest_validation_status": "passed",
    "table_count": 2,
    "figure_count": 29,
    "latest_evaluation_fixture": "awkward_headers",
    "latest_evaluation_status": "completed"
  },
  {
    "source_filename": "UPC_CH_7.pdf",
    "active_run_id": "cc4c107c-a1ab-4bc4-b461-355aadcd7855",
    "latest_validation_status": "passed",
    "table_count": 11,
    "figure_count": 10,
    "latest_evaluation_fixture": "upc_ch7",
    "latest_evaluation_status": "completed"
  }
]
```

## What Changed In This Session

### 1. Run-Scoped Evaluation Storage

Added persisted evaluation storage:

- `document_run_evaluations`
- `document_run_evaluation_queries`

Files:

- `app/db/models.py`
- `alembic/versions/0008_run_evaluations.py`

Current stored evaluation contract:

- one evaluation record per `(run_id, corpus_name, eval_version)`
- fixture name
- evaluation status: `pending`, `completed`, `failed`, or `skipped`
- summary JSON with aggregate counts
- summary JSON also includes structural evaluation results, including `structural_passed`, per-check details, and merge expectation outcomes
- per-query rows with:
  - query text
  - search mode
  - filters
  - expected result type
  - expected top-N threshold
  - pass/fail
  - candidate rank
  - baseline rank
  - rank delta
  - candidate/baseline score
  - candidate/baseline labels
  - top-result snapshots in details JSON

### 2. Search Refactor For Explicit `run_id`

Production search now supports two scopes using the same code path:

- default active-run search for API/UI behavior
- explicit `run_id` search for evaluation

File:

- `app/services/search.py`

Important implementation detail:

- evaluation does not use a parallel “shadow” search implementation
- it calls the same production search/ranking logic with `run_id=<candidate>` or `run_id=<baseline>`

This was the main architectural requirement for trustworthy regression deltas.

### 3. Evaluation Service

Added a new evaluation service:

- `app/services/evaluations.py`

Behavior:

- reads `docs/evaluation_corpus.yaml`
- matches a fixture by `document.source_filename`
- compiles expected table/chunk queries into evaluation cases
- evaluates the candidate run
- optionally evaluates a baseline run
- persists summary and per-query rows

Current corpus behavior:

- fixtures with no matching path are skipped
- matched fixtures produce stored evaluation results
- query-level pass/fail is based on expected result type appearing within expected top-N
- structural checks can additionally enforce logical table counts, figure counts, figure artifact/provenance coverage, and expected merged-table overlays

### 4. Worker Integration

Evaluation is now part of the worker path.

Order:

1. parse
2. persist artifacts/chunks/tables/figures
3. validate
4. evaluate
5. promote

File:

- `app/services/runs.py`

Important choice:

- evaluation is non-blocking for promotion in the current implementation
- validation still gates promotion
- evaluation failure records evaluation status but does not currently reject an otherwise valid run

### 5. CLI Commands

Added:

- `docling-system-eval-run <run_id> [--baseline-run-id <run_id>]`
- `docling-system-eval-corpus`

Files:

- `app/cli.py`
- `pyproject.toml`

Purpose:

- operator-triggered re-evaluation of one run
- batch re-evaluation of all active documents with matching fixtures

### 6. API And UI Surfacing

Added:

- latest evaluation summary on document list/detail payloads
- `GET /documents/{document_id}/evaluations/latest`
- read-only UI rendering for latest evaluation status and per-query results

Files:

- `app/schemas/evaluations.py`
- `app/schemas/documents.py`
- `app/services/documents.py`
- `app/api/main.py`
- `app/ui/index.html`
- `app/ui/app.js`

Live example:

`GET /documents/4a8da24f-603b-4540-baa2-431a2b10baaf/evaluations/latest` currently returns:

- fixture: `awkward_headers`
- `query_count: 3`
- `passed_queries: 3`
- `failed_queries: 0`
- all three queries currently rank the expected type at candidate rank `1`

### 7. Baseline-Aware Reprocess Evaluation

The worker and evaluation service now preserve the document's prior active run as the evaluation baseline before promotion.

Files:

- `app/services/evaluations.py`
- `app/services/runs.py`
- `app/cli.py`
- `tests/unit/test_evaluation_service.py`
- `tests/unit/test_run_logic.py`
- `tests/unit/test_cli.py`

Current behavior:

- when a non-active candidate run is evaluated, the default baseline is the document's current active run
- the worker captures that baseline before any promotion can occur
- explicit CLI baselines still work, but self-baselines are ignored
- baseline validation now rejects cross-document or missing baseline run IDs

This closes the main gap from the prior handoff: future reprocess evaluations now persist real longitudinal deltas by default.

### 8. Ruff-Clean Repository

Added `ruff` to the dev environment and cleaned the repository to pass lint.

Files:

- `pyproject.toml`
- `uv.lock`
- multiple `app/` and `tests/` modules reformatted or line-broken to satisfy Ruff

Important implementation choice:

- `app/api/main.py` has a targeted Ruff per-file ignore for `B008`
- this is intentional because FastAPI dependency and file parameter defaults use `Depends(...)` and `File(...)` idiomatically
- the ignore is narrow and keeps `B008` enabled elsewhere

### 9. Chapter 4 Evaluation Fixture

Added a fixed-corpus fixture for chapter 4.

Files:

- `docs/evaluation_corpus.yaml`
- `tests/unit/test_eval_config.py`

Current fixture:

- `name: upc_ch4`
- `path: /Users/chunkstand/Documents/UPC/UPC_CH_4.pdf`
- expected logical table count: `3`
- expected figure count: `0`
- expected table query: `minimum required plumbing fixtures`
- expected chunk query: `public lavatories`

The current active chapter 4 run evaluates cleanly with `2/2` queries passing.

### 10. Chapter 5 Table Normalization Hardening

Chapter 5 initially failed validation because badly scanned venting tables produced logical tables with empty previews and invalid row counts.

Files:

- `app/services/docling_parser.py`
- `tests/unit/test_docling_parser.py`
- `tests/unit/test_validation.py`

Current behavior:

- logical-table `row_count` and `col_count` are derived from normalized grid rows, not Docling's declared counts
- title-only empty spacer segments are collapsed before logical-table merging
- carried page spans are preserved when those empty segments bridge real continuation fragments

This keeps chapter 5 promotable without weakening the validation contract.

### 11. Registry-Driven Table Supplements

The one-off chapter-5 overlay path has been replaced with a small registry-driven repair mechanism.

Files:

- `config/table_supplements.yaml`
- `app/core/config.py`
- `app/services/docling_parser.py`
- `tests/unit/test_docling_parser.py`

Current behavior:

- supplement rules are loaded from `config/table_supplements.yaml`
- rules match by canonical source filename
- supplement PDFs are resolved from the source directory or allowed local roots
- overlays are applied by matcher strategy, currently `upc_510_family`
- overlay metadata is persisted on the replacement logical tables
- chapter-local page spans and original source-segment provenance are retained

Current live rule:

- `UPC_CH_5.pdf` + `510.1.2.pdf` + matcher `upc_510_family`

Current live result on active run `7d8559b8-848f-40bc-bf39-2e6da7f8c15f`:

- `TABLE 510.1.2(1)` pages `103-108`
- `TABLE 510.1.2(2)` pages `109-113`
- `TABLE 510.1.2(3)` pages `114-116`
- `TABLE 510.1.2(4)` pages `117-119`
- `TABLE 510.1.2(5)` pages `120-121`
- `TABLE 510.1.2(6)` pages `122-124`

### 12. Structural Merge Checks In Evaluation

Evaluation fixtures can now assert structural merge expectations directly.

Files:

- `app/services/evaluations.py`
- `docs/evaluation_corpus.yaml`
- `tests/unit/test_evaluation_service.py`
- `tests/unit/test_eval_config.py`

Current behavior:

- fixtures can declare `expected_merged_tables`
- merge expectations can match by title text, heading text, page span, minimum source segment count, and overlay metadata
- evaluation summaries now include `structural_passed`, `structural_check_count`, `failed_structural_checks`, and detailed structural-check rows
- repaired-family regressions can now fail the structural portion of evaluation even if simple search queries still pass

Current live chapter 5 result:

- latest chapter 5 evaluation reports `structural_passed: true`
- the repaired `TABLE 510.1.2(2)` overlay family is matched as an expected merged table

## Evaluation Corpus Status

Current configured fixtures:

- `upc_ch7`
- `upc_ch2_figures`
- `born_digital_simple`
- `awkward_headers`
- `upc_ch4`
- `upc_ch5`
- `prose_control`

Corpus-wide evaluation command:

```bash
uv run docling-system-eval-corpus
```

Current result:

- all seven configured fixtures complete successfully
- all configured query cases currently pass
- chapter 5 also passes structural merge checks for the repaired `510.1.2(2)` family

Important limitation:

- historical evaluation rows created before this session may still have `baseline_run_id: null`
- future reprocess evaluations now default to the prior active run baseline, but existing stored rows are not backfilled automatically

## Current Contracts

### Promotion Gate

Promotion still requires validation success before `documents.active_run_id` advances.

Evaluation does not currently gate promotion.

This split is intentional:

- validation protects search integrity and artifact correctness
- evaluation measures retrieval quality over time

### Search

`POST /search` remains the active-corpus endpoint.

New internal/runtime capability:

- the service layer can now execute the same search path against an explicit `run_id`

This is used by evaluation and should remain the single ranking implementation.

### Table Supplements

Table supplements are now a first-class provisional repair mechanism, but they are not a second canonical ingest path.

Keep these constraints:

- the chapter PDF remains the canonical document source
- supplement PDFs are narrow repair inputs for specific corrupted table families
- overlay outputs must preserve the chapter-local page span and original source-segment lineage
- registry entries should remain sparse, explicit, and test-covered

### Future Supplement Workflow

For future sessions adding new chapter PDFs with supporting clean tables, follow this exact sequence:

1. ingest the chapter PDF as the canonical document
2. place the clean supporting table PDF under an allowed local root
3. add a registry rule in `config/table_supplements.yaml`
4. reprocess the chapter and inspect the replacement family once
5. add or extend the matching fixture in `docs/evaluation_corpus.yaml`
6. include `expected_merged_tables` for the repaired family when there is a stable identity for it
7. run `uv run docling-system-eval-run <run_id>` and confirm `summary.structural_passed` is `true`

### Evaluation Storage

Evaluation is now a first-class persisted subsystem and must not be overloaded into:

- `validation_results_json`
- ad hoc metric files
- hand-written notes in docs

Validation and evaluation are separate concerns and should remain separate.

## Files Changed Or Added Recently

Core runtime:

- `app/api/main.py`
- `app/cli.py`
- `app/core/config.py`
- `app/db/models.py`
- `app/schemas/documents.py`
- `app/schemas/evaluations.py`
- `app/services/documents.py`
- `app/services/docling_parser.py`
- `app/services/evaluations.py`
- `app/services/runs.py`
- `app/services/search.py`

UI:

- `app/ui/index.html`
- `app/ui/app.js`

Migration:

- `alembic/versions/0008_run_evaluations.py`

Tests:

- `tests/unit/test_cli.py`
- `tests/unit/test_documents_api.py`
- `tests/unit/test_docling_parser.py`
- `tests/unit/test_evaluation_service.py`
- `tests/unit/test_eval_config.py`
- `tests/unit/test_search_service.py`
- `tests/unit/test_ui.py`

Config:

- `config/table_supplements.yaml`
- `pyproject.toml`

## Verification Performed

Commands run across the last two sessions:

```bash
uv run alembic upgrade head
uv run pytest tests
uv run python -m compileall app tests
uv run docling-system-eval-corpus
uv run pytest tests/unit/test_docling_parser.py tests/unit/test_validation.py -q
uv run pytest tests/unit/test_evaluation_service.py tests/unit/test_eval_config.py -q
uv run ruff check app tests
curl -sS http://127.0.0.1:8000/documents/<document_id>/evaluations/latest | jq
curl -sS http://127.0.0.1:8000/documents | jq
```

Passing results:

- `uv run pytest tests` -> `47 passed, 1 skipped`
- `uv run pytest tests/unit/test_docling_parser.py tests/unit/test_validation.py -q` -> `13 passed`
- `uv run pytest tests/unit/test_evaluation_service.py tests/unit/test_eval_config.py -q` -> `7 passed`
- `uv run python -m compileall app tests` passed
- `uv run ruff check app tests` passed
- migration to `0008_run_evaluations` passed
- batch evaluation over the configured corpus completed successfully
- live reprocess of `UPC_CH_5.pdf` completed and promoted as run `7d8559b8-848f-40bc-bf39-2e6da7f8c15f`
- live chapter 5 evaluation now reports `structural_passed: true` for the repaired `510.1.2(2)` family

Live runtime checks:

- API health check succeeded
- API and worker processes are currently running
- queue counts are currently all zero outside `completed`
- document list now includes `latest_evaluation`
- latest evaluation route returns persisted query-level rows

## Known Gaps / Risks

### 1. Evaluation Does Not Yet Gate Promotion

This is deliberate for now, but it means:

- a retrieval regression can still be promoted if validation passes

That is a good v1 default while metrics are new, but not the likely end state.

### 2. Historical Evaluations Are Still Sparse

The schema and worker now support real baseline deltas for reprocess runs, but:

- previously stored evaluation rows may still have `baseline_run_id: null`
- the current corpus still has relatively few query cases per fixture

The next useful step is to generate more candidate reprocesses and broaden the corpus so the delta data becomes richer.

### 3. `UPC_Appendix_B.pdf` Is In The Document Set But Not In The Eval Corpus

There is an active document for:

- `UPC_Appendix_B.pdf`

It has:

- validation `passed`
- `table_count=0`
- no evaluation fixture match

This is not a correctness issue, but it is an example of a document in the system that is outside the current fixed eval set.

### 4. The Branch Is Committed But Not Pushed From This Handoff

The current branch is clean and committed through:

- `924eae9` `Add structural merge checks to evaluations`

Do not assume that commit has been pushed unless you verify it explicitly.

## Next Steps For The Next Session

### Priority 1: Decide Whether Evaluation Should Influence Promotion

Recommended path:

1. keep validation as the hard promotion gate
2. add explicit policy for eval-based warnings vs blocking failures
3. only make evaluation gating mandatory after baseline deltas are stable and trusted

### Priority 2: Expand Corpus Richness

The baseline plumbing is now in place. The next leverage point is to increase corpus depth:

- add more query cases per fixture
- explicitly include mode and filters where it matters
- add negative or adversarial queries where ranking confusion is likely
- when new supplement-backed repairs are added, include `expected_merged_tables` so the repaired family is structurally pinned in evaluation

### Priority 3: Continue UPC Uploads

The current active chapter set is:

- `UPC_CH_1.pdf`
- `UPC_Ch_2.pdf`
- `UPC_CH_3.pdf`
- `UPC_CH_4.pdf`
- `UPC_CH_5.pdf`
- `UPC_CH_7.pdf`

The current non-chapter ingests are:

- `UPC_Appendix_B.pdf`
- `UPC_Appendix_N.pdf`

The runtime is healthy and ready to continue chapter uploads.

## Handy Commands

Health:

```bash
curl -sS http://127.0.0.1:8000/health
```

List documents:

```bash
curl -sS http://127.0.0.1:8000/documents | jq
```

Read latest evaluation:

```bash
curl -sS http://127.0.0.1:8000/documents/<document_id>/evaluations/latest | jq
```

Evaluate one run:

```bash
uv run docling-system-eval-run <run_id>
```

Evaluate one run against a baseline:

```bash
uv run docling-system-eval-run <candidate_run_id> --baseline-run-id <baseline_run_id>
```

Evaluate all matching active fixtures:

```bash
uv run docling-system-eval-corpus
```

Run full tests:

```bash
uv run pytest tests
```

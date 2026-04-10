# Session Handoff

Date: 2026-04-10
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `codex/docling-system-build`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`

## Executive Summary

The system is running locally and is materially ahead of GitHub `main`.

The current implementation includes:

- durable DB-backed document runs
- validation-gated promotion through `documents.active_run_id`
- canonical `docling.json` plus human-readable `document.yaml`
- first-class tables with JSON/YAML artifacts, segment provenance, and mixed retrieval
- first-class figures/diagrams with JSON/YAML artifacts, caption attachment metadata, provenance, and confidence
- read-only UI
- CLI local-file ingest
- evaluation corpus config with prose, table, and figure fixtures

The most important change in this session was finishing first-class figure support and then fixing a real table continuation gap in Chapter 3. `TABLE 313.3 HANGERS AND SUPPORTS` now merges into one logical table across pages 35-36 when processed with the patched parser.

## Current Runtime State

At handoff time:

- Postgres container is healthy on `localhost:5432`
- API is healthy at `http://127.0.0.1:8000`
- worker process is running again

Verification:

```bash
curl -sS http://127.0.0.1:8000/health
```

Result:

```json
{"status":"ok"}
```

Current active document set:

```json
[
  {
    "document_id": "4a8da24f-603b-4540-baa2-431a2b10baaf",
    "source_filename": "UPC_CH_3.pdf",
    "active_run_id": "0ac3a1ff-5a6b-47d6-90a1-31157b0e055c",
    "latest_validation_status": "passed",
    "table_count": 2,
    "figure_count": 29
  },
  {
    "document_id": "215a55c7-508f-41ba-8440-cba24f0c3e41",
    "source_filename": "UPC_Ch_2.pdf",
    "active_run_id": "2c094484-7651-4efd-b26a-0b9b8ca9237c",
    "latest_validation_status": "passed",
    "table_count": 0,
    "figure_count": 18
  },
  {
    "document_id": "f9cf2f57-441f-495b-9fb1-6108da3d1731",
    "source_filename": "UPC_CH_7.pdf",
    "active_run_id": "cc4c107c-a1ab-4bc4-b461-355aadcd7855",
    "latest_validation_status": "passed",
    "table_count": 11,
    "figure_count": 10
  },
  {
    "document_id": "a85d7a04-5ee6-4067-af9b-7012f54fab39",
    "source_filename": "UPC_CH_1.pdf",
    "active_run_id": "2c95e372-0b2a-46f0-9c1e-f6c3a85b5137",
    "latest_validation_status": "passed",
    "table_count": 0,
    "figure_count": 0
  }
]
```

## What Changed In This Session

### 1. First-Class Figures / Diagram Integrity

Added first-class figure support across parser, persistence, validation, storage, API, cleanup, and UI.

Main files:

- `app/services/docling_parser.py`
- `app/db/models.py`
- `app/services/runs.py`
- `app/services/validation.py`
- `app/services/storage.py`
- `app/services/documents.py`
- `app/api/main.py`
- `app/services/figures.py`
- `app/schemas/figures.py`
- `app/ui/index.html`
- `app/ui/app.js`
- `alembic/versions/0007_document_figures.py`

Current figure contract:

- run-scoped `figure_id`
- `source_figure_ref`
- caption
- heading
- page range
- confidence
- JSON artifact
- YAML artifact
- caption resolution source
- caption attachment confidence
- source confidence if present
- normalized provenance including bbox and page number

Current figure behavior:

- explicit Docling caption refs are preferred when available
- fallback caption heuristics use nearby caption/text items
- fallback vs explicit attachment is stored in metadata
- figures are validation-gated before promotion, same as tables

Live examples from Chapter 2:

- `Bottle Fillers and Drinking Fountain Alts.`
- `Grease Interceptors (UPC)`
- `PrimaryDefinition: Invert`

### 2. Worker / API Module Entrypoints

Added `if __name__ == "__main__": run()` to:

- `app/api/main.py`
- `app/workers/poller.py`

Reason:

- `python -m app.api.main`
- `python -m app.workers.poller`

were not reliable before because the module `run()` functions were not invoked on direct module execution. This was a real runtime gap discovered during validation.

### 3. Chapter 2 Ingest and Figure Eval Coverage

Ingested:

- `/Users/chunkstand/Documents/UPC/UPC_Ch_2.pdf`

Result:

- `document_id`: `215a55c7-508f-41ba-8440-cba24f0c3e41`
- active `run_id`: `2c094484-7651-4efd-b26a-0b9b8ca9237c`
- validation: `passed`
- tables: `0`
- figures: `18`

This document is now the figure-heavy eval fixture in:

- `docs/evaluation_corpus.yaml`

Fixture name:

- `upc_ch2_figures`

Thresholds added:

- `expected_figure_count: 18`
- `figure_count_tolerance: 1`
- `minimum_captioned_figure_count: 18`
- `minimum_figures_with_provenance: 18`
- `minimum_figures_with_artifacts: 18`
- expected figure captions:
  - `Bottle Fillers and Drinking Fountain Alts.`
  - `Grease Interceptors (UPC)`
  - `PrimaryDefinition: Invert`
- expected chunk-hit queries:
  - `accepted engineering practice`
  - `air gap`

### 4. Chapter 3 Ingest and Table Continuation Fix

Ingested:

- `/Users/chunkstand/Documents/UPC/UPC_CH_3.pdf`

Initial behavior:

- `TABLE 313.3 HANGERS AND SUPPORTS` appeared as two logical tables on pages 35 and 36
- both were marked `ambiguous_continuation_candidate: true`

Parser fix:

- updated `app/services/docling_parser.py`
- added `_segment_merge_reason(...)`
- allowed adjacent same-title same-heading continuation merges even when column count drifts across pages
- lowered merge confidence for this case instead of blocking the merge entirely

New merge behavior:

- `TABLE 313.3 HANGERS AND SUPPORTS` now merges into one logical table over pages 35-36
- merge metadata:
  - `merge_reason: adjacent_same_title_heading_continuation`
  - lower `merge_confidence` than exact-shape merges

Important verification detail:

- The live worker path was noisy because an older worker process was still around during one reprocess.
- To verify the parser fix deterministically, I queued a fresh Chapter 3 run and processed it directly with `process_run(...)` in a one-off script.
- That direct run promoted successfully and is now the active Chapter 3 run.

Current active Chapter 3 result:

- `document_id`: `4a8da24f-603b-4540-baa2-431a2b10baaf`
- active `run_id`: `0ac3a1ff-5a6b-47d6-90a1-31157b0e055c`
- validation: `passed`
- table count: `2`
- figure count: `29`

Active Chapter 3 tables now:

1. `TABLE 313.3 HANGERS AND SUPPORTS`
   - pages `35-36`
   - row_count `17`
2. `HANGER ROD SIZES`
   - page `38`

### 5. Evaluation Corpus Updates

`docs/evaluation_corpus.yaml` now has real fixtures for:

- `upc_ch7`
  - multi-page standards tables
- `upc_ch2_figures`
  - figure-heavy definitions
- `awkward_headers`
  - now points to `UPC_CH_3.pdf`
- `prose_control`
  - `UPC_CH_1.pdf`

Current `awkward_headers` config:

- path: `/Users/chunkstand/Documents/UPC/UPC_CH_3.pdf`
- expected logical table count: `2`
- logical table tolerance: `0`
- maximum unexpected merges: `0`
- maximum unexpected splits: `0`
- expected top-N table queries:
  - `hangers and supports`
  - `hanger rod sizes`
- expected top-N chunk query:
  - `listed standards`

Note:

- `born_digital_simple` is still a placeholder and still needs a real PDF.

## Current Contracts

### Artifact Canon

Document level:

- canonical machine-readable artifact: `docling.json`
- human-readable artifact: `document.yaml`

Table level:

- canonical machine-readable artifact: normalized table JSON
- human-readable artifact: normalized table YAML

Figure level:

- canonical machine-readable artifact: normalized figure JSON
- human-readable artifact: normalized figure YAML

Important rule:

- JSON-backed structured objects and normalized DB fields are the machine-facing source of truth.
- YAML exists for operator/agent readability and inspection, not as a storage-of-record for retrieval.

### Promotion Gate

Promotion still requires validation success before `documents.active_run_id` advances.

Current validation scope includes:

- document artifact existence
- chunk persistence count checks
- title/page-count sanity
- table artifact existence and search-text sanity
- table row/column sanity
- continued-table merge sanity
- repeated-header-removal sanity
- figure artifact existence
- figure provenance presence
- figure caption-resolution metadata presence
- figure confidence-field presence

### Search

Mixed `/search` is still:

- immediate replacement rollout
- typed result set with `chunk` and `table`
- deterministic merge/tie-break rules

Important limitation:

- figures are first-class integrity objects, not yet `result_type="figure"` search results

Important ranking note:

- Chapter 3 continuation is fixed
- but some table-title queries still rank chunk hits above table hits
- the awkward-table eval thresholds currently allow top-3 table presence rather than requiring rank-1 dominance

## Files Changed Or Added Recently

Core runtime:

- `app/api/main.py`
- `app/db/models.py`
- `app/schemas/documents.py`
- `app/schemas/figures.py`
- `app/services/cleanup.py`
- `app/services/docling_parser.py`
- `app/services/documents.py`
- `app/services/figures.py`
- `app/services/runs.py`
- `app/services/storage.py`
- `app/services/validation.py`
- `app/workers/poller.py`

Docs/config:

- `README.md`
- `SYSTEM_PLAN.md`
- `AGENTS.md`
- `.env.example`
- `docs/evaluation_corpus.yaml`
- `docs/SESSION_HANDOFF.md`

Migrations:

- `alembic/versions/0002_document_run_cleanup_index.py`
- `alembic/versions/0003_document_tables.py`
- `alembic/versions/0004_yaml_artifacts.py`
- `alembic/versions/0005_validation_gate_fields.py`
- `alembic/versions/0006_table_hardening_fields.py`
- `alembic/versions/0007_document_figures.py`

Tests:

- `tests/unit/test_docling_parser.py`
- `tests/unit/test_eval_config.py`
- `tests/unit/test_figures_api.py`
- `tests/unit/test_validation.py`
- plus previously added table/search/UI/telemetry tests

## Verification Performed

During this session:

```bash
uv run pytest tests/unit/test_docling_parser.py tests/unit/test_eval_config.py
uv run pytest tests/unit/test_eval_config.py
uv run python -m compileall app tests
uv run alembic upgrade head
```

Relevant passing results:

- figure parser/API/validation tests passed earlier in session
- `tests/unit/test_docling_parser.py` passed with the new Chapter 3 continuation case
- `tests/unit/test_eval_config.py` passed after adding figure coverage and the Chapter 3 awkward-table fixture
- `uv run pytest tests` had previously passed at `35 passed, 1 skipped` before the Chapter 3 continuation patch

Live runtime checks performed:

- API health check succeeded
- Chapter 2 ingest completed and promoted
- Chapter 3 ingest completed and promoted
- Chapter 3 deterministic reprocess through `process_run(...)` completed and promoted with `table_count=2`

## Known Gaps / Risks

### 1. Ranking Still Needs Work

Even after fixing the Chapter 3 continuation split, some table-title queries still return chunk hits above table hits.

Example:

- query: `hangers and supports`

Current behavior:

- chunk title/caption-like hits rank above the merged table hit
- table hit is still present in top 3

This is acceptable under the current eval thresholds, but it is not ideal retrieval quality.

### 2. `born_digital_simple` Eval Slot Still Empty

The evaluation corpus still needs a real simple-table document for:

- `born_digital_simple`

This is the main missing eval fixture now.

### 3. Worktree Is Not Clean

There are still many local modifications and untracked files in the repo. This work has not been committed yet.

This includes:

- runtime files
- docs
- migrations
- tests
- UI files

Do not assume the branch is committed or pushed.

## Next Steps For The Next Session

### Priority 1: Ingest The Next PDF

Continue one PDF at a time.

Reason:

- the eval workflow is working best when each document is classified individually as prose-heavy, figure-heavy, simple-table, or awkward-table

Immediate target:

- find a real candidate for the `born_digital_simple` eval slot

What to do:

1. ingest the next PDF with `uv run docling-system-ingest-file ...`
2. inspect:
   - chunk count
   - table count
   - figure count
   - whether tables are continued/awkward or simple
3. if it is a clean simple-table document, replace `born_digital_simple.path: null` in `docs/evaluation_corpus.yaml`

### Priority 2: Improve Table Ranking

After the next fixture is in place, work on ranking so true table-title queries rank table hits above chunk title/caption noise more consistently.

Likely place:

- `app/services/search.py`

Focus queries:

- `hangers and supports`
- `hanger rod sizes`
- `drainage fixture unit values`

### Priority 3: Re-Run Full Suite After Ranking Changes

Once ranking changes are made:

```bash
uv run pytest tests
```

Then verify:

- Chapter 3 still has `table_count=2`
- Chapter 7 still has `table_count=11`
- Chapter 2 still has `figure_count=18`

### Priority 4: Commit Milestone Work

This branch needs a real commit point. After the next fixture and any ranking adjustments are stable:

1. review `git status`
2. stage intentional files
3. commit the milestone
4. push to `origin`

## Handy Commands

Health:

```bash
curl -sS http://127.0.0.1:8000/health
```

List documents:

```bash
curl -sS http://127.0.0.1:8000/documents | jq
```

Ingest local file:

```bash
uv run docling-system-ingest-file /absolute/path/to/file.pdf
```

Reprocess one document:

```bash
curl -s -X POST http://127.0.0.1:8000/documents/<document_id>/reprocess
```

Run worker manually:

```bash
uv run python -m app.workers.poller
```

Run API manually:

```bash
uv run python -m app.api.main
```

Apply migrations:

```bash
uv run alembic upgrade head
```

Run full tests:

```bash
uv run pytest tests
```
